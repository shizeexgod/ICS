"""Safe string templating for admin-configured notification messages."""

from __future__ import annotations

import string


class _SafeDict(dict):
    """Return the placeholder unchanged when a key is missing."""

    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


def format_template(template_text: str, context: dict) -> str:
    """Safely substitute ``{placeholder}`` values from *context*.

    Unknown placeholders are left as-is instead of raising ``KeyError``.
    """
    safe_context = _SafeDict(context)
    formatter = string.Formatter()
    parts: list[str] = []

    for literal, field_name, format_spec, conversion in formatter.parse(template_text):
        parts.append(literal)
        if field_name is None:
            continue
        value = safe_context[field_name]
        if conversion:
            value = formatter.convert_field(value, conversion)
        if format_spec:
            value = formatter.format_field(value, format_spec)
        parts.append(str(value))

    return "".join(parts)
