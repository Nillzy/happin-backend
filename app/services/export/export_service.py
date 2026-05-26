"""Build export rows from participant data + custom fields.

Pure function — does no I/O. Filters to accepted participants, explodes one
row per ticket, sorts so that all tickets of one buyer appear consecutively.
"""

from typing import Any


_BASE_HEADERS = ["Vorname", "Nachname", "Ticket-Option", "Gast-Name"]


def _normalize_value(value: Any) -> str:
    """Normalize a custom field value to a CSV/PDF-safe string."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return "ja" if value else "nein"
    if isinstance(value, list):
        return "; ".join(_normalize_value(v) for v in value)
    return str(value)


def build_rows(
    participants: list[dict],
    custom_fields: list[dict],
    include_rsvp_responses: bool,
) -> tuple[list[str], list[list[str]]]:
    """Build (headers, rows) for the export.

    Args:
        participants: as returned by event_service.get_event_participants()["participants"]
        custom_fields: as returned by custom_field_service.get_custom_fields(),
            already sorted by sort_order.
        include_rsvp_responses: when True, append one column per custom field.

    Returns:
        (headers, rows) — headers is a list of column titles,
        rows is a list of equal-length string lists.
    """
    field_order: list[dict] = list(custom_fields) if include_rsvp_responses else []
    headers: list[str] = list(_BASE_HEADERS) + [
        f"rsvp_{f['label']}" for f in field_order
    ]

    field_id_to_index: dict[str, int] = {
        f["custom_field_id"]: i for i, f in enumerate(field_order)
    }

    rows: list[list[str]] = []

    for p in participants:
        if (p.get("status") or "").lower() != "accepted":
            continue

        person = p.get("person") or {}
        first_name = person.get("first_name") or ""
        last_name = person.get("last_name") or ""

        for tr in p.get("ticket_responses") or []:
            row: list[str] = [
                first_name,
                last_name,
                tr.get("ticket_option_name") or "",
                tr.get("guest_name") or "",
            ]
            if include_rsvp_responses:
                rsvp_cells: list[str] = [""] * len(field_order)
                for r in tr.get("responses") or []:
                    idx = field_id_to_index.get(r.get("custom_field_id"))
                    if idx is not None:
                        rsvp_cells[idx] = _normalize_value(r.get("value"))
                row.extend(rsvp_cells)
            rows.append(row)

    rows.sort(
        key=lambda r: (r[1].lower(), r[0].lower(), r[2].lower())
    )

    return headers, rows
