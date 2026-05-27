# Event Absagen

## Überblick

Events können vom Host abgesagt werden. Beim Absagen werden alle bezahlten Tickets automatisch via Stripe zurückerstattet. Die Aktion ist irreversibel — abgesagte Events können nicht reaktiviert werden.

## Datenbankfeld

```sql
ALTER TABLE event ADD COLUMN cancelled_at TIMESTAMPTZ NULL;
```

`NULL` = aktiv. Wenn gesetzt, ist das Event abgesagt.

## Sichtbarkeitsregeln

| Zustand | Host | Teilnehmer | Öffentlich/Anonym |
|---|---|---|---|
| `cancelled_at` gesetzt | Dauerhaft sichtbar (`is_cancelled=true`) | Dauerhaft sichtbar (`is_cancelled=true`) | Nicht in Discovery (Filter `cancelled_at IS NULL`) |

Abgesagte Events bleiben für Host und Teilnehmer dauerhaft sichtbar, damit Kontext (Bezeichnung, ehemalige Tickets, RSVP-Historie) erhalten bleibt. Aus dem öffentlichen Discovery-Feed werden sie ausgeblendet.

## API

### POST /api/v1/events/{event_id}/cancel

- **Auth**: Nur Host (403 sonst)
- **Keine 48h-Sperre** — Absagen ist jederzeit möglich, gerade kurzfristige Absagen sind wichtig
- **Side-Effects**: Refund aller bezahlten Tickets, Pending-Orders auf `failed` gesetzt
- **Response**: 200 OK mit `RefundSummary`

#### RefundSummary

```json
{
  "refunded_count": 2,
  "failed_count": 0,
  "failed_order_ids": [],
  "skipped_count": 1
}
```

- `refunded_count` — erfolgreich zurückerstattete Orders
- `failed_count` — Stripe-Fehler bei Refund (Support-Eskalation)
- `failed_order_ids` — IDs der fehlgeschlagenen Refunds
- `skipped_count` — übersprungene Orders (alle Tickets bereits gescannt)

### Fehler-Codes

| ValueError | HTTP |
|---|---|
| `already_cancelled` | 400 |
| `event_not_found` | 404 |
| `PermissionError` | 403 |

## Auto-Refund

Beim Absagen ruft `cancel_event` `_refund_all_paid_orders` auf:

1. Alle `ticket_order` mit `status = 'paid'` werden iteriert
2. Wenn alle Tickets einer Order bereits gescannt → übersprungen
3. Sonst: Stripe-Refund mit Idempotency-Key `event-cancel-{order_id}`
4. Bei Erfolg: `ticket_order.status = 'refunded'`, Tickets gelöscht, `event_participation.status = 'Declined'`
5. Pending Orders → `status = 'failed'`

Stripe-Fehler blockieren das Cancel **nicht** — sie werden im `RefundSummary` zurückgegeben und im Server-Log geloggt.

## Aktions-Sperren auf abgesagten Events

Defense-in-Depth: Service-Layer-Helper `event_service._ensure_event_active(event_id, token)` wirft `ValueError('event_cancelled')`, wenn das Event abgesagt ist. Aufgerufen in:

- `rsvp_event` — RSVP nicht mehr möglich
- `update_event` — Event-Edit nicht mehr möglich
- `booking_service.validate_booking` — Ticket-Kauf-Checkout nicht mehr möglich
- `custom_field_service.sync_custom_fields` — Host kann Custom-Fields nicht mehr ändern
- Custom-Field-Response-Submit (`POST /events/{id}/custom-fields/responses`) — Teilnehmer kann Angaben nicht mehr ändern

Alle Endpoints mappen `event_cancelled` auf HTTP 400 mit der Meldung "Event wurde abgesagt und kann nicht mehr verändert werden".

## Betroffene Services

- `event_service.cancel_event()` — setzt `cancelled_at`, ruft Auto-Refund auf, gibt `RefundSummary` zurück
- `event_service._ensure_event_active()` — Helper für Cancel-Locks
- `event_service._refund_all_paid_orders()` — Stripe-Refunds beim Absagen
- `event_service.get_public_events()` — filtert `cancelled_at IS NOT NULL` aus (Discovery)
- `event_service.get_event_by_id()` — gibt abgesagtes Event unverändert zurück (kein 48h-Gate mehr)
- `user_service.list_user_events()` — listet Host- und Attendee-Events inkl. abgesagter
- `payment_service._refund_single_order()` — wiederverwendbarer Refund-Kern
- `reminder_scheduler` — keine Reminders für `cancelled_at IS NOT NULL` Events
