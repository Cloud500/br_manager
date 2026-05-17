from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone

from config.rbac.services import has_permission
from config.models import BaseModel


class UserManager(BaseUserManager):
    def create_user(self, email: str, password: str = None, **extra_fields) -> 'User':
        if not email:
            raise ValueError('E-Mail-Adresse muss angegeben werden')

        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email: str, password: str = None, **extra_fields) -> 'User':
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser muss is_staff=True haben')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser muss is_superuser=True haben')

        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin, BaseModel):
    GENDER_CHOICES = [
        ('M', 'Männlich'),
        ('F', 'Weiblich'),
    ]

    TWO_FACTOR_METHOD_CHOICES = [
        ('TOTP', 'Authenticator App (TOTP)'),
        # ('SMS', 'SMS'),
    ]

    email = models.EmailField(unique=True, verbose_name='E-Mail-Adresse', help_text='Wird als Login verwendet', )
    first_name = models.CharField(max_length=150, verbose_name='Vorname', )
    last_name = models.CharField(max_length=150, verbose_name='Nachname', )
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, verbose_name='Geschlecht',
                              help_text='Pflichtangabe für § 15 Abs. 2 BetrVG (Geschlechterquote)', )
    phone = models.CharField(max_length=20, blank=True, verbose_name='Telefon', )
    is_active = models.BooleanField(default=True, verbose_name='Aktiv', )
    is_staff = models.BooleanField(default=False, verbose_name='Staff-Status', )
    date_joined = models.DateTimeField(default=timezone.now, verbose_name='Beigetreten am', )
    two_factor_enabled = models.BooleanField(default=False, verbose_name='2FA aktiviert')
    two_factor_method = models.CharField(max_length=10, choices=TWO_FACTOR_METHOD_CHOICES, blank=True,
                                         verbose_name='2FA-Methode', )
    totp_secret = models.CharField(max_length=255, blank=True, verbose_name='TOTP-Secret', )

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

    def has_committee_perm(self, perm, committee):
        return has_permission(self, perm, committee)


class UserProfile(BaseModel):
    department = models.CharField(max_length=200, blank=True, verbose_name='Abteilung', )
    employee_id = models.CharField(max_length=50, blank=True, verbose_name='Personalnummer', )
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True, verbose_name='Profilbild', )
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile',
        verbose_name='Benutzer',
    )

    class Meta:
        verbose_name = 'Benutzerprofil'
        verbose_name_plural = 'Benutzerprofile'

    def __str__(self) -> str:
        return f"Profil von {self.user.get_full_name()}"


class TwoFactorRecoveryCode(BaseModel):
    code = models.CharField(max_length=255, verbose_name='Code (gehasht)',
                            help_text='Recovery-Code wird gehasht gespeichert', )
    is_used = models.BooleanField(default=False, verbose_name='Verwendet', )
    used_at = models.DateTimeField(null=True, blank=True, verbose_name='Verwendet am', )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='recovery_codes',
        verbose_name='Benutzer',
    )

    class Meta:
        verbose_name = '2FA Recovery-Code'
        verbose_name_plural = '2FA Recovery-Codes'
        ordering = ['-created_at']

    def __str__(self) -> str:
        if self.is_used:
            return f"Recovery-Code für {self.user.email} (verwendet)"
        return f"Recovery-Code für {self.user.email} (verfügbar)"

    def mark_as_used(self) -> None:
        self.is_used = True
        self.used_at = timezone.now()
        self.save(update_fields=['is_used', 'used_at'])
