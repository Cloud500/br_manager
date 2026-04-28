# Implementierungsplan: Accounts & Roles Apps

## Übersicht

Dieser Plan beschreibt die parallele Implementierung der `accounts` und `roles` Apps. Beide Apps haben eine **zirkuläre Abhängigkeit** und müssen daher koordiniert entwickelt werden.

### ⚠️ Code-Konventionen

**Wichtig:** Alle Code-Implementierungen folgen den Richtlinien in `docs/implementation/CODE_STYLE_GUIDE.md`

Kurzübersicht:
- ✅ **Code (Python) = Englisch** (Variablen, Funktionen, Klassen, Kommentare)
- ✅ **User-sichtbare Strings = Deutsch** (verbose_name, Labels, Templates, Messages)

**📖 Vollständige Beispiele:** Siehe `docs/implementation/CODE_STYLE_GUIDE.md`

### Warum parallel?

```
accounts ←→ roles
   ↓         ↓
   committees
```

**Abhängigkeiten:**
- `accounts` definiert **User-Modell** → benötigt von `roles` (ForeignKey)
- `accounts` definiert **Berechtigungen** → benötigt von `roles` (Permission-System)
- `roles` definiert **Systemrollen** → referenziert von `accounts` (SYSTEM_ADMIN, USER)
- `roles` definiert **Gremiumsrollen** → benötigt von `committees` (CHAIR, MEMBER, etc.)

**Fazit:** Eine rein sequenzielle Implementierung ist **nicht möglich**. Die Lösung ist eine **phasenweise parallele Entwicklung**.

---

## Strategie: Parallele Phasen-Implementierung

### Prinzip
Beide Apps werden **gleichzeitig in kleinen, koordinierten Schritten** aufgebaut:
1. Basis-Modelle ohne ForeignKeys
2. ForeignKeys hinzufügen und gemeinsam migrieren
3. Features schrittweise parallel erweitern
4. Integration und Tests

### Vorteile
- ✅ Minimiert Risiko von Inkonsistenzen
- ✅ Migrationen sind aufeinander abgestimmt
- ✅ Frühe Integration-Tests möglich
- ✅ Klare Abhängigkeiten zwischen Phasen

---

## Phase 0: Core-App & Basis-UI

### Ziel
Basis-Dashboard mit Navigation erstellen, damit Login/Logout und Profil erreichbar sind.

### Schritt 0.1: Core-App Dashboard & Navigation

**Dateien zu erstellen:**

1. **`apps/core/views.py`**
   - `DashboardView` (LoginRequiredMixin + TemplateView)
   - Template: `core/dashboard.html`
   - Login-URL: `/accounts/login/`

2. **`apps/core/urls.py`**
   - app_name: `'core'`
   - Route: `''` → DashboardView (name='dashboard')

3. **`config/urls.py`**
   - Include core.urls als Root (`''`)
   - Include accounts.urls unter `'accounts/'`
   - Media files handling für DEBUG-Mode

4. **`templates/base.html`**
   - HTML5 Doctype, lang="de"
   - Bootstrap 5 CSS + Icons
   - Navbar mit User-Dropdown (nur wenn authenticated)
   - Flash Messages Container
   - Content Block
   - Footer
   - Bootstrap JS Bundle
   - Siehe CODE_STYLE_GUIDE.md für Template-Struktur

5. **`apps/core/templates/core/dashboard.html`**
   - Extends base.html
   - Willkommensnachricht mit `{{ user.get_full_name }}`
   - Dashboard-Cards für Sitzungen, Protokolle, Dokumente (Placeholder)
   - Benutzerprofil-Card mit allen User-Feldern
   - Links zu Profil bearbeiten, Passwort ändern

**Templates-Konfiguration:**
- In `config/settings/base.py` sicherstellen: `DIRS: [BASE_DIR / "templates"]`
- APP_DIRS: True

---

## Phase 1: Basis-Modelle & Struktur

### Ziel
Projekt-Grundgerüst erstellen und Basis-Modelle ohne komplexe Abhängigkeiten implementieren.

### Schritt 1.1: Projekt-Setup (beide Apps)

**Apps erstellen:**
```bash
python manage.py startapp accounts apps/accounts
python manage.py startapp roles apps/roles
```

**Verzeichnisstruktur anlegen:**
```bash
# Tests
mkdir -p apps/accounts/tests apps/roles/tests
touch apps/accounts/tests/{__init__.py,test_models.py,test_views.py,test_auth.py}
touch apps/roles/tests/{__init__.py,test_models.py,test_views.py,test_permissions.py}

# Templates & Static
mkdir -p apps/accounts/templates/accounts apps/accounts/static/accounts
mkdir -p apps/roles/templates/roles apps/roles/static/roles

# Management Commands
mkdir -p apps/roles/management/commands
touch apps/roles/management/__init__.py apps/roles/management/commands/__init__.py
```

**Apps registrieren:**
- In `config/settings/base.py` → `LOCAL_APPS` ergänzen:
  - `"apps.core"`
  - `"apps.accounts"`
  - `"apps.roles"`

---

### Schritt 1.2: accounts - User-Modell (Basis)

**Datei:** `apps/accounts/models.py`

**Funktionalität:**
- Custom User Model basierend auf `AbstractBaseUser` + `PermissionsMixin`
- UUID als Primary Key (`uuid.uuid4`)
- E-Mail als `USERNAME_FIELD` (statt Username)
- Pflichtfelder: `email` (unique), `first_name`, `last_name`, `gender`
- Optionale Felder: `phone`
- Status-Felder: `is_active`, `is_staff`, `date_joined`
- 2FA-Felder (vorbereitet für Phase 3): `two_factor_enabled`, `two_factor_method`, `totp_secret`

**GENDER_CHOICES:**
- `('M', 'Männlich')`
- `('F', 'Weiblich')`
- Help-Text: "Pflichtangabe für § 15 Abs. 2 BetrVG (Geschlechterquote)"

**Custom Manager: UserManager**
- Extends `BaseUserManager`
- `create_user(email, password, **extra_fields)`: Email normalisieren, Passwort hashen
- `create_superuser(email, password, **extra_fields)`: is_staff=True, is_superuser=True

**Model-Methoden:**
- `__str__()`: Return "First Last (email)"
- `get_full_name()`: Return "First Last"
- `get_short_name()`: Return first_name

**Meta:**
- verbose_name/verbose_name_plural: 'Benutzer'
- ordering: `['last_name', 'first_name']`

**REQUIRED_FIELDS:** `['first_name', 'last_name', 'gender']`

**Siehe:** CODE_STYLE_GUIDE.md → "Django Best Practices → Models"

---

**Datei:** `apps/accounts/apps.py`

- `default_auto_field = 'django.db.models.BigAutoField'`
- `name = 'apps.accounts'`
- `verbose_name = 'Benutzerverwaltung'`

---

**Datei:** `apps/accounts/admin.py`

**Funktionalität:**
- `UserAdmin` extends `BaseUserAdmin` from `django.contrib.auth.admin`
- `@admin.register(User)` decorator

**list_display:**
- email, first_name, last_name, gender, is_active, date_joined

**list_filter:**
- is_active, is_staff, gender, two_factor_enabled

**search_fields:**
- email, first_name, last_name

**fieldsets (gruppiert):**
1. None: email, password
2. Persönliche Daten: first_name, last_name, gender, phone
3. Berechtigungen: is_active, is_staff, is_superuser
4. 2FA: two_factor_enabled, two_factor_method
5. Wichtige Daten: date_joined, last_login

**add_fieldsets:**
- email, first_name, last_name, gender, password1, password2

---

**Datei:** `apps/accounts/tests/test_models.py`

**Tests zu implementieren:**

1. **test_user_creation_with_email**
   - User mit allen Pflichtfeldern erstellen
   - Assert: email, first_name, last_name, gender korrekt gespeichert
   - Assert: is_active=True per default

2. **test_user_email_unique**
   - Zwei User mit gleicher Email erstellen sollte fehlschlagen
   - Assert: IntegrityError wird geworfen

3. **test_user_get_full_name**
   - get_full_name() sollte "First Last" zurückgeben
   - Assert: Format korrekt

4. **test_user_get_short_name**
   - get_short_name() sollte first_name zurückgeben
   - Assert: Nur Vorname

5. **test_user_str_representation**
   - __str__() sollte "First Last (email)" zurückgeben
   - Assert: Format korrekt

6. **test_create_user_without_email**
   - User ohne Email sollte ValueError werfen
   - Assert: ValueError mit Meldung

7. **test_create_superuser**
   - create_superuser() sollte is_staff=True und is_superuser=True setzen
   - Assert: Beide Flags gesetzt

8. **test_password_is_hashed**
   - Passwort sollte gehasht gespeichert werden
   - Assert: user.password != plain_password
   - Assert: user.check_password() funktioniert

**Siehe:** CODE_STYLE_GUIDE.md → "Django Best Practices → Testing"

---

**Migration:**
```bash
python manage.py makemigrations accounts
# NOCH NICHT ausführen! Wartet auf Schritt 1.4
```

---

### Schritt 1.3: roles - Basis-Modelle (ohne ForeignKeys)

**Datei:** `apps/roles/models.py`

**3 Modelle zu implementieren:**

#### 1. Permission Model

**Zweck:** Granulare Berechtigungen (z.B. 'meeting.create')

**Felder:**
- `id`: UUIDField (PK, default=uuid.uuid4)
- `codename`: CharField(100, unique=True) - z.B. "meeting.create"
- `name`: CharField(200) - Anzeigename
- `description`: TextField(blank=True)
- `category`: CharField(50) - Modul/App (z.B. "meeting", "committee")

**Meta:**
- verbose_name: 'Berechtigung'
- ordering: `['category', 'codename']`

**__str__():** Return f"{category}: {name} ({codename})"

---

#### 2. Role Model

**Zweck:** Rolle mit zugewiesenen Berechtigungen (RBAC)

**ROLE_TYPE_CHOICES:**
- `('SYSTEM', 'System-Rolle')`
- `('COMMITTEE', 'Gremiums-Rolle')`

**Felder:**
- `id`: UUIDField (PK)
- `name`: CharField(100)
- `codename`: CharField(50, unique=True) - z.B. "CHAIR", "SYSTEM_ADMIN"
- `description`: TextField(blank=True)
- `role_type`: CharField(20, choices=ROLE_TYPE_CHOICES)
- `is_system_role`: BooleanField(default=False) - Standard-Rollen nicht löschbar
- `created_at`: DateTimeField(default=timezone.now)
- `updated_at`: DateTimeField(auto_now=True)
- `permissions`: ManyToManyField(Permission, through='RolePermission')

**ForeignKey (NOCH NICHT hinzufügen!):**
- `created_by` → wird in Schritt 1.4 ergänzt

**Meta:**
- verbose_name: 'Rolle'
- ordering: `['role_type', 'name']`

**__str__():** Return f"{name} ({codename})"

---

#### 3. RolePermission Model

**Zweck:** M:N-Zuordnung Rolle ↔ Berechtigung mit Metadaten

**Felder:**
- `id`: UUIDField (PK)
- `role`: ForeignKey(Role, CASCADE)
- `permission`: ForeignKey(Permission, CASCADE)
- `assigned_at`: DateTimeField(default=timezone.now)

**ForeignKey (NOCH NICHT hinzufügen!):**
- `assigned_by` → wird in Schritt 1.4 ergänzt

**Meta:**
- verbose_name: 'Rollen-Berechtigung'
- unique_together: `[['role', 'permission']]`
- ordering: `['role', 'permission']`

**__str__():** Return f"{role.codename} → {permission.codename}"

---

**Datei:** `apps/roles/apps.py`

- `name = 'apps.roles'`
- `verbose_name = 'Rollen & Berechtigungen'`

---

**Datei:** `apps/roles/admin.py`

**3 Admin-Klassen:**

1. **PermissionAdmin**
   - list_display: codename, name, category
   - list_filter: category
   - search_fields: codename, name, description

2. **RoleAdmin**
   - list_display: name, codename, role_type, is_system_role, created_at
   - list_filter: role_type, is_system_role
   - filter_horizontal: permissions

3. **RolePermissionAdmin**
   - list_display: role, permission, assigned_at
   - list_filter: role__role_type, permission__category

---

**Datei:** `apps/roles/tests/test_models.py`

**Tests zu implementieren:**

1. **test_permission_creation**
   - Permission mit allen Feldern erstellen
   - Assert: codename, name, category korrekt gespeichert

2. **test_permission_codename_unique**
   - Zwei Permissions mit gleichem codename sollten fehlschlagen
   - Assert: IntegrityError

3. **test_permission_str_representation**
   - __str__() sollte "{category}: {name} ({codename})" zurückgeben
   - Assert: Format korrekt

4. **test_role_creation**
   - Role mit allen Feldern erstellen
   - Assert: name, codename, role_type korrekt

5. **test_role_codename_unique**
   - Zwei Roles mit gleichem codename sollten fehlschlagen
   - Assert: IntegrityError

6. **test_role_permissions_relationship**
   - Role mit Permissions verknüpfen via RolePermission
   - Assert: ManyToMany-Beziehung funktioniert

7. **test_role_permission_unique_together**
   - Gleiche Role+Permission-Kombination zweimal hinzufügen sollte fehlschlagen
   - Assert: IntegrityError bei duplicate

8. **test_system_role_flag**
   - is_system_role Flag testen
   - Assert: System-Rollen markiert

**Siehe:** CODE_STYLE_GUIDE.md → "Django Best Practices → Testing"

---

**Migration:**
```bash
python manage.py makemigrations roles
# NOCH NICHT ausführen! Wartet auf Schritt 1.4
```

---

### Schritt 1.4: ForeignKeys hinzufügen & gemeinsam migrieren

**Datei:** `apps/roles/models.py` ergänzen

**In Role-Klasse hinzufügen:**
```python
created_by = models.ForeignKey(
    'accounts.User',
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    related_name='created_roles',
    verbose_name='Erstellt von',
    help_text='NULL = System-generierte Rolle'
)
```

**In RolePermission-Klasse hinzufügen:**
```python
assigned_by = models.ForeignKey(
    'accounts.User',
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    related_name='assigned_permissions',
    verbose_name='Zugewiesen von'
)
```

**Migrationen erstellen & ausführen:**
```bash
python manage.py makemigrations roles
python manage.py migrate  # JETZT alle Migrationen gemeinsam!
```

**settings.py anpassen:**
```python
AUTH_USER_MODEL = 'accounts.User'
```

**Superuser erstellen:**
```bash
python manage.py createsuperuser
# E-Mail, Vorname, Nachname, Geschlecht (M/F), Passwort
```

---

## Phase 2: Authentifizierung & Berechtigungen

### Ziel
Basis-Login implementieren und Standard-Rollen/Berechtigungen definieren.

### Schritt 2.1: accounts - Basis-Authentifizierung (ohne 2FA)

**Datei:** `apps/accounts/views.py`

**3 Views zu implementieren:**

1. **LoginView**
   - Extends `django.contrib.auth.views.LoginView`
   - template_name: `'accounts/login.html'`
   - redirect_authenticated_user: True
   - get_success_url(): Return `reverse_lazy('core:dashboard')`
   - Docstring: "Login with email + password. 2FA added in Phase 3."

2. **LogoutView**
   - Extends `django.contrib.auth.views.LogoutView`
   - next_page: `reverse_lazy('accounts:login')`

3. **ProfileView**
   - LoginRequiredMixin + TemplateView
   - template_name: `'accounts/profile.html'`
   - Placeholder für Phase 3 (Profil-Bearbeitung)

---

**Datei:** `apps/accounts/urls.py`

**URLs:**
- `'login/'` → LoginView (name='login')
- `'logout/'` → LogoutView (name='logout')
- `'profile/'` → ProfileView (name='profile')

app_name: `'accounts'`

---

**Datei:** `config/urls.py` ergänzen

- `'accounts/'` → include('apps.accounts.urls')

---

**Templates:**

1. **`apps/accounts/templates/accounts/login.html`**
   - Extends base.html
   - Bootstrap Card mit Login-Form
   - {{ form|crispy }} (wenn crispy-forms installiert, sonst {{ form.as_p }})
   - Submit-Button: "Anmelden"
   - Title: "Login"

2. **`apps/accounts/templates/accounts/profile.html`**
   - Extends base.html
   - Card mit Benutzer-Infos (Name, E-Mail, Geschlecht, Telefon, Beitrittsdatum)
   - Verwendet: `user.get_full_name`, `user.get_gender_display`

---

**settings.py ergänzen:**
```python
LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/accounts/login/"
```

---

**Datei:** `apps/accounts/tests/test_views.py`

**Tests zu implementieren:**

1. **test_login_view_get**
   - GET-Request auf Login-Seite
   - Assert: Status 200, Template korrekt

2. **test_login_with_valid_credentials**
   - POST mit korrekten Credentials
   - Assert: Redirect zu Dashboard, User ist authenticated

3. **test_login_with_invalid_credentials**
   - POST mit falschen Credentials
   - Assert: Bleibt auf Login-Seite, Error-Message angezeigt

4. **test_login_redirect_authenticated_user**
   - Bereits eingeloggter User greift auf Login-Seite zu
   - Assert: Redirect zu Dashboard

5. **test_logout**
   - Logout-Request
   - Assert: User ist nicht mehr authenticated, Redirect zu Login

6. **test_profile_view_requires_login**
   - Unauthenticated User greift auf Profil zu
   - Assert: Redirect zu Login-Seite

7. **test_profile_view_authenticated**
   - Authenticated User greift auf Profil zu
   - Assert: Status 200, User-Daten im Context

**Siehe:** CODE_STYLE_GUIDE.md → "Django Best Practices → Testing"

---

### Schritt 2.2: roles - Berechtigungen und Rollen per Migration erstellen

**Datei:** `apps/roles/migrations/9999_seed_roles_and_permissions.py`

**Funktionalität:**
- Data Migration (RunPython)
- Erstellt Permissions, Roles und deren Zuordnungen in einem Schritt
- Reverse-Funktion zum Rückgängigmachen implementiert

**Berechtigungen zu erstellen:**

**System-Berechtigungen:**
- `system.admin` - "Systemweiter Admin-Zugriff" - "Voller Zugriff auf alle System-Funktionen"
- `system.manage_users` - "Benutzer verwalten" - "Benutzer erstellen, bearbeiten und löschen"

**Rollen-Berechtigungen:**
- `role.create` - "Rolle erstellen" - "Neue Rollen anlegen"
- `role.edit` - "Rolle bearbeiten" - "Existierende Rollen bearbeiten"
- `role.delete` - "Rolle löschen" - "Rollen löschen (außer System-Rollen)"
- `role.assign_permissions` - "Berechtigungen zuweisen" - "Berechtigungen zu Rollen hinzufügen oder entfernen"
- `role.view` - "Rollen einsehen" - "Liste aller Rollen anzeigen"
- `role.assign_to_member` - "Rolle zuweisen" - "Rollen an Gremiumsmitglieder zuweisen"

**System-Rollen zu erstellen:**
- `SYSTEM_ADMIN` - "System-Administrator" - "Vollständige System-Administration" (SYSTEM, sort_order=1)
- `USER` - "Benutzer" - "Standard-Benutzer ohne besondere Rechte" (SYSTEM, sort_order=100)

**Gremiums-Rollen zu erstellen:**
- `CHAIR` - "Vorsitz" - "Vorsitzender des Gremiums" (COMMITTEE, sort_order=1, auto_include_in_ba=True)
- `VICE_CHAIR` - "Stellv. Vorsitz" - "Stellvertretender Vorsitzender" (COMMITTEE, sort_order=2, auto_include_in_ba=True)
- `CLERK` - "Schriftführung" - "Schriftführer des Gremiums" (COMMITTEE, sort_order=10, auto_include_in_ba=False)
- `MEMBER` - "Mitglied" - "Reguläres Gremiumsmitglied" (COMMITTEE, sort_order=20, auto_include_in_ba=False)
- `SUBSTITUTE` - "Ersatzmitglied" - "Ersatzmitglied für reguläre Mitglieder" (COMMITTEE, sort_order=30, auto_include_in_ba=False)
- `EXTERNAL_MEMBER` - "Externes Mitglied" - "Externes Mitglied ohne Stimmrecht" (COMMITTEE, sort_order=40, auto_include_in_ba=False)
- `GUEST` - "Gast" - "Gast ohne Stimmrecht" (COMMITTEE, sort_order=50, auto_include_in_ba=False)

**Implementierung in 3 Schritten:**

**STEP 1: Create Permissions**
- Loop über PERMISSIONS-Liste: Permission.objects.get_or_create()
- Felder: codename, name, description, category

**STEP 2: Create Roles**
- Loop über SYSTEM_ROLES und COMMITTEE_ROLES
- Role.objects.get_or_create() mit allen Feldern
- Bei committee roles: auto_include_in_ba aktualisieren falls bereits existent

**STEP 3: Assign ALL Permissions to SYSTEM_ADMIN**
- SYSTEM_ADMIN Rolle laden
- Alle Permissions abrufen
- Für jede Permission: RolePermission.objects.get_or_create()

**Reverse-Funktion:**
- Löscht alle RolePermissions für system/role category
- Löscht alle Permissions mit category='system' oder 'role'
- Löscht alle Roles mit den definierten codenames

**Migration ausführen:**
```bash
python manage.py makemigrations roles
python manage.py migrate roles 9999
```

**Siehe:** CODE_STYLE_GUIDE.md → "Django Best Practices → Data Migrations"

---

**Datei:** `apps/roles/tests/test_permissions.py`

**Tests zu implementieren:**

1. **test_migration_creates_permissions**
   - Migration ausführen (oder DB-State nach Migration prüfen)
   - Assert: Alle erwarteten Permissions existieren in DB

2. **test_migration_creates_roles**
   - Assert: Alle System- und Gremiums-Rollen existieren

3. **test_system_admin_has_all_permissions**
   - SYSTEM_ADMIN Rolle laden
   - Assert: Hat ALLE Permissions zugewiesen (nicht nur system)

4. **test_system_roles_marked_correctly**
   - System-Rollen prüfen
   - Assert: is_system_role=True

5. **test_committee_roles_created_with_correct_attributes**
   - Alle Gremiums-Rollen prüfen
   - Assert: CHAIR, VICE_CHAIR haben auto_include_in_ba=True
   - Assert: Andere Committee-Roles haben auto_include_in_ba=False
   - Assert: sort_order korrekt gesetzt

6. **test_permission_categorization**
   - Permissions nach category filtern
   - Assert: system.* und role.* Permissions korrekt kategorisiert

7. **test_migration_is_idempotent**
   - Migration-Funktion zweimal aufrufen (simuliert)
   - Assert: Keine Duplikate, gleiche Anzahl

8. **test_reverse_migration_cleans_up**
   - Reverse-Funktion testen
   - Assert: Alle erstellten Daten werden entfernt

**Siehe:** CODE_STYLE_GUIDE.md → "Django Best Practices → Testing"

---

### Schritt 2.4: accounts - UserProfile & 2FA-Vorbereitung

**Datei:** `apps/accounts/models.py` ergänzen

**2 zusätzliche Modelle:**

#### 1. UserProfile Model

**Zweck:** Erweiterte Benutzerprofile (OneToOne zu User)

**Felder:**
- `id`: UUIDField (PK)
- `user`: OneToOneField(User, CASCADE, related_name='profile')
- `department`: CharField(200, blank=True)
- `employee_id`: CharField(50, blank=True)
- `notification_preferences`: JSONField(default=dict)
- `avatar`: ImageField(upload_to='avatars/', blank=True, null=True)

**Meta:**
- verbose_name: 'Benutzerprofil'

**__str__():** Return f"Profil von {user.get_full_name()}"

---

#### 2. TwoFactorRecoveryCode Model

**Zweck:** Recovery-Codes für 2FA (Phase 3)

**Felder:**
- `id`: UUIDField (PK)
- `user`: ForeignKey(User, CASCADE, related_name='recovery_codes')
- `code`: CharField(255) - gehasht gespeichert
- `is_used`: BooleanField(default=False)
- `created_at`: DateTimeField(default=timezone.now)
- `used_at`: DateTimeField(null=True, blank=True)

**Meta:**
- verbose_name: '2FA Recovery-Code'
- ordering: `['-created_at']`

**__str__():** Return Status (verwendet/verfügbar)

---

**Migration:**
```bash
python manage.py makemigrations accounts
python manage.py migrate
```

---

**Datei:** `apps/accounts/tests/test_models.py` ergänzen

**Zusätzliche Tests für neue Modelle:**

9. **test_user_profile_creation**
   - UserProfile erstellen und mit User verknüpfen
   - Assert: OneToOne-Beziehung funktioniert

10. **test_user_profile_auto_created** (optional für Signal)
    - User erstellen sollte automatisch Profile erstellen
    - Assert: user.profile existiert

11. **test_user_profile_str_representation**
    - __str__() von UserProfile testen
    - Assert: Format "Profil von {name}"

12. **test_recovery_code_creation**
    - TwoFactorRecoveryCode erstellen
    - Assert: Alle Felder korrekt

13. **test_recovery_code_is_hashed**
    - Code sollte gehasht gespeichert werden
    - Assert: Plaintext nicht in DB

14. **test_recovery_code_mark_as_used**
    - Recovery-Code als verwendet markieren
    - Assert: is_used=True, used_at gesetzt

**Siehe:** CODE_STYLE_GUIDE.md → "Django Best Practices → Testing"

---

## Phase 3: Erweiterte Features

### Schritt 3.1: accounts - 2FA-Implementierung

**Siehe ausführlich:** `docs/apps/01_accounts.md` Abschnitt "2FA-Workflow"

**Komponenten zu implementieren:**

1. **TwoFactorSetupView**
   - TOTP-Secret generieren mit `pyotp`
   - QR-Code generieren mit `qrcode`
   - Recovery-Codes erstellen (10 Stück, gehasht)

2. **TwoFactorVerifyView**
   - TOTP-Code validieren
   - Recovery-Code als Fallback
   - Rate-Limiting: Max 5 Versuche pro 5 Min (django-ratelimit)

3. **RecoveryCodesView**
   - Recovery-Codes anzeigen (nur einmalig bei Erstellung)
   - Regenerieren-Funktion

4. **Require2FAMiddleware**
   - 2FA-Pflicht durchsetzen
   - Whitelist: Login, 2FA-Setup, Static Files
   - Redirect zu 2FA-Setup wenn nicht aktiviert

**Dependencies:**
```bash
uv add pyotp qrcode django-ratelimit
```

**Security:**
- TOTP-Secret verschlüsselt speichern
- Recovery-Codes mit bcrypt hashen
- Session-basiertes 2FA-Tracking
- Brute-Force-Schutz via Rate-Limiting

---

**Datei:** `apps/accounts/tests/test_auth.py`

**Tests für 2FA zu implementieren:**

1. **test_totp_secret_generation**
   - TOTP-Secret generieren
   - Assert: Secret ist Base32, korrekte Länge

2. **test_qr_code_generation**
   - QR-Code für TOTP generieren
   - Assert: QR-Code-Bild wird erstellt

3. **test_totp_verification_valid_code**
   - Gültigen TOTP-Code verifizieren
   - Assert: Verifikation erfolgreich

4. **test_totp_verification_invalid_code**
   - Ungültigen Code verifizieren
   - Assert: Verifikation schlägt fehl

5. **test_recovery_code_verification**
   - Recovery-Code als Fallback verwenden
   - Assert: Code funktioniert, wird als verwendet markiert

6. **test_recovery_code_cannot_be_reused**
   - Verwendeten Recovery-Code erneut verwenden
   - Assert: Schlägt fehl

7. **test_2fa_rate_limiting**
   - Mehr als 5 Versuche innerhalb 5 Minuten
   - Assert: Rate-Limit greift

8. **test_2fa_middleware_blocks_without_2fa**
   - User ohne 2FA versucht Dashboard zu erreichen
   - Assert: Redirect zu 2FA-Setup

9. **test_2fa_middleware_allows_with_2fa**
   - User mit aktivierter 2FA
   - Assert: Zugriff erlaubt

10. **test_2fa_session_tracking**
    - 2FA-Status in Session speichern
    - Assert: Session-Variable korrekt gesetzt

**Siehe:** CODE_STYLE_GUIDE.md → "Django Best Practices → Testing"

---

### Schritt 3.2: accounts - User-Verwaltung für Admins

**Ziel:** Admin kann Benutzer per E-Mail einladen, Benutzer registriert sich über Link

#### 3.2.1: UserInvitation Model

**Datei:** `apps/accounts/models.py` ergänzen

**Felder:**
- `id`: UUIDField (PK)
- `email`: EmailField
- `token`: CharField(64, unique=True) - generiert mit `secrets.token_urlsafe(32)`
- `invited_by`: ForeignKey(User, SET_NULL, related_name='sent_invitations')
- `created_at`: DateTimeField(default=timezone.now)
- `expires_at`: DateTimeField - 7 Tage Gültigkeit
- `is_used`: BooleanField(default=False)
- `used_at`: DateTimeField(null=True, blank=True)

**Methoden:**
- `is_valid()`: Return not is_used AND expires_at > now
- `mark_as_used()`: Set is_used=True, used_at=now, save()

**Meta:**
- verbose_name: 'Benutzer-Einladung'
- ordering: `['-created_at']`

---

#### 3.2.2: Views für User-Verwaltung

**Datei:** `apps/accounts/views.py` ergänzen

**Custom Mixin:**
- **AdminRequiredMixin**(UserPassesTestMixin)
  - test_func(): Check is_superuser OR has_perm('accounts.manage_users')

**Views zu implementieren:**

1. **UserListView** (LoginRequiredMixin, AdminRequiredMixin, ListView)
   - Model: User
   - Pagination: 20 per page
   - Suchfunktion: Filter nach first_name, last_name, email
   - Template: `accounts/user_list.html`

2. **UserInviteView** (LoginRequiredMixin, AdminRequiredMixin, CreateView)
   - Model: UserInvitation
   - Form: UserInviteForm
   - Token generieren mit secrets.token_urlsafe(32)
   - Expires_at: timezone.now() + timedelta(days=7)
   - E-Mail senden mit django.core.mail.send_mail()
   - Template: `accounts/user_invite.html`

3. **UserRegistrationView** (FormView)
   - Token validieren in dispatch()
   - Redirect wenn Invitation abgelaufen
   - User erstellen + UserProfile
   - Invitation mark_as_used()
   - Success-Message + Redirect zu 2FA-Setup (Phase 3)
   - Template: `accounts/user_register.html`

4. **UserUpdateView** (LoginRequiredMixin, AdminRequiredMixin, UpdateView)
   - Model: User
   - Form: UserUpdateForm
   - Template: `accounts/user_update.html`

5. **UserDeleteView** (LoginRequiredMixin, AdminRequiredMixin, DeleteView)
   - **Soft-Delete**: is_active = False (kein echtes DELETE!)
   - Success-Message
   - Template: `accounts/user_confirm_delete.html`

---

#### 3.2.3: Forms

**Datei:** `apps/accounts/forms.py` erstellen

**3 Forms:**

1. **UserInviteForm**(ModelForm)
   - Model: UserInvitation
   - Fields: ['email']
   - Widget: EmailInput mit Bootstrap-Class

2. **UserRegistrationForm**(ModelForm)
   - Model: User
   - Fields: first_name, last_name, gender, phone
   - Zusätzlich: password, password_confirm (PasswordInput)
   - clean(): Passwörter vergleichen
   - __init__: email-Parameter für Invitation

3. **UserUpdateForm**(ModelForm)
   - Model: User
   - Fields: first_name, last_name, gender, phone, is_active
   - Alle mit Bootstrap-Classes

**Siehe:** CODE_STYLE_GUIDE.md → "Django Best Practices → Forms"

---

#### 3.2.4: URLs

**Datei:** `apps/accounts/urls.py` ergänzen

**Neue URLs:**
- `'users/'` → UserListView (name='user_list')
- `'users/invite/'` → UserInviteView (name='user_invite')
- `'users/<uuid:pk>/edit/'` → UserUpdateView (name='user_update')
- `'users/<uuid:pk>/delete/'` → UserDeleteView (name='user_delete')
- `'register/<str:token>/'` → UserRegistrationView (name='register')
- `'password/change/'` → PasswordChangeView (name='password_change')

---

#### 3.2.5: Templates

**Templates zu erstellen:**

1. **`accounts/user_list.html`**
   - Tabelle mit allen Benutzern
   - Spalten: Name, E-Mail, Geschlecht, Status, 2FA, Beigetreten, Aktionen
   - Suchfeld (GET-Form)
   - Button "Benutzer einladen"
   - Aktionen: Bearbeiten, Löschen (Icons)

2. **`accounts/user_invite.html`**
   - Form mit E-Mail-Feld
   - Submit: "Einladung senden"

3. **`accounts/user_register.html`**
   - Form: first_name, last_name, gender, phone, password, password_confirm
   - E-Mail als readonly-Field anzeigen
   - Submit: "Konto erstellen"

4. **`accounts/user_update.html`**
   - Form zum Bearbeiten
   - Submit: "Speichern"

5. **`accounts/user_confirm_delete.html`**
   - Bestätigungs-Dialog
   - Warning: Benutzer wird deaktiviert (nicht gelöscht)
   - Buttons: Abbrechen, Deaktivieren

**Alle Templates:** Bootstrap 5 Styling, Icons von Bootstrap Icons

---

**Datei:** `apps/accounts/tests/test_views.py` ergänzen

**Zusätzliche Tests für User-Verwaltung:**

8. **test_user_list_requires_admin**
   - Normaler User greift auf User-Liste zu
   - Assert: 403 Forbidden oder Redirect

9. **test_user_list_accessible_by_admin**
   - Admin/Superuser greift auf User-Liste zu
   - Assert: Status 200, User-Liste im Context

10. **test_user_list_search**
    - Suchfunktion mit Suchbegriff testen
    - Assert: Gefilterte Ergebnisse korrekt

11. **test_user_invite_creates_invitation**
    - Admin lädt Benutzer ein
    - Assert: UserInvitation erstellt, E-Mail gesendet

12. **test_user_invite_duplicate_email**
    - Einladung für existierende E-Mail
    - Assert: Error-Message, keine Einladung

13. **test_user_registration_with_valid_token**
    - Registrierung mit gültigem Token
    - Assert: User erstellt, Profile erstellt, Invitation als verwendet markiert

14. **test_user_registration_with_expired_token**
    - Registrierung mit abgelaufenem Token
    - Assert: Redirect zu Login, Error-Message

15. **test_user_update_by_admin**
    - Admin ändert Benutzerdaten
    - Assert: Änderungen gespeichert

16. **test_user_soft_delete**
    - Admin "löscht" Benutzer
    - Assert: is_active=False, User existiert noch in DB

**Datei:** `apps/accounts/tests/test_models.py` ergänzen

**Tests für UserInvitation:**

15. **test_invitation_is_valid_when_fresh**
    - Frische Einladung erstellen
    - Assert: is_valid() = True

16. **test_invitation_is_invalid_when_expired**
    - Einladung mit expires_at in Vergangenheit
    - Assert: is_valid() = False

17. **test_invitation_is_invalid_when_used**
    - Einladung als verwendet markieren
    - Assert: is_valid() = False

18. **test_invitation_mark_as_used_sets_timestamp**
    - mark_as_used() aufrufen
    - Assert: is_used=True, used_at ist gesetzt

19. **test_invitation_token_unique**
    - Zwei Einladungen mit gleichem Token
    - Assert: IntegrityError

**Siehe:** CODE_STYLE_GUIDE.md → "Django Best Practices → Testing"

---

### Schritt 3.3: roles - Rollen-Verwaltung für Admins

**Ähnlich wie 3.2, aber für Roles:**

**Views:**
- RoleListView (Liste aller Rollen)
- RoleCreateView (Neue Rolle erstellen)
- RoleUpdateView (Rolle bearbeiten, Permissions zuweisen)
- RoleDeleteView (Nur benutzerdefinierte Rollen löschbar!)

**Forms:**
- RoleCreateForm
- RoleUpdateForm (mit Permissions-Auswahl via filter_horizontal)

**Templates:**
- roles/role_list.html
- roles/role_form.html
- roles/role_confirm_delete.html

**Besonderheit:**
- System-Rollen (is_system_role=True) dürfen NICHT gelöscht oder umbenannt werden
- Nur Permissions können bei System-Rollen angepasst werden (mit Warnung)

---

**Datei:** `apps/roles/tests/test_views.py`

**Tests für Rollen-Verwaltung:**

1. **test_role_list_requires_admin**
   - Normaler User greift auf Rollen-Liste zu
   - Assert: 403 Forbidden

2. **test_role_create_by_admin**
   - Admin erstellt neue Rolle
   - Assert: Rolle erstellt, Permissions zuweisbar

3. **test_role_update_permissions**
   - Permissions einer Rolle ändern
   - Assert: Änderungen gespeichert

4. **test_system_role_cannot_be_deleted**
   - Versuch System-Rolle zu löschen
   - Assert: Error-Message, Rolle existiert noch

5. **test_custom_role_can_be_deleted**
   - Benutzerdefinierte Rolle löschen
   - Assert: Erfolgreich gelöscht

6. **test_system_role_codename_cannot_be_changed**
   - Versuch System-Rolle umzubenennen
   - Assert: Codename bleibt unverändert (readonly)

**Siehe:** CODE_STYLE_GUIDE.md → "Django Best Practices → Testing"

---

## Validierung nach jeder Phase

### Checkliste nach Abschluss einer Phase:

**1. Migrations prüfen:**
```bash
python manage.py makemigrations --check --dry-run
python manage.py showmigrations
```

**2. Admin-Interface testen:**
- http://localhost:8000/admin/
- Alle Models sichtbar?
- CRUD-Operationen funktionieren?

**3. URLs testen:**
```bash
python manage.py show_urls  # Django-extensions erforderlich
```

**4. Alle Tests ausführen:**
```bash
# Alle Tests
pytest

# Nur accounts
pytest apps/accounts/tests/

# Nur roles
pytest apps/roles/tests/

# Mit Coverage
pytest --cov=apps.accounts --cov=apps.roles
```

**5. Code-Qualität prüfen:**
```bash
# Type-Checking (wenn mypy installiert)
mypy apps/accounts apps/roles

# Linting (wenn ruff installiert)
ruff check apps/accounts apps/roles
```

**Siehe:** CODE_STYLE_GUIDE.md → "Django Best Practices → Testing"

---

## Deployment-Vorbereitung

### Security-Settings für Production

**In `config/settings/production.py`:**

```python
# Session Security
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Strict'
SESSION_COOKIE_AGE = 1800  # 30 Minuten

# Password Settings
MIN_PASSWORD_LENGTH = 12
PASSWORD_HISTORY_COUNT = 5
PASSWORD_MAX_AGE_DAYS = 90

# 2FA Settings
TOTP_TOLERANCE = 1  # ±30 Sekunden
TOTP_ISSUER = 'BR-Manager'
RECOVERY_CODES_COUNT = 10

# Rate Limiting
RATELIMIT_ENABLE = True
RATELIMIT_USE_CACHE = 'default'
```

### Konstanten in settings definieren

**Siehe:** CODE_STYLE_GUIDE.md → "Clean Code Principles → Use Constants"

Alle Magic Numbers in settings.py definieren:
- INVITATION_VALIDITY_DAYS = 7
- MAX_LOGIN_ATTEMPTS = 5
- LOGIN_ATTEMPT_TIMEOUT = 300  # 5 Minuten

---

## Zusammenfassung

### Reihenfolge kritisch:

1. ✅ Phase 0: Core-UI (Dashboard, Navigation)
2. ✅ Phase 1.1-1.2: User-Model (OHNE ForeignKeys)
3. ✅ Phase 1.3: Role-Models (OHNE ForeignKeys zu User)
4. ✅ Phase 1.4: ForeignKeys hinzufügen, DANN migrieren
5. ✅ Phase 2: Auth + Permissions seeden
6. ✅ Phase 3: 2FA + User-Verwaltung + Role-Verwaltung

### Code-Qualität sicherstellen:

- **Clean Code:** Siehe CODE_STYLE_GUIDE.md
- **Type Hints:** Für alle Funktionen
- **Docstrings:** Google Style, Pflicht
- **DRY:** Keine Code-Duplikation
- **Tests:** Für ALLE Funktionen und Views (nicht optional!)
- **Test Coverage:** Minimum 80% anstreben

### Test-Driven Development (TDD):

**Empfohlener Workflow:**
1. Test schreiben (Red)
2. Minimale Implementierung (Green)
3. Refactoring (Refactor)
4. Nächster Test

**Oder:** Implementierung dann Tests - Hauptsache Tests sind vorhanden!

### Wichtige Referenzen:

- CODE_STYLE_GUIDE.md (Alle Code-Beispiele)
- docs/apps/01_accounts.md (2FA-Details)
- docs/apps/02_roles.md (RBAC-Details)
- docs/06_berechtigungskonzept.md (Permission-Matrix)

---

## Nächste Schritte nach Accounts & Roles

Nach erfolgreicher Implementierung:
1. Committees-App (verwendet User + Roles)
2. Meetings-App (verwendet Committees)
3. Weitere Apps gemäß Projektplan
