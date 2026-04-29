# Event Draft-Status: Entwürfe und Veröffentlichung

## Übersicht

Events haben einen `status`-Spalte mit zwei Werten:
- **`draft`** — Entwurf, nur für den Host (Ersteller) sichtbar
- **`published`** — Veröffentlicht, für alle sichtbar

Dies ermöglicht den zweistufigen Erstellungsflow: Das Frontend erstellt sofort nach Eingabe der Kerndaten einen Entwurf, der dann auf der Event-Detailseite weiter bearbeitet und schließlich veröffentlicht wird.

---

## DB-Migration

**Datei:** `supabase/migrations/20260430120000_add_event_status.sql`

```sql
ALTER TABLE event
ADD COLUMN status text NOT NULL DEFAULT 'published';
```

- Typ: `text` (kein Enum — Validierung im Application Layer)
- Default: `'published'` für Abwärtskompatibilität mit bestehenden Events
- Neue Events vom Frontend werden mit `status: 'draft'` erstellt

---

## Schema-Änderungen (`app/schemas/events.py`)

### EventCreate

```python
class EventCreate(BaseModel):
    # ...
    status: str = "published"

    @field_validator("status")
    @classmethod
    def status_valid(cls, v: str) -> str:
        if v not in ("draft", "published"):
            raise ValueError("status must be 'draft' or 'published'")
        return v
```

### EventUpdate

```python
class EventUpdate(BaseModel):
    # ...
    status: str | None = None

    @field_validator("status")
    @classmethod
    def status_valid(cls, v: str | None) -> str | None:
        if v is not None and v not in ("draft", "published"):
            raise ValueError("status must be 'draft' or 'published'")
        return v
```

### Response-Schemas

`EventListItem` und `EventDetailResponse` enthalten:
```python
status: str = "published"
```

---

## Service-Änderungen (`app/services/event_service.py`)

### `get_public_events()`

Filtert Entwürfe aus der öffentlichen Liste:
```python
.eq("is_public", True)
.eq("status", "published")
```

### `create_event()`

Übernimmt den Status aus dem Payload:
```python
event_payload = {
    # ...
    "status": data.get("status", "published"),
}
```

### `get_event_by_id()`

Kein Status-Filter — Access Control liegt im Route-Layer. Die Abfrage wurde erweitert um `person_id` und `supabase_user_id` im Join:
```python
"event_participation(event_participation_id, role, person(person_id, supabase_user_id, first_name, last_name))"
```

### `update_event()`

Keine spezielle Behandlung nötig — der generische dict-Iterator übernimmt `status` automatisch:
```python
for key, value in data.items():
    if value is not None:
        event_patch[key] = ...
```

---

## Route-Änderungen (`app/api/v1/events.py`)

### GET `/api/v1/events/{event_id}` — Draft Access Control

Logik:
1. Event laden
2. Wenn `status == "draft"`:
   - User muss authentifiziert sein (`get_current_user_optional`)
   - User muss Host des Events sein (über `event_participation.role == "Host"` und `person.supabase_user_id`)
   - Falls nicht → **404** (nicht 403, um Existenz nicht zu verraten)
3. Wenn `status == "published"` → normal zurückgeben

```python
if raw.get("status") == "draft":
    if not user:
        raise HTTPException(status_code=404, detail="Event not found")
    participations = raw.get("event_participation") or []
    is_host = any(
        p.get("role") == "Host"
        and p.get("person", {}).get("supabase_user_id") == user.user.id
        for p in participations
    )
    if not is_host:
        raise HTTPException(status_code=404, detail="Event not found")
```

### PATCH `/api/v1/events/{event_id}` — Status-Änderung

Der bestehende PATCH-Endpoint akzeptiert `status` als Feld im Body. Damit kann das Frontend den Status von `draft` zu `published` ändern:

```json
PATCH /api/v1/events/{event_id}
{ "status": "published" }
```

Autorisierung: Nur der Host darf updaten (geprüft in `event_service.update_event`).

### Response-Mapping

Beide Helper (`_to_list_item` und `_to_detail`) geben `status` zurück:
```python
status=raw.get("status", "published"),
```

---

## Sicherheitsmodell

| Szenario | Ergebnis |
|----------|----------|
| Unauthentifizierter GET auf Draft | 404 |
| Anderer User GET auf Draft | 404 |
| Host GET auf eigenen Draft | Volles Event mit `status: "draft"` |
| Unauthentifizierter GET auf Published | Event-Daten |
| Draft in öffentlicher Liste | Nie enthalten (Service filtert) |
| Host PATCH `status: "published"` | Event wird öffentlich |
| Nicht-Host PATCH | 403 |

---

## Frontend-Integration

Das Frontend nutzt diese Endpoints wie folgt:

1. **Event als Draft erstellen:** `POST /api/v1/events/` mit `{ status: "draft", ... }`
2. **Draft laden (Host):** `GET /api/v1/events/{id}` mit Bearer-Token
3. **Details bearbeiten:** `PATCH /api/v1/events/{id}` mit geänderten Feldern
4. **Veröffentlichen:** `PATCH /api/v1/events/{id}` mit `{ status: "published" }`

---

## Betroffene Dateien

| Aktion | Datei |
|--------|-------|
| NEU | `supabase/migrations/20260430120000_add_event_status.sql` |
| ÄNDERN | `app/schemas/events.py` — status-Feld + Validator in EventCreate, EventUpdate, EventListItem |
| ÄNDERN | `app/services/event_service.py` — Draft-Filter, Status in Payload, erweiterter Join |
| ÄNDERN | `app/api/v1/events.py` — Access Control, status in Response-Mapping |
