# Authentication

**Kategorie:** A-Software  
**Entwurfs-Entsprechung:** `<<component>> Authentication`  
**Implementierung:** `app/core/auth.py`, `app/core/supabase.py`, Supabase Auth (extern)

## Beschreibung

Die `Authentication`-Komponente ist verantwortlich für die Verwaltung von Benutzerkonten und die Absicherung aller geschützten Endpunkte. Sie stellt dem `APIAdapter` die Schnittstellen `Register`, `Login`, `Logout` und `Delete` zur Verfügung.

[→ Im Architekturentwurf ansehen](<https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Entwurf/Komponentendiagramm#:~:text=Umgesetzte%20Anforderungen-,Authentication,-M1%20(Passwortlose%20Authentifizierung>)

!!! note "Abweichung vom Entwurf"
    Im ursprünglichen Entwurf sollte bei der Registrierung eine **Handynummer per SMS** bestätigt werden (M1). In der Implementierung wird **E-Mail-OTP über Supabase Auth** eingesetzt. Supabase übernimmt die gesamte Authentifizierungslogik (Registrierung, OTP-Versand, Session-Verwaltung). Das Backend validiert eingehende JWTs, ohne selbst Passwörter oder Sessions zu speichern.

## Bereitgestellte Schnittstellen

| Entwurfs-Schnittstelle | Implementierung |
|---|---|
| `Register` | Supabase Auth: OTP-Registrierung per E-Mail |
| `Login` | Supabase Auth: OTP-Verifizierung |
| `Logout` | Supabase Auth: Session invalidieren |
| `Delete` | `app/api/v1/users.py`: `DELETE /api/v1/users/me` |

## Genutzte Schnittstellen

- **`SendMessage`** (MessagingAdapter): Im Entwurf für OTP-SMS vorgesehen. In der Implementierung übernimmt Supabase direkt den E-Mail-Versand; der `MessagingAdapter` (Resend) wird für transaktionale E-Mails außerhalb des Auth-Flows genutzt.
- **`Auth`** (DatabaseAdapter): Supabase Auth authentifiziert Nutzer gegen die PostgreSQL-Datenbank (`DBAuth`).

## Implementierung

### JWT-Validierung

Die zentrale Auth-Dependency prüft den Bearer-Token aus dem `Authorization`-Header:

```python
# app/core/auth.py
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    token = credentials.credentials
    user = supabase.auth.get_user(token)
    return user.user
```

### Optionale Authentifizierung

Für öffentliche Endpunkte, die auch authentifizierte Zusatzdaten liefern können:

```python
async def get_current_user_optional(...) -> dict | None:
    # Gibt None zurück statt Exception bei fehlendem Token
```

### Account-Löschung

```
DELETE /api/v1/users/me
```

Löscht das Supabase-Auth-Konto sowie alle zugehörigen Datenbankeinträge (Events, Tickets, Buchungen).

## Abhängigkeiten

- `app/core/supabase.py` – Supabase-Client-Singleton
- `app/core/config.py` – `SUPABASE_JWT_SECRET` für Token-Validierung
- [`MessagingAdapter`](messaging-adapter.md) – E-Mail-Benachrichtigungen
- [`DatabaseAdapter`](database-adapter.md) – Datenbankzugriff
