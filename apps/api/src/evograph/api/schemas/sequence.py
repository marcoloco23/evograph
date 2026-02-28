from pydantic import BaseModel
from datetime import datetime

class SequenceOut(BaseModel):
    id: str
    ott_id: int
    marker: str
    source: str
    accession: str
    length: int
    is_canonical: bool
    retrieved_at: datetime | None = None
