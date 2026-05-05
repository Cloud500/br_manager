"""Tests for configurable e-mail templates."""

from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.email_templates.models import EmailTemplate


class EmailTemplateModelTest(TestCase):
    """Tests for template defaults, placeholder validation, and rendering."""

    def test_get_default_creates_system_template(self):
        """System templates are available without allowing ad-hoc template creation."""
        template = EmailTemplate.get_default(EmailTemplate.MEETING_INVITATION)

        self.assertEqual(template.key, EmailTemplate.MEETING_INVITATION)
        self.assertTrue(template.is_system_template)
        self.assertIn("meeting_title", template.available_placeholders)
        self.assertIn("{{ meeting_title }}", template.subject)

    def test_render_replaces_allowed_placeholders(self):
        """Rendering replaces configured placeholders in subject and body fields."""
        template = EmailTemplate.get_default(EmailTemplate.MEETING_INVITATION)
        template.subject = "Einladung: {{ meeting_title }}"
        template.body_text = "Hallo {{ recipient_name }}, {{ message }} {{ agenda_text }}"
        template.body_html = "<p>{{ recipient_name }}</p><p>{{ message }}</p>"
        template.save()

        rendered = template.render({
            "recipient_name": "Max Mustermann",
            "meeting_title": "Monatssitzung",
            "message": "Bitte pünktlich sein.",
            "agenda_text": "Tagesordnung:\n1. Begrüßung",
        })

        self.assertEqual(rendered.subject, "Einladung: Monatssitzung")
        self.assertIn("Hallo Max Mustermann", rendered.body_text)
        self.assertIn("Bitte pünktlich sein.", rendered.body_text)
        self.assertIn("Tagesordnung:", rendered.body_text)
        self.assertIn("<p>Max Mustermann</p>", rendered.body_html)

    def test_clean_rejects_unknown_placeholders(self):
        """Templates may only use placeholders defined for their system key."""
        template = EmailTemplate.get_default(EmailTemplate.USER_INVITATION)
        template.subject = "Einladung {{ unknown_placeholder }}"

        with self.assertRaises(ValidationError) as context:
            template.full_clean()

        self.assertIn("unknown_placeholder", str(context.exception))

    def test_render_requires_known_context_values(self):
        """Missing runtime values are rejected instead of sending broken placeholders."""
        template = EmailTemplate.get_default(EmailTemplate.USER_INVITATION)

        with self.assertRaises(ValidationError) as context:
            template.render({"invite_url": "https://example.test/register"})

        self.assertIn("inviter_name", str(context.exception))
