.PHONY: up down migrate ingest_ott ingest_bold canonical neighbors export validate

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

validate:
	docker compose exec api python -m evograph.pipeline.validate
