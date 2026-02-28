# EvoGraph — Next Tasks

## High Priority

### Sequence Coverage
- [ ] Expand NCBI ingestion — current query finds only 167/18,805 species. Try broader search terms, search by genus when species fails, increase `--per-species` limit
- [ ] Retry BOLD portal — `portal.boldsystems.org` has been down since Feb 2026. Check periodically; when it returns, `ingest_bold.py` is ready
- [ ] Add NCBI taxonomy ID lookup — `ncbi_tax_id` column exists but is never populated. Add pipeline step to query NCBI Taxonomy by name and backfill

### Testing
- [ ] API route tests — pytest + httpx TestClient for all 6 endpoints
- [ ] Pipeline unit tests — test MI computation with known sequences, test canonical selection logic
- [ ] Frontend smoke tests — basic render tests for key pages

### Performance
- [ ] Cache MI network endpoint — the full graph loads all edges every request. Add Redis or in-memory caching with TTL
- [ ] Add DB indexes on `edges(src_ott_id, dst_ott_id)` if not already present
- [ ] Paginate children for large taxa (Aves has 729 direct children)

## Medium Priority

### Frontend Polish
- [ ] Add `getSequences()` to frontend API client — endpoint exists but no client function
- [ ] Sequence viewer page — show aligned sequences for a species, highlight conserved regions
- [ ] Mobile responsive layout — test and fix breakpoints
- [ ] Loading skeletons instead of plain "Loading..." text
- [ ] Graph page: add node search/filter within the MI network

### Data Quality
- [ ] Run `validate.py` and document results — what % of neighbors share genus/family?
- [ ] Flag taxonomic outliers — species whose MI neighbors are in different families
- [ ] Deduplicate sequences — check for identical accessions from multiple sources

### DevOps
- [ ] Add Dockerfile health checks
- [ ] CI pipeline (GitHub Actions) — lint, typecheck, test
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
