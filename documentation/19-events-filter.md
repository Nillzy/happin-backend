# 19 — Events API: Filter Parameters

## Overview

`GET /api/v1/events/` accepts optional query parameters for filtering the event list.
All parameters are optional; omitting them returns all upcoming public events (default behaviour unchanged).

## Query Parameters

| Param | Type | Description |
|---|---|---|
| `date_from` | ISO datetime string | Lower bound for `starts_at` (inclusive). Defaults to `now()` if omitted. |
| `date_to` | ISO datetime string | Upper bound for `starts_at` (inclusive). No upper bound if omitted. |
| `categories` | comma-separated string | e.g. `Musik,Sport`. Events matching any listed category are included (OR logic). |
| `city` | string | Case-insensitive match against `location.city`. |
| `is_free` | boolean | When `true`, only free events are returned. |

## Implementation

### API Layer (`app/api/v1/events.py`)

Filter params are declared as FastAPI `Query` parameters on `list_public_events` and
forwarded verbatim to `event_service.get_public_events()`.

### Service Layer (`app/services/event_service.py`)

`get_public_events` applies filters in two stages:

**Stage 1 — Supabase query filters (database level):**
- `date_from` → `.gte("starts_at", date_from)` (defaults to `datetime.now(UTC)`)
- `date_to` → `.lte("starts_at", date_to)`
- `is_free=True` → `.eq("is_free", True)`

**Stage 2 — Python post-fetch filters:**
- `city` → case-insensitive equality match on `event["location"]["city"]`
- `categories` → any category in the comma-separated list must appear as substring in `event["category"]`

Post-fetch filtering is used for city and categories because the `category` column stores
a comma-separated string and the `location` table is a joined relation, making server-side
OR filtering cumbersome.

## Tests

Filter behaviour is covered in `tests/test_events_filter.py`:
- `test_filter_by_city` — city match returns only matching events
- `test_filter_by_city_case_insensitive` — lowercase query matches mixed-case city
- `test_filter_by_category` — single category filter
- `test_filter_by_multiple_categories` — OR logic across two categories
- `test_filter_by_is_free` — boolean filter applied at DB level
- `test_no_filter_returns_all` — no params → all events returned
- `test_filter_city_no_match` — unknown city → empty list
