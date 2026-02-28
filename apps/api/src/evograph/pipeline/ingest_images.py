"""Fetch thumbnail images from Wikimedia Commons for canonical species.

Uses the Wikipedia REST API (no auth required):
  GET https://en.wikipedia.org/api/rest_v1/page/summary/{species_name}

Stores results in the node_media table.

Usage:
  conda run -n evograph python -m evograph.pipeline.ingest_images
"""

import logging
import time

import httpx
from sqlalchemy import select, text

from evograph.db.models import NodeMedia, Taxon
from evograph.db.session import engine

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger(__name__)

WIKI_API = "https://en.wikipedia.org/api/rest_v1/page/summary"
RATE_LIMIT_DELAY = 0.1  # seconds between requests


def fetch_thumbnail(species_name: str) -> tuple[str | None, dict | None]:
    """Fetch thumbnail URL and attribution from Wikipedia REST API."""
    slug = species_name.replace(" ", "_")
    url = f"{WIKI_API}/{slug}"
    try:
        resp = httpx.get(url, timeout=10, follow_redirects=True, headers={
            "User-Agent": "EvoGraph/1.0 (educational project; mailto:evograph@example.com)",
        })
        if resp.status_code == 404:
            return None, None
        resp.raise_for_status()
        data = resp.json()
        thumb = data.get("thumbnail", {})
        image_url = thumb.get("source")
        if not image_url:
            return None, None
        attribution = {
            "title": data.get("title"),
            "description": data.get("description"),
            "content_urls": data.get("content_urls", {}).get("desktop", {}).get("page"),
        }
        return image_url, attribution
    except httpx.HTTPError as e:
        log.warning("Failed to fetch %s: %s", species_name, e)
        return None, None


def run() -> None:
    """Fetch images for all canonical species and genera."""
    from sqlalchemy.orm import Session

    with Session(engine) as db:
        # Get existing media ott_ids to skip
        existing = set(
            row[0] for row in db.execute(select(NodeMedia.ott_id)).all()
        )
        log.info("Already have %d images in node_media", len(existing))

        # Get species with canonical sequences first (most important)
        canonical_species = db.execute(
            text("""
                SELECT DISTINCT t.ott_id, t.name
                FROM taxa t
                JOIN sequences s ON s.ott_id = t.ott_id AND s.is_canonical = true
                WHERE t.rank IN ('species', 'subspecies')
                ORDER BY t.name
            """)
        ).all()

        # Also get genera and families for broader coverage
        higher_taxa = db.execute(
            text("""
                SELECT t.ott_id, t.name
                FROM taxa t
                WHERE t.rank IN ('genus', 'family', 'order')
                ORDER BY t.rank, t.name
            """)
        ).all()

        targets = [(ott_id, name) for ott_id, name in canonical_species if ott_id not in existing]
        higher_targets = [(ott_id, name) for ott_id, name in higher_taxa if ott_id not in existing]

        log.info(
            "Fetching images: %d canonical species, %d higher taxa to process",
            len(targets), len(higher_targets),
        )

        fetched = 0
        skipped = 0

        for ott_id, name in targets + higher_targets:
            image_url, attribution = fetch_thumbnail(name)
            if image_url:
                db.merge(NodeMedia(
                    ott_id=ott_id,
                    image_url=image_url,
                    attribution=attribution,
                ))
                fetched += 1
                if fetched % 25 == 0:
                    db.commit()
                    log.info("  ... fetched %d images so far", fetched)
            else:
                skipped += 1

            time.sleep(RATE_LIMIT_DELAY)

        db.commit()
        log.info("Done: %d images fetched, %d species had no image", fetched, skipped)


if __name__ == "__main__":
    run()
