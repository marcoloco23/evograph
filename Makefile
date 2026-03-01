.PHONY: up down up-prod down-prod migrate ingest_ott ingest_ncbi ingest_bold canonical neighbors export images validate pipeline

up:
	docker compose up --build

down:
	docker compose down

up-prod:
	docker compose -f docker-compose.yml -f docker-compose.prod.yml up --build -d

down-prod:
	docker compose -f docker-compose.yml -f docker-compose.prod.yml down

migrate:
	docker compose exec api alembic upgrade head

ingest_ott:
	docker compose exec api python -m evograph.pipeline.ingest_ott

ingest_ncbi:
	docker compose exec api python -m evograph.pipeline.ingest_ncbi

ingest_bold:
	docker compose exec api python -m evograph.pipeline.ingest_bold

canonical:
	docker compose exec api python -m evograph.pipeline.select_canonical

neighbors:
	docker compose exec api python -m evograph.pipeline.build_neighbors

export:
	docker compose exec api python -m evograph.pipeline.build_graph_export

images:
	docker compose exec api python -m evograph.pipeline.ingest_images

validate:
	docker compose exec api python -m evograph.pipeline.validate

pipeline: ingest_ott ingest_ncbi canonical neighbors export images validate
