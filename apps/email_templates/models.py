"""Models for configurable system e-mail templates."""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass

from django.core.exceptions import ValidationError
from django.db import models
from django.utils.html import conditional_escape


PLACEHOLDER_PATTERN = re.compile(r"{{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*}}")


@dataclass(frozen=True)
class RenderedEmail:
    """Rendered e-mail content."""

    subject: str
    body_text: str
    body_html: str


class EmailTemplate(models.Model):
    """System-provided e-mail template editable through RBAC permissions."""

    USER_INVITATION = "user_invitation"
    MEETING_INVITATION = "meeting_invitation"

    TEMPLATE_CHOICES = [
        (USER_INVITATION, "Benutzer-Einladung"),
        (MEETING_INVITATION, "Sitzungseinladung"),
    ]

    DEFAULTS = {
        USER_INVITATION: {
            "name": "Benutzer-Einladung",
            "description": "Einladung neuer Benutzer zur Registrierung im BR-Manager.",
            "subject": "Einladung zum BR-Manager",
            "body_text": (
                "Hallo,\n\n"
                "Sie wurden von {{ inviter_name }} zum BR-Manager eingeladen.\n\n"
                "Bitte klicken Sie auf den folgenden Link, um Ihr Konto einzurichten:\n\n"
                "{{ invite_url }}\n\n"
                "Dieser Link ist {{ validity_days }} Tage gültig.\n\n"
                "Mit freundlichen Grüßen\n"
                "Ihr BR-Manager Team\n"
            ),
            "body_html": """
<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
<div style="background-color: #f8f9fa; padding: 20px; border-radius: 5px;">
<h2 style="color: #212529; margin-top: 0;">Einladung zum BR-Manager</h2>
<p>Hallo,</p>
<p>Sie wurden von <strong>{{ inviter_name }}</strong> zum BR-Manager eingeladen.</p>
<p>Bitte klicken Sie auf den folgenden Button, um Ihr Konto einzurichten:</p>
<div style="text-align: center; margin: 30px 0;">
<a href="{{ invite_url }}" style="background-color: #0d6efd; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; display: inline-block; font-weight: bold;">Konto einrichten</a>
</div>
<p style="font-size: 14px; color: #6c757d;">Oder kopieren Sie diesen Link in Ihren Browser:<br><a href="{{ invite_url }}" style="color: #0d6efd; word-break: break-all;">{{ invite_url }}</a></p>
<p style="font-size: 14px; color: #6c757d;"><strong>Hinweis:</strong> Dieser Link ist {{ validity_days }} Tage gültig.</p>
<hr style="border: none; border-top: 1px solid #dee2e6; margin: 20px 0;">
<p style="font-size: 14px; color: #6c757d; margin-bottom: 0;">Mit freundlichen Grüßen<br>Ihr BR-Manager Team</p>
</div>
</body>
</html>""".strip(),
            "available_placeholders": [
                "invite_url",
                "inviter_name",
                "recipient_email",
                "validity_days",
            ],
            "sort_order": 10,
        },
        MEETING_INVITATION: {
            "name": "Sitzungseinladung",
            "description": "Einladung von Teilnehmern zu einer Sitzung inklusive Tagesordnung.",
            "subject": "Einladung: {{ meeting_title }} - {{ meeting_date }}",
            "body_text": (
                "Sehr geehrte/r {{ recipient_name }},\n\n"
                "hiermit laden wir Sie zur Sitzung des {{ committee_name }} ein.\n\n"
                "Titel: {{ meeting_title }}\n"
                "Datum: {{ meeting_date }}\n"
                "Uhrzeit: {{ meeting_start_time }} Uhr\n"
                "Ort: {{ meeting_location }}\n\n"
                "{{ agenda_text }}\n\n"
                "{{ additional_message_block }}\n\n"
                "Mit freundlichen Grüßen\n"
                "BR-Manager"
            ),
            "body_html": "",
            "available_placeholders": [
                "additional_message_block",
                "agenda_text",
                "committee_name",
                "meeting_date",
                "meeting_location",
                "meeting_start_time",
                "meeting_title",
                "message",
                "recipient_email",
                "recipient_name",
            ],
            "sort_order": 20,
        },
    }

    LEGACY_BODY_TEXTS = {
        MEETING_INVITATION: (
            "Sehr geehrte/r {{ recipient_name }},\n\n"
            "hiermit laden wir Sie zur Sitzung des {{ committee_name }} ein.\n\n"
            "Titel: {{ meeting_title }}\n"
            "Datum: {{ meeting_date }}\n"
            "Uhrzeit: {{ meeting_start_time }} Uhr\n"
            "Ort: {{ meeting_location }}"
            "{{ agenda_text }}"
            "{{ additional_message_block }}\n\n"
            "Mit freundlichen Grüßen\n"
            "BR-Manager"
        ),
    }

    PREVIEW_CONTEXTS = {
        USER_INVITATION: {
            "invite_url": "https://br-manager.example/registrieren/beispiel",
            "inviter_name": "Max Mustermann",
            "recipient_email": "mitglied@example.test",
            "validity_days": "7",
        },
        MEETING_INVITATION: {
            "additional_message_block": (
                "Zusätzliche Nachricht:\n"
                "Bitte Unterlagen zur Sitzung mitbringen."
            ),
            "agenda_text": (
                "Tagesordnung:\n"
                "TOP 1: Begrüßung\n"
                "TOP 2: Aktuelle Themen\n"
                "TOP 3: Beschlussfassung"
            ),
            "committee_name": "Betriebsrat",
            "meeting_date": "15.05.2026",
            "meeting_location": "Besprechungsraum 1",
            "meeting_start_time": "10:00",
            "meeting_title": "Monatssitzung",
            "message": "Bitte Unterlagen zur Sitzung mitbringen.",
            "recipient_email": "mitglied@example.test",
            "recipient_name": "Erika Musterfrau",
        },
    }

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    key = models.CharField(
        max_length=100,
        unique=True,
        choices=TEMPLATE_CHOICES,
        verbose_name="Vorlagen-Schlüssel",
    )
    name = models.CharField(
        max_length=150,
        verbose_name="Name",
    )
    description = models.TextField(
        blank=True,
        verbose_name="Beschreibung",
    )
    subject = models.CharField(
        max_length=255,
        verbose_name="Betreff",
    )
    body_text = models.TextField(
        verbose_name="Text-Inhalt",
        help_text="Platzhalter werden mit {{ platzhalter }} eingefügt.",
    )
    body_html = models.TextField(
        blank=True,
        verbose_name="HTML-Inhalt",
        help_text="Optionaler HTML-Inhalt. Leer lassen, wenn nur Text versendet werden soll.",
    )
    available_placeholders = models.JSONField(
        default=list,
        verbose_name="Verfügbare Platzhalter",
    )
    is_system_template = models.BooleanField(
        default=True,
        verbose_name="System-Vorlage",
        help_text="System-Vorlagen können bearbeitet, aber nicht frei neu angelegt werden.",
    )
    sort_order = models.PositiveIntegerField(
        default=100,
        verbose_name="Sortierung",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Erstellt am",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Aktualisiert am",
    )

    class Meta:
        verbose_name = "E-Mail-Vorlage"
        verbose_name_plural = "E-Mail-Vorlagen"
        ordering = ["sort_order", "name"]

    def __str__(self) -> str:
        """Return the template name."""
        return self.name

    @classmethod
    def get_default(cls, key: str) -> "EmailTemplate":
        """Return a system template, creating the basis template if missing."""
        defaults = cls.DEFAULTS[key]
        template, created = cls.objects.get_or_create(
            key=key,
            defaults=defaults,
        )
        if created:
            return template

        changed_fields = []
        for field in ["name", "description", "available_placeholders", "sort_order"]:
            if getattr(template, field) != defaults[field]:
                setattr(template, field, defaults[field])
                changed_fields.append(field)
        if template.body_text == cls.LEGACY_BODY_TEXTS.get(key):
            template.body_text = defaults["body_text"]
            changed_fields.append("body_text")
        if changed_fields:
            template.save(update_fields=[*changed_fields, "updated_at"])
        return template

    @classmethod
    def ensure_defaults(cls) -> list["EmailTemplate"]:
        """Ensure all system templates exist."""
        return [cls.get_default(key) for key in cls.DEFAULTS]

    def get_preview_context(self) -> dict[str, str]:
        """Return sample values for rendering the edit-page preview."""
        preview_context = dict(self.PREVIEW_CONTEXTS.get(self.key, {}))
        for placeholder in self.available_placeholders or []:
            preview_context.setdefault(placeholder, f"{{{{ {placeholder} }}}}")
        return preview_context

    @staticmethod
    def extract_placeholders(content: str) -> set[str]:
        """Extract placeholder names from template content."""
        return set(PLACEHOLDER_PATTERN.findall(content or ""))

    def clean(self):
        """Validate that only supported placeholders are used."""
        super().clean()
        if self.key not in self.DEFAULTS:
            raise ValidationError({"key": "Unbekannte System-Vorlage."})

        used_placeholders = self._used_placeholders()
        allowed_placeholders = set(self.available_placeholders or [])
        unknown_placeholders = used_placeholders - allowed_placeholders
        if unknown_placeholders:
            unknown = ", ".join(sorted(unknown_placeholders))
            raise ValidationError(
                "Diese Platzhalter sind für diese Vorlage nicht erlaubt: "
                f"{unknown}"
            )

    def render(self, context: dict[str, object]) -> RenderedEmail:
        """Render subject, text body and optional HTML body with the given context."""
        self.full_clean()
        used_placeholders = self._used_placeholders()
        missing_placeholders = {
            placeholder for placeholder in used_placeholders
            if placeholder not in context or context[placeholder] is None
        }
        if missing_placeholders:
            missing = ", ".join(sorted(missing_placeholders))
            raise ValidationError(f"Fehlende Werte für Platzhalter: {missing}")

        return RenderedEmail(
            subject=self._render_content(self.subject, context),
            body_text=self._render_content(self.body_text, context),
            body_html=self._render_content(self.body_html, context, escape_html=True),
        )

    def _used_placeholders(self) -> set[str]:
        """Return all placeholders used by this template."""
        return (
            self.extract_placeholders(self.subject)
            | self.extract_placeholders(self.body_text)
            | self.extract_placeholders(self.body_html)
        )

    @staticmethod
    def _render_content(
        content: str,
        context: dict[str, object],
        escape_html: bool = False,
    ) -> str:
        """Replace placeholders in a content string."""
        if not content:
            return ""

        def replace(match: re.Match) -> str:
            value = str(context[match.group(1)])
            if escape_html:
                return str(conditional_escape(value)).replace("\n", "<br>")
            return value

        return PLACEHOLDER_PATTERN.sub(replace, content)

