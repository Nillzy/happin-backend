# Kalenderexport (ICS)

## Übersicht

Der Kalenderexport ermöglicht es Nutzern, Events als ICS-Datei herunterzuladen und in ihren persönlichen Kalender (Apple Calendar, Google Calendar, Outlook, etc.) zu importieren.

**Anforderung:** "Man könnte [...] per Kalenderexport das Event 'automatisch' im Kalender vormerken."

---

## Endpoint

### `GET /api/v1/events/{event_id}/calendar.ics`

| Eigenschaft | Wert |
|-------------|------|
| Auth | Optional (Bearer JWT) |
| Response | `text/calendar` (ICS-Datei) |
| Fehler | 404 (Event nicht gefunden) |

**Authentifizierung:** Optional. Ohne Token sind nur öffentliche Events abrufbar. Mit Token können auch private Events exportiert werden (sofern der User Zugang hat).

**Response Headers:**
```
Content-Type: text/calendar; charset=utf-8
Content-Disposition: attachment; filename="event-{event_id}.ics"
```

---

## ICS-Format

Das generierte ICS folgt dem [iCalendar-Standard (RFC 5545)](https://datatracker.ietf.org/doc/html/rfc5545):

```ics
BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Happin//Event Calendar//DE
CALSCALE:GREGORIAN
METHOD:PUBLISH
BEGIN:VEVENT
UID:35b43254-4e21-459f-b729-4cb3966cf322@happin.app
SUMMARY:Techno Night Berlin
DESCRIPTION:Eine legendäre Nacht.
DTSTART:20260510T220000Z
DTEND:20260511T060000Z
LOCATION:Revaler Str. 99, 10245 Berlin, Deutschland
DTSTAMP:20260506T120000Z
END:VEVENT
END:VCALENDAR
```

### Feld-Mapping

| ICS-Feld | Quelle | Anmerkung |
|----------|--------|-----------|
| `UID` | `{event_id}@happin.app` | Eindeutige ID für Kalender-Updates |
| `SUMMARY` | `event.title` | Event-Titel |
| `DESCRIPTION` | `event.description` | Optional |
| `DTSTART` | `event.starts_at` | Startzeit (UTC) |
| `DTEND` | `event.ends_at` | Endzeit; falls NULL → Start + 2 Stunden |
| `LOCATION` | `location.*` | Formatierte Adresse |
| `DTSTAMP` | Server-Zeit | Generierungszeitpunkt |

### Adress-Formatierung

Die Location wird als Einzeiler formatiert:
```
{street} {house_number}, {postal_code} {city}, {country}
```

Fehlende Komponenten werden übersprungen.

---

## Abhängigkeiten

| Paket | Version | Zweck |
|-------|---------|-------|
| `icalendar` | 5.0.13 | ICS-Generierung nach RFC 5545 |

Installation: `pip install icalendar==5.0.13`

---

## Architektur

### Service-Layer

`app/services/calendar_service.py`:

| Funktion | Zweck |
|----------|-------|
| `get_event_for_calendar(event_id, token)` | Lädt Event-Daten für Export |
| `generate_ics(event_id, token)` | Generiert ICS-Bytes |
| `_format_location(location)` | Formatiert Location als Adress-String |

### API-Layer

`app/api/v1/events.py`:

Der Endpoint nutzt `fastapi.responses.Response` mit Custom-Content-Type statt eines JSON-Modells.

---

## Sicherheit

- **Öffentliche Events:** Ohne Token abrufbar (wie Event-Detail)
- **Private Events:** Nur mit gültigem JWT abrufbar
- **Keine sensiblen Daten:** ICS enthält nur öffentlich sichtbare Event-Informationen

---

## Frontend-Integration

### Download-Button

```typescript
const downloadCalendar = (eventId: string) => {
  window.open(`${API_URL}/api/v1/events/${eventId}/calendar.ics`);
};
```

### Mit Auth-Token (für private Events)

```typescript
const downloadCalendar = async (eventId: string, token: string) => {
  const response = await fetch(
    `${API_URL}/api/v1/events/${eventId}/calendar.ics`,
    { headers: { Authorization: `Bearer ${token}` } }
  );
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `event-${eventId}.ics`;
  a.click();
};
```

---

## Tests

Tests in `tests/test_calendar.py`:

| Test | Prüft |
|------|-------|
| `test_calendar_endpoint_returns_ics` | Endpoint liefert valides ICS |
| `test_calendar_contains_event_details` | Event-Daten im ICS enthalten |
| `test_calendar_endpoint_not_found` | 404 bei unbekanntem Event |
| `test_calendar_event_without_end_time` | Default-Dauer bei fehlendem `ends_at` |
| `test_calendar_event_without_location` | ICS ohne Location ist valide |
| `test_calendar_uid_format` | UID folgt erwartetem Format |

---

## Dateien

| Datei | Rolle |
|-------|-------|
| `requirements.txt` | `icalendar==5.0.13` hinzugefügt |
| `app/services/calendar_service.py` | ICS-Generierungs-Logik |
| `app/api/v1/events.py` | GET `/{event_id}/calendar.ics` Endpoint |
| `tests/test_calendar.py` | Unit-Tests |
| `documentation/17-calendar-export.md` | Diese Dokumentation |

---

## Zukünftige Erweiterungen

| Feature | Beschreibung |
|---------|--------------|
| `VALARM` | Erinnerung X Minuten vor Event |
| `ORGANIZER` | Host-Email als Organisator |
| `ATTACH` | Event-Bild als Anhang |
| Recurring Events | RRULE für wiederkehrende Events |
