# PaymentAdapter

**Kategorie:** T-Software  
**Entwurfs-Entsprechung:** `<<component>> PaymentAdapter`  
**Implementierung:** `app/adapters/stripe_payment.py`, `app/services/payment_service.py`, `app/services/stripe_webhook_service.py`

## Beschreibung

Der `PaymentAdapter` kapselt die Kommunikation mit dem externen Zahlungsdienst **Stripe Connect**. Er stellt dem Anwendungskern die Schnittstellen `Pay` (Zahlungsabwicklung) und `Withdraw` (Erstattungen) bereit.

Stripe Connect ermöglicht es, dass Ticket-Einnahmen direkt auf das Stripe-Konto des Event-Hosts ausgezahlt werden, ohne dass Happin als Zwischenhändler fungiert.

## Bereitgestellte Schnittstellen

| Schnittstelle | Genutzt von | Beschreibung |
|---|---|---|
| `Pay` | RSVP, Ticketing | Stripe-Checkout-Session für Ticketkauf erstellen |
| `Withdraw` | EventAdmin | Erstattung auslösen bei Event-Absage (S2) |

## Genutzter externer Dienst

**Stripe** (AT-Software) – Zahlungsabwicklung, Connect-Konten für Hosts, Webhooks.

## Implementierung

### Stripe-Wrapper (`stripe_payment.py`)

```python
# app/adapters/stripe_payment.py

async def create_express_account(email: str) -> str:
    """Erstellt ein Stripe Express-Konto für einen neuen Host."""
    account = stripe.Account.create(type="express", email=email)
    return account.id

async def create_account_link(account_id: str, ...) -> str:
    """Erzeugt Onboarding-Link für den Host."""
    link = stripe.AccountLink.create(account=account_id, ...)
    return link.url

async def create_login_link(account_id: str) -> str:
    """Erzeugt Login-Link zum Stripe Dashboard des Hosts."""

async def set_manual_payouts(account_id: str) -> None:
    """Stellt manuelle Auszahlungen für das Host-Konto ein."""
```

### Payment-Service (`payment_service.py`)

```python
# app/services/payment_service.py

async def create_checkout_session(
    event_id: str,
    ticket_option_id: str,
    quantity: int,
    user: dict
) -> str:
    """Erstellt Stripe Checkout-Session, gibt URL zurück."""

async def process_refund(
    payment_intent_id: str,
    amount: float,
    idempotency_key: str
) -> None:
    """Löst Erstattung mit Idempotenzschlüssel aus."""
```

### Webhook-Handler (`stripe_webhook_service.py`)

Stripe sendet Webhook-Events an `/api/v1/payments/webhook`. Verarbeitete Events:

| Stripe-Event | Aktion |
|---|---|
| `checkout.session.completed` | Buchung abschließen, Ticket erstellen |
| `account.updated` | Host-Stripe-Status aktualisieren |
| `payment_intent.payment_failed` | Buchung als fehlgeschlagen markieren |

## Konfiguration

| Umgebungsvariable | Beschreibung |
|---|---|
| `STRIPE_SECRET_KEY` | Stripe API-Schlüssel |
| `STRIPE_WEBHOOK_SECRET` | Webhook-Signaturschlüssel |

## Abhängigkeiten

- Stripe (AT-Software, externer Dienst)
- [`DatabaseAdapter`](database-adapter.md) – Buchungsstatus speichern
- [`Ticketing`](ticketing.md) – Ticket nach erfolgreicher Zahlung erstellen
