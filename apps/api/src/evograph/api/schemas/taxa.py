from pydantic import BaseModel


class TaxonSummary(BaseModel):
    ott_id: int
    name: str
    rank: str
    child_count: int = 0
    image_url: str | None = None


class TaxonDetail(BaseModel):
    ott_id: int
    name: str
    rank: str
    parent_ott_id: int | None = None
    parent_name: str | None = None
    ncbi_tax_id: int | None = None
    children: list[TaxonSummary] = []
    total_children: int = 0
    has_canonical_sequence: bool = False
    image_url: str | None = None
    lineage: list[TaxonSummary] = []
    wikipedia_url: str | None = None


class ChildrenPage(BaseModel):
    items: list[TaxonSummary]
    total: int
    offset: int
    limit: int


class SearchPage(BaseModel):
    items: list[TaxonSummary]
    total: int
    limit: int
