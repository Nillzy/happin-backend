## Commands

```bash
# Development
uvicorn app.main:app --reload --port 8001   # Start dev server with auto-reload

# Testing
pytest tests/ --tb=short                    # Run all tests
pytest tests/ --tb=short -p no:warnings     # Run tests (CI mode)

# Docker
docker build -t happin-backend .
docker run -p 8001:8001 --env-file .env happin-backend
```

## Environment

Copy `.env.example` to `.env` and fill in the values:

- `SUPABASE_URL` — Supabase instance URL (use `http://localhost:8000` for local Supabase)
- `SUPABASE_ANON_KEY` — Supabase public anon key
- `SUPABASE_JWT_SECRET` — Supabase JWT secret (for local token verification)
- `DATABASE_URL` — PostgreSQL connection string (optional, Supabase client is used instead)
- `DEBUG` — `true` enables Swagger UI at `/docs` and `/redoc`; `false` disables docs
- `LOG_LEVEL` — Logging verbosity (`info`, `debug`, `warning`, etc.)

Settings are loaded via `pydantic-settings` in `app/core/config.py`. Missing required vars raise a validation error at startup.

## Architecture

This is a **FastAPI** backend (Python 3.11+) serving as the REST API for the Happin event discovery platform. It runs on port **8001** (port 8000 is reserved for the Supabase dashboard).

### Project Layout

```
app/
  main.py             # FastAPI instance, CORS middleware, root/health endpoints, lifespan hooks
  core/
    config.py         # Pydantic Settings — single source of truth for all env vars
    supabase.py       # Lazy-initialized Supabase client (global `supabase` instance)
    auth.py           # HTTPBearer JWT middleware — get_current_user / get_current_user_optional
  api/v1/
    router.py         # Aggregates all v1 sub-routers; include here when adding new routers
    user.py           # /api/v1/user/* endpoints
  schemas/
    user.py           # Pydantic response models (UserResponse)
  services/           # Business logic (currently empty — add feature logic here)
  utils/              # Helper functions (currently empty)
tests/
  conftest.py         # Pytest fixtures; mocks Supabase before app import
  test_health.py      # Tests for /, /health, /api/v1/health
  test_auth.py        # Tests for /api/v1/user/me auth flow
documentation/        # Source of truth for architecture and design decisions
```

### API Versioning

All endpoints live under `/api/v1`. Add new feature routers as sub-modules of `app/api/v1/` and register them in `app/api/v1/router.py`. Planned routers: `events`, `rsvp`, `tickets`.

### Authentication

The backend delegates auth entirely to **Supabase**:

1. Frontend authenticates with Supabase directly (OTP/phone flow) and receives a JWT.
2. Frontend sends `Authorization: Bearer <jwt>` on every protected request.
3. Backend validates the token by calling `supabase.auth.get_user(token)`.

Use `Depends(get_current_user)` for required auth, `Depends(get_current_user_optional)` for optional auth. Both are defined in `app/core/auth.py`.

### Database

There is no ORM. All database access goes through the **Supabase Python client** (`supabase==2.10.0`). The global client is initialized lazily in `app/core/supabase.py`. Business logic that queries the database belongs in `app/services/`.

### Schemas

Request and response shapes are validated with **Pydantic v2** models in `app/schemas/`. Keep schemas in `app/schemas/`, not inline in route files.

## Testing

Tests mock the Supabase client before importing the app — this pattern must be preserved:

```python
with patch("supabase.create_client", return_value=_mock_supabase):
    from app.main import app
```

Each test receives a `client` (httpx `TestClient`) and `mock_supabase` fixture. Reset mock return values per test rather than relying on global state.

## Documentation

The `documentation/` folder is the source of truth for project context and design decisions:

- `documentation/00-index.md` — index of all docs
- `documentation/01-project-overview.md` — purpose, tech stack, system role

**Always read the relevant docs before starting a task.** When making changes, update the appropriate file in `documentation/`. New topics that don't fit an existing file get their own file, registered in `00-index.md`.

**All documentation must live in `documentation/` — never create doc files outside this folder.**
Every major change should be well documented (in its own file if needed).

## CI/CD

The GitLab pipeline (`.gitlab-ci.yml`) has three stages:

1. **test** — runs on `main` and all merge requests; executes `pytest`
2. **build** — runs on `main` only; builds and pushes Docker image to GitLab Container Registry
3. **deploy** — manual trigger on `main`; SSHs into `vm552.ipp-vps.net` and runs `docker compose`

The production server listens on `http://vm552.ipp-vps.net:8001`.
