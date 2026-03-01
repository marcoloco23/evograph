"""Shared test fixtures for EvoGraph API tests."""

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from evograph.db.models import Edge, NodeMedia, Sequence, Taxon
from evograph.db.session import get_db
from evograph.main import app


def _make_taxon(ott_id: int, name: str, rank: str, parent_ott_id: int | None = None, **kw) -> Taxon:
    t = MagicMock(spec=Taxon)
    t.ott_id = ott_id
    t.name = name
    t.rank = rank
    t.parent_ott_id = parent_ott_id
    t.ncbi_tax_id = kw.get("ncbi_tax_id")
    t.bold_tax_id = kw.get("bold_tax_id")
    t.synonyms = kw.get("synonyms")
    t.lineage = kw.get("lineage")
    return t


def _make_sequence(ott_id: int, **kw) -> Sequence:
    s = MagicMock(spec=Sequence)
    s.id = kw.get("id", uuid.uuid4())
    s.ott_id = ott_id
    s.marker = kw.get("marker", "COI")
    s.source = kw.get("source", "NCBI")
    s.accession = kw.get("accession", "NC_000001")
    s.sequence = kw.get("sequence", "ATCGATCG")
    s.length = kw.get("length", 658)
    s.quality = kw.get("quality")
    s.is_canonical = kw.get("is_canonical", False)
    s.retrieved_at = kw.get("retrieved_at", datetime(2024, 1, 1, tzinfo=timezone.utc))
    return s


def _make_edge(src: int, dst: int, **kw) -> Edge:
    e = MagicMock(spec=Edge)
    e.src_ott_id = src
    e.dst_ott_id = dst
    e.marker = kw.get("marker", "COI")
    e.distance = kw.get("distance", 0.15)
    e.mi_norm = kw.get("mi_norm", 0.85)
    e.align_len = kw.get("align_len", 600)
    e.created_at = kw.get("created_at", datetime(2024, 1, 1, tzinfo=timezone.utc))
    return e


def _make_media(ott_id: int, image_url: str) -> NodeMedia:
    m = MagicMock(spec=NodeMedia)
    m.ott_id = ott_id
    m.image_url = image_url
    m.attribution = None
    return m


# ── Sample data ─────────────────────────────────────────
AVES = _make_taxon(81461, "Aves", "class")
PASSERIFORMES = _make_taxon(1041547, "Passeriformes", "order", parent_ott_id=81461)
CORVIDAE = _make_taxon(187411, "Corvidae", "family", parent_ott_id=1041547)
CORVUS = _make_taxon(369568, "Corvus", "genus", parent_ott_id=187411)
CORVUS_CORAX = _make_taxon(700118, "Corvus corax", "species", parent_ott_id=369568)
CORVUS_CORONE = _make_taxon(893498, "Corvus corone", "species", parent_ott_id=369568)


@pytest.fixture()
def sample_taxa():
    return {
        "aves": AVES,
        "passeriformes": PASSERIFORMES,
        "corvidae": CORVIDAE,
        "corvus": CORVUS,
        "corvus_corax": CORVUS_CORAX,
        "corvus_corone": CORVUS_CORONE,
    }


class MockExistsClause:
    """Wraps a boolean for EXISTS subquery simulation."""
    pass


class MockQuery:
    """Chainable mock for SQLAlchemy query calls."""

    def __init__(self, results=None):
        self._results = results or []

    def filter(self, *args, **kwargs):
        return self

    def order_by(self, *args, **kwargs):
        return self

    def limit(self, *args, **kwargs):
        return self

    def offset(self, *args, **kwargs):
        return self

    def join(self, *args, **kwargs):
        return self

    def group_by(self, *args, **kwargs):
        return self

    def select_from(self, *args, **kwargs):
        return self

    def exists(self):
        """Return an exists clause marker for use in outer query."""
        return MockExistsClause()

    def scalar(self):
        # When called on an EXISTS wrapper query, return False
        if self._results and isinstance(self._results[0], MockExistsClause):
            return False
        return 0

    def count(self):
        return len(self._results)

    def all(self):
        return self._results

    def first(self):
        return self._results[0] if self._results else None

    def one(self):
        return self._results[0] if self._results else (None,)


class MockExecuteResult:
    """Mock result for db.execute() calls (used by recursive CTEs)."""

    def __init__(self, rows=None):
        self._rows = rows or []

    def fetchall(self):
        return self._rows

    def scalars(self):
        return self

    def all(self):
        return [row[0] if isinstance(row, tuple) else row for row in self._rows]


class MockDB:
    """Mock database session that dispatches query() by model type."""

    def __init__(self):
        self._registry: dict[type | tuple, list] = {}

    def set(self, key, results):
        """Register results for a given model or model-tuple."""
        self._registry[key] = results
        return self

    def query(self, *models):
        # For EXISTS wrapper: db.query(exists_clause)
        if len(models) == 1 and isinstance(models[0], MockExistsClause):
            return MockQuery([models[0]])
        # For multi-model queries like (Edge, Taxon), use a tuple key
        key = models[0] if len(models) == 1 else models
        results = self._registry.get(key, [])
        return MockQuery(results)

    def execute(self, *args, **kwargs):
        """Handle raw SQL execute calls (recursive CTEs). Returns empty results."""
        return MockExecuteResult([])


@pytest.fixture()
def mock_db():
    return MockDB()


@pytest.fixture()
def client(mock_db):
    """FastAPI TestClient with the get_db dependency overridden."""

    def _override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
