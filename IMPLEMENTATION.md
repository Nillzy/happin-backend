# Backend - Was existiert

**Stand:** 2026-04-21

---

## Dateien & Module

### Core (`app/core/`)


| Datei         | Was es macht                                                           |
| ------------- | ---------------------------------------------------------------------- |
| `config.py`   | Lädt .env Settings (SUPABASE_URL, SUPABASE_KEY, DEBUG, etc.)           |
| `supabase.py` | Supabase Client (global verfügbar als `supabase`)                      |
| `auth.py`     | JWT Middleware: `get_current_user()` und `get_current_user_optional()` |


### API Endpoints (`app/api/v1/`)


| Datei       | Endpoints                                                      |
| ----------- | -------------------------------------------------------------- |
| `router.py` | Main Router, bindet alle Sub-Router ein                        |
| `user.py`   | `GET /api/v1/user/me` - Gibt aktuellen User zurück (geschützt) |


### Schemas (`app/schemas/`)


| Datei     | Was drin ist                                                          |
| --------- | --------------------------------------------------------------------- |
| `user.py` | `UserResponse` - Schema für User-Daten (id, phone, email, created_at) |


### Services & Utils


| Ordner          | Status                             |
| --------------- | ---------------------------------- |
| `app/services/` | Leer (bereit für Business Logic)   |
| `app/utils/`    | Leer (bereit für Helper Functions) |


### Main App


| Datei         | Was es macht                                    |
| ------------- | ----------------------------------------------- |
| `app/main.py` | FastAPI App mit CORS, Logging, Health Endpoints |


---

## Verfügbare Endpoints


| Endpoint              | Auth | Beschreibung                      |
| --------------------- | ---- | --------------------------------- |
| `GET /`               | -    | Root Info                         |
| `GET /health`         | -    | Health Check                      |
| `GET /api/v1/health`  | -    | API v1 Health                     |
| `GET /api/v1/user/me` | 🔒   | Current User Info (TEST-ENDPOINT) |
| `GET /docs`           | -    | Swagger UI (nur DEBUG=true)       |


---

## Dependencies

```txt
fastapi==0.109.0
uvicorn[standard]==0.27.0
pydantic-settings==2.1.0
supabase==2.3.0
```

---

## Environment Variables

Definiert in `.env.example`:

- `SUPABASE_URL`
- `SUPABASE_KEY`
- `SUPABASE_JWT_SECRET`
- `DATABASE_URL`
- `DEBUG`
- `LOG_LEVEL`

---

## Test-Endpoint

`GET /api/v1/user/me` ist ein vollständiges Beispiel:

- Nutzt Auth Middleware
- Gibt User-Daten zurück
- Test-Anleitung in `TEST.md`

**Verwendung:**

```python
# In einem Router:
from app.core.auth import get_current_user

@router.get("/protected")
async def my_endpoint(user = Depends(get_current_user)):
    return {"user_id": user.user.id}
```

