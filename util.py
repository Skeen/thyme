from datetime import datetime


def hours_from_datetimes(
    start: datetime, end: datetime, rounding: bool = False
) -> float:
    delta = end - start
    hours = delta.seconds // 3600
    minutes = (delta.seconds // 60) % 60
    if rounding:
        minutes = 15 * round(minutes / 15)

    return hours + (minutes / 60)
