"""Forms for protocol editing."""

import re
from html import escape
from html.parser import HTMLParser
from urllib.parse import urlparse

from django import forms


ALLOWED_PROTOCOL_HTML_TAGS = {
    "a",
    "b",
    "blockquote",
    "br",
    "div",
    "em",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "i",
    "li",
    "ol",
    "p",
    "s",
    "span",
    "strong",
    "sub",
    "sup",
    "u",
    "ul",
}
VOID_PROTOCOL_HTML_TAGS = {"br"}
SKIPPED_PROTOCOL_HTML_TAGS = {"script", "style"}
SAFE_PROTOCOL_LINK_SCHEMES = {"", "http", "https", "mailto"}
ALLOWED_PROTOCOL_CLASSES = re.compile(r"^(ql-(align|indent|size)-[a-z0-9-]+|ql-ui)$")
ALLOWED_PROTOCOL_DATA_LIST_VALUES = {"ordered", "bullet", "checked", "unchecked"}
ALLOWED_PROTOCOL_CSS_PROPERTIES = {"color", "background-color", "text-align"}
SAFE_PROTOCOL_CSS_VALUE = re.compile(r"^[#(),.%\w\s-]+$")


class ProtocolNoteHTMLSanitizer(HTMLParser):
    """Allowlist sanitizer for Quill-generated protocol note HTML."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.skipped_tag_depth = 0

    def handle_starttag(self, tag, attrs):
        """Keep supported tags and safe attributes."""
        tag = tag.lower()
        if tag in SKIPPED_PROTOCOL_HTML_TAGS:
            self.skipped_tag_depth += 1
            return
        if self.skipped_tag_depth or tag not in ALLOWED_PROTOCOL_HTML_TAGS:
            return

        attributes = self._sanitize_attrs(tag, attrs)
        self.parts.append(f"<{tag}{attributes}>")

    def handle_startendtag(self, tag, attrs):
        """Handle self-closing tags."""
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag):
        """Close supported non-void tags."""
        tag = tag.lower()
        if tag in SKIPPED_PROTOCOL_HTML_TAGS and self.skipped_tag_depth:
            self.skipped_tag_depth -= 1
            return
        if self.skipped_tag_depth or tag not in ALLOWED_PROTOCOL_HTML_TAGS or tag in VOID_PROTOCOL_HTML_TAGS:
            return
        self.parts.append(f"</{tag}>")

    def handle_data(self, data):
        """Escape text content."""
        if not self.skipped_tag_depth:
            self.parts.append(escape(data, quote=False))

    def handle_entityref(self, name):
        """Preserve HTML entities as text."""
        if not self.skipped_tag_depth:
            self.parts.append(f"&{name};")

    def handle_charref(self, name):
        """Preserve character references as text."""
        if not self.skipped_tag_depth:
            self.parts.append(f"&#{name};")

    def get_html(self) -> str:
        """Return sanitized HTML."""
        return "".join(self.parts).strip()

    def _sanitize_attrs(self, tag: str, attrs: list[tuple[str, str | None]]) -> str:
        """Return serialized safe attributes for Quill output."""
        safe_attrs = []
        for name, value in attrs:
            name = name.lower()
            value = value or ""
            if tag == "a" and name == "href" and self._is_safe_href(value):
                safe_attrs.append(f'href="{escape(value, quote=True)}"')
            elif tag == "a" and name == "title":
                safe_attrs.append(f'title="{escape(value, quote=True)}"')
            elif name == "class":
                sanitized_class = self._sanitize_class(value)
                if sanitized_class:
                    safe_attrs.append(f'class="{sanitized_class}"')
            elif tag == "li" and name == "data-list" and value in ALLOWED_PROTOCOL_DATA_LIST_VALUES:
                safe_attrs.append(f'data-list="{escape(value, quote=True)}"')
            elif name == "style":
                sanitized_style = self._sanitize_style(value)
                if sanitized_style:
                    safe_attrs.append(f'style="{sanitized_style}"')
        if not safe_attrs:
            return ""
        return " " + " ".join(safe_attrs)

    def _sanitize_class(self, value: str) -> str:
        """Keep only Quill formatting classes."""
        classes = [css_class for css_class in value.split() if ALLOWED_PROTOCOL_CLASSES.match(css_class)]
        return escape(" ".join(classes), quote=True)

    def _sanitize_style(self, value: str) -> str:
        """Keep a small safe subset of inline styles used by Quill."""
        declarations = []
        for declaration in value.split(";"):
            if ":" not in declaration:
                continue
            property_name, property_value = declaration.split(":", 1)
            property_name = property_name.strip().lower()
            property_value = property_value.strip()
            if property_name not in ALLOWED_PROTOCOL_CSS_PROPERTIES:
                continue
            if not SAFE_PROTOCOL_CSS_VALUE.match(property_value):
                continue
            declarations.append(f"{property_name}: {property_value}")
        return escape("; ".join(declarations), quote=True)

    @staticmethod
    def _is_safe_href(value: str) -> bool:
        """Allow normal safe links."""
        return urlparse(value.strip()).scheme.lower() in SAFE_PROTOCOL_LINK_SCHEMES


def sanitize_protocol_note_html(value: str) -> str:
    """Sanitize formatted protocol note HTML."""
    sanitizer = ProtocolNoteHTMLSanitizer()
    sanitizer.feed(value or "")
    sanitizer.close()
    return sanitizer.get_html()


class ProtocolAgendaItemNoteForm(forms.Form):
    """Edit the clerk note of one agenda item."""

    body = forms.CharField(
        label="Protokollnotiz",
        required=False,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 5}),
        help_text="Absätze und einfache Listen können direkt im Textfeld formatiert werden.",
    )

    def clean_body(self):
        """Sanitize formatted protocol note HTML before storing it."""
        return sanitize_protocol_note_html(self.cleaned_data.get("body", ""))


class ProtocolBodyForm(forms.Form):
    """Edit the main protocol body after the meeting."""

    body = forms.CharField(
        label="Protokolltext",
        required=False,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 12}),
        help_text="Strukturierter Protokolltext. Absätze und Listen bleiben nachvollziehbar erhalten.",
    )
