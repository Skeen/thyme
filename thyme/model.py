# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
import datetime

from pydantic import BaseModel


class TimeEntry(BaseModel):
    id: int
    note: str

    tags: dict[str, str]

    hours: float
    date: datetime.date

    def get_issue(self) -> str | None:
        return self.tags.get("issue")
