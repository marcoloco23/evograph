Below is a full “hand this to a coding agent” MVP implementation plan. It’s opinionated, scoped, and buildable without burning a year of compute.

MVP goal: Browse a slice of Animalia (pick a clade) as a tree + an MI-similarity overlay graph computed from a single comparable marker (COI barcodes). Users can search taxa, click nodes, see metadata, and see nearest neighbors by MI-derived distance.

⸻

0) MVP scope (hard constraints)

Choose one scope slice (pick one, don’t be a hero)
	•	Birds (Aves) (nice imagery, manageable)
	•	Mammals (Mammalia) (smaller than insects)
	•	Chordata (bigger)
	•	Namibia fauna (if you want locality, but sourcing gets trickier)

For the agent: implement as SCOPE_OTT_ROOT = "Aves" or an OTT id.

Marker choice
	•	COI (Cytochrome c oxidase I) barcodes only.

What we compute
	•	For each taxon (species ideally), store one canonical COI sequence (longest/highest quality).
	•	Build a k-nearest-neighbor graph where edge weight = MI-derived distance from pairwise alignment.

What we do NOT do in MVP
	•	Whole genomes
	•	Multi-locus phylogeny inference
	•	Full “all animals”
	•	Perfect taxonomy reconciliation across every source

⸻

1) Tech stack (practical + agent-friendly)

Backend
	•	Python 3.12
	•	FastAPI
	•	Postgres (metadata, taxa, sequences)
	•	Redis (optional caching)
	•	Object storage (S3-compatible or local) for raw FASTA/JSON payloads

Compute jobs
	•	Python workers with a job queue:
	•	simplest: RQ (Redis Queue) or Celery
	•	even simpler: “one-shot CLI pipeline scripts” + cron for MVP

Frontend
	•	Next.js (TypeScript)
	•	Graph viewer: sigma.js (WebGL) or cytoscape.js (easier)

DevOps
	•	Docker compose for local
	•	Makefile commands for pipeline steps

⸻

2) Repository structure

evo-graph-mvp/
  README.md
  docker-compose.yml
  .env.example
  Makefile

  apps/
    api/                       # FastAPI
      pyproject.toml
      src/
        evograph/
          __init__.py
          main.py              # FastAPI entry
          settings.py
          db/
            session.py
            models.py
            migrations/        # alembic
          api/
            routes/
              taxa.py
              sequences.py
              graph.py
              search.py
            schemas/
              taxa.py
              sequence.py
              graph.py
          services/
            ott_client.py      # OpenTree client
            bold_client.py     # BOLD client
            ncbi_client.py     # Optional
            mi_distance.py     # MI computation
            neighbor_index.py  # candidate selection
          pipeline/
            ingest_ott.py
            ingest_bold.py
            select_canonical.py
            build_neighbors.py
            build_graph_export.py
          utils/
            fasta.py
            alignment.py
            logging.py

    web/                       # Next.js
      package.json
      next.config.js
      src/
        app/
          page.tsx
          taxa/[ottId]/page.tsx
          graph/page.tsx
        components/
          GraphView.tsx
          TaxonCard.tsx
          SearchBox.tsx
        lib/
          api.ts
          types.ts

  data/
    raw/
      ott/
      bold/
    processed/
      sequences/
      alignments/
      graph/


⸻

3) Data model (Postgres)

Tables (minimal)
	•	taxa
	•	ott_id (PK, int)
	•	name (text)
	•	rank (text)
	•	parent_ott_id (int, nullable, indexed)
	•	lineage (int[] or text) optional
	•	ncbi_tax_id (int, nullable)
	•	bold_tax_id (text, nullable)
	•	synonyms (jsonb)
	•	sequences
	•	id (uuid PK)
	•	ott_id (int, indexed)
	•	marker (text) = “COI”
	•	source (text) = “BOLD” | “NCBI”
	•	accession (text)
	•	sequence (text) (store uppercase A/C/G/T/N)
	•	length (int)
	•	quality (jsonb) (optional)
	•	is_canonical (bool)
	•	retrieved_at (timestamp)
	•	edges
	•	src_ott_id (int, indexed)
	•	dst_ott_id (int, indexed)
	•	marker (text)
	•	distance (double precision)
	•	mi_norm (double precision)
	•	align_len (int)
	•	created_at (timestamp)
	•	PK (src_ott_id, dst_ott_id, marker)
	•	node_media (optional)
	•	ott_id
	•	image_url
	•	attribution (jsonb)

⸻

4) Pipeline overview (end-to-end)

Step A — Ingest OpenTree taxonomy slice
	•	Pull subtree under SCOPE_OTT_ROOT (ott id or name resolved via OpenTree)
	•	Store nodes in taxa with parent links

Step B — Ingest COI sequences
	•	Query BOLD API for COI records matching taxa names (imperfect → use heuristics)
	•	Store raw response in data/raw/bold/
	•	Normalize sequences into sequences table

Step C — Pick canonical per taxon

Rules:
	•	prefer BOLD records with:
	•	longer length
	•	fewer ambiguous bases (“N”)
	•	optional: fewer gaps if pre-aligned
	•	set is_canonical = true for chosen record

Step D — Candidate neighbors (avoid O(n²))

For each taxon:
	•	candidates = taxa within same genus/family OR top-k by k-mer sketch similarity
	•	MVP simplest: candidates within same family (using taxonomy ranks)

Step E — Compute MI-distance for candidates
	•	Pairwise global alignment (Needleman–Wunsch)
	•	Convert alignment into MI-derived similarity
	•	Convert to distance
	•	Keep smallest k distances per node (kNN)

Step F — Export graph for frontend
	•	Build JSON files:
	•	nodes.json (ott_id, name, rank, image_url)
	•	edges.json (src, dst, distance)
	•	API can also serve dynamically, but pre-export helps.

⸻

5) Key implementation details + code examples

5.1 FastAPI entry

# apps/api/src/evograph/main.py
from fastapi import FastAPI
from evograph.api.routes import taxa, graph, search

app = FastAPI(title="EvoGraph MVP")

app.include_router(search.router, prefix="/v1")
app.include_router(taxa.router, prefix="/v1")
app.include_router(graph.router, prefix="/v1")


⸻

5.2 OpenTree ingestion (taxonomy backbone)

Use OpenTree APIs to resolve a name to OTT id and fetch a subtree.
(Agent can implement a minimal HTTP client with httpx.)

# apps/api/src/evograph/services/ott_client.py
from dataclasses import dataclass
import httpx

@dataclass(frozen=True)
class OpenTreeClient:
    base_url: str = "https://api.opentreeoflife.org/v3"

    async def tnrs_match(self, name: str) -> dict:
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.post(f"{self.base_url}/tnrs/match_names", json={"names":[name]})
            r.raise_for_status()
            return r.json()

    async def taxonomy_subtree(self, ott_id: int) -> dict:
        async with httpx.AsyncClient(timeout=60) as c:
            r = await c.post(f"{self.base_url}/taxonomy/subtree", json={"ott_id": ott_id})
            r.raise_for_status()
            return r.json()

Then persist to DB:

# apps/api/src/evograph/pipeline/ingest_ott.py
import asyncio
from evograph.services.ott_client import OpenTreeClient
from evograph.db.session import SessionLocal
from evograph.db.models import Taxon

async def run(scope_name: str) -> None:
    ott = OpenTreeClient()
    m = await ott.tnrs_match(scope_name)
    ott_id = m["results"][0]["matches"][0]["taxon"]["ott_id"]

    subtree = await ott.taxonomy_subtree(ott_id)
    # subtree format: depends; agent should implement parser that yields nodes with parent

    db = SessionLocal()
    try:
        for node in parse_subtree(subtree):  # yields {ott_id, name, rank, parent_ott_id}
            db.merge(Taxon(**node))
        db.commit()
    finally:
        db.close()

def parse_subtree(subtree_json: dict):
    # TODO: agent implements robust traversal based on OpenTree response shape
    yield from []

if __name__ == "__main__":
    asyncio.run(run("Aves"))

MVP note: OpenTree “subtree” response is often Newick-ish or structured; agent should adapt after inspecting real response.

⸻

5.3 BOLD ingestion (COI sequences)

BOLD has an API; for MVP you can query by taxon name and marker.
Store raw response for provenance.

# apps/api/src/evograph/services/bold_client.py
import httpx
from dataclasses import dataclass

@dataclass(frozen=True)
class BoldClient:
    base_url: str = "https://www.boldsystems.org/index.php/API_Public"

    async def fetch_sequences(self, taxon: str, marker: str = "COI-5P") -> str:
        # Many BOLD endpoints return TSV/FASTA; agent should pick a stable endpoint.
        params = {"taxon": taxon, "marker": marker, "format": "tsv"}  # example
        async with httpx.AsyncClient(timeout=60) as c:
            r = await c.get(f"{self.base_url}/sequence", params=params)
            r.raise_for_status()
            return r.text

Parsing TSV into normalized sequences:

# apps/api/src/evograph/pipeline/ingest_bold.py
import asyncio, pathlib, re
from evograph.services.bold_client import BoldClient
from evograph.db.session import SessionLocal
from evograph.db.models import Sequence, Taxon

def clean_seq(s: str) -> str:
    s = re.sub(r"[^ACGTN]", "", s.upper())
    return s

async def run(limit_taxa: int = 2000) -> None:
    db = SessionLocal()
    bold = BoldClient()

    taxa = db.query(Taxon).filter(Taxon.rank.in_(["species"])).limit(limit_taxa).all()
    out_dir = pathlib.Path("data/raw/bold")
    out_dir.mkdir(parents=True, exist_ok=True)

    for t in taxa:
        try:
            raw = await bold.fetch_sequences(t.name)
        except Exception:
            continue

        (out_dir / f"{t.ott_id}.tsv").write_text(raw, encoding="utf-8")

        for rec in parse_bold_tsv(raw):
            seq = clean_seq(rec["nuc"])
            if len(seq) < 400:
                continue
            db.add(Sequence(
                ott_id=t.ott_id,
                marker="COI",
                source="BOLD",
                accession=rec.get("processid") or rec.get("sampleid") or "",
                sequence=seq,
                length=len(seq),
                quality={"ambig": seq.count("N")},
                is_canonical=False,
            ))
        db.commit()

    db.close()

def parse_bold_tsv(raw: str) -> list[dict]:
    # Agent: implement robust TSV parsing; columns vary.
    # Minimal: splitlines, header, dict rows.
    lines = [l for l in raw.splitlines() if l.strip()]
    if len(lines) < 2:
        return []
    header = lines[0].split("\t")
    out = []
    for line in lines[1:]:
        cols = line.split("\t")
        row = dict(zip(header, cols))
        # BOLD sequence column name varies; agent map to "nuc"
        row["nuc"] = row.get("nuc") or row.get("sequence") or row.get("nucleotide")
        out.append(row)
    return out

if __name__ == "__main__":
    asyncio.run(run())


⸻

5.4 Canonical selection per taxon

# apps/api/src/evograph/pipeline/select_canonical.py
from evograph.db.session import SessionLocal
from evograph.db.models import Sequence

def score(seq: Sequence) -> float:
    ambig = (seq.quality or {}).get("ambig", seq.sequence.count("N"))
    return seq.length - 10.0 * ambig

def run() -> None:
    db = SessionLocal()
    try:
        taxa_ids = [r[0] for r in db.query(Sequence.ott_id).distinct().all()]
        for ott_id in taxa_ids:
            seqs = db.query(Sequence).filter(Sequence.ott_id == ott_id, Sequence.marker == "COI").all()
            if not seqs:
                continue
            best = max(seqs, key=score)
            for s in seqs:
                s.is_canonical = (s.id == best.id)
            db.commit()
    finally:
        db.close()

if __name__ == "__main__":
    run()


⸻

6) MI distance: alignment → MI → distance

6.1 Global alignment

For MVP, use a Python library:
	•	parasail (fast SIMD) or edlib (good edit distance but less full scoring)
If you want pure Python fallback: slow but workable for small counts.

Agent path: use parasail for speed.

Pseudo-wrapper:

# apps/api/src/evograph/utils/alignment.py
from dataclasses import dataclass

@dataclass(frozen=True)
class AlignmentResult:
    a: str
    b: str

def global_align(a: str, b: str) -> AlignmentResult:
    """
    MVP: agent should implement using parasail and return aligned strings with '-' gaps.
    """
    raise NotImplementedError

6.2 MI from aligned pairs

We estimate MI on aligned columns ignoring gaps. For DNA alphabet {A,C,G,T,N}.

MI definition:
	•	Let X be base at position i in aligned seq A
	•	Let Y be base at position i in aligned seq B
	•	Compute empirical joint distribution P(X,Y), marginals P(X), P(Y)
	•	MI = Σ P(x,y) log( P(x,y) / (P(x)P(y)) )

Normalize:
	•	NMI = MI / min(H(X), H(Y)) (or / sqrt(Hx*Hy))
Distance:
	•	d = 1 - NMI (bounded in [0,1] if clean)

# apps/api/src/evograph/services/mi_distance.py
import math
from collections import Counter
from evograph.utils.alignment import AlignmentResult

ALPHABET = ["A","C","G","T","N"]

def entropy(p: dict[str, float]) -> float:
    return -sum(v * math.log(v + 1e-12) for v in p.values() if v > 0)

def mi_from_alignment(aln: AlignmentResult) -> tuple[float, float, int]:
    a, b = aln.a, aln.b
    assert len(a) == len(b)

    joint = Counter()
    cx = Counter()
    cy = Counter()
    n = 0

    for x, y in zip(a, b):
        if x == "-" or y == "-":
            continue
        if x not in ALPHABET or y not in ALPHABET:
            continue
        joint[(x, y)] += 1
        cx[x] += 1
        cy[y] += 1
        n += 1

    if n < 50:
        return (0.0, 0.0, n)

    px = {k: v / n for k, v in cx.items()}
    py = {k: v / n for k, v in cy.items()}
    pxy = {k: v / n for k, v in joint.items()}

    hx = entropy(px)
    hy = entropy(py)
    mi = 0.0
    for (x, y), p in pxy.items():
        mi += p * math.log((p + 1e-12) / ((px[x] * py[y]) + 1e-12))

    denom = min(hx, hy)
    nmi = mi / denom if denom > 1e-9 else 0.0
    nmi = max(0.0, min(1.0, nmi))
    return (mi, nmi, n)

def distance_from_nmi(nmi: float) -> float:
    return 1.0 - nmi

Reality note: this MI is a crude similarity proxy; for MVP it’s fine as long as you validate neighbor sanity.

⸻

7) Candidate neighbor selection (MVP-simple, taxonomy-based)

Simplest candidate strategy (no k-mers yet):
	•	For each species, find its family in the taxonomy tree.
	•	Candidates = canonical sequences of other species in same family.
	•	Then compute MI-distance only on those candidate pairs.
	•	Keep k smallest.

Implementation approach:
	•	Precompute taxa_family_map: species_ott_id -> family_ott_id
	•	Precompute family_members: family_ott_id -> list[species_ott_id]

# apps/api/src/evograph/services/neighbor_index.py
from collections import defaultdict
from evograph.db.models import Taxon

def build_family_index(taxa: list[Taxon]) -> tuple[dict[int,int], dict[int,list[int]]]:
    # Agent: needs parent links + rank parsing to walk up to family
    species_to_family: dict[int,int] = {}
    family_to_species: dict[int,list[int]] = defaultdict(list)
    # TODO: implement walk-up using parent_ott_id pointers
    return species_to_family, family_to_species


⸻

8) Build kNN edges job

# apps/api/src/evograph/pipeline/build_neighbors.py
from evograph.db.session import SessionLocal
from evograph.db.models import Sequence, Edge, Taxon
from evograph.utils.alignment import global_align
from evograph.services.mi_distance import mi_from_alignment, distance_from_nmi
from evograph.services.neighbor_index import build_family_index

K = 15

def run() -> None:
    db = SessionLocal()
    try:
        taxa = db.query(Taxon).all()
        species_to_family, family_to_species = build_family_index(taxa)

        canon = db.query(Sequence).filter(Sequence.marker=="COI", Sequence.is_canonical==True).all()
        canon_by_ott = {s.ott_id: s for s in canon}

        for ott_id, seq in canon_by_ott.items():
            fam = species_to_family.get(ott_id)
            if fam is None:
                continue
            candidates = [c for c in family_to_species.get(fam, []) if c != ott_id and c in canon_by_ott]
            if not candidates:
                continue

            scored: list[tuple[int, float, float, int]] = []
            for cand_id in candidates:
                aln = global_align(seq.sequence, canon_by_ott[cand_id].sequence)
                mi, nmi, n = mi_from_alignment(aln)
                dist = distance_from_nmi(nmi)
                scored.append((cand_id, dist, nmi, n))

            scored.sort(key=lambda x: x[1])
            for cand_id, dist, nmi, n in scored[:K]:
                db.merge(Edge(
                    src_ott_id=ott_id,
                    dst_ott_id=cand_id,
                    marker="COI",
                    distance=dist,
                    mi_norm=nmi,
                    align_len=n,
                ))
            db.commit()
    finally:
        db.close()

if __name__ == "__main__":
    run()

Edge direction: store directed kNN edges; frontend can treat as undirected by symmetrizing.

⸻

9) API endpoints

9.1 Search taxa
	•	GET /v1/search?q=lion&limit=20
Returns list with ott_id/name/rank.

9.2 Taxon detail
	•	GET /v1/taxa/{ott_id}
Returns metadata + parent + children + canonical sequence availability.

9.3 Subtree graph
	•	GET /v1/graph/subtree/{ott_id}?depth=3
Returns nodes+edges for that subtree (tree edges + MI edges among nodes present).

9.4 Neighbors
	•	GET /v1/graph/neighbors/{ott_id}?k=15
Returns nearest neighbors by distance.

Schema sample:

# apps/api/src/evograph/api/schemas/graph.py
from pydantic import BaseModel

class Node(BaseModel):
    ott_id: int
    name: str
    rank: str
    image_url: str | None = None

class Edge(BaseModel):
    src: int
    dst: int
    kind: str  # "taxonomy" | "mi"
    distance: float | None = None

class GraphResponse(BaseModel):
    nodes: list[Node]
    edges: list[Edge]


⸻

10) Frontend (Next.js) UX plan

Pages
	•	/ search + featured graph entry (root scope)
	•	/graph graph viewer for scope root
	•	/taxa/[ottId] detail panel + embedded local graph

GraphView requirements
	•	Load GraphResponse from API
	•	Render nodes; size maybe by rank; show labels on hover
	•	Two edge layers:
	•	taxonomy edges: faint
	•	MI edges: stronger; tooltip with distance

Basic API client

// apps/web/src/lib/api.ts
export async function getJSON<T>(path: string): Promise<T> {
  const res = await fetch(process.env.NEXT_PUBLIC_API_BASE + path);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json() as Promise<T>;
}


⸻

11) Docker compose (local dev)

version: "3.9"
services:
  db:
    image: postgres:16
    environment:
      POSTGRES_PASSWORD: postgres
      POSTGRES_USER: postgres
      POSTGRES_DB: evograph
    ports: ["5432:5432"]
    volumes: ["pgdata:/var/lib/postgresql/data"]

  redis:
    image: redis:7
    ports: ["6379:6379"]

  api:
    build: ./apps/api
    environment:
      DATABASE_URL: postgresql+psycopg://postgres:postgres@db:5432/evograph
      REDIS_URL: redis://redis:6379/0
    ports: ["8000:8000"]
    depends_on: [db, redis]

  web:
    build: ./apps/web
    environment:
      NEXT_PUBLIC_API_BASE: http://localhost:8000
    ports: ["3000:3000"]
    depends_on: [api]

volumes:
  pgdata:


⸻

12) Makefile commands (agent ergonomics)

.PHONY: up down migrate ingest_ott ingest_bold canonical neighbors export

up:
	docker compose up --build

down:
	docker compose down

migrate:
	docker compose exec api alembic upgrade head

ingest_ott:
	docker compose exec api python -m evograph.pipeline.ingest_ott

ingest_bold:
	docker compose exec api python -m evograph.pipeline.ingest_bold

canonical:
	docker compose exec api python -m evograph.pipeline.select_canonical

neighbors:
	docker compose exec api python -m evograph.pipeline.build_neighbors

export:
	docker compose exec api python -m evograph.pipeline.build_graph_export


⸻

13) Validation checks (don’t ship a pretty lie)

Add a script pipeline/validate.py that computes:
	•	% of MI-neighbors sharing genus/family (from taxonomy)
	•	distribution of distances
	•	identify outliers (distance near 0 for far taxa or near 1 for same genus)

MVP “success criteria”:
	•	For most nodes, top-5 neighbors share family (ideally genus) most of the time.

⸻

14) “Coding agent” task breakdown (tickets)

Ticket 1: DB + models + migrations
	•	SQLAlchemy models for Taxon/Sequence/Edge
	•	Alembic migrations

Ticket 2: OpenTree ingest
	•	Implement tnrs_match + taxonomy_subtree parsing
	•	Persist taxa with parent relationships

Ticket 3: BOLD ingest
	•	Implement BOLD endpoint choice + parsing
	•	Store raw + normalized sequences
	•	Basic rate limiting / retry

Ticket 4: Canonical selection
	•	Implement scoring + set canonical

Ticket 5: Alignment implementation
	•	Implement global_align using parasail
	•	Return aligned strings with gaps

Ticket 6: MI + distance
	•	Implement MI from aligned columns
	•	Unit tests with known toy sequences

Ticket 7: Family index + candidate selection
	•	Walk parent chain to nearest family
	•	Build species_to_family, family_to_species

Ticket 8: Build kNN edges job
	•	Compute MI-distance among candidates
	•	Store top-K edges

Ticket 9: API
	•	Search, taxa detail, subtree graph, neighbors

Ticket 10: Frontend
	•	Search UI
	•	Taxon page
	•	Graph view with layered edges

Ticket 11: Export + caching (optional)
	•	Pre-export JSON for scope root
	•	Serve static graph quickly

⸻

15) Notes that save you pain later
	•	IDs are everything: treat OTT id as primary. Names are lies.
	•	Sequence provenance: store raw payload and “accession/process id” always.
	•	Rate limits: BOLD/NCBI can throttle—implement backoff.
	•	Graph size: keep it local. Render subtree graphs; don’t try to draw 200k nodes at once.

⸻

If you want the agent to be fully unblocked, the one thing they’ll need to adapt in real time is the exact OpenTree subtree response shape and the exact BOLD API endpoint/fields, because those APIs are real-world messy. Everything else above is stable engineering.

Next logical upgrade after MVP (still sane): replace “same-family candidates” with a k-mer sketch ANN index so you can find neighbors across families (useful for mislabels and deeper structure).