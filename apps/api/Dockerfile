FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml .
RUN pip install --no-cache-dir .

COPY src/ src/
COPY alembic.ini .

ENV PYTHONPATH=/app/src
CMD ["uvicorn", "evograph.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
