# RSVP

**Kategorie:** A-Software  
**Entwurfs-Entsprechung:** `<<component>> RSVP` (im Anwendungskern)  
**Implementierung:** `app/services/booking_service.py`, `app/services/waitlist_service.py`

## Beschreibung

Die `RSVP`-Komponente verwaltet die Anmeldung von Nutzern zu Events. Sie unterscheidet zwischen kostenfreien RSVP-Zusagen und kostenpflichtigen Ticketbuchungen und steuert Wartelisten für ausgebuchte Events.

[→ Im Architekturentwurf ansehen](<https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Entwurf/Komponentendiagramm#:~:text=Co%2DHosts%20persistieren)-,RSVP,-M5%20(RSVP%20speichern>)

## Bereitgestellte Schnittstellen

| Schnittstelle | Endpunkt | Beschreibung |
|---|---|---|
| `RSVP` (Status setzen) | `POST /api/v1/events/{event_id}/rsvp` | RSVP-Status setzen (attending / not_attending) |
| `RSVP` (Waitlist) | `POST /api/v1/events/{event_id}/waitlist` | Warteliste beitreten |
| `RSVP` (Cancel) | `DELETE /api/v1/events/{event_id}/rsvp` | RSVP zurückziehen |

## Genutzte Schnittstellen

- **`Read`** (DatabaseAdapter): Liest aktuellen RSVP-Status, verfügbare Plätze
- **`Write`** (DatabaseAdapter): Schreibt RSVP-Einträge, Wartelisten-Einträge
- **`Pay`** (PaymentAdapter): Löst Stripe-Checkout für kostenpflichtige Buchungen aus

## RSVP-Zustände

```
             ┌──────────┐
             │  (none)  │
             └────┬─────┘
                  │ RSVP
         ┌────────▼─────────┐
    ┌────┤   pending /      ├────┐
    │    │   confirmed      │    │
    │    └──────────────────┘    │
    │ Cancel                     │ Event voll
    ▼                            ▼
 (none)                    ┌──────────┐
                           │Waitlist  │
                           └──────────┘
```

## Implementierung

### RSVP für kostenfreie Events

```python
# app/services/booking_service.py
async def rsvp_event(
    event_id: str,
    user_id: str,
    status: Literal["attending", "not_attending"]
) -> dict:
    # 1. Event laden, Kapazität prüfen
    # 2. Vorhandenen RSVP-Eintrag aktualisieren oder anlegen
    # 3. Benachrichtigung an Host auslösen
```

### Wartelisten-Verwaltung

```python
# app/services/waitlist_service.py
async def join_waitlist(event_id: str, user_id: str) -> dict:
    # 1. Prüfen ob Nutzer bereits auf Warteliste
    # 2. Wartelisten-Eintrag anlegen
    # 3. Position auf Warteliste zurückgeben

async def promote_from_waitlist(event_id: str) -> None:
    # Wird aufgerufen wenn Platz frei wird (Stornierung)
    # Nächste Person auf Warteliste benachrichtigen
```

## Abhängigkeiten

- [`DatabaseAdapter`](database-adapter.md)
- [`PaymentAdapter`](payment-adapter.md) – für kostenpflichtige Buchungen
- [`Notification`](notification.md) – Benachrichtigung des Hosts
