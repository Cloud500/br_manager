"""Two-factor authentication utilities."""

import io
import secrets
from typing import List, Tuple

import pyotp
import qrcode
from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.core.files.base import ContentFile

from .models import TwoFactorRecoveryCode, User


def generate_totp_secret() -> str:
    """
    Generate a new TOTP secret for 2FA.
    
    Returns:
        Base32 encoded secret (32 characters)
    """
    return pyotp.random_base32()


def generate_totp_uri(user: User, secret: str) -> str:
    """
    Generate TOTP provisioning URI for QR code.
    
    Args:
        user: User object
        secret: TOTP secret
    
    Returns:
        Provisioning URI string
    """
    issuer_name = getattr(settings, 'TOTP_ISSUER', 'BR-Manager')
    totp = pyotp.TOTP(secret)
    return totp.provisioning_uri(
        name=user.email,
        issuer_name=issuer_name
    )


def generate_qr_code(uri: str) -> ContentFile:
    """
    Generate QR code image from TOTP URI.
    
    Args:
        uri: TOTP provisioning URI
    
    Returns:
        ContentFile containing PNG image data
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(uri)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Save to bytes buffer
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    
    return ContentFile(buffer.read(), name='qr_code.png')


def verify_totp_code(user: User, code: str) -> bool:
    """
    Verify TOTP code for user.
    
    Args:
        user: User object with totp_secret
        code: 6-digit TOTP code to verify
    
    Returns:
        True if code is valid
    """
    if not user.totp_secret:
        return False
    
    totp = pyotp.TOTP(user.totp_secret)
    tolerance = getattr(settings, 'TOTP_TOLERANCE', 1)
    
    return totp.verify(code, valid_window=tolerance)


def generate_recovery_codes(user: User, count: int = 10) -> List[str]:
    """
    Generate recovery codes for user.
    
    Creates hashed recovery codes and stores them in database.
    Returns plaintext codes for user to save.
    
    Args:
        user: User object
        count: Number of codes to generate (default 10)
    
    Returns:
        List of plaintext recovery codes
    """
    # Delete existing recovery codes
    user.recovery_codes.all().delete()
    
    plaintext_codes = []
    
    for _ in range(count):
        # Generate random code (format: XXXX-XXXX-XXXX)
        code = '-'.join([
            secrets.token_hex(2).upper()
            for _ in range(3)
        ])
        plaintext_codes.append(code)
        
        # Store hashed version
        TwoFactorRecoveryCode.objects.create(
            user=user,
            code=make_password(code)
        )
    
    return plaintext_codes


def verify_recovery_code(user: User, code: str) -> bool:
    """
    Verify and mark recovery code as used.
    
    Args:
        user: User object
        code: Recovery code to verify
    
    Returns:
        True if code is valid and unused
    """
    from django.contrib.auth.hashers import check_password
    
    # Get all unused recovery codes for user
    recovery_codes = user.recovery_codes.filter(is_used=False)
    
    for recovery_code in recovery_codes:
        if check_password(code, recovery_code.code):
            recovery_code.mark_as_used()
            return True
    
    return False


def get_available_recovery_codes_count(user: User) -> int:
    """
    Get number of available (unused) recovery codes for user.
    
    Args:
        user: User object
    
    Returns:
        Count of unused recovery codes
    """
    return user.recovery_codes.filter(is_used=False).count()
