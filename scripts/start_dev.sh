#!/bin/sh
# Entwicklungsserver starten. Baut MkDocs-Dokumentation wenn DEBUG=true.
set -e

if [ -f .env ]; then
  export $(grep -v '^#' .env | xargs)
fi

if [ "$DEBUG" = "true" ]; then
  echo "DEBUG=true: Baue MkDocs-Dokumentation nach site/ ..."
  python3 -m mkdocs build --quiet
  echo "Dokumentation verfügbar unter http://127.0.0.1:8001/docs"
fi

uvicorn app.main:app --reload --port 8001
