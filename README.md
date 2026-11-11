# Nevis Search API

Search API across clients and their documents: substring/fuzzy matching on client fields and
semantic (Sentence-BERT) search over document content.

> Work in progress — full setup instructions and examples will be added.

## Quick start

```bash
cp .env.example .env
docker compose up --build
```

- API: http://localhost:8000
- Swagger UI: http://localhost:8000/docs

## Tests

```bash
docker compose --profile test run --rm tests
```
