# 05 – URL- und View-Konzept

## 5.1 Übersicht

Da der BR Manager als Django-Monolith aufgebaut ist, wird die gesamte Anwendungslogik über **Django Views** und **Django
Templates** bereitgestellt. Die Navigation erfolgt über ein klassisches URL-Routing. Für dynamische Interaktionen (
HTMX-Requests) liefern Views **HTML-Fragmente** statt vollständiger Seiten zurück.

### Architektur-Prinzip

```
Browser-Request (GET /meetings/a1b2c3d4-e5f6-7890-abcd-ef1234567890/)
         │
         ▼
┌────────────────────────┐
│  Django URL-Router     │
│  (config/urls.py →     │
│   apps/*/urls.py)      │
└────────┬───────────────┘
         │
         ▼
┌────────────────────────┐
│  Middleware             │
│  - AuthenticationMiddleware
│  - PermissionMiddleware │
│  - AuditMiddleware      │
└────────┬───────────────┘
         │
         ▼
┌────────────────────────┐
│  Django View            │
│  - Geschäftslogik       │
│  - Formular-Validierung │
│  - Template rendern     │
└────────┬───────────────┘
         │
         ▼
┌────────────────────────┐
│  Response               │
│  - Vollständige Seite   │
│    (normaler Request)   │
│  - HTML-Fragment        │
│    (HTMX-Request)       │
└────────────────────────┘
```

### Konventionen

- **URL-Schema:** Lesbare, hierarchische URLs mit UUIDs (z. B. `/meetings/a1b2c3d4-e5f6-7890-abcd-ef1234567890/agenda/`)
- **Authentifizierung:** Django Sessions (Cookie-basiert, CSRF-geschützt)
- **Berechtigungsprüfung:** Decorator-basiert (`@login_required`, `@permission_required`) oder Mixins
- **HTMX-Erkennung:** `request.headers.get('HX-Request')` – liefert Fragment statt volle Seite
- **Formulare:** Django Forms mit serverseitiger Validierung
- **Namespacing:** Jede App hat einen eigenen URL-Namespace (z. B. `agendas:detail`)
- **UUIDs statt Integer-IDs:** Alle Modelle verwenden UUIDs als Primärschlüssel. In URLs werden ausschließlich UUIDs
  verwendet (`<uuid:id>`), um das Erraten von Ressourcen-IDs durch sequentielle Nummerierung zu verhindern.

## 5.2 URL-Konfiguration

### Root-URL-Konfiguration (`config/urls.py`)

```python
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('apps.accounts.urls', namespace='accounts')),
    path('committees/', include('apps.committees.urls', namespace='committees')),
    path('meetings/', include('apps.meetings.urls', namespace='meetings')),
    path('meetings/<uuid:meeting_id>/agenda/', include('apps.agendas.urls', namespace='agendas')),
    path('minutes/', include('apps.minutes.urls', namespace='minutes')),
    path('attendance/', include('apps.attendance.urls', namespace='attendance')),
    path('documents/', include('apps.documents.urls', namespace='documents')),
    path('resolutions/', include('apps.resolutions.urls', namespace='resolutions')),
    path('calendar/', include('apps.calendar_mgmt.urls', namespace='calendar')),
    path('notifications/', include('apps.notifications.urls', namespace='notifications')),
    path('roles/', include('apps.roles.urls', namespace='roles')),
    path('audit/', include('apps.audit.urls', namespace='audit')),
    path('todos/', include('apps.todos.urls', namespace='todos')),
    path('personnel/', include('apps.personnel.urls', namespace='personnel')),
    path('', include('apps.core.urls', namespace='core')),  # Dashboard
]
```

## 5.3 URLs und Views nach Modul

### 5.3.1 Authentifizierung & Benutzerverwaltung (`/accounts/`)

| URL                          | View                  | Methode  | Beschreibung                       |
|------------------------------|-----------------------|----------|------------------------------------|
| `/accounts/login/`           | `LoginView`           | GET/POST | Login-Seite (E-Mail + Passwort)    |
| `/accounts/logout/`          | `LogoutView`          | POST     | Logout                             |
| `/accounts/profile/`         | `ProfileView`         | GET/POST | Eigenes Profil anzeigen/bearbeiten |
| `/accounts/password/change/` | `PasswordChangeView`  | GET/POST | Passwort ändern                    |
| `/accounts/2fa/setup/`       | `TwoFactorSetupView`  | GET/POST | 2FA einrichten                     |
| `/accounts/2fa/verify/`      | `TwoFactorVerifyView` | GET/POST | 2FA-Code verifizieren              |
| `/accounts/oauth/login/`     | `OAuthLoginView`      | GET      | OAuth2-Autorisierung starten       |
| `/accounts/oauth/callback/`  | `OAuthCallbackView`   | GET      | OAuth2-Callback verarbeiten        |

### 5.3.2 Dashboard (`/`)

| URL | View            | Methode | Beschreibung                                                             |
|-----|-----------------|---------|--------------------------------------------------------------------------|
| `/` | `DashboardView` | GET     | Übersichtsseite (nächste Sitzungen, offene Aufgaben, Benachrichtigungen) |

### 5.3.3 Gremien & Mitgliedschaften (`/committees/`)

| URL                                                | View                  | Methode  | Beschreibung                                                                    |
|----------------------------------------------------|-----------------------|----------|---------------------------------------------------------------------------------|
| `/committees/`                                     | `CommitteeListView`   | GET      | Alle Gremien (des Benutzers) auflisten                                          |
| `/committees/create/`                              | `CommitteeCreateView` | GET/POST | Neues Gremium erstellen                                                         |
| `/committees/<uuid:id>/`                           | `CommitteeDetailView` | GET      | Gremiumsdetails anzeigen                                                        |
| `/committees/<uuid:id>/edit/`                      | `CommitteeEditView`   | GET/POST | Gremium bearbeiten                                                              |
| `/committees/<uuid:id>/members/`                   | `MemberListView`      | GET      | Mitglieder auflisten                                                            |
| `/committees/<uuid:id>/members/add/`               | `MemberAddView`       | GET/POST | Mitglied hinzufügen (mit Rollenzuweisung, Listenname, Listenplatz, Stimmenzahl) |
| `/committees/<uuid:id>/members/<uuid:mid>/edit/`   | `MemberEditView`      | GET/POST | Mitgliedschaft bearbeiten (inkl. Rolle, Listenname, Listenplatz, Stimmenzahl)   |
| `/committees/<uuid:id>/members/<uuid:mid>/remove/` | `MemberRemoveView`    | POST     | Mitglied entfernen                                                              |
| `/committees/<uuid:id>/substitutes/`               | `SubstituteListView`  | GET      | Ersatzmitglieder mit Listenname, Listenplatz und Rang anzeigen                  |

**HTMX-Fragmente:**

| URL                                                     | Trigger              | Beschreibung                            |
|---------------------------------------------------------|----------------------|-----------------------------------------|
| `/committees/<uuid:id>/members/search/`                 | `hx-get` (Suchfeld)  | Live-Suche in Mitgliederliste           |
| `/committees/<uuid:id>/members/<uuid:mid>/inline-edit/` | `hx-get` / `hx-post` | Inline-Bearbeitung einer Mitgliedschaft |

### 5.3.4 Sitzungsverwaltung (`/meetings/`)

| URL                             | View                      | Methode  | Beschreibung                                                                                                                                                                                                                                   |
|---------------------------------|---------------------------|----------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `/meetings/`                    | `MeetingListView`         | GET      | Sitzungen auflisten                                                                                                                                                                                                                            |
| `/meetings/create/`             | `MeetingCreateView`       | GET/POST | Neue Sitzung erstellen (Typ: Online/Hybrid/Präsenz, Vorsitz, Protokollführung). Bei Online: nur Teilnahmelink; bei Hybrid/Präsenz: Adressfelder (Ortsbezeichnung, Straße, PLZ, Stadt, Raum). Formular passt sich dynamisch dem Sitzungstyp an. |
| `/meetings/from-template/`      | `MeetingFromTemplateView` | GET/POST | Sitzung aus Vorlage erstellen                                                                                                                                                                                                                  |
| `/meetings/<uuid:id>/`          | `MeetingDetailView`       | GET      | Sitzungsdetails mit Tagesordnung, Vorsitz und Protokollführung                                                                                                                                                                                 |
| `/meetings/<uuid:id>/edit/`     | `MeetingEditView`         | GET/POST | Sitzung bearbeiten (Adressfelder je nach Sitzungstyp: Online → Teilnahmelink; Hybrid → Teilnahmelink + Adresse; Präsenz → Adresse)                                                                                                             |
| `/meetings/<uuid:id>/delete/`   | `MeetingDeleteView`       | POST     | Sitzung löschen (nur Entwurf)                                                                                                                                                                                                                  |
| `/meetings/<uuid:id>/send/`     | `MeetingSendView`         | POST     | Tagesordnung per E-Mail versenden                                                                                                                                                                                                              |
| `/meetings/<uuid:id>/complete/` | `MeetingCompleteView`     | POST     | Sitzung abschließen                                                                                                                                                                                                                            |

### 5.3.5 Tagesordnungen (`/meetings/<uuid:id>/agenda/`)

| URL                                             | View                   | Methode  | Beschreibung                        |
|-------------------------------------------------|------------------------|----------|-------------------------------------|
| `/meetings/<uuid:id>/agenda/add/`               | `AgendaItemCreateView` | GET/POST | Tagesordnungspunkt (TOP) hinzufügen |
| `/meetings/<uuid:id>/agenda/<uuid:aid>/edit/`   | `AgendaItemEditView`   | GET/POST | TOP bearbeiten                      |
| `/meetings/<uuid:id>/agenda/<uuid:aid>/delete/` | `AgendaItemDeleteView` | POST     | TOP löschen                         |

**HTMX-Fragmente:**

| URL                                                  | Trigger                 | Beschreibung                     |
|------------------------------------------------------|-------------------------|----------------------------------|
| `/meetings/<uuid:id>/agenda/reorder/`                | `hx-post` (Drag & Drop) | TOPs per Drag & Drop umsortieren |
| `/meetings/<uuid:id>/agenda/<uuid:aid>/inline-edit/` | `hx-get` / `hx-post`    | TOP inline bearbeiten            |

### 5.3.6 Tagesordnungsvorlagen (`/meetings/templates/`)

| URL                                     | View                 | Methode  | Beschreibung           |
|-----------------------------------------|----------------------|----------|------------------------|
| `/meetings/templates/`                  | `TemplateListView`   | GET      | Vorlagen auflisten     |
| `/meetings/templates/create/`           | `TemplateCreateView` | GET/POST | Neue Vorlage erstellen |
| `/meetings/templates/<uuid:id>/`        | `TemplateDetailView` | GET      | Vorlagendetails        |
| `/meetings/templates/<uuid:id>/edit/`   | `TemplateEditView`   | GET/POST | Vorlage bearbeiten     |
| `/meetings/templates/<uuid:id>/delete/` | `TemplateDeleteView` | POST     | Vorlage löschen        |

### 5.3.7 Protokolle (`/minutes/`)

| URL                                      | View                       | Methode  | Beschreibung                                 |
|------------------------------------------|----------------------------|----------|----------------------------------------------|
| `/meetings/<uuid:id>/minutes/`           | `MinutesDetailView`        | GET      | Protokoll einer Sitzung anzeigen             |
| `/meetings/<uuid:id>/minutes/create/`    | `MinutesCreateView`        | GET/POST | Protokoll erstellen (WYSIWYG-Editor)         |
| `/minutes/<uuid:id>/edit/`               | `MinutesEditView`          | GET/POST | Protokoll bearbeiten                         |
| `/minutes/<uuid:id>/sign/clerk/`         | `MinutesSignClerkView`     | POST     | Digitale Unterschrift durch Protokollführung |
| `/minutes/<uuid:id>/sign/chair/`         | `MinutesSignChairView`     | POST     | Digitale Unterschrift durch Vorsitz          |
| `/minutes/<uuid:id>/reject/`             | `MinutesRejectView`        | POST     | Zurückweisen (mit Kommentar)                 |
| `/minutes/<uuid:id>/finalize/`           | `MinutesFinalizeView`      | POST     | Finalisieren (nach Sitzungsbeschluss)        |
| `/minutes/<uuid:id>/versions/`           | `MinutesVersionListView`   | GET      | Versionshistorie                             |
| `/minutes/<uuid:id>/versions/<version>/` | `MinutesVersionDetailView` | GET      | Bestimmte Version anzeigen                   |
| `/minutes/<uuid:id>/diff/<v1>/<v2>/`     | `MinutesDiffView`          | GET      | Diff zwischen Versionen                      |
| `/minutes/<uuid:id>/export/pdf/`         | `MinutesPDFExportView`     | GET      | PDF-Export/Download                          |

**HTMX-Fragmente:**

| URL                            | Trigger           | Beschreibung                      |
|--------------------------------|-------------------|-----------------------------------|
| `/minutes/<uuid:id>/autosave/` | `hx-post` (Timer) | Auto-Save während der Bearbeitung |
| `/minutes/<uuid:id>/preview/`  | `hx-get`          | Live-Vorschau des Protokolls      |

### 5.3.8 Anwesenheit (`/attendance/`)

| URL                                           | View                        | Methode  | Beschreibung                                                                                   |
|-----------------------------------------------|-----------------------------|----------|------------------------------------------------------------------------------------------------|
| `/meetings/<uuid:id>/attendance/`             | `AttendanceListView`        | GET      | Anwesenheitsliste anzeigen                                                                     |
| `/meetings/<uuid:id>/attendance/confirm/`     | `AttendanceConfirmView`     | GET/POST | Anwesenheit bestätigen (mit 2FA, Online/Hybrid)                                                |
| `/meetings/<uuid:id>/attendance/print/`       | `AttendancePrintView`       | GET      | Druckbare Anwesenheitsliste (Präsenz)                                                          |
| `/meetings/<uuid:id>/attendance/manual/`      | `AttendanceManualEntryView` | GET/POST | Manuelle Anwesenheitseintragung (Präsenz)                                                      |
| `/attendance/<uuid:id>/edit/`                 | `AttendanceEditView`        | GET/POST | Anwesenheit bearbeiten                                                                         |
| `/meetings/<uuid:id>/substitute-suggestions/` | `SubstituteSuggestionsView` | GET      | Ersatzmitglieder-Vorschläge (nach Listenzugehörigkeit, Listenplatz, Geschlecht, Verfügbarkeit) |
| `/meetings/<uuid:id>/assign-substitute/`      | `AssignSubstituteView`      | POST     | Ersatzmitglied zuweisen                                                                        |
| `/meetings/<uuid:id>/quorum/`                 | `QuorumCheckView`           | GET      | Beschlussfähigkeit prüfen                                                                      |

**HTMX-Fragmente:**

| URL                                      | Trigger            | Beschreibung                          |
|------------------------------------------|--------------------|---------------------------------------|
| `/meetings/<uuid:id>/attendance/status/` | `hx-get` (Polling) | Live-Anwesenheitsstatus aktualisieren |
| `/meetings/<uuid:id>/quorum/check/`      | `hx-get`           | Beschlussfähigkeit live prüfen        |

### 5.3.9 Dokumente (`/documents/`)

| URL                                                   | View                        | Methode  | Beschreibung                           |
|-------------------------------------------------------|-----------------------------|----------|----------------------------------------|
| `/documents/`                                         | `DocumentListView`          | GET      | Dokumente auflisten (mit Filter/Suche) |
| `/documents/upload/`                                  | `DocumentUploadView`        | GET/POST | Dokument hochladen                     |
| `/documents/<uuid:id>/`                               | `DocumentDetailView`        | GET      | Dokumentendetails anzeigen             |
| `/documents/<uuid:id>/edit/`                          | `DocumentEditView`          | GET/POST | Dokumentenmetadaten bearbeiten         |
| `/documents/<uuid:id>/delete/`                        | `DocumentDeleteView`        | POST     | Dokument löschen                       |
| `/documents/<uuid:id>/download/`                      | `DocumentDownloadView`      | GET      | Dokument herunterladen                 |
| `/documents/<uuid:id>/preview/`                       | `DocumentPreviewView`       | GET      | Dokumentenvorschau                     |
| `/documents/<uuid:id>/versions/`                      | `DocumentVersionListView`   | GET      | Versionshistorie                       |
| `/documents/<uuid:id>/versions/upload/`               | `DocumentVersionUploadView` | POST     | Neue Version hochladen                 |
| `/documents/<uuid:id>/share/`                         | `DocumentShareView`         | GET/POST | Gastzugriff gewähren                   |
| `/documents/<uuid:id>/share/<uuid:access_id>/revoke/` | `DocumentShareRevokeView`   | POST     | Gastzugriff widerrufen                 |
| `/documents/folders/`                                 | `FolderListView`            | GET      | Ordner auflisten                       |
| `/documents/folders/create/`                          | `FolderCreateView`          | GET/POST | Ordner erstellen                       |
| `/documents/folders/<uuid:id>/edit/`                  | `FolderEditView`            | GET/POST | Ordner bearbeiten                      |
| `/documents/folders/<uuid:id>/delete/`                | `FolderDeleteView`          | POST     | Ordner löschen                         |

**HTMX-Fragmente:**

| URL                                     | Trigger             | Beschreibung                |
|-----------------------------------------|---------------------|-----------------------------|
| `/documents/search/`                    | `hx-get` (Suchfeld) | Live-Suche in Dokumenten    |
| `/documents/<uuid:id>/upload-progress/` | `hx-get` (Polling)  | Upload-Fortschritt anzeigen |

### 5.3.10 Beschlüsse & Wahlen (`/resolutions/`)

| URL                                        | View                         | Methode  | Beschreibung                                                                               |
|--------------------------------------------|------------------------------|----------|--------------------------------------------------------------------------------------------|
| `/resolutions/`                            | `ResolutionListView`         | GET      | Beschlüsse auflisten                                                                       |
| `/resolutions/create/`                     | `ResolutionCreateView`       | GET/POST | Beschluss erstellen                                                                        |
| `/resolutions/<uuid:id>/`                  | `ResolutionDetailView`       | GET      | Beschlussdetails anzeigen                                                                  |
| `/resolutions/<uuid:id>/edit/`             | `ResolutionEditView`         | GET/POST | Beschluss bearbeiten                                                                       |
| `/resolutions/<uuid:id>/vote/`             | `ResolutionVoteView`         | GET/POST | Abstimmungsergebnis erfassen (inkl. Beschlussfähigkeit und Ergebnis-Override)              |
| `/resolutions/<uuid:id>/send-employer/`    | `ResolutionSendEmployerView` | POST     | Beschluss-PDF per E-Mail an Arbeitgeber senden                                             |
| `/resolutions/elections/`                  | `ElectionListView`           | GET      | Wahlen auflisten                                                                           |
| `/resolutions/elections/create/`           | `ElectionCreateView`         | GET/POST | Wahl erstellen (nur Präsenzsitzungen); Kandidaten als Freitext (`candidate_name`) erfassen |
| `/resolutions/elections/<uuid:id>/`        | `ElectionDetailView`         | GET      | Wahldetails inkl. Kandidatenliste anzeigen                                                 |
| `/resolutions/elections/<uuid:id>/result/` | `ElectionResultView`         | GET/POST | Wahlergebnis erfassen (Stimmen pro Kandidat/in)                                            |

**HTMX-Fragmente:**

| URL                                         | Trigger                           | Beschreibung                                          |
|---------------------------------------------|-----------------------------------|-------------------------------------------------------|
| `/resolutions/<uuid:id>/vote/live/`         | `hx-post`                         | Live-Abstimmung (Ergebnis sofort aktualisiert)        |
| `/resolutions/<uuid:id>/vote/quorum-check/` | `hx-get` (Änderung Anwesend-Feld) | Beschlussfähigkeit und Ergebnis automatisch berechnen |

### 5.3.11 Kalender (`/calendar/`)

| URL                                    | View                | Methode  | Beschreibung                          |
|----------------------------------------|---------------------|----------|---------------------------------------|
| `/calendar/`                           | `CalendarView`      | GET      | Kalenderansicht (FullCalendar-Widget) |
| `/calendar/events/create/`             | `EventCreateView`   | GET/POST | Termin erstellen                      |
| `/calendar/events/<uuid:id>/edit/`     | `EventEditView`     | GET/POST | Termin bearbeiten                     |
| `/calendar/events/<uuid:id>/delete/`   | `EventDeleteView`   | POST     | Termin löschen                        |
| `/calendar/export/ical/`               | `ICalExportView`    | GET      | iCal-Export                           |
| `/calendar/absences/`                  | `AbsenceListView`   | GET      | Abwesenheiten auflisten               |
| `/calendar/absences/create/`           | `AbsenceCreateView` | GET/POST | Abwesenheit eintragen                 |
| `/calendar/absences/<uuid:id>/edit/`   | `AbsenceEditView`   | GET/POST | Abwesenheit bearbeiten                |
| `/calendar/absences/<uuid:id>/delete/` | `AbsenceDeleteView` | POST     | Abwesenheit löschen                   |

**HTMX-Fragmente:**

| URL                                  | Trigger                    | Beschreibung                                      |
|--------------------------------------|----------------------------|---------------------------------------------------|
| `/calendar/events/json/`             | FullCalendar AJAX          | Kalendereinträge als JSON für FullCalendar-Widget |
| `/calendar/events/<uuid:id>/detail/` | `hx-get` (Klick auf Event) | Event-Details als Popover laden                   |

### 5.3.12 Benachrichtigungen (`/notifications/`)

| URL                              | View                          | Methode  | Beschreibung                       |
|----------------------------------|-------------------------------|----------|------------------------------------|
| `/notifications/`                | `NotificationListView`        | GET      | Eigene Benachrichtigungen anzeigen |
| `/notifications/<uuid:id>/read/` | `NotificationMarkReadView`    | POST     | Als gelesen markieren              |
| `/notifications/read-all/`       | `NotificationMarkAllReadView` | POST     | Alle als gelesen markieren         |
| `/notifications/preferences/`    | `NotificationPreferencesView` | GET/POST | Benachrichtigungs-Einstellungen    |

**HTMX-Fragmente:**

| URL                        | Trigger                  | Beschreibung                           |
|----------------------------|--------------------------|----------------------------------------|
| `/notifications/badge/`    | `hx-get` (Polling/Timer) | Ungelesene Anzahl für Navbar-Badge     |
| `/notifications/dropdown/` | `hx-get` (Klick)         | Letzte Benachrichtigungen als Dropdown |

### 5.3.13 Rollen & Berechtigungen (`/roles/`)

| URL                             | View                         | Methode  | Beschreibung                            |
|---------------------------------|------------------------------|----------|-----------------------------------------|
| `/roles/`                       | `RoleListView`               | GET      | Alle Rollen auflisten                   |
| `/roles/create/`                | `RoleCreateView`             | GET/POST | Neue Rolle erstellen                    |
| `/roles/<uuid:id>/`             | `RoleDetailView`             | GET      | Rollendetails inkl. Berechtigungen      |
| `/roles/<uuid:id>/edit/`        | `RoleEditView`               | GET/POST | Rolle bearbeiten                        |
| `/roles/<uuid:id>/delete/`      | `RoleDeleteView`             | POST     | Rolle löschen (nur benutzerdefinierte)  |
| `/roles/<uuid:id>/duplicate/`   | `RoleDuplicateView`          | POST     | Rolle duplizieren                       |
| `/roles/<uuid:id>/permissions/` | `RolePermissionsView`        | GET/POST | Berechtigungen einer Rolle verwalten    |
| `/roles/<uuid:id>/members/`     | `RoleMembersView`            | GET      | Mitglieder mit dieser Rolle             |
| `/roles/permissions/`           | `PermissionListView`         | GET      | Alle verfügbaren Berechtigungen         |
| `/roles/matrix/`                | `PermissionMatrixView`       | GET      | Berechtigungsmatrix (Übersicht)         |
| `/roles/matrix/export/`         | `PermissionMatrixExportView` | GET      | Berechtigungsmatrix als CSV exportieren |

**HTMX-Fragmente:**

| URL                                      | Trigger              | Beschreibung                                               |
|------------------------------------------|----------------------|------------------------------------------------------------|
| `/roles/<uuid:id>/permissions/toggle/`   | `hx-post` (Checkbox) | Einzelne Berechtigung per Checkbox aktivieren/deaktivieren |
| `/roles/<uuid:id>/permissions/category/` | `hx-get`             | Berechtigungen einer Kategorie laden                       |

### 5.3.14 To-Do-Verwaltung (`/todos/`)

| URL                        | View                   | Methode  | Beschreibung                                  |
|----------------------------|------------------------|----------|-----------------------------------------------|
| `/todos/`                  | `TodoListView`         | GET      | Aufgaben auflisten (persönlich/gremiumsweit)  |
| `/todos/create/`           | `TodoCreateView`       | GET/POST | Neue Aufgabe erstellen                        |
| `/todos/<uuid:id>/`        | `TodoDetailView`       | GET      | Aufgabendetails anzeigen                      |
| `/todos/<uuid:id>/edit/`   | `TodoEditView`         | GET/POST | Aufgabe bearbeiten                            |
| `/todos/<uuid:id>/delete/` | `TodoDeleteView`       | POST     | Aufgabe löschen                               |
| `/todos/<uuid:id>/status/` | `TodoStatusUpdateView` | POST     | Status ändern (Offen/In Bearbeitung/Erledigt) |
| `/todos/<uuid:id>/assign/` | `TodoAssignView`       | POST     | Mitglieder zuweisen                           |

**HTMX-Fragmente:**

| URL                               | Trigger                   | Beschreibung             |
|-----------------------------------|---------------------------|--------------------------|
| `/todos/<uuid:id>/status-toggle/` | `hx-post` (Checkbox)      | Status inline ändern     |
| `/todos/filter/`                  | `hx-get` (Filteränderung) | To-Do-Liste live filtern |

### 5.3.15 Personelle Einzelmaßnahmen (`/personnel/`)

| URL                                      | View                          | Methode     | Beschreibung                                                             |
|------------------------------------------|-------------------------------|-------------|--------------------------------------------------------------------------|
| `/personnel/`                            | `PersonnelMeasureListView`    | GET         | Maßnahmen auflisten (mit Fristanzeige)                                   |
| `/personnel/create/`                     | `PersonnelMeasureCreateView`  | GET/POST    | Neue Maßnahme erfassen                                                   |
| `/personnel/<uuid:id>/`                  | `PersonnelMeasureDetailView`  | GET         | Maßnahmendetails anzeigen                                                |
| `/personnel/<uuid:id>/edit/`             | `PersonnelMeasureEditView`    | GET/POST    | Maßnahme bearbeiten                                                      |
| `/personnel/<uuid:id>/delete/`           | `PersonnelMeasureDeleteView`  | POST        | Maßnahme löschen                                                         |
| `/personnel/<uuid:id>/statement/`        | `PersonnelStatementView`      | GET/POST    | Stellungnahme erstellen                                                  |
| `/personnel/<uuid:id>/link-resolution/`  | `PersonnelLinkResolutionView` | POST        | Beschluss verknüpfen                                                     |
| `/personnel/<uuid:id>/link-agenda-item/` | `PersonnelLinkAgendaItemView` | POST        | Maßnahme als TOP auf Tagesordnung setzen                                 |
| `/personnel/<uuid:id>/send-result/`      | `PersonnelSendResultView`     | POST        | Ergebnis per E-Mail an Arbeitgeber senden                                |
| `/personnel/api/create/`                 | `PersonnelExternalCreateAPI`  | POST (JSON) | Externe API-Schnittstelle zur Erstellung (z. B. durch Personalabteilung) |

**HTMX-Fragmente:**

| URL                             | Trigger                   | Beschreibung                 |
|---------------------------------|---------------------------|------------------------------|
| `/personnel/deadline-warnings/` | `hx-get` (Polling)        | Fristwarnungen aktualisieren |
| `/personnel/filter/`            | `hx-get` (Filteränderung) | Maßnahmenliste live filtern  |

### 5.3.16 Audit (`/audit/)

| URL                  | View                 | Methode | Beschreibung                     |
|----------------------|----------------------|---------|----------------------------------|
| `/audit/`            | `AuditLogListView`   | GET     | Audit-Logs anzeigen (mit Filter) |
| `/audit/export/csv/` | `AuditLogExportView` | GET     | Audit-Logs als CSV exportieren   |

**HTMX-Fragmente:**

| URL              | Trigger                   | Beschreibung            |
|------------------|---------------------------|-------------------------|
| `/audit/filter/` | `hx-get` (Filteränderung) | Audit-Logs live filtern |

---

## 5.4 View-Architektur

### Class-Based Views (CBVs)

Die meisten Views basieren auf Djangos Class-Based Views für konsistente Patterns:

```python
# Beispiel: apps/agendas/views.py
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView


class MeetingListView(LoginRequiredMixin, ListView):
    model = Meeting
    template_name = 'agendas/meeting_list.html'
    context_object_name = 'meetings'
    paginate_by = 20

    def get_queryset(self):
        return Meeting.objects.filter(
            committee__memberships__user=self.request.user
        ).select_related('committee').order_by('-date')


class MeetingDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = Meeting
    template_name = 'agendas/meeting_detail.html'
    permission_required = 'agenda.view'
    slug_field = 'id'
    slug_url_kwarg = 'id'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['agenda_items'] = self.object.agenda_items.order_by('order')
        return context
```

### HTMX-Pattern in Views

```python
# Detection of HTMX requests
def agenda_item_create(request, meeting_id):
    meeting = get_object_or_404(Meeting, id=meeting_id)
    form = AgendaItemForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        item = form.save(commit=False)
        item.meeting = meeting
        item.save()

        # HTMX request: return fragment only
        if request.headers.get('HX-Request'):
            return render(request, 'agendas/_item_row.html', {'item': item})
        # Normal request: redirect
        return redirect('agendas:detail', pk=meeting_id)

    return render(request, 'agendas/item_form.html', {
        'form': form, 'meeting': meeting
    })
```

### Berechtigungsprüfung

```python
# Custom permission mixin for dynamic RBAC
from apps.roles.mixins import DynamicPermissionMixin


class MeetingEditView(LoginRequiredMixin, DynamicPermissionMixin, UpdateView):
    model = Meeting
    form_class = MeetingForm
    template_name = 'meetings/meeting_form.html'
    required_permission = 'meeting.edit'

    def get_committee(self):
        return self.get_object().committee

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # Dynamically show/hide address fields based on meeting type:
        # ONLINE → location_url only; HYBRID → location_url + address; IN_PERSON → address only
        meeting_type = self.object.meeting_type if self.object else 'IN_PERSON'
        if meeting_type == 'ONLINE':
            for field in ['location_name', 'location_street', 'location_zip', 'location_city', 'location_room']:
                form.fields[field].widget = forms.HiddenInput()
        elif meeting_type == 'IN_PERSON':
            form.fields['location_url'].widget = forms.HiddenInput()
        return form
```

## 5.5 Spezielle Endpunkte

### JSON-Endpunkte (für JavaScript-Widgets)

Einige wenige Endpunkte liefern JSON statt HTML, da sie von JavaScript-Bibliotheken (z. B. FullCalendar) konsumiert
werden:

| URL                                   | Beschreibung                           | Format             |
|---------------------------------------|----------------------------------------|--------------------|
| `/calendar/events/json/`              | Kalendereinträge für FullCalendar      | JSON               |
| `/meetings/<uuid:id>/agenda/reorder/` | Reihenfolge nach Drag & Drop speichern | JSON (Bestätigung) |

Diese Endpunkte nutzen Djangos `JsonResponse` direkt, ohne Django REST Framework.

### Datei-Downloads

| URL                                     | Beschreibung                            |
|-----------------------------------------|-----------------------------------------|
| `/documents/<uuid:id>/download/`        | Dokument herunterladen (FileResponse)   |
| `/minutes/<uuid:id>/export/pdf/`        | Protokoll als PDF (WeasyPrint)          |
| `/resolutions/<uuid:id>/send-employer/` | Beschluss-PDF per E-Mail an Arbeitgeber |
| `/calendar/export/ical/`                | Kalender als iCal-Datei                 |
| `/audit/export/csv/`                    | Audit-Logs als CSV                      |
| `/roles/matrix/export/`                 | Berechtigungsmatrix als CSV             |

## 5.6 Rate Limiting

Rate Limiting wird über Nginx (Reverse Proxy) umgesetzt:

| URL-Gruppe                          | Limit                 |
|-------------------------------------|-----------------------|
| Login (`/accounts/login/`)          | 5 Anfragen / Minute   |
| Allgemein                           | 100 Anfragen / Minute |
| Datei-Upload (`/documents/upload/`) | 10 Anfragen / Minute  |
| Export (PDF, iCal, CSV)             | 20 Anfragen / Minute  |

## 5.7 Fehlerbehandlung

Django-eigene Fehlerseiten mit benutzerdefinierten Templates:

| HTTP-Code | Template   | Beschreibung         |
|-----------|------------|----------------------|
| 400       | `400.html` | Ungültige Anfrage    |
| 403       | `403.html` | Keine Berechtigung   |
| 404       | `404.html` | Seite nicht gefunden |
| 500       | `500.html` | Serverfehler         |

Für HTMX-Requests werden entsprechende Fehlerfragmente zurückgegeben, die inline im aktuellen Kontext angezeigt werden.
