# Authentifizierung

## Empfohlener Gesamtflow

1. Das **Frontend** spricht **direkt** mit **Supabase Auth** (E-Mail OTP).
2. Nach erfolgreicher Verifikation liefert Supabase ein **JWT** (Access Token).
3. Aufrufe an dieses Backend senden das Token im Header:
   `Authorization: Bearer <jwt>`
4. Geschützte Routen nutzen die Dependency **`get_current_user`** (`app/core/auth.py`), die das Token an **`supabase.auth.get_user(token)`** übergibt und bei Erfolg das Supabase-**UserResponse**-Objekt zurückgibt.

Vorteil: weniger eigener Auth-Code; Passwort-/OTP-Logik und Token-Ausstellung bleiben bei Supabase.

## Implementierung im Backend

- **`HTTPBearer`** (FastAPI `fastapi.security`) liest den Bearer-Token.
- **`get_current_user`:** Pflicht-Authentifizierung; bei ungültigem Token **401** mit `WWW-Authenticate: Bearer`.
- **`get_current_user_optional`:** Optional; ohne oder mit ungültigem Token wird `None` zurückgegeben (kein 401), geeignet für "öffentlich, aber angereichert wenn eingeloggt".

## Zugriff auf Nutzerdaten im Handler

Die Supabase-Client-Methode `get_user` liefert ein Objekt, dessen **Profilfelder** typischerweise unter **`.user`** liegen (z. B. `user.user.id`, `user.user.email`). Beim Schreiben neuer Endpoints im bestehenden Projekt das Muster aus `app/api/v1/events.py` übernehmen.

## Supabase-Client und RLS

### Zwei Client-Varianten (`app/core/supabase.py`)

| Funktion | Key | Zweck |
|----------|-----|-------|
| `get_supabase()` | Publishable/Anon Key | Für öffentliche Leseabfragen (GET-Endpoints). RLS-Policies für `anon` greifen. |
| `get_supabase_for_user(token)` | Publishable Key + User-JWT | Für authentifizierte Schreiboperationen. Der User-JWT wird als `Authorization`-Header gesetzt, PostgREST erkennt den User als `authenticated` und RLS-Policies greifen korrekt. |

### Warum kein Service-Role/Secret Key?

Supabase bietet Secret Keys (`sb_secret_...`, Nachfolger des alten `service_role`), die RLS komplett umgehen. Wir nutzen sie bewusst **nicht**:

- **Prinzip der geringsten Rechte:** Jede DB-Operation läuft mit den Rechten des eingeloggten Users. Ein kompromittierter Endpoint kann nur das tun, was der User ohnehin darf.
- **RLS schützt doppelt:** Selbst bei einem Bug im Backend-Code (z.B. fehlende Validierung) verhindert RLS, dass ein User fremde Daten ändert.
- **Kein zusätzliches Secret nötig:** Das Backend braucht nur den öffentlichen Anon-Key und den JWT des Users — kein privilegiertes Secret in der `.env`.

### Muster für neue Endpoints mit Schreibzugriff

```python
from fastapi import Depends
from fastapi.security import HTTPBearer
from app.core.auth import get_current_user
from app.core.supabase import get_supabase_for_user

@router.post("/")
async def create_something(
    body: SomeSchema,
    user=Depends(get_current_user),
    credentials=Depends(HTTPBearer()),
):
    supabase = get_supabase_for_user(credentials.credentials)
    # INSERT/UPDATE/DELETE Operationen über diesen Client
    supabase.table("...").insert({...}).execute()
```

## JWT-Secret

`SUPABASE_JWT_SECRET` ist in `Settings` vorgesehen, wird für die aktuelle `get_user`-Validierung aber nicht zwingend benötigt. Eigene **lokale** JWT-Verifikation (z. B. mit `jose`) wäre ein separates Thema und müsste explizit designt werden.
