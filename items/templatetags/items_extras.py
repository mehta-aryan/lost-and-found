from django import template
from django.core.paginator import Paginator
from django.utils.timesince import timesince

register = template.Library()


@register.simple_tag(takes_context=True)
def page_url(context, param, number, tab=None):
    """Build a '?…' URL that keeps the current filters and changes one page number."""
    params = context['request'].GET.copy()
    params[param] = number
    if tab:
        params['tab'] = tab
    return '?' + params.urlencode()


@register.simple_tag
def elided_pages(page_obj):
    """Page numbers with '…' gaps, e.g. [1, '…', 4, 5, 6, '…', 20]."""
    return list(page_obj.paginator.get_elided_page_range(
        page_obj.number, on_each_side=1, on_ends=1))


@register.filter
def is_ellipsis(value):
    return value == Paginator.ELLIPSIS


@register.filter
def ago(value):
    """'12 hours, 18 minutes' -> '12 hours ago' (largest unit only)."""
    if not value:
        return ''
    text = timesince(value).split(',')[0].replace('\xa0', ' ')
    return 'just now' if text.startswith('0 ') else f'{text} ago'
