# TicketGenerationAdapter

**Kategorie:** T-Software  
**Entwurfs-Entsprechung:** `<<component>> TicketGenerationAdapter`  
**Implementierung:** `app/services/export/`

## Beschreibung

Der `TicketGenerationAdapter` ist verantwortlich für die Erzeugung von CSV- und PDF-Exporten der Gästeliste (S8). Er wird von der `Ticketing`-Komponente über die Schnittstelle `GenerateTicket` aufgerufen. Intern delegiert er an spezialisierte Renderer-Komponenten: `CSVGenerator` und `PDFGenerator`.

Diese Komponente wurde im Entwurf explizit als T-Software eingestuft, da sie auf generische Python-Bibliotheken zurückgreift.

## Bereitgestellte Schnittstellen

| Schnittstelle | Genutzt von | Beschreibung |
|---|---|---|
| `GenerateTicket` (CSV) | Ticketing | Gästeliste als CSV exportieren |
| `GenerateTicket` (PDF) | Ticketing | Gästeliste als PDF exportieren |

## Unterkomponenten

### CSVGenerator (`csv_renderer.py`)

**Kategorie:** T-Software (Python-Standardbibliothek `csv`)

```python
# app/services/export/csv_renderer.py

def render_csv(headers: list[str], rows: list[list[str]]) -> bytes:
    """
    Erzeugt UTF-8-BOM CSV (kompatibel mit Microsoft Excel).
    """
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(headers)
    writer.writerows(rows)
    return output.getvalue().encode("utf-8-sig")
```

### PDFGenerator (`pdf_renderer.py`)

**Kategorie:** T-Software (ReportLab-Bibliothek)

```python
# app/services/export/pdf_renderer.py

def render_pdf(
    title: str,
    headers: list[str],
    rows: list[list[str]]
) -> bytes:
    """
    Erzeugt A4-Querformat PDF mit dynamischer Schriftgrößen-
    anpassung und Textkurzung bei langen Spaltenwerten.
    """
    # ReportLab Table mit automatischer Spaltenbreite
    # Schriftgröße wird reduziert wenn Tabelle zu breit
```

### Export-Koordinator (`export_service.py`)

```python
# app/services/export/export_service.py

def build_rows(
    participants: list[dict],
    custom_fields: list[dict],
    field_responses: list[dict]
) -> tuple[list[str], list[list[str]]]:
    """
    Wandelt Teilnehmerdaten + Custom-Field-Antworten
    in Header + Zeilen für CSV/PDF-Export um.
    Filtert nur akzeptierte Teilnehmer.
    """
```

## Exportformat

Die Gästeliste enthält folgende Spalten:

| Spalte | Beschreibung |
|---|---|
| Name | Anzeigename des Teilnehmers |
| E-Mail | E-Mail-Adresse |
| Ticket-Typ | Name der Ticketoption |
| Preis | Bezahlter Betrag |
| Status | attending / checked_in |
| *Custom Fields* | Alle benutzerdefinierten Felder des Events |

## Endpunkte

```
GET /api/v1/events/{event_id}/export/csv   → CSV-Download
GET /api/v1/events/{event_id}/export/pdf   → PDF-Download
```

Beide Endpunkte sind nur für den Event-Host zugänglich.

## Abhängigkeiten

- Python `csv` (Standardbibliothek, T-Software)
- ReportLab (Open-Source-Bibliothek, T-Software)
- [`DatabaseAdapter`](database-adapter.md) – Teilnehmer- und Custom-Field-Daten
