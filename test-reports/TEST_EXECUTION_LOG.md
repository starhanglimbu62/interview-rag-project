# Test Execution Log

Historical entries are append-only for this audit.

| Timestamp | Test ID | Description | Status | Duration | Evidence |
|---|---|---|---|---|---|
| 2026-11-03T23:45:53+05:45 | BASELINE-001 | Existing pytest suite | PASS | 1.38s | 176 passed, 4 skipped |
| 2026-11-03T23:45:53+05:45 | INFRA-001 | PostgreSQL, Redis, Qdrant, and Ollama connectivity | PASS | <1m | Live TCP/HTTP probes; SQLAlchemy connection |
| 2026-11-03T23:45:53+05:45 | MODEL-001 | Configured Ollama model availability | PASS | <1m | `/api/tags` contained `qwen3:1.7b` |
| 2026-11-03T23:45:53+05:45 | MODEL-002 | Embedding model load and vector dimension | PASS | <1m | 384-dimensional vector generated |
| 2026-11-03T23:45:53+05:45 | API-001 | Root, health, docs, and OpenAPI endpoints | PASS | <1s | All returned HTTP 200 |
| 2026-11-03T23:45:53+05:45 | INGEST-001 | Live TXT upload and recursive chunking | PASS | <1m | HTTP 200; metadata and vector cleanup completed |
| 2026-11-03T23:45:53+05:45 | INGEST-002 | Live PDF upload and extraction | PASS | <1m | HTTP 200; one page reported; cleanup completed |
| 2026-11-03T23:45:53+05:45 | RAG-001 | Grounded answer with source metadata | PASS | <1m | HTTP 200; expected fact and Qdrant sources |
| 2026-11-03T23:45:53+05:45 | RAG-002 | History-aware follow-up | PASS | <1m | HTTP 200; expected timezone answer |
| 2026-11-03T23:45:53+05:45 | BOOK-001 | Ollama extraction and confirmation workflow | PASS | <1m | Awaiting confirmation then persisted booking |
| 2026-11-03T23:45:53+05:45 | API-002 | Invalid extension, empty, oversized, UUID, extra field, missing state | PASS | <1s | 400/413/422 responses matched expectations |
| 2026-11-03T23:56:06+05:45 | PHASE1-001 | Qdrant URL configuration and validation tests | PASS | 0.18s | 16 passed |
| 2026-11-03T23:56:06+05:45 | PHASE1-002 | Full regression suite after Qdrant remediation | PASS | 1.48s | 183 passed, 4 skipped |
| 2026-11-03T23:58:56+05:45 | PHASE2-001 | Fresh isolated Alembic upgrade and existing-schema stamp | PASS | 0.36s | 2 passed |
| 2026-11-03T23:58:56+05:45 | PHASE2-002 | Read-only live PostgreSQL schema inspection | PASS | <1s | Existing documents/bookings schema and indexes inspected; no writes |
| 2026-11-03T23:58:56+05:45 | PHASE2-003 | Full regression suite after migration changes | PASS | 1.57s | 185 passed, 4 skipped |
| 2026-11-04T00:01:58+05:45 | PHASE3-001 | Health and readiness regression tests | PASS | 0.61s | 5 passed |
| 2026-11-04T00:01:58+05:45 | PHASE3-002 | Configuration plus health regression tests | PASS | 0.61s | 11 passed |
| 2026-11-04T00:01:58+05:45 | PHASE3-003 | Full regression suite after readiness changes | PASS | 6.05s | 190 passed, 4 skipped |
| 2026-11-04T00:01:58+05:45 | PHASE3-004 | Live liveness and readiness endpoints | PASS | 4.4s | Both HTTP 200; all dependencies `ok` |
| 2026-11-04T00:05:15+05:45 | PHASE4-001 | Docker Compose configuration validation | PASS | <1s | `docker compose config` succeeded |
| 2026-11-04T00:05:15+05:45 | PHASE4-002 | Full regression suite after Compose changes | PASS | 5.75s | 190 passed, 4 skipped |
| 2026-11-04T00:05:15+05:45 | PHASE4-003 | Dependency container health inspection | PASS | <1s | Existing PostgreSQL and Redis healthy; Qdrant state inspected |
| 2026-11-04T00:05:15+05:45 | PHASE4-004 | FastAPI Docker image build | BLOCKED | >9m | Dependency installation exceeded verification window; command stopped |
| 2026-11-04T00:22:59+05:45 | PHASE5-001 | Secret/configuration regression tests | PASS | 0.29s | 10 passed |
| 2026-11-04T00:22:59+05:45 | PHASE5-002 | Compose validation with explicit password | PASS | <1s | `docker compose config --quiet` succeeded |
| 2026-11-04T00:22:59+05:45 | PHASE5-003 | Full regression suite after secret changes | PASS | 6.05s | 194 passed, 4 skipped |
| 2026-11-04T06:26:04+05:45 | PHASE6-001 | API-key authentication regression tests | PASS | 0.32s | 4 passed |
| 2026-11-04T06:26:04+05:45 | PHASE6-002 | Final full regression suite after authentication | PASS | 4.95s | 198 passed, 4 skipped |
| 2026-11-04T06:31:02+05:45 | FINAL-001 | Final full regression suite | PASS | 4.23s | 198 passed, 4 skipped |
| 2026-11-04T06:31:02+05:45 | FINAL-002 | Final Docker Compose validation | PASS | <1s | `docker compose config --quiet` succeeded |
| 2026-11-04T06:31:02+05:45 | FINAL-003 | Final live readiness verification | PASS | <1s | Liveness/readiness HTTP 200; all dependencies `ok` |
| 2026-11-04T06:31:02+05:45 | FINAL-004 | Docker application image build | BLOCKED | >9m | Dependency installation exceeded verification window |
| 2026-11-04T08:00:00+05:45 | PHASE7-001 | CPU-only Docker application image build | PASS | 9m 10s | `docker compose build app`; image `interview-rag-problem-app` created |
| 2026-11-04T08:00:00+05:45 | PHASE7-002 | Compose runtime startup and service health | PASS | <2m | App, PostgreSQL, Redis, and Qdrant healthy; no destructive commands |
| 2026-11-04T08:00:00+05:45 | PHASE7-003 | In-container dependency connectivity | PASS | <1m | SQLAlchemy PostgreSQL, Redis ping, Qdrant HTTP, and Ollama HTTP checks passed |
| 2026-11-04T08:00:00+05:45 | PHASE7-004 | Docker health endpoints | PASS | <1m | External and in-container readiness HTTP 200; all dependencies `ok` |
| 2026-11-04T08:00:00+05:45 | PHASE7-005 | Dockerized auth and application workflows | PASS | <15m | Auth rejection, TXT/PDF upload, invalid extension, grounded RAG, and follow-up passed |
| 2026-11-04T08:00:00+05:45 | PHASE7-006 | App restart persistence | PASS | <2m | PostgreSQL metadata, Qdrant vectors, and Redis conversation survived app restart |
| 2026-11-04T08:00:00+05:45 | PHASE7-007 | Final regression and Compose checks | PASS | 11.25s | 198 passed, 4 skipped; Compose config and `git diff --check` passed |
| 2026-11-04T08:00:00+05:45 | PHASE7-008 | Host default pytest command | BLOCKED | <1s | System Python had no pytest; repository environment command used successfully |

Exact commands:

```text
.\env\Scripts\python.exe -m pytest tests/ -v
.\env\Scripts\python.exe -m pytest tests/ -q --tb=short
docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}"
docker compose build app
docker compose up -d app
docker compose config --quiet
.\env\Scripts\python.exe -m pytest tests/ -v
git diff --check
```
