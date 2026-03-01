"""Tests for the NCBI taxonomy ID backfill pipeline."""

import pytest
from unittest.mock import AsyncMock, MagicMock
import httpx

from evograph.pipeline.backfill_ncbi_tax_id import _lookup_tax_id


@pytest.fixture
def mock_client():
    return AsyncMock(spec=httpx.AsyncClient)


class TestLookupTaxId:
    """Tests for _lookup_tax_id function."""

    @pytest.mark.asyncio
    async def test_single_match_returns_id(self, mock_client):
        """When NCBI returns exactly one match, return the ID."""
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "esearchresult": {"idlist": ["9606"]}
        }
        mock_resp.raise_for_status = MagicMock()
        mock_client.get.return_value = mock_resp

        result = await _lookup_tax_id(mock_client, "Homo sapiens")
        assert result == 9606

    @pytest.mark.asyncio
    async def test_no_match_returns_none(self, mock_client):
        """When NCBI returns no matches, return None."""
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "esearchresult": {"idlist": []}
        }
        mock_resp.raise_for_status = MagicMock()
        mock_client.get.return_value = mock_resp

        result = await _lookup_tax_id(mock_client, "Fakeus speciesus")
        assert result is None

    @pytest.mark.asyncio
    async def test_multiple_matches_returns_none(self, mock_client):
        """When NCBI returns multiple matches, return None (ambiguous)."""
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "esearchresult": {"idlist": ["9606", "9607"]}
        }
        mock_resp.raise_for_status = MagicMock()
        mock_client.get.return_value = mock_resp

        result = await _lookup_tax_id(mock_client, "Homo")
        assert result is None

    @pytest.mark.asyncio
    async def test_uses_scientific_name_field(self, mock_client):
        """Verify the query uses [Scientific Name] field qualifier."""
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "esearchresult": {"idlist": ["9606"]}
        }
        mock_resp.raise_for_status = MagicMock()
        mock_client.get.return_value = mock_resp

        await _lookup_tax_id(mock_client, "Corvus corax")

        call_args = mock_client.get.call_args
        params = call_args.kwargs.get("params", call_args[1].get("params", {}))
        assert params["db"] == "taxonomy"
        assert '"Corvus corax"[Scientific Name]' in params["term"]

    @pytest.mark.asyncio
    async def test_http_error_propagates(self, mock_client):
        """HTTP errors should propagate to caller."""
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "500", request=MagicMock(), response=MagicMock()
        )
        mock_client.get.return_value = mock_resp

        with pytest.raises(httpx.HTTPStatusError):
            await _lookup_tax_id(mock_client, "test")

    @pytest.mark.asyncio
    async def test_returns_int(self, mock_client):
        """Return value should be int, not string."""
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "esearchresult": {"idlist": ["12345"]}
        }
        mock_resp.raise_for_status = MagicMock()
        mock_client.get.return_value = mock_resp

        result = await _lookup_tax_id(mock_client, "test")
        assert isinstance(result, int)
        assert result == 12345
