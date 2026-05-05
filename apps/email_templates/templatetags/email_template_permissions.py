"""Template tags for e-mail template permissions."""

from django import template

from apps.email_templates.permissions import user_can_manage_email_templates

register = template.Library()


@register.simple_tag
def can_manage_email_templates(user) -> bool:
    """Expose e-mail template management permission to templates."""
    return user_can_manage_email_templates(user)
