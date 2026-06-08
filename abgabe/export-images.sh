#!/usr/bin/env bash
# Erstellt happin-abgabe-<version>.tar.gz mit allem, was der Dozent zum Starten braucht:
#   - docker-compose.yml
#   - backend.env
#   - frontend.env
#   - README.md
#   - happin-images.tar.gz (Backend- und Frontend-Image)
#
# Optional: Lädt das Bundle in die GitLab Package Registry hoch.
#
# Voraussetzungen:
#   - docker login registry.gitlab.com (mit PAT, scope read_registry)
#   - Fuer Upload: GITLAB_TOKEN gesetzt (PAT mit scope "api")
#
# Verwendung:
#   ./export-images.sh                       # Nur Bundle bauen
#   ./export-images.sh v0.1.0                # Bundle bauen + zur Package Registry hochladen
#   GITLAB_TOKEN=glpat-xxx ./export-images.sh v0.1.0

set -euo pipefail

BACKEND_IMAGE="registry.gitlab.com/dhbw-se/se-tinf24b2/happin/backend/backend:latest"
FRONTEND_IMAGE="registry.gitlab.com/dhbw-se/se-tinf24b2/happin/frontend/frontend:latest"

PROJECT_PATH="dhbw-se%2Fse-tinf24b2%2Fhappin%2Fbackend"
PACKAGE_NAME="happin-abgabe"

VERSION="${1:-}"
BUNDLE_VERSION="${VERSION:-dev}"
BUNDLE_NAME="happin-abgabe-${BUNDLE_VERSION}"
BUNDLE_FILE="${BUNDLE_NAME}.tar.gz"
IMAGES_FILE="happin-images.tar.gz"

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo "==> Pulling images..."
docker pull "$BACKEND_IMAGE"
docker pull "$FRONTEND_IMAGE"

echo "==> Saving images to $IMAGES_FILE..."
docker save "$BACKEND_IMAGE" "$FRONTEND_IMAGE" | gzip > "$IMAGES_FILE"

echo "==> Building bundle $BUNDLE_FILE..."
STAGING_DIR="$(mktemp -d)"
trap 'rm -rf "$STAGING_DIR"' EXIT
mkdir "$STAGING_DIR/$BUNDLE_NAME"
cp docker-compose.yml backend.env frontend.env README.md "$IMAGES_FILE" "$STAGING_DIR/$BUNDLE_NAME/"
tar -czf "$BUNDLE_FILE" -C "$STAGING_DIR" "$BUNDLE_NAME"

echo "==> Bundle ready: $(du -h "$BUNDLE_FILE" | cut -f1) -> $BUNDLE_FILE"

if [[ -z "$VERSION" ]]; then
  echo
  echo "Hinweis: Keine Version uebergeben -> Upload uebersprungen."
  echo "Fuer Upload: ./export-images.sh <version>   (z.B. v0.1.0)"
  exit 0
fi

if [[ -z "${GITLAB_TOKEN:-}" ]]; then
  echo "FEHLER: GITLAB_TOKEN ist nicht gesetzt." >&2
  echo "Erstelle einen Personal Access Token mit Scope 'api' und exportiere ihn:" >&2
  echo "  export GITLAB_TOKEN=glpat-xxxxx" >&2
  exit 1
fi

UPLOAD_URL="https://gitlab.com/api/v4/projects/${PROJECT_PATH}/packages/generic/${PACKAGE_NAME}/${VERSION}/${BUNDLE_FILE}"

echo "==> Uploading to Package Registry: $UPLOAD_URL"
curl --fail --show-error \
     --header "PRIVATE-TOKEN: $GITLAB_TOKEN" \
     --upload-file "$BUNDLE_FILE" \
     "$UPLOAD_URL"

echo
echo "==> Upload fertig."
echo "    Asset-URL fuer Release: $UPLOAD_URL"
