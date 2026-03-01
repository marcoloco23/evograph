"""Tests for NCBI COI ingestion pipeline search strategy."""

import pytest
from unittest.mock import AsyncMock, MagicMock

import httpx

from evograph.pipeline.ingest_ncbi import (
    _build_query,
    _esearch,
    _efetch_fasta,
    _fetch_coi_sequences,
)


@pytest.fixture
def mock_client():
    return AsyncMock(spec=httpx.AsyncClient)


def _mock_response(json_data=None, text_data=None):
    """Create a mock HTTP response."""
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    if json_data is not None:
        resp.json.return_value = json_data
    if text_data is not None:
        resp.text = text_data
    return resp


class TestBuildQuery:
    """Tests for _build_query function."""

    def test_includes_organism(self):
        q = _build_query("Corvus corax")
        assert '"Corvus corax"[Organism]' in q

    def test_includes_coi_gene_variants(self):
        q = _build_query("Corvus corax")
        assert "COI[Gene]" in q
        assert "COX1[Gene]" in q
        assert "COXI[Gene]" in q
        assert "CO1[Gene]" in q

    def test_includes_title_variants(self):
        q = _build_query("Corvus corax")
        assert '"cytochrome c oxidase subunit I"[Title]' in q
        assert '"cytochrome c oxidase subunit 1"[Title]' in q

    def test_includes_length_filter(self):
        q = _build_query("Corvus corax")
        assert "400:2000[Sequence Length]" in q


class TestEsearch:
    """Tests for _esearch function."""

    @pytest.mark.asyncio
    async def test_returns_id_list(self, mock_client):
        mock_client.get.return_value = _mock_response(
            json_data={"esearchresult": {"idlist": ["123", "456"]}}
        )
        result = await _esearch(mock_client, "test query", 5)
        assert result == ["123", "456"]

    @pytest.mark.asyncio
    async def test_returns_empty_on_no_results(self, mock_client):
        mock_client.get.return_value = _mock_response(
            json_data={"esearchresult": {"idlist": []}}
        )
        result = await _esearch(mock_client, "test query", 5)
        assert result == []

    @pytest.mark.asyncio
    async def test_passes_correct_params(self, mock_client):
        mock_client.get.return_value = _mock_response(
            json_data={"esearchresult": {"idlist": []}}
        )
        await _esearch(mock_client, "test query", 10)

        call_args = mock_client.get.call_args
        params = call_args.kwargs.get("params", call_args[1].get("params", {}))
        assert params["db"] == "nucleotide"
        assert params["term"] == "test query"
        assert params["retmax"] == 10
        assert params["retmode"] == "json"


class TestEfetchFasta:
    """Tests for _efetch_fasta function."""

    @pytest.mark.asyncio
    async def test_parses_single_record(self, mock_client):
        fasta = ">NC_002008.1 Corvus corax\nATCGATCG\nGCTAGCTA\n"
        mock_client.get.return_value = _mock_response(text_data=fasta)

        records = await _efetch_fasta(mock_client, ["123"])
        assert len(records) == 1
        assert records[0]["header"] == "NC_002008.1 Corvus corax"
        assert records[0]["seq"] == "ATCGATCGGCTAGCTA"

    @pytest.mark.asyncio
    async def test_parses_multiple_records(self, mock_client):
        fasta = ">seq1\nATCG\n>seq2\nGCTA\n"
        mock_client.get.return_value = _mock_response(text_data=fasta)

        records = await _efetch_fasta(mock_client, ["1", "2"])
        assert len(records) == 2
        assert records[0]["seq"] == "ATCG"
        assert records[1]["seq"] == "GCTA"

    @pytest.mark.asyncio
    async def test_handles_empty_response(self, mock_client):
        mock_client.get.return_value = _mock_response(text_data="")

        records = await _efetch_fasta(mock_client, ["123"])
        assert records == []


class TestFetchCoiSequences:
    """Tests for _fetch_coi_sequences with tiered search strategy."""

    @pytest.mark.asyncio
    async def test_species_level_search_hits(self, mock_client):
        """When species search finds results, return them directly."""
        mock_client.get.side_effect = [
            # esearch returns results
            _mock_response(json_data={"esearchresult": {"idlist": ["123"]}}),
            # efetch returns FASTA
            _mock_response(text_data=">NC_001.1\nATCG\n"),
        ]

        records = await _fetch_coi_sequences(mock_client, "Corvus corax", 5)
        assert len(records) == 1
        assert records[0]["seq"] == "ATCG"

    @pytest.mark.asyncio
    async def test_genus_fallback_when_species_fails(self, mock_client):
        """When species search returns nothing, fall back to genus."""
        mock_client.get.side_effect = [
            # species esearch: no results
            _mock_response(json_data={"esearchresult": {"idlist": []}}),
            # genus esearch: has results
            _mock_response(json_data={"esearchresult": {"idlist": ["456"]}}),
            # efetch returns FASTA
            _mock_response(text_data=">NC_002.1\nGCTA\n"),
        ]

        records = await _fetch_coi_sequences(
            mock_client, "Corvus corax", 5, genus_fallback=True
        )
        assert len(records) == 1

        # Verify the genus query was made
        calls = mock_client.get.call_args_list
        genus_call_params = calls[1].kwargs.get("params", calls[1][1].get("params", {}))
        assert '"Corvus"[Organism]' in genus_call_params["term"]

    @pytest.mark.asyncio
    async def test_no_genus_fallback_when_disabled(self, mock_client):
        """When genus_fallback=False, don't try genus search."""
        mock_client.get.return_value = _mock_response(
            json_data={"esearchresult": {"idlist": []}}
        )

        records = await _fetch_coi_sequences(
            mock_client, "Corvus corax", 5, genus_fallback=False
        )
        assert records == []
        # Only one call should have been made (species-level)
        assert mock_client.get.call_count == 1

    @pytest.mark.asyncio
    async def test_no_genus_fallback_for_single_word(self, mock_client):
        """Single-word names (genus-level taxa) don't trigger genus fallback."""
        mock_client.get.return_value = _mock_response(
            json_data={"esearchresult": {"idlist": []}}
        )

        records = await _fetch_coi_sequences(
            mock_client, "Corvus", 5, genus_fallback=True
        )
        assert records == []
        # Only one call — no fallback for single-word names
        assert mock_client.get.call_count == 1

    @pytest.mark.asyncio
    async def test_both_searches_fail(self, mock_client):
        """When both species and genus searches fail, return empty."""
        mock_client.get.return_value = _mock_response(
            json_data={"esearchresult": {"idlist": []}}
        )

        records = await _fetch_coi_sequences(
            mock_client, "Fakeus specieus", 5, genus_fallback=True
        )
        assert records == []
