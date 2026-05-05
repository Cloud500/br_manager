"""Form tests for configurable e-mail templates."""

from django.test import TestCase

from apps.email_templates.forms import EmailTemplateForm
from apps.email_templates.models import EmailTemplate


class EmailTemplateFormTest(TestCase):
    """Tests for template form sanitization."""

    def test_body_html_is_sanitized_before_saving(self):
        """Dangerous HTML is removed while safe formatting is preserved."""
        template = EmailTemplate.get_default(EmailTemplate.USER_INVITATION)
        form = EmailTemplateForm(
            data={
                "subject": "Einladung {{ recipient_email }}",
                "body_html": (
                    '<p onclick="alert(1)">Hallo '
                    '<strong>{{ recipient_email }}</strong></p>'
                    '<script>alert("x")</script>'
                    '<a href="javascript:alert(1)">Unsicher</a>'
                    '<a href="https://example.test">Sicher</a>'
                ),
            },
            instance=template,
        )

        self.assertTrue(form.is_valid(), form.errors)
        saved = form.save()

        self.assertIn("<p>Hallo <strong>{{ recipient_email }}</strong></p>", saved.body_html)
        self.assertIn('<a href="https://example.test">Sicher</a>', saved.body_html)
        self.assertNotIn("onclick", saved.body_html)
        self.assertNotIn("script", saved.body_html)
        self.assertNotIn("javascript:", saved.body_html)

    def test_body_text_is_derived_from_formatted_body(self):
        """The plain-text fallback is generated from the single formatted field."""
        template = EmailTemplate.get_default(EmailTemplate.USER_INVITATION)
        form = EmailTemplateForm(
            data={
                "subject": "Einladung {{ recipient_email }}",
                "body_html": "<h2>Hallo</h2><p>{{ recipient_email }}<br>Willkommen</p>",
            },
            instance=template,
        )

        self.assertTrue(form.is_valid(), form.errors)
        saved = form.save()

        self.assertEqual(saved.body_text, "Hallo\n\n{{ recipient_email }}\nWillkommen")

    def test_form_initializes_formatted_body_from_text_fallback(self):
        """Existing text-only templates are shown in the formatted editor."""
        template = EmailTemplate.get_default(EmailTemplate.MEETING_INVITATION)
        template.body_html = ""
        template.save()

        form = EmailTemplateForm(instance=template)

        self.assertIn("<p>", form.initial["body_html"])
        self.assertIn("{{ recipient_name }}", form.initial["body_html"])
