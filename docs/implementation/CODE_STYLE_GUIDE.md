# Code Style Guide - BR-Manager

## Inhaltsverzeichnis

1. [Projektspezifische Konventionen](#projektspezifische-konventionen)
2. [Sprachkonventionen](#sprachkonventionen)
3. [Clean Code Principles](#clean-code-principles)
4. [Django Best Practices](#django-best-practices)
5. [Code-Beispiele](#code-beispiele)

---

## Projektspezifische Konventionen

### Package Management: UV

**Regel:** Verwende **ausschließlich** `uv` für Package-Management.

```bash
# ✅ Korrekt - Pakete mit uv installieren
uv add django
uv add loguru pydantic-settings
uv add --dev pytest pytest-django

# ✅ Korrekt - Pakete entfernen
uv remove package-name

# ✅ Korrekt - Dependencies synchronisieren
uv sync

# ❌ Falsch - pip verwenden
pip install django  # ❌ NICHT VERWENDEN
```

**Warum uv?**
- ⚡ Bis zu 10x schneller als pip
- 🔒 Lock-File (`uv.lock`) für reproduzierbare Builds
- 📦 Besseres Dependency-Management
- 🎯 Projekt-Standard

---

### Django Apps erstellen

**Regel:** Neue Django-Apps **immer** mit `manage.py startapp` erstellen.

```bash
# ✅ Korrekt - App mit Django-Command erstellen
python manage.py startapp myapp apps/myapp

# ❌ Falsch - Manuelle Ordnerstruktur
mkdir apps/myapp  # ❌ NICHT VERWENDEN
touch apps/myapp/models.py
```

**Warum?**
- Erstellt automatisch alle benötigten Dateien
- Generiert korrekte `apps.py` mit AppConfig
- Verhindert vergessene Dateien
- Django-Standard

**Erstellt automatisch:**
- `__init__.py`
- `models.py`
- `views.py`
- `admin.py`
- `apps.py`
- `tests.py`
- `migrations/` Verzeichnis

---

### Migrations

**Regel:** Migrations immer generieren lassen, nie manuell erstellen.

```bash
# ✅ Korrekt - Migrations erstellen
python manage.py makemigrations
python manage.py makemigrations accounts  # Spezifische App
python manage.py migrate

# ✅ Korrekt - Migrations prüfen vor Commit
python manage.py makemigrations --check --dry-run

# ✅ Korrekt - Migration-Status prüfen
python manage.py showmigrations

# ❌ Falsch - Manuelle Migration-Dateien
# Niemals Migrations-Dateien händisch schreiben!
```

**Best Practices:**
- Vor jedem Commit: `makemigrations --check`
- Migrations in Git committen
- Aussagekräftige Migration-Namen
- Bei Konflikten: `python manage.py makemigrations --merge`

---

### Git Workflow

**Regel:** Aussagekräftige Commit-Messages auf Englisch (Semantic Commits).

```bash
# ✅ Korrekt - Semantic Commit Messages
git commit -m "feat: add user invitation functionality"
git commit -m "fix: resolve 2FA validation bug"
git commit -m "refactor: extract email sending to service layer"
git commit -m "docs: update CODE_STYLE_GUIDE with clean code principles"
git commit -m "test: add unit tests for UserInvitation model"
git commit -m "chore: update dependencies via uv"

# ❌ Falsch - Unklare Messages
git commit -m "update"           # ❌ Was wurde aktualisiert?
git commit -m "fixes"            # ❌ Was wurde gefixt?
git commit -m "WIP"              # ❌ Niemals committen!
git commit -m "asdf"             # ❌ Sinnlos
```

**Commit-Types:**
- `feat:` - Neues Feature
- `fix:` - Bugfix
- `refactor:` - Code-Refactoring ohne Funktionsänderung
- `docs:` - Dokumentation
- `test:` - Tests hinzufügen/ändern
- `chore:` - Build-Prozess, Dependencies, Konfiguration
- `style:` - Code-Formatierung (keine Logikänderung)
- `perf:` - Performance-Verbesserung

**Beispiele mit Scope:**
```bash
git commit -m "feat(accounts): add user invitation via email"
git commit -m "fix(roles): correct permission check for CHAIR role"
git commit -m "test(accounts): add integration tests for 2FA workflow"
```

---

## Sprachkonventionen

### Regel: Code = Englisch, User-Facing Strings = Deutsch

| Element | Sprache | Beispiel |
|---------|---------|----------|
| **Variablen** | 🇬🇧 Englisch | `user_email`, `created_at`, `is_active` |
| **Funktionen** | 🇬🇧 Englisch | `create_user()`, `send_invitation()` |
| **Klassen** | 🇬🇧 Englisch | `UserManager`, `UserInvitation` |
| **Kommentare** | 🇬🇧 Englisch | `# Create new instance` |
| **Docstrings** | 🇬🇧 Englisch | `"""Create and save user."""` |
| **verbose_name** | 🇩🇪 Deutsch | `verbose_name='Benutzer'` |
| **Form labels** | 🇩🇪 Deutsch | `label='E-Mail-Adresse'` |
| **Templates** | 🇩🇪 Deutsch | `<h1>Willkommen</h1>` |
| **Messages** | 🇩🇪 Deutsch | `'Benutzer wurde erstellt'` |
| **E-Mails** | 🇩🇪 Deutsch | `'Einladung zum BR-Manager'` |

### Beispiel: Model

```python
# ✅ Korrekt
class User(AbstractBaseUser, PermissionsMixin):
    """
    Custom user model with UUID primary key.
    Login is performed via email address.
    """
    
    GENDER_CHOICES = [
        ('M', 'Männlich'),  # ✅ Display value in German
        ('F', 'Weiblich'),
    ]
    
    # Field names in English
    email = models.EmailField(
        unique=True,
        verbose_name='E-Mail-Adresse',  # ✅ Label in German
        help_text='Wird als Login verwendet'  # ✅ Help text in German
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='Aktiv'  # ✅ German
    )
    
    class Meta:
        verbose_name = 'Benutzer'  # ✅ German for admin
        verbose_name_plural = 'Benutzer'


# ❌ Falsch
class Benutzer(AbstractBaseUser):  # ❌ Class name in German
    email_adresse = models.EmailField(...)  # ❌ Field name in German
    ist_aktiv = models.BooleanField(...)  # ❌ Field name in German
```

---

## Clean Code Principles

*Basierend auf [Clean Code Python](https://github.com/zedr/clean-code-python) und Robert C. Martin's "Clean Code"*

### 1. Meaningful Variable Names

**Regel:** Verwende sprechende, aussprechbare, suchbare Variablennamen.

```python
# ❌ Bad
ymdstr = datetime.date.today().strftime("%y-%m-%d")
usr = User.objects.get(pk=1)
n = 5
x = 86400

# ✅ Good
current_date = datetime.date.today().strftime("%y-%m-%d")
current_user = User.objects.get(pk=1)
max_retry_attempts = 5
SECONDS_IN_A_DAY = 86400
```

**Django-Beispiel:**

```python
# ❌ Bad
inv = UserInvitation.objects.filter(e=email, u=True)
exp = timezone.now() + timedelta(days=7)

# ✅ Good
active_invitations = UserInvitation.objects.filter(
    email=email,
    is_used=True
)
INVITATION_VALIDITY_DAYS = 7
expires_at = timezone.now() + timedelta(days=INVITATION_VALIDITY_DAYS)
```

---

### 2. Use Constants for Magic Numbers

**Regel:** Benannte Konstanten statt "Magic Numbers".

```python
# ❌ Bad
time.sleep(86400)
invitation.expires_at = timezone.now() + timedelta(days=7)
if len(password) < 12:
    raise ValidationError('Passwort zu kurz')

# ✅ Good
SECONDS_IN_A_DAY = 60 * 60 * 24
time.sleep(SECONDS_IN_A_DAY)

INVITATION_VALIDITY_DAYS = 7
invitation.expires_at = timezone.now() + timedelta(days=INVITATION_VALIDITY_DAYS)

MIN_PASSWORD_LENGTH = 12
if len(password) < MIN_PASSWORD_LENGTH:
    raise ValidationError(f'Passwort muss mindestens {MIN_PASSWORD_LENGTH} Zeichen haben')
```

**In Django settings.py:**

```python
# config/settings/base.py

# Session configuration
SESSION_COOKIE_AGE = 1800  # 30 minutes
SESSION_MAX_AGE = 28800  # 8 hours

# Invitation settings
INVITATION_VALIDITY_DAYS = 7
INVITATION_MAX_PER_USER = 10

# Password settings
MIN_PASSWORD_LENGTH = 12
PASSWORD_HISTORY_COUNT = 5
PASSWORD_MAX_AGE_DAYS = 90
```

---

### 3. Avoid Mental Mapping

**Regel:** Explizit ist besser als implizit.

```python
# ❌ Bad - What does 'l' mean?
locations = ['Berlin', 'Munich', 'Hamburg']
for l in locations:  # ❌ Single letter variable
    process(l)

# ✅ Good
locations = ['Berlin', 'Munich', 'Hamburg']
for location in locations:
    process(location)

# Django Example
# ❌ Bad
for u in User.objects.all():  # ❌ What is 'u'?
    send_email(u)

# ✅ Good
for user in User.objects.all():
    send_email(user)
```

---

### 4. Don't Add Unneeded Context

**Regel:** Kontext aus Klasse/Modul ist ausreichend.

```python
# ❌ Bad - Redundant prefixes
class User:
    user_first_name: str  # ❌ "user_" is redundant
    user_last_name: str
    user_email: str
    
    def get_user_full_name(self):  # ❌ "user_" is redundant
        return f"{self.user_first_name} {self.user_last_name}"

# ✅ Good
class User:
    first_name: str
    last_name: str
    email: str
    
    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"
```

---

### 5. Functions Should Do One Thing (SRP)

**Regel:** Single Responsibility Principle - Eine Funktion = Eine Aufgabe.

```python
# ❌ Bad - Too many responsibilities
def invite_user(email):
    # Validate
    if not email:
        raise ValidationError('Email required')
    
    # Create invitation
    token = secrets.token_urlsafe(32)
    invitation = UserInvitation.objects.create(
        email=email,
        token=token,
        expires_at=timezone.now() + timedelta(days=7)
    )
    
    # Send email
    send_mail(
        subject='Invitation',
        message=f'Click here: {token}',
        recipient_list=[email]
    )
    
    # Log
    logger.info(f'Invited {email}')
    
    # Update stats
    stats = Statistics.objects.first()
    stats.invitations_sent += 1
    stats.save()
    
    return invitation

# ✅ Good - Separated concerns
def validate_email(email: str) -> None:
    """Validate email address format and presence."""
    if not email:
        raise ValidationError('E-Mail-Adresse erforderlich')
    
    # Additional validation if needed
    if '@' not in email:
        raise ValidationError('Ungültige E-Mail-Adresse')

def create_invitation(email: str, invited_by: User) -> UserInvitation:
    """Create a new user invitation with secure token."""
    token = secrets.token_urlsafe(32)
    return UserInvitation.objects.create(
        email=email,
        token=token,
        invited_by=invited_by,
        expires_at=timezone.now() + timedelta(days=INVITATION_VALIDITY_DAYS)
    )

def send_invitation_email(invitation: UserInvitation, invite_url: str) -> None:
    """Send invitation email to user."""
    send_mail(
        subject='Einladung zum BR-Manager',
        message=f'Registrieren Sie sich hier: {invite_url}',
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[invitation.email]
    )

def log_invitation_sent(email: str) -> None:
    """Log invitation activity."""
    logger.info(f'Invitation sent to {email}')

def increment_invitation_statistics() -> None:
    """Increment invitation counter in statistics."""
    stats, _ = Statistics.objects.get_or_create(pk=1)
    stats.invitations_sent += 1
    stats.save()

# Coordinator function
def invite_user(email: str, invited_by: User, request) -> UserInvitation:
    """
    Complete user invitation workflow.
    
    Validates email, creates invitation, sends email, and updates statistics.
    """
    validate_email(email)
    
    invitation = create_invitation(email, invited_by)
    
    invite_url = request.build_absolute_uri(
        reverse('accounts:register', kwargs={'token': invitation.token})
    )
    
    send_invitation_email(invitation, invite_url)
    log_invitation_sent(email)
    increment_invitation_statistics()
    
    return invitation
```

---

### 6. Function Arguments (2-3 Maximum)

**Regel:** Maximal 2-3 Argumente. Bei mehr: Dataclass oder **kwargs verwenden.

```python
# ❌ Bad - Too many arguments
def create_user(
    email,
    first_name,
    last_name,
    gender,
    phone,
    department,
    employee_id,
    is_active
):
    pass

# ✅ Good - Use dataclass
from dataclasses import dataclass
from typing import Optional

@dataclass
class UserData:
    email: str
    first_name: str
    last_name: str
    gender: str
    phone: str = ''
    department: str = ''
    employee_id: str = ''
    is_active: bool = True

def create_user(user_data: UserData) -> User:
    """Create a new user from UserData object."""
    return User.objects.create(
        email=user_data.email,
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        gender=user_data.gender,
        phone=user_data.phone,
        is_active=user_data.is_active
    )

# Usage
user_data = UserData(
    email='test@example.com',
    first_name='Max',
    last_name='Mustermann',
    gender='M'
)
user = create_user(user_data)
```

---

### 7. Use Type Hints

**Regel:** Immer Type Hints verwenden für bessere IDE-Unterstützung.

```python
# ❌ Bad - No type hints
def send_email(recipient, subject, message):
    pass

def get_user(user_id):
    return User.objects.get(pk=user_id)

# ✅ Good - With type hints
from typing import Optional, List
from uuid import UUID

def send_email(
    recipient: str,
    subject: str,
    message: str,
    attachments: Optional[List[str]] = None
) -> bool:
    """
    Send email to recipient.
    
    Args:
        recipient: Email address
        subject: Email subject
        message: Email body
        attachments: Optional list of file paths
    
    Returns:
        True if email was sent successfully
    """
    # Implementation
    return True

def get_user(user_id: UUID) -> Optional[User]:
    """
    Get user by ID.
    
    Args:
        user_id: UUID of user
    
    Returns:
        User object or None if not found
    """
    try:
        return User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return None
```

**Django Model Example:**

```python
from typing import Optional
from django.db import models

class UserInvitation(models.Model):
    """User invitation model."""
    
    email: str = models.EmailField()
    token: str = models.CharField(max_length=64)
    is_used: bool = models.BooleanField(default=False)
    
    def is_valid(self) -> bool:
        """Check if invitation is still valid."""
        from django.utils import timezone
        return not self.is_used and self.expires_at > timezone.now()
    
    def mark_as_used(self) -> None:
        """Mark invitation as used with timestamp."""
        from django.utils import timezone
        self.is_used = True
        self.used_at = timezone.now()
        self.save()
```

---

### 8. Docstrings sind Pflicht

**Regel:** Jede Funktion, Klasse und Methode benötigt einen Docstring.

**Google Style Docstring Format:**

```python
def function_name(param1: str, param2: int) -> bool:
    """
    Short one-line description of function.
    
    Longer description if needed. Can span multiple lines.
    Explain what the function does, not how it does it.
    
    Args:
        param1: Description of param1
        param2: Description of param2
    
    Returns:
        Description of return value
    
    Raises:
        ValueError: When param1 is empty
        UserNotFoundError: When user doesn't exist
    
    Example:
        >>> result = function_name('test', 42)
        >>> print(result)
        True
    """
    pass
```

**Vollständiges Beispiel:**

```python
from typing import Optional
from django.core.exceptions import ValidationError

def process_invitation(token: str) -> Optional[User]:
    """
    Validate invitation and create user account.
    
    Checks if the invitation token is valid and not expired.
    If valid, creates a new user account and marks the invitation as used.
    
    Args:
        token: Invitation token string (32-character URL-safe string)
    
    Returns:
        Created User object if successful, None otherwise
    
    Raises:
        ValidationError: If token is invalid or user already exists
    
    Example:
        >>> user = process_invitation('abc123xyz')
        >>> if user:
        ...     print(f'User created: {user.email}')
    
    Note:
        This function will send a welcome email to the new user.
    """
    # Implementation
    pass


class UserInvitation(models.Model):
    """
    Invitation for new users.
    
    Administrators can invite new users via email. An invitation link
    with a secure token is sent. The token is valid for 7 days.
    
    Attributes:
        email: Email address of invitee
        token: Secure random token (32 chars, URL-safe)
        invited_by: User who sent the invitation
        expires_at: Expiration datetime (7 days from creation)
        is_used: Whether invitation has been accepted
        used_at: Timestamp when invitation was used
    
    Example:
        >>> invitation = UserInvitation.objects.create(
        ...     email='new@example.com',
        ...     token=secrets.token_urlsafe(32),
        ...     invited_by=admin_user,
        ...     expires_at=timezone.now() + timedelta(days=7)
        ... )
        >>> if invitation.is_valid():
        ...     send_invitation_email(invitation)
    """
    pass
```

**Minimalanforderung:**

```python
# ✅ Minimum - One-liner für einfache Funktionen
def get_user_email(user: User) -> str:
    """Return user's email address."""
    return user.email

# ✅ Minimum - Klassen
class Permission(models.Model):
    """Permission model for role-based access control."""
    pass
```

---

### 9. Use Guard Clauses (Early Return)

**Regel:** Vermeide tief verschachtelte if-Bedingungen durch frühe Returns.

```python
# ❌ Bad - Deep nesting
def process_user_invitation(token: str) -> Optional[User]:
    if token:
        try:
            invitation = UserInvitation.objects.get(token=token)
            if invitation.is_valid():
                if not User.objects.filter(email=invitation.email).exists():
                    user = create_user(invitation.email)
                    invitation.mark_as_used()
                    return user
                else:
                    logger.error('User already exists')
                    return None
            else:
                logger.error('Invitation expired')
                return None
        except UserInvitation.DoesNotExist:
            logger.error('Invalid token')
            return None
    else:
        logger.error('No token provided')
        return None

# ✅ Good - Guard clauses
def process_user_invitation(token: str) -> Optional[User]:
    """Process user invitation and create account."""
    
    # Guard: Check token exists
    if not token:
        logger.warning('No token provided')
        return None
    
    # Guard: Get invitation
    try:
        invitation = UserInvitation.objects.get(token=token)
    except UserInvitation.DoesNotExist:
        logger.error(f'Invalid token: {token}')
        return None
    
    # Guard: Check validity
    if not invitation.is_valid():
        logger.error(f'Invitation expired for: {invitation.email}')
        return None
    
    # Guard: Check if user already exists
    if User.objects.filter(email=invitation.email).exists():
        logger.error(f'User already exists: {invitation.email}')
        return None
    
    # Happy path - no nesting!
    user = create_user(invitation.email)
    invitation.mark_as_used()
    logger.info(f'User created from invitation: {user.email}')
    
    return user
```

---

### 10. Don't Repeat Yourself (DRY)

**Regel:** Vermeide Code-Duplikation durch Extraktion gemeinsamer Logik.

```python
# ❌ Bad - Duplicated code
def create_user_from_invitation(invitation: UserInvitation) -> User:
    user = User.objects.create(
        email=invitation.email,
        is_active=True,
        date_joined=timezone.now()
    )
    UserProfile.objects.create(user=user)
    invitation.is_used = True
    invitation.used_at = timezone.now()
    invitation.save()
    return user

def create_user_from_oauth(oauth_data: dict) -> User:
    user = User.objects.create(
        email=oauth_data['email'],
        is_active=True,
        date_joined=timezone.now()
    )
    UserProfile.objects.create(user=user)
    return user

# ✅ Good - Extracted common logic
def create_user_with_profile(email: str, **extra_fields) -> User:
    """Create user and associated profile."""
    user = User.objects.create(
        email=email,
        is_active=True,
        date_joined=timezone.now(),
        **extra_fields
    )
    UserProfile.objects.create(user=user)
    return user

def create_user_from_invitation(invitation: UserInvitation) -> User:
    """Create user from invitation and mark it as used."""
    user = create_user_with_profile(invitation.email)
    invitation.mark_as_used()
    return user

def create_user_from_oauth(oauth_data: dict) -> User:
    """Create user from OAuth data."""
    return create_user_with_profile(
        email=oauth_data['email'],
        first_name=oauth_data.get('first_name', ''),
        last_name=oauth_data.get('last_name', '')
    )
```

---

### 11. Error Handling

**Regel:** Fange spezifische Exceptions, vermeide leere except-Blöcke.

```python
# ❌ Bad - Catching all exceptions
try:
    user = User.objects.get(email=email)
    send_email(user)
except:  # ❌ NEVER use bare except!
    pass

# ❌ Bad - Too broad
try:
    user = User.objects.get(email=email)
except Exception:  # ❌ Too broad
    pass

# ✅ Good - Specific exceptions
from loguru import logger
from django.core.mail import SMTPException

try:
    user = User.objects.get(email=email)
except User.DoesNotExist:
    logger.warning(f'User with email {email} not found')
    return None
except User.MultipleObjectsReturned:
    logger.error(f'Multiple users found for email {email}')
    raise

try:
    send_email(user)
except SMTPException as e:
    logger.error(f'Failed to send email to {user.email}: {e}')
    return False

return True
```

**Django-spezifische Exception-Behandlung:**

```python
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.db import IntegrityError

def create_unique_user(email: str) -> User:
    """Create user, handle duplicate email gracefully."""
    try:
        return User.objects.create(email=email)
    except IntegrityError:
        logger.error(f'User with email {email} already exists')
        raise ValidationError('E-Mail-Adresse bereits registriert')
    except Exception as e:
        logger.exception(f'Unexpected error creating user: {e}')
        raise
```

---

### 12. Avoid Side Effects

**Regel:** Funktionen sollten keine unerwarteten Nebeneffekte haben.

```python
# ❌ Bad - Hidden side effect
def check_password(username: str, password: str) -> bool:
    """Check if password is correct."""
    user = User.objects.get(username=username)
    is_valid = user.check_password(password)
    
    if is_valid:
        # ❌ Hidden side effect: creates session!
        Session.objects.create(user=user)
    
    return is_valid

# ✅ Good - Explicit separation
def check_password(user: User, password: str) -> bool:
    """Check if password is correct for user."""
    return user.check_password(password)

def create_user_session(user: User) -> Session:
    """Create a new session for user."""
    return Session.objects.create(user=user)

# Usage - Explicit and clear
if check_password(user, password):
    session = create_user_session(user)
```

---

## Django Best Practices

### Models

**1. Use UUID for Primary Keys**

```python
import uuid
from django.db import models

class User(models.Model):
    """User model with UUID primary key."""
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
```

**Warum UUIDs?**
- Keine ID-Enumeration möglich (Sicherheit)
- Verteilte Systeme (ID-Kollisionen vermeiden)
- URLs sehen professioneller aus
- Kann vor Speichern generiert werden

---

**2. Use verbose_name and help_text**

```python
class User(models.Model):
    email = models.EmailField(
        unique=True,
        verbose_name='E-Mail-Adresse',
        help_text='Wird als Login verwendet'
    )
    
    class Meta:
        verbose_name = 'Benutzer'
        verbose_name_plural = 'Benutzer'
        ordering = ['last_name', 'first_name']
```

---

**3. Custom Managers**

```python
class ActiveUserManager(models.Manager):
    """Manager for active users only."""
    
    def get_queryset(self):
        """Return only active users."""
        return super().get_queryset().filter(is_active=True)


class User(models.Model):
    is_active = models.BooleanField(default=True)
    
    objects = models.Manager()  # Default manager
    active = ActiveUserManager()  # Custom manager

# Usage
all_users = User.objects.all()
active_users = User.active.all()
```

---

**4. Model Methods**

```python
class User(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    
    def get_full_name(self) -> str:
        """Return user's full name."""
        return f"{self.first_name} {self.last_name}"
    
    def __str__(self) -> str:
        """String representation of user."""
        return self.get_full_name()
```

---

### Views

**1. Use Class-Based Views (CBVs)**

```python
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, CreateView

class UserListView(LoginRequiredMixin, ListView):
    """Display list of all users."""
    
    model = User
    template_name = 'accounts/user_list.html'
    context_object_name = 'users'
    paginate_by = 20
    
    def get_queryset(self):
        """Filter active users only."""
        return User.objects.filter(is_active=True)
```

**Warum CBVs?**
- DRY (Don't Repeat Yourself)
- Mixins für Wiederverwendbarkeit
- Weniger Code
- Django-Standard

---

**2. Custom Mixins**

```python
from django.contrib.auth.mixins import UserPassesTestMixin

class AdminRequiredMixin(UserPassesTestMixin):
    """Require admin permissions."""
    
    def test_func(self) -> bool:
        """Check if user is admin."""
        return self.request.user.is_superuser or \
               self.request.user.has_perm('system.admin')


class UserInviteView(LoginRequiredMixin, AdminRequiredMixin, CreateView):
    """Invite new users (admin only)."""
    pass
```

---

**3. Form Handling**

```python
from django.contrib import messages

class UserCreateView(CreateView):
    """Create new user."""
    
    model = User
    form_class = UserCreateForm
    
    def form_valid(self, form):
        """Handle valid form submission."""
        response = super().form_valid(form)
        
        messages.success(
            self.request,
            f'Benutzer {self.object.get_full_name()} wurde erstellt.'
        )
        
        return response
    
    def form_invalid(self, form):
        """Handle invalid form submission."""
        messages.error(
            self.request,
            'Fehler beim Erstellen des Benutzers.'
        )
        
        return super().form_invalid(form)
```

---

### Forms

**1. Model Forms**

```python
from django import forms

class UserCreateForm(forms.ModelForm):
    """Form for creating new users."""
    
    password = forms.CharField(
        label='Passwort',
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        help_text='Mindestens 12 Zeichen'
    )
    
    class Meta:
        model = User
        fields = ['email', 'first_name', 'last_name', 'gender']
        widgets = {
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'gender': forms.Select(attrs={'class': 'form-select'}),
        }
    
    def clean_email(self):
        """Validate email is unique."""
        email = self.cleaned_data['email']
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('E-Mail-Adresse bereits registriert')
        return email
```

---

**2. Custom Validation**

```python
class UserRegistrationForm(forms.ModelForm):
    """User registration form."""
    
    password = forms.CharField(widget=forms.PasswordInput)
    password_confirm = forms.CharField(widget=forms.PasswordInput)
    
    def clean(self):
        """Validate passwords match."""
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')
        
        if password and password_confirm and password != password_confirm:
            raise forms.ValidationError('Passwörter stimmen nicht überein')
        
        return cleaned_data
```

---

### Templates

**1. Verwende Template Inheritance**

```html
<!-- base.html -->
<!DOCTYPE html>
<html lang="de">
<head>
    <title>{% block title %}BR-Manager{% endblock %}</title>
    {% block extra_css %}{% endblock %}
</head>
<body>
    {% include 'partials/navbar.html' %}
    
    <main>
        {% block content %}{% endblock %}
    </main>
    
    {% include 'partials/footer.html' %}
    
    {% block extra_js %}{% endblock %}
</body>
</html>

<!-- user_list.html -->
{% extends 'base.html' %}

{% block title %}Benutzerverwaltung{% endblock %}

{% block content %}
<h1>Benutzer</h1>
<!-- ... -->
{% endblock %}
```

---

**2. Use Template Tags**

```python
# templatetags/user_tags.py
from django import template

register = template.Library()

@register.filter
def user_initials(user):
    """Return user initials (e.g. 'MM')."""
    return f"{user.first_name[0]}{user.last_name[0]}".upper()

# Usage in template
{{ user|user_initials }}
```

---

### Testing

**1. Test-Struktur**

```python
from django.test import TestCase
from apps.accounts.models import User

class UserModelTest(TestCase):
    """Tests for User model."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email='test@example.com',
            password='SecurePass123!',
            first_name='Max',
            last_name='Mustermann',
            gender='M'
        )
    
    def test_user_creation(self):
        """Test user is created correctly."""
        self.assertEqual(self.user.email, 'test@example.com')
        self.assertTrue(self.user.check_password('SecurePass123!'))
    
    def test_get_full_name(self):
        """Test get_full_name method."""
        self.assertEqual(
            self.user.get_full_name(),
            'Max Mustermann'
        )
    
    def test_str_representation(self):
        """Test string representation."""
        expected = 'Max Mustermann (test@example.com)'
        self.assertEqual(str(self.user), expected)
```

---

**2. Test Views**

```python
from django.test import TestCase, Client
from django.urls import reverse

class UserListViewTest(TestCase):
    """Tests for UserListView."""
    
    def setUp(self):
        """Set up test client and data."""
        self.client = Client()
        self.admin = User.objects.create_superuser(
            email='admin@example.com',
            password='AdminPass123!'
        )
    
    def test_login_required(self):
        """Test view requires login."""
        response = self.client.get(reverse('accounts:user_list'))
        self.assertEqual(response.status_code, 302)  # Redirect to login
    
    def test_admin_can_access(self):
        """Test admin can access user list."""
        self.client.login(
            username='admin@example.com',
            password='AdminPass123!'
        )
        response = self.client.get(reverse('accounts:user_list'))
        self.assertEqual(response.status_code, 200)
```

---

## Code-Beispiele

### Model Example (Vollständig)

```python
"""User invitation model."""

import uuid
import secrets
from datetime import timedelta
from typing import Optional

from django.conf import settings
from django.db import models
from django.utils import timezone


class UserInvitation(models.Model):
    """
    Invitation for new users.
    
    Administrators can invite new users via email. An invitation link
    with a secure token is sent. The token is valid for 7 days.
    """
    
    # Constants
    TOKEN_LENGTH = 32
    VALIDITY_DAYS = 7
    
    # Fields
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    email = models.EmailField(
        verbose_name='E-Mail-Adresse',
        help_text='E-Mail-Adresse des einzuladenden Benutzers'
    )
    token = models.CharField(
        max_length=64,
        unique=True,
        verbose_name='Einladungs-Token'
    )
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='sent_invitations',
        verbose_name='Eingeladen von'
    )
    created_at = models.DateTimeField(
        default=timezone.now,
        verbose_name='Erstellt am'
    )
    expires_at = models.DateTimeField(
        verbose_name='Gültig bis'
    )
    is_used = models.BooleanField(
        default=False,
        verbose_name='Verwendet'
    )
    used_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Verwendet am'
    )
    
    class Meta:
        verbose_name = 'Benutzer-Einladung'
        verbose_name_plural = 'Benutzer-Einladungen'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['token']),
            models.Index(fields=['email']),
        ]
    
    def __str__(self) -> str:
        """String representation."""
        return f"Einladung für {self.email}"
    
    def is_valid(self) -> bool:
        """
        Check if invitation is still valid.
        
        Returns:
            True if invitation is not used and not expired
        """
        return not self.is_used and self.expires_at > timezone.now()
    
    def mark_as_used(self) -> None:
        """Mark invitation as used with current timestamp."""
        self.is_used = True
        self.used_at = timezone.now()
        self.save(update_fields=['is_used', 'used_at'])
    
    @classmethod
    def create_invitation(
        cls,
        email: str,
        invited_by: 'User'
    ) -> 'UserInvitation':
        """
        Create a new invitation with secure token.
        
        Args:
            email: Email address of invitee
            invited_by: User who sent the invitation
        
        Returns:
            Created UserInvitation object
        """
        return cls.objects.create(
            email=email,
            token=secrets.token_urlsafe(cls.TOKEN_LENGTH),
            invited_by=invited_by,
            expires_at=timezone.now() + timedelta(days=cls.VALIDITY_DAYS)
        )
```

---

### View Example (Vollständig)

```python
"""User invitation views."""

import secrets
from datetime import timedelta
from typing import Optional

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.mail import send_mail
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse_lazy, reverse
from django.utils import timezone
from django.views.generic import CreateView, FormView
from loguru import logger

from .forms import UserInviteForm, UserRegistrationForm
from .models import User, UserInvitation, UserProfile


class AdminRequiredMixin(UserPassesTestMixin):
    """Mixin to require admin permissions."""
    
    def test_func(self) -> bool:
        """Check if user has admin permissions."""
        return (
            self.request.user.is_superuser or
            self.request.user.has_perm('accounts.manage_users')
        )


class UserInviteView(LoginRequiredMixin, AdminRequiredMixin, CreateView):
    """
    Invite new user via email.
    
    Only accessible by administrators. Sends invitation email
    with registration link valid for 7 days.
    """
    
    model = UserInvitation
    form_class = UserInviteForm
    template_name = 'accounts/user_invite.html'
    success_url = reverse_lazy('accounts:user_list')
    
    def form_valid(self, form):
        """
        Handle valid form submission.
        
        Creates invitation and sends email to invitee.
        """
        email = form.cleaned_data['email']
        
        # Check if user already exists
        if User.objects.filter(email=email).exists():
            messages.error(
                self.request,
                f'Benutzer mit E-Mail {email} existiert bereits.'
            )
            return self.form_invalid(form)
        
        # Create invitation
        invitation = UserInvitation.create_invitation(
            email=email,
            invited_by=self.request.user
        )
        
        # Generate invitation URL
        invite_url = self._build_invitation_url(invitation.token)
        
        # Send email
        self._send_invitation_email(invitation, invite_url)
        
        # Success message
        messages.success(
            self.request,
            f'Einladung wurde an {email} gesendet.'
        )
        
        logger.info(
            f'User {self.request.user.email} invited {email}'
        )
        
        return redirect(self.success_url)
    
    def _build_invitation_url(self, token: str) -> str:
        """Build absolute URL for invitation registration."""
        return self.request.build_absolute_uri(
            reverse('accounts:register', kwargs={'token': token})
        )
    
    def _send_invitation_email(
        self,
        invitation: UserInvitation,
        invite_url: str
    ) -> None:
        """Send invitation email to invitee."""
        send_mail(
            subject='Einladung zum BR-Manager',
            message=f'''Hallo,

Sie wurden von {self.request.user.get_full_name()} zum BR-Manager eingeladen.

Bitte klicken Sie auf den folgenden Link, um Ihr Konto einzurichten:
{invite_url}

Dieser Link ist 7 Tage gültig.

Mit freundlichen Grüßen
Ihr BR-Manager Team
''',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[invitation.email],
            fail_silently=False,
        )
```

---

## Zusammenfassung

### Quick Reference

| Kategorie | Regel |
|-----------|-------|
| **Packages** | Nur `uv add` verwenden |
| **Apps** | `python manage.py startapp` |
| **Variablen** | Englisch, sprechend, suchbar |
| **Funktionen** | 2-3 Args max, eine Aufgabe, Type Hints |
| **Docstrings** | Pflicht, Google Style |
| **Fehler** | Spezifische Exceptions |
| **Code** | DRY, Guard Clauses, kein Mental Mapping |
| **Commits** | Semantic, Englisch |
| **Tests** | Für alles, aussagekräftige Namen |

### Weitere Ressourcen

- [Clean Code Python](https://github.com/zedr/clean-code-python)
- [Django Best Practices](https://django-best-practices.readthedocs.io/)
- [PEP 8](https://pep8.org/)
- [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)
