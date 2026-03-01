# CLAUDE.md — EvoGraph Development Guide

## Project Overview

EvoGraph is an evolutionary biology visualization platform that maps species relationships through both taxonomy (Open Tree of Life) and genetic similarity (mutual information from COI barcode sequences). The MVP scope is **Aves (birds)**: ~27,853 taxa, ~167 species with COI sequences, ~1,787 MI edges.

**Core idea:** Build a k-nearest-neighbor graph where edge weight = MI-derived distance from pairwise COI sequence alignment. Overlay this on the taxonomic tree so users can explore how genetic similarity compares to taxonomic classification.

## Architecture

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Next.js    │────▶│   FastAPI    │────▶│  PostgreSQL  │
│  (port 3000) │     │  (port 8000) │     │  (port 5432) │
└──────────────┘     └──────────────┘     └──────────────┘
                           │                     │
                           ▼                     │
                     ┌──────────┐               │
                     │  Redis   │  (unused yet)  │
                     │ (6379)   │               │
                     └──────────┘               │
                                                │
                     ┌──────────────────────────┘
                     │  Pipeline scripts
                     │  (ingest → compute → export)
                     └─────────────────────────────
```

## Repository Structure

```
evograph/
├── apps/
│   ├── api/                          # Python FastAPI backend
│   │   ├── pyproject.toml            # Dependencies, pytest config, ruff config
│   │   ├── Dockerfile
│   │   ├── alembic.ini
│   │   ├── src/evograph/
│   │   │   ├── main.py               # FastAPI app, CORS, routers
│   │   │   ├── settings.py           # DATABASE_URL, REDIS_URL, SCOPE_OTT_ROOT
│   │   │   ├── db/
│   │   │   │   ├── models.py         # Taxon, Sequence, Edge, NodeMedia
│   │   │   │   ├── session.py        # engine, SessionLocal, get_db
│   │   │   │   └── migrations/versions/001_initial.py
│   │   │   ├── api/
│   │   │   │   ├── routes/           # search, taxa, graph, sequences
│   │   │   │   └── schemas/          # Pydantic response models
│   │   │   ├── services/
│   │   │   │   ├── ott_client.py     # OpenTree API (tnrs, subtree, taxon_info)
│   │   │   │   ├── bold_client.py    # BOLD portal v5 (currently down)
│   │   │   │   ├── mi_distance.py    # entropy, MI, NMI, distance
│   │   │   │   └── neighbor_index.py # family-scoped candidate selection
│   │   │   ├── pipeline/            # Data ingestion & computation scripts
│   │   │   │   ├── ingest_ott.py     # Newick parser → taxa table
│   │   │   │   ├── ingest_ncbi.py    # NCBI esearch/efetch → sequences
│   │   │   │   ├── ingest_bold.py    # BOLD portal → sequences (portal down)
│   │   │   │   ├── select_canonical.py # Pick best COI per species
│   │   │   │   ├── build_neighbors.py  # Pairwise MI → kNN edges
│   │   │   │   ├── build_graph_export.py # JSON files for caching
│   │   │   │   ├── ingest_images.py  # Wikipedia thumbnails → node_media
│   │   │   │   └── validate.py       # Quality stats & outlier detection
│   │   │   └── utils/
│   │   │       ├── alignment.py      # parasail global alignment wrapper
│   │   │       └── fasta.py          # FASTA format parser
│   │   └── tests/                    # 42 pytest tests
│   │       ├── conftest.py           # MockDB, fixtures, factories
│   │       ├── test_health.py
│   │       ├── test_search.py
│   │       ├── test_taxa.py
│   │       ├── test_graph.py
│   │       ├── test_sequences.py
│   │       └── test_mi_distance.py
│   └── web/                          # Next.js 15 + TypeScript frontend
│       ├── package.json
│       ├── Dockerfile
│       ├── tsconfig.json             # Strict mode, @/* path alias
│       ├── next.config.js            # output: "standalone"
│       └── src/
│           ├── app/
│           │   ├── globals.css       # Dark theme, skeleton, responsive
│           │   ├── layout.tsx        # Root layout, sticky nav
│           │   ├── page.tsx          # Home: search + quick links
│           │   ├── graph/page.tsx    # MI network explorer (Sigma.js)
│           │   └── taxa/[ottId]/
│           │       ├── page.tsx      # Taxon detail (hero, children, neighbors)
│           │       └── sequences/page.tsx  # COI sequence viewer
│           ├── components/
│           │   ├── SearchBox.tsx      # Debounced autocomplete
│           │   ├── TaxonCard.tsx      # Thumbnail + rank badge
│           │   ├── GraphView.tsx      # Cytoscape.js (small graphs)
│           │   ├── GraphViewSigma.tsx # Sigma.js (large networks)
│           │   └── Skeleton.tsx       # Shimmer loading states
│           └── lib/
│               ├── api.ts            # API client functions
│               ├── types.ts          # TypeScript interfaces
│               └── external-links.ts # Wikipedia, iNaturalist, eBird URLs
├── docker-compose.yml                # postgres:16, redis:7, api, web
├── Makefile                          # Pipeline orchestration commands
├── .github/workflows/ci.yml         # Lint, test, typecheck, build
├── .env.example
├── TODO.md                           # Tracked tasks with completion status
├── ROADMAP.md                        # 6-phase long-term vision
└── MVP.md                            # Original implementation spec
```

## Database Schema

Four PostgreSQL tables (migration: `001_initial.py`):

| Table | PK | Purpose | Key columns |
|-------|-----|---------|-------------|
| **taxa** | `ott_id` (int) | Taxonomy backbone | name, rank, parent_ott_id (self-FK), ncbi_tax_id, lineage (int[]), synonyms (jsonb) |
| **sequences** | `id` (uuid) | COI barcode DNA | ott_id (FK), marker, source, accession, sequence (text), length, quality (jsonb), is_canonical |
| **edges** | `(src_ott_id, dst_ott_id, marker)` | MI similarity graph | distance (0-1), mi_norm (0-1), align_len |
| **node_media** | `ott_id` (FK) | Species images | image_url, attribution (jsonb) |

**Indexes:** taxa(name), taxa(parent_ott_id), sequences(ott_id), edges(src_ott_id), edges(dst_ott_id)

## API Endpoints

All under FastAPI with CORS enabled (all origins).

| Method | Path | Params | Response | Notes |
|--------|------|--------|----------|-------|
| GET | `/health` | — | `{"status":"ok"}` | |
| GET | `/v1/search` | `q` (required, min 1), `limit` (max 100) | `TaxonSummary[]` | ILIKE on name |
| GET | `/v1/taxa/{ott_id}` | — | `TaxonDetail` | Children limited to 100 inline |
| GET | `/v1/taxa/{ott_id}/children` | `offset`, `limit` (max 500) | `ChildrenPage` | Paginated |
| GET | `/v1/taxa/{ott_id}/sequences` | — | `SequenceOut[]` | Includes DNA sequence text |
| GET | `/v1/graph/subtree/{ott_id}` | `depth` (1-5, default 3) | `GraphResponse` | BFS + MI edges |
| GET | `/v1/graph/mi-network` | — | `GraphResponse` | All MI-connected species |
| GET | `/v1/graph/neighbors/{ott_id}` | `k` (1-50, default 15) | `NeighborOut[]` | Sorted by distance |

**Key response types:**
- `TaxonDetail`: includes children[], total_children, lineage[], has_canonical_sequence, wikipedia_url
- `GraphResponse`: nodes[] + edges[] (kind: "taxonomy" | "mi")
- `SequenceOut`: includes full DNA sequence text, source, accession, is_canonical

## Pipeline Order

Run via Makefile or directly as `python -m evograph.pipeline.<name>`:

```
1. ingest_ott      — Parse OpenTree Newick subtree → taxa table (~27,853 for Aves)
2. ingest_ncbi     — Fetch COI from NCBI GenBank → sequences table
   ingest_bold     — Fetch COI from BOLD portal → sequences table (portal down)
3. select_canonical — Score sequences (length - 10*ambig), mark best per species
4. build_neighbors  — Pairwise alignment + MI distance → kNN edges (k=15)
5. build_graph_export — Export nodes.json + edges.json
6. ingest_images   — Wikipedia thumbnails → node_media table
7. validate        — Print quality report (genus/family sharing %, distance stats)
```

**Full pipeline:** `make pipeline` runs steps 1-7 in sequence.

## Key Algorithms

### MI Distance (services/mi_distance.py)
```
1. Global alignment via parasail (Needleman-Wunsch, SIMD)
   Scoring: match=+2, mismatch=-1, gap_open=3, gap_extend=1

2. From aligned columns (excluding gaps):
   - P(X), P(Y): marginal distributions of bases
   - P(X,Y): joint distribution
   - MI = Σ P(x,y) * log(P(x,y) / (P(x)*P(y)))
   - NMI = MI / min(H(X), H(Y)), clamped to [0,1]
   - Requires ≥ 50 non-gap columns

3. Distance = 1 - NMI (0 = identical, 1 = unrelated)
```

### Candidate Selection (services/neighbor_index.py)
- Walk up parent chain from each species to find enclosing family
- Only compute MI distance between species in the same family
- Phase 2 upgrade: k-mer ANN index for cross-family detection

### Canonical Sequence Selection (pipeline/select_canonical.py)
- Score = length - 10 * ambiguous_base_count
- Highest score per species wins canonical flag

## Development Commands

```bash
# Local dev (Docker)
make up                   # docker compose up --build
make down                 # docker compose down
make migrate              # alembic upgrade head

# API tests (42 tests)
cd apps/api && python -m pytest tests/ -v

# Lint
cd apps/api && ruff check src/ tests/
cd apps/web && npm run lint

# Typecheck
cd apps/web && npx tsc --noEmit

# Build frontend
cd apps/web && npm run build
```

## Environment Variables

```
DATABASE_URL=postgresql+psycopg://postgres:postgres@db:5432/evograph
REDIS_URL=redis://redis:6379/0
SCOPE_OTT_ROOT=Aves
NEXT_PUBLIC_API_BASE=http://localhost:8000
```

## Testing Strategy

**Current: 42 tests passing** (all in `apps/api/tests/`)

Tests use `MockDB` with FastAPI dependency override — no real database needed:
- `conftest.py`: Mock factories (`_make_taxon`, `_make_sequence`, `_make_edge`, `_make_media`), `MockQuery` (chainable filter/limit/order_by/scalar), `MockDB` (registry by model type)
- Override `get_db` dependency with mock session

**What's tested:**
- All 8 API endpoints (status codes, response schemas, validation errors, 404s)
- MI distance computation (entropy, NMI, clamping, gap exclusion)

**What's NOT tested:**
- Pipeline scripts (ingest, canonical selection, neighbor building)
- Frontend components (no Jest/RTL)
- External API integration (OpenTree, NCBI, Wikipedia)
- Database migrations

## Frontend Conventions

- **Dark theme:** CSS variables in globals.css (--bg, --fg, --accent, --border, --bg-card)
- **Rank colors:** class=#e57373, order=#ffb74d, family=#fff176, genus=#81c784, species=#4fc3f7
- **Two graph renderers:** GraphView.tsx (Cytoscape, for small subtree graphs) and GraphViewSigma.tsx (Sigma.js WebGL, for full MI network)
- **Loading states:** Skeleton.tsx with shimmer animation (not plain text)
- **Responsive breakpoints:** 768px (tablet), 480px (mobile)
- **Species names:** Always italicized (`<span className="italic">`)

## Type Consistency Rules

The following types must stay in sync across three layers:

| Python Schema | TypeScript Type | DB Model |
|---------------|-----------------|----------|
| `TaxonSummary` | `TaxonSummary` | `Taxon` |
| `TaxonDetail` | `TaxonDetail` | `Taxon` + joins |
| `ChildrenPage` | `ChildrenPage` | — |
| `SequenceOut` | `SequenceOut` | `Sequence` |
| `Node` / `GraphEdge` / `GraphResponse` | `GraphNode` / `GraphEdge` / `GraphResponse` | `Taxon` + `Edge` |
| `NeighborOut` | `NeighborOut` | `Edge` + `Taxon` join |

**When adding a field:** Update all three: schema → route mapping → TypeScript type → API client → UI usage.

**File locations:**
- Python schemas: `apps/api/src/evograph/api/schemas/`
- TypeScript types: `apps/web/src/lib/types.ts`
- API client: `apps/web/src/lib/api.ts`

## Current Data Status

| Metric | Value |
|--------|-------|
| Total taxa | ~27,853 (Aves) |
| Species with COI | ~167 (0.6%) |
| Total sequences | ~167 |
| MI edges | ~1,787 |
| Images | Fetched from Wikipedia |

**Why so few sequences:**
- NCBI query finds only ~167 matches for Aves species
- BOLD portal has been down since Feb 2026
- TODO: Broader NCBI search (genus fallback, relaxed terms)

## Remaining Work (from TODO.md)

### High Priority
- [ ] Expand NCBI ingestion — try genus-level queries, broader search terms
- [ ] Retry BOLD portal when it comes back online
- [ ] Pipeline unit tests — test canonical selection logic
- [ ] Frontend smoke tests
- [ ] Cache MI network endpoint (Redis or in-memory TTL)

### Medium Priority
- [ ] Graph page: add node search/filter
- [ ] Run validate.py and document results
- [ ] Dockerfile health checks
- [ ] Production deployment config

### Phase 2
- [ ] Make SCOPE_OTT_ROOT configurable for other clades
- [ ] k-mer candidate filtering (FAISS/Annoy) for cross-family neighbors
- [ ] Job queue (Celery/RQ) for background pipeline jobs
- [ ] Multi-marker support (16S, 18S)

## Architectural Principles

1. **OTT ID is canonical identity** — everything links through ott_id
2. **Sequences are immutable** — stored with provenance (source, accession)
3. **Edges are recomputable** — derived from sequences, can be rebuilt
4. **Graph is derived data** — not the source of truth
5. **MI is a similarity proxy, not phylogenetic truth** — always label as "similarity"

## Known Gotchas

- `pyproject.toml` requires Python >=3.11 (relaxed from 3.12 for compatibility)
- Build backend is `hatchling.build` (not `hatchling.backends`)
- Redis is configured but not used yet (reserved for caching)
- CORS is wide open (`allow_origins=["*"]`) — tighten for production
- `data/raw/` and `data/processed/` are gitignored — not in repo
- Graph JSON exports exist at `apps/api/src/data/processed/graph/` but are gitignored
- Sequence `quality` field is JSONB with `{"ambig": N}` format
- Edges are directed (A→B) but UI treats as undirected
- Lineage is built by walking parent chain at query time (not precomputed)
- The `ingest_images.py` uses raw SQL (`text()`) for the join query
