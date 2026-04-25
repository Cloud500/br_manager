# App: `personnel` - Personelle Einzelmaßnahmen

## Übersicht

Verwaltung personeller Einzelmaßnahmen gemäß §§ 99–101 BetrVG (Einstellungen, Versetzungen, Umgruppierungen, Kündigungen) mit Fristenüberwachung und Beschlussfassung. Pro Ausschuss aktivierbar (`personnel_enabled`).

## Hauptfunktionen

- **Maßnahmen erfassen:** Typ, Name der betroffenen Person (Klartext), Beschreibung, Unterlagen
- **Fristenüberwachung:** Automatische Berechnung (7 Tage nach § 99 Abs. 3 BetrVG)
- **Status-Workflow:** RECEIVED → COMPLETE → IN_REVIEW → STATEMENT_DRAFTED → RESOLUTION_MADE → COMPLETED
- **Verknüpfung mit TOP:** Als PERSONNEL_MEASURE-TOP auf Tagesordnung
- **Verknüpfung mit Beschluss:** Stellungnahme = Beschluss (Zustimmung/Verweigerung)
- **Fristwarnung:** Automatische Benachrichtigung bei ≤ 2 Tagen Restfrist
- **Ergebnisversand:** E-Mail an Arbeitgeber
- **Dokumentenanhänge:** Unterlagen des Arbeitgebers, eigene Stellungnahmen
- **Externe API:** Personalabteilung kann Maßnahmen extern anlegen
- **Zugriff:** Alle regulären Gremiumsmitglieder + aktive Ersatzmitglieder (Lesezugriff)
- **Verwaltung:** Nur in Ausschüssen mit `personnel_enabled`

## Datenmodell

### PersonnelMeasure
- `id`, `measure_type` (HIRING, TRANSFER, RECLASSIFICATION, DISMISSAL, OTHER)
- `reference_number` (Aktenzeichen, UNIQUE)
- `subject_name` (Name der Person, Klartext)
- `description`, `received_at`, `deadline` (automatisch: received_at + 7 Tage)
- `status` (RECEIVED, COMPLETE, IN_REVIEW, STATEMENT_DRAFTED, RESOLUTION_MADE, COMPLETED)
- `resolution` (FK → Resolution, optional)
- `statement` (Stellungnahme), `notes` (Sitzungsnotizen)
- `committee` (FK, muss `personnel_enabled=True` haben)
- `result_sent_at`, `result_sent_to` (E-Mail)
- `created_by`, `created_at`, `updated_at`

## URLs

| URL | Beschreibung |
|-----|--------------|
| `/personnel/` | Maßnahmen auflisten (mit Fristanzeige) |
| `/personnel/create/` | Neue Maßnahme erfassen |
| `/personnel/<uuid:id>/` | Details |
| `/personnel/<uuid:id>/edit/` | Bearbeiten |
| `/personnel/<uuid:id>/statement/` | Stellungnahme erstellen |
| `/personnel/<uuid:id>/link-resolution/` | Beschluss verknüpfen |
| `/personnel/<uuid:id>/link-agenda-item/` | Als TOP auf Tagesordnung |
| `/personnel/<uuid:id>/send-result/` | Ergebnis an Arbeitgeber senden |
| `/personnel/api/create/` | Externe API (JSON, POST) |

### HTMX
- `/personnel/deadline-warnings/` - Fristwarnungen (Polling)
- `/personnel/filter/` - Live-Filterung

## Abhängigkeiten

- **accounts** (User)
- **committees** (Committee mit `personnel_enabled`)
- **resolutions** (Resolution)
- **agendas** (AgendaItem mit `item_type=PERSONNEL_MEASURE`)
- **documents** (DocumentLink für Anhänge)
- **notifications** (Fristwarnungen)

## Berechtigungen

- `personnel.create` - Erfassen
- `personnel.edit` - Bearbeiten
- `personnel.delete` - Löschen (nur Admin/Vorsitz)
- `personnel.view` - Einsehen (alle regulären Mitglieder + aktive Ersatzmitglieder)
- `personnel.create_statement` - Stellungnahme erstellen (nur Vorsitz/Stellv.)
- `personnel.link_resolution` - Beschluss verknüpfen
- `personnel.link_agenda_item` - Als TOP auf Tagesordnung
- `personnel.send_result` - Ergebnisversand (nur Vorsitz/Stellv.)

## Templates

- `personnel/measure_list.html` (mit Fristanzeige, Ampel-System)
- `personnel/measure_detail.html`
- `personnel/measure_form.html`
- `personnel/statement_form.html`

## Implementierungshinweise

### Automatische Fristberechnung
```python
class PersonnelMeasure(models.Model):
    # ...
    
    def save(self, *args, **kwargs):
        if not self.deadline:
            self.deadline = self.received_at + timedelta(days=7)
        super().save(*args, **kwargs)
    
    @property
    def days_remaining(self):
        if self.status == 'COMPLETED':
            return None
        delta = self.deadline - timezone.now()
        return delta.days
    
    @property
    def is_overdue(self):
        return self.days_remaining is not None and self.days_remaining < 0
    
    @property
    def is_urgent(self):
        return self.days_remaining is not None and 0 <= self.days_remaining <= 2
```

### Celery-Task für Fristwarnungen
```python
@periodic_task(run_every=timedelta(hours=6))
def check_personnel_deadlines():
    from apps.notifications.utils import notify
    
    urgent = PersonnelMeasure.objects.filter(
        status__in=['RECEIVED', 'COMPLETE', 'IN_REVIEW'],
        deadline__lte=timezone.now() + timedelta(days=2)
    )
    
    for measure in urgent:
        # Benachrichtige Vorsitz und zuständige Mitglieder
        vorsitz = measure.committee.memberships.filter(role__codename='CHAIR').first()
        if vorsitz:
            notify(
                recipient=vorsitz.user,
                notification_type='PERSONNEL_DEADLINE_WARNING',
                title=f'Fristwarnung: {measure.reference_number}',
                message=f'Die Maßnahme "{measure.subject_name}" läuft in {measure.days_remaining} Tagen ab!',
                related_object=measure
            )
```

### Externe API (POST /personnel/api/create/)
```python
@csrf_exempt
@require_http_methods(["POST"])
def personnel_external_create_api(request):
    # API-Key-Authentifizierung
    api_key = request.headers.get('X-API-Key')
    if not validate_api_key(api_key):
        return JsonResponse({'error': 'Invalid API key'}, status=401)
    
    # Rate Limiting
    if not check_rate_limit(api_key):
        return JsonResponse({'error': 'Rate limit exceeded'}, status=429)
    
    # JSON-Validierung
    data = json.loads(request.body)
    form = PersonnelMeasureAPIForm(data)
    
    if form.is_valid():
        measure = form.save()
        
        # Audit-Logging
        AuditLog.objects.create(
            action='CREATE',
            resource_type='PersonnelMeasure',
            resource_id=measure.id,
            description=f'External API created personnel measure {measure.reference_number}',
            ip_address=get_client_ip(request)
        )
        
        return JsonResponse({'id': str(measure.id), 'reference_number': measure.reference_number}, status=201)
    
    return JsonResponse({'errors': form.errors}, status=400)
```

### Ergebnisversand
```python
def send_personnel_result(measure, employer_email):
    # E-Mail mit Ergebnis (Zustimmung/Verweigerung + Begründung)
    send_mail(
        subject=f'Stellungnahme zu {measure.reference_number}',
        message=f'Stellungnahme: {measure.statement}',
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[employer_email]
    )
    
    measure.result_sent_at = timezone.now()
    measure.result_sent_to = employer_email
    measure.status = 'COMPLETED'
    measure.save()
```

## Tests

- Unit-Tests für Fristberechnung
- Celery-Task-Tests für Fristwarnungen
- API-Tests (Authentifizierung, Rate Limiting, Validierung)
- Integration-Tests für Verknüpfung mit TOPs und Beschlüssen
- E-Mail-Versand-Tests
