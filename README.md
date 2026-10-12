# RetailPipeline

An ecommerce data platform: rows are extracted incrementally from an OLTP Postgres database,
validated, and modelled in DuckDB.

```
simulator -> Postgres OLTP -> bronze (raw Parquet) -> silver (validated Parquet) + rejects -> DuckDB
```

Currently covers users. Transactions (purchases, returns, discounts), Airflow and CI follow.

## Run it

```sh
uv sync --extra dev
cp .env.example .env                       # then set PGPASSWORD in .env
export UV_ENV_FILE=.env                    # makes `uv run` load it
docker compose up -d --wait oltp

uv run retail-pipeline simulate --days 3   # generate signups and profile changes in Postgres
uv run retail-pipeline run                 # extract -> ingest -> transform -> check
```

`run` is safe to repeat: with no new activity it extracts nothing and the warehouse is unchanged.
Output lands in `data/` (override with `RETAIL_DATA_DIR`); the database is set with `OLTP_DSN`.
Run `uv run retail-pipeline init-db` to create the tables in a Postgres that wasn't started by
Compose.

## Tests

```sh
uv run pytest                              # unit tests; integration tests skip
OLTP_DSN=postgresql://retail@localhost:5432/retail uv run pytest -m integration
```

Integration tests create and drop their own Postgres schema, so they don't touch simulated data.

## Security

- **No secrets in the repo.** The database password lives in `.env` (gitignored) as `PGPASSWORD`;
  code and Compose only reference it. Put a password in `OLTP_DSN` only via the environment.
- **Local database is loopback-only.** Compose publishes Postgres on `127.0.0.1`.
- **Extraction is read-only.** The pipeline opens the OLTP with `default_transaction_read_only`,
  so it cannot modify the application database. Only `simulate` and `init-db` write to it.
- **SQL is never built from input.** Values are bound parameters and table names come from a
  fixed allow-list.
- **Output contains personal data.** `data/` holds user emails (including raw rows in
  `rejects/`) and is gitignored; don't copy it into the repo or share it.
