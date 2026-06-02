# Architektur

## Komponentendiagramm

Das folgende Diagramm zeigt den ursprünglichen Architekturentwurf des Happin-Backends.

![Architekturdiagramm Backend](assets/architecture.png)

Die Backend-Komponenten lassen sich in drei Schichten einteilen:

1. **API-Schicht** – der `APIAdapter` empfängt alle HTTP-Anfragen
2. **Anwendungskern** – fachliche Komponenten für Events, Tickets, Zahlungen usw.
3. **Adapter-Schicht** – kapselt alle externen Dienste und die Datenbank

---

## Entwurf vs. Implementierung

### APIAdapter

*✅ vollständig umgesetzt*

Der Entwurf sieht einen zentralen `APIAdapter` vor, der alle API-Schnittstellen bereitstellt. In der Implementierung entspricht dieser dem Modul `app/api/v1/` mit dem aggregierenden `router.py` sowie den einzelnen Router-Dateien (`events.py`, `tickets.py`, `payments.py`, …).

Die im Entwurf definierten Schnittstellen sind direkt als FastAPI-Endpunkte realisiert:

| Entwurfs-Schnittstelle | Implementierung |
|---|---|
| `AuthAPI` | `app/api/v1/user.py`, `app/api/v1/users.py` |
| `EventInfoAPI` | `app/api/v1/events.py` (GET-Endpunkte) |
| `EventAdminAPI` | `app/api/v1/events.py` (POST/PATCH/DELETE) |
| `RSVPAPI` | `app/api/v1/events.py` (RSVP-Endpunkte) |
| `HostDashboardAPI` | `app/api/v1/events.py`, `app/api/v1/users.py` |
| `NotificationAPI` | `app/api/v1/notifications.py` |
| `PublicListAPI` | `app/api/v1/events.py` (öffentliche Listenendpunkte) |
| `TicketingAPI` | `app/api/v1/tickets.py`, `app/api/v1/ticket_options.py` |

### Authentication

*✅ vollständig umgesetzt*

Die `Authentication`-Komponente ist als `app/core/auth.py` umgesetzt. Die Schnittstellen `Register`, `Login`, `Logout` und `Delete` werden von Supabase Auth übernommen – das Backend validiert lediglich die JWT-Tokens. Registrierung und Login erfolgen clientseitig über Supabase; das Backend stellt `get_current_user()` als FastAPI-Dependency bereit.

!!! note "Abweichung vom Entwurf"
    Im Entwurf verwaltet die `Authentication`-Komponente Register/Login/Logout/Delete direkt. In der Implementierung wird **Supabase Auth** als externer Dienst eingesetzt: Registrierung, OTP-Verifikation und Session-Verwaltung übernimmt vollständig Supabase. Das Backend ist damit für die eigentliche Authentifizierungslogik zuständigkeitsfrei und validiert nur eingehende JWTs.

### MessagingAdapter

*✅ umgesetzt – E-Mail statt SMS*

Der `MessagingAdapter` ist als `app/services/email_service.py` umgesetzt, der den Dienst **Resend** über dessen REST-API nutzt. 

!!! note "Abweichung vom Entwurf"
    Im ursprünglichen Entwurf war die Verifikation per **Handynummer (SMS)** vorgesehen (M1). Die Implementierung verwendet stattdessen **E-Mail-OTP** über Supabase Auth + Resend. Diese Entscheidung wurde getroffen, weil SMS-Dienste kostenpflichtig und schwerer zu testen sind.

### Anwendungskern

*✅ vollständig umgesetzt*

Der Anwendungskern besteht in der Implementierung aus dem `app/services/`-Verzeichnis. Jede Entwurfskomponente entspricht einem oder mehreren Service-Modulen:

| Entwurfs-Komponente | Implementierung |
|---|---|
| `EventInfo` | `event_service.py` (Lesen) |
| `EventAdmin` | `event_service.py` (Schreiben), `custom_field_service.py` |
| `RSVP` | `booking_service.py`, `waitlist_service.py` |
| `HostDashboard` | `user_service.py`, `person_service.py` |
| `Notification` | `notification_service.py`, `reminder_service.py`, `expo_push_service.py` |
| `PublicList` | `event_service.py` (gefilterte öffentliche Abfragen) |
| `Ticketing` | `ticket_service.py`, `ticket_option_service.py`, `calendar_service.py`, `google_wallet_service.py` |

### DatabaseAdapter

*✅ umgesetzt – Supabase statt generisch*

Der `DatabaseAdapter` ist als `app/core/supabase.py` sowie der Supabase Python-Client realisiert. Die Schnittstellen `Auth` (DBAuth), `Read` und `Write` (DBData) werden durch den Supabase-Client bereitgestellt.

### PaymentAdapter

*✅ umgesetzt*

Der `PaymentAdapter` entspricht `app/adapters/stripe_payment.py` + `app/services/payment_service.py` + `app/services/stripe_webhook_service.py`. Externer Dienst ist **Stripe Connect**.

### MapsAdapter

*✅ umgesetzt*

Der `MapsAdapter` ist als `app/services/geocoding_service.py` umgesetzt und kommuniziert mit **MapTiler**.

### WeatherAdapter

*✅ umgesetzt*

Der `WeatherAdapter` entspricht `app/adapters/weatherapi.py` + `app/services/weather_service.py`. Externer Dienst ist **WeatherAPI.com**.

### TicketGenerationAdapter

*✅ umgesetzt*

Der `TicketGenerationAdapter` ist als `app/services/export/` umgesetzt mit:

- `export_service.py` – koordiniert den Export
- `csv_renderer.py` – erzeugt CSV-Dateien (CSVGenerator aus dem Entwurf)
- `pdf_renderer.py` – erzeugt PDF-Dateien mit ReportLab (PDFGenerator aus dem Entwurf)

Zusätzlich erzeugt `ticket_service.py` QR-Code-Token für digitale Tickets, und `google_wallet_service.py` generiert Google Wallet Passes – **beides ist eine Erweiterung über den ursprünglichen Entwurf hinaus**.

---

## Ergänzungen gegenüber dem Entwurf

Folgende Komponenten entstanden bei der Implementierung, die im ursprünglichen Architekturentwurf nicht explizit vorgesehen waren:

| Neue Komponente | Begründung |
|---|---|
| `reminder_scheduler.py` | APScheduler für zeitgesteuerte Push-Erinnerungen (K4) |
| `expo_push_service.py` | Expo Push API für native App-Benachrichtigungen |
| `google_wallet_service.py` | Google Wallet Passes als digitale Tickets |
| `calendar_service.py` | ICS-Kalenderexport für Events |
| `waitlist_service.py` | Wartelisten-Verwaltung bei ausgebuchten Events |
| `images.py` (Router) | Unsplash-Proxy für Event-Titelbilder |
