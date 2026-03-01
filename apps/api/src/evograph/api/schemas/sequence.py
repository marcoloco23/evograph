from datetime import datetime

from pydantic import BaseModel


class SequenceOut(BaseModel):
    id: str
    ott_id: int
    marker: str
    source: str
    accession: str
    sequence: str
    length: int
    is_canonical: bool
    retrieved_at: datetime | None = None


class SequencePage(BaseModel):
    items: list[SequenceOut]
    total: int
    offset: int
    limit: int
