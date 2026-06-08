# Ticketing

**Kategorie:** A-Software  
**Entwurfs-Entsprechung:** `<<component>> Ticketing` (im Anwendungskern)  
**Implementierung:** `app/services/ticket_service.py`, `app/services/ticket_option_service.py`, `app/services/calendar_service.py`, `app/services/google_wallet_service.py`

## Beschreibung

Die `Ticketing`-Komponente ist verantwortlich für den gesamten Ticketlebenszyklus: Erstellung, Ausgabe, Validierung beim Einlass und Export. Sie wird bei Buchungen aufgerufen und stellt Tickets in verschiedenen Formaten bereit.

[→ Im Architekturentwurf ansehen](<https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Entwurf/Komponentendiagramm#:~:text=S7%20(Kategoriefilterung)-,Ticketing,-M8%20(Digitale%20Tickets>)

## Bereitgestellte Schnittstellen

| Schnittstelle | Endpunkt | Beschreibung |
|---|---|---|
| `Ticketing` (Buchen) | `POST /api/v1/events/{id}/tickets` | Ticket buchen (free oder paid) |
| `Ticketing` (Liste) | `GET /api/v1/events/{id}/tickets` | Gebuchte Tickets des Nutzers |
| `Ticketing` (Nutzer) | `GET /api/v1/users/tickets` | Alle Tickets eines Nutzers |
| `Ticketing` (Scan) | `POST /api/v1/events/{id}/scan` | QR-Code validieren (Einlass) |
| `Ticketing` (Kalender) | `GET /api/v1/events/{id}/calendar` | ICS-Kalenderexport |
| `Ticketing` (Wallet) | `GET /api/v1/events/{id}/wallet` | Google Wallet Pass |
| `Ticketing` (Options) | `GET/POST /api/v1/events/{id}/ticket_options` | Preisoptionen verwalten |

## Genutzte Schnittstellen

- **`Read` / `Write`** (DatabaseAdapter): Ticketdatensätze, Buchungen
- **`GenerateTicket`** (TicketGenerationAdapter): CSV/PDF-Export der Gästeliste (S8)

## Ticket-QR-Code

Jedes Ticket erhält einen signierten HMAC-Token als QR-Code. Die Signatur verhindert gefälschte Tickets:

```python
# app/core/ticket_token.py
def sign_ticket_token(ticket_id: str, event_id: str) -> str:
    payload = f"{ticket_id}:{event_id}"
    return hmac.new(SECRET_KEY, payload, sha256).hexdigest()

def verify_ticket_token(token: str, ticket_id: str, event_id: str) -> bool:
    expected = sign_ticket_token(ticket_id, event_id)
    return hmac.compare_digest(token, expected)
```

## Ticket-Optionen (Preisstufen)

Ein Event kann mehrere Ticket-Optionen mit unterschiedlichen Preisen haben:

```python
class TicketOption(BaseModel):
    id: str
    name: str            # z. B. "Regulär", "Early Bird"
    price: float         # 0.0 für kostenfreie Tickets
    capacity: int | None # None = unbegrenzt
    description: str | None
```

## Kalenderexport (ICS)

```python
# app/services/calendar_service.py
def generate_ics(event: dict) -> bytes:
    # Erzeugt RFC 5545-konformes ICS-Kalenderformat
    # Kompatibel mit Google Calendar, Apple Calendar, Outlook
```

## Google Wallet Integration

!!! note "Erweiterung gegenüber dem Entwurf"
    Google Wallet Passes waren im ursprünglichen Entwurf nicht vorgesehen und wurden als Zusatzfeature implementiert.

```python
# app/services/google_wallet_service.py
def create_wallet_pass(ticket: dict, event: dict) -> str:
    # Erzeugt signierten JWT für Google Wallet
    # Nutzt Google Service Account Credentials
```

## Abhängigkeiten

- [`DatabaseAdapter`](database-adapter.md)
- [`TicketGenerationAdapter`](ticket-generation-adapter.md) – CSV/PDF-Gästeliste
- `app/core/ticket_token.py` – HMAC-Token-Signierung
