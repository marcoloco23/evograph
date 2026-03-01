from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from evograph.api.routes import graph, search, sequences, taxa

app = FastAPI(title="EvoGraph MVP", version="0.1.0")

# GZip responses > 500 bytes — critical for graph endpoints with large JSON payloads
app.add_middleware(GZipMiddleware, minimum_size=500)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(search.router, prefix="/v1")
app.include_router(taxa.router, prefix="/v1")
app.include_router(graph.router, prefix="/v1")
app.include_router(sequences.router, prefix="/v1")


@app.get("/health")
def health():
    return {"status": "ok"}
