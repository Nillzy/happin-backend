# Traceability-Konzept

Im Happin-Projekt sind **Lastenheft, Pflichtenheft, Architekturentwurf und Code** über Rückreferenzen lückenlos miteinander verknüpft. Jeder Schritt im Projekt verweist auf den **vorhergehenden** Schritt – so lässt sich von einer beliebigen Codedatei zurückverfolgen, welche Komponente sie umsetzt, welche Anforderung dahintersteht und welcher Stakeholder-Wunsch sie ursprünglich motiviert hat.

## Die vier Ebenen

```
Lastenheft  (WAS)         ←── Pflichtenheft  (WIE)        ←── Architekturentwurf      ←── Codedokumentation
Stakeholder-Wünsche        Anforderungs-IDs                  Komponentendiagramm           docs/ + Code
                           Mx, Sx, Kx
```

Die Verweise verlaufen **immer rückwärts**: das spätere Dokument referenziert das frühere, nie umgekehrt. Dadurch bleibt das jeweils frühere Dokument unverändert, wenn später Anforderungen oder Komponenten hinzukommen.

## Die drei Rückreferenzen

### (1) Codedokumentation → Architekturentwurf

Die Codedokumentation in [`docs/`](http://localhost:8001/docs) enthält **dieselben Komponenten**, die im Architekturentwurf festgelegt wurden, und ordnet jeder Komponente die **Codedateien** zu, die sie umsetzen.

Beispiel: Die Komponente `Authentication` aus dem Architekturentwurf wird in [`docs/components/authentication.md`](../docs/components/authentication.md) dokumentiert und auf `app/core/auth.py`, `app/core/supabase.py` sowie Supabase Auth (extern) abgebildet.

Jede Komponentenseite enthält dafür einen klar markierten Rückverweis (siehe unten).

Beachte den **Text-Fragment-Anchor** (`#:~:text=…`): Damit springt der Browser direkt an die Stelle im GitLab-Wiki, an der die Komponente steht. Das funktioniert in allen modernen Chromium- und Firefox-Browsern.

### (2) Architekturentwurf → Pflichtenheft

Der Architekturentwurf verweist für jede identifizierte Komponente auf **die Anforderungen im Pflichtenheft**, an deren Umsetzung die Komponente beteiligt ist.

Beispiel: Die Komponente `Authentication` listet im GitLab-Wiki unter "Umgesetzte Anforderungen" `M1 (Passwortlose Authentifizierung)`. Klickt man auf `M1`, gelangt man direkt zur entsprechenden Anforderung im Pflichtenheft.

### (3) Pflichtenheft → Lastenheft

Das Pflichtenheft verweist mit **eindeutigen IDs** (Mx = Muss, Sx = Soll, Kx = Kann) auf die ursprünglichen Anforderungen im Lastenheft. Die ID-Kette `M1 → M1 → M1` zieht sich konsistent durch alle drei Dokumente.

## So sieht eine Rückreferenz aus

In der Codedokumentation wird der Verweis als Markdown-Link mit URL-Fragment-Anchor eingebaut:

```markdown
[→ Im Architekturentwurf ansehen](<https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Entwurf/Komponentendiagramm#:~:text=Umgesetzte%20Anforderungen-,Authentication,-M1%20(Passwortlose%20Authentifizierung>)
```

Aufbau des Anchors `#:~:text=PRÄFIX-,SUCHTEXT,-SUFFIX`:

| Teil | Bedeutung |
|---|---|
| `PRÄFIX` | Text **vor** dem gesuchten Begriff (zur eindeutigen Lokalisierung) |
| `SUCHTEXT` | Der eigentlich zu markierende Text – z. B. der Komponentenname |
| `SUFFIX` | Text **nach** dem Suchtext (ebenfalls zur Disambiguierung) |

Sonderzeichen (Leerzeichen, Klammern, Umlaute) müssen URL-encoded sein (`%20`, `%28`, `%29`, `%C3%84` …).

Da der Anchor `(` und `)` enthält, muss die URL in Markdown in **spitze Klammern** `<…>` gesetzt werden – sonst frisst der Markdown-Parser die Klammern.

## Beispiele aus der Codebase

In [`docs/architecture.md`](../docs/architecture.md) findet man die Rückreferenzen-Tabelle für jede Anwendungskern-Komponente:

```markdown
| `EventInfo` | `event_service.py` (Lesen) | [→](<https://gitlab.com/.../#:~:text=Validierung%2C%20Account%2DErstellung)-,EventInfo,-M4>) |
| `EventAdmin` | `event_service.py` (Schreiben) | [→](<https://gitlab.com/.../#:~:text=in%20Eventdaten%20liefern)-,EventAdmin,-M2>) |
| `RSVP` | `booking_service.py`, `waitlist_service.py` | [→](<https://gitlab.com/.../#:~:text=Co%2DHosts%20persistieren)-,RSVP,-M5>) |
```

Auf den Komponentenseiten unter [`docs/components/`](../docs/components/) gibt es jeweils einen prominent platzierten Block am Anfang:

```markdown
**Kategorie:** A-Software  
**Entwurfs-Entsprechung:** `<<component>> Authentication`  
**Implementierung:** `app/core/auth.py`, `app/core/supabase.py`

[→ Im Architekturentwurf ansehen](<https://gitlab.com/.../#:~:text=…>)
```

## So pflegst du die Rückreferenzen

### Wenn du eine **neue Komponente** dokumentierst

1. Lege die Datei unter `docs/components/<komponentenname>.md` an.
2. Trage in den Header die Felder **Kategorie**, **Entwurfs-Entsprechung** und **Implementierung** ein.
3. Hole dir aus dem GitLab-Wiki den Text-Fragment-Link zur Komponente:
   - GitLab-Wiki öffnen: [Komponentendiagramm](https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Entwurf/Komponentendiagramm).
   - Den Komponentennamen und dessen direktes Umfeld kopieren.
   - URL nach dem Schema `…#:~:text=PRÄFIX-,KOMPONENTE,-SUFFIX` zusammensetzen, alle Sonderzeichen URL-encoden.
   - Die URL in spitze Klammern `<…>` einfassen, weil sie Klammern enthält.
4. Füge den Link als `[→ Im Architekturentwurf ansehen](<URL>)` direkt nach dem Header ein.
5. Trage die neue Komponente in `mkdocs.yml` unter `nav:` ein.
6. In `docs/architecture.md` einen Eintrag in der entsprechenden Tabelle ergänzen, ebenfalls mit Rückreferenz.

### Wenn du eine **bestehende Komponente** änderst

- Felder **Implementierung** und Beschreibungstext aktualisieren.
- Rückreferenz **prüfen**: Falls sich der Wiki-Text geändert hat, Anchor neu generieren.
- Die `mkdocs.yml`-Navigation muss nur bei einer Umbenennung angepasst werden.

### Was du **nicht** tun darfst

- Den Architekturentwurf in `docs/` neu duplizieren – stattdessen verlinken.
- Anforderungs-IDs (M1, S2 …) in der Codedoku neu erfinden – immer dieselben IDs wie im Pflichtenheft verwenden.
- Eine Komponente einführen, die es im Architekturentwurf gar nicht gibt, ohne sie unter "Ergänzungen gegenüber dem Entwurf" in `docs/architecture.md` zu listen.

## Externe Quelldokumente

| Dokument | URL |
|---|---|
| Architekturentwurf (Komponentendiagramm) | <https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Entwurf/Komponentendiagramm> |
| Pflichtenheft (WIE-Ebene) | <https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Requirement-Engineering/WIE-Ebene/Pflichtenheft> |
| Lastenheft (WAS-Ebene) | <https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Requirement-Engineering/WAS-Ebene/Lastenheft> |

## Verwandte Doku

- [`24-documentation-concept.md`](24-documentation-concept.md) – Überblick über die drei Dokumentations-Ebenen.
