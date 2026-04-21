# 05 – URL- und View-Konzept

## 5.1 Übersicht

Da der BR Manager als Django-Monolith aufgebaut ist, wird die gesamte Anwendungslogik über **Django Views** und **Django Templates** bereitgestellt. Die Navigation erfolgt über ein klassisches URL-Routing. Für dynamische Interaktionen (HTMX-Requests) liefern Views **HTML-Fragmente** statt vollständiger Seiten zurück.

### Architektur-Prinzip

```
Browser-Request (GET /meetings/123/)
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

- **URL-Schema:** Lesbare, hierarchische URLs (z. B. `/meetings/123/agenda/`)
- **Authentifizierung:** Django Sessions (Cookie-basiert, CSRF-geschützt)
- **Berechtigungsprüfung:** Decorator-basiert (`@login_required`, `@permission_required`) oder Mixins
- **HTMX-Erkennung:** `request.headers.get('HX-Request')` – liefert Fragment statt volle Seite
- **Formulare:** Django Forms mit serverseitiger Validierung
- **Namespacing:** Jede App hat einen eigenen URL-Namespace (z. B. `agendas:detail`)

## 5.2 URL-Konfiguration

### Root-URL-Konfiguration (`config/urls.py`)

```python
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('apps.accounts.urls', namespace='accounts')),
    path('committees/', include('apps.committees.urls', namespace='committees')),
    path('meetings/', include('apps.agendas.urls', namespace='agendas')),
    path('minutes/', include('apps.minutes.urls', namespace='minutes')),
    path('attendance/', include('apps.attendance.urls', namespace='attendance')),
    path('documents/', include('apps.documents.urls', namespace='documents')),
    path('resolutions/', include('apps.resolutions.urls', namespace='resolutions')),
    path('calendar/', include('apps.calendar_mgmt.urls', namespace='calendar')),
    path('notifications/', include('apps.notifications.urls', namespace='notifications')),
    path('roles/', include('apps.roles.urls', namespace='roles')),
    path('audit/', include('apps.audit.urls', namespace='audit')),
    path('', include('apps.core.urls', namespace='core')),  # Dashboard
]
```

## 5.3 URLs und Views nach Modul

### 5.3.1 Authentifizierung & Benutzerverwaltung (`/accounts/`)

| URL | View | Methode | Beschreibung |
|-----|------|---------|-------------|
| `/accounts/login/` | `LoginView` | GET/POST | Login-Seite (E-Mail + Passwort) |
| `/accounts/logout/` | `LogoutView` | POST | Logout |
| `/accounts/profile/` | `ProfileView` | GET/POST | Eigenes Profil anzeigen/bearbeiten |
| `/accounts/password/change/` | `PasswordChangeView` | GET/POST | Passwort ändern |
| `/accounts/2fa/setup/` | `TwoFactorSetupView` | GET/POST | 2FA einrichten |
| `/accounts/2fa/verify/` | `TwoFactorVerifyView` | GET/POST | 2FA-Code verifizieren |
| `/accounts/oauth/login/` | `OAuthLoginView` | GET | OAuth2-Autorisierung starten |
| `/accounts/oauth/callback/` | `OAuthCallbackView` | GET | OAuth2-Callback verarbeiten |

### 5.3.2 Dashboard (`/`)

| URL | View | Methode | Beschreibung |
|-----|------|---------|-------------|
| `/` | `DashboardView` | GET | Übersichtsseite (nächste Sitzungen, offene Aufgaben, Benachrichtigungen) |

### 5.3.3 Gremien & Mitgliedschaften (`/committees/`)

| URL | View | Methode | Beschreibung |
|-----|------|---------|-------------|
| `/committees/` | `CommitteeListView` | GET | Alle Gremien (des Benutzers) auflisten |
| `/committees/create/` | `CommitteeCreateView` | GET/POST | Neues Gremium erstellen |
| `/committees/<id>/` | `CommitteeDetailView` | GET | Gremiumsdetails anzeigen |
| `/committees/<id>/edit/` | `CommitteeEditView` | GET/POST | Gremium bearbeiten |
| `/committees/<id>/members/` | `MemberListView` | GET | Mitglieder auflisten |
| `/committees/<id>/members/add/` | `MemberAddView` | GET/POST | Mitglied hinzufügen (mit Rollenzuweisung) |
| `/committees/<id>/members/<mid>/edit/` | `MemberEditView` | GET/POST | Mitgliedschaft bearbeiten (inkl. Rolle) |
| `/committees/<id>/members/<mid>/remove/` | `MemberRemoveView` | POST | Mitglied entfernen |
| `/committees/<id>/substitutes/` | `SubstituteListView` | GET | Ersatzmitglieder mit Rang anzeigen |

**HTMX-Fragmente:**

| URL | Trigger | Beschreibung |
|-----|---------|-------------|
| `/committees/<id>/members/search/` | `hx-get` (Suchfeld) | Live-Suche in Mitgliederliste |
| `/committees/<id>/members/<mid>/inline-edit/` | `hx-get` / `hx-post` | Inline-Bearbeitung einer Mitgliedschaft |

### 5.3.4 Sitzungen & Tagesordnungen (`/meetings/`)

| URL | View | Methode | Beschreibung |
|-----|------|---------|-------------|
| `/meetings/` | `MeetingListView` | GET | Sitzungen auflisten |
| `/meetings/create/` | `MeetingCreateView` | GET/POST | Neue Sitzung erstellen |
| `/meetings/from-template/` | `MeetingFromTemplateView` | GET/POST | Sitzung aus Vorlage erstellen |
| `/meetings/<id>/` | `MeetingDetailView` | GET | Sitzungsdetails mit Tagesordnung |
| `/meetings/<id>/edit/` | `MeetingEditView` | GET/POST | Sitzung bearbeiten |
| `/meetings/<id>/delete/` | `MeetingDeleteView` | POST | Sitzung löschen (nur Entwurf) |
| `/meetings/<id>/send/` | `MeetingSendView` | POST | Tagesordnung per E-Mail versenden |
| `/meetings/<id>/complete/` | `MeetingCompleteView` | POST | Sitzung abschließen |
| `/meetings/<id>/agenda/add/` | `AgendaItemCreateView` | GET/POST | Tagesordnungspunkt (TOP) hinzufügen |
| `/meetings/<id>/agenda/<aid>/edit/` | `AgendaItemEditView` | GET/POST | TOP bearbeiten |
| `/meetings/<id>/agenda/<aid>/delete/` | `AgendaItemDeleteView` | POST | TOP löschen |

**HTMX-Fragmente:**

| URL | Trigger | Beschreibung |
|-----|---------|-------------|
| `/meetings/<id>/agenda/reorder/` | `hx-post` (Drag & Drop) | TOPs per Drag & Drop umsortieren |
| `/meetings/<id>/agenda/<aid>/inline-edit/` | `hx-get` / `hx-post` | TOP inline bearbeiten |

### 5.3.5 Tagesordnungsvorlagen (`/meetings/templates/`)

| URL | View | Methode | Beschreibung |
|-----|------|---------|-------------|
| `/meetings/templates/` | `TemplateListView` | GET | Vorlagen auflisten |
| `/meetings/templates/create/` | `TemplateCreateView` | GET/POST | Neue Vorlage erstellen |
| `/meetings/templates/<id>/` | `TemplateDetailView` | GET | Vorlagendetails |
| `/meetings/templates/<id>/edit/` | `TemplateEditView` | GET/POST | Vorlage bearbeiten |
| `/meetings/templates/<id>/delete/` | `TemplateDeleteView` | POST | Vorlage löschen |

### 5.3.6 Protokolle (`/minutes/`)

| URL | View | Methode | Beschreibung |
|-----|------|---------|-------------|
| `/meetings/<id>/minutes/` | `MinutesDetailView` | GET | Protokoll einer Sitzung anzeigen |
| `/meetings/<id>/minutes/create/` | `MinutesCreateView` | GET/POST | Protokoll erstellen (WYSIWYG-Editor) |
| `/minutes/<id>/edit/` | `MinutesEditView` | GET/POST | Protokoll bearbeiten |
| `/minutes/<id>/submit/` | `MinutesSubmitView` | POST | Zur Prüfung einreichen |
| `/minutes/<id>/approve/chair/` | `MinutesApproveChairView` | POST | Genehmigung durch Vorsitz |
| `/minutes/<id>/approve/clerk/` | `MinutesApproveClerkView` | POST | Genehmigung durch Protokollführung |
| `/minutes/<id>/reject/` | `MinutesRejectView` | POST | Zurückweisen (mit Kommentar) |
| `/minutes/<id>/finalize/` | `MinutesFinalizeView` | POST | Finalisieren (nach Sitzungsbeschluss) |
| `/minutes/<id>/versions/` | `MinutesVersionListView` | GET | Versionshistorie |
| `/minutes/<id>/versions/<version>/` | `MinutesVersionDetailView` | GET | Bestimmte Version anzeigen |
| `/minutes/<id>/diff/<v1>/<v2>/` | `MinutesDiffView` | GET | Diff zwischen Versionen |
| `/minutes/<id>/export/pdf/` | `MinutesPDFExportView` | GET | PDF-Export/Download |

**HTMX-Fragmente:**

| URL | Trigger | Beschreibung |
|-----|---------|-------------|
| `/minutes/<id>/autosave/` | `hx-post` (Timer) | Auto-Save während der Bearbeitung |
| `/minutes/<id>/preview/` | `hx-get` | Live-Vorschau des Protokolls |

### 5.3.7 Anwesenheit (`/attendance/`)

| URL | View | Methode | Beschreibung |
|-----|------|---------|-------------|
| `/meetings/<id>/attendance/` | `AttendanceListView` | GET | Anwesenheitsliste anzeigen |
| `/meetings/<id>/attendance/confirm/` | `AttendanceConfirmView` | GET/POST | Anwesenheit bestätigen (mit 2FA) |
| `/attendance/<id>/edit/` | `AttendanceEditView` | GET/POST | Anwesenheit bearbeiten |
| `/meetings/<id>/substitute-suggestions/` | `SubstituteSuggestionsView` | GET | Ersatzmitglieder-Vorschläge |
| `/meetings/<id>/assign-substitute/` | `AssignSubstituteView` | POST | Ersatzmitglied zuweisen |
| `/meetings/<id>/quorum/` | `QuorumCheckView` | GET | Beschlussfähigkeit prüfen |

**HTMX-Fragmente:**

| URL | Trigger | Beschreibung |
|-----|---------|-------------|
| `/meetings/<id>/attendance/status/` | `hx-get` (Polling) | Live-Anwesenheitsstatus aktualisieren |
| `/meetings/<id>/quorum/check/` | `hx-get` | Beschlussfähigkeit live prüfen |

### 5.3.8 Dokumente (`/documents/`)

| URL | View | Methode | Beschreibung |
|-----|------|---------|-------------|
| `/documents/` | `DocumentListView` | GET | Dokumente auflisten (mit Filter/Suche) |
| `/documents/upload/` | `DocumentUploadView` | GET/POST | Dokument hochladen |
| `/documents/<id>/` | `DocumentDetailView` | GET | Dokumentendetails anzeigen |
| `/documents/<id>/edit/` | `DocumentEditView` | GET/POST | Dokumentenmetadaten bearbeiten |
| `/documents/<id>/delete/` | `DocumentDeleteView` | POST | Dokument löschen |
| `/documents/<id>/download/` | `DocumentDownloadView` | GET | Dokument herunterladen |
| `/documents/<id>/preview/` | `DocumentPreviewView` | GET | Dokumentenvorschau |
| `/documents/<id>/versions/` | `DocumentVersionListView` | GET | Versionshistorie |
| `/documents/<id>/versions/upload/` | `DocumentVersionUploadView` | POST | Neue Version hochladen |
| `/documents/<id>/share/` | `DocumentShareView` | GET/POST | Gastzugriff gewähren |
| `/documents/<id>/share/<access_id>/revoke/` | `DocumentShareRevokeView` | POST | Gastzugriff widerrufen |
| `/documents/folders/` | `FolderListView` | GET | Ordner auflisten |
| `/documents/folders/create/` | `FolderCreateView` | GET/POST | Ordner erstellen |
| `/documents/folders/<id>/edit/` | `FolderEditView` | GET/POST | Ordner bearbeiten |
| `/documents/folders/<id>/delete/` | `FolderDeleteView` | POST | Ordner löschen |

**HTMX-Fragmente:**

| URL | Trigger | Beschreibung |
|-----|---------|-------------|
| `/documents/search/` | `hx-get` (Suchfeld) | Live-Suche in Dokumenten |
| `/documents/<id>/upload-progress/` | `hx-get` (Polling) | Upload-Fortschritt anzeigen |

### 5.3.9 Beschlüsse & Wahlen (`/resolutions/`)

| URL | View | Methode | Beschreibung |
|-----|------|---------|-------------|
| `/resolutions/` | `ResolutionListView` | GET | Beschlüsse auflisten |
| `/resolutions/create/` | `ResolutionCreateView` | GET/POST | Beschluss erstellen |
| `/resolutions/<id>/` | `ResolutionDetailView` | GET | Beschlussdetails anzeigen |
| `/resolutions/<id>/edit/` | `ResolutionEditView` | GET/POST | Beschluss bearbeiten |
| `/resolutions/<id>/vote/` | `ResolutionVoteView` | GET/POST | Abstimmungsergebnis erfassen (inkl. Beschlussfähigkeit und Ergebnis-Override) |
| `/resolutions/elections/` | `ElectionListView` | GET | Wahlen auflisten |
| `/resolutions/elections/create/` | `ElectionCreateView` | GET/POST | Wahl erstellen |
| `/resolutions/elections/<id>/` | `ElectionDetailView` | GET | Wahldetails anzeigen |
| `/resolutions/elections/<id>/result/` | `ElectionResultView` | GET/POST | Wahlergebnis erfassen |

**HTMX-Fragmente:**

| URL | Trigger | Beschreibung |
|-----|---------|-------------|
| `/resolutions/<id>/vote/live/` | `hx-post` | Live-Abstimmung (Ergebnis sofort aktualisiert) |
| `/resolutions/<id>/vote/quorum-check/` | `hx-get` (Änderung Anwesend-Feld) | Beschlussfähigkeit und Ergebnis automatisch berechnen |

### 5.3.10 Kalender (`/calendar/`)

| URL | View | Methode | Beschreibung |
|-----|------|---------|-------------|
| `/calendar/` | `CalendarView` | GET | Kalenderansicht (FullCalendar-Widget) |
| `/calendar/events/create/` | `EventCreateView` | GET/POST | Termin erstellen |
| `/calendar/events/<id>/edit/` | `EventEditView` | GET/POST | Termin bearbeiten |
| `/calendar/events/<id>/delete/` | `EventDeleteView` | POST | Termin löschen |
| `/calendar/export/ical/` | `ICalExportView` | GET | iCal-Export |
| `/calendar/absences/` | `AbsenceListView` | GET | Abwesenheiten auflisten |
| `/calendar/absences/create/` | `AbsenceCreateView` | GET/POST | Abwesenheit eintragen |
| `/calendar/absences/<id>/edit/` | `AbsenceEditView` | GET/POST | Abwesenheit bearbeiten |
| `/calendar/absences/<id>/delete/` | `AbsenceDeleteView` | POST | Abwesenheit löschen |

**HTMX-Fragmente:**

| URL | Trigger | Beschreibung |
|-----|---------|-------------|
| `/calendar/events/json/` | FullCalendar AJAX | Kalendereinträge als JSON für FullCalendar-Widget |
| `/calendar/events/<id>/detail/` | `hx-get` (Klick auf Event) | Event-Details als Popover laden |

### 5.3.11 Benachrichtigungen (`/notifications/`)

| URL | View | Methode | Beschreibung |
|-----|------|---------|-------------|
| `/notifications/` | `NotificationListView` | GET | Eigene Benachrichtigungen anzeigen |
| `/notifications/<id>/read/` | `NotificationMarkReadView` | POST | Als gelesen markieren |
| `/notifications/read-all/` | `NotificationMarkAllReadView` | POST | Alle als gelesen markieren |
| `/notifications/preferences/` | `NotificationPreferencesView` | GET/POST | Benachrichtigungs-Einstellungen |

**HTMX-Fragmente:**

| URL | Trigger | Beschreibung |
|-----|---------|-------------|
| `/notifications/badge/` | `hx-get` (Polling/Timer) | Ungelesene Anzahl für Navbar-Badge |
| `/notifications/dropdown/` | `hx-get` (Klick) | Letzte Benachrichtigungen als Dropdown |

### 5.3.12 Rollen & Berechtigungen (`/roles/`)

| URL | View | Methode | Beschreibung |
|-----|------|---------|-------------|
| `/roles/` | `RoleListView` | GET | Alle Rollen auflisten |
| `/roles/create/` | `RoleCreateView` | GET/POST | Neue Rolle erstellen |
| `/roles/<id>/` | `RoleDetailView` | GET | Rollendetails inkl. Berechtigungen |
| `/roles/<id>/edit/` | `RoleEditView` | GET/POST | Rolle bearbeiten |
| `/roles/<id>/delete/` | `RoleDeleteView` | POST | Rolle löschen (nur benutzerdefinierte) |
| `/roles/<id>/duplicate/` | `RoleDuplicateView` | POST | Rolle duplizieren |
| `/roles/<id>/permissions/` | `RolePermissionsView` | GET/POST | Berechtigungen einer Rolle verwalten |
| `/roles/<id>/members/` | `RoleMembersView` | GET | Mitglieder mit dieser Rolle |
| `/roles/permissions/` | `PermissionListView` | GET | Alle verfügbaren Berechtigungen |
| `/roles/matrix/` | `PermissionMatrixView` | GET | Berechtigungsmatrix (Übersicht) |
| `/roles/matrix/export/` | `PermissionMatrixExportView` | GET | Berechtigungsmatrix als CSV exportieren |

**HTMX-Fragmente:**

| URL | Trigger | Beschreibung |
|-----|---------|-------------|
| `/roles/<id>/permissions/toggle/` | `hx-post` (Checkbox) | Einzelne Berechtigung per Checkbox aktivieren/deaktivieren |
| `/roles/<id>/permissions/category/` | `hx-get` | Berechtigungen einer Kategorie laden |

### 5.3.13 Audit (`/audit/`)

| URL | View | Methode | Beschreibung |
|-----|------|---------|-------------|
| `/audit/` | `AuditLogListView` | GET | Audit-Logs anzeigen (mit Filter) |
| `/audit/export/csv/` | `AuditLogExportView` | GET | Audit-Logs als CSV exportieren |

**HTMX-Fragmente:**

| URL | Trigger | Beschreibung |
|-----|---------|-------------|
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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['agenda_items'] = self.object.agenda_items.order_by('order')
        return context
```

### HTMX-Pattern in Views

```python
# Erkennung von HTMX-Requests
def agenda_item_create(request, meeting_id):
    meeting = get_object_or_404(Meeting, id=meeting_id)
    form = AgendaItemForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        item = form.save(commit=False)
        item.meeting = meeting
        item.save()

        # HTMX-Request: nur Fragment zurückgeben
        if request.headers.get('HX-Request'):
            return render(request, 'agendas/_item_row.html', {'item': item})
        # Normaler Request: Redirect
        return redirect('agendas:detail', pk=meeting_id)

    return render(request, 'agendas/item_form.html', {
        'form': form, 'meeting': meeting
    })
```

### Berechtigungsprüfung

```python
# Custom Permission Mixin für dynamisches RBAC
from apps.roles.mixins import DynamicPermissionMixin

class MeetingEditView(LoginRequiredMixin, DynamicPermissionMixin, UpdateView):
    model = Meeting
    form_class = MeetingForm
    template_name = 'agendas/meeting_form.html'
    required_permission = 'agenda.edit'

    def get_committee(self):
        return self.get_object().committee
```

## 5.5 Spezielle Endpunkte

### JSON-Endpunkte (für JavaScript-Widgets)

Einige wenige Endpunkte liefern JSON statt HTML, da sie von JavaScript-Bibliotheken (z. B. FullCalendar) konsumiert werden:

| URL | Beschreibung | Format |
|-----|-------------|--------|
| `/calendar/events/json/` | Kalendereinträge für FullCalendar | JSON |
| `/meetings/<id>/agenda/reorder/` | Reihenfolge nach Drag & Drop speichern | JSON (Bestätigung) |

Diese Endpunkte nutzen Djangos `JsonResponse` direkt, ohne Django REST Framework.

### Datei-Downloads

| URL | Beschreibung |
|-----|-------------|
| `/documents/<id>/download/` | Dokument herunterladen (FileResponse) |
| `/minutes/<id>/export/pdf/` | Protokoll als PDF (WeasyPrint) |
| `/calendar/export/ical/` | Kalender als iCal-Datei |
| `/audit/export/csv/` | Audit-Logs als CSV |
| `/roles/matrix/export/` | Berechtigungsmatrix als CSV |

## 5.6 Rate Limiting

Rate Limiting wird über Nginx (Reverse Proxy) umgesetzt:

| URL-Gruppe | Limit |
|------------|-------|
| Login (`/accounts/login/`) | 5 Anfragen / Minute |
| Allgemein | 100 Anfragen / Minute |
| Datei-Upload (`/documents/upload/`) | 10 Anfragen / Minute |
| Export (PDF, iCal, CSV) | 20 Anfragen / Minute |

## 5.7 Fehlerbehandlung

Django-eigene Fehlerseiten mit benutzerdefinierten Templates:

| HTTP-Code | Template | Beschreibung |
|-----------|----------|-------------|
| 400 | `400.html` | Ungültige Anfrage |
| 403 | `403.html` | Keine Berechtigung |
| 404 | `404.html` | Seite nicht gefunden |
| 500 | `500.html` | Serverfehler |

Für HTMX-Requests werden entsprechende Fehlerfragmente zurückgegeben, die inline im aktuellen Kontext angezeigt werden.
