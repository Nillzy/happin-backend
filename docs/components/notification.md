# Notification

**Kategorie:** A-Software  
**Entwurfs-Entsprechung:** `<<component>> Notification` (im Anwendungskern)  
**Implementierung:** `app/services/notification_service.py`, `app/services/reminder_service.py`, `app/services/reminder_scheduler.py`, `app/services/expo_push_service.py`

## Beschreibung

Die `Notification`-Komponente verwaltet alle Benachrichtigungen an Nutzer. Sie unterscheidet zwischen **In-App-Benachrichtigungen** (sichtbar in der App) und **Push-Benachrichtigungen** (native Push / Web Push für Erinnerungen).

[→ Im Architekturentwurf ansehen](<https://gitlab.com/groups/dhbw-se/se-tinf24b2/happin/-/wikis/Entwurf/Komponentendiagramm#:~:text=Host%2DRechte%20verwalten)-,Notification,-M3%20(Teilnehmer%20%C3%BCber>)

!!! note "Erweiterung gegenüber dem Entwurf"
    Die vollständige Push-Benachrichtigungsinfrastruktur (VAPID Web Push, Expo Push API, APScheduler) ist eine Erweiterung, die im ursprünglichen Architekturentwurf nicht explizit vorgesehen war.

## Bereitgestellte Schnittstellen

| Schnittstelle | Endpunkt | Beschreibung |
|---|---|---|
| `Notification` (Liste) | `GET /api/v1/users/{id}/notifications` | In-App-Benachrichtigungen abrufen |
| `Notification` (Read) | `PATCH /api/v1/users/{id}/notifications/{nid}` | Als gelesen markieren |
| `Notification` (Reminder abonnieren) | `POST /api/v1/users/{id}/reminders` | Push-Erinnerung für Event registrieren |
| `Notification` (Reminder löschen) | `DELETE /api/v1/users/{id}/reminders/{rid}` | Erinnerung abbestellen |

## Genutzte Schnittstellen

- **`Read` / `Write`** (DatabaseAdapter): Benachrichtigungseinträge und Reminder-Subscriptions
- Expo Push API (extern) – native App-Benachrichtigungen
- Web Push VAPID (Browser-Standard) – Browser-Push-Benachrichtigungen

## Benachrichtigungstypen

| Typ | Auslöser | Kanal |
|---|---|---|
| `new_rsvp` | Nutzer sagt zu | In-App (Host) |
| `rsvp_cancelled` | Nutzer sagt ab | In-App (Host) |
| `event_cancelled` | Host sagt Event ab | In-App + Push (Teilnehmer) |
| `event_reminder` | Zeitgesteuert (K4) | Push (Teilnehmer) |
| `waitlist_promoted` | Platz frei geworden | Push (Wartender) |

## Implementierung

### In-App-Benachrichtigungen

```python
# app/services/notification_service.py
async def create_notification(
    user_id: str,
    type: str,
    event_id: str,
    message: str
) -> None:
    # Eintrag in notifications-Tabelle anlegen
```

### Zeitgesteuerte Push-Erinnerungen (K4)

Der `reminder_scheduler.py` verwendet APScheduler, um geplante Push-Benachrichtigungen auszuliefern:

```python
# app/services/reminder_scheduler.py
scheduler = AsyncIOScheduler()

async def schedule_reminder(reminder: Reminder) -> None:
    scheduler.add_job(
        send_reminder_push,
        trigger=DateTrigger(run_date=reminder.scheduled_for),
        args=[reminder]
    )
```

### Expo Push (native Apps)

```python
# app/services/expo_push_service.py
async def send_expo_push(
    token: str,
    title: str,
    body: str
) -> None:
    # POST https://exp.host/--/api/v2/push/send
```

## Abhängigkeiten

- [`DatabaseAdapter`](database-adapter.md)
- Expo Push Notification Service (extern)
- Web Push / VAPID (Browser-Standard)
