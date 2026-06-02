# Anwendungskern – Überblick

**Kategorie:** A-Software  
**Entwurfs-Entsprechung:** `<<component>> Anwendungskern`  
**Implementierung:** `app/services/`

## Beschreibung

Der Anwendungskern enthält die gesamte fachliche Logik des Happin-Backends. Er ist in mehrere Unterkomponenten gegliedert, die jeweils einer API-Schnittstelle des `APIAdapters` entsprechen. Alle Komponenten nutzen über den `DatabaseAdapter` die Supabase-Datenbank und kommunizieren bei Bedarf mit externen Adapter-Komponenten.

## Unterkomponenten

| Komponente | Zuständigkeit | Service-Dateien |
|---|---|---|
| [`EventInfo`](eventinfo.md) | Event-Details lesen | `event_service.py` |
| [`EventAdmin`](eventadmin.md) | Events erstellen, bearbeiten, absagen | `event_service.py`, `custom_field_service.py` |
| [`RSVP`](rsvp.md) | Anmeldung, Buchung, Warteliste | `booking_service.py`, `waitlist_service.py` |
| [`HostDashboard`](hostdashboard.md) | Host-Ansichten, Teilnehmerverwaltung | `user_service.py`, `person_service.py` |
| [`Notification`](notification.md) | In-App- und Push-Benachrichtigungen | `notification_service.py`, `reminder_service.py`, `expo_push_service.py` |
| [`PublicList`](publiclist.md) | Öffentliche Event-Suche und -Liste | `event_service.py` |
| [`Ticketing`](ticketing.md) | Ticketverwaltung, QR-Codes, Export | `ticket_service.py`, `ticket_option_service.py`, `calendar_service.py`, `google_wallet_service.py` |

## Abhängigkeiten

Der Anwendungskern nutzt folgende Adapter:

- [`DatabaseAdapter`](database-adapter.md) – `Read` und `Write` für alle Datenbankoperationen
- [`PaymentAdapter`](payment-adapter.md) – `Withdraw` und `Pay` (Ticketkauf, Erstattungen)
- [`MapsAdapter`](maps-adapter.md) – `ConvertCoordinates` (Geocoding)
- [`WeatherAdapter`](weather-adapter.md) – `GetWeather` (Wettervorhersage)
- [`TicketGenerationAdapter`](ticket-generation-adapter.md) – `GenerateTicket` (CSV/PDF-Export)
