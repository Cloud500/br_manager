# 06 – Berechtigungskonzept

## 6.1 Übersicht

Der BR Manager implementiert ein **dynamisches, rollenbasiertes Zugriffskontrollsystem (RBAC)** mit konfigurierbaren Rollen und Berechtigungen. Administratoren und Vorsitzende können **eigene Rollen erstellen**, bestehende Rollen anpassen und diesen granulare Berechtigungen zuweisen. Berechtigungen werden kontextabhängig (pro Gremium) vergeben und berücksichtigen den besonderen Status von Ersatzmitgliedern.

### Kernprinzipien

- **Dynamische Rollen:** Rollen sind keine fest im Code verankerten Konstanten, sondern konfigurierbare Entitäten in der Datenbank.
- **Granulare Berechtigungen:** Jede Aktion im System ist als eigenständige Berechtigung (Permission) definiert.
- **Rollen-Berechtigung-Zuordnung:** Einer Rolle können beliebig viele Berechtigungen zugewiesen werden.
- **Vordefinierte Standard-Rollen:** Das System liefert Standard-Rollen mit empfohlenen Berechtigungen aus, die als Ausgangsbasis dienen und anpassbar sind.
- **Kontextbezogenheit:** Rollen gelten pro Gremium/Ausschuss – ein Benutzer kann in verschiedenen Gremien unterschiedliche Rollen haben.

---

## 6.2 Berechtigungssystem (Permissions)

### 6.2.1 Berechtigungs-Kategorien

Alle Berechtigungen sind nach Modulen organisiert:

| Kategorie | Codename-Präfix | Beschreibung |
|-----------|----------------|-------------|
| Sitzungen | `meeting.*` | Sitzungen erstellen, bearbeiten, löschen, einsehen |
| Tagesordnungen | `agenda.*` | TOPs und Vorlagen verwalten |
| Protokolle | `minutes.*` | Protokolle erstellen, genehmigen, finalisieren |
| Anwesenheit | `attendance.*` | Anwesenheiten verwalten, Ersatzmitglieder zuweisen |
| Dokumente | `document.*` | Dokumente verwalten, Gastzugriff steuern |
| Beschlüsse | `resolution.*` | Beschlüsse und Wahlen verwalten |
| Kalender | `calendar.*` | Termine und Abwesenheiten verwalten |
| Gremien | `committee.*` | Gremien und Mitglieder verwalten |
| Rollen & Rechte | `role.*` | Rollen und Berechtigungen verwalten |
| System | `system.*` | Systemweite Verwaltung, Audit-Logs |

### 6.2.2 Vollständiger Berechtigungskatalog

#### Sitzungen & Tagesordnungen

| Codename | Beschreibung |
|----------|-------------|
| `meeting.create` | Sitzung erstellen |
| `meeting.edit` | Sitzung bearbeiten |
| `meeting.delete_draft` | Sitzung im Entwurf-Status löschen |
| `meeting.view` | Sitzung/Tagesordnung einsehen |
| `meeting.send` | Tagesordnung versenden |
| `meeting.complete` | Sitzung abschließen |
| `agenda.add_item` | TOP hinzufügen |
| `agenda.edit_item` | TOP bearbeiten |
| `agenda.delete_item` | TOP löschen |
| `agenda.reorder` | TOPs umsortieren |
| `agenda.manage_templates` | Vorlagen erstellen/bearbeiten/löschen |

#### Protokolle

| Codename | Beschreibung |
|----------|-------------|
| `minutes.create` | Protokoll erstellen |
| `minutes.edit` | Protokoll bearbeiten |
| `minutes.submit` | Protokoll zur Prüfung einreichen |
| `minutes.approve` | Protokoll genehmigen |
| `minutes.reject` | Protokoll zurückweisen |
| `minutes.finalize` | Protokoll finalisieren |
| `minutes.view` | Protokoll einsehen |
| `minutes.view_versions` | Versionshistorie einsehen |
| `minutes.export_pdf` | PDF-Export durchführen |

#### Anwesenheit

| Codename | Beschreibung |
|----------|-------------|
| `attendance.confirm_own` | Eigene Anwesenheit bestätigen |
| `attendance.view_list` | Anwesenheitsliste einsehen |
| `attendance.edit` | Anwesenheit anderer bearbeiten |
| `attendance.assign_substitute` | Ersatzmitglied zuweisen |
| `attendance.view_suggestions` | Ersatzmitglieder-Vorschläge einsehen |
| `attendance.check_quorum` | Beschlussfähigkeit prüfen |

#### Dokumente

| Codename | Beschreibung |
|----------|-------------|
| `document.upload` | Dokument hochladen |
| `document.view_committee` | Gremiumsdokumente einsehen |
| `document.view_restricted` | Eingeschränkte Dokumente einsehen |
| `document.view_confidential` | Vertrauliche Dokumente einsehen |
| `document.edit_own` | Eigene Dokumente bearbeiten/löschen |
| `document.edit_all` | Alle Dokumente bearbeiten/löschen |
| `document.manage_access` | Gastzugriff gewähren/widerrufen |
| `document.manage_folders` | Ordner erstellen/bearbeiten/löschen |

#### Beschlüsse & Wahlen

| Codename | Beschreibung |
|----------|-------------|
| `resolution.create` | Beschluss erstellen |
| `resolution.edit` | Beschluss bearbeiten |
| `resolution.record_vote` | Abstimmungsergebnis erfassen |
| `resolution.override_result` | Beschlussfähigkeit oder Abstimmungsergebnis manuell überschreiben |
| `resolution.view` | Beschlüsse einsehen |
| `resolution.participate_vote` | An Abstimmung teilnehmen |
| `resolution.manage_elections` | Wahlen erstellen und verwalten |

#### Kalender

| Codename | Beschreibung |
|----------|-------------|
| `calendar.view` | Kalender einsehen |
| `calendar.manage_own_absence` | Eigene Abwesenheit eintragen/bearbeiten |
| `calendar.create_meeting_event` | Sitzungstermin erstellen |
| `calendar.export_ical` | iCal-Export |

#### Gremien & Mitglieder

| Codename | Beschreibung |
|----------|-------------|
| `committee.create` | Gremium erstellen |
| `committee.edit` | Gremium bearbeiten |
| `committee.view` | Gremiumsdetails einsehen |
| `committee.manage_members` | Mitglieder hinzufügen/entfernen/bearbeiten |
| `committee.view_members` | Mitgliederliste einsehen |

#### Rollen & Rechte

| Codename | Beschreibung |
|----------|-------------|
| `role.create` | Neue Rolle erstellen |
| `role.edit` | Rolle bearbeiten (Name, Beschreibung) |
| `role.delete` | Rolle löschen |
| `role.assign_permissions` | Berechtigungen einer Rolle zuweisen/entziehen |
| `role.view` | Rollen und deren Berechtigungen einsehen |
| `role.assign_to_member` | Rolle einem Mitglied zuweisen |

#### System

| Codename | Beschreibung |
|----------|-------------|
| `system.admin` | Vollzugriff auf alle Systemfunktionen |
| `system.view_audit_logs` | Audit-Logs einsehen |
| `system.export_audit_logs` | Audit-Logs exportieren |
| `system.manage_users` | Benutzerkonten verwalten |

---

## 6.3 Rollenmodell

### 6.3.1 Rollentypen

| Typ | Scope | Beschreibung |
|-----|-------|-------------|
| **Systemrolle** | Systemweit | Gilt unabhängig von Gremien (z. B. System-Admin) |
| **Gremiumsrolle** | Pro Gremium | Wird einem Mitglied innerhalb eines Gremiums zugewiesen |

### 6.3.2 Vordefinierte Standard-Rollen

Das System liefert folgende Standard-Rollen aus. Diese dienen als **Ausgangsbasis** und können vom Administrator **angepasst, erweitert oder als Vorlage für neue Rollen** verwendet werden.

> **Hinweis:** Standard-Rollen, die als `is_system_role = true` markiert sind, können nicht gelöscht, aber in ihren Berechtigungen angepasst werden. Benutzerdefinierte Rollen können vollständig erstellt, bearbeitet und gelöscht werden.

#### Systemrollen (Standard)

| Rolle | Kürzel | Löschbar | Beschreibung |
|-------|--------|----------|-------------|
| **System-Admin** | `SYSTEM_ADMIN` | Nein | Vollzugriff auf das gesamte System |
| **Benutzer** | `USER` | Nein | Basis-Zugriff, kann Gremien beitreten |

#### Gremiumsrollen (Standard)

| Rolle | Kürzel | Löschbar | Standard-Berechtigungen |
|-------|--------|----------|------------------------|
| **Vorsitz** | `CHAIR` | Nein | Alle Gremiums-Berechtigungen inkl. `role.*`, `minutes.approve`, `minutes.finalize` |
| **Stellv. Vorsitz** | `VICE_CHAIR` | Nein | Wie Vorsitz, außer `minutes.finalize` und `role.delete` |
| **Mitglied** | `MEMBER` | Nein | Lese-/Abstimmungsrechte, eigene Dokumente verwalten |
| **Protokollführung** | `CLERK` | Nein | Wie Mitglied + `minutes.create`, `minutes.edit`, `minutes.submit` |
| **Ersatzmitglied** | `SUBSTITUTE` | Nein | Kontextabhängig (siehe 6.5) + dauerhaft: `calendar.view`, `calendar.manage_own_absence` |
| **Gast** | `GUEST` | Nein | Zeitbegrenzter Zugriff auf freigegebene Dokumente |

### 6.3.3 Benutzerdefinierte Rollen

Administratoren und Vorsitzende können **eigene Rollen erstellen**:

- **Name und Beschreibung** frei wählbar.
- **Berechtigungen** aus dem Berechtigungskatalog (6.2.2) beliebig zusammenstellbar.
- **Scope:** Benutzerdefinierte Rollen können als System- oder Gremiumsrollen erstellt werden.
- **Vorlagen:** Bestehende Rollen können als Vorlage dupliziert und angepasst werden.
- **Löschbar:** Benutzerdefinierte Rollen können gelöscht werden, sofern sie keinem Mitglied mehr zugewiesen sind.

**Beispiel-Szenarien:**

| Benutzerdefinierte Rolle | Anwendungsfall | Berechtigungen |
|--------------------------|---------------|----------------|
| Leseberechtigter | Externer Prüfer, nur Leserechte | `meeting.view`, `minutes.view`, `resolution.view`, `document.view_committee` |
| Assistenz Vorsitz | Unterstützt den Vorsitz bei der Verwaltung | Alle Rechte des Vorsitzes ohne `role.*` und `minutes.finalize` |
| Archivbeauftragter | Zuständig für Dokumentenverwaltung | `document.*`, `calendar.view` |
| Wahlleitender | Leitet Wahlen | `resolution.manage_elections`, `resolution.record_vote`, `resolution.view` |

---

## 6.4 Standard-Berechtigungsmatrix

Die folgende Matrix zeigt die **Standard-Zuordnung** der Berechtigungen zu den vordefinierten Rollen. Diese Zuordnungen sind **veränderbar** über die Rollenverwaltung.

### 6.4.1 Sitzungen & Tagesordnungen

| Berechtigung | Admin | Vorsitz | Stellv. Vorsitz | Mitglied | Protokollf. | Ersatz (aktiv) | Ersatz (inaktiv) | Gast |
|-------------|-------|---------|----------------|----------|-------------|---------------|-----------------|------|
| `meeting.create` | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| `meeting.edit` | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| `meeting.delete_draft` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| `meeting.view` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| `meeting.send` | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| `agenda.add_item` | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| `agenda.edit_item` | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| `agenda.manage_templates` | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |

### 6.4.2 Protokolle

| Berechtigung | Admin | Vorsitz | Stellv. Vorsitz | Mitglied | Protokollf. | Ersatz (aktiv) | Ersatz (inaktiv) | Gast |
|-------------|-------|---------|----------------|----------|-------------|---------------|-----------------|------|
| `minutes.create` | ✅ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| `minutes.edit` | ✅ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| `minutes.submit` | ✅ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| `minutes.approve` | ✅ | ✅ | ✅* | ❌ | ❌ | ❌ | ❌ | ❌ |
| `minutes.reject` | ✅ | ✅ | ✅* | ❌ | ❌ | ❌ | ❌ | ❌ |
| `minutes.finalize` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| `minutes.view` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| `minutes.view_versions` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| `minutes.export_pdf` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |

\* Stellv. Vorsitz standardmäßig nur bei Abwesenheit des Vorsitzes. Diese Einschränkung kann über die Rollenkonfiguration aufgehoben werden.

### 6.4.3 Anwesenheit

| Berechtigung | Admin | Vorsitz | Stellv. Vorsitz | Mitglied | Protokollf. | Ersatz (aktiv) | Ersatz (inaktiv) | Gast |
|-------------|-------|---------|----------------|----------|-------------|---------------|-----------------|------|
| `attendance.confirm_own` | – | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| `attendance.view_list` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| `attendance.edit` | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| `attendance.assign_substitute` | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| `attendance.view_suggestions` | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |

### 6.4.4 Dokumente

| Berechtigung | Admin | Vorsitz | Stellv. Vorsitz | Mitglied | Protokollf. | Ersatz (aktiv) | Ersatz (inaktiv) | Gast |
|-------------|-------|---------|----------------|----------|-------------|---------------|-----------------|------|
| `document.upload` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| `document.view_committee` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| `document.view_restricted` | ✅ | ✅ | ✅ | Nur Berechtigte | Nur Berechtigte | Nur Berechtigte | ❌ | ❌ |
| `document.view_confidential` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| `document.edit_own` | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| `document.edit_all` | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| `document.manage_access` | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |

### 6.4.5 Beschlüsse & Wahlen

| Berechtigung | Admin | Vorsitz | Stellv. Vorsitz | Mitglied | Protokollf. | Ersatz (aktiv) | Ersatz (inaktiv) | Gast |
|-------------|-------|---------|----------------|----------|-------------|---------------|-----------------|------|
| `resolution.create` | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| `resolution.record_vote` | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| `resolution.view` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| `resolution.participate_vote` | – | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| `resolution.manage_elections` | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |

### 6.4.6 Kalender

| Berechtigung | Admin | Vorsitz | Stellv. Vorsitz | Mitglied | Protokollf. | Ersatz (aktiv) | Ersatz (inaktiv) | Gast |
|-------------|-------|---------|----------------|----------|-------------|---------------|-----------------|------|
| `calendar.view` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | **✅** | ❌ |
| `calendar.manage_own_absence` | – | ✅ | ✅ | ✅ | ✅ | ✅ | **✅** | ❌ |
| `calendar.create_meeting_event` | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| `calendar.export_ical` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | **✅** | ❌ |

> **Besonderheit:** Ersatzmitglieder haben **unabhängig vom Einsatzstatus** dauerhaften Zugriff auf den Kalender. Diese Berechtigungen (`calendar.view`, `calendar.manage_own_absence`, `calendar.export_ical`) sind als **permanente Berechtigungen** konfiguriert und nicht an den Einsatzstatus gebunden.

---

## 6.5 Ersatzmitglieder – Zugriffslogik

### Automatische Rechteaktivierung

```
Ersatzmitglied wird einer Sitzung zugewiesen (SubstituteAssignment)
    │
    ▼
System aktiviert temporäre Berechtigungen:
  - meeting.view (für die zugewiesene Sitzung)
  - minutes.view (für die zugewiesene Sitzung)
  - attendance.confirm_own
  - resolution.participate_vote
  - resolution.view
  - document.view_committee (für Sitzungsdokumente)
  - document.upload
    │
    ▼
Nach Abschluss der Sitzung:
  - Zugriff auf Sitzungsdaten bleibt bestehen (für die zugewiesene Sitzung)
  - Neuer temporärer Zugriff nur bei erneuter Zuweisung
```

### Permanente Berechtigungen (unabhängig vom Einsatz)

| Berechtigung | Beschreibung |
|-------------|-------------|
| `calendar.view` | Kalender einsehen |
| `calendar.manage_own_absence` | Eigene Abwesenheiten verwalten |
| `calendar.export_ical` | iCal-Export |
| – | Eigenes Profil bearbeiten |
| – | Benachrichtigungen empfangen und verwalten |

---

## 6.6 Gastzugriff

### Einladungsprozess

1. Benutzer mit Berechtigung `document.manage_access` erstellt eine Gasteinladung mit Angabe der freigegebenen Dokumente.
2. System generiert einen zeitbegrenzten Zugangslink.
3. Gast registriert sich oder meldet sich an.
4. Gast hat Zugriff auf die freigegebenen Dokumente bis zum Ablaufdatum.
5. Nach Ablauf wird der Zugriff automatisch entzogen.

### Zeitbegrenzung

- Standardmäßig: Zugriff bis 24 Stunden nach der Sitzung.
- Individuell konfigurierbar durch berechtigte Benutzer.
- Automatische Aufräumung durch Celery-Task.

---

## 6.7 Rollenverwaltung – Benutzeroberfläche

### 6.7.1 Rollen-Übersicht

- Tabellarische Ansicht aller verfügbaren Rollen (System- und Gremiumsrollen).
- Anzeige: Name, Beschreibung, Typ (System/Gremium), Anzahl zugewiesener Mitglieder, Status (Standard/Benutzerdefiniert).
- Filter nach Typ, Status und Gremium.

### 6.7.2 Rolle erstellen/bearbeiten

- **Formular:**
  - Name (Pflichtfeld, eindeutig pro Scope)
  - Beschreibung (optional)
  - Rollentyp: System oder Gremium
  - Vorlage: Optional – Berechtigungen einer bestehenden Rolle als Ausgangsbasis kopieren
- **Berechtigungs-Editor:**
  - Berechtigungen sind nach Kategorien (Modulen) gruppiert.
  - Checkboxen zum Aktivieren/Deaktivieren einzelner Berechtigungen.
  - „Alle auswählen" / „Alle abwählen" pro Kategorie.
  - Suchfunktion zum schnellen Finden von Berechtigungen.
  - Vorschau der resultierenden Zugriffsmatrix.

### 6.7.3 Rolle zuweisen

- Bei der Mitgliederverwaltung eines Gremiums: Dropdown zur Rollenauswahl.
- Nur Gremiumsrollen werden im Gremiums-Kontext angeboten.
- Systemrollen werden in der globalen Benutzerverwaltung zugewiesen.
- **Rollenwechsel:** Bei Änderung der Rolle werden die Berechtigungen sofort aktualisiert.
- **Audit-Trail:** Jede Rollenzuweisung und -änderung wird im Audit-Log protokolliert.

### 6.7.4 Rolle löschen

- Nur benutzerdefinierte Rollen (nicht Systemrollen) sind löschbar.
- **Voraussetzung:** Die Rolle darf keinem Mitglied mehr zugewiesen sein.
- Vor dem Löschen: Warnung mit Auflistung aller aktuell zugewiesenen Mitglieder.
- Alternative: Mitglieder können einer neuen Rolle zugeordnet werden (Rollen-Migration).

---

## 6.8 Technische Umsetzung

### Django-Implementierung

```python
# Dynamische Berechtigungsprüfung (Django Mixin für Class-Based Views)
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied

class DynamicPermissionMixin:
    """Mixin für dynamische Berechtigungsprüfung basierend auf Gremiumsrollen."""
    required_permission = None

    def get_committee(self):
        """Muss von der konkreten View überschrieben werden."""
        raise NotImplementedError

    def check_permission(self, user):
        committee = self.get_committee()

        # System-Admin hat immer Zugriff
        if user.system_role and user.system_role.codename == 'SYSTEM_ADMIN':
            return True

        # Gremiumsrolle des Benutzers laden
        membership = Membership.objects.filter(
            user=user,
            committee=committee,
            is_active=True
        ).select_related('role').first()

        if not membership:
            return False

        # Berechtigung über die zugewiesene Rolle prüfen
        return RolePermission.objects.filter(
            role=membership.role,
            permission__codename=self.required_permission
        ).exists()

    def dispatch(self, request, *args, **kwargs):
        if not self.check_permission(request.user):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)


def check_active_substitute(user, meeting):
    """Prüft ob das Ersatzmitglied für die Sitzung aktiv ist."""
    return SubstituteAssignment.objects.filter(
        substitute=user,
        meeting=meeting,
        access_revoked_at__isnull=True
    ).exists()


# Beispiel: View mit dynamischer Berechtigungsprüfung
class MeetingEditView(LoginRequiredMixin, DynamicPermissionMixin, UpdateView):
    model = Meeting
    form_class = MeetingForm
    template_name = 'agendas/meeting_form.html'
    required_permission = 'meeting.edit'

    def get_committee(self):
        return self.get_object().committee
```

### Berechtigungsprüfungs-Reihenfolge

1. **Authentifizierung:** Ist der Benutzer angemeldet?
2. **Systemrolle:** Hat der Benutzer eine Systemrolle mit `system.admin`-Berechtigung? → Vollzugriff.
3. **Gremiumsmitgliedschaft:** Ist der Benutzer Mitglied des betreffenden Gremiums?
4. **Rollenberechtigung:** Hat die zugewiesene Gremiumsrolle die erforderliche Berechtigung?
5. **Kontextprüfung:** Zusätzliche Prüfungen (z. B. Einsatzstatus bei Ersatzmitgliedern, Zeitbegrenzung bei Gästen).
6. **Objekt-Level:** Hat der Benutzer Zugriff auf das spezifische Objekt (z. B. Dokument-Zugriffsebene)?

### Caching

- Rollen-Berechtigung-Zuordnungen werden in **Redis** gecached.
- Cache-Invalidierung bei Änderung von Rollen oder Berechtigungszuordnungen.
- TTL: 5 Minuten (konfigurierbar).
- Individuelle User-Permission-Caches für schnelle Abfragen.

---

## 6.9 Sicherheitsaspekte

### Schutzmaßnahmen für die Rollenverwaltung

- **Vier-Augen-Prinzip (optional):** Kritische Rollenänderungen (z. B. Hinzufügen von `system.admin`) können ein Bestätigungs-Workflow erfordern.
- **Unveränderbare Kern-Berechtigungen:** Die `system.admin`-Berechtigung kann nur durch einen bestehenden System-Admin vergeben werden.
- **Rollenänderungs-Audit:** Jede Änderung an Rollen und Berechtigungszuordnungen wird detailliert im Audit-Log protokolliert (alter Zustand → neuer Zustand).
- **Maximale Berechtigung:** Benutzerdefinierte Rollen können nicht mehr Rechte erhalten als die Rolle des Erstellers (Privilege Escalation Prevention).

---

## 6.10 Audit & Compliance

- **Alle Berechtigungsprüfungen** werden im Audit-Log protokolliert.
- **Fehlgeschlagene Zugriffsversuche** werden besonders markiert und lösen bei Häufung eine Warnung aus.
- **Regelmäßige Rechte-Reviews:** Das System bietet eine Übersicht aller aktiven Berechtigungen pro Gremium und pro Rolle.
- **Rollenänderungs-Historie:** Vollständiger Verlauf aller Änderungen an Rollen und Berechtigungszuordnungen.
- **Berechtigungs-Diff:** Bei Rollenänderungen wird ein Diff (hinzugefügte/entfernte Berechtigungen) protokolliert.
- **Zugriffsprotokolle** können für DSGVO-Auskunftsersuchen exportiert werden.
- **Compliance-Bericht:** Export einer vollständigen Berechtigungsmatrix pro Gremium für interne Prüfungen.
