"""12-hour display time for script output: 2:05 pm, 12:00 am."""


def clock12(dt):
    """`{h % 12 or 12}:{mm} {am|pm}` for the hour and minute of `dt` as given; callers convert to UTC first."""
    return f"{dt.hour % 12 or 12}:{dt.minute:02d} {'am' if dt.hour < 12 else 'pm'}"
