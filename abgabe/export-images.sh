#!/usr/bin/env bash
# Erstellt happin-images.tar.gz mit Backend- und Frontend-Image fuer die Abgabe.
# Voraussetzung: docker login registry.gitlab.com (mit PAT, scope read_registry)

set -euo pipefail

BACKEND_IMAGE="registry.gitlab.com/dhbw-se/se-tinf24b2/happin/backend/backend:latest"
FRONTEND_IMAGE="registry.gitlab.com/dhbw-se/se-tinf24b2/happin/frontend/frontend:latest"
OUTPUT="happin-images.tar.gz"

echo "==> Pulling images..."
docker pull "$BACKEND_IMAGE"
docker pull "$FRONTEND_IMAGE"

echo "==> Saving to $OUTPUT..."
docker save "$BACKEND_IMAGE" "$FRONTEND_IMAGE" | gzip > "$OUTPUT"

echo "==> Done: $(du -h "$OUTPUT" | cut -f1) -> $OUTPUT"
