"""Factories for creating test data."""

import secrets

import pyotp
from django.contrib.auth.hashers import make_password
from factory import LazyAttribute, SubFactory, post_generation
from factory.django import DjangoModelFactory
from factory.faker import Faker

from apps.accounts.models import TwoFactorRecoveryCode, User, UserProfile

# FESTER SECRET FÜR ALLE DEVELOPMENT-USER
# Kann in Authenticator-App einmalig eingegeben werden
# Alle Test-User verwenden den gleichen Secret → gleicher TOTP-Code
# WICHTIG: Muss valides Base32 sein (A-Z, 2-7, keine 0,1,8,9)
DEV_TOTP_SECRET = "BRMANAGERDEV2FATESTKEY234567"


class UserFactory(DjangoModelFactory):
    """
    Factory für Test-User mit aktivem 2FA.
    
    Alle User haben:
    - Passwort: 'testpass123'
    - 2FA aktiviert mit festem TOTP-Secret (DEV_TOTP_SECRET)
    - Deutsche Namen und E-Mail @example.org
    
    Example:
        >>> user = UserFactory.create()
        >>> user.email
        'max.mustermann@example.org'
        >>> user.two_factor_enabled
        True
        >>> user.totp_secret == DEV_TOTP_SECRET
        True
    """

    class Meta:
        model = User

    # Basis-Daten (deutsche Lokalisierung)
    email = Faker("email", domain="example.org", locale="de_DE")
    first_name = Faker("first_name", locale="de_DE")
    last_name = Faker("last_name", locale="de_DE")
    gender = Faker("random_element", elements=["M", "F"])
    phone = Faker("phone_number", locale="de_DE")

    # Status
    is_active = True
    is_staff = False

    # 2FA - IMMER aktiviert mit festem Secret
    two_factor_enabled = True
    two_factor_method = "TOTP"
    totp_secret = DEV_TOTP_SECRET  # Alle haben den gleichen!

    @post_generation
    def password(self, create, extracted, **kwargs):
        """Setze Passwort auf 'testpass123' für alle."""
        if create:
            self.set_password("testpass123")
            self.save()


class UserProfileFactory(DjangoModelFactory):
    """
    Factory für UserProfile mit deutschen Abteilungsnamen.
    
    Example:
        >>> profile = UserProfileFactory.create()
        >>> profile.department in ['IT', 'Personalabteilung', ...]
        True
        >>> profile.employee_id
        'EMP-12345'
    """

    class Meta:
        model = UserProfile

    user = SubFactory(UserFactory)
    department = Faker(
        "random_element",
        elements=[
            "IT",
            "Personalabteilung",
            "Produktion",
            "Vertrieb",
            "Marketing",
            "Finanzen",
            "Einkauf",
            "Qualitätssicherung",
        ],
    )
    employee_id = LazyAttribute(
        lambda o: f"EMP-{Faker('random_int', min=10000, max=99999).evaluate(None, None, {'locale': None})}"
    )
    notification_preferences = {
        "email": True,
        "push": False,
        "meeting_reminders": True,
    }


class TwoFactorRecoveryCodeFactory(DjangoModelFactory):
    """
    Factory für 2FA Recovery Codes.
    
    Generiert gehashte Recovery-Codes im Format: RECOVERY-XXXXX-XXXXX
    Der ungehashte Code wird in self._raw_code gespeichert (nur für Development).
    
    Example:
        >>> code = TwoFactorRecoveryCodeFactory.create()
        >>> code.is_used
        False
        >>> code._raw_code  # Nur im Speicher, nicht in DB
        'RECOVERY-A1B2C-D3E4F'
    """

    class Meta:
        model = TwoFactorRecoveryCode

    user = SubFactory(UserFactory)
    is_used = False

    @post_generation
    def code_generator(self, create, extracted, **kwargs):
        """Generiere gehashten Recovery-Code."""
        if create:
            # Format: RECOVERY-XXXXX-XXXXX
            part1 = secrets.token_hex(5).upper()
            part2 = secrets.token_hex(5).upper()
            raw_code = f"RECOVERY-{part1}-{part2}"

            self.code = make_password(raw_code)
            self.save()

            # Speichere raw_code für Output (nur Development!)
            # ACHTUNG: In Production niemals ungeshashte Codes speichern!
            self._raw_code = raw_code
