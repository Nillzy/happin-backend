# Event-Erstellung — Backend-Architektur

## Überblick

Die Event-Erstellung ermöglicht eingeloggten Nutzern, öffentliche oder private Events anzulegen. Der Ersteller wird automatisch als Host zugewiesen. Dieses Feature deckt die Wiki-Anforderungen M2 (Event erstellen) und M8 (Private Events mit Einladungslink) ab.

## DB-Migration: `supabase_user_id` auf `person`

**Problem:** Die `person`-Tabelle hatte keinen Link zu Supabase Auth. Supabase Auth identifiziert User via UUID (`auth.users.id`), aber `person.person_id` ist ein autoinkrementierendes Integer.

**Lösung:** Neue Spalte `supabase_user_id UUID UNIQUE` auf `person`. Nullable, da bestehende Einträge (eingeladene Gäste ohne Account) ohne Auth-Verknüpfung existieren können.

**Migration:** `supabase/migrations/20260428160032_add_supabase_user_id.sql`

## Person Service (`app/services/person_service.py`)

`get_or_create_person(supabase_user_id, email, token)`:
1. Erstellt einen Supabase-Client mit dem User-JWT (`get_supabase_for_user(token)`)
2. Sucht Person mit gegebener `supabase_user_id`
3. Wenn gefunden: gibt bestehenden Eintrag zurück
4. Wenn nicht: erstellt neue Person mit email als `email_address` und email-Prefix als `first_name`

Dieses Pattern stellt sicher, dass jeder Auth-User genau einen `person`-Eintrag hat, der beim ersten Event-Create automatisch angelegt wird.

## Event-Erstellungs-Flow (`app/services/event_service.py`)

`create_event(data, person_id, token)` führt 4 sequenzielle Inserts aus (alle über `get_supabase_for_user(token)`):

1. **Location** → `location` Tabelle → `location_id`
2. **invitation_link** generieren: `secrets.token_urlsafe(16)` (128-Bit, URL-sicher)
3. **Event** → `event` Tabelle (mit `location_id`, `invitation_link`, `starts_at`, optional `ends_at`) → `event_id`
4. **Host-Participation** → `event_participation` Tabelle (role: `Host`, status: `Accepted`) → fertig

Danach wird das vollständige Event via `get_event_by_id()` zurückgeladen.

> **Hinweis:** Seit der Schema-Optimierung (siehe [10-schema-optimization.md](10-schema-optimization.md)) ist die `participation`-Tabelle aufgelöst. `status` wird direkt auf `event_participation` gesetzt — kein separater Insert mehr nötig.

### Warum sequenziell und keine Transaktion?

Das Supabase Python SDK (`supabase-py`) bietet keine Transaktionsunterstützung über den PostgREST-Client. Für echte Transaktionen bräuchte man entweder eine direkte DB-Verbindung oder eine Supabase Edge Function. Das übersteigt den Sprint-2-Scope.

**Risiko:** Wenn ein späterer Insert fehlschlägt, bleiben die vorherigen bestehen (z.B. Location ohne Event). In der Praxis ist das selten, da die Inserts einfach sind und keine komplexen Constraints verletzen.

### invitation_link-Generierung

- `secrets.token_urlsafe(16)` erzeugt 22 Zeichen (128 Bit Entropie)
- Nicht erratbar (kryptographisch sicher)
- UNIQUE-Constraint in der DB verhindert Kollisionen
- Wird für jedes Event generiert (auch öffentliche), da das Feld `NOT NULL` ist

## POST `/api/v1/events/` Endpoint

**Auth:** `Depends(get_current_user)` + `Depends(HTTPBearer())` — Bearer JWT erforderlich. Anonyme Anfragen erhalten 401.

**Supabase-Client:** `get_supabase_for_user(token)` — alle DB-Operationen (Location-Insert, Event-Insert, Participation-Insert) laufen mit dem JWT des Users. PostgREST erkennt den User als `authenticated`, RLS-Policies greifen. Kein Service-Role/Secret Key nötig.

**Request-Schema:** `EventCreate`
```json
{
    "title": "Sommerparty",
    "starts_at": "2026-07-15T18:00:00",
    "ends_at": "2026-07-15T23:00:00",
    "description": "...",
    "category": "Party",
    "max_capacity": 100,
    "is_public": true,
    "location": {
        "city": "Berlin",
        "street": "Unter den Linden",
        "house_number": "1",
        "postal_code": "10117",
        "country": "Deutschland"
    }
}
```

**Validierung (Pydantic):**
- `title`: nicht leer, max 255 Zeichen
- `starts_at`: muss in der Zukunft liegen
- `ends_at`: optional
- `max_capacity`: wenn gesetzt, > 0 (integer)
- `location.city`: nicht leer

**Response:** `EventDetailResponse` (gleiche Shape wie GET `/events/{id}`) mit Status 201.

## Hinweis: `maybe_single()` in postgrest-py

`maybe_single().execute()` gibt `None` zurück (nicht ein Response-Objekt mit leerer `.data`), wenn 0 Zeilen gefunden werden. Code muss deshalb immer prüfen:

```python
response = supabase.table("x").select("*").eq(...).maybe_single().execute()
if response and response.data:
    return response.data
```

Ohne die `response`-Prüfung crasht der Zugriff auf `.data` mit `'NoneType' object has no attribute 'data'`.

## Bekannte Limitierungen

- Kein Rollback bei Teil-Fehlern (kein Transaktionssupport)
- Keine Bild-Uploads beim Erstellen (Sprint 2+)
- RLS-Policies sind permissiv (authenticated kann alles) — feinere Policies kommen später
