FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml README.md /app/
COPY datanorma /app/datanorma
COPY alembic /app/alembic
COPY alembic.ini /app/alembic.ini
COPY dbt /app/dbt

RUN pip install --no-cache-dir -e .

EXPOSE 8000

CMD ["python", "-m", "datanorma.web"]
