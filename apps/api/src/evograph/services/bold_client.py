"""BOLD Systems portal API client (new v5 API)."""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass

import httpx

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class BoldClient:
    """Async client for the BOLD portal API."""

    base_url: str = "https://portal.boldsystems.org/api"

    async def fetch_sequences(self, taxon: str, marker: str = "COI-5P") -> list[dict]:
        """Fetch COI sequences for a taxon from BOLD.

        Uses the new portal API:
        1. GET /query to create a query token
        2. GET /documents/{query_id}/download to fetch JSONL data

        Returns a list of parsed record dicts.
        Retries up to 3 times with exponential backoff.
        """
        last_exc: Exception | None = None

        for attempt in range(3):
            try:
                async with httpx.AsyncClient(timeout=120, follow_redirects=True) as client:
                    # Step 1: Create query
                    query_str = f"tax:species:{taxon}"
                    resp = await client.get(
                        f"{self.base_url}/query",
                        params={"query": query_str, "extent": "full"},
                    )
                    resp.raise_for_status()
                    query_data = resp.json()
                    query_id = query_data["query_id"]

                    # Step 2: Download data as JSONL
                    resp2 = await client.get(
                        f"{self.base_url}/documents/{query_id}/download",
                        params={"format": "tsv-bcdm"},
                    )
                    resp2.raise_for_status()

                    # Parse JSONL (each line is a JSON object)
                    records = []
                    for line in resp2.text.strip().split("\n"):
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            rec = json.loads(line)
                            # Only keep records with the right marker and a sequence
                            if rec.get("marker_code") == marker and rec.get("nuc"):
                                records.append(rec)
                        except json.JSONDecodeError:
                            continue

                    return records

            except (httpx.HTTPStatusError, httpx.TransportError) as exc:
                last_exc = exc
                logger.warning(
                    "BOLD request failed (attempt %d/3): %s", attempt + 1, exc
                )
                if attempt < 2:
                    await asyncio.sleep(2 ** (attempt + 1))

        raise last_exc  # type: ignore[misc]
