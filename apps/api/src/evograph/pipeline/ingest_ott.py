"""Ingest OpenTree taxonomy for a configurable scope (default: Aves).

Run as: python -m evograph.pipeline.ingest_ott [--scope Mammalia]
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import re

from sqlalchemy.dialects.postgresql import insert as pg_insert

from evograph.db.models import Taxon
from evograph.db.session import SessionLocal
from evograph.services.ott_client import OpenTreeClient
from evograph.settings import settings

logger = logging.getLogger(__name__)

# Matches both '_ott12345' (unquoted) and ' ott12345' (quoted labels)
_OTT_RE = re.compile(r"[_ ]ott(\d+)$")
BATCH_SIZE = 500


def _parse_label(label: str) -> tuple[str, int | None]:
    """Parse 'Parus_major_ott12345' or 'Some name ott12345' → (name, ott_id)."""
    m = _OTT_RE.search(label)
    if m:
        ott_id = int(m.group(1))
        name_part = label[: m.start()]
    else:
        ott_id = None
        name_part = label
    name = name_part.replace("_", " ").strip()
    return name, ott_id


def _parse_newick(newick: str) -> list[dict]:
    """Stack-based Newick parser. Returns flat list of nodes with parent links."""
    nodes: list[dict] = []
    nodes_by_id: dict[int, dict] = {}
    pos = 0
    n = len(newick)

    def _skip_ws():
        nonlocal pos
        while pos < n and newick[pos] in " \t\n\r":
            pos += 1

    def _read_label() -> str:
        nonlocal pos
        _skip_ws()
        if pos < n and newick[pos] == "'":
            pos += 1
            start = pos
            while pos < n and newick[pos] != "'":
                pos += 1
            label = newick[start:pos]
            if pos < n:
                pos += 1
            return label
        start = pos
        while pos < n and newick[pos] not in ",():; \t\n\r":
            pos += 1
        return newick[start:pos]

    def _skip_branch_length():
        nonlocal pos
        _skip_ws()
        if pos < n and newick[pos] == ":":
            pos += 1
            while pos < n and newick[pos] not in ",();":
                pos += 1

    def _add_node(label: str, child_ott_ids: list[int | None]) -> int | None:
        name, ott_id = _parse_label(label)
        is_leaf = len(child_ott_ids) == 0
        if ott_id is not None and ott_id not in nodes_by_id:
            node = {
                "ott_id": ott_id,
                "name": name,
                "rank": "",
                "parent_ott_id": None,
                "is_leaf": is_leaf,
            }
            nodes.append(node)
            nodes_by_id[ott_id] = node
            for cid in child_ott_ids:
                if cid is not None and cid in nodes_by_id:
                    nodes_by_id[cid]["parent_ott_id"] = ott_id
        return ott_id

    # Stack: each entry is a list of child ott_ids for the current group
    stack: list[list[int | None]] = [[]]

    while pos < n:
        _skip_ws()
        if pos >= n:
            break
        ch = newick[pos]
        if ch == "(":
            pos += 1
            stack.append([])
        elif ch == ")":
            pos += 1
            label = _read_label()
            _skip_branch_length()
            children = stack.pop()
            ott_id = _add_node(label, children)
            if stack:
                stack[-1].append(ott_id)
        elif ch == ",":
            pos += 1
        elif ch == ";":
            break
        else:
            label = _read_label()
            _skip_branch_length()
            ott_id = _add_node(label, [])
            if stack:
                stack[-1].append(ott_id)

    return nodes


def _infer_ranks(nodes: list[dict]) -> None:
    """Infer ranks heuristically from tree structure and name patterns.

    - Leaf nodes with binomial names → species
    - Other leaves → subspecies or no rank
    - Inner nodes: unknown until API enrichment
    """
    for node in nodes:
        name = node["name"]
        words = name.split()
        if node["is_leaf"]:
            if len(words) == 2 and words[0][0].isupper() and words[1][0].islower():
                node["rank"] = "species"
            elif len(words) >= 3:
                node["rank"] = "subspecies"
            else:
                node["rank"] = "no rank"
        else:
            node["rank"] = "no rank"


async def _enrich_ranks(client: OpenTreeClient, nodes: list[dict], batch: int = 50) -> None:
    """Fetch ranks from OpenTree API for inner nodes (non-species)."""
    inner = [n for n in nodes if n["rank"] == "no rank"]
    logger.info("Enriching ranks for %d inner nodes...", len(inner))

    for i in range(0, len(inner), batch):
        chunk = inner[i: i + batch]
        tasks = [client.taxon_info(n["ott_id"]) for n in chunk]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for node, result in zip(chunk, results):
            if isinstance(result, Exception):
                continue
            node["rank"] = result.get("rank", "no rank")
        done = min(i + batch, len(inner))
        if done % 200 == 0 or done == len(inner):
            logger.info("  Enriched %d / %d inner nodes", done, len(inner))


def _persist_nodes(nodes: list[dict]) -> int:
    """Upsert taxonomy nodes into DB using two-pass approach for FK safety."""
    session = SessionLocal()
    count = 0
    try:
        # Pass 1: Insert all nodes WITHOUT parent references
        logger.info("Pass 1: Inserting %d nodes (no parent refs)...", len(nodes))
        for i, node in enumerate(nodes):
            stmt = pg_insert(Taxon).values(
                ott_id=node["ott_id"],
                name=node["name"],
                rank=node["rank"],
                parent_ott_id=None,
            ).on_conflict_do_update(
                index_elements=[Taxon.ott_id],
                set_={"name": node["name"], "rank": node["rank"]},
            )
            session.execute(stmt)
            count += 1
            if count % BATCH_SIZE == 0:
                session.commit()
                logger.info("  Pass 1: %d / %d", count, len(nodes))
        session.commit()
        logger.info("Pass 1 complete: %d nodes inserted", count)

        # Pass 2: Update parent references
        logger.info("Pass 2: Setting parent references...")
        updated = 0
        for i, node in enumerate(nodes):
            if node["parent_ott_id"] is not None:
                from sqlalchemy import update
                stmt = update(Taxon).where(Taxon.ott_id == node["ott_id"]).values(
                    parent_ott_id=node["parent_ott_id"]
                )
                session.execute(stmt)
                updated += 1
                if updated % BATCH_SIZE == 0:
                    session.commit()
                    logger.info("  Pass 2: %d parent refs updated", updated)
        session.commit()
        logger.info("Pass 2 complete: %d parent refs set", updated)
    finally:
        session.close()
    return count


async def _resolve_scope(client: OpenTreeClient, scope: str) -> int:
    """Resolve a scope name to an OTT ID via TNRS."""
    logger.info("Resolving '%s' via TNRS...", scope)
    match_resp = await client.tnrs_match(scope)
    matches = match_resp["results"][0]["matches"]
    if not matches:
        raise RuntimeError(f"No OTT match found for '{scope}'")
    ott_id = matches[0]["taxon"]["ott_id"]
    logger.info("Resolved '%s' -> ott_id=%d", scope, ott_id)
    return ott_id


async def _ingest_subtree(client: OpenTreeClient, ott_id: int, scope: str, resume: bool = False) -> int:
    """Fetch and ingest a single subtree by OTT ID. Returns node count."""
    # Check existing taxa if resuming
    existing_ids: set[int] = set()
    if resume:
        session = SessionLocal()
        try:
            from sqlalchemy import select
            rows = session.execute(select(Taxon.ott_id)).scalars().all()
            existing_ids = set(rows)
        finally:
            session.close()

    logger.info("Fetching taxonomy subtree for ott_id=%d...", ott_id)
    try:
        subtree_resp = await client.taxonomy_subtree(ott_id)
    except Exception as e:
        logger.error("Failed to fetch subtree for ott_id=%d: %s", ott_id, e)
        return 0

    newick = subtree_resp["newick"]
    logger.info("Received Newick string (%d chars)", len(newick))

    logger.info("Parsing Newick...")
    nodes = _parse_newick(newick)
    logger.info("Parsed %d nodes", len(nodes))

    if resume and existing_ids:
        before = len(nodes)
        nodes = [n for n in nodes if n["ott_id"] not in existing_ids]
        logger.info("Resume mode: skipped %d existing nodes, %d new", before - len(nodes), len(nodes))
        if not nodes:
            return 0

    _infer_ranks(nodes)
    species_count = sum(1 for n in nodes if n["rank"] == "species")
    logger.info("Identified %d species by name pattern", species_count)

    await _enrich_ranks(client, nodes)

    ott_set = {n["ott_id"] for n in nodes} | existing_ids
    for n in nodes:
        if n["parent_ott_id"] not in ott_set:
            n["parent_ott_id"] = None

    count = _persist_nodes(nodes)
    logger.info("Ingested %d taxa for subtree ott_id=%d", count, ott_id)
    return count


async def ingest(scope: str | None = None, strategy: str = "api", resume: bool = False) -> None:
    """Run the full OTT ingestion pipeline.

    Args:
        scope: Root taxon name (default: from settings).
        strategy: 'api' for single subtree fetch, 'chunked' for per-child fetching.
        resume: Skip OTT IDs already in the database.
    """
    scope = scope or settings.scope_ott_root
    client = OpenTreeClient()
    ott_id = await _resolve_scope(client, scope)

    if strategy == "chunked":
        await ingest_chunked(client, ott_id, scope, resume=resume)
    else:
        await _ingest_subtree(client, ott_id, scope, resume=resume)


async def ingest_chunked(
    client: OpenTreeClient, root_ott_id: int, scope: str, resume: bool = False
) -> None:
    """Chunked ingestion: fetch each child's subtree separately.

    Useful for very large clades (Animalia, Insecta) where the full Newick
    string exceeds API limits or memory constraints.
    """
    # First, insert the root taxon itself
    info = await client.taxon_info(root_ott_id)
    root_node = {
        "ott_id": root_ott_id,
        "name": info.get("unique_name", info.get("name", scope)),
        "rank": info.get("rank", "no rank"),
        "parent_ott_id": None,
    }
    _persist_nodes([root_node])
    logger.info("Inserted root taxon: %s (ott_id=%d)", root_node["name"], root_ott_id)

    # Get direct children
    children = await client.taxon_children(root_ott_id)
    logger.info("Root has %d direct children to ingest", len(children))

    total = 0
    for i, child in enumerate(children):
        child_ott_id = child["ott_id"]
        child_name = child["name"]
        logger.info("[%d/%d] Ingesting subtree: %s (ott_id=%d)", i + 1, len(children), child_name, child_ott_id)

        count = await _ingest_subtree(client, child_ott_id, child_name, resume=resume)
        total += count
        logger.info("[%d/%d] Done: %d nodes from %s (running total: %d)", i + 1, len(children), count, child_name, total)

    logger.info("Chunked ingestion complete for '%s': %d total taxa from %d children", scope, total, len(children))


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest OpenTree taxonomy")
    parser.add_argument(
        "--scope", type=str, default=None,
        help="Root taxon name (default: from SCOPE_OTT_ROOT env or 'Aves')",
    )
    parser.add_argument(
        "--strategy", choices=["api", "chunked"], default="api",
        help="Ingestion strategy: 'api' for single subtree fetch, 'chunked' for per-child fetching (default: api)",
    )
    parser.add_argument(
        "--resume", action="store_true",
        help="Skip OTT IDs already in the database",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    asyncio.run(ingest(scope=args.scope, strategy=args.strategy, resume=args.resume))


if __name__ == "__main__":
    main()
