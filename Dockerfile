FROM python:3.12-slim AS py-builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY pyproject.toml README.md /app/
COPY datanorma /app/datanorma
COPY alembic /app/alembic
COPY alembic.ini /app/alembic.ini
COPY dbt /app/dbt
RUN pip wheel --no-cache-dir --wheel-dir /tmp/wheels .

FROM node:20-alpine AS frontend-builder
ARG VITE_BASE=/ui/
ENV VITE_BASE=$VITE_BASE
WORKDIR /frontend
COPY client/package*.json /frontend/
RUN npm install
COPY client /frontend
RUN npm run build

FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY --from=py-builder /tmp/wheels /tmp/wheels
RUN pip install --no-cache-dir /tmp/wheels/*.whl && rm -rf /tmp/wheels

COPY pyproject.toml README.md /app/
COPY datanorma /app/datanorma
COPY alembic /app/alembic
COPY alembic.ini /app/alembic.ini
COPY dbt /app/dbt
COPY data/samples /app/data/samples
COPY dagster_workspace.yaml /app/dagster_workspace.yaml
COPY --from=frontend-builder /frontend/dist /app/client/dist
COPY docker/entrypoint.py /app/docker/entrypoint.py

EXPOSE 8080
ENTRYPOINT ["python", "/app/docker/entrypoint.py"]
CMD ["python", "-m", "datanorma.web", "--host", "0.0.0.0", "--port", "8080"]
