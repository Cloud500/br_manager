# App: `accounts` - Benutzerverwaltung & Authentifizierung

## Übersicht

Die `accounts`-App ist die Basis-App für Benutzer-Authentifizierung, Profilverwaltung und Zugriffskontrolle. Sie muss als erste implementiert werden, da alle anderen Apps auf das Benutzermodell angewiesen sind.

## Hauptfunktionen

### 1. Benutzerregistrierung und -verwaltung
- Erweitertes Django-User-Modell mit UUIDs als Primärschlüssel
- Pflichtfelder: E-Mail (Login), Vorname, Nachname, Geschlecht (für § 15 Abs. 2 BetrVG - Geschlechterquote)
  - **Geschlecht:** Auswahlfeld mit nur zwei Optionen: "Männlich" oder "Weiblich" (BetrVG kennt keine dritte Option)
- Optionale Felder: Telefonnummer, Profilbild, Abteilung, Personalnummer

### 2. Authentifizierung
- **Lokaler Login:** E-Mail + Passwort + 2FA (Pflicht)
- **SSO (OAuth2) - Optional später:** Integration mit Azure AD, Keycloak oder anderen OAuth2-Providern (ersetzt lokalen Login)
- **Session-Management:** Django Sessions mit konfigurierbarem Timeout (30 Min Inaktivität, 8h max)
- **Passwort-Richtlinien:**
  - Mindestlänge: 12 Zeichen
  - Komplexität: Groß-/Kleinbuchstaben, Ziffern, Sonderzeichen
  - Historie: Letzte 5 Passwörter gesperrt
  - Maximales Alter: 90 Tage
  - Brute-Force-Schutz: 5 Fehlversuche → 15 Min. Lockout

### 3. Zwei-Faktor-Authentifizierung (2FA)
- **Vollständig implementiert** für alle Benutzer
- **Pflicht für alle Benutzer ohne Ausnahme**
- Benutzer müssen 2FA beim ersten Login einrichten
- Login ohne aktiviertes 2FA ist nicht möglich
- **Alternative (später):** OAuth2/SSO (ersetzt lokalen Login + 2FA)
- **Methoden:**
  - TOTP (Authenticator-Apps wie Google Authenticator, Authy, Microsoft Authenticator)
  - E-Mail-OTP als Fallback
- **Recovery-Codes:** 
  - Bei 2FA-Einrichtung werden 10 Einmal-Codes generiert
  - Können zum Account-Recovery bei Verlust des 2FA-Geräts verwendet werden
  - Müssen sicher gespeichert werden (Download als TXT-Datei)

### 4. Profilverwaltung
- Eigenes Profil anzeigen und bearbeiten
- Passwort ändern
- Benachrichtigungseinstellungen konfigurieren
- Avatar hochladen

### 5. DSGVO-konforme Funktionen
- Einwilligungsverwaltung (Consent Management)
- Datenexport (Art. 15 DSGVO)
- Datenberichtigung (Art. 16 DSGVO)
- Datenlöschung mit Anonymisierung (Art. 17 DSGVO)
- Account-Deaktivierung ohne Datenlöschung (Art. 18 DSGVO)

## Datenmodell

### User (erweitertes Django-User-Modell)
- `id` (UUID, PK)
- `email` (EmailField, UNIQUE, Login)
- `first_name` (CharField(100))
- `last_name` (CharField(100))
- `gender` (CharField(1), choices: 'M' = Männlich, 'F' = Weiblich) - Pflichtfeld für § 15 Abs. 2 BetrVG
- `phone` (CharField(20), optional)
- `is_active` (BooleanField)
- `date_joined` (DateTimeField)
- `two_factor_enabled` (BooleanField)
- `two_factor_method` (CharField(10): 'totp', 'email', NULL)
- `totp_secret` (CharField(32), encrypted, optional)
- `last_login` (DateTimeField)
- `password` (CharField, Argon2id-Hash)

### TwoFactorRecoveryCode (ManyToOne → User)
- `id` (UUID, PK)
- `user` (ForeignKey → User)
- `code` (CharField(16), hashed)
- `is_used` (BooleanField)
- `created_at` (DateTimeField)
- `used_at` (DateTimeField, optional)

### UserProfile (OneToOne → User)
- `id` (UUID, PK)
- `user` (OneToOneField → User)
- `department` (CharField(200), optional)
- `employee_id` (CharField(50), optional)
- `notification_preferences` (JSONField)
- `avatar` (ImageField, optional)

## URLs und Views

| URL | View | Beschreibung |
|-----|------|--------------|
| `/accounts/login/` | LoginView | Login-Seite (Email + Passwort) |
| `/accounts/login/2fa/` | TwoFactorVerifyView | 2FA-Code verifizieren |
| `/accounts/logout/` | LogoutView | Logout |
| `/accounts/profile/` | ProfileView | Profil anzeigen/bearbeiten |
| `/accounts/password/change/` | PasswordChangeView | Passwort ändern |
| `/accounts/2fa/setup/` | TwoFactorSetupView | 2FA einrichten (TOTP oder Email) |
| `/accounts/2fa/enable/` | TwoFactorEnableView | 2FA aktivieren |
| `/accounts/2fa/disable/` | TwoFactorDisableView | 2FA deaktivieren |
| `/accounts/2fa/recovery-codes/` | RecoveryCodesView | Recovery-Codes anzeigen/regenerieren |
| `/accounts/oauth/login/` | OAuthLoginView | OAuth2-Login starten |
| `/accounts/oauth/callback/` | OAuthCallbackView | OAuth2-Callback |

## Abhängigkeiten

### Django-Pakete
- `django.contrib.auth` (Standard-Auth-System)
- `django-allauth` (SSO/OAuth2) - optional
- `django-otp` (2FA TOTP-Unterstützung)
- `qrcode` (QR-Code-Generierung für TOTP-Setup)
- `pyotp` (TOTP-Token-Generierung und -Validierung)

### Externe Dienste
- OAuth2-Provider (Azure AD, Keycloak) - optional
- SMTP-Server für E-Mail-Versand

### Datenbank
- PostgreSQL ≥ 16

## Berechtigungen

Die folgenden Berechtigungen werden von dieser App bereitgestellt:

- `system.admin` - Systemweiter Admin-Zugriff
- `system.manage_users` - Benutzerkonten verwalten

**Hinweis:** Systemrollen (SYSTEM_ADMIN, USER) und Gremiumsrollen (CHAIR, MEMBER, etc.) werden in der `roles`-App definiert und verwaltet.

## Sicherheitsaspekte

- **Passwort-Hashing:** Argon2id (Django-Standard)
- **CSRF-Schutz:** Django CSRF-Middleware
- **Session-Sicherheit:** HttpOnly, Secure, SameSite=Strict Cookies
- **Brute-Force-Schutz:** Account-Lockout nach 5 Fehlversuchen (15 Min)
- **2FA-Sicherheit:**
  - TOTP-Secret wird verschlüsselt in der Datenbank gespeichert
  - Recovery-Codes werden gehasht (bcrypt)
  - Rate-Limiting für 2FA-Verifizierung (max. 5 Versuche pro 5 Min)
  - 2FA-Codes haben 30 Sekunden Gültigkeit (TOTP-Standard)
- **Audit-Logging:** Login, Logout, Fehlversuche, Passwortänderungen, 2FA-Aktivierung/-Deaktivierung

## Templates

- `base.html` - Basis-Template
- `accounts/login.html` - Login-Formular (Email + Passwort)
- `accounts/login_2fa.html` - 2FA-Verifizierung (nach erfolgreichem Passwort-Login)
- `accounts/profile.html` - Profil-Ansicht
- `accounts/password_change.html` - Passwort ändern
- `accounts/2fa_setup.html` - 2FA-Einrichtung (Methodenauswahl)
- `accounts/2fa_setup_totp.html` - TOTP-Setup (QR-Code + manueller Key)
- `accounts/2fa_setup_email.html` - Email-OTP-Setup
- `accounts/2fa_recovery_codes.html` - Recovery-Codes anzeigen
- `accounts/2fa_disable_confirm.html` - 2FA-Deaktivierung bestätigen

## Implementierungshinweise

### 1. Implementierungsreihenfolge
1. **Phase 1:** User-Modell und grundlegende Authentifizierung (Email + Passwort)
2. **Phase 2:** 2FA-Funktionalität (TOTP + Recovery-Codes) - **PFLICHT für alle**
3. **Phase 3:** Profilverwaltung und DSGVO-Funktionen
4. **Phase 4 (optional später):** OAuth2/SSO-Integration (Alternative zu lokalem Login)
5. **Phase 5 (optional später):** Email-OTP als 2FA-Fallback

**Wichtig:** 2FA ist ab Phase 2 Pflicht für alle Benutzer. Ohne aktiviertes 2FA ist kein Zugriff möglich (außer OAuth-Benutzer).

### 2. User-Modell: Geschlechterfeld

Das Geschlechterfeld ist Pflicht für die Berechnung der Geschlechterquote nach § 15 Abs. 2 BetrVG:

```python
# models.py
class User(AbstractBaseUser):
    GENDER_CHOICES = [
        ('M', 'Männlich'),
        ('F', 'Weiblich'),
    ]
    
    gender = models.CharField(
        max_length=1,
        choices=GENDER_CHOICES,
        verbose_name='Geschlecht',
        help_text='Pflichtangabe für § 15 Abs. 2 BetrVG (Geschlechterquote)'
    )
    
    # ... weitere Felder
```

**Hinweis:** Das BetrVG kennt aktuell nur zwei Geschlechter für die Berechnung der Mindestquote. Eine dritte Option "Divers" existiert im BetrVG nicht.

### 3. 2FA-Workflow

#### TOTP-Setup:
```python
# 1. TOTP-Secret generieren
import pyotp
secret = pyotp.random_base32()

# 2. QR-Code für Authenticator-App generieren
import qrcode
from io import BytesIO

totp_uri = pyotp.totp.TOTP(secret).provisioning_uri(
    name=user.email,
    issuer_name='BR-Manager'
)

qr = qrcode.make(totp_uri)
buffer = BytesIO()
qr.save(buffer, format='PNG')

# 3. Secret verschlüsselt speichern
from django.conf import settings
from cryptography.fernet import Fernet

cipher = Fernet(settings.TOTP_ENCRYPTION_KEY)
user.totp_secret = cipher.encrypt(secret.encode()).decode()
user.save()

# 4. Recovery-Codes generieren
import secrets
codes = [secrets.token_hex(8) for _ in range(10)]
for code in codes:
    TwoFactorRecoveryCode.objects.create(
        user=user,
        code=make_password(code)  # Gehashed speichern
    )
```

#### 2FA-Verifizierung:
```python
import pyotp
from django.contrib.auth.hashers import check_password

def verify_2fa_code(user, code):
    # TOTP-Verifizierung
    if user.two_factor_method == 'totp':
        cipher = Fernet(settings.TOTP_ENCRYPTION_KEY)
        secret = cipher.decrypt(user.totp_secret.encode()).decode()
        totp = pyotp.TOTP(secret)
        return totp.verify(code, valid_window=1)  # ±30 Sekunden
    
    # Recovery-Code-Verifizierung
    for recovery_code in user.recovery_codes.filter(is_used=False):
        if check_password(code, recovery_code.code):
            recovery_code.is_used = True
            recovery_code.used_at = timezone.now()
            recovery_code.save()
            return True
    
    return False
```

### 3. Erzwungene 2FA für alle Benutzer

```python
# Middleware zur Erzwingung von 2FA
class Require2FAMiddleware:
    """
    Stellt sicher, dass alle Benutzer 2FA aktiviert haben.
    OAuth-Benutzer sind ausgenommen (verwenden SSO-2FA des Providers).
    """
    def __init__(self, get_response):
        self.get_response = get_response
        
    def __call__(self, request):
        if request.user.is_authenticated:
            # OAuth-Benutzer überspringen (haben keine lokalen Credentials)
            if request.user.has_usable_password():
                # 2FA-Setup-Seiten überspringen
                exempt_paths = [
                    '/accounts/2fa/setup/',
                    '/accounts/logout/',
                    '/accounts/password/change/',
                ]
                
                if not any(request.path.startswith(path) for path in exempt_paths):
                    if not request.user.two_factor_enabled:
                        messages.warning(
                            request, 
                            "Sie müssen 2FA einrichten, um das System zu nutzen."
                        )
                        return redirect('accounts:2fa_setup')
        
        return self.get_response(request)

# In LoginView nach erfolgreicher Passwort-Authentifizierung
class CustomLoginView(LoginView):
    def form_valid(self, form):
        user = form.get_user()
        
        # OAuth-Benutzer haben keine 2FA-Pflicht (SSO regelt das)
        if not user.has_usable_password():
            return super().form_valid(form)
        
        # Lokale Benutzer müssen 2FA haben
        if not user.two_factor_enabled:
            # Session-Flag setzen für 2FA-Setup
            self.request.session['pending_2fa_setup'] = True
            self.request.session['pending_user_id'] = str(user.id)
            messages.info(
                self.request,
                "Bitte richten Sie 2FA ein, um Ihren Account zu schützen."
            )
            return redirect('accounts:2fa_setup')
        
        # 2FA-Verifizierung erforderlich
        self.request.session['pre_2fa_user_id'] = str(user.id)
        return redirect('accounts:login_2fa')
```

### 4. Konfiguration

```python
# settings.py
TOTP_ENCRYPTION_KEY = env('TOTP_ENCRYPTION_KEY')  # Fernet-Key generieren mit: Fernet.generate_key()

# Middleware für 2FA-Pflicht
MIDDLEWARE = [
    # ... andere Middleware
    'accounts.middleware.Require2FAMiddleware',  # Nach AuthenticationMiddleware
]

# Rate-Limiting für 2FA-Verifizierung
AXES_ENABLED = True
AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = timedelta(minutes=5)
AXES_LOCK_OUT_BY_USER_OR_IP = True

# TOTP-Konfiguration
TOTP_ISSUER = 'BR-Manager'
TOTP_DIGITS = 6
TOTP_INTERVAL = 30  # Sekunden
TOTP_VALID_WINDOW = 1  # ±30 Sekunden Toleranz

# 2FA-Pflicht
REQUIRE_2FA_FOR_ALL_USERS = True  # Alle lokalen Benutzer benötigen 2FA
```

## Verbindungen zu anderen Apps

### Ausgehende Abhängigkeiten
- **audit** (optional, später): Audit-Logging für Auth-Events
- **notifications** (optional, später): E-Mail-Benachrichtigungen

### Eingehende Abhängigkeiten
- **Alle Apps** nutzen das User-Modell (ForeignKey → User)

## Tests

- Unit-Tests für Authentifizierung (Email + Passwort)
- Integration-Tests für Login/Logout
- Sicherheitstests für Brute-Force-Schutz
- **2FA-Tests:**
  - TOTP-Setup und -Verifizierung
  - Recovery-Code-Generierung und -Verwendung
  - **Erzwungene 2FA für alle Benutzer (Middleware-Test)**
  - **Login ohne 2FA wird blockiert**
  - Rate-Limiting für 2FA-Codes
  - QR-Code-Generierung
  - Verschlüsselung von TOTP-Secrets
  - OAuth-Benutzer sind von 2FA-Pflicht ausgenommen
- DSGVO-Compliance-Tests (Export, Löschung)
