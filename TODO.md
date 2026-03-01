# EvoGraph — Next Tasks

## High Priority

### Sequence Coverage
- [x] Expand NCBI ingestion — broader COI gene search terms (COI/COX1/COXI/CO1 + title variants), genus-level fallback, `--skip-existing` flag
- [ ] Retry BOLD portal — `portal.boldsystems.org` has been down since Feb 2026. Check periodically; when it returns, `ingest_bold.py` is ready
- [x] Add NCBI taxonomy ID lookup — `backfill_ncbi_tax_id.py` queries NCBI Taxonomy API by scientific name and updates ncbi_tax_id column

### Testing
- [x] API route tests — pytest + httpx TestClient for all endpoints (42 tests)
- [x] MI distance unit tests — entropy, MI computation, NMI clamping, distance conversion
- [x] Pipeline unit tests — canonical selection scoring logic (11 tests)
- [x] Frontend smoke tests — Jest + React Testing Library, 58 tests across 8 suites (pages, components, API client, utilities)

### Performance
- [x] Cache MI network endpoint — in-memory cache with 5-minute TTL
- [x] Performance indexes (migration 002) — pg_trgm, composite indexes for neighbors/canonical/search
- [x] Paginate children for large taxa — inline limit of 100, dedicated `/taxa/{id}/children` endpoint with offset/limit
- [x] Connection pooling — 10 persistent + 20 overflow, pre-ping, 5min recycle
- [x] Recursive CTE for lineage — single query replaces N+1 parent chain walk
- [x] Recursive CTE for subtree — single query replaces Python BFS with per-level queries
- [x] GZip compression — middleware compresses responses > 500 bytes
- [x] Search optimization — pg_trgm GIN index + prefix ranking + LIKE pattern escaping
- [x] EXISTS for canonical check — replaces fetching full row

## Medium Priority

### Frontend Polish
- [x] Add `getSequences()` to frontend API client
- [x] Sequence viewer page — color-coded DNA bases, composition bar, expandable cards
- [x] Mobile responsive layout — breakpoints at 768px and 480px
- [x] Loading skeletons — shimmer animation for taxon detail and graph pages
- [x] Graph page: node search/filter within the MI network — autocomplete dropdown with camera animation

### Data Quality
- [ ] Run `validate.py` and document results — what % of neighbors share genus/family?
- [x] Flag taxonomic outliers — `validate.py` now returns structured `ValidationReport` with `OutlierRecord` objects (cross-family close, within-genus distant), JSON export via `--output`
- [x] Deduplicate sequences — `dedup_sequences.py` removes duplicate accessions, keeping longest per (ott_id, accession, marker)

### DevOps
- [x] Add Dockerfile health checks — API (Python urllib), Web (Node fetch), DB (pg_isready), Redis (redis-cli ping)
- [x] CI pipeline (GitHub Actions) — lint, typecheck, test, build
- [x] Fix lint warnings — removed unused imports, fixed f-string, removed unused variable
- [ ] Production deployment config (fly.io, Railway, or VPS)

## Phase 2 (from ROADMAP.md)

### Scale Across Animalia
- [x] Make `SCOPE_OTT_ROOT` configurable — env var in docker-compose, `--scope` CLI arg, exposed in `/health` endpoint
- [ ] k-mer candidate filtering — replace family-scoped search with ANN index (FAISS/Annoy) for cross-family neighbor detection
- [ ] Job queue — replace one-shot scripts with Celery/RQ for background pipeline jobs
- [ ] Precompute subtree graph exports for common entry points

### Multi-Marker Support (Phase 3)
- [ ] Add 16S, 18S marker ingestion
- [ ] Typed edges: `Edge(marker="COI", method="mi_alignment")`
- [ ] Composite distance: weighted sum across markers
