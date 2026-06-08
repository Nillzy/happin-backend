# Dokumentationskonzept

Im Happin-Projekt existieren **drei getrennte Dokumentationen** mit unterschiedlichen Zielgruppen und Zwecken. Diese Seite erklärt, welche Doku wofür da ist, wo sie zu finden ist und wann sie aktualisiert werden muss.

## Übersicht

| Doku | Zielgruppe | Inhalt | Zugriff |
|---|---|---|---|
| `repo-docs/` | Entwicklungsteam, KI-Agenten | Implementierungsdetails, Feature-Historie, Konventionen | Direkt im Repository (Markdown) |
| `docs/` | Alle Stakeholder | Architektur-Übersicht, Vergleich Entwurf↔Implementierung, Komponenten | MkDocs-Site unter `/docs` (nur bei `DEBUG=true`) |
| `api-docs/` | Frontend-Entwickler, externe Konsumenten | Interaktive Swagger-UI mit allen REST-Endpunkten | FastAPI-Swagger unter `/api/docs` (nur bei `DEBUG=true`) |

---

## 1. `repo-docs/` – Entwickler- & Agenten-Doku

**Wer:** Mitglieder der Entwicklungsteams und KI-Agenten (Claude Code, Codex etc.)

**Was:** Detaillierte Implementierungsdokumentation jedes größeren Features. Jede Änderung im Backend wird hier in einer eigenen Datei dokumentiert (z. B. `20-event-absagen.md`, `21-erinnerungen-k4.md`).

**Wo:** Markdown-Dateien direkt im Repository unter `repo-docs/`. Sie werden nicht gerendert, sondern in der IDE oder in GitLab gelesen.

**Konvention:**

- Dateien werden mit nummeriertem Präfix angelegt (`<NN>-<feature-slug>.md`).
- Jede neue Datei wird in [`00-index.md`](00-index.md) eingetragen.
- Gut geeignet für: Architektur-Entscheidungen, Migrations-Anleitungen, "Warum haben wir es so gebaut".

**Nicht zu verwechseln mit:** der Stakeholder-Doku unter `docs/` – die ist **Übersicht**, `repo-docs/` ist **Tiefenwissen**.

---

## 2. `docs/` – Stakeholder-Doku (MkDocs)

**Wer:** Alle Stakeholder (Product Owner, Tutoren, Reviewer, neue Entwickler).

**Was:**

- Allgemeine Übersicht des Backends (Tech-Stack, Projektstruktur, Schnellstart).
- **Architekturentwurf vs. Implementierung**: jede Entwurfskomponente wird auf ihre tatsächliche Umsetzung im Code abgebildet, inklusive Abweichungen.
- Eine Seite pro Komponente unter `docs/components/` mit Beschreibung, bereitgestellten/genutzten Schnittstellen und Implementierungsdetails.

**Wo:**

- Quelldateien: `docs/` im Repository (`docs/index.md`, `docs/architecture.md`, `docs/components/*.md`).
- Konfiguration: [`mkdocs.yml`](../mkdocs.yml).
- Gerendert: erreichbar unter [`http://localhost:8001/docs`](http://localhost:8001/docs) – **nur, wenn `DEBUG=true` in der `.env` gesetzt ist**.

**Build:**

Die MkDocs-Site wird beim Start des Backends automatisch gebaut, sofern `DEBUG=true` ist. Das Skript `scripts/start_dev.sh` führt vor dem Uvicorn-Start `mkdocs build` aus. Die FastAPI-App mountet anschließend das `site/`-Verzeichnis unter `/docs`.

**Build manuell auslösen:**

```bash
mkdocs build
```

**Konvention:**

- Eine neue Komponente bekommt eine eigene Datei unter `docs/components/`.
- Sie wird in `mkdocs.yml` unter `nav:` registriert.
- Der zugehörige Eintrag in `docs/architecture.md` (Tabelle "Anwendungskern" bzw. eigener Abschnitt) wird ergänzt – inklusive Rückreferenz auf den Architekturentwurf (siehe [Traceability-Konzept](25-traceability.md)).

---

## 3. `api-docs/` – API-Referenz (Swagger)

**Wer:** Frontend-Entwickler, externe API-Konsumenten, QA.

**Was:** Interaktive Swagger-UI mit allen REST-Endpunkten – Request-Parameter, Response-Schemas, Auth-Anforderungen, Beispiel-Calls. Wird automatisch von FastAPI aus den Pydantic-Modellen und Route-Definitionen generiert.

**Wo:**

- Erreichbar unter [`http://localhost:8001/api/docs`](http://localhost:8001/api/docs) – **nur, wenn `DEBUG=true` gesetzt ist**.
- Auch über die Stakeholder-Doku unter `/docs` erreichbar: in der oberen Navigationsleiste auf **„API-Referenz"** klicken (siehe `mkdocs.yml`, Eintrag `API-Referenz: /api/docs`).

**Konvention:**

- Keine separate Pflege nötig – die Swagger-Doku ist eine Reflektion des Codes.
- Endpoint-Beschreibungen, Tags und Beispiele werden direkt in den FastAPI-Routern via Docstrings und `summary=`/`description=`-Parameter gepflegt.
- Pydantic-Schemas in `app/schemas/` definieren die Request- und Response-Strukturen.

---

## Wann welche Doku?

| Aufgabe | Doku |
|---|---|
| Neues Feature implementieren | `repo-docs/<NN>-<feature>.md` anlegen + in `00-index.md` eintragen |
| Neue Architektur-Komponente | Eintrag in `docs/architecture.md` + Datei unter `docs/components/` + `mkdocs.yml` |
| Neuen REST-Endpoint | Nur Code & Pydantic-Schemas pflegen – Swagger entsteht automatisch |
| Stakeholder fragt "Wie ist das Backend aufgebaut?" | Verweis auf `http://localhost:8001/docs` |
| Frontend-Entwickler braucht Endpoint-Details | Verweis auf `http://localhost:8001/api/docs` |
| Agent oder Entwickler braucht Hintergrund zu einem Feature | `repo-docs/` durchsuchen, beginnend bei `00-index.md` |

## Zugriff & Voraussetzungen

In der `.env` muss `DEBUG=true` gesetzt sein, damit sowohl `/docs` als auch `/api/docs` erreichbar sind. Im Production-Build (`DEBUG=false`) liefern beide Routen 404 zurück – die Doku ist nicht öffentlich zugänglich.