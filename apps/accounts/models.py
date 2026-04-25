"""Models for accounts app."""

import uuid

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone


class UserManager(BaseUserManager):
    """Custom user manager for email-based authentication."""
    
    def create_user(self, email: str, password: str = None, **extra_fields) -> 'User':
        """
        Create and save a regular user with email and password.
        
        Args:
            email: User's email address
            password: User's password (will be hashed)
            **extra_fields: Additional fields for user model
        
        Returns:
            Created User object
        
        Raises:
            ValueError: If email is not provided
        """
        if not email:
            raise ValueError('E-Mail-Adresse muss angegeben werden')
        
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email: str, password: str = None, **extra_fields) -> 'User':
        """
        Create and save a superuser with email and password.
        
        Args:
            email: User's email address
            password: User's password (will be hashed)
            **extra_fields: Additional fields for user model
        
        Returns:
            Created superuser object
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser muss is_staff=True haben')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser muss is_superuser=True haben')
        
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """
    Custom user model with UUID primary key.
    
    Login is performed via email address instead of username.
    Includes fields for 2FA and BetrVG compliance (gender field).
    
    Attributes:
        id: UUID primary key
        email: Email address (unique, used for login)
        first_name: User's first name
        last_name: User's last name
        gender: Gender (required for § 15 Abs. 2 BetrVG)
        phone: Optional phone number
        is_active: Whether user account is active
        is_staff: Whether user can access admin site
        date_joined: Timestamp when user was created
        two_factor_enabled: Whether 2FA is enabled
        two_factor_method: 2FA method (TOTP/SMS)
        totp_secret: Secret key for TOTP 2FA
    """
    
    GENDER_CHOICES = [
        ('M', 'Männlich'),
        ('F', 'Weiblich'),
    ]
    
    TWO_FACTOR_METHOD_CHOICES = [
        ('TOTP', 'Authenticator App (TOTP)'),
        ('SMS', 'SMS'),
    ]
    
    # Primary fields
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    email = models.EmailField(
        unique=True,
        verbose_name='E-Mail-Adresse',
        help_text='Wird als Login verwendet'
    )
    
    # Personal information
    first_name = models.CharField(
        max_length=150,
        verbose_name='Vorname'
    )
    last_name = models.CharField(
        max_length=150,
        verbose_name='Nachname'
    )
    gender = models.CharField(
        max_length=1,
        choices=GENDER_CHOICES,
        verbose_name='Geschlecht',
        help_text='Pflichtangabe für § 15 Abs. 2 BetrVG (Geschlechterquote)'
    )
    phone = models.CharField(
        max_length=20,
        blank=True,
        verbose_name='Telefon'
    )
    
    # Status fields
    is_active = models.BooleanField(
        default=True,
        verbose_name='Aktiv'
    )
    is_staff = models.BooleanField(
        default=False,
        verbose_name='Staff-Status'
    )
    date_joined = models.DateTimeField(
        default=timezone.now,
        verbose_name='Beigetreten am'
    )
    
    # 2FA fields (prepared for Phase 3)
    two_factor_enabled = models.BooleanField(
        default=False,
        verbose_name='2FA aktiviert'
    )
    two_factor_method = models.CharField(
        max_length=10,
        choices=TWO_FACTOR_METHOD_CHOICES,
        blank=True,
        verbose_name='2FA-Methode'
    )
    totp_secret = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='TOTP-Secret'
    )
    
    objects = UserManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name', 'gender']
    
    class Meta:
        verbose_name = 'Benutzer'
        verbose_name_plural = 'Benutzer'
        ordering = ['last_name', 'first_name']
    
    def __str__(self) -> str:
        """String representation of user."""
        return f"{self.first_name} {self.last_name} ({self.email})"
    
    def get_full_name(self) -> str:
        """Return user's full name."""
        return f"{self.first_name} {self.last_name}"
    
    def get_short_name(self) -> str:
        """Return user's first name."""
        return self.first_name


class UserProfile(models.Model):
    """
    Extended user profile with additional information.
    
    OneToOne relationship to User for storing optional profile data
    like department, employee ID, and notification preferences.
    
    Attributes:
        id: UUID primary key
        user: OneToOne link to User
        department: User's department (optional)
        employee_id: Employee identification number (optional)
        notification_preferences: JSON field for notification settings
        avatar: Profile picture upload
    
    Example:
        >>> profile = UserProfile.objects.create(
        ...     user=user,
        ...     department='IT',
        ...     employee_id='EMP-12345'
        ... )
    """
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile',
        verbose_name='Benutzer'
    )
    department = models.CharField(
        max_length=200,
        blank=True,
        verbose_name='Abteilung'
    )
    employee_id = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='Mitarbeiter-ID'
    )
    notification_preferences = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='Benachrichtigungseinstellungen',
        help_text='JSON-Objekt mit Benachrichtigungseinstellungen'
    )
    avatar = models.ImageField(
        upload_to='avatars/',
        blank=True,
        null=True,
        verbose_name='Profilbild'
    )
    
    class Meta:
        verbose_name = 'Benutzerprofil'
        verbose_name_plural = 'Benutzerprofile'
    
    def __str__(self) -> str:
        """String representation."""
        return f"Profil von {self.user.get_full_name()}"


class TwoFactorRecoveryCode(models.Model):
    """
    Recovery codes for two-factor authentication.
    
    Each user gets multiple recovery codes that can be used as fallback
    when TOTP is not available. Codes are hashed before storage.
    
    Attributes:
        id: UUID primary key
        user: Foreign key to User
        code: Hashed recovery code
        is_used: Whether code has been used
        created_at: Creation timestamp
        used_at: Timestamp when code was used
    
    Example:
        >>> from django.contrib.auth.hashers import make_password
        >>> code = TwoFactorRecoveryCode.objects.create(
        ...     user=user,
        ...     code=make_password('RECOVERY-CODE-123')
        ... )
    """
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='recovery_codes',
        verbose_name='Benutzer'
    )
    code = models.CharField(
        max_length=255,
        verbose_name='Code (gehasht)',
        help_text='Recovery-Code wird gehasht gespeichert'
    )
    is_used = models.BooleanField(
        default=False,
        verbose_name='Verwendet'
    )
    created_at = models.DateTimeField(
        default=timezone.now,
        verbose_name='Erstellt am'
    )
    used_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Verwendet am'
    )
    
    class Meta:
        verbose_name = '2FA Recovery-Code'
        verbose_name_plural = '2FA Recovery-Codes'
        ordering = ['-created_at']
    
    def __str__(self) -> str:
        """String representation."""
        if self.is_used:
            return f"Recovery-Code für {self.user.email} (verwendet)"
        return f"Recovery-Code für {self.user.email} (verfügbar)"
    
    def mark_as_used(self) -> None:
        """Mark recovery code as used with timestamp."""
        self.is_used = True
        self.used_at = timezone.now()
        self.save(update_fields=['is_used', 'used_at'])


class UserInvitation(models.Model):
    """
    Invitation for new users.
    
    Administrators can invite new users via email. An invitation link
    with a secure token is sent. The token is valid for 7 days.
    
    Attributes:
        id: UUID primary key
        email: Email address of invitee
        token: Secure random token (URL-safe, 32 chars)
        invited_by: User who sent the invitation
        created_at: Creation timestamp
        expires_at: Expiration datetime (7 days from creation)
        is_used: Whether invitation has been accepted
        used_at: Timestamp when invitation was used
    
    Example:
        >>> from datetime import timedelta
        >>> import secrets
        >>> invitation = UserInvitation.objects.create(
        ...     email='new@example.com',
        ...     token=secrets.token_urlsafe(32),
        ...     invited_by=admin_user,
        ...     expires_at=timezone.now() + timedelta(days=7)
        ... )
    """
    
    VALIDITY_DAYS = 7
    TOKEN_BYTES = 32  # 32 bytes = 256 bits of entropy for secure tokens
    
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
        User,
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
