"""Ingest COI sequences from NCBI GenBank for species in the DB.

Uses NCBI E-utilities (esearch + efetch) as a fallback when BOLD is unavailable.

Search strategy (tiered fallback):
1. Species-level search with broad COI gene name variants
2. Genus-level search if species-level finds nothing

Run as: python -m evograph.pipeline.ingest_ncbi [--limit N] [--per-species N] [--skip-existing]
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import re
import uuid

import httpx
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from evograph.db.models import Sequence, Taxon
from evograph.db.session import SessionLocal
from evograph.settings import settings

logger = logging.getLogger(__name__)

NCBI_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
_NON_ACGTN = re.compile(r"[^ACGTN]")
MIN_SEQ_LEN = 400
MAX_PER_SPECIES = 5

# NCBI rate limit: 3 req/s without API key, 10 req/s with
_RATE_DELAY = 0.1 if settings.ncbi_api_key else 0.4

# Broader COI gene search terms — many GenBank entries use different annotations
_COI_TERMS = (
    'COI[Gene] OR COX1[Gene] OR COXI[Gene] OR CO1[Gene] '
    'OR "cytochrome oxidase subunit I"[Title] '
    'OR "cytochrome oxidase subunit 1"[Title] '
    'OR "cytochrome c oxidase subunit I"[Title] '
    'OR "cytochrome c oxidase subunit 1"[Title] '
    'OR "COI"[Title]'
)


def _build_query(organism: str) -> str:
    """Build NCBI esearch query for COI sequences of a given organism."""
    return (
        f'"{organism}"[Organism] AND ({_COI_TERMS}) '
        f'AND 400:2000[Sequence Length]'
    )


async def _esearch(
    client: httpx.AsyncClient, query: str, max_seqs: int
) -> list[str]:
    """Run NCBI esearch and return list of GI/accession IDs."""
    params: dict[str, str | int] = {
        "db": "nucleotide",
        "term": query,
        "retmax": max_seqs,
        "retmode": "json",
    }
    if settings.ncbi_api_key:
        params["api_key"] = settings.ncbi_api_key
    resp = await client.get(f"{NCBI_BASE}/esearch.fcgi", params=params)
    resp.raise_for_status()
    data = resp.json()
    return data.get("esearchresult", {}).get("idlist", [])


async def _efetch_fasta(
    client: httpx.AsyncClient, id_list: list[str]
) -> list[dict]:
    """Fetch sequences in FASTA format and parse them."""
    params: dict[str, str] = {
        "db": "nucleotide",
        "id": ",".join(id_list),
        "rettype": "fasta",
        "retmode": "text",
    }
    if settings.ncbi_api_key:
        params["api_key"] = settings.ncbi_api_key
    resp = await client.get(f"{NCBI_BASE}/efetch.fcgi", params=params)
    resp.raise_for_status()

    records = []
    current_header = None
    current_seq_parts: list[str] = []

    for line in resp.text.split("\n"):
        line = line.strip()
        if line.startswith(">"):
            if current_header and current_seq_parts:
                records.append({"header": current_header, "seq": "".join(current_seq_parts)})
            current_header = line[1:]
            current_seq_parts = []
        elif line:
            current_seq_parts.append(line)

    if current_header and current_seq_parts:
        records.append({"header": current_header, "seq": "".join(current_seq_parts)})

    return records


async def _fetch_coi_sequences(
    client: httpx.AsyncClient,
    species_name: str,
    max_seqs: int = MAX_PER_SPECIES,
    genus_fallback: bool = True,
) -> list[dict]:
    """Fetch COI sequences with tiered search strategy.

    1. Search by exact species name
    2. If no results and genus_fallback=True, search by genus name
    """
    # Tier 1: species-level search
    query = _build_query(species_name)
    id_list = await _esearch(client, query, max_seqs)

    # Tier 2: genus-level fallback
    if not id_list and genus_fallback:
        parts = species_name.split()
        if len(parts) >= 2:
            genus = parts[0]
            # NCBI rate limit pause before second request
            await asyncio.sleep(_RATE_DELAY)
            query = _build_query(genus)
            id_list = await _esearch(client, query, max_seqs)
            if id_list:
                logger.debug(
                    "  Genus fallback for %s → found %d via genus %s",
                    species_name, len(id_list), genus,
                )

    if not id_list:
        return []

    # NCBI rate limit pause before fetch
    await asyncio.sleep(_RATE_DELAY)
    return await _efetch_fasta(client, id_list)


async def ingest(
    limit: int | None = None,
    per_species: int = MAX_PER_SPECIES,
    skip_existing: bool = False,
    genus_fallback: bool = True,
) -> None:
    """Run the NCBI COI ingestion pipeline."""
    session = SessionLocal()

    try:
        stmt = select(Taxon).where(Taxon.rank == "species")

        if skip_existing:
            # Subquery: species that already have sequences
            has_seqs = (
                select(Sequence.ott_id)
                .where(Sequence.source == "NCBI", Sequence.marker == "COI")
                .distinct()
                .subquery()
            )
            stmt = stmt.where(Taxon.ott_id.notin_(select(has_seqs.c.ott_id)))

        if limit is not None:
            stmt = stmt.limit(limit)

        taxa = session.execute(stmt).scalars().all()
        logger.info("Found %d species-rank taxa to process", len(taxa))

        total_stored = 0
        species_with_seqs = 0

        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            for i, taxon in enumerate(taxa):
                try:
                    if (i + 1) % 50 == 0 or i == 0:
                        logger.info(
                            "[%d/%d] Fetching NCBI sequences for %s (ott_id=%d) "
                            "[stored=%d, species_covered=%d]",
                            i + 1, len(taxa), taxon.name, taxon.ott_id,
                            total_stored, species_with_seqs,
                        )

                    records = await _fetch_coi_sequences(
                        client, taxon.name, per_species, genus_fallback
                    )

                    count = 0
                    for rec in records:
                        raw_seq = rec["seq"].upper()
                        seq = _NON_ACGTN.sub("", raw_seq)
                        if len(seq) < MIN_SEQ_LEN:
                            continue

                        # Extract accession from header (first word)
                        header = rec["header"]
                        accession = header.split()[0] if header else str(uuid.uuid4())
                        ambig = seq.count("N")

                        stmt_ins = pg_insert(Sequence).values(
                            id=uuid.uuid4(),
                            ott_id=taxon.ott_id,
                            marker="COI",
                            source="NCBI",
                            accession=accession,
                            sequence=seq,
                            length=len(seq),
                            quality={"ambig": ambig},
                            is_canonical=False,
                        ).on_conflict_do_nothing()
                        session.execute(stmt_ins)
                        count += 1

                    session.commit()
                    total_stored += count
                    if count > 0:
                        species_with_seqs += 1

                except Exception:
                    session.rollback()
                    logger.exception(
                        "  Error processing %s (ott_id=%d)", taxon.name, taxon.ott_id
                    )

                # NCBI rate limit: max 3 requests/second without API key
                await asyncio.sleep(_RATE_DELAY)

            logger.info(
                "NCBI ingestion complete. Sequences stored: %d, species covered: %d/%d",
                total_stored, species_with_seqs, len(taxa),
            )

    finally:
        session.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest NCBI COI sequences")
    parser.add_argument(
        "--limit", type=int, default=None,
        help="Max number of taxa to process",
    )
    parser.add_argument(
        "--per-species", type=int, default=MAX_PER_SPECIES,
        help="Max sequences per species (default: 5)",
    )
    parser.add_argument(
        "--skip-existing", action="store_true",
        help="Skip species that already have NCBI COI sequences",
    )
    parser.add_argument(
        "--no-genus-fallback", action="store_true",
        help="Disable genus-level fallback when species search fails",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    asyncio.run(ingest(
        limit=args.limit,
        per_species=args.per_species,
        skip_existing=args.skip_existing,
        genus_fallback=not args.no_genus_fallback,
    ))


if __name__ == "__main__":
    main()
