# Integration Test and Reliability Audit

## Project and environment

- Project: Interview RAG Backend
- Audit timestamp: 2026-11-03T23:45:53+05:45
- Platform: Windows
- Python: 3.14.6
- Test runner: pytest 9.2.0
- Git branch: `main`
- Working tree: already contained uncommitted booking-related changes before this audit

## Scope and method

The audit covered repository inspection, the existing test suite, live service
connectivity, isolated live API calls, document ingestion, Qdrant retrieval,
Ollama generation, Redis conversation memory, booking confirmation, API
validation, and Docker/deployment configuration. Live records used unique
identifiers and were removed after the probes.

## Infrastructure status

| Service | Result | Evidence |
|---|---|---|
| FastAPI import and health/docs | PASS | `/`, `/health`, `/docs`, and `/openapi.json` returned 200 |
| PostgreSQL | PASS | Application SQLAlchemy engine connected as `raguser`; tables were readable |
| Redis | PASS | Isolated set/get/TTL/delete probe passed |
| Qdrant | PASS | `/healthz` returned 200; `document_chunks` was accessible |
| Ollama | PASS | `/api/tags` returned the configured `qwen3:1.7b` model |
| Embeddings | PASS | `all-MiniLM-L6-v2` loaded and generated 384-dimensional vectors |

## Test execution summary

- Baseline command: `python -m pytest tests/ -v`
- Actual command: `.\env\Scripts\python.exe -m pytest tests/ -v`
- Result: **176 passed, 4 skipped, 0 failed**, in 1.38 seconds
- Live API validation: 6 cases executed; all returned the expected validation/error status
- Live end-to-end probe: 2 uploads, 2 chat turns, and 2 booking turns passed
- Phase 1 remediation changed only Qdrant configuration and its regression
  tests; no unrelated business logic was changed.

## Phase 1 remediation retest

The Qdrant configuration remediation was implemented after the original audit:

- Added validated `QDRANT_URL` configuration with the existing localhost
  development default.
- Removed the vector-store hardcoded URL.
- Added Compose-hostname and invalid-URL configuration tests.
- Added a vector-store test proving the configured URL is passed to the
  Qdrant client.

Retest results:

- Targeted command: `.\env\Scripts\python.exe -m pytest tests/test_config.py tests/test_vector_store.py -v`
- Result: **16 passed**
- Full command: `.\env\Scripts\python.exe -m pytest tests/ -v`
- Result: **183 passed, 4 skipped, 0 failed**, in 1.48 seconds

## Phase 2 migration remediation

Alembic was introduced with an initial migration for the modeled `documents`
and `bookings` tables, including all columns, the booking status check
constraint, and the partial unique interview-slot index. The migration
configuration uses the application's database URL without changing the
existing database.

Verification:

- Fresh isolated SQLite upgrade: **PASS**
- Isolated pre-existing schema stamp: **PASS**; existing tables were not
  recreated or dropped
- Live PostgreSQL schema inspection: **PASS**; existing tables and indexes were
  read only, and no `alembic_version` table was added
- Full suite after migration changes: **185 passed, 4 skipped, 0 failed**, in
  1.57 seconds

Existing databases must be verified against the baseline before running
`alembic stamp head`; this audit intentionally did not stamp the user's live
database.

## Phase 3 health and readiness remediation

Added:

- `/health/live` for process liveness.
- `/health/ready` for PostgreSQL, Redis, Qdrant, and configured Ollama model
  checks.
- Per-dependency bounded checks with generic `ok`/`unavailable` statuses.
- HTTP 503 readiness responses when any dependency fails or times out.
- `HEALTH_TIMEOUT_SECONDS`, defaulting to 5 seconds.
- Regression tests for healthy readiness, dependency failure, timeout, legacy
  `/health` compatibility, and error-message non-disclosure.

The first live readiness probe with a 2-second bound timed out on Redis and
Ollama, although both checks passed individually just over that threshold.
The bound was adjusted to 5 seconds; the final live probe returned HTTP 200
with all dependencies `ok`.

Final Phase 3 verification:

- Health tests: **5 passed**
- Configuration plus health tests: **11 passed**
- Full suite: **190 passed, 4 skipped, 0 failed**, in 6.05 seconds
- Live `/health/live`: **200**
- Live `/health/ready`: **200**, PostgreSQL/Redis/Qdrant/Ollama all `ok`

## Phase 4 Docker Compose remediation

Added a FastAPI application service with a Dockerfile, persistent dependency
volumes, dependency health ordering, a Qdrant healthcheck, and container-safe
service URLs:

- PostgreSQL: `postgres`
- Redis: `redis`
- Qdrant: `qdrant`
- Ollama: external by default through Docker Desktop's
  `host.docker.internal`

Ollama was intentionally not added as a Compose container because its model
runtime/storage requirements are host- and platform-dependent. Migration
commands are documented separately and are not run automatically, protecting
the existing database.

Verification:

- `docker compose config`: **PASS**
- Full pytest suite: **190 passed, 4 skipped, 0 failed**
- Existing PostgreSQL, Redis, and Qdrant container health: **PASS**
- Application image build: **BLOCKED** during dependency installation after
  exceeding the verification window; no image success is claimed
- No containers, volumes, or existing data were recreated or deleted

## Integration results

### Document ingestion

PASS. A unique TXT and PDF were uploaded through `/api/v1/documents/upload`.
Both used recursive chunking, persisted metadata, generated embeddings, and
stored vectors in Qdrant. The PDF reported one page and the configured vector
dimension was 384. Invalid extension, empty file, and 10 MB-plus file probes
returned 400, 400, and 413 respectively.

### RAG and generation

PASS. A known fact in the isolated TXT document was retrieved and returned by
Ollama with source metadata. A follow-up question reused Redis history and
returned the expected timezone fact. The RAG system prompt explicitly treats
retrieved content as untrusted data and preserves the current question in the
generation message.

### Redis conversation memory

PASS for the exercised path. A conversation ID was generated, two turns were
stored, and the follow-up used the same conversation. Redis TTL was observed
on an isolated key. Existing unit tests cover history limits, malformed
history, and service failure handling.

### Booking workflow

PASS for the exercised happy path. Ollama extracted a synthetic candidate,
email, and unique future timestamp; the API returned `awaiting_confirmation`,
then persisted a confirmed booking only after explicit confirmation. The
created booking and Redis state were cleaned up.

### API reliability

PASS for exercised validation cases. Invalid UUIDs and unexpected fields
returned 422; confirmation without state returned 422; service errors are
mapped to generic 503/500 responses by the routes. OpenAPI documentation was
available.

## Security findings

See [SECURITY_AUDIT.md](./SECURITY_AUDIT.md). No critical or high-confidence
exploitable issue was demonstrated during the live probes. Configuration and
deployment weaknesses remain unresolved.

## Docker and deployment results

The PostgreSQL, Redis, and Qdrant containers were running and healthy enough
for the probes. However, `docker-compose.yml` does not declare the FastAPI
application or Ollama service, has no Qdrant healthcheck, and the application
requires the new `QDRANT_URL` setting to use the Qdrant service hostname. A fresh compose-only
deployment therefore does not satisfy the documented full-stack startup
requirement. No destructive Docker commands were run.

## Known limitations and unresolved issues

1. No README or documented startup procedure exists in the repository.
2. Alembic migrations now initialize fresh databases. The live database remains
   unstamped by design and requires an operator-verified `alembic stamp head`
   before future upgrades.
3. `/health` remains a legacy static endpoint; dependency-aware readiness is
   available at `/health/ready`.
4. Qdrant URL configuration is now supported through `QDRANT_URL`.
5. Ollama is available locally but absent from Compose.
6. Concurrent booking behavior was not load-tested; the database unique index
   is the protection observed in code.

## Final readiness assessment

**PASS WITH LIMITATIONS** — Core live ingestion, retrieval, memory, and booking
paths passed, and Qdrant configuration is remediated. Secret hardening remains unresolved. Application image build and in-container
connectivity require a follow-up run with sufficient build time. This is not a
full production-readiness approval.

## Phase 5 secret configuration remediation

Database secret handling now:

- Requires an explicit `POSTGRES_PASSWORD` in production and staging.
- Retains the existing password fallback only for local development imports.
- Requires `POSTGRES_PASSWORD` in Compose interpolation rather than silently
  selecting the development default.
- Documents placeholder-only configuration in `.env.example`.
- Adds regression tests for development fallback, production/staging failure,
  and explicit secret use.

Verification:

- Secret/config tests: **10 passed**
- Full suite: **194 passed, 4 skipped, 0 failed**, in 6.05 seconds
- Compose validation with explicit password: **PASS**
- No secret values were printed or added to repository files.
- The repository's existing `.env` defines a password, so missing-secret
  Compose rejection was not independently exercised without modifying that
  file.

Secret hardening is resolved for application configuration; authentication was
handled in Phase 6 with an approved minimal API-key scope.

## Phase 6 authentication assessment and implementation

The original assignment does not require authentication. The user approved a
minimal API-key implementation for internet-facing protection:

- `X-API-Key` protects every `/api/v1` route.
- `/health`, `/health/live`, `/health/ready`, and documentation remain public.
- Keys are supplied through `API_KEY`; comparison uses constant-time
  `hmac.compare_digest`.
- Development without a configured key remains compatible for local tests.
- Production, staging, and prod environments fail closed if `API_KEY` is
  missing.

Verification:

- Authentication tests: **4 passed**
- Final full suite: **198 passed, 4 skipped, 0 failed**, in 4.95 seconds
- `git diff --check`: **PASS**

Authentication is implemented with an explicit approved scope; no large
identity system or user database was introduced.

## Final verification

- Full pytest suite: **198 passed, 4 skipped, 0 failed**, in 4.23 seconds
- `docker compose config --quiet`: **PASS**
- Live `/health/live`: **200**
- Live `/health/ready`: **200**, with PostgreSQL, Qdrant, Redis, and Ollama
  all `ok`
- `git diff --check`: **PASS**
- Docker application image build: **BLOCKED** during the earlier verification
  window while installing the large sentence-transformers/PyTorch dependency
  stack; no successful image build is claimed

Resolved findings: REL-002, DEPLOY-002, REL-001, SEC-003, SEC-001, and
SEC-004. Remaining limitation: in-container application startup/connectivity
and image build require a longer dedicated Docker build run.

Final classification: **PASS WITH LIMITATIONS**

## Phase 7 Docker build and runtime verification

The application image was built using the existing architecture. The Dockerfile
now preinstalls the compatible CPU-only `torch==2.9.1+cpu` wheel before the
unchanged requirements, avoiding the CUDA/Triton dependency graph observed in
the initial build. The required 384-dimensional
`all-MiniLM-L6-v2` embedding model and application behavior were preserved.

Verification results:

- `docker compose build app`: **PASS**, 9m 10s; image created
- `docker compose up -d app`: **PASS**; no volumes or existing data were deleted
- Final Compose status: FastAPI, PostgreSQL, Redis, and Qdrant healthy
- In-container connectivity: **PASS** for PostgreSQL via SQLAlchemy, Redis via
  `PING`, Qdrant via `/healthz`, and external Ollama via `/api/tags`
- External and in-container `/health/live` and `/health/ready`: **PASS**;
  readiness returned HTTP 200 with all dependencies `ok`
- Authentication: missing and incorrect API keys rejected; temporary correct
  key accepted
- TXT and PDF ingestion: **PASS**; metadata persisted and 384-dimensional
  vectors stored
- Invalid extension: **PASS**; HTTP 400
- Grounded RAG: **PASS**; response included the expected fact and source
  metadata
- Conversation memory: **PASS** before and after app restart
- Persistence: PostgreSQL metadata and Qdrant vectors remained available after
  restarting only the FastAPI container
- Probe records, vectors, Redis keys, and temporary files were removed after
  verification; pre-existing data was not deleted
- Final suite: **198 passed, 4 skipped, 0 failed** in 11.25 seconds
- `docker compose config --quiet`: **PASS**
- `git diff --check`: **PASS**

The Qdrant healthcheck initially failed because `curl` is absent from the
Qdrant image. It was corrected to use the image's Bash HTTP probe and retested
successfully. The host default `python -m pytest` command was unavailable
because system Python lacked pytest; the repository environment command was
used and passed.

Final Phase 7 verdict: **PASS**
