# Security Audit

Audit timestamp: 2026-11-03T23:45:53+05:45

No critical or high-severity exploitable vulnerability was demonstrated in the
executed tests. Findings below are configuration or defense-in-depth issues
with reproducible evidence.

| Finding ID | Severity | Affected component | Evidence | Reproduction | Recommended correction | Status |
|---|---|---|---|---|---|---|
| SEC-001 | MEDIUM | `docker-compose.yml`, `app/database.py` | Development password fallback was available without an environment guard | Production/staging configuration without `POSTGRES_PASSWORD` now raises a configuration error; Compose requires explicit interpolation | Require a secret in non-development deployments and fail closed when absent | Resolved in Phase 5; 10 targeted and 194 full-suite tests passed |
| SEC-002 | MEDIUM | `app/services/vector_store.py` | Qdrant address was hardcoded to `http://localhost:6333` | Run the API in a container while Qdrant is a separate Compose service; localhost points at the API container | Read a validated Qdrant URL from environment/configuration | Resolved in Phase 1; 16 targeted and 183 full-suite tests passed |
| SEC-003 | LOW | `app/main.py` | Legacy health endpoint reports healthy even when dependencies are unavailable | Stop a required dependency and request `/health`; legacy implementation remains static | Implement separate liveness and dependency readiness endpoints | Resolved in Phase 3; `/health/ready` now checks all required services |
| SEC-004 | LOW | API routes | No authentication or authorization layer was registered | `/api/v1` routes now require configured `X-API-Key`; health and docs remain public by approved scope | Use the configured API key for trusted clients; replace with a full identity system only if product requirements expand | Resolved in Phase 6; 4 targeted and 198 full-suite tests passed |

Positive controls observed:

- Upload size is capped at 10 MiB and only PDF/TXT extensions are accepted.
- SQLAlchemy parameterization is used for database queries.
- Booking details are validated with Pydantic and explicit confirmation is
  required before persistence.
- RAG prompts identify retrieved documents as untrusted input.
- Client-facing infrastructure errors use generic messages rather than
  returning exception text or stack traces.

No secrets, tokens, or credentials were included in this report.

## Remediation history

- 2026-11-03T23:56:06+05:45: SEC-002/REL-002 remediated by adding
  validated `QDRANT_URL` configuration and wiring the vector store to the
  setting. The local development default remains unchanged.
- 2026-11-04T00:01:58+05:45: SEC-003/REL-001 remediated with separate
  liveness/readiness endpoints and bounded dependency checks. No internal
  exception details are returned.

- 2026-11-04T00:05:15+05:45: Container deployment was added with service-name
  networking and external Ollama configuration. Secret defaults remain open
  for the later secret-configuration phase.
- 2026-11-04T06:26:04+05:45: SEC-004 resolved with approved minimal
  `X-API-Key` protection on `/api/v1`. Health and documentation endpoints
  remain public; no API key values are recorded.
- 2026-11-04T08:00:00+05:45: Phase 7 runtime verification confirmed that
  API-key rejection and acceptance work through the Dockerized application.
  A temporary key was supplied only through the process environment and was
  not recorded.
