"""Exportiert das OpenAPI-Schema der FastAPI-App als openapi.json nach docs/api/.

Wird im CI vor dem MkDocs-Build ausgeführt, damit die Swagger-UI-Seite
auf GitLab Pages das aktuelle Schema einbetten kann.
Alle Supabase-/Stripe-Abhängigkeiten werden gemockt, damit kein echter
Dienst erreichbar sein muss.
"""

import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# Projekt-Root zum Suchpfad hinzufügen, damit `app` importierbar ist
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Dummy-Umgebungsvariablen setzen, bevor pydantic-settings die Settings lädt
os.environ.setdefault("SUPABASE_URL", "https://placeholder.supabase.co")
os.environ.setdefault("SUPABASE_ANON_KEY", "placeholder-anon-key")
os.environ.setdefault("DEBUG", "true")

mock_supabase = MagicMock()

with patch("supabase.create_client", return_value=mock_supabase):
    from app.main import app

schema = app.openapi()

out_dir = Path(__file__).resolve().parent.parent / "docs" / "api"
out_dir.mkdir(parents=True, exist_ok=True)
out_file = out_dir / "openapi.json"
out_file.write_text(json.dumps(schema, indent=2, ensure_ascii=False))

print(f"OpenAPI-Schema exportiert nach {out_file}")
