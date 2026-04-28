"""Custom template tags and filters for the agendas app."""

from django import template

register = template.Library()


@register.filter(name='count_dots')
def count_dots(value: str) -> int:
    """Count the number of dots in a string.
    
    This filter is used to determine the nesting level of agenda items
    by counting dots in their item_number (e.g., "1.2.3" has 2 dots = level 2).
    
    Args:
        value: The string to count dots in (typically an item_number)
        
    Returns:
        The number of dots in the string
        
    Example:
        {{ item.item_number|count_dots }}  # "1.2.3" returns 2
    """
    if not value:
        return 0
    return str(value).count('.')
