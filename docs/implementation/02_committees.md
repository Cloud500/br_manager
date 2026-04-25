# Implementierungsplan: Committees App

## Übersicht

Dieser Plan beschreibt die Implementierung der `committees`-App für die Gremienverwaltung (Betriebsrat, Ausschüsse, Mitgliedschaften). Diese App baut auf den bereits implementierten `accounts` und `roles` Apps auf.

### ⚠️ Code-Konventionen

**Wichtig:** Alle Code-Implementierungen folgen den Richtlinien in `docs/implementation/CODE_STYLE_GUIDE.md`

Kurzübersicht:
- ✅ **Code (Python) = Englisch** (Variablen, Funktionen, Klassen, Kommentare)
- ✅ **User-sichtbare Strings = Deutsch** (verbose_name, Labels, Templates, Messages)

**📖 Vollständige Beispiele:** Siehe `docs/implementation/CODE_STYLE_GUIDE.md`

### Abhängigkeiten

```
accounts ──┐
           ├──→ committees
roles ─────┘
```

**Abhängigkeiten:**
- `accounts` definiert **User-Modell** → benötigt für Membership (ForeignKey)
- `roles` definiert **Gremiumsrollen** → benötigt für Membership (CHAIR, MEMBER, etc.)
- `committees` ist die **Basis für weitere Apps** (meetings, documents, etc.)

**Fazit:** committees kann **sequenziell nach accounts & roles** implementiert werden.

---

## Strategie: Sequenzielle Phasen-Implementierung

### Prinzip
Die App wird in logischen Schritten aufgebaut:
1. Basis-Modelle (Committee, Membership)
2. Validierung und Business Logic
3. Admin-Interface & Berechtigungen
4. Views und Templates
5. Erweiterte Features (Helper-Funktionen)

### Vorteile
- ✅ Klare Abhängigkeiten zu accounts und roles
- ✅ Schrittweise Erweiterung
- ✅ Frühe Tests der Kern-Funktionalität
- ✅ Modularer Aufbau

---

## Phase 1: Projekt-Setup & Basis-Modelle

### Ziel
App-Struktur erstellen und Kern-Modelle (Committee, Membership) implementieren.

### Schritt 1.1: Projekt-Setup

**App erstellen:**
```bash
python manage.py startapp committees apps/committees
```

**Verzeichnisstruktur anlegen:**
```bash
# Tests
mkdir -p apps/committees/tests
touch apps/committees/tests/{__init__.py,test_models.py,test_views.py,test_permissions.py,test_helpers.py}

# Templates & Static
mkdir -p apps/committees/templates/committees apps/committees/static/committees

# Management Commands
mkdir -p apps/committees/management/commands
touch apps/committees/management/__init__.py apps/committees/management/commands/__init__.py

# Utils
touch apps/committees/utils.py
touch apps/committees/mixins.py
```

**App registrieren:**
- In `config/settings/base.py` → `LOCAL_APPS` ergänzen:
  - `"apps.committees"`

---

### Schritt 1.2: Soft-Delete Manager & QuerySet

**Datei:** `apps/committees/models.py`

**SoftDeleteQuerySet implementieren mit:**
- `delete()`: Setzt deleted_at=timezone.now()
- `hard_delete()`: super().delete() für permanentes Löschen
- `alive()`: filter(deleted_at__isnull=True)
- `deleted()`: filter(deleted_at__isnull=False)

**SoftDeleteManager implementieren mit:**
- `get_queryset()`: Gibt nur nicht-gelöschte Objekte zurück (nutzt SoftDeleteQuerySet.alive())
- `all_with_deleted()`: Gibt alle Objekte inkl. gelöschte zurück (für Admin)
- `deleted_only()`: Gibt nur gelöschte Objekte zurück

**Siehe:** CODE_STYLE_GUIDE.md → "Django Best Practices → Custom Managers"

---

### Schritt 1.3: Committee-Modell

**Datei:** `apps/committees/models.py` ergänzen

**Funktionalität:**
- Gremien-Typen (Betriebsrat, Ausschüsse, Ad-hoc)
- Hierarchische Struktur mit parent-Beziehung
- Konfigurationsfelder für Sitze, Quorum, Personelle Maßnahmen
- **Soft-Delete Unterstützung**

**COMMITTEE_TYPE_CHOICES:**
- `('MAIN', 'Betriebsrat (Hauptgremium)')`
- `('COMMITTEE', 'Betriebsausschuss')`
- `('SUBCOMMITTEE', 'Fachausschuss')`
- `('ADHOC', 'Ad-hoc-Ausschuss')`

**QUORUM_TYPE_CHOICES:**
- `('SIMPLE_MAJORITY', 'Einfache Mehrheit')`
- `('QUALIFIED', 'Qualifizierte Mehrheit')`

**GENDER_CHOICES:**
- `('M', 'Männlich')`
- `('F', 'Weiblich')`

**Felder:**
- `id`: UUIDField (PK, default=uuid.uuid4)
- `name`: CharField(200, verbose_name='Name')
- `committee_type`: CharField(20, choices=COMMITTEE_TYPE_CHOICES)
- `parent`: ForeignKey('self', SET_NULL, null=True, blank=True, related_name='subcommittees')
- `description`: TextField(blank=True, verbose_name='Beschreibung')
- `created_at`: DateTimeField(default=timezone.now)
- `is_active`: BooleanField(default=True)
- `deleted_at`: DateTimeField(null=True, blank=True, verbose_name='Gelöscht am')
- `deleted_by`: ForeignKey('accounts.User', SET_NULL, null=True, blank=True, related_name='deleted_committees', verbose_name='Gelöscht von')
- `total_seats`: PositiveIntegerField(verbose_name='Gesamtanzahl Sitze')
- `quorum_type`: CharField(20, choices=QUORUM_TYPE_CHOICES, default='SIMPLE_MAJORITY')
- `personnel_enabled`: BooleanField(default=False, verbose_name='Personelle Einzelmaßnahmen aktiviert')
- `substitute_logic_enabled`: BooleanField(default=False, verbose_name='Nachrücklogik aktiviert')
- `minority_gender`: CharField(1, choices=GENDER_CHOICES, blank=True, null=True, verbose_name='Minderheitengeschlecht')
- `minority_min_count`: PositiveIntegerField(blank=True, null=True, verbose_name='Mindestanzahl Minderheitengeschlecht')

**Meta:**
- verbose_name: 'Gremium'
- verbose_name_plural: 'Gremien'
- ordering: `['committee_type', 'name']`

**Manager:**
- `objects`: SoftDeleteManager() - Standard-Manager (nur nicht-gelöschte)
- `all_objects`: SoftDeleteManager().all_with_deleted() - Für Admin

**Methoden:**
- `__str__()`: Return name
- `clean()`: Hierarchie-Validierung (siehe unten)
- `delete(user=None)`: Soft-Delete mit Kaskadierung (siehe unten)
- `hard_delete()`: Permanentes Löschen
- `get_active_members()`: QuerySet der aktiven REGULAR Mitglieder (nicht gelöscht)
- `get_active_substitutes()`: QuerySet der aktiven SUBSTITUTE Mitglieder (nicht gelöscht)
- `get_external_members()`: QuerySet der EXTERNAL Mitglieder (nicht gelöscht)

**Hierarchie-Validierung in clean():**
```python
def clean(self):
    """
    Validate committee hierarchy rules:
    - MAIN committees cannot have a parent
    - Non-MAIN committees must have a parent
    - Prevent circular references
    - Validate minority gender configuration
    """
    # MAIN darf kein parent haben
    if self.committee_type == 'MAIN' and self.parent:
        raise ValidationError({
            'parent': 'Hauptgremium darf kein übergeordnetes Gremium haben'
        })
    
    # Nicht-MAIN muss parent haben
    if self.committee_type != 'MAIN' and not self.parent:
        raise ValidationError({
            'parent': 'Ausschuss benötigt ein übergeordnetes Gremium'
        })
    
    # Zirkelbezug-Prüfung
    if self.parent:
        current = self.parent
        visited = {self.id} if self.id else set()
        while current:
            if current.id in visited:
                raise ValidationError({
                    'parent': 'Zirkelbezug in Gremien-Hierarchie erkannt'
                })
            visited.add(current.id)
            current = current.parent
    
    # Minderheitengeschlecht-Validierung
    if self.minority_min_count and not self.minority_gender:
        raise ValidationError({
            'minority_gender': 'Minderheitengeschlecht muss angegeben werden wenn Mindestanzahl festgelegt ist'
        })
    
    if self.minority_min_count and self.minority_min_count > self.total_seats:
        raise ValidationError({
            'minority_min_count': 'Mindestanzahl darf nicht größer sein als Gesamtanzahl Sitze'
        })
```

**Soft-Delete Methoden:**

**delete(user=None):**
- Setzt `deleted_at = timezone.now()` und `deleted_by = user`
- **Kaskadiert zu allen Memberships:** Ruft `delete(user=user)` für alle `self.memberships.alive()` auf
- Gibt Tuple zurück: `(anzahl_gelöscht, {'committees.Committee': 1, 'committees.Membership': anzahl_memberships})`

**hard_delete():**
- Ruft `super().delete()` für permanentes Löschen (nur Admin)

**Siehe:** CODE_STYLE_GUIDE.md → "Django Best Practices → Models"

---

### Schritt 1.4: Membership-Modell

**Datei:** `apps/committees/models.py` ergänzen

**Funktionalität:**
- Mitgliedschaft User ↔ Committee
- Rollenzuweisung pro Mitglied
- Mitgliedstypen (Regular, Substitute, External)
- Wahlinfo-Felder für Ersatzmitglieder-Nachrücken

**MEMBER_TYPE_CHOICES:**
- `('REGULAR', 'Reguläres Mitglied')`
- `('SUBSTITUTE', 'Ersatzmitglied')`
- `('EXTERNAL', 'Externes Ausschussmitglied')`

**Felder:**
- `id`: UUIDField (PK, default=uuid.uuid4)
- `user`: ForeignKey('accounts.User', CASCADE, related_name='memberships')
- `committee`: ForeignKey(Committee, CASCADE, related_name='memberships')
- `role`: ForeignKey('roles.Role', SET_NULL, null=True, related_name='committee_memberships')
- `is_active`: BooleanField(default=True)
- `member_type`: CharField(20, choices=MEMBER_TYPE_CHOICES, default='REGULAR')
- `start_date`: DateField(verbose_name='Beginn der Mitgliedschaft')
- `end_date`: DateField(null=True, blank=True, verbose_name='Ende der Mitgliedschaft')
- `election_list_name`: CharField(100, blank=True, verbose_name='Listenname bei Listenwahl')
- `election_list_position`: PositiveIntegerField(null=True, blank=True, verbose_name='Listenplatz')
- `election_votes`: PositiveIntegerField(null=True, blank=True, verbose_name='Stimmenzahl bei Wahl')
- `deleted_at`: DateTimeField(null=True, blank=True, verbose_name='Gelöscht am')
- `deleted_by`: ForeignKey('accounts.User', SET_NULL, null=True, blank=True, related_name='deleted_memberships', verbose_name='Gelöscht von')

**Meta:**
- verbose_name: 'Mitgliedschaft'
- verbose_name_plural: 'Mitgliedschaften'
- unique_together: `[['user', 'committee']]`
- ordering: `['committee', 'member_type', '-start_date']`

**Manager:**
- `objects`: SoftDeleteManager() - Standard-Manager (nur nicht-gelöschte)
- `all_objects`: SoftDeleteManager().all_with_deleted() - Für Admin

**Methoden:**
- `__str__()`: Return f"{user.get_full_name()} → {committee.name} ({get_member_type_display()})"
- `clean()`: Validierung für externe Mitglieder (siehe unten)
- `delete(user=None)`: Soft-Delete (siehe unten)
- `hard_delete()`: Permanentes Löschen
- `is_current()`: Property - prüft ob Mitgliedschaft aktuell gültig (start_date <= heute, end_date >= heute oder NULL, is_active=True, nicht gelöscht)

**Validierung in clean():**
```python
def clean(self):
    """
    Validate membership rules:
    - External members cannot be in main committee simultaneously
    - External members cannot have election info
    """
    # Externe Ausschussmitglieder dürfen nicht im Hauptgremium sein
    if self.member_type == 'EXTERNAL':
        # Prüfe ob User bereits im Hauptgremium ist
        main_committee = self.committee.parent if self.committee.committee_type != 'MAIN' else self.committee
        if main_committee and Membership.objects.filter(
            user=self.user,
            committee__committee_type='MAIN',
            is_active=True
        ).exclude(id=self.id).exists():
            raise ValidationError({
                'member_type': 'Externe Ausschussmitglieder dürfen nicht gleichzeitig im Hauptgremium sein'
            })
    
    # Wahlinfo nur für REGULAR und SUBSTITUTE
    if self.member_type == 'EXTERNAL' and (self.election_list_name or self.election_list_position):
        raise ValidationError({
            'election_list_name': 'Externe Mitglieder haben keine Wahlinfo'
        })
```

**Soft-Delete Methoden:**

**delete(user=None):**
- Setzt `deleted_at = timezone.now()` und `deleted_by = user`
- Gibt Tuple zurück: `(1, {'committees.Membership': 1})`

**hard_delete():**
- Ruft `super().delete()` für permanentes Löschen (nur Admin)

**is_current Property:**
- Prüft zusätzlich `deleted_at` (muss None sein für current=True)

**Siehe:** CODE_STYLE_GUIDE.md → "Django Best Practices → Models"

---

**Datei:** `apps/committees/apps.py`

- `default_auto_field = 'django.db.models.BigAutoField'`
- `name = 'apps.committees'`
- `verbose_name = 'Gremienverwaltung'`

---

**Migration:**
```bash
python manage.py makemigrations committees
python manage.py migrate
```

---

### Schritt 1.5: Model-Tests

**Datei:** `apps/committees/tests/test_models.py`

**Tests zu implementieren:**

#### Committee-Model Tests

1. **test_committee_creation**
   - Committee mit allen Pflichtfeldern erstellen
   - Assert: name, committee_type, total_seats korrekt gespeichert

2. **test_main_committee_without_parent**
   - MAIN Committee ohne parent erstellen
   - Assert: Erfolgreich gespeichert

3. **test_main_committee_with_parent_raises_error**
   - MAIN Committee mit parent erstellen
   - Assert: ValidationError

4. **test_subcommittee_without_parent_raises_error**
   - SUBCOMMITTEE ohne parent erstellen
   - Assert: ValidationError

5. **test_subcommittee_with_parent**
   - SUBCOMMITTEE mit parent erstellen
   - Assert: Erfolgreich gespeichert, parent-Beziehung korrekt

6. **test_circular_reference_detection**
   - Versuch Zirkelbezug zu erstellen (A → B → A)
   - Assert: ValidationError

7. **test_committee_str_representation**
   - __str__() sollte name zurückgeben
   - Assert: Format korrekt

8. **test_get_active_members**
   - Committee mit mehreren Mitgliedern (aktiv/inaktiv, REGULAR/SUBSTITUTE)
   - Assert: get_active_members() gibt nur aktive REGULAR zurück

9. **test_get_active_substitutes**
   - Committee mit Ersatzmitgliedern
   - Assert: get_active_substitutes() filtert korrekt

10. **test_get_external_members**
    - Committee mit externen Mitgliedern
    - Assert: get_external_members() filtert korrekt

11. **test_minority_gender_with_min_count**
    - Committee mit minority_gender='F' und minority_min_count=3 erstellen
    - Assert: Erfolgreich gespeichert

12. **test_minority_min_count_without_gender_raises_error**
    - Committee mit minority_min_count aber ohne minority_gender
    - Assert: ValidationError

13. **test_minority_min_count_exceeds_total_seats_raises_error**
    - Committee mit minority_min_count > total_seats
    - Assert: ValidationError

14. **test_substitute_logic_enabled**
    - Committee mit substitute_logic_enabled=True erstellen
    - Assert: Erfolgreich gespeichert, Flag korrekt

#### Membership-Model Tests

15. **test_membership_creation**
    - Membership mit allen Pflichtfeldern erstellen
    - Assert: user, committee, role, start_date korrekt

16. **test_membership_unique_user_committee**
    - Zwei Memberships für gleichen User + Committee
    - Assert: IntegrityError

17. **test_membership_str_representation**
    - __str__() sollte "User → Committee (Type)" zurückgeben
    - Assert: Format korrekt

18. **test_membership_is_current_active**
    - Mitgliedschaft aktuell gültig (start_date in Vergangenheit, kein end_date)
    - Assert: is_current = True

19. **test_membership_is_current_future**
    - Mitgliedschaft start_date in Zukunft
    - Assert: is_current = False

20. **test_membership_is_current_expired**
    - Mitgliedschaft end_date in Vergangenheit
    - Assert: is_current = False

21. **test_membership_is_current_inactive**
    - Mitgliedschaft is_active=False
    - Assert: is_current = False

22. **test_external_member_not_in_main_committee**
    - Externes Ausschussmitglied erstellen
    - Versuch gleichzeitig im Hauptgremium zu sein
    - Assert: ValidationError

23. **test_external_member_no_election_info**
    - Externes Mitglied mit election_list_name
    - Assert: ValidationError

24. **test_substitute_with_election_info**
    - Ersatzmitglied mit election_list_name, position, votes
    - Assert: Erfolgreich gespeichert

#### Soft-Delete Tests (Committee)

25. **test_committee_soft_delete**
    - Committee mit delete() löschen
    - Assert: deleted_at gesetzt, deleted_by korrekt
    - Assert: Committee nicht mehr in objects.all()
    - Assert: Committee in all_objects.deleted_only()

26. **test_committee_soft_delete_with_user**
    - Committee mit delete(user=admin) löschen
    - Assert: deleted_by == admin

27. **test_committee_soft_delete_cascades_to_memberships**
    - Committee mit 3 Memberships löschen
    - Assert: Alle 3 Memberships haben deleted_at gesetzt
    - Assert: Return-Wert zeigt 1 Committee + 3 Memberships

28. **test_committee_hard_delete**
    - Committee mit hard_delete() löschen
    - Assert: Komplett aus DB entfernt
    - Assert: Nicht in all_objects.all()

29. **test_committee_queryset_excludes_deleted**
    - 2 Committees erstellen, 1 davon löschen
    - Assert: objects.all() zeigt nur 1
    - Assert: all_objects.all() zeigt beide

30. **test_deleted_committee_not_in_get_active_members**
    - Membership erstellen, dann Committee löschen
    - Assert: get_active_members() leer

#### Soft-Delete Tests (Membership)

31. **test_membership_soft_delete**
    - Membership mit delete() löschen
    - Assert: deleted_at gesetzt, deleted_by korrekt
    - Assert: Membership nicht mehr in objects.all()

32. **test_membership_soft_delete_with_user**
    - Membership mit delete(user=admin) löschen
    - Assert: deleted_by == admin

33. **test_membership_hard_delete**
    - Membership mit hard_delete() löschen
    - Assert: Komplett aus DB entfernt

34. **test_membership_is_current_deleted**
    - Mitgliedschaft löschen
    - Assert: is_current = False (wegen deleted_at)

35. **test_membership_queryset_excludes_deleted**
    - 3 Memberships erstellen, 1 davon löschen
    - Assert: objects.all() zeigt nur 2
    - Assert: all_objects.all() zeigt alle 3

36. **test_soft_delete_manager_alive_method**
    - Memberships erstellen, einige löschen
    - Assert: objects.alive() == objects.all()
    - Assert: all_objects.alive() filtert korrekt

37. **test_soft_delete_manager_deleted_method**
    - Memberships erstellen, einige löschen
    - Assert: all_objects.deleted() zeigt nur gelöschte

**Siehe:** CODE_STYLE_GUIDE.md → "Django Best Practices → Testing"

---

## Phase 2: Admin-Interface

### Ziel
Basis-Verwaltung über Django Admin aktivieren.

### Schritt 2.1: Admin-Klassen

**Datei:** `apps/committees/admin.py`

**2 Admin-Klassen zu implementieren:**

#### 1. CommitteeAdmin

**Decorator:** `@admin.register(Committee)`

**list_display:**
- name, committee_type, parent, total_seats, is_active, created_at, is_deleted_display

**list_filter:**
- committee_type, is_active, quorum_type, personnel_enabled, substitute_logic_enabled, ('deleted_at', admin.EmptyFieldListFilter)

**search_fields:**
- name, description

**fieldsets (gruppiert):**
1. None: name, committee_type, parent, description
2. Konfiguration: total_seats, quorum_type, personnel_enabled
3. Nachrücklogik: substitute_logic_enabled, minority_gender, minority_min_count
4. Status: is_active, created_at
5. Soft-Delete: deleted_at, deleted_by

**readonly_fields:**
- created_at, deleted_at, deleted_by

**Custom Methods:**
- `is_deleted_display(obj)`: @admin.display(boolean=True), return obj.deleted_at is not None

**get_queryset():**
- Verwendet `all_objects.all_with_deleted()` statt `objects.all()`
- select_related('parent', 'deleted_by')

#### 2. MembershipAdmin

**Decorator:** `@admin.register(Membership)`

**list_display:**
- user, committee, role, member_type, is_active, start_date, end_date, is_deleted_display

**list_filter:**
- member_type, is_active, committee__committee_type, start_date, ('deleted_at', admin.EmptyFieldListFilter)

**search_fields:**
- user__first_name, user__last_name, user__email, committee__name

**fieldsets (gruppiert):**
1. None: user, committee, role, member_type
2. Zeitraum: start_date, end_date, is_active
3. Wahlinfo: election_list_name, election_list_position, election_votes
   - Description: "Nur für reguläre Mitglieder und Ersatzmitglieder relevant"
4. Soft-Delete: deleted_at, deleted_by

**autocomplete_fields:**
- user, committee, role

**readonly_fields:**
- deleted_at, deleted_by

**Custom Methods:**
- `is_deleted_display(obj)`: @admin.display(boolean=True), return obj.deleted_at is not None

**get_queryset():**
- Verwendet `all_objects.all_with_deleted()` statt `objects.all()`
- select_related('user', 'committee', 'role', 'deleted_by')
- get_queryset(): select_related('user', 'committee', 'role')

**Autocomplete konfigurieren:**
- CommitteeAdmin: `search_fields = ['name']` hinzufügen
- UserAdmin (accounts): `search_fields = ['email', 'first_name', 'last_name']`
- RoleAdmin (roles): `search_fields = ['name', 'codename']`

**Siehe:** CODE_STYLE_GUIDE.md → "Django Best Practices → Admin"

---

## Phase 3: Berechtigungen & Seed-Daten

### Schritt 3.1: Berechtigungen definieren

**Datei:** `apps/committees/management/commands/seed_committee_permissions.py`

**Funktionalität:**
- Django Management Command
- help = 'Erstellt Standard-Berechtigungen für Committees'

**Berechtigungen zu erstellen (Liste von Tupeln):**

**Committee-Berechtigungen:**
- `committee.create` - "Gremium erstellen"
- `committee.edit` - "Gremium bearbeiten"
- `committee.view` - "Gremiumsdetails einsehen"
- `committee.delete` - "Gremium löschen (soft-delete)"
- `committee.manage_members` - "Mitglieder hinzufügen/entfernen/bearbeiten"
- `committee.view_members` - "Mitgliederliste einsehen"

**Implementierung:**
- Loop über Liste: Permission.objects.get_or_create()
- Category: 'committee'
- Output mit self.stdout.write() und self.style.SUCCESS()
- Counter für erstellte Permissions

**Ausführen:**
```bash
python manage.py seed_committee_permissions
```

---

### Schritt 3.2: SYSTEM_ADMIN-Rolle erweitern

**Datei:** `apps/committees/management/commands/assign_committee_permissions.py`

**Funktionalität:**
- Weist SYSTEM_ADMIN alle committee-Permissions zu
- Via RolePermission.objects.get_or_create()
- Fehlerbehandlung wenn SYSTEM_ADMIN nicht existiert

**Ausführen:**
```bash
python manage.py assign_committee_permissions
```

---

### Schritt 3.3: Permission-Tests

**Datei:** `apps/committees/tests/test_permissions.py`

**Tests zu implementieren:**

1. **test_seed_committee_permissions_command**
   - Management Command ausführen
   - Assert: Alle erwarteten Permissions existieren in DB

2. **test_seed_committee_permissions_idempotent**
   - Command zweimal ausführen
   - Assert: Keine Duplikate, gleiche Anzahl

3. **test_committee_permissions_categorized**
   - Permissions nach category filtern
   - Assert: Alle committee.* Permissions haben category='committee'

4. **test_system_admin_has_committee_permissions**
   - SYSTEM_ADMIN Rolle laden
   - Assert: Hat alle Permissions mit category='committee'

**Siehe:** CODE_STYLE_GUIDE.md → "Django Best Practices → Testing"

---

## Phase 4: Views & Templates

### Ziel
Benutzer-Interface für Gremien- und Mitgliederverwaltung erstellen.

### Schritt 4.1: URL-Konfiguration

**Datei:** `apps/committees/urls.py` erstellen

**app_name:** `'committees'`

**URLs zu definieren:**

**Committee URLs:**
- `''` → CommitteeListView (name='committee_list')
- `'create/'` → CommitteeCreateView (name='committee_create')
- `'<uuid:pk>/'` → CommitteeDetailView (name='committee_detail')
- `'<uuid:pk>/edit/'` → CommitteeUpdateView (name='committee_update')
- `'<uuid:pk>/delete/'` → CommitteeDeleteView (name='committee_delete')

**Member URLs:**
- `'<uuid:committee_id>/members/'` → MemberListView (name='member_list')
- `'<uuid:committee_id>/members/add/'` → MemberAddView (name='member_add')
- `'<uuid:committee_id>/members/<uuid:pk>/edit/'` → MemberEditView (name='member_edit')
- `'<uuid:committee_id>/members/<uuid:pk>/remove/'` → MemberRemoveView (name='member_remove')

**Substitute URLs:**
- `'<uuid:committee_id>/substitutes/'` → SubstituteListView (name='substitute_list')

**config/urls.py ergänzen:**
- `'committees/'` → include('apps.committees.urls')

---

### Schritt 4.2: Custom Mixins

**Datei:** `apps/committees/mixins.py` erstellen

**2 Mixins zu implementieren:**

#### 1. CommitteePermissionMixin

**Extends:** UserPassesTestMixin

**Funktionalität:**
- Prüft ob User Berechtigung für Committee-Aktionen hat
- Attribut: `required_permission` (Override in Subclass)
- test_func(): Superuser = True, sonst is_staff (TODO: Später über roles/permissions-System)

#### 2. CommitteeContextMixin

**Funktionalität:**
- Fügt committee zum Context hinzu
- get_committee(): Holt Committee via committee_id oder pk aus URL-kwargs
- get_context_data(): Fügt 'committee' zum Context hinzu falls nicht vorhanden

**Siehe:** CODE_STYLE_GUIDE.md → "Django Best Practices → Mixins"

---

### Schritt 4.3: Committee Views

**Datei:** `apps/committees/views.py`

**5 Views für Committees:**

#### 1. CommitteeListView

**Extends:** LoginRequiredMixin, CommitteePermissionMixin, ListView

**Funktionalität:**
- Zeigt alle aktiven Committees
- Gruppiert nach committee_type (MAIN vs. andere)
- Pagination: 20 pro Seite

**Attribute:**
- model: Committee
- template_name: 'committees/committee_list.html'
- context_object_name: 'committees'
- required_permission: 'committee.view'
- paginate_by: 20

**get_queryset():**
- Filter: is_active=True
- select_related('parent')
- order_by('committee_type', 'name')

**get_context_data():**
- Gruppierung: main_committees, subcommittees

#### 2. CommitteeDetailView

**Extends:** LoginRequiredMixin, CommitteePermissionMixin, CommitteeContextMixin, DetailView

**Funktionalität:**
- Zeigt Committee-Details
- Member-Statistiken
- Letzte 5 Mitglieder

**Attribute:**
- model: Committee
- template_name: 'committees/committee_detail.html'
- context_object_name: 'committee'
- required_permission: 'committee.view'

**get_context_data():**
- active_members_count, substitute_count, external_count
- recent_members (letzte 5)

#### 3. CommitteeCreateView

**Extends:** LoginRequiredMixin, CommitteePermissionMixin, CreateView

**Funktionalität:**
- Erstellt neues Committee
- Filtert parent-Choices auf MAIN committees

**Attribute:**
- model: Committee
- template_name: 'committees/committee_form.html'
- required_permission: 'committee.create'
- fields: name, committee_type, parent, description, total_seats, quorum_type, personnel_enabled, substitute_logic_enabled, minority_gender, minority_min_count

**get_form():**
- Filter parent.queryset: committee_type='MAIN', is_active=True

**get_success_url():**
- Redirect zu committee_detail
- Success-Message

#### 4. CommitteeUpdateView

**Extends:** LoginRequiredMixin, CommitteePermissionMixin, CommitteeContextMixin, UpdateView

**Funktionalität:**
- Bearbeitet Committee
- committee_type und parent NICHT editierbar (nur bei Create)

**Attribute:**
- model: Committee
- template_name: 'committees/committee_form.html'
- required_permission: 'committee.edit'
- fields: name, description, total_seats, quorum_type, personnel_enabled, substitute_logic_enabled, minority_gender, minority_min_count, is_active

**get_success_url():**
- Redirect zu committee_detail
- Success-Message

#### 5. CommitteeDeleteView

**Extends:** LoginRequiredMixin, CommitteePermissionMixin, CommitteeContextMixin, DeleteView

**Funktionalität:**
- Soft-Delete für Committee
- Bestätigungs-Dialog
- Zeigt Warnung über kaskadierendes Löschen (Anzahl Memberships)

**Attribute:**
- model: Committee
- template_name: 'committees/committee_confirm_delete.html'
- required_permission: 'committee.delete'

**get_context_data():**
- memberships_count: Anzahl betroffener Memberships

**delete():**
- **WICHTIG:** Soft-Delete statt Hard-Delete
- Ruft `deleted_count, details = self.object.delete(user=request.user)` auf
- Success-Message zeigt: Committee-Name, Anzahl Gremien, Anzahl Memberships (aus `details` dict)

**get_success_url():**
- Redirect zu committee_list

**Siehe:** CODE_STYLE_GUIDE.md → "Django Best Practices → Views"

---

### Schritt 4.4: Membership Views

**Datei:** `apps/committees/views.py` ergänzen

**4 Views für Memberships:**

#### 1. MemberListView

**Extends:** LoginRequiredMixin, CommitteePermissionMixin, CommitteeContextMixin, ListView

**Funktionalität:**
- Zeigt alle Mitglieder eines Committees
- Gruppiert nach member_type (REGULAR, SUBSTITUTE, EXTERNAL)
- Pagination: 50 pro Seite

**Attribute:**
- model: Membership
- template_name: 'committees/member_list.html'
- context_object_name: 'memberships'
- required_permission: 'committee.view_members'
- paginate_by: 50

**get_queryset():**
- Filter: committee=get_committee(), is_active=True
- select_related('user', 'role')
- order_by('member_type', 'user__last_name')

**get_context_data():**
- Gruppierung: regular_members, substitute_members, external_members

#### 2. MemberAddView

**Extends:** LoginRequiredMixin, CommitteePermissionMixin, CommitteeContextMixin, CreateView

**Funktionalität:**
- Fügt Mitglied zu Committee hinzu
- Verwendet MembershipForm (siehe Schritt 4.5)

**Attribute:**
- model: Membership
- template_name: 'committees/member_form.html'
- form_class: MembershipForm
- required_permission: 'committee.manage_members'

**get_form_kwargs():**
- Übergibt committee zum Form

**form_valid():**
- Setzt form.instance.committee
- Success-Message

**get_success_url():**
- Redirect zu member_list

#### 3. MemberEditView

**Extends:** LoginRequiredMixin, CommitteePermissionMixin, CommitteeContextMixin, UpdateView

**Funktionalität:**
- Bearbeitet Mitgliedschafts-Details
- Verwendet MembershipForm

**Attribute:**
- model: Membership
- template_name: 'committees/member_form.html'
- form_class: MembershipForm
- required_permission: 'committee.manage_members'

**get_queryset():**
- Filter: committee=get_committee()

**get_form_kwargs():**
- Übergibt committee zum Form

**get_success_url():**
- Redirect zu member_list
- Success-Message

#### 4. MemberRemoveView

**Extends:** LoginRequiredMixin, CommitteePermissionMixin, CommitteeContextMixin, DeleteView

**Funktionalität:**
- Entfernt Mitglied (Soft-Delete: is_active=False)
- Bestätigungs-Dialog

**Attribute:**
- model: Membership
- template_name: 'committees/member_confirm_remove.html'
- required_permission: 'committee.manage_members'

**get_queryset():**
- Filter: committee=get_committee()

**delete():**
- **Soft-Delete:** Ruft `self.object.delete(user=request.user)` auf
- Success-Message mit User-Name

**get_success_url():**
- Redirect zu member_list

---

### Schritt 4.5: Forms

**Datei:** `apps/committees/forms.py` erstellen

**1 Form zu implementieren:**

#### MembershipForm

**Extends:** ModelForm

**Meta:**
- model: Membership
- fields: user, role, member_type, start_date, end_date, election_list_name, election_list_position, election_votes
- widgets: Bootstrap-Classes für alle Felder, DateInput mit type='date'

**__init__(committee=None):**
- Filter role.queryset: role_type='COMMITTEE'
- Default role basierend auf member_type (MEMBER, SUBSTITUTE, EXTERNAL_MEMBER)
- Help-Texts für election_* Felder

**clean():**
- Prüft ob User bereits Mitglied des Committees ist (unique constraint)
- ValidationError wenn Duplikat

**Siehe:** CODE_STYLE_GUIDE.md → "Django Best Practices → Forms"

---

### Schritt 4.6: Templates

**Templates zu erstellen:**

**Basis-Template:**
1. **`committees/base_committee.html`**
   - Extends base.html
   - Breadcrumb-Navigation
   - Block: breadcrumb, committee_content

**Committee-Templates:**
2. **`committees/committee_list.html`**
   - Extends base_committee.html
   - Zeigt Hauptgremium (Card) und Ausschüsse (Grid)
   - Button: "Neues Gremium" (wenn Permission)

3. **`committees/committee_detail.html`**
   - Extends base_committee.html
   - Details-Card: Typ, Parent, Sitze, Quorum, Status
   - Mitglieder-Card: Letzte 5 + Link zu "Alle anzeigen"
   - Statistik-Sidebar: Member-Counts
   - Subcommittees-Liste (falls vorhanden)

4. **`committees/committee_form.html`**
   - Extends base_committee.html
   - Form mit crispy-forms
   - Buttons: Speichern, Abbrechen

5. **`committees/committee_confirm_delete.html`**
   - Extends base_committee.html
   - Bestätigungs-Dialog mit Warnung (Soft-Delete)
   - Zeigt Anzahl betroffener Memberships
   - Hinweis: "Gremium und alle Mitgliedschaften werden als gelöscht markiert"
   - Buttons: Löschen (danger), Abbrechen

**Member-Templates:**
6. **`committees/member_list.html`**
   - Extends base_committee.html
   - 3 Tabellen: Reguläre Mitglieder, Ersatzmitglieder, Externe Mitglieder
   - Spalten: Name, Rolle, Seit, Wahlliste, Listenplatz, Aktionen
   - Button: "Mitglied hinzufügen" (wenn Permission)

7. **`committees/member_form.html`**
   - Extends base_committee.html
   - Form mit crispy-forms
   - Buttons: Speichern, Abbrechen

8. **`committees/member_confirm_remove.html`**
   - Extends base_committee.html
   - Bestätigungs-Dialog mit Warnung (Soft-Delete)
   - Buttons: Entfernen (danger), Abbrechen

**Alle Templates:** Bootstrap 5 Styling, Bootstrap Icons

**Siehe:** CODE_STYLE_GUIDE.md → "Django Best Practices → Templates"

---

### Schritt 4.7: View-Tests

**Datei:** `apps/committees/tests/test_views.py`

**Tests zu implementieren:**

#### Committee View Tests

1. **test_committee_list_requires_login**
   - Unauthenticated User greift auf Committee-Liste zu
   - Assert: Redirect zu Login

2. **test_committee_list_accessible**
   - Authenticated User mit Permission
   - Assert: Status 200, Committees im Context

3. **test_committee_detail_view**
   - Committee-Detail anzeigen
   - Assert: Status 200, Member-Counts korrekt

4. **test_committee_create_requires_permission**
   - User ohne Permission versucht Committee zu erstellen
   - Assert: 403 Forbidden

5. **test_committee_create_success**
   - Admin erstellt neues Committee
   - Assert: Committee erstellt, Redirect zu Detail

6. **test_committee_create_validation_main_with_parent**
   - MAIN Committee mit parent erstellen
   - Assert: Form-Error

7. **test_committee_create_validation_sub_without_parent**
   - SUBCOMMITTEE ohne parent erstellen
   - Assert: Form-Error

8. **test_committee_update_success**
   - Admin ändert Committee-Daten
   - Assert: Änderungen gespeichert

#### Membership View Tests

9. **test_member_list_view**
   - Mitgliederliste anzeigen
   - Assert: Alle Mitglieder im Context, gruppiert nach Type

10. **test_member_add_requires_permission**
    - User ohne Permission versucht Mitglied hinzuzufügen
    - Assert: 403 Forbidden

11. **test_member_add_success**
    - Admin fügt Mitglied hinzu
    - Assert: Membership erstellt, Redirect zu Member-List

12. **test_member_add_duplicate_user**
    - Versuch User zweimal zum gleichen Committee hinzuzufügen
    - Assert: Form-Error

13. **test_member_edit_success**
    - Admin ändert Mitgliedschafts-Daten
    - Assert: Änderungen gespeichert

14. **test_member_remove_soft_delete**
    - Admin entfernt Mitglied
    - Assert: deleted_at gesetzt, deleted_by == request.user
    - Assert: Membership nicht mehr in objects.all()

#### Soft-Delete View Tests

15. **test_committee_delete_requires_permission**
    - User ohne Permission versucht Committee zu löschen
    - Assert: 403 Forbidden

16. **test_committee_delete_view_shows_confirmation**
    - Admin greift auf Delete-View zu
    - Assert: Confirmation-Page, zeigt memberships_count

17. **test_committee_delete_soft_deletes_committee**
    - Admin löscht Committee
    - Assert: deleted_at gesetzt, deleted_by == admin
    - Assert: Committee nicht mehr in objects.all()
    - Assert: Redirect zu committee_list

18. **test_committee_delete_cascades_to_memberships**
    - Committee mit 5 Memberships löschen
    - Assert: Alle 5 Memberships haben deleted_at gesetzt
    - Assert: Success-Message zeigt korrekte Anzahl

19. **test_member_remove_tracks_user**
    - Admin entfernt Mitglied
    - Assert: deleted_by == admin
    - Assert: deleted_at innerhalb letzter 5 Sekunden

20. **test_deleted_committee_not_in_list_view**
    - 3 Committees erstellen, 1 löschen
    - Assert: List-View zeigt nur 2
    - Assert: Detail-View des gelöschten gibt 404

21. **test_deleted_membership_not_in_member_list**
    - 5 Memberships erstellen, 2 löschen
    - Assert: Member-List zeigt nur 3

**Siehe:** CODE_STYLE_GUIDE.md → "Django Best Practices → Testing"

---

## Phase 5: Helper-Funktionen & Erweiterte Features

### Ziel
Spezielle Funktionen für Ersatzmitglieder-Vorschläge und externe Zugriffsbeschränkungen.

### Schritt 5.1: Helper-Funktionen

**Datei:** `apps/committees/utils.py`

**3 Helper-Funktionen zu implementieren:**

#### 1. get_substitute_suggestions

**Signatur:** `get_substitute_suggestions(absent_member, meeting=None)`

**Zweck:** Ersatzmitglieder-Vorschläge für abwesendes Mitglied

**Algorithmus:**
1. Prüft ob committee.substitute_logic_enabled=True (sonst return empty QuerySet)
2. Gleiche Wahlliste (election_list_name)
3. Sortiert nach Listenplatz und Stimmen
4. Geschlechterquote-Prüfung wenn committee.minority_gender gesetzt:
   - Zählt aktuelles Minderheitengeschlecht im Gremium
   - Wenn < minority_min_count: Priorisiert Ersatzmitglieder mit Minderheitengeschlecht
5. TODO: Verfügbarkeit-Check (Kalender-Integration in späterer Phase)

**Returns:** QuerySet of Membership

**Siehe:** CODE_STYLE_GUIDE.md → "Clean Code Principles → Functions"

#### 2. check_external_member_access

**Signatur:** `check_external_member_access(user, resource)`

**Zweck:** Prüft ob externes Mitglied Zugriff auf Resource hat

**Logik:**
- Superuser/Staff: immer True
- Nicht-externe Mitglieder: True
- Externe Mitglieder: True nur wenn resource.committee == user's committee

**Returns:** bool

**Wird verwendet in:** meetings, documents, minutes (spätere Apps)

#### 3. suggest_default_role

**Signatur:** `suggest_default_role(member_type)`

**Zweck:** Schlägt Standard-Rolle basierend auf member_type vor

**Mapping:**
- REGULAR → MEMBER
- SUBSTITUTE → SUBSTITUTE
- EXTERNAL → EXTERNAL_MEMBER

**Returns:** Role or None

**Wird verwendet in:** MembershipForm initial value

---

### Schritt 5.2: SubstituteListView

**Datei:** `apps/committees/views.py` ergänzen

**1 zusätzliche View:**

#### SubstituteListView

**Extends:** LoginRequiredMixin, CommitteePermissionMixin, CommitteeContextMixin, ListView

**Funktionalität:**
- Zeigt Ersatzmitglieder gruppiert nach Wahlliste
- Sortiert nach Listenplatz und Stimmen

**Attribute:**
- model: Membership
- template_name: 'committees/substitute_list.html'
- context_object_name: 'substitutes'
- required_permission: 'committee.view_members'

**get_queryset():**
- Filter: committee, member_type='SUBSTITUTE', is_active=True
- select_related('user', 'role')
- order_by('election_list_name', 'election_list_position', '-election_votes')

**get_context_data():**
- Gruppierung: grouped_substitutes (Dict mit election_list_name als Key)

**Template:**
- **`committees/substitute_list.html`**
- Extends base_committee.html
- Zeigt Tabellen pro Wahlliste
- Spalten: Listenplatz, Name, Geschlecht, Stimmen, Seit

---

### Schritt 5.3: Helper-Tests

**Datei:** `apps/committees/tests/test_helpers.py`

**Tests zu implementieren:**

1. **test_get_substitute_suggestions_same_list**
   - Ersatzmitglieder von gleicher Wahlliste
   - Assert: Korrekte Reihenfolge (Listenplatz, Stimmen)

2. **test_get_substitute_suggestions_ordering**
   - Mehrere Ersatzmitglieder mit unterschiedlichen Listenplätzen
   - Assert: Sortierung korrekt

3. **test_get_substitute_suggestions_empty**
   - Keine Ersatzmitglieder vorhanden
   - Assert: Leeres QuerySet

4. **test_check_external_member_access_external_user**
   - Externes Mitglied greift auf eigenes Committee zu
   - Assert: Access = True

5. **test_check_external_member_access_external_user_wrong_committee**
   - Externes Mitglied greift auf anderes Committee zu
   - Assert: Access = False

6. **test_check_external_member_access_regular_user**
   - Reguläres Mitglied
   - Assert: Access = True

7. **test_check_external_member_access_superuser**
   - Superuser
   - Assert: Access = True (immer)

8. **test_suggest_default_role_regular**
   - member_type='REGULAR'
   - Assert: Returns MEMBER role

9. **test_suggest_default_role_substitute**
   - member_type='SUBSTITUTE'
   - Assert: Returns SUBSTITUTE role

10. **test_suggest_default_role_external**
    - member_type='EXTERNAL'
    - Assert: Returns EXTERNAL_MEMBER role

11. **test_get_substitute_suggestions_disabled_logic**
    - Committee mit substitute_logic_enabled=False
    - Assert: get_substitute_suggestions() gibt leeres QuerySet zurück

12. **test_get_substitute_suggestions_with_minority_gender**
    - Committee mit minority_gender='F', minority_min_count=3
    - Aktuell nur 2 Frauen im Gremium
    - Assert: Weibliche Ersatzmitglieder werden priorisiert

13. **test_get_substitute_suggestions_minority_quota_fulfilled**
    - Committee mit minority_gender='F', minority_min_count=3
    - Aktuell 3 Frauen im Gremium (Quote erfüllt)
    - Assert: Normale Reihenfolge nach Listenplatz

**Siehe:** CODE_STYLE_GUIDE.md → "Django Best Practices → Testing"

---

### Schritt 5.4: HTMX-Features (Progressive Enhancement)

**Ziel:** Live-Suche und Inline-Bearbeitung für bessere UX

#### URLs ergänzen

**Datei:** `apps/committees/urls.py` ergänzen

**Neue HTMX-Endpoints:**
- `'<uuid:committee_id>/members/search/'` → MemberSearchView (name='member_search')
- `'<uuid:committee_id>/members/<uuid:pk>/inline-edit/'` → MemberInlineEditView (name='member_inline_edit')

#### View 1: MemberSearchView

**Datei:** `apps/committees/views.py` ergänzen

**Extends:** LoginRequiredMixin, CommitteePermissionMixin, CommitteeContextMixin, ListView

**Funktionalität:**
- Live-Suche in Mitgliederliste via HTMX
- Filtert nach Name, E-Mail
- Gibt nur HTML-Fragment zurück (_member_row.html)

**Attribute:**
- model: Membership
- template_name: 'committees/_member_list_rows.html'
- context_object_name: 'memberships'
- required_permission: 'committee.view_members'

**get_queryset():**
- Filter: committee=get_committee(), is_active=True
- Filter nach Suchbegriff (query parameter 'q')
- Search in: user__first_name, user__last_name, user__email
- select_related('user', 'role')
- order_by('member_type', 'user__last_name')

#### View 2: MemberInlineEditView

**Datei:** `apps/committees/views.py` ergänzen

**Funktionalität:**
- Inline-Bearbeitung von Mitgliedschafts-Details
- GET: Gibt Edit-Form als Fragment zurück
- POST: Speichert und gibt aktualisierte Zeile zurück

**GET:**
- template_name: 'committees/_member_edit_form.html'
- Zeigt Form-Felder für: role, member_type, start_date, end_date

**POST:**
- Validiert und speichert Änderungen
- template_name: 'committees/_member_row.html'
- Gibt aktualisierte Tabellenzeile zurück

#### Templates für HTMX

**3 Partials zu erstellen:**

1. **`committees/_member_list_rows.html`**
   - Loop über memberships
   - Include: `_member_row.html` für jede Zeile

2. **`committees/_member_row.html`**
   - Einzelne Tabellenzeile (<tr>)
   - Spalten: Name, Rolle, Seit, Wahlliste, Aktionen
   - Aktionen: Edit-Button mit hx-get für Inline-Edit

3. **`committees/_member_edit_form.html`**
   - Inline-Edit-Form in <tr>
   - Form-Felder als <td> Elemente
   - Buttons: Speichern (hx-post), Abbrechen

#### member_list.html erweitern

**Datei:** `committees/member_list.html` anpassen

**Änderungen:**
- Suchfeld mit hx-get="/committees/<id>/members/search/" hinzufügen
- hx-trigger="keyup changed delay:300ms"
- hx-target="#member-table-body"
- Tabelle: <tbody id="member-table-body"> mit {% include '_member_list_rows.html' %}

#### HTMX einbinden

**Datei:** `templates/base.html` ergänzen (falls noch nicht vorhanden)

- HTMX CDN im <head>: `<script src="https://unpkg.com/htmx.org@1.9.10"></script>`

**Siehe:** CODE_STYLE_GUIDE.md → "Django Best Practices → HTMX Integration"

---

### Schritt 5.5: HTMX-Tests

**Datei:** `apps/committees/tests/test_views.py` ergänzen

**Tests zu implementieren:**

15. **test_member_search_view**
    - GET mit query parameter 'q=Max'
    - Assert: Nur Mitglieder mit 'Max' im Namen/Email

16. **test_member_search_empty_query**
    - GET ohne query parameter
    - Assert: Alle Mitglieder

17. **test_member_inline_edit_get**
    - GET auf inline-edit endpoint
    - Assert: Returns edit form fragment

18. **test_member_inline_edit_post_success**
    - POST mit validen Daten
    - Assert: Membership aktualisiert, returns updated row

19. **test_member_inline_edit_post_invalid**
    - POST mit invaliden Daten
    - Assert: Returns form with errors

20. **test_htmx_fragments_use_correct_templates**
    - Prüft dass HTMX-Views die richtigen Partial-Templates verwenden
    - Assert: _member_row.html, _member_edit_form.html, _member_list_rows.html

**Siehe:** CODE_STYLE_GUIDE.md → "Django Best Practices → Testing"

---

## Validierung nach jeder Phase

### Checkliste nach Abschluss einer Phase:

**1. Migrations prüfen:**
```bash
python manage.py makemigrations --check --dry-run
python manage.py showmigrations committees
```

**2. Admin-Interface testen:**
- http://localhost:8000/admin/committees/
- Alle Models sichtbar?
- CRUD-Operationen funktionieren?
- Autocomplete funktioniert?

**3. URLs testen:**
```bash
python manage.py show_urls | grep committees
```

**4. Alle Tests ausführen:**
```bash
# Alle Tests
pytest apps/committees/tests/

# Nur Model-Tests
pytest apps/committees/tests/test_models.py

# Nur View-Tests
pytest apps/committees/tests/test_views.py

# Mit Coverage
pytest --cov=apps.committees --cov-report=html
```

**5. Frontend testen:**
- Login als Superuser
- Committee erstellen (MAIN) mit Minderheitengeschlecht-Konfiguration
- Nachrücklogik aktivieren/deaktivieren testen
- Subcommittee erstellen
- Mitglieder hinzufügen
- Ersatzmitglieder-Liste anzeigen
- HTMX-Features testen:
  - Live-Suche in Mitgliederliste
  - Inline-Bearbeitung von Mitgliedschaften

**6. Code-Qualität prüfen:**
```bash
# Type-Checking
mypy apps/committees

# Linting
ruff check apps/committees
```

**Siehe:** CODE_STYLE_GUIDE.md → "Django Best Practices → Testing"

---

## Deployment-Vorbereitung

### Konstanten in settings definieren

**In `config/settings/base.py`:**

```python
# Committee Settings
DEFAULT_QUORUM_TYPE = 'SIMPLE_MAJORITY'
MIN_COMMITTEE_SEATS = 1
MAX_COMMITTEE_SEATS = 100

# Membership Settings
MEMBERSHIP_START_DATE_REQUIRED = True
ELECTION_LIST_REQUIRED_FOR_SUBSTITUTES = True
```

**Siehe:** CODE_STYLE_GUIDE.md → "Clean Code Principles → Use Constants"

### Initial Data Seeds

**Commands in richtiger Reihenfolge ausführen:**

```bash
# 1. Permissions erstellen
python manage.py seed_committee_permissions

# 2. SYSTEM_ADMIN Permissions zuweisen
python manage.py assign_committee_permissions

# 3. Optional: Demo-Daten erstellen (nur Development)
# python manage.py seed_demo_committees
```

---

## Zusammenfassung

### Implementierungs-Reihenfolge:

1. ✅ Phase 1: Projekt-Setup & Basis-Modelle (Committee, Membership)
2. ✅ Phase 2: Admin-Interface
3. ✅ Phase 3: Berechtigungen & Seed-Daten
4. ✅ Phase 4: Views & Templates
5. ✅ Phase 5: Helper-Funktionen & Erweiterte Features
   - Schritt 5.1: Helper-Funktionen (substitute_suggestions, external_access, default_role)
   - Schritt 5.2: SubstituteListView
   - Schritt 5.3: Helper-Tests
   - Schritt 5.4: HTMX-Features (Live-Suche, Inline-Edit)
   - Schritt 5.5: HTMX-Tests

### Code-Qualität sicherstellen:

- **Clean Code:** Siehe CODE_STYLE_GUIDE.md
- **Type Hints:** Für alle Funktionen
- **Docstrings:** Google Style, Pflicht
- **DRY:** Keine Code-Duplikation
- **Tests:** Für ALLE Funktionen und Views (nicht optional!)
- **Test Coverage:** Minimum 80% anstreben

### Wichtige Referenzen:

- CODE_STYLE_GUIDE.md (Alle Code-Beispiele)
- docs/apps/03_committees.md (Detaillierte Anforderungen)
- docs/06_berechtigungskonzept.md (Permission-Matrix)

### Besondere Validierungen:

- ✅ Hierarchie-Validierung (MAIN ohne parent, Sub mit parent)
- ✅ Zirkelbezug-Prüfung
- ✅ Externe Mitglieder-Validierung
- ✅ Eindeutigkeit User + Committee
- ✅ Minderheitengeschlecht-Konfiguration (min_count ≤ total_seats)
- ✅ Geschlechterquote bei Ersatzmitglieder-Vorschlägen

### Neue Features:

- ✅ **Nachrücklogik-Steuerung:** Boolean-Flag pro Gremium
- ✅ **Minderheitengeschlecht:** Konfigurierbar mit Mindestanzahl
- ✅ **HTMX Live-Suche:** Echtzeit-Filterung der Mitgliederliste
- ✅ **HTMX Inline-Edit:** Mitgliedschaften direkt in der Liste bearbeiten
- ✅ **Geschlechterquote-Prüfung:** In `get_substitute_suggestions()` integriert
- ✅ **Soft-Delete System:** Vollständiges Soft-Delete für Committee & Membership
  - Felder: `deleted_at`, `deleted_by`
  - Custom Manager/QuerySet für automatisches Filtern
  - Kaskadierendes Delete (Committee → Memberships)
  - Admin-Sichtbarkeit mit Filter
  - User-Tracking (wer hat gelöscht)
  - Hard-Delete nur über Admin möglich

---

## Nächste Schritte nach Committees

Nach erfolgreicher Implementierung:
1. **Meetings-App** (verwendet Committees)
2. **Attendance-App** (verwendet Meetings + Ersatzmitglieder-Logik)
3. **Weitere Apps** gemäß Projektplan

### Integration mit späteren Apps:

**Ersatzmitglieder-Vorschläge werden verwendet in:**
- `attendance`-App: Automatische Vorschläge bei Abwesenheit
- `meetings`-App: Teilnehmerverwaltung

**Externe Mitglieder-Zugriff wird geprüft in:**
- `meetings`-App: Zugriff auf Sitzungen
- `documents`-App: Zugriff auf Dokumente
- `minutes`-App: Zugriff auf Protokolle
