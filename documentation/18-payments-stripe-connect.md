# 18 – Zahlungen mit Stripe Connect (S2)

## Übersicht

Happin nutzt **Stripe Connect (Express)** für bezahlte Tickets. Die Plattform erstellt für jeden Host ein Express-Konto; Gäste bezahlen über gehostete Stripe-Checkout-Seiten. Gelder werden per Destination Charge direkt auf das Connected-Account-Balance des Hosts transferiert (abzüglich Plattformgebühr). Auszahlungen auf das Bankkonto des Hosts erfolgen manuell nach Event-Ende.

## Architektur

```
Gast → Frontend → Backend → Stripe Checkout Session (gehostet)
                                  ↓
                     Webhook (checkout.session.completed)
                                  ↓
                     ticket_order → paid → Tickets erzeugt
                                  ↓
                     Funds auf Host Connected Balance
```

### Charge-Typ: Destination Charges

- Zahlung wird auf dem **Plattform-Konto** erstellt
- Sofortiger Transfer an das Connected Account (Host)
- `application_fee_amount` wird vom Transfer abgezogen und geht an die Plattform
- Stripe-Verarbeitungsgebühren trägt die Plattform

### Accounts: Express

- Onboarding vollständig Stripe-gehostet (Account Links)
- Finanz-Dashboard für Hosts via Login Links
- Payout-Schedule: `manual` (Plattform triggert Auszahlung nach Event-Ende)

## Datenmodell

### Neue Felder auf `person`

| Spalte | Typ | Beschreibung |
|--------|-----|--------------|
| `stripe_connect_account_id` | text UNIQUE | Express Account ID (`acct_...`) |
| `stripe_connect_charges_enabled` | boolean | Kann Zahlungen empfangen |
| `stripe_connect_payouts_enabled` | boolean | Kann Auszahlungen erhalten |
| `stripe_connect_onboarding_completed_at` | timestamptz | Wann KYC abgeschlossen |

### Neue Tabelle `ticket_order`

| Spalte | Typ | Beschreibung |
|--------|-----|--------------|
| `ticket_order_id` | UUID PK | |
| `event_id` | UUID FK | |
| `person_id` | UUID FK | Käufer |
| `ticket_option_id` | UUID FK | Gewählte Option |
| `quantity` | integer | Anzahl Tickets |
| `amount_total_cents` | integer | Gesamtbetrag |
| `application_fee_cents` | integer | Plattformgebühr |
| `stripe_checkout_session_id` | text UNIQUE | Idempotenz-Schlüssel |
| `stripe_payment_intent_id` | text | |
| `status` | enum | `pending` / `paid` / `expired` / `failed` |
| `paid_at` | timestamptz | |

### Erweiterung `ticket`

- `ticket_order_id` (nullable FK) – verknüpft bezahlte Tickets mit ihrer Bestellung

### Erweiterung `event`

- `payout_person_id` (FK → person) – wer die Einnahmen erhält (Default: Event-Ersteller)

## API-Endpunkte

| Methode | Route | Auth | Beschreibung |
|---------|-------|------|--------------|
| POST | `/api/v1/connect/onboarding-link` | Host | Express Account + Account Link |
| GET | `/api/v1/connect/status` | Host | Onboarding-Status |
| POST | `/api/v1/connect/dashboard-link` | Host | Login Link für Express Dashboard |
| POST | `/api/v1/events/{id}/checkout-session` | Gast | Checkout Session erstellen |
| POST | `/api/v1/webhooks/stripe` | Stripe Sig | Webhook-Handler |
| GET | `/api/v1/events/{id}/payments/summary` | Host | Umsatz-Übersicht |
| POST | `/api/v1/events/{id}/payout` | Host | Auszahlung anfordern |

## Checkout-Flow

1. Gast wählt bezahlte Ticket-Option, klickt "Zur Kasse"
2. Frontend ruft `POST /events/{id}/checkout-session` auf
3. Backend erstellt `ticket_order` (status: `pending`) + Stripe Checkout Session
4. Frontend öffnet `checkout_url` (Stripe-gehostete Zahlungsseite)
5. Nach Zahlung: Stripe sendet `checkout.session.completed` Webhook
6. Backend prüft `payment_status == 'paid'`, erstellt Tickets + RSVP
7. Gast wird zu Success-Route redirected, sieht Ticket

### Sicherheit

- `POST /events/{id}/tickets` lehnt `ticket_option.price > 0` ab (HTTP 400)
- Webhook-Signatur wird mit `STRIPE_WEBHOOK_SECRET` verifiziert
- Idempotenz: doppelte Webhook-Events → `order.status == paid` → No-Op

## Gebührenmodell

- Konfiguriert via `PLATFORM_FEE_BPS` (Default: 500 = 5%)
- Berechnung: `round(amount_total_cents * BPS / 10000)`
- Host sieht nur die Plattformgebühr; Stripe Processing Fees trägt die Plattform

## Auszahlung

- Connected Accounts haben `payouts.schedule.interval = manual`
- Host kann nach Event-Ende (`starts_at < now`) Auszahlung anfordern
- Backend prüft verfügbares Balance und erstellt Stripe Payout
- Compliance DE: manuelle Auszahlung innerhalb 90 Tagen

## Environment-Variablen

| Variable | Beschreibung |
|----------|--------------|
| `STRIPE_SECRET_KEY` | API-Key (empfohlen: Restricted Key `rk_`) |
| `STRIPE_WEBHOOK_SECRET` | Webhook-Signatur-Secret (`whsec_...`) |
| `PLATFORM_FEE_BPS` | Plattformgebühr in Basispunkten (500 = 5%) |
| `STRIPE_CHECKOUT_SUCCESS_URL` | Redirect nach erfolgreicher Zahlung |
| `STRIPE_CHECKOUT_CANCEL_URL` | Redirect bei Abbruch |

## Lokale Entwicklung

```bash
# Stripe CLI für Webhook-Forwarding
stripe listen --forward-to localhost:8000/api/v1/webhooks/stripe

# Test-Checkout mit Stripe-Testkarten
# Visa: 4242 4242 4242 4242
# SEPA: DE89370400440532013000
```

## Migration

```bash
# Migration ausführen
supabase db push
# oder
supabase migration up
```
