"""Forms for configurable e-mail templates."""

import re
from html import escape
from html.parser import HTMLParser
from urllib.parse import urlparse

from django import forms

from apps.email_templates.models import EmailTemplate


ALLOWED_HTML_TAGS = {
    "a",
    "blockquote",
    "br",
    "div",
    "em",
    "h1",
    "h2",
    "h3",
    "h4",
    "i",
    "li",
    "ol",
    "p",
    "strong",
    "u",
    "ul",
}
VOID_HTML_TAGS = {"br"}
SKIPPED_HTML_TAGS = {"script", "style"}
ALLOWED_ATTRIBUTES = {
    "a": {"href", "title"},
}
SAFE_LINK_SCHEMES = {"", "http", "https", "mailto"}
BLOCK_TEXT_TAGS = {
    "blockquote",
    "div",
    "h1",
    "h2",
    "h3",
    "h4",
    "li",
    "ol",
    "p",
    "ul",
}


class EmailTemplateHTMLSanitizer(HTMLParser):
    """Small allowlist sanitizer for formatted e-mail template HTML."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.skipped_tag_depth = 0

    def handle_starttag(self, tag, attrs):
        """Keep only supported tags and safe attributes."""
        tag = tag.lower()
        if tag in SKIPPED_HTML_TAGS:
            self.skipped_tag_depth += 1
            return
        if self.skipped_tag_depth or tag not in ALLOWED_HTML_TAGS:
            return

        attributes = self._sanitize_attrs(tag, attrs)
        self.parts.append(f"<{tag}{attributes}>")

    def handle_startendtag(self, tag, attrs):
        """Handle self-closing tags."""
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag):
        """Close supported non-void tags."""
        tag = tag.lower()
        if tag in SKIPPED_HTML_TAGS and self.skipped_tag_depth:
            self.skipped_tag_depth -= 1
            return
        if self.skipped_tag_depth or tag not in ALLOWED_HTML_TAGS or tag in VOID_HTML_TAGS:
            return
        self.parts.append(f"</{tag}>")

    def handle_data(self, data):
        """Escape text content while preserving placeholders as text."""
        if not self.skipped_tag_depth:
            self.parts.append(escape(data, quote=False))

    def handle_entityref(self, name):
        """Preserve safe HTML entities as text."""
        if not self.skipped_tag_depth:
            self.parts.append(f"&{name};")

    def handle_charref(self, name):
        """Preserve safe character references as text."""
        if not self.skipped_tag_depth:
            self.parts.append(f"&#{name};")

    def get_html(self) -> str:
        """Return sanitized HTML."""
        return "".join(self.parts).strip()

    def _sanitize_attrs(self, tag: str, attrs: list[tuple[str, str | None]]) -> str:
        """Return serialized safe attributes for the given tag."""
        allowed = ALLOWED_ATTRIBUTES.get(tag, set())
        safe_attrs = []
        for name, value in attrs:
            name = name.lower()
            if name not in allowed or value is None:
                continue
            if name == "href" and not self._is_safe_href(value):
                continue
            safe_attrs.append(f'{name}="{escape(value, quote=True)}"')
        if not safe_attrs:
            return ""
        return " " + " ".join(safe_attrs)

    @staticmethod
    def _is_safe_href(value: str) -> bool:
        """Allow normal links and placeholder-only dynamic links."""
        stripped_value = value.strip()
        if stripped_value.startswith("{{") and stripped_value.endswith("}}"):
            return True
        return urlparse(stripped_value).scheme.lower() in SAFE_LINK_SCHEMES


def sanitize_email_template_html(value: str) -> str:
    """Sanitize formatted HTML for e-mail templates."""
    sanitizer = EmailTemplateHTMLSanitizer()
    sanitizer.feed(value or "")
    sanitizer.close()
    return sanitizer.get_html()


class EmailTemplateTextExtractor(HTMLParser):
    """Extract a readable plain-text fallback from formatted HTML."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.skipped_tag_depth = 0

    def handle_starttag(self, tag, attrs):
        """Add line breaks for visible HTML structure."""
        tag = tag.lower()
        if tag in SKIPPED_HTML_TAGS:
            self.skipped_tag_depth += 1
            return
        if self.skipped_tag_depth:
            return
        if tag == "br":
            self.parts.append("\n")

    def handle_endtag(self, tag):
        """Add paragraph breaks for block tags."""
        tag = tag.lower()
        if tag in SKIPPED_HTML_TAGS and self.skipped_tag_depth:
            self.skipped_tag_depth -= 1
            return
        if self.skipped_tag_depth:
            return
        if tag in BLOCK_TEXT_TAGS:
            self.parts.append("\n\n")

    def handle_data(self, data):
        """Collect visible text."""
        if not self.skipped_tag_depth:
            self.parts.append(data)

    def get_text(self) -> str:
        """Return normalized text."""
        text = "".join(self.parts)
        text = re.sub(r"[ \t\r\f\v]+", " ", text)
        text = re.sub(r" *\n *", "\n", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()


def html_to_plain_text(value: str) -> str:
    """Create the plain-text e-mail body from formatted HTML."""
    extractor = EmailTemplateTextExtractor()
    extractor.feed(value or "")
    extractor.close()
    return extractor.get_text()


def plain_text_to_html(value: str) -> str:
    """Create simple editable HTML from existing text-only templates."""
    paragraphs = []
    current_lines = []
    for line in (value or "").splitlines():
        if line.strip():
            current_lines.append(escape(line.strip(), quote=False))
            continue
        if current_lines:
            paragraphs.append("<p>" + "<br>".join(current_lines) + "</p>")
            current_lines = []
    if current_lines:
        paragraphs.append("<p>" + "<br>".join(current_lines) + "</p>")
    return "\n".join(paragraphs)


class EmailTemplateForm(forms.ModelForm):
    """Form for editing system-provided e-mail templates."""

    def __init__(self, *args, **kwargs):
        """Show one formatted content field, even for text-only templates."""
        super().__init__(*args, **kwargs)
        self.fields["body_html"].label = "Formatierter Inhalt"
        self.fields["body_html"].required = True
        if self.instance and self.instance.pk and not self.initial.get("body_html"):
            self.initial["body_html"] = plain_text_to_html(self.instance.body_text)

    def clean_body_html(self):
        """Sanitize the optional HTML e-mail body before model validation."""
        body_html = sanitize_email_template_html(self.cleaned_data.get("body_html", ""))
        if not html_to_plain_text(body_html):
            raise forms.ValidationError("Der Inhalt darf nicht leer sein.")
        return body_html

    def save(self, commit=True):
        """Save formatted content and derive the plain-text fallback."""
        instance = super().save(commit=False)
        instance.body_text = html_to_plain_text(instance.body_html)
        if commit:
            instance.save()
            self.save_m2m()
        return instance

    class Meta:
        model = EmailTemplate
        fields = ["subject", "body_html"]
        widgets = {
            "subject": forms.TextInput(attrs={"class": "form-control"}),
            "body_html": forms.Textarea(attrs={
                "class": "d-none",
                "data-rich-text-source": "email-template-html",
                "rows": 14,
            }),
        }
