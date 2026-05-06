# User-Account-API

Alle Endpoints unter `/api/v1/users/` erfordern einen gültigen Bearer-JWT.

## Endpoints

| Methode | Pfad | Zweck |
|---------|------|--------|
| GET | `/api/v1/users/me/stats` | Statistiken des eingeloggten Nutzers |
| GET | `/api/v1/events/me` | Eigene Events (als Organizer oder Teilnehmer) |
| GET | `/api/v1/users/me/tickets` | Eigene Tickets (Participations als Proxy) |
| PATCH | `/api/v1/users/me/name` | Vor- und Nachname in `person`-Tabelle aktualisieren |
| DELETE | `/api/v1/users/me` | Konto und alle Daten dauerhaft löschen |

---

## GET /me/stats

Gibt aggregierte Kennzahlen für den eingeloggten Nutzer zurück.

**Response-Schema:** `UserStatsResponse`

```json
{
  "events_attended": 3,
  "events_created": 1,
  "tickets_total": 3,
  "participants_total": 12
}
```

- `events_attended` — Anzahl der `event_participation`-Einträge des Nutzers
- `events_created` — Anzahl der Events, bei denen der Nutzer `event_host` ist
- `tickets_total` — aktuell identisch mit `events_attended` (kein separates Ticket-Kaufsystem)
- `participants_total` — Anzahl akzeptierter Teilnehmer über alle eigenen Events

---

## GET /api/v1/events/me

Gibt Events zurück, die der Nutzer organisiert oder an denen er per RSVP teilnimmt.

**Hinweis:** Dieser Endpoint liegt unter `/api/v1/events/me` (nicht unter `/users/`), da er thematisch zum Events-Router gehört.

**Query-Parameter:**

| Parameter | Typ | Default | Beschreibung |
|-----------|-----|---------|--------------|
| `period` | `upcoming` \| `past` | `upcoming` | Zeitraum |
| `role` | `organizer` \| `attendee` \| — | — | Filtert nach Rolle; ohne Angabe beides |
| `limit` | int 1–100 | 50 | Seitengröße |
| `offset` | int ≥ 0 | 0 | Offset für Paginierung |

**Response-Schema:** `EventListResponse` (identisch mit öffentlichen Events)

Jedes `EventListItem` enthält `is_host: true` wenn der Nutzer Organizer ist.

**Implementierungshinweis:** Host- und Attendee-Events werden in Python zusammengeführt und dedupliziert (ein Nutzer kann theoretisch beides sein). Sortierung und Paginierung erfolgen ebenfalls in Python nach dem Merge.

---

## GET /me/tickets

Gibt Teilnahmen des Nutzers als Ticket-Objekte zurück.

**Response-Schema:** `TicketListResponse`

```json
{
  "tickets": [
    {
      "ticket_id": "<event_participation_id>",
      "event_id": "...",
      "event_title": "Sommerfest",
      "ticket_option_name": "Standard",
      "price": 0.0,
      "currency": "EUR",
      "status": "Accepted",
      "purchased_at": "2024-11-01T18:00:00"
    }
  ],
  "total": 1
}
```

**Hinweis:** Es gibt noch kein separates Ticketkauf-System. `ticket_id` entspricht der `event_participation_id`, `purchased_at` dem Zeitpunkt der RSVP-Erstellung.

---

## PATCH /me/name

Aktualisiert `first_name` und `last_name` in der `person`-Tabelle.

**Request-Body:**

```json
{
  "first_name": "Max",
  "last_name": "Mustermann"
}
```

**Response:** `{ "first_name": "Max", "last_name": "Mustermann" }`

Verwendet `get_supabase_for_user(token)`, damit die RLS-Policy (`auth.uid() = supabase_user_id`) greift. Das Frontend ruft zusätzlich `supabase.auth.updateUser()` auf, um `user_metadata.first_name/last_name` synchron zu halten.

---

## DELETE /me

Löscht alle Nutzerdaten und anschließend den Supabase-Auth-Eintrag.

**Reihenfolge der Löschoperationen:**

1. `event_participation` des Nutzers entfernen
2. Alle eigenen Events löschen (kaskadiert Location, Media, Participations der Gäste per FK)
3. `person`-Datensatz löschen
4. Supabase-Auth-User via `auth.admin.delete_user()` entfernen (erfordert Service-Role-Key im Backend)

**Response:** `204 No Content`

---

## Timestamp-Konvention

Supabase gibt Timestamps je nach Konfiguration ohne Timezone-Suffix zurück (z. B. `2024-11-11T20:00:00`). Das Frontend behandelt solche Strings als **Lokalzeit** (nicht UTC), indem beim Parsen der Timezone-Suffix entfernt und `T` durch ein Leerzeichen ersetzt wird — das zwingt JavaScript zur lokalen Interpretation.

Beim Erstellen eines Events fügt das Frontend den lokalen UTC-Offset explizit an (z. B. `2024-11-11T20:00:00+01:00`), damit Supabase den korrekten UTC-Wert speichert.
