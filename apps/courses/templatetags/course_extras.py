from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """Django templates can't do dict[variable_key] natively — this fills
    that gap for looking up a student's score by assessment column name."""
    if not dictionary:
        return None
    return dictionary.get(key)