# App: `notifications` - Benachrichtigungssystem

## Übersicht

E-Mail- und In-App-Benachrichtigungen für alle relevanten Ereignisse im System.

## Hauptfunktionen

- **E-Mail:** Primärer Benachrichtigungskanal
- **In-App:** Benachrichtigungscenter in der Anwendung
- **Typen:** Sitzungseinladung, Erinnerung, Protokoll-Unterschrift, Dokument geteilt, Ersatzmitglied-Einladung, Beschluss-PDF, Personelle Maßnahmen (Fristwarnung, Ergebnis), Beschlussfähigkeit gefährdet, etc.
- **Benutzer-Präferenzen:** Individuell konfigurierbar
- **Digest-Modus:** Zusammenfassungs-E-Mails für nicht-kritische Benachrichtigungen

## Benachrichtigungstypen

| Typ | Auslöser | Empfänger |
|-----|----------|-----------|
| Sitzungseinladung | Tagesordnung versandt | Alle Mitglieder |
| Sitzungserinnerung | Konfigurierter Zeitpunkt | Eingeladene |
| Protokoll zur Unterschrift | Protokollführung hat unterschrieben | Vorsitz |
| Protokoll genehmigt | Vorläufige Genehmigung | Alle Mitglieder |
| Dokument geteilt | Dokument freigegeben | Betroffene |
| Ersatzmitglied-Einladung | Nachrückung | Ersatzmitglied |
| Beschluss-PDF | Versand ausgelöst | Arbeitgeber |
| Personelle Maßnahme: Fristwarnung | Frist ≤ 2 Tage | Vorsitz, Zuständige |
| Personelle Maßnahme: Ergebnis | Ergebnisversand | Arbeitgeber |
| Beschlussfähigkeit gefährdet | Zu viele Abwesenheiten | Vorsitz |
| Abwesenheitsmeldung | Mitglied meldet Abwesenheit | Vorsitz |

## Datenmodell

### Notification
- `id`, `recipient` (FK → User)
- `notification_type` (MEETING_INVITATION, REMINDER, PROTOCOL_REVIEW, etc.)
- `title`, `message`
- `is_read`, `is_email_sent`
- `related_object_type`, `related_object_id`
- `created_at`

## URLs

| URL | Beschreibung |
|-----|--------------|
| `/notifications/` | Eigene Benachrichtigungen |
| `/notifications/<uuid:id>/read/` | Als gelesen markieren |
| `/notifications/read-all/` | Alle als gelesen |
| `/notifications/preferences/` | Einstellungen |

### HTMX
- `/notifications/badge/` - Ungelesene Anzahl (Polling)
- `/notifications/dropdown/` - Letzte Benachrichtigungen (Dropdown)

## Abhängigkeiten

- **accounts** (User)
- SMTP-Server für E-Mail-Versand
- **Celery** (optional) für asynchronen Versand

## Berechtigungen

- Keine spezifischen Permissions (jeder kann eigene Benachrichtigungen verwalten)

## Templates

- `notifications/notification_list.html`
- `notifications/preferences.html`
- `notifications/_dropdown.html` (HTMX)
- `emails/` (E-Mail-Templates für jeden Typ)

## Implementierungshinweise

### Notification Helper
```python
def notify(recipient, notification_type, title, message, related_object=None):
    notification = Notification.objects.create(
        recipient=recipient,
        notification_type=notification_type,
        title=title,
        message=message,
        related_object_type=related_object.__class__.__name__ if related_object else None,
        related_object_id=related_object.id if related_object else None
    )
    
    # E-Mail senden (asynchron via Celery)
    if recipient.notification_preferences.get(notification_type, {}).get('email', True):
        send_notification_email.delay(notification.id)
    
    return notification
```

### Celery-Task für E-Mail-Versand
```python
@shared_task
def send_notification_email(notification_id):
    notification = Notification.objects.get(id=notification_id)
    
    send_mail(
        subject=notification.title,
        message=notification.message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[notification.recipient.email],
        html_message=render_to_string(f'emails/{notification.notification_type}.html', {'notification': notification})
    )
    
    notification.is_email_sent = True
    notification.save()
```

### Verwendung in anderen Apps
```python
# In meetings/views.py
from apps.notifications.utils import notify

def send_meeting_invitation(meeting):
    for member in meeting.committee.members.all():
        notify(
            recipient=member.user,
            notification_type='MEETING_INVITATION',
            title=f'Einladung: {meeting.title}',
            message=f'Sie sind eingeladen zur Sitzung am {meeting.date}',
            related_object=meeting
        )
```

## Tests

- Unit-Tests für notify-Helper
- Integration-Tests für E-Mail-Versand
- Celery-Task-Tests
- Präferenzen-Tests
