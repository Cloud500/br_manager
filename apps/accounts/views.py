"""Views for accounts app."""

import secrets
from datetime import timedelta
from typing import Any

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.views import LoginView as DjangoLoginView
from django.contrib.auth.views import LogoutView as DjangoLogoutView
from django.core.mail import EmailMultiAlternatives
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import CreateView, DeleteView, FormView, ListView, TemplateView, UpdateView
from django_ratelimit.decorators import ratelimit
from django.utils.decorators import method_decorator

from .forms import UserInviteForm, UserRegistrationForm, UserUpdateForm
from .models import UserInvitation, UserProfile
from .twofa_utils import (
    generate_qr_code,
    generate_recovery_codes,
    generate_totp_secret,
    generate_totp_uri,
    get_available_recovery_codes_count,
    verify_recovery_code,
    verify_totp_code,
)


User = get_user_model()


class LoginView(DjangoLoginView):
    """
    Login with email + password, with 2FA support.
    
    If user has 2FA enabled, redirects to 2FA verification after password check.
    Otherwise, logs in directly.
    """
    
    template_name = 'accounts/login.html'
    redirect_authenticated_user = True
    
    def form_valid(self, form):
        """
        Handle successful login form submission.
        
        Check if user has 2FA enabled:
        - If yes: Store user ID in session and redirect to 2FA verification
        - If no: Log in normally
        
        Args:
            form: The validated login form
            
        Returns:
            HttpResponse redirect to either 2FA verify or success URL
        """
        user = form.get_user()
        
        # Check if user has 2FA enabled
        if user.two_factor_enabled:
            # Don't log in yet - store user ID for 2FA verification
            self.request.session['2fa_user_id'] = str(user.id)
            self.request.session['2fa_login_timestamp'] = timezone.now().isoformat()
            
            # Redirect to 2FA verification
            return redirect('accounts:2fa_verify')
        
        # No 2FA - proceed with normal login
        return super().form_valid(form)
    
    def get_success_url(self) -> str:
        """
        Return URL to redirect to after successful login.
        
        Returns:
            URL string for dashboard
        """
        return reverse_lazy('core:dashboard')


class LogoutView(DjangoLogoutView):
    """
    Logout current user.
    
    Clears session and redirects to login page.
    """
    
    next_page = reverse_lazy('accounts:login')


class ProfileView(LoginRequiredMixin, TemplateView):
    """
    User profile view.
    
    Displays all user information including profile data and 2FA status.
    """
    
    template_name = 'accounts/profile.html'
    login_url = reverse_lazy('accounts:login')
    
    def get_context_data(self, **kwargs) -> dict:
        """
        Add user profile information to context.
        
        Returns:
            Context dictionary with user and profile data
        """
        context = super().get_context_data(**kwargs)
        
        # Get or create user profile
        profile, created = UserProfile.objects.get_or_create(user=self.request.user)
        context['profile'] = profile
        
        # Add recovery codes count
        context['recovery_codes_count'] = get_available_recovery_codes_count(self.request.user)
        
        return context


class ProfileUpdateView(LoginRequiredMixin, UpdateView):
    """
    Update user's own profile.
    
    Allows users to edit their personal information.
    """
    
    model = User
    form_class = None  # Will be set in get_form_class
    template_name = 'accounts/profile_update.html'
    success_url = reverse_lazy('accounts:profile')
    
    def get_form_class(self):
        """
        Get the appropriate form class.
        
        Returns:
            UserProfileUpdateForm for profile updates
        """
        from .forms import UserProfileUpdateForm
        return UserProfileUpdateForm
    
    def get_object(self, queryset=None) -> User:
        """
        Return the current user's object.
        
        Args:
            queryset: Optional queryset to filter (unused)
            
        Returns:
            Current user instance
        """
        return self.request.user
    
    def form_valid(self, form) -> HttpResponse:
        """
        Handle successful form submission.
        
        Args:
            form: Validated form instance
            
        Returns:
            HttpResponse redirect to profile page
        """
        messages.success(self.request, 'Profil wurde erfolgreich aktualisiert.')
        return super().form_valid(form)


class ProfilePasswordChangeView(LoginRequiredMixin, FormView):
    """
    Change user's password.
    
    Requires current password verification before setting new password.
    """
    
    template_name = 'accounts/password_change.html'
    form_class = None  # Will be set in get_form_class
    success_url = reverse_lazy('accounts:profile')
    
    def get_form_class(self):
        """
        Get the password change form class.
        
        Returns:
            PasswordChangeForm class
        """
        from .forms import PasswordChangeForm
        return PasswordChangeForm
    
    def get_form_kwargs(self) -> dict:
        """
        Add user to form kwargs.
        
        Returns:
            Form kwargs including user instance
        """
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form) -> HttpResponse:
        """
        Save new password and update session.
        
        Args:
            form: Validated password change form
            
        Returns:
            HttpResponse redirect to profile page
        """
        from django.contrib.auth import update_session_auth_hash
        
        # Set new password
        user = self.request.user
        user.set_password(form.cleaned_data['new_password'])
        user.save(update_fields=['password'])
        
        # Update session to prevent logout
        update_session_auth_hash(self.request, user)
        
        messages.success(self.request, 'Passwort wurde erfolgreich geändert.')
        return super().form_valid(form)


class TwoFactorSetupView(LoginRequiredMixin, TemplateView):
    """
    Set up Two-Factor Authentication (TOTP).
    
    Generates TOTP secret, displays QR code, and creates recovery codes.
    """
    
    template_name = 'accounts/2fa_setup.html'
    
    def get_context_data(self, **kwargs):
        """Add TOTP secret and QR code to context."""
        context = super().get_context_data(**kwargs)
        
        user = self.request.user
        
        # Generate new secret if not exists
        if not user.totp_secret:
            user.totp_secret = generate_totp_secret()
            user.save(update_fields=['totp_secret'])
        
        # Generate QR code URI
        totp_uri = generate_totp_uri(user, user.totp_secret)
        context['totp_uri'] = totp_uri
        context['totp_secret'] = user.totp_secret
        
        # Check if 2FA is required for this user
        context['twofa_required'] = self._is_2fa_required(user)
        
        return context
    
    def _is_2fa_required(self, user) -> bool:
        """
        Check if 2FA is required for the user.
        
        Args:
            user: The user to check
            
        Returns:
            True if 2FA is required, False otherwise
        """
        if user.is_superuser:
            return True
        if user.has_perm('system.manage_users'):
            return True
        if user.has_perm('role.manage_roles'):
            return True
        return False
    
    def post(self, request, *args, **kwargs):
        """Verify TOTP code and enable 2FA."""
        code = request.POST.get('code', '').strip()
        
        if not code:
            messages.error(request, 'Bitte geben Sie den Code ein.')
            return self.get(request, *args, **kwargs)
        
        user = request.user
        
        # Verify code
        if verify_totp_code(user, code):
            # Enable 2FA
            user.two_factor_enabled = True
            user.two_factor_method = 'TOTP'
            user.save(update_fields=['two_factor_enabled', 'two_factor_method'])
            
            # Generate recovery codes
            recovery_codes = generate_recovery_codes(user)
            request.session['recovery_codes'] = recovery_codes
            request.session['2fa_verified'] = True
            
            messages.success(request, '2FA wurde erfolgreich aktiviert!')
            return redirect('accounts:2fa_recovery_codes')
        else:
            messages.error(request, 'Ungültiger Code. Bitte versuchen Sie es erneut.')
            return self.get(request, *args, **kwargs)


@method_decorator(ratelimit(key='user', rate='5/5m', method='POST'), name='post')
class TwoFactorVerifyView(TemplateView):
    """
    Verify 2FA code after login or during session.
    
    Handles two scenarios:
    1. Login flow: User entered correct password, now needs 2FA code
    2. Session verification: Already logged in user needs to verify 2FA
    
    Rate-limited to prevent brute-force attacks (5 attempts per 5 minutes).
    """
    
    template_name = 'accounts/2fa_verify.html'
    
    def _get_user_for_verification(self) -> User | None:
        """
        Get the user that needs 2FA verification.
        
        Returns:
            User object if found, None otherwise
        """
        # Check if user is in login flow (not yet authenticated)
        user_id = self.request.session.get('2fa_user_id')
        if user_id:
            try:
                return User.objects.get(id=user_id)
            except User.DoesNotExist:
                return None
        
        # Check if user is already authenticated
        if self.request.user.is_authenticated:
            return self.request.user
        
        return None
    
    def get(self, request, *args, **kwargs):
        """Show 2FA verification form."""
        # Get user for verification
        user = self._get_user_for_verification()
        
        if not user:
            messages.error(request, 'Sitzung abgelaufen. Bitte melden Sie sich erneut an.')
            return redirect('accounts:login')
        
        # Check if already verified in this session
        if request.session.get('2fa_verified'):
            return redirect('core:dashboard')
        
        return super().get(request, *args, **kwargs)
    
    @method_decorator(ratelimit(key='ip', rate='5/5m', method='POST'))
    def post(self, request, *args, **kwargs):
        """Verify TOTP code or recovery code."""
        # Check rate limit
        if getattr(request, 'limited', False):
            messages.error(request, 'Zu viele Versuche. Bitte warten Sie 5 Minuten.')
            return self.get(request, *args, **kwargs)
        
        # Get user for verification
        user = self._get_user_for_verification()
        
        if not user:
            messages.error(request, 'Sitzung abgelaufen. Bitte melden Sie sich erneut an.')
            return redirect('accounts:login')
        
        code = request.POST.get('code', '').strip()
        use_recovery = request.POST.get('use_recovery', False)
        
        if not code:
            messages.error(request, 'Bitte geben Sie den Code ein.')
            return self.get(request, *args, **kwargs)
        
        # Try recovery code if requested
        if use_recovery:
            if verify_recovery_code(user, code):
                return self._handle_successful_verification(user)
            else:
                messages.error(request, 'Ungültiger Recovery-Code.')
                return self.get(request, *args, **kwargs)
        
        # Try TOTP code
        if verify_totp_code(user, code):
            return self._handle_successful_verification(user)
        else:
            messages.error(request, 'Ungültiger Code. Bitte versuchen Sie es erneut.')
            return self.get(request, *args, **kwargs)
    
    def _handle_successful_verification(self, user: User) -> HttpResponse:
        """
        Handle successful 2FA verification.
        
        If user was in login flow, log them in. Mark session as verified.
        
        Args:
            user: The user who successfully verified 2FA
            
        Returns:
            HttpResponse redirect to dashboard
        """
        from django.contrib.auth import login
        
        # If user was in login flow (not yet authenticated), log them in now
        if '2fa_user_id' in self.request.session:
            login(self.request, user, backend='django.contrib.auth.backends.ModelBackend')
            
            # Clean up login flow session variables
            del self.request.session['2fa_user_id']
            if '2fa_login_timestamp' in self.request.session:
                del self.request.session['2fa_login_timestamp']
        
        # Mark 2FA as verified in this session
        self.request.session['2fa_verified'] = True
        
        # Check recovery codes
        remaining = get_available_recovery_codes_count(user)
        if remaining <= 2:
            messages.warning(
                self.request,
                f'Achtung: Nur noch {remaining} Recovery-Codes verfügbar!'
            )
        
        messages.success(self.request, '2FA-Verifizierung erfolgreich.')
        return redirect('core:dashboard')


class RecoveryCodesView(LoginRequiredMixin, TemplateView):
    """
    Display recovery codes (only once after generation).
    
    Also allows regeneration of recovery codes.
    """
    
    template_name = 'accounts/recovery_codes.html'
    
    def get_context_data(self, **kwargs):
        """Add recovery codes to context if in session."""
        import json
        
        context = super().get_context_data(**kwargs)
        
        # Get codes from session (only shown once)
        recovery_codes = self.request.session.pop('recovery_codes', None)
        context['recovery_codes'] = recovery_codes
        
        # Add JSON version for JavaScript
        if recovery_codes:
            context['recovery_codes_json'] = json.dumps(recovery_codes)
        
        context['available_count'] = get_available_recovery_codes_count(self.request.user)
        
        return context
    
    def post(self, request, *args, **kwargs):
        """Regenerate recovery codes."""
        user = request.user
        
        if not user.two_factor_enabled:
            messages.error(request, '2FA ist nicht aktiviert.')
            return redirect('accounts:profile')
        
        # Generate new recovery codes
        recovery_codes = generate_recovery_codes(user)
        request.session['recovery_codes'] = recovery_codes
        
        messages.success(request, 'Neue Recovery-Codes wurden generiert.')
        return self.get(request, *args, **kwargs)


class TwoFactorDisableView(LoginRequiredMixin, View):
    """Disable Two-Factor Authentication."""
    
    def post(self, request, *args, **kwargs):
        """Disable 2FA for user."""
        user = request.user
        
        # Disable 2FA
        user.two_factor_enabled = False
        user.two_factor_method = ''
        user.totp_secret = ''
        user.save(update_fields=['two_factor_enabled', 'two_factor_method', 'totp_secret'])
        
        # Delete all recovery codes
        user.recovery_codes.all().delete()
        
        # Clear session
        request.session.pop('2fa_verified', None)
        
        messages.success(request, '2FA wurde deaktiviert.')
        return redirect('accounts:profile')


# -----------------------------------------------------------------------------
# User Management Views (Admin only)
# -----------------------------------------------------------------------------

class AdminRequiredMixin(UserPassesTestMixin):
    """Mixin to require admin permissions."""
    
    def test_func(self) -> bool:
        """Check if user has admin permissions."""
        return (
            self.request.user.is_superuser or
            self.request.user.has_perm('accounts.manage_users')
        )


class UserListView(LoginRequiredMixin, AdminRequiredMixin, ListView):
    """
    List all users with search and filtering.
    
    Only accessible by administrators.
    """
    
    model = User
    template_name = 'accounts/user_list.html'
    context_object_name = 'users'
    paginate_by = 20
    
    def get_queryset(self):
        """Filter users based on search query."""
        queryset = User.objects.all().order_by('-date_joined')
        
        search = self.request.GET.get('search', '').strip()
        if search:
            queryset = queryset.filter(
                Q(email__icontains=search) |
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search)
            )
        
        return queryset
    
    def get_context_data(self, **kwargs):
        """Add search query and pending invitations to context."""
        context = super().get_context_data(**kwargs)
        context['search'] = self.request.GET.get('search', '')
        
        # Get pending invitations
        pending_invitations = UserInvitation.objects.filter(
            used_at__isnull=True
        ).select_related('invited_by').order_by('-created_at')
        
        # Filter by search query if provided
        search = self.request.GET.get('search', '').strip()
        if search:
            pending_invitations = pending_invitations.filter(
                email__icontains=search
            )
        
        context['pending_invitations'] = pending_invitations
        
        return context


# -----------------------------------------------------------------------------
# Email Utilities
# -----------------------------------------------------------------------------

def generate_invitation_email_content(
    invite_url: str,
    inviter_name: str,
    validity_days: int
) -> tuple[str, str]:
    """
    Generate plain text and HTML content for invitation email.
    
    Args:
        invite_url: Full URL to registration page with token
        inviter_name: Full name or email of the person who sent invitation
        validity_days: Number of days the invitation is valid
        
    Returns:
        Tuple of (plain_text_content, html_content)
    """
    # Plain text version for email clients that don't support HTML
    text_content = f'''Hallo,

Sie wurden von {inviter_name} zum BR-Manager eingeladen.

Bitte klicken Sie auf den folgenden Link, um Ihr Konto einzurichten:

{invite_url}

Dieser Link ist {validity_days} Tage gültig.

Mit freundlichen Grüßen
Ihr BR-Manager Team
'''
    
    # HTML version for modern email clients
    html_content = f'''<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
<div style="background-color: #f8f9fa; padding: 20px; border-radius: 5px;">
<h2 style="color: #212529; margin-top: 0;">Einladung zum BR-Manager</h2>
<p>Hallo,</p>
<p>Sie wurden von <strong>{inviter_name}</strong> zum BR-Manager eingeladen.</p>
<p>Bitte klicken Sie auf den folgenden Button, um Ihr Konto einzurichten:</p>
<div style="text-align: center; margin: 30px 0;">
<a href="{invite_url}" style="background-color: #0d6efd; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; display: inline-block; font-weight: bold;">Konto einrichten</a>
</div>
<p style="font-size: 14px; color: #6c757d;">Oder kopieren Sie diesen Link in Ihren Browser:<br><a href="{invite_url}" style="color: #0d6efd; word-break: break-all;">{invite_url}</a></p>
<p style="font-size: 14px; color: #6c757d;"><strong>Hinweis:</strong> Dieser Link ist {validity_days} Tage gültig.</p>
<hr style="border: none; border-top: 1px solid #dee2e6; margin: 20px 0;">
<p style="font-size: 14px; color: #6c757d; margin-bottom: 0;">Mit freundlichen Grüßen<br>Ihr BR-Manager Team</p>
</div>
</body>
</html>'''
    
    return text_content, html_content


# -----------------------------------------------------------------------------
# User Invitation Views
# -----------------------------------------------------------------------------

class UserInviteView(LoginRequiredMixin, AdminRequiredMixin, CreateView):
    """
    Invite new user via email.
    
    Generates secure token and sends invitation email.
    """
    
    model = UserInvitation
    form_class = UserInviteForm
    template_name = 'accounts/user_invite.html'
    success_url = reverse_lazy('accounts:user_list')
    
    def form_valid(self, form: UserInviteForm) -> HttpResponse:
        """
        Create invitation and send email to invited user.
        
        Generates a secure token, saves the invitation, and sends an HTML email
        with both a clickable button and a copyable link.
        
        Args:
            form: Validated UserInviteForm containing the email address
            
        Returns:
            HttpResponse redirecting to user list with success message
            
        Raises:
            SMTPException: If email sending fails
        """
        email = form.cleaned_data['email']
        
        # Create invitation with secure token
        invitation = form.save(commit=False)
        invitation.token = secrets.token_urlsafe(UserInvitation.TOKEN_BYTES)
        invitation.invited_by = self.request.user
        invitation.expires_at = timezone.now() + timedelta(
            days=UserInvitation.VALIDITY_DAYS
        )
        invitation.save()
        
        # Generate absolute URL for registration
        invite_url = self.request.build_absolute_uri(
            reverse('accounts:register', kwargs={'token': invitation.token})
        )
        
        # Get inviter name for personalization
        inviter_name = self.request.user.get_full_name() or self.request.user.email
        
        # Generate email content
        text_content, html_content = generate_invitation_email_content(
            invite_url=invite_url,
            inviter_name=inviter_name,
            validity_days=UserInvitation.VALIDITY_DAYS
        )
        
        # Send multipart email (plain text + HTML)
        msg = EmailMultiAlternatives(
            subject='Einladung zum BR-Manager',
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[email],
        )
        msg.attach_alternative(html_content, "text/html")
        msg.send(fail_silently=False)
        
        # Show success message
        messages.success(
            self.request,
            f'Einladung wurde an {email} gesendet.'
        )
        
        return super().form_valid(form)


class UserRegistrationView(FormView):
    """
    User registration via invitation link.
    
    Validates token and creates new user account.
    After successful registration, user is automatically logged in
    and redirected to 2FA setup.
    """
    
    template_name = 'accounts/user_register.html'
    form_class = UserRegistrationForm
    success_url = reverse_lazy('accounts:2fa_setup')
    
    def dispatch(self, request, *args, **kwargs):
        """Validate invitation token before processing."""
        token = kwargs.get('token')
        
        try:
            self.invitation = UserInvitation.objects.get(token=token)
        except UserInvitation.DoesNotExist:
            messages.error(request, 'Ungültiger Einladungs-Link.')
            return redirect('accounts:login')
        
        # Check if invitation is still valid
        if not self.invitation.is_valid():
            messages.error(request, 'Diese Einladung ist abgelaufen.')
            return redirect('accounts:login')
        
        return super().dispatch(request, *args, **kwargs)
    
    def get_form_kwargs(self):
        """Add email from invitation to form."""
        kwargs = super().get_form_kwargs()
        kwargs['email'] = self.invitation.email
        return kwargs
    
    def get_context_data(self, **kwargs):
        """Add invitation email to context."""
        context = super().get_context_data(**kwargs)
        context['invitation_email'] = self.invitation.email
        return context
    
    def form_valid(self, form):
        """Create user, log them in, and redirect to 2FA setup."""
        from django.contrib.auth import login
        
        # Create user
        user = form.save()
        
        # Create user profile
        UserProfile.objects.create(user=user)
        
        # Mark invitation as used
        self.invitation.mark_as_used()
        
        # Log the user in automatically
        login(self.request, user, backend='django.contrib.auth.backends.ModelBackend')
        
        messages.success(
            self.request,
            'Konto wurde erfolgreich erstellt! Bitte richten Sie jetzt die '
            'Zwei-Faktor-Authentifizierung ein.'
        )
        
        return super().form_valid(form)


class UserUpdateView(LoginRequiredMixin, AdminRequiredMixin, UpdateView):
    """
    Update existing user.
    
    Only accessible by administrators.
    """
    
    model = User
    form_class = UserUpdateForm
    template_name = 'accounts/user_update.html'
    success_url = reverse_lazy('accounts:user_list')
    
    def form_valid(self, form):
        """Save updated user."""
        messages.success(
            self.request,
            f'Benutzer {self.object.get_full_name()} wurde aktualisiert.'
        )
        return super().form_valid(form)


class UserDeleteView(LoginRequiredMixin, AdminRequiredMixin, DeleteView):
    """
    Soft-delete user (set is_active=False).
    
    Does not actually delete user from database.
    """
    
    model = User
    template_name = 'accounts/user_confirm_delete.html'
    success_url = reverse_lazy('accounts:user_list')
    
    def post(self, request, *args, **kwargs):
        """Soft-delete user instead of hard delete."""
        self.object = self.get_object()
        
        # Prevent self-deletion
        if self.object == request.user:
            messages.error(request, 'Sie können Ihr eigenes Konto nicht deaktivieren.')
            return redirect('accounts:user_list')
        
        # Soft delete
        self.object.is_active = False
        self.object.save(update_fields=['is_active'])
        
        messages.success(
            request,
            f'Benutzer {self.object.get_full_name()} wurde deaktiviert.'
        )
        
        return redirect(self.success_url)


class UserInvitationDeleteView(LoginRequiredMixin, AdminRequiredMixin, DeleteView):
    """
    Delete a pending user invitation.
    
    Allows admins to cancel invitations that haven't been used yet.
    """
    
    model = UserInvitation
    success_url = reverse_lazy('accounts:user_list')
    
    def get_queryset(self):
        """Only allow deletion of unused invitations."""
        return UserInvitation.objects.filter(used_at__isnull=True)
    
    def post(self, request, *args, **kwargs):
        """Delete the invitation."""
        self.object = self.get_object()
        
        # Check if invitation is still pending
        if self.object.used_at is not None:
            messages.error(request, 'Diese Einladung wurde bereits verwendet.')
            return redirect('accounts:user_list')
        
        email = self.object.email
        self.object.delete()
        
        messages.success(
            request,
            f'Einladung für {email} wurde gelöscht.'
        )
        
        return redirect(self.success_url)
    
    def get(self, request, *args, **kwargs):
        """Redirect GET requests directly to delete (no confirmation page)."""
        return self.post(request, *args, **kwargs)
