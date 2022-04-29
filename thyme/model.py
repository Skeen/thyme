# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
import datetime

from pydantic import BaseModel


class TimeEntry(BaseModel):
    id: int
    issue: int
    description: str
    hours: float
    date: datetime.date
