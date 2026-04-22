# Authentifizierung

## Empfohlener Gesamtflow

1. Das **Frontend** spricht **direkt** mit **Supabase Auth** (z. B. OTP per SMS).
2. Nach erfolgreicher Verifikation liefert Supabase ein **JWT** (Access Token).
3. Aufrufe an dieses Backend senden das Token im Header:  
   `Authorization: Bearer <jwt>`
4. Geschützte Routen nutzen die Dependency **`get_current_user`** (`app/core/auth.py`), die das Token an **`supabase.auth.get_user(token)`** übergibt und bei Erfolg das Supabase-**UserResponse**-Objekt zurückgibt.

Vorteil: weniger eigener Auth-Code; Passwort-/OTP-Logik und Token-Ausstellung bleiben bei Supabase.

## Implementierung im Backend

- **`HTTPBearer`** (FastAPI `fastapi.security`) liest den Bearer-Token.
- **`get_current_user`:** Pflicht-Authentifizierung; bei ungültigem Token **401** mit `WWW-Authenticate: Bearer`.
- **`get_current_user_optional`:** Optional; ohne oder mit ungültigem Token wird `None` zurückgegeben (kein 401), geeignet für „öffentlich, aber angereichert wenn eingeloggt“.

## Zugriff auf Nutzerdaten im Handler

Die Supabase-Client-Methode `get_user` liefert ein Objekt, dessen **Profilfelder** typischerweise unter **`.user`** liegen (z. B. `user.user.id`, `user.user.email`). Beim Schreiben neuer Endpoints im bestehenden Projekt das Muster aus `app/api/v1/user.py` übernehmen.

## JWT-Secret

`SUPABASE_JWT_SECRET` ist in `Settings` vorgesehen, wird für die aktuelle `get_user`-Validierung aber nicht zwingend benötigt. Eigene **lokale** JWT-Verifikation (z. B. mit `jose`) wäre ein separates Thema und müsste explizit designt werden.
