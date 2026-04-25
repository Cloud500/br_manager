# App: `audit` - Audit-Logging & Compliance

## Übersicht

Die `audit`-App protokolliert alle sicherheitsrelevanten Ereignisse und Datenänderungen im System für Compliance, Nachvollziehbarkeit und Sicherheitsüberwachung.

## Hauptfunktionen

### 1. Umfassendes Event-Logging
- **Authentifizierung:** Login, Logout, Fehlversuche, 2FA, Passwortänderung
- **Autorisierung:** Zugriffsversuche (erfolgreich/fehlgeschlagen), Rechteänderungen
- **Datenzugriff:** CREATE, READ, UPDATE, DELETE für alle Ressourcen
- **Administration:** Benutzerverwaltung, Rollenzuweisung, Systemkonfiguration
- **Dokumente:** Upload, Download, Freigabe, Versionierung
- **Sitzungen:** Erstellen, Bearbeiten, Löschen, Versand
- **Beschlüsse:** Abstimmungen, Wahlergebnisse
- **To-Dos:** Erstellen, Bearbeiten, Zuweisen, Statusänderungen
- **Personelle Einzelmaßnahmen:** Erfassung, Bearbeitung, Stellungnahmen, Ergebnisversand
- **Externe API:** Alle API-Aufrufe inkl. IP und API-Key

### 2. Unveränderliches Audit-Log
- Append-Only-Tabelle (kein UPDATE/DELETE)
- Separate DB-Verbindung mit eingeschränkten Rechten
- Diff-Protokollierung (alte → neue Werte)

### 3. Compliance-Funktionen
- DSGVO-konforme Aufbewahrung (2 Jahre Standard)
- Export für Prüfungszwecke
- Betroffenenrechte-Protokollierung (Art. 15-21 DSGVO)
- BetrVG-relevante Ereignisse markiert

### 4. Sicherheitsüberwachung
- Automatische Alerts bei verdächtigen Mustern
- Brute-Force-Erkennung
- Anomalieerkennung (ungewöhnliche Zugriffsmuster)
- Fehlgeschlagene Zugriffe prominent markiert

### 5. Filter und Suche
- Filter nach Benutzer, Aktion, Ressourcentyp, Zeitraum
- Volltextsuche in Beschreibungen
- CSV-Export für Berichte

## Datenmodell

### AuditLog
- `id` (UUID, PK)
- `user` (ForeignKey → User, NULL = SYSTEM)
- `action` (CharField(20)) - CREATE, READ, UPDATE, DELETE, LOGIN, LOGOUT, EXPORT, APPROVE
- `resource_type` (CharField(50)) - Betroffener Ressourcentyp
- `resource_id` (UUIDField, optional) - Betroffene Ressource-ID
- `description` (TextField) - Beschreibung der Aktion
- `ip_address` (GenericIPAddressField, optional)
- `user_agent` (CharField(500), optional)
- `old_values` (JSONField, optional) - Vorherige Werte
- `new_values` (JSONField, optional) - Neue Werte
- `timestamp` (DateTimeField, auto_now_add) - UTC, ISO 8601
- `success` (BooleanField) - Erfolg/Fehlschlag
- `is_sensitive` (BooleanField) - Markierung für sensible Ereignisse

**Constraints:**
- Keine UPDATE/DELETE-Rechte auf Tabelle
- Index auf (user, timestamp), (resource_type, timestamp), (action, timestamp)

## URLs und Views

| URL | View | Beschreibung |
|-----|------|--------------|
| `/audit/` | AuditLogListView | Audit-Logs anzeigen (mit Filter) |
| `/audit/export/csv/` | AuditLogExportView | Audit-Logs als CSV exportieren |

### HTMX-Fragmente

| URL | Trigger | Beschreibung |
|-----|---------|--------------|
| `/audit/filter/` | hx-get (Filteränderung) | Audit-Logs live filtern |

## Abhängigkeiten

### Erforderliche Apps
- **accounts** (User-Modell)

### Optionale Apps
- **ELK Stack** (zentrale Log-Aggregation)
- **Prometheus/Grafana** (Alerting)

### Django-Pakete
- Django Standard (keine zusätzlichen Pakete erforderlich)

## Berechtigungen

- `system.view_audit_logs` - Audit-Logs einsehen
- `system.export_audit_logs` - Audit-Logs exportieren

**Hinweis:** Nur System-Admins haben Zugriff auf Audit-Logs

## Templates

- `audit/audit_log_list.html` - Audit-Log-Übersicht mit Filtern
- `audit/_log_entry.html` - HTMX-Fragment für einzelnen Eintrag

## Implementierungshinweise

### 1. Audit-Middleware
Django-Middleware für automatisches Logging aller Requests:

```python
class AuditMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Request-Info sammeln
        user = request.user if request.user.is_authenticated else None
        ip = self.get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        response = self.get_response(request)
        
        # Bei relevanten Aktionen loggen
        if request.method in ['POST', 'PUT', 'PATCH', 'DELETE']:
            AuditLog.objects.create(
                user=user,
                action=self.map_method_to_action(request.method),
                resource_type=self.extract_resource_type(request.path),
                resource_id=self.extract_resource_id(request.path),
                description=f"{request.method} {request.path}",
                ip_address=ip,
                user_agent=user_agent,
                success=(200 <= response.status_code < 400)
            )
        
        return response
```

### 2. Model-Signal-Basiertes Logging
Für detaillierte Datenänderungen:

```python
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

@receiver(post_save)
def log_model_save(sender, instance, created, **kwargs):
    if sender.__name__ in AUDITED_MODELS:
        action = 'CREATE' if created else 'UPDATE'
        
        old_values = None
        new_values = model_to_dict(instance)
        
        if not created and hasattr(instance, '_original_values'):
            old_values = instance._original_values
        
        AuditLog.objects.create(
            user=get_current_user(),  # ThreadLocal
            action=action,
            resource_type=sender.__name__,
            resource_id=instance.id,
            description=f"{action} {sender.__name__}",
            old_values=old_values,
            new_values=new_values
        )
```

### 3. Original-Werte tracken
Mixin für Models, um Änderungen zu tracken:

```python
class AuditMixin(models.Model):
    class Meta:
        abstract = True
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._original_values = self._get_field_values()
    
    def _get_field_values(self):
        return {
            field.name: getattr(self, field.name)
            for field in self._meta.fields
        }
    
    def save(self, *args, **kwargs):
        # Original-Werte vor dem Speichern festhalten
        if self.pk:
            self._original_values = self.__class__.objects.get(pk=self.pk)._get_field_values()
        super().save(*args, **kwargs)
```

### 4. Context-Manager für Bulk-Operations
Um mehrere Operationen als eine Audit-Aktion zu gruppieren:

```python
@contextmanager
def audit_context(action, resource_type, description):
    start_time = timezone.now()
    success = False
    try:
        yield
        success = True
    finally:
        AuditLog.objects.create(
            user=get_current_user(),
            action=action,
            resource_type=resource_type,
            description=description,
            success=success,
            timestamp=start_time
        )

# Verwendung:
with audit_context('BULK_DELETE', 'Meeting', 'Alte Sitzungen gelöscht'):
    Meeting.objects.filter(date__lt=cutoff_date).delete()
```

### 5. Retention Policy
Automatische Löschung alter Audit-Logs per Celery-Task:

```python
@periodic_task(run_every=timedelta(days=1))
def cleanup_old_audit_logs():
    retention_days = settings.AUDIT_LOG_RETENTION_DAYS  # Default: 730 (2 Jahre)
    cutoff_date = timezone.now() - timedelta(days=retention_days)
    
    deleted_count = AuditLog.objects.filter(
        timestamp__lt=cutoff_date
    ).delete()[0]
    
    logger.info(f"Deleted {deleted_count} old audit log entries")
```

### 6. Sensitive Data Filtering
Passwörter und andere sensitive Daten aus Logs filtern:

```python
SENSITIVE_FIELDS = ['password', 'token', 'api_key', 'secret']

def sanitize_values(data):
    if isinstance(data, dict):
        return {
            k: '***REDACTED***' if k in SENSITIVE_FIELDS else sanitize_values(v)
            for k, v in data.items()
        }
    return data
```

## Verbindungen zu anderen Apps

### Ausgehende Abhängigkeiten
- **accounts:** User-Modell

### Eingehende Abhängigkeiten
- **Alle Apps** nutzen Audit-Logging für Event-Protokollierung

## Security & Compliance

### DSGVO-Konformität
- **Art. 5 Abs. 2 DSGVO:** Nachweispflicht durch Audit-Logs
- **Art. 32 DSGVO:** Technische Maßnahmen (Protokollierung)
- **Art. 33/34 DSGVO:** Incident Response (Audit-Logs als Nachweis)

### Aufbewahrungsfristen
- **Standard:** 2 Jahre
- **Rechtliche Basis:** Nachweispflicht für DSGVO-Compliance
- **Konfigurierbar:** Per Setting anpassbar

### Anonymisierung
Bei Löschung von Benutzerkonten (DSGVO Art. 17):
- Audit-Logs behalten, aber user_id durch „User [anonymized]" ersetzen
- IP-Adressen anonymisieren
- User-Agent beibehalten (nicht personenbezogen)

## Monitoring & Alerting

### Kritische Ereignisse (sofortiges Alerting)
- Mehr als 5 fehlgeschlagene Logins pro User in 5 Min
- Zugriff auf vertrauliche Dokumente außerhalb Geschäftszeiten
- Massenexport von Daten
- Änderungen an System-Admin-Rollen
- Externe API-Aufrufe von unbekannten IPs

### Wöchentliche Reports
- Anzahl Logins pro User
- Häufigste Aktionen
- Fehlgeschlagene Zugriffe
- Neue Benutzer/Rollen

## Tests

- Unit-Tests für Audit-Middleware
- Integration-Tests für Model-Signals
- Performance-Tests (Bulk-Logging)
- Compliance-Tests (Retention Policy)
- Security-Tests (Unveränderlichkeit prüfen)
