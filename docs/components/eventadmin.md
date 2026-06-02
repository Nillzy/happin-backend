# EventAdmin

**Kategorie:** A-Software  
**Entwurfs-Entsprechung:** `<<component>> EventAdmin` (im Anwendungskern)  
**Implementierung:** `app/services/event_service.py` (Schreib-Operationen), `app/services/custom_field_service.py`

## Beschreibung

Die `EventAdmin`-Komponente stellt alle Funktionen zur Verwaltung von Events bereit: Erstellen, Bearbeiten, Absagen sowie die Verwaltung benutzerdefinierter Felder (Custom Fields) für Anmeldeformulare.

## Bereitgestellte Schnittstellen

| Schnittstelle | Endpunkt | Beschreibung |
|---|---|---|
| `EventAdmin` (Create) | `POST /api/v1/events/` | Neues Event erstellen |
| `EventAdmin` (Update) | `PATCH /api/v1/events/{event_id}` | Event bearbeiten (nur Host) |
| `EventAdmin` (Cancel) | `POST /api/v1/events/{event_id}/cancel` | Event absagen + Erstattungen auslösen |
| `EventAdmin` (CustomFields) | `POST /api/v1/events/{event_id}/custom_fields` | Benutzerdefinierte Felder anlegen |
| `EventAdmin` (FieldResponses) | `POST /api/v1/events/{event_id}/custom_fields/{id}/responses` | Feldantworten speichern |

## Genutzte Schnittstellen

- **`Write`** (DatabaseAdapter): Schreibt Event-Datensätze, Custom Fields und Antworten
- **`Read`** (DatabaseAdapter): Prüft Eigentümerschaft vor Änderungen
- **`Withdraw`** (PaymentAdapter): Löst Stripe-Erstattungen beim Absagen aus

## Implementierung

### Event-Erstellung

```python
# app/services/event_service.py
async def create_event(
    data: EventCreate,
    current_user: dict
) -> dict:
    # 1. Koordinaten geocodieren (MapsAdapter)
    # 2. Event in Supabase anlegen
    # 3. Ticket-Optionen anlegen (ticket_option_service)
    # 4. Event-ID zurückgeben
```

### Event-Absage mit automatischen Erstattungen

```python
async def cancel_event(event_id: str, host: dict) -> RefundSummary:
    # 1. Eigentümerschaft prüfen
    # 2. Alle bezahlten Buchungen laden
    # 3. Stripe-Erstattungen mit Idempotenzschlüsseln auslösen
    # 4. Event als cancelled markieren
    # 5. RefundSummary zurückgeben
```

### Custom Fields (Anmeldeformulare)

Custom Fields ermöglichen es Hosts, eigene Pflichtfelder für Anmeldungen zu definieren (z. B. „Ernährungseinschränkungen", „T-Shirt-Größe"):

```python
class CustomField(BaseModel):
    label: str
    field_type: Literal["text", "select", "checkbox"]
    required: bool
    options: list[str] | None   # für select
```

## Sicherheit

- Nur der Event-Host darf eigene Events bearbeiten oder absagen
- Überprüfung über Supabase Row-Level Security (RLS) + explizite Host-Prüfung im Service

## Abhängigkeiten

- [`DatabaseAdapter`](database-adapter.md)
- [`PaymentAdapter`](payment-adapter.md) – für Erstattungen bei Absagen
- [`MapsAdapter`](maps-adapter.md) – für Koordinaten-Geocoding bei Event-Erstellung
