# Interview RAG Backend

A FastAPI backend for document ingestion, semantic search, conversational RAG,
and interview booking.

## What it does

- Accepts `.txt` and `.pdf` documents.
- Extracts text and creates chunks.
- Generates embeddings with `all-MiniLM-L6-v2`.
- Stores vectors in Qdrant.
- Stores document and booking metadata in PostgreSQL.
- Uses Redis for conversation memory.
- Uses Ollama for locally hosted language-model responses.
- Provides dependency-aware health and readiness endpoints.

## Technology

- Python 3.14+
- FastAPI and Uvicorn
- PostgreSQL and SQLAlchemy
- Alembic migrations
- Qdrant vector database
- Redis
- Ollama
- Sentence Transformers

## Quick start with Docker

### 1. Configure environment variables

Copy the example environment file:

```powershell
Copy-Item .env.example .env
```

Set a real `POSTGRES_PASSWORD` in `.env`. For protected API routes, also set
an `API_KEY`.

Ollama runs outside the default Compose stack. Install Ollama on the host and
make sure the configured model is available:

```powershell
ollama pull qwen3:1.7b
```

### 2. Start the services

```powershell
docker compose up -d --build
```

The API is available at:

```text
http://localhost:8000
```

### 3. Run database migrations

For a fresh database:

```powershell
docker compose run --rm app python -m alembic upgrade head
```

Do not run this against an existing database until its schema has been
verified. See [MIGRATIONS.md](MIGRATIONS.md) for the safe existing-database
procedure.

## Local setup

Create and activate a virtual environment, then install dependencies:

```powershell
python -m venv env
.\env\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Set `DATABASE_URL`, `REDIS_URL`, `QDRANT_URL`, and `OLLAMA_BASE_URL` for the
services running on your machine. Start the API with:

```powershell
python -m uvicorn app.main:app --reload
```

## API endpoints

Public endpoints:

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/` | Basic service response |
| GET | `/health` | Legacy health endpoint |
| GET | `/health/live` | Process liveness |
| GET | `/health/ready` | PostgreSQL, Redis, Qdrant, and Ollama readiness |
| GET | `/docs` | Swagger API documentation |

API routes are under `/api/v1`:

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/api/v1/documents/upload` | Upload a TXT or PDF document |
| POST | `/api/v1/chat` | Ask a question about uploaded documents |
| POST | `/api/v1/bookings` | Create or manage an interview booking |

When `API_KEY` is configured, send it with:

```text
X-API-Key: your-api-key
```

Example document upload:

```powershell
curl.exe -H "X-API-Key: your-api-key" `
  -F "file=@document.txt" `
  http://localhost:8000/api/v1/documents/upload
```

Example RAG request:

```powershell
curl.exe -X POST http://localhost:8000/api/v1/chat `
  -H "Content-Type: application/json" `
  -H "X-API-Key: your-api-key" `
  -d '{\"question\":\"What does the document say?\"}'
```

## Configuration

| Variable | Description | Development default |
|---|---|---|
| `APP_ENV` | Environment name | `development` |
| `API_KEY` | API key for `/api/v1` routes | Unset |
| `DATABASE_URL` | PostgreSQL connection URL | Application-specific |
| `REDIS_URL` | Redis connection URL | `redis://localhost:6379/0` |
| `QDRANT_URL` | Qdrant HTTP URL | `http://localhost:6333` |
| `OLLAMA_BASE_URL` | Ollama HTTP URL | `http://localhost:11434` |
| `OLLAMA_MODEL` | Ollama model name | `qwen3:1.7b` |

Production and staging deployments require explicit database and API secrets.
Do not commit `.env` or real credentials.

## Testing

Run the complete test suite from the repository virtual environment:

```powershell
.\env\Scripts\python.exe -m pytest tests/ -v
```

The test suite includes unit tests for configuration, authentication,
document processing, vector storage, health checks, migrations, bookings, and
conversation memory.

## Project structure

```text
.
├── app/
│   ├── routes/          API route handlers
│   ├── services/        RAG, embedding, storage, and booking services
│   ├── models/          SQLAlchemy models
│   └── schemas/         Pydantic request and response schemas
├── alembic/             Database migration files
├── tests/               Automated tests
├── test-reports/        Integration and verification reports
├── Dockerfile
├── docker-compose.yml
├── MIGRATIONS.md
└── requirements.txt
```

## Verification

The Docker deployment has been verified for:

- Successful application image build.
- Compose startup and service health.
- In-container PostgreSQL, Redis, Qdrant, and Ollama connectivity.
- TXT and PDF ingestion.
- Authenticated RAG requests with source metadata.
- Redis conversation follow-up.
- Persistence after restarting the FastAPI container.

## Author

[Starhang Limbu](https://github.com/starhanglimbu62)
