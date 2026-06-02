# MessagingAdapter

**Kategorie:** T-Software  
**Entwurfs-Entsprechung:** `<<component>> MessagingAdapter`  
**Implementierung:** `app/services/email_service.py`

## Beschreibung

Der `MessagingAdapter` kapselt die Kommunikation mit einem externen Nachrichtendienst. Er stellt der `Authentication`-Komponente die Schnittstelle `SendMessage` bereit, über die Nachrichten an Nutzer versendet werden.

!!! note "Abweichung vom Entwurf"
    Im ursprünglichen Entwurf war der `MessagingAdapter` für den Versand von **SMS** (Handynummer-Verifikation bei Registrierung, M1) vorgesehen. In der Implementierung wird er für den Versand von **E-Mails** über **Resend** eingesetzt. Die Authentifizierungs-OTPs werden direkt von Supabase Auth per E-Mail versendet; der `MessagingAdapter` wird für transaktionale E-Mails außerhalb des Auth-Flows verwendet.

## Bereitgestellte Schnittstellen

| Schnittstelle | Genutzt von | Beschreibung |
|---|---|---|
| `SendMessage` | Authentication, Notification | Nachricht (E-Mail) an einen Nutzer senden |

## Genutzter externer Dienst

**Resend** – REST-basierter E-Mail-Versand-Dienst. Resend wird als AT-Software eingestuft, da der Dienst im Prinzip durch einen anderen E-Mail-Anbieter (SendGrid, Mailgun, etc.) ersetzt werden könnte.

## Implementierung

```python
# app/services/email_service.py
import resend

resend.api_key = settings.RESEND_API_KEY

async def send_email(
    to: str,
    subject: str,
    html_body: str
) -> None:
    resend.Emails.send({
        "from": "noreply@happin.app",
        "to": to,
        "subject": subject,
        "html": html_body,
    })
```

## Konfiguration

| Umgebungsvariable | Beschreibung |
|---|---|
| `RESEND_API_KEY` | API-Schlüssel für den Resend-Dienst |

## Abhängigkeiten

- Resend (AT-Software, externer Dienst)
