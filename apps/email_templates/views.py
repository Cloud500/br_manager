"""Views for e-mail template management."""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from django.views.generic import ListView, UpdateView

from apps.email_templates.forms import EmailTemplateForm
from apps.email_templates.models import EmailTemplate
from apps.email_templates.permissions import user_can_manage_email_templates


class EmailTemplatePermissionMixin(UserPassesTestMixin):
    """Require the e-mail template edit permission."""

    raise_exception = True

    def test_func(self) -> bool:
        """Check the current user's custom RBAC permission."""
        return user_can_manage_email_templates(self.request.user)


class EmailTemplateListView(LoginRequiredMixin, EmailTemplatePermissionMixin, ListView):
    """List editable system e-mail templates."""

    model = EmailTemplate
    template_name = "email_templates/email_template_list.html"
    context_object_name = "email_templates"

    def get_queryset(self):
        """Ensure system templates exist before listing them."""
        EmailTemplate.ensure_defaults()
        return EmailTemplate.objects.filter(is_system_template=True).order_by(
            "sort_order",
            "name",
        )


class EmailTemplateUpdateView(LoginRequiredMixin, EmailTemplatePermissionMixin, UpdateView):
    """Update an existing system e-mail template."""

    model = EmailTemplate
    form_class = EmailTemplateForm
    template_name = "email_templates/email_template_form.html"
    success_url = reverse_lazy("email_templates:email_template_list")

    def get_queryset(self):
        """Only system-provided templates can be edited."""
        EmailTemplate.ensure_defaults()
        return EmailTemplate.objects.filter(is_system_template=True)

    def form_valid(self, form):
        """Show success message after saving."""
        messages.success(
            self.request,
            f'E-Mail-Vorlage "{self.object.name}" wurde aktualisiert.',
        )
        return super().form_valid(form)

