"""OpenTree of Life API client."""

from dataclasses import dataclass

import httpx


@dataclass(frozen=True)
class OpenTreeClient:
    """Async client for the Open Tree of Life v3 API."""

    base_url: str = "https://api.opentreeoflife.org/v3"

    async def tnrs_match(self, name: str) -> dict:
        """Match a taxon name to an OTT ID.

        Posts to /tnrs/match_names and returns the full response dict.
        """
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{self.base_url}/tnrs/match_names",
                json={"names": [name]},
            )
            resp.raise_for_status()
            return resp.json()

    async def taxonomy_subtree(self, ott_id: int) -> dict:
        """Fetch the taxonomy subtree under an OTT ID.

        Returns dict with a 'newick' field containing the Newick string.
        """
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{self.base_url}/taxonomy/subtree",
                json={"ott_id": ott_id, "label_format": "name_and_id"},
            )
            resp.raise_for_status()
            return resp.json()

    async def taxon_info(
        self, ott_id: int, include_children: bool = False
    ) -> dict:
        """Get info about a single taxon."""
        payload: dict = {"ott_id": ott_id}
        if include_children:
            payload["include_children"] = True
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{self.base_url}/taxonomy/taxon_info",
                json=payload,
            )
            resp.raise_for_status()
            return resp.json()

    async def taxon_children(self, ott_id: int) -> list[dict]:
        """Get direct children of a taxon.

        Returns list of child dicts with 'ott_id', 'name', 'rank' keys.
        Uses taxon_info which includes children in the response.
        """
        info = await self.taxon_info(ott_id, include_children=True)
        children = info.get("children", [])
        return [
            {
                "ott_id": c["ott_id"],
                "name": c.get("unique_name", c.get("name", "")),
                "rank": c.get("rank", "no rank"),
            }
            for c in children
        ]
