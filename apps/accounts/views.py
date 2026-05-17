"""Views for accounts app."""

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView as DjangoLoginView
from django.contrib.auth.views import LogoutView as DjangoLogoutView
from django.http import HttpResponse
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic import FormView, TemplateView, UpdateView

from django_ratelimit.decorators import ratelimit

from .forms import PasswordChangeForm, UserProfileUpdateForm
from .models import UserProfile
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
    template_name = "accounts/login.html"
    redirect_authenticated_user = True

    def form_valid(self, form):
        user = form.get_user()
        if user.two_factor_enabled:
            self.request.session["2fa_user_id"] = str(user.id)
            self.request.session["2fa_login_timestamp"] = timezone.now().isoformat()
            return redirect("accounts:2fa_verify")
        return super().form_valid(form)

    def get_success_url(self) -> str:
        return reverse_lazy("core:dashboard")


class LogoutView(DjangoLogoutView):
    next_page = reverse_lazy("accounts:login")


class ProfileView(LoginRequiredMixin, TemplateView):
    template_name = "accounts/profile.html"
    login_url = reverse_lazy("accounts:login")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["profile"], _ = UserProfile.objects.get_or_create(user=self.request.user)
        context["recovery_codes_count"] = get_available_recovery_codes_count(self.request.user)
        return context


class ProfileUpdateView(LoginRequiredMixin, UpdateView):
    model = User
    form_class = UserProfileUpdateForm
    template_name = "accounts/profile_update.html"
    success_url = reverse_lazy("accounts:profile")

    def get_object(self, queryset=None):
        return self.request.user

    def form_valid(self, form) -> HttpResponse:
        messages.success(self.request, "Profil wurde erfolgreich aktualisiert.")
        return super().form_valid(form)


class ProfilePasswordChangeView(LoginRequiredMixin, FormView):
    template_name = "accounts/password_change.html"
    form_class = PasswordChangeForm
    success_url = reverse_lazy("accounts:profile")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form) -> HttpResponse:
        from django.contrib.auth import update_session_auth_hash

        user = self.request.user
        user.set_password(form.cleaned_data["new_password"])
        user.save(update_fields=["password"])
        update_session_auth_hash(self.request, user)
        messages.success(self.request, "Passwort wurde erfolgreich geändert.")
        return super().form_valid(form)


class TwoFactorSetupView(LoginRequiredMixin, TemplateView):
    template_name = "accounts/2fa_setup.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        if not user.totp_secret:
            user.totp_secret = generate_totp_secret()
            user.save(update_fields=["totp_secret"])
        context["totp_uri"] = generate_totp_uri(user, user.totp_secret)
        context["totp_secret"] = user.totp_secret
        context["twofa_required"] = self._is_2fa_required(user)
        return context

    def _is_2fa_required(self, user) -> bool:
        return user.is_superuser or user.is_staff

    def post(self, request, *args, **kwargs):
        code = request.POST.get("code", "").strip()
        if not code:
            messages.error(request, "Bitte geben Sie den Code ein.")
            return self.get(request, *args, **kwargs)
        user = request.user
        if verify_totp_code(user, code):
            user.two_factor_enabled = True
            user.two_factor_method = "TOTP"
            user.save(update_fields=["two_factor_enabled", "two_factor_method"])
            request.session["recovery_codes"] = generate_recovery_codes(user)
            request.session["2fa_verified"] = True
            messages.success(request, "2FA wurde erfolgreich aktiviert!")
            return redirect("accounts:2fa_recovery_codes")
        messages.error(request, "Ungültiger Code. Bitte versuchen Sie es erneut.")
        return self.get(request, *args, **kwargs)


@method_decorator(ratelimit(key="user", rate="5/5m", method="POST"), name="post")
class TwoFactorVerifyView(TemplateView):
    template_name = "accounts/2fa_verify.html"

    def _get_user_for_verification(self):
        user_id = self.request.session.get("2fa_user_id")
        if user_id:
            try:
                return User.objects.get(id=user_id)
            except User.DoesNotExist:
                return None
        return self.request.user if self.request.user.is_authenticated else None

    def get(self, request, *args, **kwargs):
        if not self._get_user_for_verification():
            messages.error(request, "Sitzung abgelaufen. Bitte melden Sie sich erneut an.")
            return redirect("accounts:login")
        if request.session.get("2fa_verified"):
            return redirect("core:dashboard")
        return super().get(request, *args, **kwargs)

    @method_decorator(ratelimit(key="ip", rate="5/5m", method="POST"))
    def post(self, request, *args, **kwargs):
        if getattr(request, "limited", False):
            messages.error(request, "Zu viele Versuche. Bitte warten Sie 5 Minuten.")
            return self.get(request, *args, **kwargs)
        user = self._get_user_for_verification()
        if not user:
            messages.error(request, "Sitzung abgelaufen. Bitte melden Sie sich erneut an.")
            return redirect("accounts:login")
        code = request.POST.get("code", "").strip()
        use_recovery = request.POST.get("use_recovery", False)
        if not code:
            messages.error(request, "Bitte geben Sie den Code ein.")
            return self.get(request, *args, **kwargs)
        if use_recovery:
            if verify_recovery_code(user, code):
                return self._handle_successful_verification(user)
            messages.error(request, "Ungültiger Recovery-Code.")
            return self.get(request, *args, **kwargs)
        if verify_totp_code(user, code):
            return self._handle_successful_verification(user)
        messages.error(request, "Ungültiger Code. Bitte versuchen Sie es erneut.")
        return self.get(request, *args, **kwargs)

    def _handle_successful_verification(self, user):
        from django.contrib.auth import login

        if "2fa_user_id" in self.request.session:
            login(self.request, user, backend="django.contrib.auth.backends.ModelBackend")
            self.request.session.pop("2fa_user_id", None)
            self.request.session.pop("2fa_login_timestamp", None)
        self.request.session["2fa_verified"] = True
        remaining = get_available_recovery_codes_count(user)
        if remaining <= 2:
            messages.warning(self.request, f"Achtung: Nur noch {remaining} Recovery-Codes verfügbar!")
        messages.success(self.request, "2FA-Verifizierung erfolgreich.")
        return redirect("core:dashboard")


class RecoveryCodesView(LoginRequiredMixin, TemplateView):
    template_name = "accounts/recovery_codes.html"

    def get_context_data(self, **kwargs):
        import json

        context = super().get_context_data(**kwargs)
        recovery_codes = self.request.session.pop("recovery_codes", None)
        context["recovery_codes"] = recovery_codes
        if recovery_codes:
            context["recovery_codes_json"] = json.dumps(recovery_codes)
        context["available_count"] = get_available_recovery_codes_count(self.request.user)
        return context

    def post(self, request, *args, **kwargs):
        if not request.user.two_factor_enabled:
            messages.error(request, "2FA ist nicht aktiviert.")
            return redirect("accounts:profile")
        request.session["recovery_codes"] = generate_recovery_codes(request.user)
        messages.success(request, "Neue Recovery-Codes wurden generiert.")
        return self.get(request, *args, **kwargs)


class TwoFactorDisableView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        user = request.user
        user.two_factor_enabled = False
        user.two_factor_method = ""
        user.totp_secret = ""
        user.save(update_fields=["two_factor_enabled", "two_factor_method", "totp_secret"])
        user.recovery_codes.all().delete()
        request.session.pop("2fa_verified", None)
        messages.success(request, "2FA wurde deaktiviert.")
        return redirect("accounts:profile")
