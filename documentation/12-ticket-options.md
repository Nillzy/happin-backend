# Ticket-Optionen (Preiskategorien)

## Überblick

Das Ticket-Options-System erlaubt es Hosts, beliebig viele Preiskategorien für ihre Events zu definieren (z.B. Early Bird, Normal, VIP). Jedes Event trifft eine explizite Entscheidung: **kostenlos** oder **kostenpflichtig mit Ticket-Optionen**.

Es gibt kein "Preis auf Anfrage" — der Eintritt ist immer eindeutig definiert.

---

## Datenmodell

### Neue Spalte auf `event`

| Spalte | Typ | Default | Beschreibung |
|--------|-----|---------|--------------|
| `is_free` | `boolean NOT NULL` | `true` | Explizite Markierung ob Event kostenlos ist |

### Neue Tabelle `ticket_option`

| Spalte | Typ | Beschreibung |
|--------|-----|--------------|
| `ticket_option_id` | `uuid PK` | Auto-generierte ID |
| `event_id` | `uuid FK → event` | Zugehöriges Event (CASCADE DELETE) |
| `name` | `text NOT NULL` | Name der Option (z.B. "Early Bird") |
| `description` | `text` | Optionale Beschreibung |
| `price` | `numeric(10,2)` | Preis in EUR (0.00 = kostenlose Option) |
| `quantity_limit` | `integer` | Optionales Verkaufslimit (NULL = unbegrenzt) |
| `sort_order` | `integer` | Reihenfolge in der Anzeige |
| `created_at` | `timestamptz` | Erstellungszeitpunkt |

**Abgrenzung zur `ticket`-Tabelle:** Die bestehende `ticket`-Tabelle speichert **ausgestellte Tickets** (QR-Code, scan_count, redeemed_at) — sie repräsentiert das konkrete Ticket eines Teilnehmers. `ticket_option` definiert dagegen die **Preiskategorien**, aus denen gewählt werden kann.

---

## Row Level Security (RLS)

| Policy | Operation | Berechtigung |
|--------|-----------|--------------|
| `anyone_select_ticket_options` | SELECT | Alle (public) |
| `host_insert_ticket_options` | INSERT | Nur Host des Events |
| `host_update_ticket_options` | UPDATE | Nur Host des Events |
| `host_delete_ticket_options` | DELETE | Nur Host des Events |

Die Host-Prüfung erfolgt über den Join:
```
event_participation.event_id = ticket_option.event_id
AND event_participation.role = 'Host'
AND person.supabase_user_id = auth.uid()
```

---

## API-Endpoint

### `PUT /api/v1/events/{event_id}/ticket-options`

**UPSERT-Semantik:** Sendet die vollständige gewünschte Liste. Das Backend synchronisiert:
1. Items mit `ticket_option_id` → UPDATE
2. Items ohne `ticket_option_id` → INSERT
3. Bestehende IDs die im Request fehlen → DELETE

**Auth:** Bearer Token (JWT) erforderlich. Application-Layer prüft Host-Rolle + RLS erzwingt es auf DB-Ebene.

**Request Body:**
```json
{
  "ticket_options": [
    {
      "ticket_option_id": "uuid-or-null",
      "name": "Early Bird",
      "description": "Ermäßigter Preis für Frühbucher",
      "price": 15.00,
      "quantity_limit": 50,
      "sort_order": 0
    },
    {
      "name": "VIP",
      "description": "Zugang zum VIP-Bereich",
      "price": 50.00,
      "quantity_limit": null,
      "sort_order": 1
    }
  ]
}
```

**Response:** `200 OK` mit der aktualisierten Liste (alle Items haben `ticket_option_id`).

---

## Integration in Event-Detail

Der `GET /api/v1/events/{event_id}` Endpoint liefert Ticket-Optionen direkt mit:

```json
{
  "event_id": "...",
  "is_free": false,
  "ticket_options": [
    {
      "ticket_option_id": "...",
      "name": "Early Bird",
      "description": "Ermäßigter Preis",
      "price": 15.00,
      "quantity_limit": 50,
      "sort_order": 0
    }
  ]
}
```

Kein separater GET-Endpoint für Ticket-Optionen nötig.

---

## is_free-Logik

| Aktion | Ergebnis |
|--------|----------|
| `PATCH /events/{id}` mit `is_free: true` | Alle `ticket_option` für das Event werden gelöscht |
| `PUT /events/{id}/ticket-options` mit Optionen | Host muss zusätzlich `is_free: false` setzen |
| Event erstellen | Default: `is_free: true` |

---

## Sicherheitskonzept

1. **Doppelte Absicherung:** Application-Layer Host-Check (schnelles 403) + RLS auf DB-Ebene
2. **User-Token-Client:** Alle Writes laufen über `get_supabase_for_user(token)` — kein Service-Key-Bypass
3. **Input-Validierung:** Pydantic prüft name ≠ leer, price ≥ 0, quantity_limit > 0 (wenn gesetzt)
4. **CASCADE DELETE:** Wenn ein Event gelöscht wird, werden alle Ticket-Optionen automatisch entfernt

---

## Betroffene Dateien

| Datei | Rolle |
|-------|-------|
| `supabase/migrations/20260430140000_create_ticket_option.sql` | Tabelle + RLS-Policies |
| `app/schemas/ticket_options.py` | Pydantic-Schemas (Request/Response) |
| `app/services/ticket_option_service.py` | UPSERT-Sync Business-Logik |
| `app/api/v1/ticket_options.py` | PUT-Endpoint mit Auth |
| `app/api/v1/router.py` | Router-Registrierung |
| `app/schemas/events.py` | `is_free` + `ticket_options` in Event-Schemas |
| `app/services/event_service.py` | ticket_option im Select, is_free-Cleanup |
| `app/api/v1/events.py` | Mapping in Response-Objekte |

---

## Migration anwenden

```bash
supabase db push
```
