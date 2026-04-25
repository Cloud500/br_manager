# App: `meetings` - Sitzungsverwaltung

## Übersicht

Die `meetings`-App ist das zentrale Modul für die Verwaltung von Sitzungen (Online, Hybrid, Präsenz). Alle weiteren Module (Tagesordnungen, Protokolle, Anwesenheiten, Beschlüsse) sind an Sitzungen gebunden.

## Hauptfunktionen

### 1. Sitzungstypen
- **ONLINE:** Nur Online-Teilnahmelink (URL)
- **HYBRID:** Online-Link + vollständige Adresse (Ortsbezeichnung, Straße, PLZ, Stadt, Raum)
- **IN_PERSON:** Nur Adresse (kein Online-Link)

### 2. Sitzungsverwaltung
- Erstellen, Bearbeiten, Löschen (nur Entwurf)
- Vorsitz und Protokollführung zuweisen (+ Vertretungen)
- Status-Workflow: DRAFT → IN_PROGRESS → APPROVED → SENT → COMPLETED
- Sitzungsnummer (automatisch, z.B. "2026-05")
- Tatsächlicher Start/Ende vs. geplanter Start/Ende

### 3. Verknüpfte Elemente
- Tagesordnung (1:N → AgendaItems)
- Protokoll (1:1 → Minutes)
- Anwesenheiten (1:N → AttendanceRecords)
- Beschlüsse (über AgendaItems → Resolutions)

### 4. E-Mail-Versand
- Einladung mit Tagesordnung versenden
- Erinnerungen vor Sitzung (konfigurierbar)

## Datenmodell

### Meeting
- `id` (UUID, PK)
- `committee` (ForeignKey → Committee)
- `title` (CharField(300))
- `meeting_number` (CharField(20), UNIQUE per Committee)
- `date` (DateField)
- `start_time` (TimeField)
- `end_time` (TimeField, optional)
- `actual_start_time` (TimeField, optional)
- `actual_end_time` (TimeField, optional)
- `meeting_type` (CharField(10)) - ONLINE, HYBRID, IN_PERSON
- `location_url` (URLField(500), optional) - Bei ONLINE/HYBRID
- `location_name` (CharField(200), optional) - Bei HYBRID/IN_PERSON
- `location_street` (CharField(200), optional)
- `location_zip` (CharField(10), optional)
- `location_city` (CharField(100), optional)
- `location_room` (CharField(100), optional)
- `status` (CharField(20))
- `created_by` (ForeignKey → User)
- `created_at` / `updated_at` (DateTimeField)
- `is_quorate` (BooleanField, optional) - Beschlussfähig
- `chair` (ForeignKey → User, optional) - Vorsitz der Sitzung
- `clerk` (ForeignKey → User, optional) - Protokollführung der Sitzung

**Validierung:** Formular passt sich dynamisch dem Sitzungstyp an (siehe Hauptfunktionen #1)

## URLs und Views

| URL | View | Beschreibung |
|-----|------|--------------|
| `/meetings/` | MeetingListView | Sitzungen auflisten |
| `/meetings/create/` | MeetingCreateView | Neue Sitzung erstellen |
| `/meetings/from-template/` | MeetingFromTemplateView | Aus Vorlage erstellen |
| `/meetings/<uuid:id>/` | MeetingDetailView | Sitzungsdetails |
| `/meetings/<uuid:id>/edit/` | MeetingEditView | Sitzung bearbeiten |
| `/meetings/<uuid:id>/delete/` | MeetingDeleteView | Löschen (nur Entwurf) |
| `/meetings/<uuid:id>/send/` | MeetingSendView | Einladung versenden |
| `/meetings/<uuid:id>/complete/` | MeetingCompleteView | Sitzung abschließen |

## Abhängigkeiten

### Erforderlich
- **accounts** (User)
- **committees** (Committee, Membership)
- **roles** (Berechtigungsprüfung)

### Optional
- **audit** (Logging)
- **notifications** (E-Mail-Versand)

## Berechtigungen

- `meeting.create` - Sitzung erstellen
- `meeting.edit` - Bearbeiten
- `meeting.delete_draft` - Entwurf löschen
- `meeting.view` - Einsehen
- `meeting.send` - Einladung versenden
- `meeting.complete` - Abschließen

## Verbindungen

### Ausgehend
- **committees** (Committee)
- **accounts** (User für chair, clerk, created_by)

### Eingehend
- **agendas** (AgendaItems)
- **minutes** (Minutes)
- **attendance** (AttendanceRecords)
- **resolutions** (über AgendaItems)
- **calendar_mgmt** (CalendarEvent)
- **todos** (optional verknüpft)

## Templates

- `meetings/meeting_list.html`
- `meetings/meeting_detail.html`
- `meetings/meeting_form.html` (dynamisch je nach meeting_type)
- `meetings/meeting_confirm_delete.html`

## Implementierungshinweise

### Dynamisches Formular je nach Sitzungstyp
```python
class MeetingForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        meeting_type = self.instance.meeting_type if self.instance.pk else self.initial.get('meeting_type', 'IN_PERSON')
        
        if meeting_type == 'ONLINE':
            # Nur location_url anzeigen
            for field in ['location_name', 'location_street', 'location_zip', 'location_city', 'location_room']:
                self.fields[field].widget = forms.HiddenInput()
        elif meeting_type == 'IN_PERSON':
            # Nur Adressfelder anzeigen
            self.fields['location_url'].widget = forms.HiddenInput()
```

### Automatische Sitzungsnummer
```python
def generate_meeting_number(committee, date):
    year = date.year
    count = Meeting.objects.filter(
        committee=committee,
        date__year=year
    ).count() + 1
    return f"{year}-{count:02d}"
```

## Tests

- Unit-Tests für Formular-Validierung (Sitzungstyp-Logik)
- Integration-Tests für Sitzungserstellung
- Berechtigungs-Tests
- E-Mail-Versand-Tests
