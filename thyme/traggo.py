# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
import math
from collections.abc import Callable
from collections.abc import Iterable
from collections.abc import Iterator
from collections.abc import Mapping
from datetime import date
from datetime import datetime
from datetime import timedelta
from typing import Any
from typing import cast
from typing import TypeVar

import pytz
from gql import Client
from gql import gql
from gql.transport.requests import RequestsHTTPTransport
from more_itertools import first
from more_itertools import one
from more_itertools import unzip
from pydantic import BaseModel

from .model import TimeEntry
from .requests import get_timers_query
from .requests import get_timespan_query
from .requests import start_timer_mutation
from .requests import stop_timer_mutation
from .requests import update_timer_mutation
from .util import convert_date_to_datetime
from .util import hours_from_datetimes


T = TypeVar("T")


def starstarmap(
    function: Callable[..., T], iterable: Iterable[Mapping[str, Any]]
) -> Iterator[T]:
    for args in iterable:
        yield function(**args)


class MissingIssue(Exception):
    pass


class MultipleActiveTimers(Exception):
    pass


class TraggoTimeSpan(BaseModel):
    id: int
    note: str
    start: datetime
    end: datetime
    issue: int

    @classmethod
    def parse_from_dict(
        cls, id: int, note: str, start: datetime, end: datetime, tags: list[dict]
    ) -> "TraggoTimeSpan":
        try:
            issue = one(filter(lambda x: x["key"] == "issue", tags))["value"]
        except ValueError:
            raise MissingIssue(note, start, end)

        return cls(id=id, note=note, start=start, end=end, issue=issue)


class TraggoTimer(BaseModel):
    id: str
    note: str
    start: datetime
    issue: str | None
    type: str | None

    @classmethod
    def from_dict(
        cls, id: str, note: str, start: datetime, tags: list[dict]
    ) -> "TraggoTimer":
        issue = first(filter(lambda x: x["key"] == "issue", tags), {}).get("value")
        type = first(filter(lambda x: x["key"] == "type", tags), {}).get("value")

        return cls(id=id, note=note, start=start, issue=issue, type=type)

    def to_dict(self) -> dict:
        tags = []
        if self.issue:
            tags.append({"key": "issue", "value": self.issue})
        if self.type:
            tags.append({"key": "type", "value": self.type})

        return {
            "id": int(self.id),
            "start": self.start.isoformat(),
            "note": self.note,
            "tags": tags,
        }


class TraggoConnector:
    def __init__(self, url: str, api_token: str, user_id: int | None = None):
        self._url = url
        self._api_token = api_token

        self.traggo = self._get_client(url, api_token, user_id)

    def as_user(self, user_id: int) -> "TraggoConnector":
        return TraggoConnector(self._url, self._api_token, user_id)

    def _get_client(self, url: str, api_token: str, user_id: int | None) -> Client:
        url = f"{url}/graphql"
        headers = {
            "Authorization": f"traggo {api_token}",
        }
        if user_id is not None:
            headers["X-Traggo-Impersonate"] = str(user_id)

        transport = RequestsHTTPTransport(url=url, headers=headers)
        return Client(transport=transport, fetch_schema_from_transport=True)

    def get_all_users(self) -> dict[int, dict[str, Any]]:
        query = gql(
            """
            query GetAllUsers {
              users {
                id
                name
                admin
              }
            }
        """
        )
        result = self.traggo.execute(query)
        usermap = {
            x["id"]: {"name": x["name"], "admin": x["admin"]} for x in result["users"]
        }
        return usermap

    def get_current_user(self) -> dict[str, Any]:
        query = gql(
            """
            query GetCurrentUser {
              currentUser {
                id
                name
                admin
              }
            }
        """
        )
        result = self.traggo.execute(query)
        return cast(dict[str, Any], result["currentUser"])

    def _convert_date_to_datetime(self, input_date: date) -> datetime:
        # TODO: Make timezone configurable
        return pytz.utc.localize(datetime.combine(input_date, datetime.min.time()))

    def _convert_timespan(self, timespan: TraggoTimeSpan) -> tuple[TimeEntry, float]:
        hours = hours_from_datetimes(timespan.start, timespan.end, rounding=True)
        hours_no_rounding = hours_from_datetimes(
            timespan.start, timespan.end, rounding=False
        )

        return (
            TimeEntry(
                id=timespan.id,
                issue=timespan.issue,
                description=timespan.note,
                hours=hours,
                date=timespan.start,
            ),
            hours_no_rounding - hours,
        )

    def _get_timespans(
        self, from_date: date, to_date: date
    ) -> Iterable[TraggoTimeSpan]:
        from_datetime = convert_date_to_datetime(from_date)
        to_datetime = convert_date_to_datetime(to_date) + timedelta(days=1)

        document = get_timespan_query()
        vars = {
            "from": from_datetime.isoformat(),
            "to": to_datetime.isoformat(),
        }
        # Loop as long as there are more pages
        while True:
            result = self.traggo.execute(document, variable_values=vars)
            paged_timespans = result["timeSpans"]
            # Yield all parsed timespans in this page
            timespans = paged_timespans["timeSpans"]
            yield from starstarmap(TraggoTimeSpan.parse_from_dict, timespans)
            # Fetch more pages using cursor (if more are available)
            cursor = paged_timespans["cursor"]
            if not cursor.pop("hasMore"):
                return
            vars["cursor"] = cursor

    def get_time_entries(self, from_date: date, to_date: date) -> list[TimeEntry]:
        timespans = list(self._get_timespans(from_date, to_date))
        print(timespans)
        if not timespans:
            return []
        time_entries, rounding_errors = unzip(map(self._convert_timespan, timespans))
        # Add rounding compensation
        time_entries = list(time_entries)
        time_entries[0].hours += math.ceil(sum(rounding_errors) * 4) / 4
        return cast(list[TimeEntry], time_entries)

    def start_timer(
        self, start_time: datetime, issue: str, type: str, note: str
    ) -> None:
        document, vars = start_timer_mutation(
            start_time, issue=issue, type=type, note=note
        )
        self.traggo.execute(document, variable_values=vars)

    def get_timers(self) -> Iterable[TraggoTimer]:
        r = self.traggo.execute(get_timers_query()).get("timers")
        timers = list(map(lambda x: TraggoTimer.from_dict(**x), r))
        if len(timers) > 1:
            raise MultipleActiveTimers()
        return timers

    def stop_timer(self, timer: TraggoTimer, stop_time: datetime) -> None:
        document, vars = stop_timer_mutation(timer.id, stop_time)
        self.traggo.execute(document, variable_values=vars)

    def update_timer(self, timer: TraggoTimer) -> None:
        document = update_timer_mutation()

        vars = timer.to_dict()
        self.traggo.execute(document, variable_values=vars)
