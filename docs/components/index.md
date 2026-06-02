# Komponenten – Überblick

Das Happin-Backend besteht aus folgenden Komponenten, die nach den Schichten der Architektur gegliedert sind.

## Schichtenübersicht

```
┌─────────────────────────────────────────────────────────┐
│                     API-Schicht                         │
│                   [ APIAdapter ]                        │
│  AuthAPI  EventInfoAPI  RSVPAPI  TicketingAPI  ...      │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│              Authentifizierung                          │
│              [ Authentication ]                         │
│         Register  Login  Logout  Delete                 │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│                  Anwendungskern                         │
│  EventInfo  EventAdmin  RSVP  HostDashboard             │
│  Notification  PublicList  Ticketing                    │
└──┬──────────┬──────────┬──────────┬──────────┬──────────┘
   │          │          │          │          │
   ▼          ▼          ▼          ▼          ▼
Database  Messaging  Payment    Maps      Weather
Adapter   Adapter    Adapter   Adapter   Adapter
   │
   ▼
Supabase
```

## Komponentenliste

| Komponente | Schicht | Seite |
|---|---|---|
| `APIAdapter` | API-Schicht | [→](api-adapter.md) |
| `Authentication` | Authentifizierung | [→](authentication.md) |
| `EventInfo` | Anwendungskern | [→](eventinfo.md) |
| `EventAdmin` | Anwendungskern | [→](eventadmin.md) |
| `RSVP` | Anwendungskern | [→](rsvp.md) |
| `HostDashboard` | Anwendungskern | [→](hostdashboard.md) |
| `Notification` | Anwendungskern | [→](notification.md) |
| `PublicList` | Anwendungskern | [→](publiclist.md) |
| `Ticketing` | Anwendungskern | [→](ticketing.md) |
| `DatabaseAdapter` | Adapter-Schicht | [→](database-adapter.md) |
| `MessagingAdapter` | Adapter-Schicht | [→](messaging-adapter.md) |
| `PaymentAdapter` | Adapter-Schicht | [→](payment-adapter.md) |
| `MapsAdapter` | Adapter-Schicht | [→](maps-adapter.md) |
| `WeatherAdapter` | Adapter-Schicht | [→](weather-adapter.md) |
| `TicketGenerationAdapter` | Adapter-Schicht | [→](ticket-generation-adapter.md) |

## Software-Kategorien

Nach dem Komponentendiagramm werden folgende Software-Kategorien unterschieden:

- **A-Software** (grün): Eigenentwicklung – `APIAdapter`, `Authentication`, Anwendungskern-Komponenten
- **T-Software** (blau): Technisch generische Software – `DatabaseAdapter`, Adapter-Komponenten, Python-Bibliotheken (ReportLab)
- **AT-Software** (rot): Potenziell austauschbare Fremdsoftware – Resend, Stripe, MapTiler, WeatherAPI.com
