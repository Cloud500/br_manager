# App: `calendar_mgmt` - Kalender & Terminverwaltung

## Übersicht

Zentrale Kalender- und Terminverwaltung mit Sitzungskalender, persönlichem Kalender, Abwesenheitsverwaltung und Reisedaten.

## Hauptfunktionen

- **Sitzungskalender:** Alle geplanten Sitzungen aller Gremien
- **Persönlicher Kalender:** Eigene Sitzungen und Termine
- **Abwesenheitskalender:** nachladbar/nicht nachladbar (ohne konkreten Grund - DSGVO)
- **Reisedaten:** An-/Abreise bei mehrtägigen Veranstaltungen
- **Terminkollisionsprüfung:** Warnung bei Überschneidungen
- **Raumverwaltung:** Optional
- **iCal-Export/Import:** Synchronisation mit externen Kalendern
- **Erinnerungen:** Konfigurierbar vor Sitzungen
- **Ersatzmitglieder:** Dauerhafter Zugriff unabhängig vom Einsatzstatus

## Datenmodell

### CalendarEvent
- `id`, `title`, `event_type` (MEETING, ABSENCE, REMINDER, OTHER)
- `start_datetime`, `end_datetime`, `all_day`
- `user` (FK, NULL = gremiumsweit), `committee` (FK)
- `meeting` (FK, optional), `recurrence_rule` (iCal RRULE)
- `notes`

### Absence
- `id`, `user` (FK), `start_date`, `end_date`
- `absence_type` (SUBSTITUTE_AVAILABLE, SUBSTITUTE_NOT_AVAILABLE)
- `is_approved` (zur Kenntnis genommen)

**Hinweis:** Kein konkreter Abwesenheitsgrund (Datenschutz - DSGVO)

## URLs

| URL | Beschreibung |
|-----|--------------|
| `/calendar/` | Kalenderansicht (FullCalendar) |
| `/calendar/events/create/` | Termin erstellen |
| `/calendar/events/<uuid:id>/edit/` | Bearbeiten |
| `/calendar/export/ical/` | iCal-Export |
| `/calendar/absences/` | Abwesenheiten |
| `/calendar/absences/create/` | Abwesenheit eintragen |

### HTMX / JSON
- `/calendar/events/json/` - Kalendereinträge für FullCalendar (JSON)
- `/calendar/events/<uuid:id>/detail/` - Event-Details (Popover, HTMX)

## Abhängigkeiten

- **accounts** (User)
- **committees** (Committee)
- **meetings** (Meeting)
- **FullCalendar** (JavaScript-Bibliothek)

## Berechtigungen

- `calendar.view` - Kalender einsehen
- `calendar.manage_own_absence` - Eigene Abwesenheit eintragen
- `calendar.create_meeting_event` - Sitzungstermin erstellen
- `calendar.export_ical` - iCal-Export
- `calendar.manage_travel` - Reisedaten eintragen

**Besonderheit:** Ersatzmitglieder haben dauerhaften Zugriff auf Kalender (unabhängig vom Einsatzstatus)

## Templates

- `calendar/calendar.html` (FullCalendar-Widget)
- `calendar/event_form.html`
- `calendar/absence_list.html`
- `calendar/absence_form.html`

## Implementierungshinweise

### FullCalendar-Integration
```javascript
// templates/calendar/calendar.html
var calendar = new FullCalendar.Calendar(calendarEl, {
  events: '{% url "calendar:events-json" %}',
  eventClick: function(info) {
    // HTMX-Request für Event-Details
    htmx.ajax('GET', '/calendar/events/' + info.event.id + '/detail/', {target:'#event-detail-modal'});
  }
});
```

### JSON-Endpoint für FullCalendar
```python
def calendar_events_json(request):
    events = CalendarEvent.objects.filter(
        Q(user=request.user) | Q(committee__in=request.user.committees)
    )
    
    data = [{
        'id': str(event.id),
        'title': event.title,
        'start': event.start_datetime.isoformat(),
        'end': event.end_datetime.isoformat(),
        'allDay': event.all_day
    } for event in events]
    
    return JsonResponse(data, safe=False)
```

### Verfügbarkeits-Check für Ersatzmitglieder
```python
def is_available(user, date):
    return not Absence.objects.filter(
        user=user,
        start_date__lte=date,
        end_date__gte=date
    ).exists()
```

### iCal-Export
```python
from icalendar import Calendar, Event

def export_ical(request):
    cal = Calendar()
    cal.add('prodid', '-//BR Manager//DE')
    cal.add('version', '2.0')
    
    for event in CalendarEvent.objects.filter(user=request.user):
        ical_event = Event()
        ical_event.add('summary', event.title)
        ical_event.add('dtstart', event.start_datetime)
        ical_event.add('dtend', event.end_datetime)
        cal.add_component(ical_event)
    
    response = HttpResponse(cal.to_ical(), content_type='text/calendar')
    response['Content-Disposition'] = 'attachment; filename="calendar.ics"'
    return response
```

## Tests

- Integration-Tests für FullCalendar-JSON-Endpoint
- Unit-Tests für Verfügbarkeits-Check
- iCal-Export-Tests
- Terminkollisions-Tests
