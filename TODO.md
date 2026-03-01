# EvoGraph — Next Tasks

## High Priority

### Sequence Coverage
- [ ] Expand NCBI ingestion — current query finds only 167/18,805 species. Try broader search terms, search by genus when species fails, increase `--per-species` limit
- [ ] Retry BOLD portal — `portal.boldsystems.org` has been down since Feb 2026. Check periodically; when it returns, `ingest_bold.py` is ready
- [ ] Add NCBI taxonomy ID lookup — `ncbi_tax_id` column exists but is never populated. Add pipeline step to query NCBI Taxonomy by name and backfill

### Testing
- [x] API route tests — pytest + httpx TestClient for all endpoints (42 tests)
- [x] MI distance unit tests — entropy, MI computation, NMI clamping, distance conversion
- [x] Pipeline unit tests — canonical selection scoring logic (11 tests)
- [ ] Frontend smoke tests — basic render tests for key pages

### Performance
- [x] Cache MI network endpoint — in-memory cache with 5-minute TTL
- [ ] Add DB indexes on `edges(src_ott_id, dst_ott_id)` if not already present
- [x] Paginate children for large taxa — inline limit of 100, dedicated `/taxa/{id}/children` endpoint with offset/limit

## Medium Priority

### Frontend Polish
- [x] Add `getSequences()` to frontend API client
- [x] Sequence viewer page — color-coded DNA bases, composition bar, expandable cards
- [x] Mobile responsive layout — breakpoints at 768px and 480px
- [x] Loading skeletons — shimmer animation for taxon detail and graph pages
- [x] Graph page: node search/filter within the MI network — autocomplete dropdown with camera animation

### Data Quality
- [ ] Run `validate.py` and document results — what % of neighbors share genus/family?
- [ ] Flag taxonomic outliers — species whose MI neighbors are in different families
- [ ] Deduplicate sequences — check for identical accessions from multiple sources

### DevOps
- [x] Add Dockerfile health checks — API (Python urllib), Web (Node fetch), DB (pg_isready), Redis (redis-cli ping)
- [x] CI pipeline (GitHub Actions) — lint, typecheck, test, build
- [x] Fix lint warnings — removed unused imports, fixed f-string, removed unused variable
- [ ] Production deployment config (fly.io, Railway, or VPS)

## Phase 2 (from ROADMAP.md)

### Scale Across Animalia
- [ ] Make `SCOPE_OTT_ROOT` configurable — support Mammalia, Chordata, etc.
- [ ] k-mer candidate filtering — replace family-scoped search with ANN index (FAISS/Annoy) for cross-family neighbor detection
- [ ] Job queue — replace one-shot scripts with Celery/RQ for background pipeline jobs
- [ ] Precompute subtree graph exports for common entry points

### Multi-Marker Support (Phase 3)
- [ ] Add 16S, 18S marker ingestion
- [ ] Typed edges: `Edge(marker="COI", method="mi_alignment")`
- [ ] Composite distance: weighted sum across markers
