from pydantic import BaseModel

class TaxonSummary(BaseModel):
    ott_id: int
    name: str
    rank: str

class TaxonDetail(BaseModel):
    ott_id: int
    name: str
    rank: str
    parent_ott_id: int | None = None
    parent_name: str | None = None
    ncbi_tax_id: int | None = None
    children: list[TaxonSummary] = []
    has_canonical_sequence: bool = False
    image_url: str | None = None
