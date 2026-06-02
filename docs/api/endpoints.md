# API-Endpunkte

Alle Endpunkte sind unter dem Präfix `/api/v1` erreichbar. Geschützte Endpunkte erfordern einen `Authorization: Bearer <JWT>`-Header.

!!! info "Authentifizierung"
    Alle Endpunkte erfordern `Authorization: Bearer <JWT>` – mit drei begründeten Ausnahmen, die unten mit ⚠️ markiert sind.

## Authentifizierung & Account

| Methode | Pfad | Auth | Beschreibung |
|---|---|---|---|
| `GET` | `/api/v1/user/me` | ✅ | Aktuellen Nutzer abrufen |
| `GET` | `/api/v1/users/me/profile` | ✅ | Account-Details |
| `PATCH` | `/api/v1/users/me/name` | ✅ | Anzeigename aktualisieren |
| `PATCH` | `/api/v1/users/me/city` | ✅ | Stadt aktualisieren |
| `PATCH` | `/api/v1/users/me/avatar` | ✅ | Avatar aktualisieren |
| `DELETE` | `/api/v1/users/me` | ✅ | Account löschen |
| `GET` | `/api/v1/users/me/stats` | ✅ | Host-Statistiken |
| `GET` | `/api/v1/users/me/tickets` | ✅ | Alle Tickets des Nutzers |

## Events

| Methode | Pfad | Auth | Beschreibung |
|---|---|---|---|
| `GET` | `/api/v1/events/` | ✅ | Event-Liste (mit Filtern) |
| `GET` | `/api/v1/events/me` | ✅ | Eigene Events |
| `GET` | `/api/v1/events/host/{person_id}` | ✅ | Events eines Hosts |
| `POST` | `/api/v1/events/` | ✅ | Neues Event erstellen |
| `GET` | `/api/v1/events/{id}` | ✅ | Event-Details |
| `PATCH` | `/api/v1/events/{id}` | ✅ | Event bearbeiten (nur Host) |
| `POST` | `/api/v1/events/{id}/cancel` | ✅ | Event absagen |

## RSVP, Warteliste & Teilnehmer

| Methode | Pfad | Auth | Beschreibung |
|---|---|---|---|
| `POST` | `/api/v1/events/{id}/rsvp` | ✅ | RSVP-Status setzen |
| `GET` | `/api/v1/events/{id}/participants` | ✅ | Teilnehmerliste (nur Host) |
| `DELETE` | `/api/v1/events/{id}/participants` | ✅ | Teilnehmer entfernen (nur Host) |
| `POST` | `/api/v1/events/{id}/waitlist` | ✅ | Warteliste beitreten |
| `DELETE` | `/api/v1/events/{id}/waitlist` | ✅ | Warteliste verlassen |
| `GET` | `/api/v1/events/{id}/waitlist/position` | ✅ | Position auf Warteliste |

## Tickets & Ticket-Optionen

| Methode | Pfad | Auth | Beschreibung |
|---|---|---|---|
| `GET` | `/api/v1/events/{id}/tickets` | ✅ | Tickets des Nutzers für Event |
| `POST` | `/api/v1/events/{id}/tickets/scan` | ✅ | Ticket scannen (nur Host) |
| `PUT` | `/api/v1/events/{id}/ticket-options` | ✅ | Ticket-Optionen anlegen/ersetzen |
| `GET` | `/api/v1/events/{id}/calendar.ics` | ✅ | Kalender-Export (ICS) |
| `GET` | `/api/v1/events/{id}/wallet` | ✅ | Google Wallet Pass |
| `GET` | `/api/v1/events/{id}/export` | ✅ | Gästeliste exportieren (CSV/PDF, nur Host) |

## Custom Fields

| Methode | Pfad | Auth | Beschreibung |
|---|---|---|---|
| `POST` | `/api/v1/events/{id}/custom_fields` | ✅ | Feld anlegen (Host) |
| `POST` | `/api/v1/events/{id}/custom_fields/{fid}/responses` | ✅ | Antwort einreichen |

## Zahlungen

| Methode | Pfad | Auth | Beschreibung |
|---|---|---|---|
| `POST` | `/api/v1/payments/connect/onboarding-link` | ✅ | Stripe Connect Onboarding-URL |
| `GET` | `/api/v1/payments/connect/status` | ✅ | Stripe-Konto-Status |
| `POST` | `/api/v1/payments/connect/dashboard-link` | ✅ | Stripe Dashboard-Login-URL |
| `POST` | `/api/v1/payments/events/{id}/checkout-session` | ✅ | Checkout-Session erstellen |
| `POST` | `/api/v1/payments/events/{id}/checkout-session/abandon` | ✅ | Session abbrechen |
| `GET` | `/api/v1/payments/events/{id}/checkout-session` | ✅ | Session-Status abfragen |
| `POST` | `/api/v1/payments/events/{id}/tickets/cancel` | ✅ | Ticket stornieren |
| `GET` | `/api/v1/payments/events/{id}/payments/summary` | ✅ | Zahlungsübersicht (Host) |
| `POST` | `/api/v1/payments/events/{id}/payout` | ✅ | Auszahlung anstoßen (Host) |
| `POST` | `/api/v1/payments/webhooks/stripe` | ⚠️ | Stripe-Webhook – kein JWT, aber Signaturprüfung via `STRIPE_WEBHOOK_SECRET` |

## Benachrichtigungen & Erinnerungen

| Methode | Pfad | Auth | Beschreibung |
|---|---|---|---|
| `GET` | `/api/v1/users/{id}/notifications` | ✅ | In-App-Benachrichtigungen |
| `PATCH` | `/api/v1/users/{id}/notifications/{nid}` | ✅ | Als gelesen markieren |
| `DELETE` | `/api/v1/users/{id}/notifications/{nid}` | ✅ | Benachrichtigung löschen |
| `POST` | `/api/v1/users/{id}/notifications/read-all` | ✅ | Alle als gelesen markieren |
| `GET` | `/api/v1/reminders/me/reminder-preferences` | ✅ | Erinnerungs-Einstellungen |
| `PATCH` | `/api/v1/reminders/me/reminder-preferences` | ✅ | Erinnerungs-Einstellungen aktualisieren |
| `POST` | `/api/v1/reminders/events/{id}/reminder` | ✅ | Erinnerung für Event setzen |
| `DELETE` | `/api/v1/reminders/events/{id}/reminder` | ✅ | Erinnerung löschen |
| `POST` | `/api/v1/reminders/push-subscriptions` | ✅ | Web-Push-Subscription registrieren |
| `DELETE` | `/api/v1/reminders/push-subscriptions/{id}` | ✅ | Push-Subscription löschen |
| `GET` | `/api/v1/reminders/push-subscriptions` | ✅ | Eigene Push-Subscriptions |
| `DELETE` | `/api/v1/reminders/push-tokens/{id}` | ✅ | Expo-Push-Token löschen |
| `GET` | `/api/v1/reminders/vapid-public-key` | ⚠️ | Öffentlicher VAPID-Schlüssel – kein schützenswerter Inhalt |

## Sonstiges

| Methode | Pfad | Auth | Beschreibung |
|---|---|---|---|
| `GET` | `/` | ⚠️ | Statusseite |
| `GET` | `/api/v1/health` | ⚠️ | Health-Check |
| `GET` | `/api/v1/images/search` | ⚠️ | Unsplash-Bildsuche (Proxy) – kein nutzerbezogener Inhalt |

## Filterparameter für `GET /api/v1/events/`

```
search=     Volltextsuche (Titel, Beschreibung)
categories= Kategorien (kommagetrennt)
city=       Stadtname
date_from=  ISO-8601-Datum
date_to=    ISO-8601-Datum
is_free=    true / false
limit=      Seitengröße (Standard: 20)
offset=     Offset für Pagination
```
