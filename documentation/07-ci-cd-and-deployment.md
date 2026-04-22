# CI/CD und Deployment

## GitLab CI (`.gitlab-ci.yml`)

### Stufen

| Stage | Inhalt |
|-------|--------|
| `build` | Docker-Image bauen und in die **GitLab Container Registry** pushen |
| `deploy` | **Manuelles** Deployment per SSH auf die Ziel-VM |

Die Stage **`test`** ist vorbereitet, aber auskommentiert, bis echte Tests und Job-Skripte stehen.

### Build-Job

- Läuft auf Push zu Branch **`main`** (`only: - main`).
- Tags: `$CI_REGISTRY_IMAGE/backend:$CI_COMMIT_SHORT_SHA` und `:latest`.

### Deploy-Job

- **`when: manual`** — muss in der GitLab-UI angestoßen werden.
- Nutzt **Alpine** mit `openssh-client`, lädt einen SSH-Key aus der Variable **`SSH_PRIVATE_KEY`**, vertraut dem Host-Key von **`vm552.ipp-vps.net`** (Stand Pipeline-Datei).
- Remote-Skript: u. a. Login an `registry.gitlab.com`, `docker compose` für den Dienst **`backend`**, `git pull` in einem Deployment-Pfad auf der VM.

### Erforderliche / genutzte GitLab-Variablen (Auszug)

| Variable | Verwendung |
|----------|------------|
| `SSH_PRIVATE_KEY` | SSH-Key für `happin-deploy@…` |
| `GITLAB_DEPLOY_TOKEN`, `GITLAB_DEPLOY_USERNAME` | Registry-Login auf der VM (siehe `script` in `.gitlab-ci.yml`) |

Konkrete Werte und Rotation sind **Team-/Betriebsthema**; hier nur die aus der Pipeline ersichtlichen Namen dokumentiert.

## Produktions-URL

Die Pipeline verweist in `environment.url` auf **`http://vm552.ipp-vps.net:8001`** — Anpassung bei Infrastructure-Änderungen nicht vergessen.

## Hinweise für Maintainer

- Images enthalten **keine** `documentation/`-Dateien (siehe `.dockerignore`).
- Nach Änderungen an Deploy-Skripten: Zugriffsrechte auf der VM und Compose-Pfade (`/home/shared/deployment/…`) mit dem Team abstimmen.
