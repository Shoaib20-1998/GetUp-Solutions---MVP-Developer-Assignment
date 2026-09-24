# Support Ticketing Portal

A customer support ticketing portal with AI-assisted triage. Customers raise tickets, agents work them to resolution, admins oversee the queue. This is a functional MVP built for a take-home assignment, not a production-hardened product -- see [Known limitations](#known-limitations) below.

## Stack

| Layer | Choice |
|---|---|
| Frontend | React + TypeScript (Vite) |
| Backend | FastAPI (Python) |
| Database | PostgreSQL |
| Auth | JWT, bcrypt-hashed passwords |
| AI | Google Gemini (free tier) with automatic fallback to a deterministic mock provider |
| Local run | Docker Compose |

## Running it

```bash
cp .env.example .env
# Generate a real JWT secret:
openssl rand -hex 32   # paste the output into JWT_SECRET in .env

docker compose up --build
```

This starts Postgres, the backend (`http://localhost:8000`, docs at `/docs`), and the frontend (`http://localhost:5173`).

Run the database migration and seed script once the backend container is up:

```bash
docker compose exec backend alembic upgrade head
docker compose exec backend python scripts/seed.py
```

## Environment variables

All configuration comes from the environment; nothing is committed. See `.env.example` for the full list with placeholder values:

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | Postgres connection string |
| `JWT_SECRET` | Signing key for JWTs (generate your own, do not reuse the placeholder) |
| `JWT_EXPIRY_MINUTES` | Token lifetime |
| `AI_API_KEY` | Optional. A free Gemini key (see [AI triage](#ai-triage)); leave blank to use the mock provider only |
| `AI_MODEL` | Gemini model name, e.g. `gemini-flash-lite-latest`. Unused while `AI_API_KEY` is unset |
| `MAX_ATTACHMENT_BYTES` | Attachment size limit (default 5 MiB) |
| `ALLOWED_ATTACHMENT_TYPES` | Comma-separated allowed content types |

## Demo logins

The seed script creates one account per role, all sharing the same password:

| Role | Email | Password |
|---|---|---|
| Admin | `admin@example.com` | `Password123!` |
| Agent | `agent@example.com` | `Password123!` |
| Agent | `agent2@example.com` | `Password123!` |
| Customer | `customer@example.com` | `Password123!` |
| Customer | `customer2@example.com` | `Password123!` |

Sample tickets span every status and priority, including a resolved ticket and one open for more than 48 hours, so the admin dashboard has meaningful numbers out of the box.

## AI triage

Two providers implement the same `AIProvider` interface (`backend/app/ai/base.py`):

- **`GeminiAIProvider`** (`backend/app/ai/gemini_provider.py`) calls Google's Gemini API directly over HTTPS (no SDK) when `AI_API_KEY` is set. Gemini's free tier requires no billing, just a key from [Google AI Studio](https://ai.google.dev).
- **`MockAIProvider`** (`backend/app/ai/mock_provider.py`) is deterministic and keyword-based, with no network call and no cost. It's used outright when `AI_API_KEY` is empty, and it's also the automatic second attempt whenever Gemini fails on a given ticket (network error, rate limit, timeout, or a malformed response) -- so a ticket almost always ends up with *some* suggestion, real or mock, and ticket creation is never blocked on the AI call either way.

This satisfies the brief's requirement that the app "SHALL use a deterministic mocked AI provider" and remain "fully demonstrable without a paid key," while also supporting a real LLM when a free key is available.

All AI output is advisory: it's stored separately from the ticket's real `category`/`priority` fields and only applied when an Agent or Admin explicitly confirms it via the ticket's AI suggestion panel.

## Running the tests

The backend test suite covers the three areas called out in the brief: authentication, ticket creation, and role-based access (see [Known limitations](#known-limitations)). Tests run against a real Postgres database -- nothing is mocked there.

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Point at a real Postgres instance with a database for tests to use:
export TEST_DATABASE_URL="postgresql+psycopg://ticketing:ticketing@localhost:5432/ticketing_test"
createdb -h localhost -U ticketing ticketing_test   # or via docker exec

pytest
```

Property-based tests (Hypothesis) are included alongside example-based tests; some are capped at a modest number of examples since they exercise real bcrypt hashing and real HTTP round-trips per example, which is deliberately slow.

Frontend typecheck and build:

```bash
cd frontend
npm install
npm run typecheck
npm run build
```

## Assumptions made

- "AI-assisted triage" is satisfied by Gemini (free tier) with an automatic fallback to a deterministic mock provider, so the app works fully with or without a key (see [AI triage](#ai-triage)).
- Unentitled access to a ticket (wrong role, not a participant) returns `404` rather than `403`, so a caller can't distinguish "doesn't exist" from "exists but isn't yours."
- Logout is client-side token disposal only; there's no server-side revocation list, since token lifetimes are short enough for this MVP.
- The admin's "assign ticket" UI uses a dropdown of agents (backed by a narrowly-scoped, Admin-only `GET /api/users?role=agent`), not a full user management screen.

## Known limitations

- **Test scope is deliberately narrow.** Per the brief, automated tests cover only authentication, ticket creation, and role-based access. The status workflow, pagination, comments, activity log, AI confirmation, and dashboard maths are not covered by automated tests and were verified manually.
- **No production hardening.** No rate limiting, no CSRF protection beyond what SPA + Bearer-token auth implies, no WAF, no dependency vulnerability scanning pipeline.
- **Gemini's free tier can be rate-limited or temporarily overloaded** (Google-side, not app-specific); when that happens the mock fallback kicks in automatically, so this is not user-facing but is worth knowing about if a demo shows mock suggestions unexpectedly.
- **Accessibility was reviewed structurally** (labeled controls, focus states, no horizontal scroll, loading/error states) but not validated with assistive technology or a full audit.
- **Cloud architecture is a design exercise only.** Nothing in `docs/cloud-architecture.md` is actually provisioned.

## What would be done next

- Broaden automated test coverage to the status workflow, dashboard aggregation, and the AI confirmation endpoint.
- Add rate limiting on `/api/auth/login` and `/api/auth/register`.
- Wire up the cloud architecture for real: Terraform or CDK for the AWS resources described in `docs/cloud-architecture.md`.

## Cloud architecture

See `docs/cloud-architecture.png` for the diagram and `docs/cloud-architecture.md` for the accompanying explanation (hosting, database, secrets, networking, observability, and CI/CD).
