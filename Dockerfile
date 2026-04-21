# 1. Use consistent uppercase for FROM/AS to clear warnings
FROM python:3.13-slim AS base
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY runner/ .

FROM base AS test
COPY tests/requirements-dev.txt ./requirements-dev.txt
RUN pip install --no-cache-dir -r requirements-dev.txt

COPY tests/ ./tests/ 

ENV PYTHONPATH=/app

RUN python -m pytest tests/

FROM base AS final
ENTRYPOINT ["python", "main.py"]