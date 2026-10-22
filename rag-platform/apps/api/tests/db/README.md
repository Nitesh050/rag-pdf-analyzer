# Schema checks

`schema_checks.sql` tests the rules in `src/db/schema/`: constraints, triggers, cascades and pgvector search. It runs in a transaction that is rolled back, so it never leaves data behind.

From `apps/api`:

```
docker run --rm -d --name rag-schema-check -e POSTGRES_PASSWORD=check -e POSTGRES_DB=rag \
  -v "$PWD/src/db/schema:/docker-entrypoint-initdb.d:ro" pgvector/pgvector:pg16
# wait a few seconds for the schema to load, then:
docker exec -i rag-schema-check psql -U postgres -d rag -q -At < tests/db/schema_checks.sql
docker stop rag-schema-check
```

Every line should start with `ok`. A line starting with `FAIL` means a schema change broke a rule. Re-run this after any change to the schema files.

## Model tests

`test_models.py` checks the SQLAlchemy models against the same database: that each model matches its table, and that defaults, constraints, triggers and cascades behave as expected. Start the container with a published port, then:

```
docker run --rm -d --name rag-db-test -e POSTGRES_PASSWORD=check -e POSTGRES_DB=rag -p 5433:5432 \
  -v "$PWD/src/db/schema:/docker-entrypoint-initdb.d:ro" pgvector/pgvector:pg16
TEST_DATABASE_URL=postgresql+psycopg://postgres:check@localhost:5433/rag .venv/bin/python -m pytest tests/db
docker stop rag-db-test
```

Without `TEST_DATABASE_URL` (or with the database down) these tests are skipped, so `pytest` still runs without Docker.
