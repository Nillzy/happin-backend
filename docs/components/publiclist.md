# PublicList

**Kategorie:** A-Software  
**Entwurfs-Entsprechung:** `<<component>> PublicList` (im Anwendungskern)  
**Implementierung:** `app/services/event_service.py` (öffentliche Abfragen)

## Beschreibung

Die `PublicList`-Komponente stellt die gefilterte, paginierte öffentliche Event-Liste bereit. Sie entspricht dem Workflow M11 (öffentliche Eventliste) aus dem Pflichtenheft und ist die am häufigsten aufgerufene Komponente.

[→ Im Architekturentwurf ansehen](<https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Entwurf/Komponentendiagramm#:~:text=Host%2DEinladung%20versenden)-,PublicList,-M11%20(%C3%96ffentliche%20Events>)

## Bereitgestellte Schnittstellen

| Schnittstelle | Endpunkt | Beschreibung |
|---|---|---|
| `PublicList` | `GET /api/v1/events/` | Paginierte, gefilterte öffentliche Event-Liste |

## Genutzte Schnittstellen

- **`Read`** (DatabaseAdapter): Liest Events mit Filterbedingungen

## Filterparameter

| Parameter | Typ | Beschreibung |
|---|---|---|
| `search` | `string` | Volltextsuche in Titel und Beschreibung |
| `categories` | `list[string]` | Kategoriefilter (mehrfach möglich) |
| `city` | `string` | Stadtfilter |
| `date_from` | `datetime` | Frühestes Startdatum |
| `date_to` | `datetime` | Spätestes Startdatum |
| `is_free` | `bool` | Nur kostenfreie Events |
| `limit` | `int` | Seitengröße (Standard: 20) |
| `offset` | `int` | Offset für Infinite Scroll |

## Implementierung

```python
# app/services/event_service.py
async def get_public_events(
    search: str | None = None,
    categories: list[str] | None = None,
    city: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    is_free: bool | None = None,
    limit: int = 20,
    offset: int = 0
) -> list[EventListItem]:
    # Supabase-Query mit dynamischen Filtern
    # Nur öffentliche, nicht abgesagte, zukünftige Events
    # Ortsabstraktion: keine genaue Adresse in der Liste
```

### Infinite Scroll / Pagination

Die Liste unterstützt Infinite-Scroll-Pagination über `limit` und `offset`:

```
GET /api/v1/events/?limit=20&offset=0   → erste Seite
GET /api/v1/events/?limit=20&offset=20  → zweite Seite
```

### Listenobjekt (Response)

```python
class EventListItem(BaseModel):
    id: str
    title: str
    start_time: datetime
    city: str
    district: str           # kein genauer Ort in der öffentlichen Liste
    categories: list[str]
    cover_image_url: str | None
    is_free: bool
    price_from: float | None
    rsvp_count: int
```

## Abhängigkeiten

- [`DatabaseAdapter`](database-adapter.md)
