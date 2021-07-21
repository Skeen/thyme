import datetime

from pydantic import BaseModel


class TimeEntry(BaseModel):
    issue: int
    description: str
    hours: float
    date: datetime.date
