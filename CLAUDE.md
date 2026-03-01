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
│   │   ├── Dockerfile                # Health check included
│   │   ├── alembic.ini
│   │   ├── src/evograph/
│   │   │   ├── main.py               # FastAPI app, CORS, rate limiting, logging, routers
│   │   │   ├── settings.py           # DATABASE_URL, REDIS_URL, SCOPE_OTT_ROOT, CORS_ORIGINS
│   │   │   ├── db/
│   │   │   │   ├── models.py         # Taxon, Sequence, Edge, NodeMedia
│   │   │   │   ├── session.py        # engine, SessionLocal, get_db
│   │   │   │   └── migrations/versions/001_initial.py
│   │   │   ├── api/
│   │   │   │   ├── routes/           # search, taxa, graph, sequences, stats
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
│   │   │   │   ├── backfill_ncbi_tax_id.py # NCBI Taxonomy API → ncbi_tax_id column
│   │   │   │   ├── dedup_sequences.py # Remove duplicate accessions
│   │   │   │   └── validate.py       # Quality stats & outlier detection (JSON export)
│   │   │   ├── middleware/
│   │   │   │   ├── rate_limit.py    # Sliding-window per-IP rate limiter
│   │   │   │   └── request_logging.py # Structured access logging + X-Request-ID
│   │   │   └── utils/
│   │   │       ├── alignment.py      # parasail global alignment wrapper
│   │   │       └── fasta.py          # FASTA format parser
│   │   └── tests/                    # 99 pytest tests
│   │       ├── conftest.py           # MockDB, fixtures, factories
│   │       ├── test_health.py
│   │       ├── test_search.py
│   │       ├── test_taxa.py
│   │       ├── test_graph.py
│   │       ├── test_sequences.py
│   │       ├── test_mi_distance.py
│   │       ├── test_pipeline.py      # Canonical selection scoring tests
│   │       ├── test_backfill_ncbi.py # NCBI tax ID lookup tests
│   │       ├── test_ingest_ncbi.py   # NCBI ingestion search strategy tests
│   │       ├── test_dedup_sequences.py # Sequence deduplication tests
│   │       ├── test_stats.py         # Stats endpoint tests
│   │       ├── test_validate.py      # Validation pipeline tests
│   │       ├── test_rate_limit.py    # Rate limiting middleware tests
│   │       └── test_request_logging.py # Request logging middleware tests
│   └── web/                          # Next.js 15 + TypeScript frontend
│       ├── package.json
│       ├── Dockerfile                # Health check included
│       ├── tsconfig.json             # Strict mode, @/* path alias
│       ├── next.config.js            # output: "standalone"
│       ├── jest.config.js            # Jest + next/jest setup
│       ├── jest.setup.ts             # @testing-library/jest-dom
│       └── src/
│           ├── app/
│           │   ├── globals.css       # Dark theme, skeleton, responsive, graph search
│           │   ├── layout.tsx        # Root layout, sticky nav
│           │   ├── page.tsx          # Home: search + quick links
│           │   ├── graph/page.tsx    # MI network explorer (Sigma.js) + node search
│           │   ├── stats/page.tsx   # Database stats dashboard
│           │   ├── not-found.tsx    # 404 page
│           │   ├── error.tsx        # Error boundary page
│           │   └── taxa/[ottId]/
│           │       ├── page.tsx      # Taxon detail (hero, children, neighbors)
│           │       └── sequences/page.tsx  # COI sequence viewer
│           ├── components/
│           │   ├── SearchBox.tsx      # Debounced autocomplete
│           │   ├── TaxonCard.tsx      # Thumbnail + rank badge
│           │   ├── GraphView.tsx      # Cytoscape.js (small graphs)
│           │   ├── GraphViewSigma.tsx # Sigma.js (large networks)
│           │   ├── Skeleton.tsx       # Shimmer loading states
│           │   └── ErrorBoundary.tsx  # React error boundary with retry
│           └── lib/
│               ├── api.ts            # API client functions
│               ├── types.ts          # TypeScript interfaces
│               └── external-links.ts # Wikipedia, iNaturalist, eBird URLs
│           └── __tests__/            # 71 Jest + RTL tests
│               ├── HomePage.test.tsx
│               ├── TaxonDetailPage.test.tsx
│               ├── SequencesPage.test.tsx
│               ├── SearchBox.test.tsx
│               ├── TaxonCard.test.tsx
│               ├── Skeleton.test.tsx
│               ├── ErrorBoundary.test.tsx
│               ├── StatsPage.test.tsx
│               ├── api.test.ts
│               └── external-links.test.ts
├── docker-compose.yml                # postgres:16, redis:7, api, web (with health checks)
├── Makefile                          # Pipeline orchestration commands
├── .github/workflows/ci.yml         # Lint, test, typecheck, build
├── .env.example
├── TODO.md                           # Tracked tasks with completion status
├── ROADMAP.md                        # 6-phase long-term vision
└── MVP.md                            # Original implementation spec
```

## Database Schema

Four PostgreSQL tables (migrations: `001_initial.py`, `002_performance_indexes.py`):

| Table | PK | Purpose | Key columns |
|-------|-----|---------|-------------|
| **taxa** | `ott_id` (int) | Taxonomy backbone | name, rank, parent_ott_id (self-FK), ncbi_tax_id, lineage (int[]), synonyms (jsonb) |
| **sequences** | `id` (uuid) | COI barcode DNA | ott_id (FK), marker, source, accession, sequence (text), length, quality (jsonb), is_canonical |
| **edges** | `(src_ott_id, dst_ott_id, marker)` | MI similarity graph | distance (0-1), mi_norm (0-1), align_len |
| **node_media** | `ott_id` (FK) | Species images | image_url, attribution (jsonb) |

**Indexes (migration 001):** taxa(name), taxa(parent_ott_id), sequences(ott_id), edges(src_ott_id), edges(dst_ott_id)

**Performance indexes (migration 002):**
- `ix_taxa_name_trgm` — GIN trigram index on taxa.name (fast ILIKE `%query%`)
- `ix_taxa_rank` — B-tree on taxa.rank (rank-based filtering)
- `ix_edges_src_distance` — composite on edges(src_ott_id, distance) (neighbor queries)
- `ix_sequences_ott_canonical` — composite on sequences(ott_id, is_canonical) (canonical checks)
- `ix_sequences_ott_marker` — composite on sequences(ott_id, marker) (pipeline selection)

## API Endpoints

All under FastAPI with CORS enabled (all origins).

| Method | Path | Params | Response | Notes |
|--------|------|--------|----------|-------|
| GET | `/health` | — | `{"status":"ok","scope":"Aves"}` | Includes configured scope |
| GET | `/v1/search` | `q` (required, min 1), `limit` (max 100) | `TaxonSummary[]` | pg_trgm + prefix ranking |
| GET | `/v1/taxa/{ott_id}` | — | `TaxonDetail` | Recursive CTE lineage |
| GET | `/v1/taxa/{ott_id}/children` | `offset`, `limit` (max 500) | `ChildrenPage` | Paginated |
| GET | `/v1/taxa/{ott_id}/sequences` | — | `SequenceOut[]` | Includes DNA sequence text |
| GET | `/v1/graph/subtree/{ott_id}` | `depth` (1-5, default 3) | `GraphResponse` | Recursive CTE subtree |
| GET | `/v1/graph/mi-network` | — | `GraphResponse` | Cached 5min in-memory |
| GET | `/v1/graph/neighbors/{ott_id}` | `k` (1-50, default 15) | `NeighborOut[]` | Sorted by distance |
| GET | `/v1/stats` | — | `StatsResponse` | Taxa/sequence/edge counts |

**Key response types:**
- `TaxonDetail`: includes children[], total_children, lineage[], has_canonical_sequence, wikipedia_url
- `GraphResponse`: nodes[] + edges[] (kind: "taxonomy" | "mi")
- `SequenceOut`: includes full DNA sequence text, source, accession, is_canonical

## Pipeline Order

Run via Makefile or directly as `python -m evograph.pipeline.<name>`:

```
1. ingest_ott      — Parse OpenTree Newick subtree → taxa table (--scope configurable)
2. ingest_ncbi     — Fetch COI from NCBI GenBank → sequences (genus fallback, --skip-existing)
   ingest_bold     — Fetch COI from BOLD portal → sequences table (portal down)
3. dedup_sequences — Remove duplicate accessions, keep longest (--dry-run supported)
4. select_canonical — Score sequences (length - 10*ambig), mark best per species
5. build_neighbors  — Pairwise alignment + MI distance → kNN edges (k=15)
6. build_graph_export — Export nodes.json + edges.json
7. ingest_images   — Wikipedia thumbnails → node_media table
8. backfill_ncbi_tax_id — Query NCBI Taxonomy API → ncbi_tax_id column
9. validate        — Print quality report (genus/family sharing %, distance stats, --output for JSON)
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

# API tests (96 tests)
cd apps/api && python -m pytest tests/ -v

# Frontend tests (64 tests)
cd apps/web && npm test

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

**Current: 160 tests passing** (96 API + 64 frontend)

**API tests** (`apps/api/tests/`) — use `MockDB` with FastAPI dependency override, no real database:
- `conftest.py`: Mock factories (`_make_taxon`, `_make_sequence`, `_make_edge`, `_make_media`), `MockQuery` (chainable filter/limit/order_by/scalar/exists/select_from), `MockDB` (registry by model type + execute for CTEs)
- All 10 API endpoints (status codes, response schemas, validation errors, 404s)
- MI distance computation (entropy, NMI, clamping, gap exclusion)
- Pipeline canonical selection scoring (11 tests for `_score` function)
- NCBI taxonomy ID lookup (6 tests for `_lookup_tax_id` function)
- NCBI ingestion search strategy (15 tests: query building, esearch, efetch, genus fallback)
- Sequence deduplication (3 tests for `find_duplicates` function)
- Validation pipeline (12 tests: walk_to_rank, report structure, outlier detection)
- Stats endpoint (2 tests: structure, empty database)
- Rate limiting middleware (5 tests: headers, decrement, 429, exclusions)

**Frontend tests** (`apps/web/src/__tests__/`) — Jest + React Testing Library:
- `HomePage.test.tsx` — heading, search box, quick links, rank badges
- `TaxonDetailPage.test.tsx` — skeleton, hero, breadcrumb, children, external links, error state
- `SequencesPage.test.tsx` — skeleton, accessions, canonical badge, composition, expansion toggle
- `SearchBox.test.tsx` — debounce, API calls, dropdown, navigation on selection
- `TaxonCard.test.tsx` — rendering, links, child count, image, italicization
- `Skeleton.test.tsx` — SkeletonLine/Circle/Card, TaxonDetailSkeleton, GraphPageSkeleton
- `ErrorBoundary.test.tsx` — renders children, fallback on error, custom fallback, retry recovery
- `api.test.ts` — all API client functions (URL construction, error handling)
- `external-links.test.ts` — Wikipedia, iNaturalist, eBird URL formatting

**What's NOT tested:**
- Full pipeline integration (ingest, neighbor building)
- External API integration (OpenTree, NCBI, Wikipedia)
- Database migrations
- Graph rendering components (Cytoscape, Sigma.js — require canvas)

## Frontend Conventions

- **Dark theme:** CSS variables in globals.css (--bg, --fg, --accent, --border, --bg-card)
- **Rank colors:** class=#e57373, order=#ffb74d, family=#fff176, genus=#81c784, species=#4fc3f7
- **Two graph renderers:** GraphView.tsx (Cytoscape, for small subtree graphs) and GraphViewSigma.tsx (Sigma.js WebGL, for full MI network)
- **Graph search:** NodeSearchBox component in graph/page.tsx — autocomplete dropdown that highlights + zooms to selected node
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
| (inline dict) | `StatsResponse` | Aggregation queries |

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
- Initial NCBI query found only ~167 matches (narrow COI gene annotations)
- Broader search + genus fallback now available (re-run `ingest_ncbi --skip-existing`)
- BOLD portal has been down since Feb 2026

## Remaining Work (from TODO.md)

### High Priority
- [ ] Retry BOLD portal when it comes back online

### Medium Priority
- [ ] Run validate.py and document results (now with `--output` JSON export)
- [ ] Production deployment config

### Phase 2
- [ ] k-mer candidate filtering (FAISS/Annoy) for cross-family neighbors
- [ ] Job queue (Celery/RQ) for background pipeline jobs
- [ ] Precompute subtree graph exports for common entry points
- [ ] Multi-marker support (16S, 18S)

## Architectural Principles

1. **OTT ID is canonical identity** — everything links through ott_id
2. **Sequences are immutable** — stored with provenance (source, accession)
3. **Edges are recomputable** — derived from sequences, can be rebuilt
4. **Graph is derived data** — not the source of truth
5. **MI is a similarity proxy, not phylogenetic truth** — always label as "similarity"

## Performance Characteristics

- **Connection pooling:** 10 persistent + 20 overflow connections, 5min recycle, pre-ping validation
- **GZip compression:** All responses > 500 bytes are compressed (critical for graph JSON)
- **Lineage query:** Single recursive CTE (was N+1 individual parent lookups)
- **Subtree query:** Single recursive CTE (was Python-side BFS with one query per level)
- **Canonical check:** Uses `EXISTS` subquery (was fetching full row)
- **Search:** pg_trgm GIN index for fast ILIKE substring matching; prefix matches ranked first
- **MI network:** In-memory cache with 5-minute TTL
- **Neighbor queries:** Composite index (src_ott_id, distance) for indexed ORDER BY + LIMIT
- **Rate limiting:** Sliding-window per-IP (100 req/min), /health excluded, X-RateLimit headers

## Known Gotchas

- `pyproject.toml` requires Python >=3.11 (relaxed from 3.12 for compatibility)
- Build backend is `hatchling.build` (not `hatchling.backends`)
- Redis is configured but not used yet (reserved for caching)
- CORS is wide open (`allow_origins=["*"]`) — tighten for production
- `data/raw/` and `data/processed/` are gitignored — not in repo
- Graph JSON exports exist at `apps/api/src/data/processed/graph/` but are gitignored
- Sequence `quality` field is JSONB with `{"ambig": N}` format
- Edges are directed (A→B) but UI treats as undirected
- The `ingest_images.py` uses raw SQL (`text()`) for the join query
- MI network endpoint is cached in-memory (5min TTL) — stale data possible after pipeline re-run
- Cytoscape types use `StylesheetStyle` (not `Stylesheet`) in newer @types/cytoscape
- Migration 002 requires `pg_trgm` extension — enabled automatically in upgrade()
