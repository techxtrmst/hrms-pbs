from django import template

register = template.Library()


@register.filter
def duration_human(td):
    """
    Converts a timedelta (or plain int seconds) into human-readable form.
    e.g.  10       →  10s
          90       →  1m 30s
          3780     →  1h 3m
          timedelta(seconds=10) → 10s
    """
    if td is None:
        return "—"
    try:
        # Accept both timedelta and plain int/float seconds
        total_seconds = int(td.total_seconds()) if hasattr(td, "total_seconds") else int(td)
    except (TypeError, ValueError):
        return "—"

    if total_seconds < 0:
        return "0s"

    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    parts = []
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    if seconds or not parts:
        parts.append(f"{seconds}s")

    return " ".join(parts)


@register.filter
def duration_seconds_total(td):
    """Returns the total number of seconds in a timedelta (int)."""
    if td is None:
        return 0
    try:
        return int(td.total_seconds())
    except AttributeError:
        return 0


@register.filter
def percent_of(value, max_val):
    """Returns value as a percentage of max_val, clamped to 3–100."""
    try:
        pct = (int(value) / int(max_val)) * 100
        return max(3, min(100, round(pct)))
    except (TypeError, ZeroDivisionError):
        return 3
