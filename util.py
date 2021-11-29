from datetime import date
from datetime import datetime

import pytz
from pytz import timezone


def hours_from_datetimes(
    start: datetime, end: datetime, rounding: bool = False
) -> float:
    delta = end - start
    hours = delta.seconds // 3600
    minutes = (delta.seconds // 60) % 60
    if rounding:
        minutes = 15 * round(minutes / 15)

    return hours + (minutes / 60)


def convert_date_to_datetime(input_date: date) -> datetime:
    # TODO: Make timezone configurable
    return pytz.utc.localize(datetime.combine(input_date, datetime.min.time()))


def parse_timestamp(time: str) -> datetime:
    if ":" in time:
        parsed = datetime.strptime(time, "%H:%M")
    else:
        parsed = datetime.strptime(time, "%H%M")
    naive = datetime.combine(datetime.now(), parsed.time())
    return timezone("Europe/Copenhagen").localize(naive)
