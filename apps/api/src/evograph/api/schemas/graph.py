from pydantic import BaseModel

class Node(BaseModel):
    ott_id: int
    name: str
    rank: str
    image_url: str | None = None

class GraphEdge(BaseModel):
    src: int
    dst: int
    kind: str  # "taxonomy" | "mi"
    distance: float | None = None

class GraphResponse(BaseModel):
    nodes: list[Node]
    edges: list[GraphEdge]

class NeighborOut(BaseModel):
    ott_id: int
    name: str
    rank: str
    distance: float
    mi_norm: float
