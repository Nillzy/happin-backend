# 16. Infinity Scroll - Pagination Backend-Fix

## Übersicht

Backend-Anpassungen für Infinity Scroll im Frontend: API gibt jetzt Total-Count zurück statt nur Page-Count.

## Problem

**Vorher:**
```python
def get_public_events(limit: int = 50, offset: int = 0) -> list[dict]:
    # ...
    return events

# In events.py
return EventListResponse(events=events, count=len(events))
# count war immer = limit (z.B. 12), nicht die Gesamtzahl
```

**Resultat:** Frontend dachte es gäbe nur 12 Events total → Infinity Scroll stoppte nach erster Page.

## Lösung

### event_service.py

```python
def get_public_events(limit: int = 50, offset: int = 0, person_id: str | None = None) -> tuple[list[dict], int]:
    """
    Get public events with pagination.
    Returns (events, total_count) tuple.
    """
    supabase = get_supabase()

    # Get total count - separate query
    count_response = (
        supabase.table("event")
        .select("event_id", count="exact")
        .eq("is_public", True)
        .eq("status", "published")
        .execute()
    )
    total_count = count_response.count if hasattr(count_response, 'count') else 0

    # Get paginated events
    response = (
        supabase.table("event")
        .select(...)
        .eq("is_public", True)
        .eq("status", "published")
        .order("created_at", desc=True)
        .range(offset, offset + limit - 1)
        .execute()
    )

    events = response.data or []
    # ... (is_host logic)
    
    return events, total_count
```

**Änderungen:**
1. **Return-Type**: `list[dict]` → `tuple[list[dict], int]`
2. **Separate Count-Query**: Zählt ALLE Events (ohne Limit)
3. **Docstring**: Dokumentiert neues Return-Format

### events.py (API Route)

```python
@router.get("/", response_model=EventListResponse)
async def list_public_events(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    token: str | None = Depends(get_optional_token),
):
    person_id = None
    if token:
        person = await get_person_from_token(token)
        if not person:
            raise HTTPException(status_code=401, detail="Invalid token")
        person_id = person["person_id"]

    raw_events, total_count = event_service.get_public_events(
        limit=limit, 
        offset=offset, 
        person_id=person_id
    )
    events = [_to_list_item(e) for e in raw_events]
    return EventListResponse(events=events, count=total_count)
```

**Änderungen:**
1. **Tuple Unpacking**: `raw_events, total_count = ...`
2. **Count im Response**: `count=total_count` statt `count=len(events)`

## Response-Schema

```typescript
interface EventListResponse {
    events: EventListItem[];
    count: number;  // Gesamtzahl ALLER Events, nicht nur auf der Seite
}
```

**Beispiel:**
```json
{
    "events": [ /* 12 Events */ ],
    "count": 19  // ← Total, nicht 12!
}
```

## Frontend-Integration

```typescript
const loadMore = async () => {
    const offset = events.length;
    const data = await api.getPublicEvents(EVENTS_PER_PAGE, offset, token);
    
    setEvents(prev => [...prev, ...data.events]);
    setHasMore(events.length + data.events.length < data.count);
    //                                            ^^^^^^^^^^
    //                                    Total-Count vom Backend
};
```

## Performance

**Count-Query Performance:**
- Supabase cached Count-Queries intern
- `count="exact"` triggert PostgreSQL `COUNT(*)`
- Bei < 1000 Events: < 5ms
- Index auf `is_public` + `status` vorhanden

**Alternative für große Datenmengen:**
Falls > 10.000 Events:
```python
# Option 1: Approximation
count_response = supabase.rpc("count_public_events_approx").execute()

# Option 2: Cached Count (Update per Trigger)
count = supabase.table("event_stats").select("public_count").single().execute()
```

## Breaking Changes

### API Contract
- ❌ **Return-Type geändert**: `get_public_events()` gibt jetzt Tuple zurück
- ✅ **Response-Schema unverändert**: `EventListResponse` bleibt gleich

### Migration
Keine Migration nötig - nur Backend-Code-Änderung.

## Testing

### Manual Test
```bash
# Request Page 1
curl "http://localhost:8001/api/v1/events/?limit=12&offset=0"
# Response: { "events": [...], "count": 19 }

# Request Page 2
curl "http://localhost:8001/api/v1/events/?limit=12&offset=12"
# Response: { "events": [...], "count": 19 }  # ← Gleicher Count!

# Request Page 3
curl "http://localhost:8001/api/v1/events/?limit=12&offset=24"
# Response: { "events": [], "count": 19 }  # ← Keine Events mehr, Count bleibt
```

### Integration Test
```python
def test_infinity_scroll_count():
    # Create 19 events
    for i in range(19):
        create_event(...)
    
    # First page
    response1 = client.get("/api/v1/events/?limit=12&offset=0")
    assert len(response1.json()["events"]) == 12
    assert response1.json()["count"] == 19
    
    # Second page
    response2 = client.get("/api/v1/events/?limit=12&offset=12")
    assert len(response2.json()["events"]) == 7
    assert response2.json()["count"] == 19  # Same total!
```

## Betroffene Dateien

### Modifiziert
- `app/services/event_service.py`
  - `get_public_events()` Return-Type: `list[dict]` → `tuple[list[dict], int]`
  - Separate Count-Query hinzugefügt
  - Docstring aktualisiert

- `app/api/v1/events.py`
  - Tuple Unpacking: `raw_events, total_count = ...`
  - Response-Count: `count=total_count` statt `count=len(events)`

## Zukünftige Erweiterungen

1. **Count-Caching**: Redis-Cache für Total-Count (TTL: 5 min)
2. **Cursor-basierte Pagination**: Für bessere Performance bei großen Offsets
3. **Filter-Support**: Count muss Filter berücksichtigen (Kategorie, Location)
4. **Aggregation**: Count pro Kategorie für Filter-UI

## Related

- Frontend: `documentation/05-event-list-screen.md` (Infinity Scroll Implementation)
- API: `documentation/08-events-api.md` (GET /api/v1/events/ Endpoint)
