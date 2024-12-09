from django import template

register = template.Library()

@register.filter
def multiply(value, arg):
    return value * arg

@register.filter
def endswith(value, arg):
    """Check if value ends with arg."""
    return str(value).endswith(str(arg))