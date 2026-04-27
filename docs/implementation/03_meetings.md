# Implementierungsplan: Meetings App

## Übersicht

Dieser Plan beschreibt die Implementierung der `meetings`-App für die Sitzungsverwaltung (Online, Hybrid, Präsenz). Diese App baut auf den bereits implementierten `accounts`, `roles` und `committees` Apps auf.

### ⚠️ Code-Konventionen

**Wichtig:** Alle Code-Implementierungen folgen den Richtlinien in `docs/implementation/CODE_STYLE_GUIDE.md`

Kurzübersicht:
- ✅ **Code (Python) = Englisch** (Variablen, Funktionen, Klassen, Kommentare)
- ✅ **User-sichtbare Strings = Deutsch** (verbose_name, Labels, Templates, Messages)

**📖 Vollständige Beispiele:** Siehe `docs/implementation/CODE_STYLE_GUIDE.md`

### Abhängigkeiten

```
accounts ──┐
           │
roles ─────┼──→ meetings
           │
committees ┘
```

**Abhängigkeiten:**
- `accounts` definiert **User-Modell** → benötigt für chair, clerk, created_by (ForeignKey)
- `committees` definiert **Committee-Modell** → benötigt für Meeting.committee (ForeignKey)
- `roles` definiert **Berechtigungen** → benötigt für Permission-System
- `meetings` ist die **Basis für weitere Apps** (agendas, minutes, attendance, resolutions)

**Fazit:** meetings kann **sequenziell nach accounts, roles & committees** implementiert werden.

---

## Strategie: Sequenzielle Phasen-Implementierung

### Prinzip
Die App wird in logischen Schritten aufgebaut:
1. Basis-Modell (Meeting) mit Validierung
2. Admin-Interface & Berechtigungen
3. Views und Templates mit dynamischen Formularen
4. Status-Workflow & Business Logic
5. E-Mail-Integration & Erweiterte Features

### Vorteile
- ✅ Klare Abhängigkeiten zu accounts, roles und committees
- ✅ Schrittweise Erweiterung mit Tests
- ✅ Frühe Tests der Kern-Funktionalität
- ✅ Modularer Aufbau

---

## Phase 1: Projekt-Setup & Basis-Modell

### Ziel
App-Struktur erstellen und Meeting-Modell mit vollständiger Validierung implementieren.

### Schritt 1.1: Projekt-Setup

**App erstellen:**
```bash
python manage.py startapp meetings apps/meetings
```

**Verzeichnisstruktur anlegen:**
```bash
# Tests
mkdir -p apps/meetings/tests
touch apps/meetings/tests/{__init__.py,test_models.py,test_views.py,test_forms.py,test_permissions.py,test_utils.py}

# Templates & Static
mkdir -p apps/meetings/templates/meetings apps/meetings/static/meetings

# Management Commands
mkdir -p apps/meetings/management/commands
touch apps/meetings/management/__init__.py apps/meetings/management/commands/__init__.py

# Utils
touch apps/meetings/utils.py
touch apps/meetings/mixins.py
```

**App registrieren:**
- In `config/settings/base.py` → `LOCAL_APPS` ergänzen:
  - `"apps.meetings"`

---

### Schritt 1.2: Meeting-Modell

**Datei:** `apps/meetings/models.py`

**Funktionalität:**
- Sitzungsverwaltung mit drei Sitzungstypen (ONLINE, HYBRID, IN_PERSON)
- Status-Workflow (DRAFT → SENT → IN_PROGRESS → COMPLETED)
- Automatische Sitzungsnummer pro Committee und Jahr
- Dynamische Validierung basierend auf meeting_type
- **Vorsitz und Protokollführung:** Dynamische Auswahl aus Committee-Mitgliedern
  - Default: User mit entsprechender Rolle (z.B. CHAIR für chair_role)
  - Änderbar: Kann auf jedes aktive Committee-Mitglied gesetzt werden
  - Ermöglicht flexible Vertretungen (z.B. "2. Stellvertreter")

**MEETING_TYPE_CHOICES:**
- `('ONLINE', 'Online-Sitzung')`
- `('HYBRID', 'Hybrid-Sitzung')`
- `('IN_PERSON', 'Präsenzsitzung')`

**STATUS_CHOICES:**
- `('DRAFT', 'Entwurf')`
- `('SENT', 'Einladung versendet')`
- `('IN_PROGRESS', 'In Bearbeitung')`
- `('COMPLETED', 'Abgeschlossen')`

**Felder:**
- `id`: UUIDField (PK, default=uuid.uuid4)
- `committee`: ForeignKey('committees.Committee', CASCADE, related_name='meetings')
- `title`: CharField(300, verbose_name='Titel')
- `meeting_number`: CharField(20, verbose_name='Sitzungsnummer')
- `date`: DateField(verbose_name='Datum')
- `start_time`: TimeField(verbose_name='Beginn')
- `end_time`: TimeField(null=True, blank=True, verbose_name='Geplantes Ende')
- `actual_start_time`: TimeField(null=True, blank=True, verbose_name='Tatsächlicher Beginn')
- `actual_end_time`: TimeField(null=True, blank=True, verbose_name='Tatsächliches Ende')
- `meeting_type`: CharField(10, choices=MEETING_TYPE_CHOICES, default='IN_PERSON')
- `location_url`: URLField(500, blank=True, verbose_name='Online-Link')
- `location_name`: CharField(200, blank=True, verbose_name='Ortsbezeichnung')
- `location_street`: CharField(200, blank=True, verbose_name='Straße')
- `location_zip`: CharField(10, blank=True, verbose_name='PLZ')
- `location_city`: CharField(100, blank=True, verbose_name='Stadt')
- `location_room`: CharField(100, blank=True, verbose_name='Raum')
- `status`: CharField(20, choices=STATUS_CHOICES, default='DRAFT')
- `is_quorate`: BooleanField(null=True, blank=True, verbose_name='Beschlussfähig')
- `chair`: ForeignKey('accounts.User', SET_NULL, null=True, blank=True, related_name='chaired_meetings', verbose_name='Vorsitz')
  - **Wichtig:** Dynamische Auswahl aus allen aktiven Committee-Mitgliedern
  - **Standard:** User mit meeting.lead_meeting Permission (z.B. CHAIR-Rolle)
  - **Änderbar:** Kann bei Bedarf auf jedes Mitglied gesetzt werden (z.B. "2. Stellvertreter")
- `clerk`: ForeignKey('accounts.User', SET_NULL, null=True, blank=True, related_name='clerked_meetings', verbose_name='Protokollführung')
  - **Wichtig:** Dynamische Auswahl aus allen aktiven Committee-Mitgliedern
  - **Standard:** User mit entsprechender Permission
  - **Änderbar:** Kann bei Bedarf geändert werden
- `created_by`: ForeignKey('accounts.User', SET_NULL, null=True, related_name='created_meetings', verbose_name='Erstellt von')
- `created_at`: DateTimeField(default=timezone.now)
- `updated_at`: DateTimeField(auto_now=True)
- `sent_at`: DateTimeField(null=True, blank=True, verbose_name='Einladung versendet am')

**Meta:**
- verbose_name: 'Sitzung'
- verbose_name_plural: 'Sitzungen'
- ordering: `['-date', '-start_time']`
- unique_together: `[['committee', 'meeting_number']]`
- indexes:
  - `['committee', 'date']`
  - `['status']`
  - `['date', 'start_time']`

**Methoden:**
- `__str__()`: Return f"{meeting_number} - {title} ({date})"
- `clean()`: Umfassende Validierung (siehe unten)
- `save()`: Auto-generate meeting_number wenn neu (siehe unten)
- `get_absolute_url()`: Return reverse('meetings:meeting_detail', kwargs={'pk': self.pk})
- `get_full_location()`: Property - Gibt formatierte Adresse zurück (siehe unten)
- `is_upcoming()`: Property - Prüft ob Datum in Zukunft liegt
- `is_past()`: Property - Prüft ob Datum in Vergangenheit liegt
- `is_editable()`: Property - Prüft ob bearbeitbar (status='DRAFT')
- `is_deletable()`: Property - Prüft ob löschbar (status='DRAFT')
- `can_send_invitation()`: Property - Prüft ob Einladung versendbar (status='DRAFT')
- `can_complete()`: Property - Prüft ob abschließbar (status='IN_PROGRESS')
- `get_default_chair(committee)`: Static method - Gibt Standard-Vorsitzenden zurück (User mit meeting.lead_meeting Permission)
- `get_default_clerk(committee)`: Static method - Gibt Standard-Protokollführung zurück (User mit meeting.write_minutes Permission)
- `user_can_create(user, committee)`: Static method - Prüft ob User Meeting für Committee erstellen darf
- `user_can_send_invitation(user, meeting)`: Static method - Prüft ob User Einladung versenden darf (DRAFT → SENT)
- `user_can_start_meeting(user, meeting)`: Static method - Prüft ob User Meeting starten darf (SENT → IN_PROGRESS)
- `user_can_complete_meeting(user, meeting)`: Static method - Prüft ob User Meeting abschließen darf (IN_PROGRESS → COMPLETED)
- `user_can_view_meeting(user, meeting)`: Static method - Prüft ob User Meeting anzeigen darf (wichtig für Gäste/Externe)
- `get_duration()`: Berechnet geplante Dauer (end_time - start_time), returns timedelta or None
- `get_actual_duration()`: Berechnet tatsächliche Dauer (actual_end_time - actual_start_time), returns timedelta or None

**Validierung in clean():**
```python
def clean(self) -> None:
    """
    Validate meeting data:
    - Meeting type-specific location requirements
    - Time constraints (end_time after start_time)
    - Chair/Clerk membership validation
    """
    from django.core.exceptions import ValidationError
    
    # Meeting type validation
    if self.meeting_type == 'ONLINE':
        # Online: location_url required, address fields not allowed
        if not self.location_url:
            raise ValidationError({
                'location_url': 'Online-Link ist erforderlich für Online-Sitzungen'
            })
        
        has_address_fields = any([
            self.location_name,
            self.location_street,
            self.location_zip,
            self.location_city,
            self.location_room
        ])
        if has_address_fields:
            raise ValidationError({
                'meeting_type': 'Adressfelder nicht erlaubt für Online-Sitzungen'
            })
    
    elif self.meeting_type == 'IN_PERSON':
        # In-person: address required, location_url not allowed
        has_full_address = all([
            self.location_name,
            self.location_street,
            self.location_zip,
            self.location_city
        ])
        if not has_full_address:
            raise ValidationError({
                'location_name': 'Vollständige Adresse erforderlich für Präsenzsitzungen'
            })
        
        if self.location_url:
            raise ValidationError({
                'location_url': 'Online-Link nicht erlaubt für Präsenzsitzungen'
            })
    
    elif self.meeting_type == 'HYBRID':
        # Hybrid: both URL and address required
        if not self.location_url:
            raise ValidationError({
                'location_url': 'Online-Link erforderlich für Hybrid-Sitzungen'
            })
        
        has_full_address = all([
            self.location_name,
            self.location_street,
            self.location_zip,
            self.location_city
        ])
        if not has_full_address:
            raise ValidationError({
                'location_name': 'Vollständige Adresse erforderlich für Hybrid-Sitzungen'
            })
    
    # Time validation
    if self.end_time and self.start_time and self.end_time <= self.start_time:
        raise ValidationError({
            'end_time': 'Endzeit muss nach Startzeit liegen'
        })
    
    if self.actual_end_time and self.actual_start_time:
        if self.actual_end_time <= self.actual_start_time:
            raise ValidationError({
                'actual_end_time': 'Tatsächliches Ende muss nach tatsächlichem Beginn liegen'
            })
    
    # Chair/Clerk must be members of committee (if set)
    if self.chair and self.committee:
        is_member = self.committee.memberships.filter(
            user=self.chair,
            is_active=True
        ).exists()
        if not is_member:
            raise ValidationError({
                'chair': f'{self.chair.get_full_name()} ist kein aktives Mitglied des Gremiums'
            })
    
    if self.clerk and self.committee:
        is_member = self.committee.memberships.filter(
            user=self.clerk,
            is_active=True
        ).exists()
        if not is_member:
            raise ValidationError({
                'clerk': f'{self.clerk.get_full_name()} ist kein aktives Mitglied des Gremiums'
            })
```

**Auto-Generate meeting_number in save():**
```python
def save(self, *args, **kwargs) -> None:
    """
    Auto-generate meeting_number if new meeting.
    Format: {YEAR}-{COUNT:02d} (e.g., "2026-05")
    """
    if not self.meeting_number and self.committee and self.date:
        year = self.date.year
        
        # Count existing meetings for this committee in this year
        count = Meeting.objects.filter(
            committee=self.committee,
            date__year=year
        ).count() + 1
        
        self.meeting_number = f"{year}-{count:02d}"
    
    # Call full_clean for validation before saving
    self.full_clean()
    super().save(*args, **kwargs)
```

**get_full_location Property:**
```python
@property
def get_full_location(self) -> str:
    """
    Returns formatted location string based on meeting_type.
    
    Returns:
        Formatted location string (URL for ONLINE, address for IN_PERSON,
        both for HYBRID)
    """
    if self.meeting_type == 'ONLINE':
        return f"Online: {self.location_url}"
    
    elif self.meeting_type == 'IN_PERSON':
        parts = [self.location_name]
        if self.location_room:
            parts.append(f"Raum {self.location_room}")
        parts.append(f"{self.location_street}, {self.location_zip} {self.location_city}")
        return ", ".join(parts)
    
    elif self.meeting_type == 'HYBRID':
        parts = [self.location_name]
        if self.location_room:
            parts.append(f"Raum {self.location_room}")
        parts.append(f"{self.location_street}, {self.location_zip} {self.location_city}")
        parts.append(f"(Online: {self.location_url})")
        return ", ".join(parts)
    
    return ""
```

**Helper Methods für Default-Werte:**
```python
from typing import Optional
from apps.committees.models import Membership

@staticmethod
def get_default_chair(committee: 'Committee') -> Optional['User']:
    """
    Get the default chair for a committee.
    
    Returns the first active member with 'meeting.lead_meeting' permission.
    Typically this would be the user with CHAIR role, but can be any role
    that has this permission.
    
    Args:
        committee: Committee instance
    
    Returns:
        User instance or None
    """
    memberships = Membership.objects.filter(
        committee=committee,
        is_active=True
    ).select_related('role', 'user')
    
    for membership in memberships:
        if membership.role:
            has_permission = membership.role.permissions.filter(
                codename='meeting.lead_meeting'
            ).exists()
            
            if has_permission:
                return membership.user
    
    return None

@staticmethod
def get_default_clerk(committee: 'Committee') -> Optional['User']:
    """
    Get the default clerk for a committee.
    
    Returns the first active member with 'meeting.write_minutes' permission.
    
    Args:
        committee: Committee instance
    
    Returns:
        User instance or None
    """
    memberships = Membership.objects.filter(
        committee=committee,
        is_active=True
    ).select_related('role', 'user')
    
    for membership in memberships:
        if membership.role:
            has_permission = membership.role.permissions.filter(
                codename='meeting.write_minutes'
            ).exists()
            
            if has_permission:
                return membership.user
    
    return None
```

**Business Logic Properties & Methods:**
```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from apps.accounts.models import User
    from apps.committees.models import Committee

@property
def is_editable(self) -> bool:
    """Meeting is editable only in DRAFT status."""
    return self.status == 'DRAFT'

@property
def is_deletable(self) -> bool:
    """Meeting is deletable only in DRAFT status."""
    return self.status == 'DRAFT'

@property
def can_send_invitation(self) -> bool:
    """Invitation can be sent only in DRAFT status."""
    return self.status == 'DRAFT'

@property
def can_complete(self) -> bool:
    """Meeting can be completed only when IN_PROGRESS."""
    return self.status == 'IN_PROGRESS'

@staticmethod
def user_can_create(user: 'User', committee: 'Committee') -> bool:
    """
    Check if user is allowed to create a meeting for the given committee.
    
    Rules:
    - User has permission 'meeting.create' via role in THIS committee, OR
    - User has permission 'meeting.create_other' (admins), OR
    - Special rule: MAIN committee - Betriebsausschuss members with
      'meeting.create' permission
    
    Args:
        user: User instance
        committee: Committee instance
    
    Returns:
        True if user can create meeting in this committee
    """
    from apps.committees.models import Membership
    
    # Guard: Superuser can always create
    if user.is_superuser:
        return True
    
    # Check if user has 'meeting.create_other' permission (admin permission)
    # TODO: Implement proper permission check via role system
    # For now, staff users have this permission
    if user.is_staff:
        return True
    
    # Get user's memberships in this committee
    memberships = Membership.objects.filter(
        user=user,
        committee=committee,
        is_active=True
    ).select_related('role')
    
    for membership in memberships:
        if membership.role:
            has_create_permission = membership.role.permissions.filter(
                codename='meeting.create'
            ).exists()
            
            if has_create_permission:
                return True
    
    # Special rule for MAIN committee
    if committee.committee_type == 'MAIN':
        betriebsausschuss = committee.subcommittees.filter(
            committee_type='COMMITTEE',
            is_active=True
        ).first()
        
        if betriebsausschuss:
            ba_memberships = Membership.objects.filter(
                user=user,
                committee=betriebsausschuss,
                is_active=True
            ).select_related('role')
            
            for ba_membership in ba_memberships:
                if ba_membership.role:
                    has_create_permission = ba_membership.role.permissions.filter(
                        codename='meeting.create'
                    ).exists()
                    
                    if has_create_permission:
                        return True
    
    return False

@staticmethod
def _user_has_permission(
    user: 'User',
    committee: 'Committee',
    permission_codename: str
) -> bool:
    """
    Helper method to check if user has specific permission in committee.
    
    Args:
        user: User instance
        committee: Committee instance
        permission_codename: Permission codename to check
    
    Returns:
        True if user has permission
    """
    from apps.committees.models import Membership
    
    # Guard: Superuser always has permission
    if user.is_superuser or user.is_staff:
        return True
    
    # Check if user has permission via role in committee
    memberships = Membership.objects.filter(
        user=user,
        committee=committee,
        is_active=True
    ).select_related('role')
    
    for membership in memberships:
        if membership.role:
            has_permission = membership.role.permissions.filter(
                codename=permission_codename
            ).exists()
            
            if has_permission:
                return True
    
    return False

@staticmethod
def user_can_send_invitation(user: 'User', meeting: 'Meeting') -> bool:
    """
    Check if user is allowed to send invitation (DRAFT → SENT).
    
    Args:
        user: User instance
        meeting: Meeting instance
    
    Returns:
        True if user can send invitation
    """
    return Meeting._user_has_permission(
        user,
        meeting.committee,
        'meeting.send_invitation'
    )

@staticmethod
def user_can_start_meeting(user: 'User', meeting: 'Meeting') -> bool:
    """
    Check if user is allowed to start meeting (SENT → IN_PROGRESS).
    
    Args:
        user: User instance
        meeting: Meeting instance
    
    Returns:
        True if user can start meeting
    """
    return Meeting._user_has_permission(
        user,
        meeting.committee,
        'meeting.start_meeting'
    )

@staticmethod
def user_can_complete_meeting(user: 'User', meeting: 'Meeting') -> bool:
    """
    Check if user is allowed to complete meeting (IN_PROGRESS → COMPLETED).
    
    Args:
        user: User instance
        meeting: Meeting instance
    
    Returns:
        True if user can complete meeting
    """
    return Meeting._user_has_permission(
        user,
        meeting.committee,
        'meeting.complete_meeting'
    )

@staticmethod
def user_can_view_meeting(user: 'User', meeting: 'Meeting') -> bool:
    """
    Check if user is allowed to view meeting details.
    
    Important for controlling access for guests/external users.
    
    Args:
        user: User instance
        meeting: Meeting instance
    
    Returns:
        True if user can view meeting
    """
    return Meeting._user_has_permission(
        user,
        meeting.committee,
        'meeting.view'
    )
```

**Siehe:** CODE_STYLE_GUIDE.md → "Django Best Practices → Models"

---

**Datei:** `apps/meetings/apps.py`

- `default_auto_field = 'django.db.models.BigAutoField'`
- `name = 'apps.meetings'`
- `verbose_name = 'Sitzungsverwaltung'`

---

**Migration:**
```bash
python manage.py makemigrations meetings
python manage.py migrate
```

---

### Schritt 1.3: Model-Tests

**Datei:** `apps/meetings/tests/test_models.py`

**Tests zu implementieren:**

#### Meeting Creation Tests

1. **test_meeting_creation_with_all_fields**
   - Meeting mit allen Pflichtfeldern erstellen
   - Assert: committee, title, date, start_time, meeting_type korrekt gespeichert

2. **test_meeting_number_auto_generation**
   - Meeting ohne meeting_number erstellen
   - Assert: meeting_number automatisch generiert (Format: YYYY-NN)

3. **test_meeting_number_increments_per_year**
   - Drei Meetings im gleichen Jahr erstellen
   - Assert: meeting_numbers sind 2026-01, 2026-02, 2026-03

4. **test_meeting_number_resets_per_year**
   - Ein Meeting in 2026, eins in 2027
   - Assert: 2026-01 und 2027-01

5. **test_meeting_number_unique_per_committee**
   - Zwei Committees, gleiches Jahr
   - Assert: Beide können 2026-01 haben (unique_together)

6. **test_meeting_str_representation**
   - __str__() sollte "{meeting_number} - {title} ({date})" zurückgeben
   - Assert: Format korrekt

#### Meeting Type Validation Tests

7. **test_online_meeting_requires_url**
   - ONLINE Meeting ohne location_url
   - Assert: ValidationError

8. **test_online_meeting_no_address_fields**
   - ONLINE Meeting mit location_name
   - Assert: ValidationError

9. **test_in_person_meeting_requires_full_address**
   - IN_PERSON Meeting ohne location_city
   - Assert: ValidationError

10. **test_in_person_meeting_no_url**
    - IN_PERSON Meeting mit location_url
    - Assert: ValidationError

11. **test_hybrid_meeting_requires_both**
    - HYBRID Meeting ohne location_url
    - Assert: ValidationError

12. **test_hybrid_meeting_valid_with_both**
    - HYBRID Meeting mit URL und vollständiger Adresse
    - Assert: Erfolgreich gespeichert

#### Time Validation Tests

13. **test_end_time_after_start_time**
    - Meeting mit end_time vor start_time
    - Assert: ValidationError

14. **test_actual_end_time_after_actual_start_time**
    - Meeting mit actual_end_time vor actual_start_time
    - Assert: ValidationError

15. **test_get_duration_calculation**
    - Meeting mit start_time=10:00, end_time=12:00
    - Assert: get_duration() returns timedelta(hours=2)

16. **test_get_actual_duration_calculation**
    - Meeting mit actual_start_time und actual_end_time
    - Assert: get_actual_duration() korrekt

17. **test_get_duration_returns_none_without_end_time**
    - Meeting ohne end_time
    - Assert: get_duration() returns None

#### Chair/Clerk Validation Tests

18. **test_chair_must_be_committee_member**
    - Meeting mit chair der nicht im Committee ist
    - Assert: ValidationError

19. **test_clerk_must_be_committee_member**
    - Meeting mit clerk der nicht im Committee ist
    - Assert: ValidationError

20. **test_chair_and_clerk_can_be_same_person**
    - Meeting mit chair == clerk (sollte erlaubt sein)
    - Assert: Erfolgreich gespeichert

21. **test_get_default_chair_returns_user_with_lead_permission**
    - Committee mit User der meeting.lead_meeting Permission hat
    - Assert: get_default_chair(committee) == dieser User

22. **test_get_default_chair_returns_none_if_no_permission**
    - Committee ohne User mit meeting.lead_meeting Permission
    - Assert: get_default_chair(committee) == None

23. **test_get_default_clerk_returns_user_with_minutes_permission**
    - Committee mit User der meeting.write_minutes Permission hat
    - Assert: get_default_clerk(committee) == dieser User

#### Property Tests

24. **test_is_upcoming_for_future_meeting**
    - Meeting mit Datum in 7 Tagen
    - Assert: is_upcoming = True

25. **test_is_past_for_past_meeting**
    - Meeting mit Datum vor 7 Tagen
    - Assert: is_past = True

26. **test_is_editable_only_in_draft**
    - Meeting mit status='DRAFT'
    - Assert: is_editable = True
    - Meeting mit status='COMPLETED'
    - Assert: is_editable = False

27. **test_is_deletable_only_in_draft**
    - Meeting mit status='DRAFT'
    - Assert: is_deletable = True
    - Andere Status
    - Assert: is_deletable = False

28. **test_can_send_invitation_only_in_draft**
    - Meeting mit status='DRAFT'
    - Assert: can_send_invitation = True
    - Meeting mit status='SENT'
    - Assert: can_send_invitation = False
    - Meeting mit status='IN_PROGRESS'
    - Assert: can_send_invitation = False

29. **test_can_complete_only_in_progress**
    - Meeting mit status='IN_PROGRESS'
    - Assert: can_complete = True
    - Meeting mit status='DRAFT'
    - Assert: can_complete = False
    - Meeting mit status='SENT'
    - Assert: can_complete = False

30. **test_get_full_location_online**
    - ONLINE Meeting
    - Assert: get_full_location == "Online: {url}"

31. **test_get_full_location_in_person**
    - IN_PERSON Meeting
    - Assert: get_full_location enthält Name, Straße, PLZ, Stadt

32. **test_get_full_location_hybrid**
    - HYBRID Meeting
    - Assert: get_full_location enthält Adresse + Online-Link

33. **test_get_absolute_url**
    - Meeting erstellen
    - Assert: get_absolute_url() == reverse('meetings:meeting_detail', kwargs={'pk': pk})

#### Permission Method Tests

34. **test_user_can_create_with_permission_in_own_committee**
    - User hat meeting.create Permission in Committee A (über Rolle)
    - Assert: user_can_create(user, Committee A) = True

35. **test_user_can_create_with_permission_in_betriebsausschuss_for_main**
    - Committee ist MAIN
    - User hat meeting.create Permission im Betriebsausschuss
    - Assert: user_can_create(user, MAIN) = True

36. **test_user_cannot_create_in_other_committee**
    - User hat meeting.create Permission in Committee A
    - Versuch Meeting in Committee B zu erstellen
    - Assert: user_can_create(user, Committee B) = False

37. **test_user_can_create_with_create_other_permission**
    - User hat meeting.create_other Permission (Admin)
    - Assert: user_can_create(user, ANY_COMMITTEE) = True

38. **test_user_can_send_invitation_with_permission**
    - User hat meeting.send_invitation Permission im Committee
    - Assert: user_can_send_invitation(user, meeting) = True

39. **test_user_cannot_send_invitation_without_permission**
    - User hat KEINE meeting.send_invitation Permission
    - Assert: user_can_send_invitation(user, meeting) = False

40. **test_user_can_start_meeting_with_permission**
    - User hat meeting.start_meeting Permission im Committee
    - Assert: user_can_start_meeting(user, meeting) = True

41. **test_user_can_complete_meeting_with_permission**
    - User hat meeting.complete_meeting Permission im Committee
    - Assert: user_can_complete_meeting(user, meeting) = True

42. **test_user_can_view_meeting_with_permission**
    - User hat meeting.view Permission im Committee
    - Assert: user_can_view_meeting(user, meeting) = True

43. **test_guest_cannot_view_meeting_without_permission**
    - User ist Gast ohne meeting.view Permission
    - Assert: user_can_view_meeting(user, meeting) = False

44. **test_flexible_role_permissions**
    - User hat Custom-Rolle "2. Stellvertreter" mit meeting.start_meeting Permission
    - Assert: user_can_start_meeting(user, meeting) = True

**Siehe:** CODE_STYLE_GUIDE.md → "Django Best Practices → Testing"

---

## Phase 2: Admin-Interface

### Ziel
Basis-Verwaltung über Django Admin aktivieren.

### Schritt 2.1: Admin-Klasse

**Datei:** `apps/meetings/admin.py`

**MeetingAdmin zu implementieren:**

**Decorator:** `@admin.register(Meeting)`

**list_display:**
- meeting_number, title, committee, date, start_time, meeting_type, status, is_quorate_display, created_at

**list_filter:**
- status, meeting_type, committee, date, is_quorate, ('sent_at', admin.EmptyFieldListFilter)

**search_fields:**
- title, meeting_number, committee__name, location_name, location_city

**fieldsets (gruppiert):**
1. None: committee, title, meeting_number
2. Zeitplanung: date, start_time, end_time, actual_start_time, actual_end_time
3. Sitzungstyp & Ort:
   - meeting_type
   - **ONLINE/HYBRID:** location_url
   - **IN_PERSON/HYBRID:** location_name, location_street, location_zip, location_city, location_room
4. Verantwortliche: chair, chair_substitute, clerk, clerk_substitute
5. Status: status, is_quorate, sent_at
6. Meta: created_by, created_at, updated_at

**readonly_fields:**
- meeting_number, created_at, updated_at, sent_at

**autocomplete_fields:**
- committee, chair, chair_substitute, clerk, clerk_substitute, created_by

**Custom Methods:**
- `is_quorate_display(obj)`: @admin.display(boolean=True), return obj.is_quorate if obj.is_quorate is not None else None

**get_queryset():**
- select_related('committee', 'chair', 'clerk', 'chair_substitute', 'clerk_substitute', 'created_by')

**save_model():**
- Setzt created_by = request.user wenn neues Meeting

**Autocomplete konfigurieren:**
- CommitteeAdmin (committees): `search_fields = ['name']` sicherstellen
- UserAdmin (accounts): `search_fields = ['email', 'first_name', 'last_name']` sicherstellen

**Siehe:** CODE_STYLE_GUIDE.md → "Django Best Practices → Admin"

---

## Phase 3: Berechtigungen & Seed-Daten

### Schritt 3.1: Berechtigungen definieren

**Datei:** `apps/meetings/management/commands/seed_meeting_permissions.py`

**Funktionalität:**
- Django Management Command
- help = 'Erstellt Standard-Berechtigungen für Meetings'

**Berechtigungen zu erstellen (Liste von Tupeln):**

**Meeting-Berechtigungen:**
- `meeting.create` - "Sitzung erstellen (im eigenen Gremium)"
- `meeting.create_other` - "Sitzung in anderen Gremien erstellen" - Nur für Admins/Superuser
- `meeting.view` - "Sitzung anzeigen" - Für alle Mitglieder, Gäste, Externe
- `meeting.edit` - "Sitzung bearbeiten (nur DRAFT)"
- `meeting.delete_draft` - "Entwurf löschen"

**Status-Workflow-Berechtigungen (granular):**
- `meeting.send_invitation` - "Status ändern: DRAFT → SENT (Einladung versenden)"
- `meeting.start_meeting` - "Status ändern: SENT → IN_PROGRESS (Sitzung beginnen)"
- `meeting.complete_meeting` - "Status ändern: IN_PROGRESS → COMPLETED (Sitzung abschließen)"

**Weitere Berechtigungen:**
- `meeting.manage_participants` - "Teilnehmer verwalten"
- `meeting.lead_meeting` - "Sitzung leiten" - Verwendet für Default chair-Auswahl (typisch: CHAIR, VICE_CHAIR)
- `meeting.write_minutes` - "Protokoll schreiben" - Verwendet für Default clerk-Auswahl (typisch: SECRETARY, CLERK)

**Hinweis:** Permissions sind über das Rollensystem flexibel konfigurierbar. 

**Beispiel-Konfiguration:**
```
CHAIR-Rolle:
  - meeting.create, meeting.view, meeting.edit
  - meeting.send_invitation, meeting.start_meeting, meeting.complete_meeting
  - meeting.lead_meeting

VICE_CHAIR-Rolle:
  - meeting.create, meeting.view, meeting.edit
  - meeting.send_invitation, meeting.start_meeting, meeting.complete_meeting
  - meeting.lead_meeting

"2. STELLVERTRETER"-Rolle:
  - meeting.view
  - meeting.start_meeting, meeting.complete_meeting
  - meeting.lead_meeting

MEMBER-Rolle:
  - meeting.view

GUEST-Rolle (Externe/Gäste):
  - meeting.view (oder auch nicht, wenn vertraulich)
```

**Implementierung:**
- Loop über Liste: Permission.objects.get_or_create()
- Category: 'meeting'
- Output mit self.stdout.write() und self.style.SUCCESS()
- Counter für erstellte Permissions

**Ausführen:**
```bash
python manage.py seed_meeting_permissions
```

---

### Schritt 3.2: SYSTEM_ADMIN-Rolle erweitern

**Datei:** `apps/meetings/management/commands/assign_meeting_permissions.py`

**Funktionalität:**
- Weist SYSTEM_ADMIN alle meeting-Permissions zu
- Via RolePermission.objects.get_or_create()
- Fehlerbehandlung wenn SYSTEM_ADMIN nicht existiert

**Ausführen:**
```bash
python manage.py assign_meeting_permissions
```

---

### Schritt 3.3: Permission-Tests

**Datei:** `apps/meetings/tests/test_permissions.py`

**Tests zu implementieren:**

1. **test_seed_meeting_permissions_command**
   - Management Command ausführen
   - Assert: Alle erwarteten Permissions existieren in DB

2. **test_seed_meeting_permissions_idempotent**
   - Command zweimal ausführen
   - Assert: Keine Duplikate, gleiche Anzahl

3. **test_meeting_permissions_categorized**
   - Permissions nach category filtern
   - Assert: Alle meeting.* Permissions haben category='meeting'

4. **test_system_admin_has_meeting_permissions**
   - SYSTEM_ADMIN Rolle laden
   - Assert: Hat alle Permissions mit category='meeting'

**Siehe:** CODE_STYLE_GUIDE.md → "Django Best Practices → Testing"

---

## Phase 4: Forms & Dynamische Validierung

### Ziel
Intelligente Formulare erstellen, die sich dem Sitzungstyp anpassen.

### Schritt 4.1: Forms

**Datei:** `apps/meetings/forms.py` erstellen

**3 Forms zu implementieren:**

#### 1. MeetingForm

**Extends:** ModelForm

**Meta:**
- model: Meeting
- fields: committee, title, date, start_time, end_time, meeting_type, location_url, location_name, location_street, location_zip, location_city, location_room, chair, chair_substitute, clerk, clerk_substitute, is_quorate
- widgets: Bootstrap-Classes für alle Felder, DateInput mit type='date', TimeInput mit type='time'

**__init__():**
```python
def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    
    # Get meeting_type from instance or initial data
    meeting_type = self.instance.meeting_type if self.instance.pk else self.initial.get('meeting_type', 'IN_PERSON')
    
    # Apply dynamic field visibility based on meeting_type
    if meeting_type == 'ONLINE':
        # Show only location_url
        for field in ['location_name', 'location_street', 'location_zip', 'location_city', 'location_room']:
            self.fields[field].widget = forms.HiddenInput()
            self.fields[field].required = False
        self.fields['location_url'].required = True
    
    elif meeting_type == 'IN_PERSON':
        # Show only address fields
        self.fields['location_url'].widget = forms.HiddenInput()
        self.fields['location_url'].required = False
        for field in ['location_name', 'location_street', 'location_zip', 'location_city']:
            self.fields[field].required = True
    
    elif meeting_type == 'HYBRID':
        # Show both
        self.fields['location_url'].required = True
        for field in ['location_name', 'location_street', 'location_zip', 'location_city']:
            self.fields[field].required = True
    
    # Filter chair/clerk choices to committee members
    if self.instance.pk and self.instance.committee:
        members = self.instance.committee.get_active_members()
        member_users = [m.user.id for m in members]
        self.fields['chair'].queryset = User.objects.filter(id__in=member_users)
        self.fields['chair_substitute'].queryset = User.objects.filter(id__in=member_users)
        self.fields['clerk'].queryset = User.objects.filter(id__in=member_users)
        self.fields['clerk_substitute'].queryset = User.objects.filter(id__in=member_users)
    
    # Add Bootstrap classes
    for field_name, field in self.fields.items():
        if not isinstance(field.widget, forms.HiddenInput):
            field.widget.attrs.update({'class': 'form-control'})
    
    # Help texts
    self.fields['meeting_type'].help_text = 'Wählen Sie den Sitzungstyp. Die Formularfelder passen sich automatisch an.'
    self.fields['is_quorate'].help_text = 'Wird nach Anwesenheitsprüfung automatisch gesetzt'
```

**clean():**
```python
def clean(self):
    cleaned_data = super().clean()
    meeting_type = cleaned_data.get('meeting_type')
    
    # Additional form-level validation can go here
    # (Model.clean() already handles most validation)
    
    return cleaned_data
```

**Siehe:** CODE_STYLE_GUIDE.md → "Django Best Practices → Forms"

---

#### 2. MeetingFilterForm

**Extends:** Form

**Zweck:** Filter-Form für MeetingListView

**Felder:**
- `committee`: ModelChoiceField(Committee, required=False, label='Gremium')
- `status`: ChoiceField(STATUS_CHOICES, required=False, label='Status')
- `meeting_type`: ChoiceField(MEETING_TYPE_CHOICES, required=False, label='Sitzungstyp')
- `date_from`: DateField(required=False, label='Von Datum', widget=DateInput(type='date'))
- `date_to`: DateField(required=False, label='Bis Datum', widget=DateInput(type='date'))

**__init__():**
- Fügt leere Option ('', '--------') zu allen ChoiceFields hinzu
- Bootstrap-Classes

---

#### 3. MeetingSendInvitationForm

**Extends:** Form

**Zweck:** Einladung versenden mit optionaler Nachricht

**Felder:**
- `message`: CharField(widget=Textarea, required=False, label='Zusätzliche Nachricht')
- `include_agenda`: BooleanField(initial=True, required=False, label='Tagesordnung anhängen')

**__init__():**
- Bootstrap-Classes
- Help-Text für message: "Optional: Fügen Sie eine persönliche Nachricht hinzu"

---

### Schritt 4.2: Form-Tests

**Datei:** `apps/meetings/tests/test_forms.py`

**Tests zu implementieren:**

#### MeetingForm Tests

1. **test_meeting_form_valid_online**
   - Form-Daten für ONLINE Meeting
   - Assert: Form valid, nur location_url erforderlich

2. **test_meeting_form_invalid_online_without_url**
   - ONLINE Meeting ohne location_url
   - Assert: Form invalid, Error bei location_url

3. **test_meeting_form_valid_in_person**
   - Form-Daten für IN_PERSON Meeting
   - Assert: Form valid, Adressfelder erforderlich

4. **test_meeting_form_invalid_in_person_without_address**
   - IN_PERSON Meeting ohne location_city
   - Assert: Form invalid, Error bei location_city

5. **test_meeting_form_valid_hybrid**
   - Form-Daten für HYBRID Meeting
   - Assert: Form valid, beide erforderlich

6. **test_meeting_form_dynamic_field_hiding_online**
   - Form mit meeting_type='ONLINE' initialisieren
   - Assert: Adressfelder haben HiddenInput widget

7. **test_meeting_form_dynamic_field_hiding_in_person**
   - Form mit meeting_type='IN_PERSON'
   - Assert: location_url hat HiddenInput widget

8. **test_meeting_form_chair_queryset_filtered_to_members**
   - Form für existierendes Meeting
   - Assert: chair.queryset enthält nur Committee-Mitglieder

#### MeetingFilterForm Tests

9. **test_meeting_filter_form_all_fields_optional**
   - Leeres Form absenden
   - Assert: Form valid

10. **test_meeting_filter_form_date_range**
    - date_from und date_to
    - Assert: Form valid, Daten korrekt

#### MeetingSendInvitationForm Tests

11. **test_send_invitation_form_valid**
    - Form mit message absenden
    - Assert: Form valid

12. **test_send_invitation_form_include_agenda_default_true**
    - Form ohne Daten initialisieren
    - Assert: include_agenda initial=True

**Siehe:** CODE_STYLE_GUIDE.md → "Django Best Practices → Testing"

---

## Phase 5: Views & Templates

### Ziel
Benutzer-Interface für Sitzungsverwaltung mit Status-Workflow erstellen.

### Schritt 5.1: URL-Konfiguration

**Datei:** `apps/meetings/urls.py` erstellen

**app_name:** `'meetings'`

**URLs zu definieren:**

**Meeting URLs:**
- `''` → MeetingListView (name='meeting_list')
- `'create/'` → MeetingCreateView (name='meeting_create')
- `'<uuid:pk>/'` → MeetingDetailView (name='meeting_detail')
- `'<uuid:pk>/edit/'` → MeetingUpdateView (name='meeting_update')
- `'<uuid:pk>/delete/'` → MeetingDeleteView (name='meeting_delete')
- `'<uuid:pk>/send/'` → MeetingSendInvitationView (name='meeting_send')
- `'<uuid:pk>/complete/'` → MeetingCompleteView (name='meeting_complete')

**HTMX URLs (später):**
- `'<uuid:pk>/update-status/'` → MeetingUpdateStatusView (name='meeting_update_status')

**config/urls.py ergänzen:**
- `'meetings/'` → include('apps.meetings.urls')

---

### Schritt 5.2: Custom Mixins

**Datei:** `apps/meetings/mixins.py` erstellen

**2 Mixins zu implementieren:**

#### 1. MeetingPermissionMixin

**Extends:** UserPassesTestMixin

**Funktionalität:**
- Prüft ob User Berechtigung für Meeting-Aktionen hat
- Attribut: `required_permission` (Override in Subclass)
- test_func(): Superuser = True, sonst is_staff (TODO: Später über roles/permissions-System)

```python
class MeetingPermissionMixin(UserPassesTestMixin):
    """
    Mixin to check if user has permission for meeting actions.
    Subclass must define `required_permission` attribute.
    """
    required_permission = None
    
    def test_func(self):
        if self.request.user.is_superuser:
            return True
        if self.request.user.is_staff:
            return True
        # TODO: Implement permission check via roles.Permission
        # return self.request.user.has_perm(self.required_permission)
        return False
```

#### 2. MeetingContextMixin

**Funktionalität:**
- Fügt meeting zum Context hinzu
- get_context_data(): Fügt committee, is_editable, is_deletable, can_send_invitation, can_complete hinzu

```python
class MeetingContextMixin:
    """
    Adds meeting-related context variables to the view.
    """
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        meeting = self.object if hasattr(self, 'object') else None
        
        if meeting:
            context['committee'] = meeting.committee
            context['is_editable'] = meeting.is_editable
            context['is_deletable'] = meeting.is_deletable
            context['can_send_invitation'] = meeting.can_send_invitation
            context['can_complete'] = meeting.can_complete
        
        return context
```

**Siehe:** CODE_STYLE_GUIDE.md → "Django Best Practices → Mixins"

---

### Schritt 5.3: Meeting Views

**Datei:** `apps/meetings/views.py`

**7 Views für Meetings:**

#### 1. MeetingListView

**Extends:** LoginRequiredMixin, MeetingPermissionMixin, ListView

**Funktionalität:**
- Zeigt alle Meetings mit Filterung
- Gruppiert nach Status (Upcoming, Past)
- Pagination: 20 pro Seite

**Attribute:**
- model: Meeting
- template_name: 'meetings/meeting_list.html'
- context_object_name: 'meetings'
- required_permission: 'meeting.view'
- paginate_by: 20

**get_queryset():**
```python
def get_queryset(self):
    queryset = Meeting.objects.select_related(
        'committee', 'chair', 'clerk', 'created_by'
    ).all()
    
    # Apply filters from MeetingFilterForm
    committee = self.request.GET.get('committee')
    status = self.request.GET.get('status')
    meeting_type = self.request.GET.get('meeting_type')
    date_from = self.request.GET.get('date_from')
    date_to = self.request.GET.get('date_to')
    
    if committee:
        queryset = queryset.filter(committee_id=committee)
    if status:
        queryset = queryset.filter(status=status)
    if meeting_type:
        queryset = queryset.filter(meeting_type=meeting_type)
    if date_from:
        queryset = queryset.filter(date__gte=date_from)
    if date_to:
        queryset = queryset.filter(date__lte=date_to)
    
    return queryset.order_by('-date', '-start_time')
```

**get_context_data():**
```python
def get_context_data(self, **kwargs):
    context = super().get_context_data(**kwargs)
    
    # Add filter form
    context['filter_form'] = MeetingFilterForm(self.request.GET)
    
    # Group meetings
    from datetime import date
    today = date.today()
    
    context['upcoming_meetings'] = self.get_queryset().filter(date__gte=today)
    context['past_meetings'] = self.get_queryset().filter(date__lt=today)
    
    return context
```

#### 2. MeetingDetailView

**Extends:** LoginRequiredMixin, MeetingPermissionMixin, MeetingContextMixin, DetailView

**Funktionalität:**
- Zeigt Meeting-Details
- Anwesenheitsstatistik (TODO: später mit attendance-App)
- Tagesordnung-Preview (TODO: später mit agendas-App)
- Protokoll-Link (TODO: später mit minutes-App)

**Attribute:**
- model: Meeting
- template_name: 'meetings/meeting_detail.html'
- context_object_name: 'meeting'
- required_permission: 'meeting.view'

**get_context_data():**
```python
def get_context_data(self, **kwargs):
    context = super().get_context_data(**kwargs)
    
    # TODO: Add agenda items count when agendas app is implemented
    # context['agenda_items_count'] = self.object.agenda_items.count()
    
    # TODO: Add attendance statistics when attendance app is implemented
    # context['attendees_count'] = self.object.attendance_records.filter(status='PRESENT').count()
    
    return context
```

#### 3. MeetingCreateView

**Extends:** LoginRequiredMixin, MeetingPermissionMixin, CreateView

**Funktionalität:**
- Erstellt neues Meeting
- Setzt created_by automatisch

**Attribute:**
- model: Meeting
- template_name: 'meetings/meeting_form.html'
- form_class: MeetingForm
- required_permission: 'meeting.create'

**form_valid():**
```python
def form_valid(self, form):
    form.instance.created_by = self.request.user
    form.instance.status = 'DRAFT'
    messages.success(self.request, f'Sitzung "{form.instance.title}" wurde erstellt.')
    return super().form_valid(form)
```

**get_success_url():**
- Redirect zu meeting_detail

#### 4. MeetingUpdateView

**Extends:** LoginRequiredMixin, MeetingPermissionMixin, MeetingContextMixin, UpdateView

**Funktionalität:**
- Bearbeitet Meeting
- Nur möglich wenn is_editable=True (status='DRAFT')

**Attribute:**
- model: Meeting
- template_name: 'meetings/meeting_form.html'
- form_class: MeetingForm
- required_permission: 'meeting.edit'

**dispatch():**
```python
def dispatch(self, request, *args, **kwargs):
    meeting = self.get_object()
    if not meeting.is_editable:
        messages.error(request, 'Sitzung kann nicht mehr bearbeitet werden (Status ist nicht DRAFT).')
        return redirect('meetings:meeting_detail', pk=meeting.pk)
    return super().dispatch(request, *args, **kwargs)
```

**form_valid():**
```python
def form_valid(self, form):
    messages.success(self.request, f'Sitzung "{form.instance.title}" wurde aktualisiert.')
    return super().form_valid(form)
```

**get_success_url():**
- Redirect zu meeting_detail

#### 5. MeetingDeleteView

**Extends:** LoginRequiredMixin, MeetingPermissionMixin, MeetingContextMixin, DeleteView

**Funktionalität:**
- Löscht Meeting (Hard-Delete)
- Nur möglich wenn is_deletable=True (status='DRAFT')
- Bestätigungs-Dialog

**Attribute:**
- model: Meeting
- template_name: 'meetings/meeting_confirm_delete.html'
- required_permission: 'meeting.delete_draft'

**dispatch():**
```python
def dispatch(self, request, *args, **kwargs):
    meeting = self.get_object()
    if not meeting.is_deletable:
        messages.error(request, 'Nur Entwürfe können gelöscht werden.')
        return redirect('meetings:meeting_detail', pk=meeting.pk)
    return super().dispatch(request, *args, **kwargs)
```

**delete():**
```python
def delete(self, request, *args, **kwargs):
    meeting = self.get_object()
    meeting_title = meeting.title
    response = super().delete(request, *args, **kwargs)
    messages.success(request, f'Sitzung "{meeting_title}" wurde gelöscht.')
    return response
```

**get_success_url():**
- Redirect zu meeting_list

#### 6. MeetingSendInvitationView

**Extends:** LoginRequiredMixin, MeetingPermissionMixin, MeetingContextMixin, FormView

**Funktionalität:**
- Sendet Einladung per E-Mail
- Nur möglich wenn can_send_invitation=True
- Ändert Status zu 'SENT'
- Setzt sent_at timestamp

**Attribute:**
- template_name: 'meetings/meeting_send_invitation.html'
- form_class: MeetingSendInvitationForm
- required_permission: 'meeting.send'

**dispatch():**
```python
def dispatch(self, request, *args, **kwargs):
    self.meeting = get_object_or_404(Meeting, pk=kwargs['pk'])
    if not self.meeting.can_send_invitation:
        messages.error(request, 'Einladung kann in diesem Status nicht versendet werden.')
        return redirect('meetings:meeting_detail', pk=self.meeting.pk)
    return super().dispatch(request, *args, **kwargs)
```

**get_context_data():**
```python
def get_context_data(self, **kwargs):
    context = super().get_context_data(**kwargs)
    context['meeting'] = self.meeting
    context['committee'] = self.meeting.committee
    return context
```

**form_valid():**
```python
def form_valid(self, form):
    from django.utils import timezone
    
    # TODO: Send actual email when notifications app is implemented
    # For now, just update status and timestamp
    
    self.meeting.status = 'SENT'
    self.meeting.sent_at = timezone.now()
    self.meeting.save()
    
    messages.success(
        self.request, 
        f'Einladung für Sitzung "{self.meeting.title}" wurde versendet.'
    )
    return redirect('meetings:meeting_detail', pk=self.meeting.pk)
```

**get_success_url():**
- Redirect zu meeting_detail

#### 7. MeetingCompleteView

**Extends:** LoginRequiredMixin, MeetingPermissionMixin, MeetingContextMixin, View

**Funktionalität:**
- Schließt Sitzung ab (Status → 'COMPLETED')
- Nur möglich wenn can_complete=True
- Redirect-only View (kein Template)

**Attribute:**
- required_permission: 'meeting.complete'

**dispatch():**
```python
def dispatch(self, request, *args, **kwargs):
    self.meeting = get_object_or_404(Meeting, pk=kwargs['pk'])
    if not self.meeting.can_complete:
        messages.error(request, 'Sitzung kann nicht abgeschlossen werden.')
        return redirect('meetings:meeting_detail', pk=self.meeting.pk)
    return super().dispatch(request, *args, **kwargs)
```

**post():**
```python
def post(self, request, *args, **kwargs):
    self.meeting.status = 'COMPLETED'
    self.meeting.save()
    
    messages.success(
        request, 
        f'Sitzung "{self.meeting.title}" wurde abgeschlossen.'
    )
    return redirect('meetings:meeting_detail', pk=self.meeting.pk)
```

**Siehe:** CODE_STYLE_GUIDE.md → "Django Best Practices → Views"

---

### Schritt 5.4: Templates

**Templates zu erstellen:**

**Basis-Template:**
1. **`meetings/base_meeting.html`**
   - Extends base.html
   - Breadcrumb-Navigation
   - Block: breadcrumb, meeting_content

**Meeting-Templates:**
2. **`meetings/meeting_list.html`**
   - Extends base_meeting.html
   - Filter-Form (MeetingFilterForm)
   - Zwei Tabs: "Kommende Sitzungen" und "Vergangene Sitzungen"
   - Tabelle: Sitzungsnummer, Titel, Gremium, Datum, Uhrzeit, Typ, Status, Aktionen
   - Button: "Neue Sitzung" (wenn Permission)

3. **`meetings/meeting_detail.html`**
   - Extends base_meeting.html
   - Details-Card:
     - Titel, Sitzungsnummer, Gremium
     - Datum, Uhrzeit (geplant + tatsächlich)
     - Typ, Ort (formatiert via get_full_location)
     - Status-Badge (farblich je nach Status)
     - Vorsitz, Stellv. Vorsitz, Protokollführung, Stellv. Protokollführung
     - Beschlussfähig (ja/nein/unbekannt)
   - Action-Buttons (basierend auf Properties):
     - Bearbeiten (wenn is_editable)
     - Löschen (wenn is_deletable)
     - Einladung versenden (wenn can_send_invitation)
     - Abschließen (wenn can_complete)
   - Tagesordnung-Card (Placeholder für später)
   - Anwesenheit-Card (Placeholder für später)

4. **`meetings/meeting_form.html`**
   - Extends base_meeting.html
   - Form mit crispy-forms
   - **JavaScript für dynamisches Formular:**
     ```javascript
     // meeting_type onChange: Show/Hide Felder
     document.getElementById('id_meeting_type').addEventListener('change', function() {
         const type = this.value;
         const urlField = document.getElementById('id_location_url').closest('.form-group');
         const addressFields = [
             'location_name', 'location_street', 'location_zip', 
             'location_city', 'location_room'
         ].map(f => document.getElementById(`id_${f}`).closest('.form-group'));
         
         if (type === 'ONLINE') {
             urlField.style.display = 'block';
             addressFields.forEach(f => f.style.display = 'none');
         } else if (type === 'IN_PERSON') {
             urlField.style.display = 'none';
             addressFields.forEach(f => f.style.display = 'block');
         } else if (type === 'HYBRID') {
             urlField.style.display = 'block';
             addressFields.forEach(f => f.style.display = 'block');
         }
     });
     ```
   - Buttons: Speichern, Abbrechen

5. **`meetings/meeting_confirm_delete.html`**
   - Extends base_meeting.html
   - Bestätigungs-Dialog mit Warnung
   - Zeigt Meeting-Details (Titel, Datum, Gremium)
   - Warnung: "Diese Sitzung wird permanent gelöscht."
   - Buttons: Löschen (danger), Abbrechen

6. **`meetings/meeting_send_invitation.html`**
   - Extends base_meeting.html
   - Meeting-Details anzeigen (Titel, Datum, Ort)
   - Form: MeetingSendInvitationForm
   - Vorschau: Empfänger-Liste (alle Committee-Mitglieder)
   - Buttons: Einladung versenden, Abbrechen

**Alle Templates:** Bootstrap 5 Styling, Bootstrap Icons

**Siehe:** CODE_STYLE_GUIDE.md → "Django Best Practices → Templates"

---

### Schritt 5.5: View-Tests

**Datei:** `apps/meetings/tests/test_views.py`

**Tests zu implementieren:**

#### Meeting List Tests

1. **test_meeting_list_requires_login**
   - Unauthenticated User greift auf Meeting-Liste zu
   - Assert: Redirect zu Login

2. **test_meeting_list_accessible**
   - Authenticated User mit Permission
   - Assert: Status 200, Meetings im Context

3. **test_meeting_list_filter_by_committee**
   - Filter-Parameter: committee=<id>
   - Assert: Nur Meetings des Committees

4. **test_meeting_list_filter_by_status**
   - Filter-Parameter: status=DRAFT
   - Assert: Nur DRAFT-Meetings

5. **test_meeting_list_filter_by_date_range**
   - Filter-Parameter: date_from, date_to
   - Assert: Nur Meetings im Zeitraum

6. **test_meeting_list_grouping**
   - Meetings in Vergangenheit und Zukunft
   - Assert: upcoming_meetings und past_meetings korrekt gruppiert

#### Meeting Detail Tests

7. **test_meeting_detail_view**
   - Meeting-Detail anzeigen
   - Assert: Status 200, Meeting im Context

8. **test_meeting_detail_context_variables**
   - Meeting mit bestimmtem Status
   - Assert: is_editable, is_deletable, can_send_invitation korrekt

#### Meeting Create Tests

9. **test_meeting_create_requires_permission**
   - User ohne Permission versucht Meeting zu erstellen
   - Assert: 403 Forbidden

10. **test_meeting_create_success**
    - Admin erstellt neues Meeting
    - Assert: Meeting erstellt, created_by gesetzt, status='DRAFT'

11. **test_meeting_create_auto_generates_meeting_number**
    - Meeting ohne meeting_number erstellen
    - Assert: meeting_number automatisch generiert

12. **test_meeting_create_sets_created_by**
    - Meeting erstellen
    - Assert: created_by == request.user

#### Meeting Update Tests

13. **test_meeting_update_success**
    - Admin ändert DRAFT Meeting
    - Assert: Änderungen gespeichert

14. **test_meeting_update_blocked_for_non_draft**
    - Versuch COMPLETED Meeting zu bearbeiten
    - Assert: Redirect mit Error-Message

#### Meeting Delete Tests

15. **test_meeting_delete_requires_permission**
    - User ohne Permission versucht Meeting zu löschen
    - Assert: 403 Forbidden

16. **test_meeting_delete_success_for_draft**
    - Admin löscht DRAFT Meeting
    - Assert: Meeting gelöscht, Redirect zu List

17. **test_meeting_delete_blocked_for_non_draft**
    - Versuch SENT Meeting zu löschen
    - Assert: Redirect mit Error-Message

#### Meeting Send Invitation Tests

18. **test_send_invitation_requires_permission**
    - User ohne Permission versucht Einladung zu senden
    - Assert: 403 Forbidden

19. **test_send_invitation_success**
    - Admin sendet Einladung für DRAFT Meeting
    - Assert: Status='SENT', sent_at gesetzt

20. **test_send_invitation_blocked_for_completed**
    - Versuch Einladung für COMPLETED Meeting zu senden
    - Assert: Redirect mit Error-Message

#### Meeting Complete Tests

21. **test_complete_meeting_success**
    - Admin schließt SENT Meeting ab (Datum in Vergangenheit)
    - Assert: Status='COMPLETED'

22. **test_complete_meeting_blocked_for_future**
    - Versuch SENT Meeting mit Zukunfts-Datum abzuschließen
    - Assert: Redirect mit Error-Message

23. **test_complete_meeting_blocked_for_draft**
    - Versuch DRAFT Meeting abzuschließen
    - Assert: Redirect mit Error-Message

**Siehe:** CODE_STYLE_GUIDE.md → "Django Best Practices → Testing"

---

## Phase 6: Erweiterte Features & Utils

### Ziel
Helper-Funktionen und erweiterte Features für Meetings implementieren.

### Schritt 6.1: Helper-Funktionen

**Datei:** `apps/meetings/utils.py`

**5 Helper-Funktionen zu implementieren:**

#### 1. generate_meeting_number

**Signatur:** `generate_meeting_number(committee, date)`

**Zweck:** Generiert fortlaufende Sitzungsnummer pro Committee und Jahr (Format: YYYY-NN)

**Returns:** str (z.B. "2026-05")

#### 2. get_next_meeting

**Signatur:** `get_next_meeting(committee)`

**Zweck:** Holt die nächste bevorstehende Sitzung eines Gremiums

**Returns:** Meeting or None

#### 3. get_last_completed_meeting

**Signatur:** `get_last_completed_meeting(committee)`

**Zweck:** Holt die letzte abgeschlossene Sitzung eines Gremiums

**Returns:** Meeting or None

#### 4. calculate_meeting_statistics

**Signatur:** `calculate_meeting_statistics(committee, year=None)`

**Zweck:** Berechnet Sitzungsstatistiken für ein Gremium

**Returns:** dict mit total_meetings, completed_meetings, upcoming_meetings, draft_meetings, average_duration_minutes

#### 5. check_meeting_conflicts

**Signatur:** `check_meeting_conflicts(meeting)`

**Zweck:** Prüft ob es Termin-Konflikte mit anderen Meetings gibt (nur gleiche oder übergeordnete Committees)

**Algorithmus:**
```python
from django.db.models import Q, QuerySet

def check_meeting_conflicts(meeting: 'Meeting') -> QuerySet['Meeting']:
    """
    Check if a meeting has scheduling conflicts with other meetings.
    
    A conflict exists if:
    - Same committee OR parent committee (übergeordnetes Gremium)
    - Same date
    - Overlapping time ranges
    
    Args:
        meeting: Meeting instance
    
    Returns:
        QuerySet of conflicting meetings
    """
    # Build list of committees to check for conflicts
    committees_to_check = [meeting.committee]
    
    # Add parent committee if exists
    if meeting.committee.parent:
        committees_to_check.append(meeting.committee.parent)
    
    # Check for conflicts in same or parent committee
    conflicts = Meeting.objects.filter(
        committee__in=committees_to_check,
        date=meeting.date
    ).exclude(pk=meeting.pk)
    
    # Check for time overlap
    # A meeting conflicts if:
    # - It starts before this meeting ends AND
    # - It ends after this meeting starts
    if meeting.end_time:
        conflicts = conflicts.filter(
            Q(start_time__lt=meeting.end_time, end_time__gt=meeting.start_time) |
            Q(start_time__lt=meeting.end_time, end_time__isnull=True) |
            Q(start_time__gte=meeting.start_time, start_time__lt=meeting.end_time)
        )
    
    return conflicts
```

**Siehe:** CODE_STYLE_GUIDE.md → "Clean Code Principles → Functions"

---

### Schritt 6.2: Utils-Tests

**Datei:** `apps/meetings/tests/test_utils.py`

**Tests zu implementieren:**

1. **test_generate_meeting_number_first_of_year**
   - Erstes Meeting in 2026
   - Assert: meeting_number == "2026-01"

2. **test_generate_meeting_number_increments**
   - Drei Meetings im gleichen Jahr
   - Assert: "2026-01", "2026-02", "2026-03"

3. **test_generate_meeting_number_different_years**
   - Meetings in 2026 und 2027
   - Assert: "2026-01", "2027-01"

4. **test_get_next_meeting_returns_upcoming**
   - Meeting in 7 Tagen erstellen
   - Assert: get_next_meeting() gibt dieses Meeting zurück

5. **test_get_next_meeting_returns_none_if_no_upcoming**
   - Nur vergangene Meetings
   - Assert: get_next_meeting() == None

6. **test_get_last_completed_meeting**
   - Mehrere COMPLETED Meetings
   - Assert: Gibt das neueste zurück

7. **test_get_last_completed_meeting_ignores_non_completed**
   - COMPLETED und DRAFT Meetings
   - Assert: Gibt nur COMPLETED zurück

8. **test_calculate_meeting_statistics**
   - Mehrere Meetings mit verschiedenen Status
   - Assert: Alle Zähler korrekt

9. **test_calculate_meeting_statistics_average_duration**
   - 3 COMPLETED Meetings mit actual_start/end_time
   - Assert: average_duration korrekt berechnet

10. **test_check_meeting_conflicts_same_time**
    - Zwei Meetings zur gleichen Zeit
    - Assert: Konflikt erkannt

11. **test_check_meeting_conflicts_overlapping**
    - Meeting 10:00-12:00, anderes 11:00-13:00
    - Assert: Konflikt erkannt

12. **test_check_meeting_conflicts_no_conflict**
    - Meeting 10:00-12:00, anderes 13:00-15:00
    - Assert: Kein Konflikt

13. **test_check_meeting_conflicts_different_committee**
    - Gleiche Zeit, unterschiedliche Committees
    - Assert: Kein Konflikt

**Siehe:** CODE_STYLE_GUIDE.md → "Django Best Practices → Testing"

---

### Schritt 6.3: HTMX-Features (Progressive Enhancement)

**Ziel:** Live-Updates und Inline-Status-Änderung

#### URLs ergänzen

**Datei:** `apps/meetings/urls.py` ergänzen

**Neue HTMX-Endpoints:**
- `'<uuid:pk>/update-status/'` → MeetingUpdateStatusView (name='meeting_update_status')
- `'search/'` → MeetingSearchView (name='meeting_search')

#### View 1: MeetingUpdateStatusView

**Datei:** `apps/meetings/views.py` ergänzen

**Extends:** LoginRequiredMixin, MeetingPermissionMixin, View

**Funktionalität:**
- AJAX-Endpoint für Status-Änderung
- Gibt nur HTML-Fragment zurück (_meeting_status_badge.html)
- Validiert Status-Workflow-Regeln

**Attribute:**
- required_permission: 'meeting.change_status'

**post():**
```python
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render, get_object_or_404
from django.utils import timezone

def post(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
    """
    Handle status change request with granular permission checks.
    
    Validates status transition and checks permission based on target status.
    """
    meeting = get_object_or_404(Meeting, pk=kwargs['pk'])
    new_status = request.POST.get('status')
    
    # Validate status transition
    valid_transitions = {
        'DRAFT': ['SENT'],
        'SENT': ['IN_PROGRESS'],
        'IN_PROGRESS': ['COMPLETED'],
        'COMPLETED': []
    }
    
    if new_status not in valid_transitions.get(meeting.status, []):
        return JsonResponse({
            'error': f'Ungültiger Status-Übergang von {meeting.status} zu {new_status}'
        }, status=400)
    
    # Check granular permission based on transition
    permission_checks = {
        'SENT': Meeting.user_can_send_invitation,
        'IN_PROGRESS': Meeting.user_can_start_meeting,
        'COMPLETED': Meeting.user_can_complete_meeting,
    }
    
    permission_errors = {
        'SENT': 'Keine Berechtigung zum Versenden der Einladung',
        'IN_PROGRESS': 'Keine Berechtigung zum Starten des Meetings',
        'COMPLETED': 'Keine Berechtigung zum Abschließen des Meetings',
    }
    
    check_func = permission_checks.get(new_status)
    if check_func and not check_func(request.user, meeting):
        return JsonResponse({
            'error': permission_errors[new_status]
        }, status=403)
    
    # Update status
    meeting.status = new_status
    if new_status == 'SENT' and not meeting.sent_at:
        meeting.sent_at = timezone.now()
    meeting.save()
    
    # Return HTML fragment for HTMX
    return render(request, 'meetings/_meeting_status_badge.html', {'meeting': meeting})
```

#### View 2: MeetingSearchView

**Datei:** `apps/meetings/views.py` ergänzen

**Extends:** LoginRequiredMixin, MeetingPermissionMixin, ListView

**Funktionalität:**
- Live-Suche in Meeting-Liste via HTMX
- Filtert nach Titel, Sitzungsnummer, Committee-Name
- Gibt nur HTML-Fragment zurück (_meeting_list_rows.html)

**Attribute:**
- model: Meeting
- template_name: 'meetings/_meeting_list_rows.html'
- context_object_name: 'meetings'
- required_permission: 'meeting.view'

**get_queryset():** Filtert nach Titel, Sitzungsnummer, Committee-Name (Q objects mit icontains)

#### Templates für HTMX

**3 Partials zu erstellen:**

1. **`meetings/_meeting_status_badge.html`**
   - Einzelner Status-Badge (<span>)
   - Farbcodierung je nach Status:
     - DRAFT: secondary
     - SENT: info
     - IN_PROGRESS: primary
     - COMPLETED: success

2. **`meetings/_meeting_list_rows.html`**
   - Loop über meetings
   - Include: `_meeting_row.html` für jede Zeile

3. **`meetings/_meeting_row.html`**
   - Einzelne Tabellenzeile (<tr>)
   - Spalten: Sitzungsnummer, Titel, Gremium, Datum, Uhrzeit, Typ, Status-Badge, Aktionen

#### meeting_list.html erweitern

**Datei:** `meetings/meeting_list.html` anpassen

**Änderungen:**
- Suchfeld mit hx-get="/meetings/search/" hinzufügen
- hx-trigger="keyup changed delay:300ms"
- hx-target="#meeting-table-body"
- Tabelle: <tbody id="meeting-table-body"> mit {% include '_meeting_list_rows.html' %}

#### meeting_detail.html erweitern

**Datei:** `meetings/meeting_detail.html` anpassen

**Änderungen:**
- Status-Badge mit hx-trigger für Inline-Status-Änderung
- Dropdown-Menü für erlaubte Status-Übergänge
- hx-post="/meetings/<pk>/update-status/"
- hx-target="closest .status-badge-container"

---

## Validierung nach jeder Phase

### Checkliste nach Abschluss einer Phase:

**1. Migrations prüfen:**
```bash
python manage.py makemigrations --check --dry-run
python manage.py showmigrations meetings
```

**2. Admin-Interface testen:**
- http://localhost:8000/admin/meetings/
- Alle Models sichtbar?
- CRUD-Operationen funktionieren?
- Autocomplete funktioniert?

**3. URLs testen:**
```bash
python manage.py show_urls | grep meetings
```

**4. Alle Tests ausführen:**
```bash
# Alle Tests
pytest apps/meetings/tests/

# Nur Model-Tests
pytest apps/meetings/tests/test_models.py

# Nur View-Tests
pytest apps/meetings/tests/test_views.py

# Mit Coverage
pytest --cov=apps.meetings --cov-report=html
```

**5. Frontend testen:**
- Login als Superuser
- Meeting erstellen (alle drei Typen: ONLINE, HYBRID, IN_PERSON)
- Dynamisches Formular testen (Typ wechseln)
- Meeting bearbeiten (nur DRAFT)
- Einladung versenden (Status-Übergang)
- Meeting abschließen
- Filter-Funktionen testen
- HTMX-Features testen:
  - Live-Suche in Meeting-Liste
  - Inline-Status-Änderung

**6. Code-Qualität prüfen:**
```bash
# Type-Checking
mypy apps/meetings

# Linting
ruff check apps/meetings
```

**Siehe:** CODE_STYLE_GUIDE.md → "Django Best Practices → Testing"

---

## Deployment-Vorbereitung

### Konstanten in settings definieren

**In `config/settings/base.py`:**

```python
# Meeting Settings
DEFAULT_MEETING_TYPE = 'IN_PERSON'
MEETING_NUMBER_FORMAT = '{year}-{count:02d}'
MEETING_REMINDER_DAYS_BEFORE = [7, 3, 1]  # Erinnerungen 7, 3 und 1 Tag vorher

# Status Workflow
MEETING_STATUS_TRANSITIONS = {
    'DRAFT': ['SENT'],
    'SENT': ['IN_PROGRESS'],
    'IN_PROGRESS': ['COMPLETED'],
    'COMPLETED': []
}

# Location validation
REQUIRE_FULL_ADDRESS_FOR_IN_PERSON = True
REQUIRE_URL_FOR_ONLINE = True
```

**Siehe:** CODE_STYLE_GUIDE.md → "Clean Code Principles → Use Constants"

### Initial Data Seeds

**Commands in richtiger Reihenfolge ausführen:**

```bash
# 1. Permissions erstellen
python manage.py seed_meeting_permissions

# 2. SYSTEM_ADMIN Permissions zuweisen
python manage.py assign_meeting_permissions

# 3. Optional: Demo-Daten erstellen (nur Development)
# python manage.py seed_demo_meetings
```

---

## Zusammenfassung

### Implementierungs-Reihenfolge:

1. ✅ Phase 1: Projekt-Setup & Basis-Modell (Meeting mit vollständiger Validierung)
2. ✅ Phase 2: Admin-Interface
3. ✅ Phase 3: Berechtigungen & Seed-Daten
4. ✅ Phase 4: Forms & Dynamische Validierung
5. ✅ Phase 5: Views & Templates
6. ✅ Phase 6: Erweiterte Features & Utils
   - Schritt 6.1: Helper-Funktionen (meeting_number, statistics, conflicts)
   - Schritt 6.2: Utils-Tests
   - Schritt 6.3: HTMX-Features (Live-Suche, Inline-Status-Update)

### Code-Qualität sicherstellen:

- **Clean Code:** Siehe CODE_STYLE_GUIDE.md
- **Type Hints:** Für alle Funktionen
- **Docstrings:** Google Style, Pflicht
- **DRY:** Keine Code-Duplikation
- **Tests:** Für ALLE Funktionen und Views (nicht optional!)
- **Test Coverage:** Minimum 80% anstreben

### Wichtige Referenzen:

- CODE_STYLE_GUIDE.md (Alle Code-Beispiele)
- docs/apps/05_meetings.md (Detaillierte Anforderungen)
- docs/06_berechtigungskonzept.md (Permission-Matrix)

### Besondere Validierungen:

- ✅ Meeting-Typ-spezifische Location-Validierung (ONLINE/HYBRID/IN_PERSON)
- ✅ Zeit-Constraints (end_time > start_time)
- ✅ Chair/Clerk müssen Committee-Mitglieder sein
- ✅ Status-Workflow-Validierung (nur erlaubte Übergänge)
- ✅ Bearbeitungs-/Lösch-Rechte basierend auf Status
- ✅ Automatische Sitzungsnummer-Generierung
- ✅ Termin-Konflikt-Erkennung (gleiche/übergeordnete Committees)

### Neue Features:

- ✅ **Dynamisches Formular:** Felder passen sich dem meeting_type an
- ✅ **Auto-Generate meeting_number:** Format YYYY-NN pro Committee
- ✅ **Status-Workflow:** DRAFT → SENT → IN_PROGRESS → COMPLETED
- ✅ **Flexible Chair/Clerk-Auswahl:** Dropdown aus allen Committee-Mitgliedern, Standard via Permissions
- ✅ **Granulare Berechtigungen:** Separate Permissions pro Status-Übergang (send_invitation, start_meeting, complete_meeting)
- ✅ **View-Permission:** meeting.view für Kontrolle über Gäste/Externe
- ✅ **Properties für Business Logic:** is_editable, is_deletable, can_send_invitation, can_complete
- ✅ **Permission-Helper-Methoden:** user_can_send_invitation(), user_can_start_meeting(), user_can_complete_meeting(), user_can_view_meeting()
- ✅ **Formatierte Location:** get_full_location basierend auf Typ
- ✅ **Dauer-Berechnung:** Geplant (end_time - start_time) und Tatsächlich (actual_end_time - actual_start_time)
- ✅ **HTMX Live-Suche:** Echtzeit-Filterung der Meeting-Liste
- ✅ **HTMX Inline-Status-Update:** Status direkt in der Detailansicht ändern mit granularen Permission-Checks
- ✅ **Meeting-Statistiken:** Sitzungszahlen und Durchschnittsdauer pro Gremium
- ✅ **Konflikt-Erkennung:** Prüfung auf Zeit-Überschneidungen nur mit gleichem oder übergeordnetem Committee

---

## Nächste Schritte nach Meetings

Nach erfolgreicher Implementierung:
1. **Agendas-App** (verwendet Meetings) - Tagesordnungspunkte
2. **Attendance-App** (verwendet Meetings + Committees) - Anwesenheitsverwaltung
3. **Minutes-App** (verwendet Meetings + Agendas) - Protokollführung
4. **Resolutions-App** (verwendet Meetings + Agendas) - Beschlüsse
5. **Weitere Apps** gemäß Projektplan

### Integration mit späteren Apps:

**Meetings wird verwendet in:**
- `agendas`-App: Tagesordnungspunkte für Meetings (1:N)
- `attendance`-App: Anwesenheitserfassung für Meetings (1:N)
- `minutes`-App: Protokolle für Meetings (1:1)
- `resolutions`-App: Beschlüsse über Agenda-Items in Meetings (1:N)
- `calendar_mgmt`-App: Kalender-Events für Meetings (1:1)
- `notifications`-App: E-Mail-Versand für Einladungen und Erinnerungen

**E-Mail-Integration (später):**
- Einladung versenden → alle Committee-Mitglieder
- Erinnerungs-E-Mails → X Tage vor Sitzung (konfigurierbar)
- Protokoll-Versand → nach Abschluss
