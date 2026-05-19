# Event Soft-Delete

## Überblick

Events können vom Host soft-gelöscht werden. Statt eines Hard-Deletes wird ein `deleted_at`-Timestamp gesetzt.

## Datenbankfeld

```sql
ALTER TABLE event ADD COLUMN deleted_at TIMESTAMPTZ NULL;
```

`NULL` = aktiv. Wenn gesetzt, ist das Event gelöscht.

## Sichtbarkeitsregeln

| Zustand | Host | Teilnehmer | Öffentlich/Anonym |
|---|---|---|---|
| `deleted_at` gesetzt, < 48h her | Sichtbar (`is_deleted=true`) | Sichtbar (`is_deleted=true`) | 404 |
| `deleted_at` gesetzt, ≥ 48h her | 404 / nicht in Listen | 404 / nicht in Listen | 404 |

## API

### DELETE /api/v1/events/{event_id}

- **Auth**: Nur Host (403 sonst)
- **Bedingung**: `starts_at - now() >= 48h` (400 sonst, Meldung: "weniger als 48h")
- **Response**: 204 No Content

### Fehler-Codes

| ValueError | HTTP |
|---|---|
| `too_close_to_start` | 400 |
| `already_deleted` | 400 |
| `event_not_found` | 404 |
| `PermissionError` | 403 |

## Betroffene Services

- `event_service.delete_event()` — setzt `deleted_at`
- `event_service.get_public_events()` — filtert `deleted_at IS NOT NULL` aus
- `event_service.get_event_by_id()` — prüft 48h-Fenster und Host/Teilnehmer-Zugehörigkeit
- `user_service.get_user_events()` — zeigt gelöschte Events innerhalb des 48h-Fensters
