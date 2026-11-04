# Database migrations

The application schema is managed with Alembic. Migrations use the configured
`DATABASE_URL`, or the PostgreSQL settings loaded by the application when
`DATABASE_URL` is not set.

Set `POSTGRES_PASSWORD` explicitly before starting Compose. Production and
staging application configuration fails closed when the password is missing;
the development-only fallback exists solely for local non-Compose workflows.

## New database

After configuring the database connection, apply all migrations:

```powershell
.\env\Scripts\python.exe -m alembic upgrade head
```

This creates the `documents` and `bookings` tables, the booking status check
constraint, the active interview-slot partial unique index, and Alembic's
`alembic_version` table.

## Existing database

Do not run `upgrade head` against an existing application database that was
created with `Base.metadata.create_all()` unless the schema has been verified
to match the migration baseline. The initial migration creates tables and is
intended for a fresh database.

After independently verifying that the existing schema matches the baseline,
stamp it without recreating or deleting tables:

```powershell
.\env\Scripts\python.exe -m alembic stamp head
```

The stamp command adds only the Alembic version marker. Back up and verify the
database before stamping it. Future migrations should be applied with:

```powershell
.\env\Scripts\python.exe -m alembic upgrade head
```

Migration tests use isolated SQLite databases and never modify the configured
application database.

## Docker Compose

Build and start the application and its PostgreSQL, Redis, and Qdrant
dependencies:

```powershell
docker compose up -d --build
```

Ollama is intentionally external to the default Compose stack because its
model storage and runtime requirements vary by host. On Docker Desktop,
`OLLAMA_BASE_URL` defaults to `http://host.docker.internal:11434`; set it
explicitly when Ollama runs elsewhere.

For a fresh Compose database, run the migration from the application
container:

```powershell
docker compose run --rm app python -m alembic upgrade head
```

Do not run that command against the existing database until its schema has
been verified and stamped as described above.
