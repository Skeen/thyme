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
from more_itertools import unzip
from pydantic import AnyHttpUrl
from pydantic import BaseModel

from .model import TimeEntry


Document = Any


def get_timespan_query() -> Document:
    query = """
        query FetchTimespans(
            $cursor: InputCursor, $from: Time, $to: Time
        ) {
            timeSpans(
                fromInclusive: $from, toInclusive: $to, cursor: $cursor
            ) {
                timeSpans {
                    id
                    note
                    start
                    end
                    tags {
                        key
                        value
                    }
                }
                cursor {
                  hasMore
                  startId
                  offset
                  pageSize
                }
            }
        }
    """
    return gql(query)


def convert_date_to_datetime(input_date: date) -> datetime:
    # TODO: Make timezone configurable
    return pytz.utc.localize(datetime.combine(input_date, datetime.min.time()))


def hours_from_datetimes(
    start: datetime, end: datetime, rounding: bool = False
) -> float:
    delta = end - start
    hours = delta.seconds // 3600
    minutes = (delta.seconds // 60) % 60
    if rounding:
        minutes = 15 * round(minutes / 15)

    return hours + (minutes / 60)


T = TypeVar("T")


def starstarmap(
    function: Callable[..., T], iterable: Iterable[Mapping[str, Any]]
) -> Iterator[T]:
    for args in iterable:
        yield function(**args)


class TraggoTimeSpan(BaseModel):
    id: int
    note: str
    tags: list[dict]

    start: datetime
    end: datetime


class TraggoConnector:
    def __init__(self, url: AnyHttpUrl, api_token: str, user_id: int | None = None):
        self._url = url
        self._api_token = api_token

        # Construct Client
        headers = {"Authorization": f"traggo {api_token}"}
        if user_id is not None:
            headers["X-Traggo-Impersonate"] = str(user_id)
        self.traggo = Client(
            transport=RequestsHTTPTransport(url=f"{url}graphql", headers=headers),
            fetch_schema_from_transport=True,
        )

    def impersonate(self, user_id: int) -> "TraggoConnector":
        # TODO: Assert that current user is admin
        return TraggoConnector(self._url, self._api_token, user_id)

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

    def _convert_timespan(self, timespan: TraggoTimeSpan) -> tuple[TimeEntry, float]:
        hours = hours_from_datetimes(timespan.start, timespan.end, rounding=True)
        hours_no_rounding = hours_from_datetimes(
            timespan.start, timespan.end, rounding=False
        )

        return (
            TimeEntry(
                id=timespan.id,
                hours=hours,
                date=timespan.start.date(),
                note=timespan.note,
                tags={item["key"]: item["value"] for item in timespan.tags},
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
            yield from starstarmap(TraggoTimeSpan, timespans)
            # Fetch more pages using cursor (if more are available)
            cursor = paged_timespans["cursor"]
            if not cursor.pop("hasMore"):
                return
            vars["cursor"] = cursor

    def get_time_entries(self, from_date: date, to_date: date) -> list[TimeEntry]:
        timespans = list(self._get_timespans(from_date, to_date))
        if not timespans:
            return []
        time_entries_iter, rounding_errors_iter = unzip(
            map(self._convert_timespan, timespans)
        )
        # Add rounding compensation
        rounding_errors: list[float] = cast(list[float], list(rounding_errors_iter))
        time_entries: list[TimeEntry] = cast(list[TimeEntry], list(time_entries_iter))
        time_entries[0].hours += math.ceil(sum(rounding_errors) * 4) / 4
        return cast(list[TimeEntry], time_entries)
