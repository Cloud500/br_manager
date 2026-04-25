# App: `roles` - Dynamische Rollen- & Berechtigungsverwaltung

## Übersicht

Die `roles`-App implementiert ein vollständig konfigurierbares rollenbasiertes Zugriffskontrollsystem (RBAC). Administratoren und Vorsitzende können eigene Rollen erstellen, Berechtigungen zuweisen und Rollen anpassen.

## Hauptfunktionen

### 1. Berechtigungsverwaltung
- Vordefinierte granulare Berechtigungen (Permissions) pro Modul
- Berechtigungen nach Kategorien gruppiert (meetings, agendas, minutes, etc.)
- Berechtigungen sind unveränderlich, nur zuweisbar

### 2. Rollenverwaltung
- **Standard-Rollen:**
  - Systemrollen: SYSTEM_ADMIN, USER
  - Gremiumsrollen: CHAIR, VICE_CHAIR, MEMBER, CLERK, SUBSTITUTE, EXTERNAL_MEMBER, GUEST
- **Benutzerdefinierte Rollen:**
  - Frei erstellbar mit eigenem Namen und Beschreibung
  - Berechtigungen beliebig zusammenstellbar
  - Als Vorlage: Bestehende Rollen duplizierbar
  - Löschbar (wenn nicht zugewiesen)

### 3. Berechtigungs-Editor
- Visuelle Oberfläche zum Zuweisen/Entziehen von Berechtigungen
- Gruppierung nach Modulen/Kategorien
- Checkboxen für einzelne Berechtigungen
- "Alle auswählen" / "Alle abwählen" pro Kategorie
- Suchfunktion
- Vorschau der Zugriffsmatrix

### 4. Berechtigungsmatrix
- Übersichtliche Matrix: Rollen (Spalten) × Berechtigungen (Zeilen)
- Export als CSV für Compliance-Berichte

### 5. Sicherheit
- **Privilege Escalation Prevention:** Benutzer können keine Rollen mit mehr Rechten erstellen als ihre eigene Rolle
- **Audit-Trail:** Alle Änderungen an Rollen und Berechtigungen werden protokolliert
- **Vier-Augen-Prinzip:** Optional für kritische Rollenänderungen

## Datenmodell

### Role
- `id` (UUID, PK)
- `name` (CharField(100)) - Rollenname
- `codename` (CharField(50), UNIQUE) - Kurzname (z.B. CHAIR, MEMBER)
- `description` (TextField) - Beschreibung
- `role_type` (CharField(20)) - SYSTEM oder COMMITTEE
- `is_system_role` (BooleanField) - Standard-Rolle (nicht löschbar)
- `created_by` (ForeignKey → User, NULL = System-Seed)
- `created_at` (DateTimeField)
- `updated_at` (DateTimeField)

### Permission
- `id` (UUID, PK)
- `codename` (CharField(100), UNIQUE) - z.B. "meeting.create"
- `name` (CharField(200)) - Anzeigename
- `description` (TextField) - Beschreibung
- `category` (CharField(50)) - Modul (meeting, minutes, document, etc.)

### RolePermission (M:N)
- `id` (UUID, PK)
- `role` (ForeignKey → Role)
- `permission` (ForeignKey → Permission)
- `assigned_by` (ForeignKey → User)
- `assigned_at` (DateTimeField)
- **Constraint:** UNIQUE(role, permission)

## Berechtigungskonzept

### Aufbau von Berechtigungen
Berechtigungen folgen dem Muster: `<app>.<aktion>`

Beispiele:
- `meeting.create` - Sitzung erstellen
- `committee.manage_members` - Mitglieder verwalten
- `role.assign_permissions` - Berechtigungen zuweisen

### Kategorie-Gruppierung
Berechtigungen werden nach App/Modul gruppiert:
- `meeting.*` - Sitzungsverwaltung
- `agenda.*` - Tagesordnungen
- `minutes.*` - Protokolle
- `attendance.*` - Anwesenheit
- `document.*` - Dokumente
- `resolution.*` - Beschlüsse
- `committee.*` - Gremien
- `role.*` - Rollen & Rechte
- `system.*` - System-Administration
- etc.

Die konkreten Berechtigungen jeder App sind in der jeweiligen App-Dokumentation (unter `docs/apps/`) beschrieben.

## URLs und Views

| URL | View | Beschreibung |
|-----|------|--------------|
| `/roles/` | RoleListView | Alle Rollen auflisten |
| `/roles/create/` | RoleCreateView | Neue Rolle erstellen |
| `/roles/<uuid:id>/` | RoleDetailView | Rollendetails inkl. Berechtigungen |
| `/roles/<uuid:id>/edit/` | RoleEditView | Rolle bearbeiten |
| `/roles/<uuid:id>/delete/` | RoleDeleteView | Rolle löschen (nur benutzerdefiniert) |
| `/roles/<uuid:id>/duplicate/` | RoleDuplicateView | Rolle duplizieren |
| `/roles/<uuid:id>/permissions/` | RolePermissionsView | Berechtigungen verwalten |
| `/roles/<uuid:id>/members/` | RoleMembersView | Mitglieder mit dieser Rolle |
| `/roles/permissions/` | PermissionListView | Alle Berechtigungen |
| `/roles/matrix/` | PermissionMatrixView | Berechtigungsmatrix |
| `/roles/matrix/export/` | PermissionMatrixExportView | Matrix als CSV exportieren |

### HTMX-Fragmente

| URL | Trigger | Beschreibung |
|-----|---------|--------------|
| `/roles/<uuid:id>/permissions/toggle/` | Checkbox | Berechtigung aktivieren/deaktivieren |
| `/roles/<uuid:id>/permissions/category/` | hx-get | Berechtigungen einer Kategorie laden |

## Abhängigkeiten

### Erforderliche Apps
- **accounts** (User-Modell)

### Optionale Apps
- **audit** (Audit-Logging für Rollenänderungen)

### Django-Pakete
- `django.contrib.auth` (Basis-Permissions)
- Django Standard (keine zusätzlichen Pakete erforderlich)

### Cache
- Redis (optional) für Berechtigungs-Caching (TTL: 5 Min)

## Berechtigungen dieser App

- `role.create` - Neue Rolle erstellen
- `role.edit` - Rolle bearbeiten
- `role.delete` - Rolle löschen
- `role.assign_permissions` - Berechtigungen zuweisen/entziehen
- `role.view` - Rollen einsehen
- `role.assign_to_member` - Rolle einem Mitglied zuweisen

## Templates

- `roles/role_list.html` - Rollenübersicht
- `roles/role_detail.html` - Rollendetails
- `roles/role_form.html` - Rolle erstellen/bearbeiten
- `roles/permissions_editor.html` - Berechtigungs-Editor
- `roles/permission_matrix.html` - Berechtigungsmatrix
- `roles/_permission_toggle.html` - HTMX-Fragment für Checkbox

## Implementierungshinweise

### 1. Datenmigration für Berechtigungen
Berechtigungen werden pro App in deren Migrationen angelegt. Die `roles`-App definiert nur die Basisstruktur. Beispiel-Struktur:

```python
# Beispiel aus einer anderen App: meetings/migrations/create_permissions.py
def create_meeting_permissions(apps, schema_editor):
    Permission = apps.get_model('roles', 'Permission')
    
    permissions = [
        ('meeting.create', 'Sitzung erstellen', 'meeting'),
        ('meeting.edit', 'Sitzung bearbeiten', 'meeting'),
        ('meeting.view', 'Sitzung einsehen', 'meeting'),
        # ... weitere Meeting-Berechtigungen
    ]
    
    for codename, name, category in permissions:
        Permission.objects.get_or_create(
            codename=codename,
            defaults={'name': name, 'category': category}
        )
```

Die `roles`-App erstellt nur ihre eigenen Berechtigungen (siehe Abschnitt "Berechtigungen dieser App").

### 2. Datenmigration für Standard-Rollen
Standard-Rollen werden mit minimalen Basis-Berechtigungen angelegt. Weitere Berechtigungen können später durch Admins hinzugefügt werden:

```python
# Migration: create_default_roles.py
def create_default_roles(apps, schema_editor):
    Role = apps.get_model('roles', 'Role')
    Permission = apps.get_model('roles', 'Permission')
    RolePermission = apps.get_model('roles', 'RolePermission')
    
    # Systemrollen
    admin_role = Role.objects.create(
        codename='SYSTEM_ADMIN',
        name='System-Admin',
        role_type='SYSTEM',
        is_system_role=True
    )
    
    # SYSTEM_ADMIN erhält zunächst nur system.* Berechtigungen
    # Weitere können per Admin-Interface zugewiesen werden
    admin_perms = Permission.objects.filter(category='system')
    for perm in admin_perms:
        RolePermission.objects.create(role=admin_role, permission=perm)
    
    # USER-Rolle mit minimalen Rechten
    user_role = Role.objects.create(
        codename='USER',
        name='Benutzer',
        role_type='SYSTEM',
        is_system_role=True
    )
    
    # Gremiumsrollen (CHAIR, MEMBER, etc.) werden ohne Berechtigungen erstellt
    # Berechtigungen werden später per Admin-Interface konfiguriert
    committee_roles = [
        ('CHAIR', 'Vorsitz'),
        ('VICE_CHAIR', 'Stellv. Vorsitz'),
        ('MEMBER', 'Mitglied'),
        ('CLERK', 'Schriftführung'),
        ('SUBSTITUTE', 'Ersatzmitglied'),
        ('EXTERNAL_MEMBER', 'Externes Ausschussmitglied'),
        ('GUEST', 'Gast'),
    ]
    
    for codename, name in committee_roles:
        Role.objects.create(
            codename=codename,
            name=name,
            role_type='COMMITTEE',
            is_system_role=True
        )
```

### 3. Berechtigungsprüfung in Views
Eigenes Mixin für dynamische Berechtigungsprüfung:

```python
class DynamicPermissionMixin:
    required_permission = None
    
    def check_permission(self, user):
        # System-Admin hat immer Zugriff
        if user.system_role and user.system_role.codename == 'SYSTEM_ADMIN':
            return True
        
        # Gremiumsrolle prüfen
        committee = self.get_committee()
        membership = Membership.objects.filter(
            user=user, committee=committee, is_active=True
        ).select_related('role').first()
        
        if not membership:
            return False
        
        return RolePermission.objects.filter(
            role=membership.role,
            permission__codename=self.required_permission
        ).exists()
```

### 4. Caching
Rollen-Berechtigungen cachen für Performance:

```python
def get_user_permissions(user, committee):
    cache_key = f"perms:{user.id}:{committee.id}"
    cached = cache.get(cache_key)
    
    if cached:
        return cached
    
    # Berechtigungen aus DB laden
    perms = RolePermission.objects.filter(
        role__memberships__user=user,
        role__memberships__committee=committee
    ).values_list('permission__codename', flat=True)
    
    cache.set(cache_key, list(perms), 300)  # 5 Min TTL
    return perms
```

## Verbindungen zu anderen Apps

### Ausgehende Abhängigkeiten
- **accounts:** User-Modell
- **audit:** Audit-Logging für Rollenänderungen

### Eingehende Abhängigkeiten
- **committees:** Membership-Modell nutzt Role
- **Alle Apps:** Prüfen Berechtigungen über diese App

## Tests

- Unit-Tests für Berechtigungsprüfungen
- Integration-Tests für Rollenzuweisung
- Sicherheitstests für Privilege Escalation Prevention
- Performance-Tests für Berechtigungsprüfung mit Cache
