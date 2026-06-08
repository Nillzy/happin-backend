# Gästelisten-Export (S8)

Hosts können die Gästeliste eines Events als CSV oder PDF exportieren. Pflichtenheft-Anforderung S8: Export von 500 Einträgen muss in ≤10 s fertig sein.

## Endpoint

```
GET /api/v1/events/{event_id}/export
```

**Query-Parameter:**

| Name | Typ | Default | Beschreibung |
|---|---|---|---|
| `format` | `csv` \| `pdf` | — (required) | Ausgabeformat |
| `include_rsvp_responses` | `bool` | `false` | Wenn `true`, wird je Custom Field eine eigene Spalte angehängt |

**Auth:** Nur Hosts. `get_current_user` + `event_service.is_user_host()`. Nicht-Host → `403`.

**Response:**

- `200` mit `Content-Disposition: attachment; filename="gaesteliste_{event_id}_{YYYY-MM-DD}.{ext}"`
- CSV: `Content-Type: text/csv; charset=utf-8`, UTF-8 mit BOM, CRLF-Newlines, Excel-kompatibel
- PDF: `Content-Type: application/pdf`, A4 Querformat
- `422` bei ungültigem `format` (FastAPI Literal-Validation)

## Datenmodell

**Filter:** Nur Teilnehmer mit `participation.status == "accepted"` (case-insensitiv).

**Granularität:** Eine Zeile pro Ticket. Hat ein Käufer mehrere Tickets (z.B. „2× Standard, 1× VIP"), entstehen drei Zeilen.

**Sortierung:** stabil nach `(Nachname, Vorname, Ticket-Option)` — Tickets eines Käufers erscheinen damit konsekutiv.

**Spalten (Basis, immer enthalten):**

| Spalte | Quelle |
|---|---|
| `Vorname` | `participant.person.first_name` |
| `Nachname` | `participant.person.last_name` (kann leer sein) |
| `Ticket-Option` | `ticket_response.ticket_option_name` |
| `Gast-Name` | `ticket_response.guest_name` (Name auf dem Ticket; kann leer sein) |

**Spalten (mit `include_rsvp_responses=true`):** Eine zusätzliche Spalte je Custom Field, Reihenfolge stabil aus `custom_field.sort_order`. Spaltenname: `rsvp_<custom_field.label>`.

**Wert-Normalisierung in Custom-Field-Zellen:**

| Eingabe | Ausgabe |
|---|---|
| `None` | `""` |
| `True` / `False` | `"ja"` / `"nein"` |
| `list` (Multi-Select) | mit `"; "` joined |
| `str`, `int`, … | `str(value)` |

## Datenschutz

**Telefonnummern werden bewusst NICHT exportiert**, obwohl `participant.person` das Feld enthält. Hosts erhalten Personenkontakt nur über die App, nicht in austauschbaren Dateien.

## Architektur

```
backend/app/services/export/
├── __init__.py
├── export_service.py    # build_rows: Filter + Explode + Sort
├── csv_renderer.py      # render_csv: stdlib csv → UTF-8 BOM bytes
└── pdf_renderer.py      # render_pdf: reportlab Platypus → PDF bytes
```

- **`export_service.build_rows(participants, custom_fields, include_rsvp_responses) → (headers, rows)`** ist eine reine Funktion ohne I/O — gut testbar und format-agnostisch.
- **`event_service.get_event_participants()`** wird unverändert wiederverwendet (auch von `GET /participants`).
- **`custom_field_service.get_custom_fields(event_id)`** liefert die Felder bereits sortiert nach `sort_order`.

## PDF-Layout

- A4 Querformat, 1.5 cm Ränder
- Titelblock: „Gästeliste – {Event-Name}", Event-Datum, Anzahl akzeptierter Tickets, Erstellungsdatum
- Tabelle: dunkler Header, alternierende Zeilen, dünne Gitterlinien, Schriftgröße 9 pt
- Bei vielen Custom-Field-Spalten reduziert der Renderer die Schriftgröße automatisch (9 → 8 → 7 pt). Unter 7 pt: harter Truncate auf 20 Zeichen mit „…"
- Footer: Seitenzahl rechts unten

## Performance

Erwartete Latenz für 500 Tickets:

- Daten holen (Supabase, 2 Queries): ~1–2 s
- `build_rows`: <0.05 s
- CSV: <0.1 s
- PDF: ~2–4 s

Gesamt: deutlich unter dem 10-s-Budget. Kein Streaming, kein Job-System.

## Dependencies

- **`reportlab==4.2.5`** (neu, in `requirements.txt`) — PDF-Generierung
- **`pypdf==5.1.0`** (neu, dev) — für Tests, falls inhaltliche PDF-Verifikation gebraucht wird

## Tests

`backend/tests/test_export.py`:

- 8× Unit-Tests für `build_rows` (Filter, Explode, Sortierung, Wert-Normalisierung, fehlender Nachname, Telefonnummer-Ausschluss)
- 4× Unit-Tests für `csv_renderer` (BOM, CRLF, Umlaute, Quoting)
- 3× Unit-Tests für `pdf_renderer` (PDF-Header, leere Zeilen, viele Spalten)
- 8× HTTP-Tests für den Endpoint (CSV/PDF 200, 403 für Non-Host, ungültiges Format, RSVP-Spalten an/aus, Telefonnummer-Ausschluss, Header-only bei 0 Akzeptierten)

23 neue Tests, alle grün, keine Regression in den 94 bestehenden Tests.
