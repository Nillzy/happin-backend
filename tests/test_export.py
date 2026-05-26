"""Tests für den Gästelisten-Export (S8)."""

import io

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient


@pytest.fixture
def mock_supabase():
    mock_client = MagicMock()
    with patch("app.services.event_service.get_supabase", return_value=mock_client):
        with patch("app.services.event_service.get_supabase_for_user", return_value=mock_client):
            yield mock_client


@pytest.fixture
def mock_person_service():
    with patch("app.services.person_service.get_or_create_person") as mock:
        mock.return_value = {"person_id": "c1d2e3f4-a5b6-7890-cdef-123456789012"}
        yield mock


# ---------------------------------------------------------------------------
# Unit-Tests: build_rows
# ---------------------------------------------------------------------------


class TestBuildRows:
    """Tests für export_service.build_rows."""

    def _participants_fixture(self) -> list[dict]:
        return [
            {
                "status": "Accepted",
                "person": {"first_name": "Max", "last_name": "Lehmann"},
                "ticket_responses": [
                    {
                        "ticket_id": "t1",
                        "guest_name": "Max Lehmann",
                        "ticket_option_name": "Standard",
                        "responses": [{"custom_field_id": "cf1", "value": "Vegan"}],
                    },
                    {
                        "ticket_id": "t2",
                        "guest_name": "Anna Lehmann",
                        "ticket_option_name": "VIP",
                        "responses": [],
                    },
                ],
            },
            {
                "status": "declined",
                "person": {"first_name": "Sophie", "last_name": "Klein"},
                "ticket_responses": [
                    {"ticket_id": "t3", "guest_name": "Sophie Klein",
                     "ticket_option_name": "Standard", "responses": []}
                ],
            },
            {
                "status": "Accepted",
                "person": {"first_name": "Anna", "last_name": "Berg"},
                "ticket_responses": [
                    {
                        "ticket_id": "t4",
                        "guest_name": "Anna Berg",
                        "ticket_option_name": "Standard",
                        "responses": [
                            {"custom_field_id": "cf1", "value": None},
                            {"custom_field_id": "cf2", "value": True},
                        ],
                    }
                ],
            },
        ]

    def _custom_fields_fixture(self) -> list[dict]:
        return [
            {"custom_field_id": "cf1", "label": "Allergien", "sort_order": 0},
            {"custom_field_id": "cf2", "label": "Plus-Eins", "sort_order": 1},
        ]

    def test_filters_only_accepted(self):
        from app.services.export.export_service import build_rows

        _, rows = build_rows(self._participants_fixture(), [], False)

        # 2 Käufer akzeptiert, davon 1 mit 2 Tickets, 1 mit 1 Ticket → 3 Zeilen
        assert len(rows) == 3
        # Sophie (declined) darf nicht erscheinen
        assert all(row[1] != "Klein" for row in rows)

    def test_one_row_per_ticket(self):
        from app.services.export.export_service import build_rows

        _, rows = build_rows(self._participants_fixture(), [], False)

        lehmann_rows = [r for r in rows if r[1] == "Lehmann"]
        assert len(lehmann_rows) == 2
        ticket_options = {r[2] for r in lehmann_rows}
        assert ticket_options == {"Standard", "VIP"}

    def test_sorts_by_lastname_then_firstname_then_option(self):
        from app.services.export.export_service import build_rows

        _, rows = build_rows(self._participants_fixture(), [], False)

        # Erwartete Reihenfolge: Berg, Lehmann (Standard vor VIP)
        assert rows[0][1] == "Berg"
        assert rows[1][1] == "Lehmann"
        assert rows[1][2] == "Standard"
        assert rows[2][1] == "Lehmann"
        assert rows[2][2] == "VIP"

    def test_headers_without_rsvp(self):
        from app.services.export.export_service import build_rows

        headers, _ = build_rows(self._participants_fixture(), [], False)
        assert headers == ["Vorname", "Nachname", "Ticket-Option", "Gast-Name"]

    def test_headers_and_columns_with_rsvp(self):
        from app.services.export.export_service import build_rows

        headers, rows = build_rows(
            self._participants_fixture(),
            self._custom_fields_fixture(),
            include_rsvp_responses=True,
        )

        assert headers == [
            "Vorname",
            "Nachname",
            "Ticket-Option",
            "Gast-Name",
            "rsvp_Allergien",
            "rsvp_Plus-Eins",
        ]
        # Jede Zeile hat exakt 6 Spalten
        assert all(len(r) == 6 for r in rows)

    def test_value_normalization(self):
        from app.services.export.export_service import build_rows

        participants = [
            {
                "status": "accepted",
                "person": {"first_name": "Test", "last_name": "User"},
                "ticket_responses": [
                    {
                        "ticket_id": "t1",
                        "guest_name": "Test",
                        "ticket_option_name": "Standard",
                        "responses": [
                            {"custom_field_id": "cf_none", "value": None},
                            {"custom_field_id": "cf_bool_true", "value": True},
                            {"custom_field_id": "cf_bool_false", "value": False},
                            {"custom_field_id": "cf_list", "value": ["a", "b", "c"]},
                            {"custom_field_id": "cf_str", "value": "Hallo"},
                        ],
                    }
                ],
            }
        ]
        custom_fields = [
            {"custom_field_id": "cf_none", "label": "None", "sort_order": 0},
            {"custom_field_id": "cf_bool_true", "label": "BoolTrue", "sort_order": 1},
            {"custom_field_id": "cf_bool_false", "label": "BoolFalse", "sort_order": 2},
            {"custom_field_id": "cf_list", "label": "Liste", "sort_order": 3},
            {"custom_field_id": "cf_str", "label": "Str", "sort_order": 4},
        ]

        _, rows = build_rows(participants, custom_fields, include_rsvp_responses=True)
        assert len(rows) == 1
        row = rows[0]
        assert row[4] == ""        # None
        assert row[5] == "ja"      # True
        assert row[6] == "nein"    # False
        assert row[7] == "a; b; c" # list
        assert row[8] == "Hallo"   # str

    def test_handles_missing_lastname(self):
        from app.services.export.export_service import build_rows

        participants = [
            {
                "status": "accepted",
                "person": {"first_name": "Jonas", "last_name": None},
                "ticket_responses": [
                    {"ticket_id": "t1", "guest_name": "Jonas",
                     "ticket_option_name": "Standard", "responses": []}
                ],
            }
        ]
        _, rows = build_rows(participants, [], False)
        assert rows[0][0] == "Jonas"
        assert rows[0][1] == ""

    def test_excludes_phone_number_completely(self):
        """Datenschutz: Telefonnummern dürfen nicht in den Export."""
        from app.services.export.export_service import build_rows

        participants = [
            {
                "status": "accepted",
                "person": {
                    "first_name": "Max",
                    "last_name": "Lehmann",
                    "phone_number": "+49 170 1234567",
                },
                "ticket_responses": [
                    {"ticket_id": "t1", "guest_name": "Max",
                     "ticket_option_name": "Standard", "responses": []}
                ],
            }
        ]
        headers, rows = build_rows(participants, [], False)

        assert not any("phone" in h.lower() or "telefon" in h.lower() for h in headers)
        assert not any("+49" in str(c) for r in rows for c in r)


# ---------------------------------------------------------------------------
# Unit-Tests: csv_renderer
# ---------------------------------------------------------------------------


class TestCsvRenderer:
    def test_starts_with_utf8_bom(self):
        from app.services.export.csv_renderer import render_csv

        body = render_csv(["A", "B"], [["1", "2"]])
        assert body.startswith(b"\xef\xbb\xbf")  # UTF-8 BOM

    def test_uses_crlf_line_endings(self):
        from app.services.export.csv_renderer import render_csv

        body = render_csv(["A"], [["1"], ["2"]])
        assert b"\r\n" in body

    def test_handles_umlauts(self):
        from app.services.export.csv_renderer import render_csv

        body = render_csv(["Größe"], [["müßig"]])
        decoded = body.decode("utf-8-sig")
        assert "Größe" in decoded
        assert "müßig" in decoded

    def test_escapes_commas_and_quotes(self):
        from app.services.export.csv_renderer import render_csv

        body = render_csv(["A"], [['Hallo, "Welt"']])
        decoded = body.decode("utf-8-sig")
        assert '"Hallo, ""Welt"""' in decoded


# ---------------------------------------------------------------------------
# Unit-Tests: pdf_renderer
# ---------------------------------------------------------------------------


class TestPdfRenderer:
    def test_returns_pdf_bytes(self):
        from app.services.export.pdf_renderer import render_pdf

        body = render_pdf(
            ["Vorname", "Nachname", "Ticket-Option", "Gast-Name"],
            [["Max", "Lehmann", "Standard", "Max"]],
            {"name": "Test-Event", "starts_at": "2026-08-15T19:00:00+00:00"},
        )
        assert body.startswith(b"%PDF-")
        assert len(body) > 500  # mindestens minimaler PDF-Inhalt

    def test_handles_empty_rows(self):
        from app.services.export.pdf_renderer import render_pdf

        body = render_pdf(["A", "B"], [], {"name": "Leeres Event"})
        assert body.startswith(b"%PDF-")

    def test_handles_many_columns(self):
        from app.services.export.pdf_renderer import render_pdf

        headers = ["A"] * 20
        rows = [["x"] * 20 for _ in range(3)]
        body = render_pdf(headers, rows, None)
        assert body.startswith(b"%PDF-")

    def test_event_title_appears_in_pdf(self):
        """Event-Titel muss im PDF-Header sichtbar sein.

        Supabase liefert das Event mit Schlüssel ``title`` (nicht ``name``);
        der Renderer muss beide Schlüssel akzeptieren.
        """
        from app.services.export.pdf_renderer import render_pdf
        from pypdf import PdfReader

        body = render_pdf(
            ["Vorname", "Nachname", "Ticket-Option", "Gast-Name"],
            [["Max", "Lehmann", "Standard", "Max"]],
            {"title": "Sommerfest 2026", "starts_at": "2026-08-15T19:00:00+00:00"},
        )
        reader = PdfReader(io.BytesIO(body))
        page_text = reader.pages[0].extract_text()
        assert "Sommerfest 2026" in page_text


# ---------------------------------------------------------------------------
# HTTP-Tests: GET /api/v1/events/{id}/export
# ---------------------------------------------------------------------------


class TestExportEndpoint:
    """Tests für GET /api/v1/events/{event_id}/export."""

    _PARTICIPANTS = {
        "participants": [
            {
                "event_participation_id": "p1",
                "status": "Accepted",
                "person": {
                    "person_id": "person-1",
                    "first_name": "Max",
                    "last_name": "Lehmann",
                    "phone_number": "+49 170 1234567",
                },
                "ticket_count": 1,
                "ticket_responses": [
                    {
                        "ticket_id": "t1",
                        "guest_name": "Max",
                        "ticket_option_id": "opt-1",
                        "ticket_option_name": "Standard",
                        "responses": [{"custom_field_id": "cf1", "value": "Vegan"}],
                    }
                ],
            }
        ],
        "counts": {"accepted": 1, "declined": 0, "pending": 0},
        "ticket_option_summary": [],
    }

    _CUSTOM_FIELDS = [
        {"custom_field_id": "cf1", "label": "Allergien", "sort_order": 0},
    ]

    def _patch_chain(self, is_host=True):
        """Hilfs-Context mit allen Mocks für einen Host-Aufruf."""
        return [
            patch("app.api.v1.events.person_service.get_or_create_person",
                  return_value={"person_id": "person-1"}),
            patch("app.services.event_service.is_user_host", return_value=is_host),
            patch("app.services.event_service.get_event_participants",
                  return_value=self._PARTICIPANTS),
            patch("app.services.event_service.get_event_by_id",
                  return_value={"event_id": "e1", "name": "Test-Event",
                                "starts_at": "2026-08-15T19:00:00+00:00"}),
            patch("app.services.custom_field_service.get_custom_fields",
                  return_value=self._CUSTOM_FIELDS),
        ]

    def _run(self, client, mock_supabase, query: str, is_host=True):
        mock_supabase.auth.get_user.return_value = MagicMock(
            user=MagicMock(id="uid-test", email="test@example.com")
        )
        patches = self._patch_chain(is_host=is_host)
        for p in patches:
            p.start()
        try:
            return client.get(
                f"/api/v1/events/e1/export?{query}",
                headers={"Authorization": "Bearer fake-token"},
            )
        finally:
            for p in patches:
                p.stop()

    def test_csv_returns_200_with_correct_headers(self, client, mock_supabase):
        response = self._run(client, mock_supabase, "format=csv")

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/csv")
        assert 'attachment' in response.headers["content-disposition"]
        assert "gaesteliste_e1_" in response.headers["content-disposition"]
        assert response.headers["content-disposition"].endswith('.csv"')
        assert response.content.startswith(b"\xef\xbb\xbf")  # UTF-8 BOM

    def test_pdf_returns_200_with_correct_headers(self, client, mock_supabase):
        response = self._run(client, mock_supabase, "format=pdf")

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
        assert response.content.startswith(b"%PDF-")
        assert response.headers["content-disposition"].endswith('.pdf"')

    def test_invalid_format_returns_422(self, client, mock_supabase):
        # FastAPI Literal-Validation gibt 422 statt 400 zurück
        response = self._run(client, mock_supabase, "format=xml")
        assert response.status_code in (400, 422)

    def test_non_host_returns_403(self, client, mock_supabase):
        response = self._run(client, mock_supabase, "format=csv", is_host=False)
        assert response.status_code == 403

    def test_include_rsvp_responses_adds_columns(self, client, mock_supabase):
        # Mit include_rsvp_responses=true muss die Allergien-Spalte da sein
        response = self._run(
            client, mock_supabase, "format=csv&include_rsvp_responses=true"
        )
        assert response.status_code == 200
        decoded = response.content.decode("utf-8-sig")
        assert "rsvp_Allergien" in decoded
        assert "Vegan" in decoded

    def test_include_rsvp_responses_omitted_excludes_columns(self, client, mock_supabase):
        response = self._run(client, mock_supabase, "format=csv")
        assert response.status_code == 200
        decoded = response.content.decode("utf-8-sig")
        assert "rsvp_" not in decoded

    def test_phone_number_is_never_in_output(self, client, mock_supabase):
        response = self._run(
            client, mock_supabase, "format=csv&include_rsvp_responses=true"
        )
        assert b"+49" not in response.content
        assert b"1234567" not in response.content

    def test_no_accepted_participants_returns_header_only(self, client, mock_supabase):
        empty = {"participants": [], "counts": {"accepted": 0, "declined": 0,
                                                "pending": 0},
                 "ticket_option_summary": []}
        mock_supabase.auth.get_user.return_value = MagicMock(
            user=MagicMock(id="uid-test", email="test@example.com")
        )
        with patch("app.api.v1.events.person_service.get_or_create_person",
                   return_value={"person_id": "person-1"}):
            with patch("app.services.event_service.is_user_host", return_value=True):
                with patch("app.services.event_service.get_event_participants",
                           return_value=empty):
                    response = client.get(
                        "/api/v1/events/e1/export?format=csv",
                        headers={"Authorization": "Bearer fake-token"},
                    )

        assert response.status_code == 200
        decoded = response.content.decode("utf-8-sig")
        # Nur Header-Zeile (keine Datenzeilen)
        assert decoded.strip().count("\n") == 0
        assert "Vorname" in decoded
