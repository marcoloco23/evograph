# EvoGraph

Explore the evolutionary tree of life through mutual information similarity graphs. EvoGraph builds a k-nearest-neighbor graph from COI barcode sequences, connecting species by genetic similarity rather than just taxonomy.

**Current scope:** Aves (birds) — 27,853 taxa, 167 species with COI barcodes, 1,787 MI edges.

## Architecture

```
apps/
  api/     FastAPI + SQLAlchemy 2.0 + PostgreSQL
  web/     Next.js 15 + Cytoscape.js / Sigma.js
data/
  raw/     Downloaded sequences (gitignored)
  processed/  Exported graph JSON (gitignored)
```

**Backend** serves a REST API with taxonomy, sequence, and graph endpoints. **Frontend** renders an interactive graph explorer and taxon detail pages with images, breadcrumbs, and MI neighbor cards.

## Quick Start

### With Docker (recommended)

```bash
cp .env.example .env
make up            # starts postgres, redis, api, web
make migrate       # run DB migrations
```

Then run the pipeline:
```bash
make ingest_ott    # load Aves taxonomy from OpenTree
make ingest_bold   # fetch COI sequences from NCBI
make canonical     # select best sequence per species
make neighbors     # compute MI distances, build kNN graph
make export        # export graph JSON for frontend
make validate      # check neighbor quality
```

### Local Development (without Docker)

**Prerequisites:** Python 3.12 (not 3.13 — breaks parasail), Node.js 18+, PostgreSQL 16.

```bash
# Database
docker compose up db -d

# API
cd apps/api/src
conda create -n evograph python=3.12
conda activate evograph
pip install -e ".[dev]"
uvicorn evograph.main:app --port 8000 --reload

# Frontend
cd apps/web
npm install
npm run dev
```

Pipeline scripts run standalone:
```bash
cd apps/api/src
python -m evograph.pipeline.ingest_ott
python -m evograph.pipeline.ingest_ncbi
python -m evograph.pipeline.select_canonical
python -m evograph.pipeline.build_neighbors
python -m evograph.pipeline.build_graph_export
python -m evograph.pipeline.ingest_images   # fetch Wikimedia thumbnails
python -m evograph.pipeline.validate
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/v1/search?q=corvus&limit=20` | Search taxa by name |
| GET | `/v1/taxa/{ott_id}` | Taxon detail with children, lineage, image |
| GET | `/v1/taxa/{ott_id}/sequences` | COI sequences for a taxon |
| GET | `/v1/graph/subtree/{ott_id}?depth=2` | Subtree with taxonomy + MI edges |
| GET | `/v1/graph/mi-network` | Full MI similarity network |
| GET | `/v1/graph/neighbors/{ott_id}?k=15` | k nearest neighbors by MI distance |
| GET | `/health` | Health check |

## How It Works

1. **Taxonomy backbone** from [Open Tree of Life](https://opentreeoflife.github.io/) — provides the hierarchical tree structure
2. **COI barcode sequences** from NCBI GenBank (BOLD portal is currently down) — one canonical sequence per species
3. **Global alignment** using parasail (Needleman-Wunsch, SIMD-accelerated)
4. **Mutual information** computed on aligned columns — measures shared information between paired bases
5. **Distance metric:** `d = 1 - NMI` where NMI = MI / min(H(X), H(Y))
6. **kNN graph:** each species connects to its 15 nearest neighbors within the same family

The MI distance is a **similarity proxy**, not a phylogenetic reconstruction. It measures how much aligned sequences share, which correlates with evolutionary relatedness but is not a substitution model.

## Data Sources

| Source | What | API |
|--------|------|-----|
| [Open Tree of Life](https://opentreeoflife.github.io/) | Taxonomy backbone | v3 REST API |
| [NCBI GenBank](https://www.ncbi.nlm.nih.gov/genbank/) | COI sequences | E-utilities |
| [Wikimedia Commons](https://en.wikipedia.org/api/rest_v1/) | Species images | REST API (no auth) |

## Tech Stack

- **Python 3.12**, FastAPI, SQLAlchemy 2.0, psycopg3, parasail, httpx
- **Next.js 15**, TypeScript, Cytoscape.js (small graphs), Sigma.js (large networks)
- **PostgreSQL 16**, Alembic migrations
- **Docker Compose** for local development

## Project Structure

```
apps/api/src/evograph/
  main.py                    # FastAPI app
  settings.py                # Configuration
  db/
    models.py                # Taxon, Sequence, Edge, NodeMedia
    session.py               # DB engine + session
    migrations/              # Alembic
  api/
    routes/                  # search, taxa, sequences, graph
    schemas/                 # Pydantic models
  services/
    ott_client.py            # OpenTree API client
    bold_client.py           # BOLD API client
    mi_distance.py           # MI computation
    neighbor_index.py        # Family-scoped candidate selection
  pipeline/
    ingest_ott.py            # Step 1: taxonomy
    ingest_ncbi.py           # Step 2: sequences (NCBI fallback)
    ingest_bold.py           # Step 2: sequences (BOLD)
    select_canonical.py      # Step 3: pick best per species
    build_neighbors.py       # Step 4: MI kNN graph
    build_graph_export.py    # Step 5: JSON export
    ingest_images.py         # Optional: Wikimedia thumbnails
    validate.py              # Quality checks
  utils/
    alignment.py             # parasail wrapper
    fasta.py                 # FASTA parser

apps/web/src/
  app/
    page.tsx                 # Home: search + quick links
    graph/page.tsx           # MI network explorer
    taxa/[ottId]/page.tsx    # Taxon detail
  components/
    SearchBox.tsx            # Autocomplete search
    GraphView.tsx            # Cytoscape renderer
    GraphViewSigma.tsx       # Sigma renderer (large graphs)
    TaxonCard.tsx            # Taxon summary card
  lib/
    api.ts                   # API client
    types.ts                 # TypeScript interfaces
    external-links.ts        # Wikipedia, iNaturalist, eBird URLs
```

## License

MIT
