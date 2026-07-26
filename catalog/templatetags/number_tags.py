from django import template
from django.utils.safestring import mark_safe
import locale

register = template.Library()


def nepali_number_format(value):
    """Format number in Nepali/Indian system: 12,83,705 instead of 1,283,705"""
    try:
        if value is None:
            return '0'
        if isinstance(value, str):
            value = float(value)
        if isinstance(value, float):
            if value == int(value) and abs(value) < 1e15:
                value = int(value)
            else:
                negative = value < 0
                value = abs(value)
                parts = f"{value:.2f}".split('.')
                int_part = parts[0]
                dec_part = parts[1]
                formatted = nepali_format_int(int_part)
                result = f"{formatted}.{dec_part}"
                return f"-{result}" if negative else result
        value = int(value)
        negative = value < 0
        value = abs(value)
        result = nepali_format_int(str(value))
        return f"-{result}" if negative else result
    except (ValueError, TypeError):
        return value


def nepali_format_int(int_str):
    """Format integer string in Nepali grouping: first 3, then every 2"""
    if len(int_str) <= 3:
        return int_str
    result = int_str[-3:]
    remaining = int_str[:-3]
    while remaining:
        chunk = remaining[-2:]
        result = chunk + ',' + result
        remaining = remaining[:-2]
    return result


@register.filter(name='nepali')
def nepali_filter(value):
    return nepali_number_format(value)


@register.filter(name='nepali_currency')
def nepali_currency(value):
    formatted = nepali_number_format(value)
    return mark_safe(f'रू {formatted}')


@register.filter(name='nepali_percent')
def nepali_percent(value):
    try:
        return f'{nepali_number_format(value)}%'
    except:
        return f'{value}%'
