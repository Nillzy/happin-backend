# 17. Ticket-System (M8)

## Übersicht

Tickets werden automatisch generiert wenn ein Gast einem Event zusagt (RSVP status = "Accepted"). Jedes Ticket enthält einen eindeutigen `qr_token` der als QR-Code dargestellt und beim Einlass gescannt wird.

## Datenbank-Schema

Die `ticket`-Tabelle muss manuell im Supabase Dashboard angelegt werden:

```sql
CREATE TABLE ticket (
    ticket_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id UUID NOT NULL REFERENCES event(event_id) ON DELETE CASCADE,
    person_id UUID NOT NULL REFERENCES person(person_id) ON DELETE CASCADE,
    ticket_option_id UUID REFERENCES ticket_option(ticket_option_id),
    qr_token TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'used', 'expired')),
    created_at TIMESTAMPTZ DEFAULT now(),
    used_at TIMESTAMPTZ,
    UNIQUE(event_id, person_id)
);

CREATE INDEX idx_ticket_qr_token ON ticket(qr_token);

ALTER TABLE ticket ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can read own tickets" ON ticket
    FOR SELECT USING (person_id IN (
        SELECT person_id FROM person WHERE supabase_user_id = auth.uid()
    ));

CREATE POLICY "Hosts can read event tickets" ON ticket
    FOR SELECT USING (event_id IN (
        SELECT eh.event_id FROM event_host eh
        JOIN person p ON p.person_id = eh.person_id
        WHERE p.supabase_user_id = auth.uid()
    ));
```

## Ablauf

1. Gast ruft `POST /api/v1/events/{event_id}/rsvp` mit `status: "Accepted"` auf
2. RSVP wird in `event_participation` gespeichert (bestehende Logik)
3. `ticket_service.create_ticket()` generiert Ticket mit `qr_token = secrets.token_urlsafe(32)`
4. Bei erneutem Accept (idempotent): Bestehendes Ticket wird zurückgegeben
5. Bei Absage (`status: "Declined"`): Ticket wird gelöscht

## API

### GET /api/v1/users/me/tickets

Gibt alle Tickets des eingeloggten Users zurück.

**Response:**
```json
{
    "tickets": [
        {
            "ticket_id": "uuid",
            "qr_token": "zufälliger-43-zeichen-token",
            "event_id": "uuid",
            "event_title": "Summer Party",
            "starts_at": "2026-05-20T19:00:00Z",
            "city": "Stuttgart",
            "ticket_option_name": "Standard",
            "price": 0.0,
            "currency": "EUR",
            "status": "active",
            "created_at": "2026-05-07T10:00:00Z",
            "used_at": null
        }
    ],
    "total": 1
}
```

## QR-Token Design

- **Format**: `secrets.token_urlsafe(32)` → 43 Zeichen Base64url
- **Entropie**: 256 Bit (kryptographisch sicher)
- **Zweck**: Wird im QR-Code auf dem Ticket dargestellt und beim Scan validiert
- **Vorteile**: Unabhängig von `ticket_id`, regenerierbar bei Leak, erweiterbar (HMAC für Offline-Validierung)

## Betroffene Dateien

- `app/services/ticket_service.py` — CRUD-Operationen
- `app/api/v1/events.py` — Hook im RSVP-Endpoint
- `app/services/user_service.py` — Delegation an ticket_service
- `app/schemas/user.py` — TicketItem mit qr_token
