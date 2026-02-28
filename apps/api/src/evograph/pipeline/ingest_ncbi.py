"""Ingest COI sequences from NCBI GenBank for species in the DB.

Uses NCBI E-utilities (esearch + efetch) as a fallback when BOLD is unavailable.

Run as: python -m evograph.pipeline.ingest_ncbi [--limit N] [--per-species N]
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

logger = logging.getLogger(__name__)

NCBI_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
_NON_ACGTN = re.compile(r"[^ACGTN]")
MIN_SEQ_LEN = 400
MAX_PER_SPECIES = 5


async def _fetch_coi_sequences(
    client: httpx.AsyncClient, species_name: str, max_seqs: int = MAX_PER_SPECIES
) -> list[dict]:
    """Fetch COI sequences for a species from NCBI GenBank."""
    # Search for COI/COX1 sequences
    query = f'"{species_name}"[Organism] AND (COI[Gene] OR COX1[Gene] OR "cytochrome oxidase subunit I"[Title]) AND 400:2000[Sequence Length]'
    search_resp = await client.get(
        f"{NCBI_BASE}/esearch.fcgi",
        params={
            "db": "nucleotide",
            "term": query,
            "retmax": max_seqs,
            "retmode": "json",
        },
    )
    search_resp.raise_for_status()
    search_data = search_resp.json()
    id_list = search_data.get("esearchresult", {}).get("idlist", [])

    if not id_list:
        return []

    # Fetch sequences in FASTA format
    fetch_resp = await client.get(
        f"{NCBI_BASE}/efetch.fcgi",
        params={
            "db": "nucleotide",
            "id": ",".join(id_list),
            "rettype": "fasta",
            "retmode": "text",
        },
    )
    fetch_resp.raise_for_status()

    # Parse FASTA
    records = []
    current_header = None
    current_seq_parts: list[str] = []

    for line in fetch_resp.text.split("\n"):
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


async def ingest(limit: int | None = None, per_species: int = MAX_PER_SPECIES) -> None:
    """Run the NCBI COI ingestion pipeline."""
    session = SessionLocal()

    try:
        stmt = select(Taxon).where(Taxon.rank == "species")
        if limit is not None:
            stmt = stmt.limit(limit)
        taxa = session.execute(stmt).scalars().all()
        logger.info("Found %d species-rank taxa to process", len(taxa))

        total_stored = 0
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            for i, taxon in enumerate(taxa):
                try:
                    if (i + 1) % 50 == 0 or i == 0:
                        logger.info(
                            "[%d/%d] Fetching NCBI sequences for %s (ott_id=%d)",
                            i + 1, len(taxa), taxon.name, taxon.ott_id,
                        )

                    records = await _fetch_coi_sequences(client, taxon.name, per_species)

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

                except Exception:
                    session.rollback()
                    logger.exception(
                        "  Error processing %s (ott_id=%d)", taxon.name, taxon.ott_id
                    )

                # NCBI rate limit: max 3 requests/second without API key
                await asyncio.sleep(0.4)

            logger.info("NCBI ingestion complete. Total sequences stored: %d", total_stored)

    finally:
        session.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest NCBI COI sequences")
    parser.add_argument("--limit", type=int, default=None, help="Max number of taxa to process")
    parser.add_argument("--per-species", type=int, default=MAX_PER_SPECIES, help="Max sequences per species")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    asyncio.run(ingest(limit=args.limit, per_species=args.per_species))


if __name__ == "__main__":
    main()
