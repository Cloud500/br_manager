"""View and permission tests for e-mail template management."""

from datetime import date

from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import User
from apps.committees.models import Committee, Membership
from apps.email_templates.models import EmailTemplate
from apps.roles.models import Permission, Role, RolePermission


class EmailTemplateViewTest(TestCase):
    """Tests for server-side template management permissions."""

    def setUp(self):
        self.template = EmailTemplate.get_default(EmailTemplate.MEETING_INVITATION)
        self.permission, _created = Permission.objects.get_or_create(
            codename="email_template.edit",
            defaults={
                "name": "E-Mail-Vorlagen bearbeiten",
                "category": "email_template",
            },
        )
        self.chair_role, _created = Role.objects.get_or_create(
            codename="CHAIR",
            defaults={
                "name": "Vorsitz",
                "role_type": "COMMITTEE",
            },
        )
        self.member_role, _created = Role.objects.get_or_create(
            codename="MEMBER",
            defaults={
                "name": "Mitglied",
                "role_type": "COMMITTEE",
            },
        )
        RolePermission.objects.get_or_create(
            role=self.chair_role,
            permission=self.permission,
        )
        self.committee = Committee.objects.create(
            name="BR E-Mail",
            committee_type="MAIN",
            total_seats=5,
        )
        self.chair = User.objects.create_user(
            email="chair@example.com",
            password="testpass123",
            first_name="Chair",
            last_name="User",
            gender="F",
        )
        self.member = User.objects.create_user(
            email="member@example.com",
            password="testpass123",
            first_name="Member",
            last_name="User",
            gender="M",
        )
        Membership.objects.create(
            user=self.chair,
            committee=self.committee,
            role=self.chair_role,
            member_type="REGULAR",
            start_date=date.today(),
            is_active=True,
        )
        Membership.objects.create(
            user=self.member,
            committee=self.committee,
            role=self.member_role,
            member_type="REGULAR",
            start_date=date.today(),
            is_active=True,
        )

    def test_user_with_dynamic_permission_can_edit_template(self):
        """A role permission grants template editing without hard-coded role checks."""
        self.client.force_login(self.chair)

        response = self.client.post(
            reverse("email_templates:email_template_update", kwargs={"pk": self.template.pk}),
            {
                "subject": "Angepasste Einladung {{ meeting_title }}",
                "body_html": "<p>Hallo {{ recipient_name }}</p><p>{{ agenda_text }}</p>",
            },
        )

        self.assertRedirects(response, reverse("email_templates:email_template_list"))
        self.template.refresh_from_db()
        self.assertEqual(self.template.subject, "Angepasste Einladung {{ meeting_title }}")

    def test_user_without_permission_cannot_edit_template(self):
        """Template editing is denied server-side without the RBAC permission."""
        self.client.force_login(self.member)

        response = self.client.get(
            reverse("email_templates:email_template_update", kwargs={"pk": self.template.pk})
        )

        self.assertEqual(response.status_code, 403)

    def test_superuser_can_access_template_list(self):
        """Administrators can manage templates by default."""
        admin = User.objects.create_superuser(
            email="admin@example.com",
            password="testpass123",
            first_name="Admin",
            last_name="User",
            gender="M",
            two_factor_enabled=True,
        )
        self.client.force_login(admin)

        response = self.client.get(reverse("email_templates:email_template_list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "E-Mail-Vorlagen")

    def test_edit_page_contains_local_formatting_editor(self):
        """The HTML body can be edited with a local formatting toolbar."""
        self.client.force_login(self.chair)

        response = self.client.get(
            reverse("email_templates:email_template_update", kwargs={"pk": self.template.pk})
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Formatierung")
        self.assertContains(response, "email_template_editor.js")
        self.assertContains(response, "data-rich-text-source")
        self.assertContains(response, "Formatierter Inhalt")
        self.assertContains(response, "Gerenderte Vorschau")
        self.assertNotContains(response, "Text-Version der E-Mail")
