# Failure Log

No application test failures were observed in the executed baseline or live
probes. The following unresolved audit failures are deployment/reliability
findings rather than failed runtime assertions.

| Failure ID | Timestamp | Component | Expected | Actual | Root cause | Fix | Retest |
|---|---|---|---|---|---|---|---|
| DEPLOY-001 | 2026-11-03T23:45:53+05:45 | Docker Compose | Full application stack startable from Compose | Compose declares only PostgreSQL, Redis, and Qdrant; Ollama and FastAPI are absent | Incomplete deployment definition | Add application/Ollama services or document external prerequisites | Not fixed; not retested |
| DEPLOY-002 | 2026-11-03T23:45:53+05:45 | Database initialization | Fresh database should initialize schema | Existing tables were present, but no migration or startup schema mechanism was found | Schema lifecycle was external/manual | Add migrations and a documented initialization path | Resolved in Phase 2; live database intentionally remains unstamped |
| REL-001 | 2026-11-03T23:45:53+05:45 | Health endpoint | Health should reflect required dependency readiness | `/health` returned `{"status":"healthy"}` without dependency checks | Static health implementation | Add liveness/readiness distinction and bounded dependency probes | Resolved in Phase 3; live `/health/ready` returned 200 |
| REL-002 | 2026-11-03T23:45:53+05:45 | Qdrant configuration | Container-safe configurable service address | `QDRANT_URL` was not read; `localhost:6333` was hardcoded | Missing configuration surface | Add a validated Qdrant URL setting | Resolved in Phase 1 |

No data belonging to other users was deleted. Audit-created documents,
vectors, booking, and Redis keys were cleaned up.

## Remediation history

| Failure ID | Fix timestamp | Fix | Retest result |
|---|---|---|---|
| REL-002 | 2026-11-03T23:56:06+05:45 | Added validated `QDRANT_URL` setting and wired `QdrantVectorStore` to it; documented the setting in `.env.example` | Targeted: 16 passed; full suite: 183 passed, 4 skipped |
| DEPLOY-002 | 2026-11-03T23:58:56+05:45 | Added Alembic baseline, fresh-upgrade and safe-stamp tests, and migration documentation | Migration tests: 2 passed; full suite: 185 passed, 4 skipped |
| REL-001 | 2026-11-04T00:01:58+05:45 | Added `/health/live`, dependency-aware `/health/ready`, bounded checks, generic failure responses, and regression tests | Health tests: 5 passed; full suite: 190 passed, 4 skipped; live readiness 200 |
| DEPLOY-001 | 2026-11-04T00:05:15+05:45 | Added FastAPI Compose service, Dockerfile, dependency health ordering, Qdrant healthcheck, service-name URLs, and external Ollama documentation | Compose config passed; full suite passed; image build blocked during large dependency installation |
| SEC-001 | 2026-11-04T00:22:59+05:45 | Added production/staging fail-closed password validation, required Compose interpolation, and placeholder-only example configuration | Secret tests: 10 passed; full suite: 194 passed, 4 skipped; Compose explicit-password validation passed |
| SEC-004 | 2026-11-04T06:26:04+05:45 | Added approved minimal `X-API-Key` protection for `/api/v1`, public health/docs, constant-time comparison, and production fail-closed behavior | Auth tests: 4 passed; full suite: 198 passed, 4 skipped |
| FINAL-001 | 2026-11-04T06:31:02+05:45 | Final verification completed | Full suite, Compose validation, readiness, and formatting passed; Docker image build remains blocked by dependency installation duration |
| PHASE7-BUILD | 2026-11-04T08:00:00+05:45 | Docker image build | Image must build within the verification run | Default install pulled CUDA/Triton PyTorch dependencies and stalled | Preinstall compatible CPU-only `torch==2.9.1+cpu` in Dockerfile | Build passed in 9m 10s |
| PHASE7-QDRANT-HEALTH | 2026-11-04T08:00:00+05:45 | Qdrant startup | Compose dependency healthcheck must pass | Qdrant image did not contain `curl` | Healthcheck assumed an unavailable executable | Use the image-provided Bash HTTP probe | Qdrant healthy; app started |
| PHASE7-TEST-ENV | 2026-11-04T08:00:00+05:45 | Host regression command | `python -m pytest tests/ -v` should execute | System Python had no pytest | Test dependencies are installed in repository `env` | Use `.\env\Scripts\python.exe -m pytest tests/ -v` | 198 passed, 4 skipped |
