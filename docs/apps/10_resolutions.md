# App: `resolutions` - Beschluss- & Wahlsystem

## Übersicht

Erfassung und Dokumentation von Beschlüssen mit automatischer Beschlussfähigkeits- und Ergebnis-Berechnung. Wahlen nur bei Präsenzsitzungen.

## Hauptfunktionen

### 1. Beschlüsse
- Verknüpfung mit TOP
- **Felder:** Beschlusstext, Begründung, Abstimmungsergebnis
- **Automatisch:** Beschlussfähigkeit, Ergebnis (Angenommen/Abgelehnt)
- **Überschreibbar:** Beschlussfähigkeit und Ergebnis manuell anpassbar
- **Beschlussnummer:** Automatisch, fortlaufend (z.B. BR-2026-042)
- **Beschluss-PDF an Arbeitgeber:** E-Mail mit PDF (nur Text, Begründung, Ergebnis)

### 2. Wahlen
- **Nur Präsenzsitzungen:** Warnung bei Online/Hybrid
- **Manuelle Ergebniserfassung:** System dient nur Dokumentation
- **Wahlverfahren:** Mehrheitswahl, Verhältniswahl
- **Kandidaten:** Freitext (candidate_name), keine Verknüpfung mit User-Konto
- **Geheime Abstimmung:** Optional

## Datenmodell

### Resolution
- `id`, `agenda_item` (FK), `resolution_number`, `title`, `text`, `reasoning`
- `resolution_type` (STANDARD, ELECTION), `majority_type` (SIMPLE, QUALIFIED)
- `votes_for`, `votes_against`, `abstentions`, `eligible_voters`
- `is_quorate` (berechnet), `is_quorate_override`
- `result` (ACCEPTED, REJECTED), `result_override`
- `is_secret_vote`
- `sent_to_employer`, `sent_to_employer_at`, `sent_to_employer_email`

### Election
- `id`, `resolution` (OneToOne), `election_type` (MAJORITY, PROPORTIONAL)
- `position_title`, `is_secret`, `meeting_type_check` (nur IN_PERSON)

### ElectionCandidate
- `id`, `election` (FK), `candidate_name` (CharField, Freitext)
- `votes_received`, `is_elected`

## URLs

| URL | Beschreibung |
|-----|--------------|
| `/resolutions/` | Alle Beschlüsse |
| `/resolutions/create/` | Beschluss erstellen |
| `/resolutions/<uuid:id>/` | Details |
| `/resolutions/<uuid:id>/vote/` | Abstimmungsergebnis erfassen |
| `/resolutions/<uuid:id>/send-employer/` | PDF an Arbeitgeber senden |
| `/resolutions/elections/` | Wahlen |
| `/resolutions/elections/create/` | Wahl erstellen (nur Präsenz) |
| `/resolutions/elections/<uuid:id>/result/` | Wahlergebnis erfassen |

### HTMX
- `/resolutions/<uuid:id>/vote/live/` - Live-Abstimmung
- `/resolutions/<uuid:id>/vote/quorum-check/` - Automatische Berechnung

## Abhängigkeiten

- **agendas** (AgendaItem)
- **attendance** (AttendanceRecord für eligible_voters, Beschlussfähigkeit)
- **meetings** (Meeting für meeting_type-Check bei Wahlen)
- **accounts** (User)

## Berechtigungen

- `resolution.create`, `resolution.edit`, `resolution.record_vote`
- `resolution.override_result`, `resolution.view`, `resolution.participate_vote`
- `resolution.manage_elections`, `resolution.send_employer`

## Templates

- `resolutions/resolution_list.html`
- `resolutions/resolution_detail.html`
- `resolutions/resolution_vote_form.html`
- `resolutions/election_form.html`
- `resolutions/election_result_form.html`

## Implementierungshinweise

### Automatische Beschlussfähigkeits- und Ergebnis-Berechnung
```python
def calculate_resolution_result(resolution):
    # Beschlussfähigkeit
    total_seats = resolution.agenda_item.meeting.committee.total_seats
    quorum_threshold = total_seats / 2
    resolution.is_quorate = (resolution.eligible_voters >= quorum_threshold)
    
    # Ergebnis
    if resolution.majority_type == 'SIMPLE':
        resolution.result = 'ACCEPTED' if resolution.votes_for > resolution.votes_against else 'REJECTED'
    elif resolution.majority_type == 'QUALIFIED':
        required = resolution.eligible_voters * 2 / 3
        resolution.result = 'ACCEPTED' if resolution.votes_for >= required else 'REJECTED'
    
    return resolution
```

### Beschluss-PDF-Versand
```python
from django.core.mail import EmailMessage
from weasyprint import HTML

def send_resolution_to_employer(resolution, employer_email):
    # PDF generieren (nur Text, Begründung, Ergebnis)
    html_content = render_to_string('resolutions/resolution_pdf.html', {'resolution': resolution})
    pdf = HTML(string=html_content).write_pdf()
    
    email = EmailMessage(
        subject=f'Beschluss {resolution.resolution_number}',
        body='Anbei der Beschluss...',
        to=[employer_email],
        attachments=[('beschluss.pdf', pdf, 'application/pdf')]
    )
    email.send()
    
    resolution.sent_to_employer = True
    resolution.sent_to_employer_at = timezone.now()
    resolution.sent_to_employer_email = employer_email
    resolution.save()
```

### Wahl-Validierung (nur Präsenz)
```python
class ElectionForm(forms.ModelForm):
    def clean(self):
        agenda_item = self.cleaned_data.get('agenda_item')
        if agenda_item.meeting.meeting_type != 'IN_PERSON':
            raise ValidationError("Wahlen sind nur bei Präsenzsitzungen möglich!")
        return self.cleaned_data
```

## Tests

- Unit-Tests für Beschlussfähigkeits-Berechnung
- Unit-Tests für Ergebnis-Berechnung (einfache/qualifizierte Mehrheit)
- Integration-Tests für Wahl-Validierung
- PDF-Generierungs-Tests
- E-Mail-Versand-Tests
