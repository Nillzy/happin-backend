# Google Wallet Integration

## Übersicht

Die Google Wallet Integration ermöglicht es Nutzern, Event-Tickets als digitale Karten in Google Wallet zu speichern. Im Gegensatz zum Apple Wallet ist Google Wallet kostenlos nutzbar.

**Anforderung:** "Man könnte das Ticket an Apple Wallet exportieren oder auch per Kalenderexport das Event 'automatisch' im Kalender vormerken."

---

## Endpoint

### `GET /api/v1/events/{event_id}/wallet`

| Eigenschaft | Wert |
|-------------|------|
| Auth | Optional (Bearer JWT) |
| Response | `application/json` |
| Erfolg | `{ "wallet_url": "https://pay.google.com/..." }` |
| Fehler | 404 (Event nicht gefunden), 503 (nicht konfiguriert) |

**Response Beispiel:**
```json
{
  "wallet_url": "https://pay.google.com/gp/v/save/eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

Die `wallet_url` öffnet direkt Google Wallet und fügt das Ticket hinzu.

---

## Google Wallet Pass

Das generierte Ticket enthält:

| Feld | Quelle | Anmerkung |
|------|--------|-----------|
| Event-Name | `event.title` | Titel des Events |
| Datum | `event.starts_at` | Formatiert als "DD.MM.YYYY" |
| Uhrzeit | `starts_at` / `ends_at` | "HH:MM - HH:MM" |
| Venue | `location.city` | Stadt als Venue-Name |
| Adresse | `location.*` | Formatierte Adresse |
| QR-Code | Generiert | Format: `happin:{event_id}:{object_id}` |
| Hero Image | `event_media[0]` | Event-Bild (optional) |

---

## Konfiguration

### Umgebungsvariablen

```env
GOOGLE_WALLET_ISSUER_ID=3388000000023116326
GOOGLE_SERVICE_ACCOUNT_FILE=secrets/google-wallet-credentials.json
```

### Google Cloud Setup

1. **Google Cloud Projekt** mit aktivierter Google Wallet API
2. **Service Account** mit Wallet-Berechtigung erstellen
3. **JSON-Key** herunterladen und sicher speichern (nicht in Git!)
4. **Issuer Account** bei Google beantragen (kostenlos)

---

## Abhängigkeiten

| Paket | Version | Zweck |
|-------|---------|-------|
| `google-auth` | 2.29.0 | Service Account Authentication |
| `PyJWT` | 2.8.0 | JWT-Signierung für Wallet-Links |
| `cryptography` | >=42.0.0 | RSA-Signierung |

Installation: `pip install google-auth==2.29.0 PyJWT==2.8.0 cryptography>=42.0.0`

---

## Architektur

### Service-Layer

`app/services/google_wallet_service.py`:

| Funktion | Zweck |
|----------|-------|
| `generate_wallet_link(event_id, token)` | Generiert "Add to Wallet"-URL |
| `get_event_for_wallet(event_id, token)` | Lädt Event-Daten für Pass |
| `_create_event_ticket_object(event_data, object_id)` | Erstellt EventTicketObject-Payload |
| `_format_location(location)` | Formatiert Location als Adress-String |
| `is_configured()` | Prüft ob Integration konfiguriert ist |

### API-Layer

`app/api/v1/events.py`:

Der Endpoint prüft zuerst die Konfiguration und gibt 503 zurück wenn Google Wallet nicht eingerichtet ist.

---

## Sicherheit

- **Service Account Key:** Niemals in Git committen, in `secrets/` Ordner speichern
- **Öffentliche Events:** Ohne Token abrufbar
- **Private Events:** Nur mit gültigem JWT
- **JWT-Signierung:** Tickets werden mit RSA256 signiert

---

## Frontend-Integration

### "Add to Wallet" Button

```typescript
const addToWallet = async (eventId: string) => {
  const response = await fetch(
    `${API_URL}/api/v1/events/${eventId}/wallet`
  );
  const { wallet_url } = await response.json();

  // Öffnet Google Wallet
  window.open(wallet_url, '_blank');
};
```

### Mit Auth-Token (für private Events)

```typescript
const addToWallet = async (eventId: string, token: string) => {
  const response = await fetch(
    `${API_URL}/api/v1/events/${eventId}/wallet`,
    { headers: { Authorization: `Bearer ${token}` } }
  );
  const { wallet_url } = await response.json();
  window.open(wallet_url, '_blank');
};
```

### Conditional Rendering

```tsx
{isGoogleWalletAvailable && (
  <Button onPress={() => addToWallet(event.event_id)}>
    Zu Google Wallet hinzufügen
  </Button>
)}
```

---

## Tests

Tests in `tests/test_google_wallet.py`:

| Test | Prüft |
|------|-------|
| `test_wallet_endpoint_not_configured` | 503 bei fehlender Konfiguration |
| `test_wallet_endpoint_event_not_found` | 404 bei unbekanntem Event |
| `test_wallet_endpoint_returns_url` | Endpoint liefert gültige URL |
| `test_format_location` | Adress-Formatierung |
| `test_create_event_ticket_object` | Ticket-Objekt Struktur |
| `test_wallet_event_without_end_time` | Default-Dauer bei fehlendem `ends_at` |
| `test_wallet_event_without_location` | Pass ohne Location ist valide |
| `test_wallet_event_without_image` | Pass ohne Bild ist valide |

---

## Dateien

| Datei | Rolle |
|-------|-------|
| `app/core/config.py` | `GOOGLE_WALLET_*` Settings hinzugefügt |
| `app/services/google_wallet_service.py` | Wallet-Link-Generierung |
| `app/api/v1/events.py` | GET `/{event_id}/wallet` Endpoint |
| `requirements.txt` | `google-auth`, `PyJWT`, `cryptography` hinzugefügt |
| `tests/test_google_wallet.py` | Unit-Tests |
| `documentation/18-google-wallet.md` | Diese Dokumentation |

---

## Demo Mode

Als Studentenprojekt läuft die Integration im **Demo Mode**:
- Tickets funktionieren vollständig
- "Demo"-Wasserzeichen auf den Karten
- Keine Produktionsfreigabe erforderlich

---

## Unterschied zu Apple Wallet

| Aspekt | Google Wallet | Apple Wallet |
|--------|---------------|--------------|
| Kosten | Kostenlos | $99/Jahr Developer Account |
| Signierung | JWT (Service Account) | PKPass (Zertifikat) |
| Format | JSON via URL | Signiertes ZIP-Archiv |
| Setup | 1-2 Tage | Mehrere Wochen |

---

## Zukünftige Erweiterungen

| Feature | Beschreibung |
|---------|--------------|
| Ticket-Updates | Änderungen am Event aktualisieren den Pass |
| Personalisierung | Teilnehmer-Name auf dem Ticket |
| Check-In | QR-Code Scan am Einlass |
| Notifications | Push-Benachrichtigungen vor Event-Start |
