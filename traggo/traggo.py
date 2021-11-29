from datetime import date
from datetime import datetime
from typing import Iterable, Optional

import typer
from gql import Client
from gql.transport.requests import RequestsHTTPTransport
from more_itertools import one
from pydantic import BaseModel
import pytz

from model import TimeEntry
from util import hours_from_datetimes
from traggo.requests import get_timespan_query
from traggo.requests import start_timer_mutation
from traggo.requests import stop_timer_mutation
from traggo.requests import get_timers_query


class TraggoTimeSpan(BaseModel):
    note: str
    start: datetime
    end: datetime
    issue: int

    @classmethod
    def parse_from_dict(cls, note, start, end, tags):
        try:
            issue = one(filter(lambda x: x["key"] == "issue", tags))["value"]
        except ValueError:
            typer.secho(
                f"Missing issue on '{note}', {start}, {end}", fg=typer.colors.RED
            )
            raise typer.Exit()

        return cls(note=note, start=start, end=end, issue=issue)


class TraggoConnector:
    def __init__(self, url: str, api_token: str):
        self.traggo = self._get_client(url, api_token)

    def _get_client(self, url: str, api_token: str) -> Client:
        url = f"{url}/graphql"
        headers = {"Authorization": f"traggo {api_token}"}

        transport = RequestsHTTPTransport(url=url, headers=headers)
        return Client(transport=transport, fetch_schema_from_transport=True)

    def _convert_timespan(self, timespan: TraggoTimeSpan) -> TimeEntry:
        hours = hours_from_datetimes(timespan.start, timespan.end, rounding=True)

        return TimeEntry(
            issue=timespan.issue,
            description=timespan.note,
            hours=hours,
            date=timespan.start,
        )

    def _get_timespans(
        self, from_date: date, to_date: date
    ) -> Iterable[TraggoTimeSpan]:
        result = self.traggo.execute(get_timespan_query(from_date, to_date))
        timespans = result.get("timeSpans").get("timeSpans")
        return map(lambda x: TraggoTimeSpan.parse_from_dict(**x), timespans)

    def get_time_entries(self, from_date: date, to_date: date) -> Iterable[TimeEntry]:
        typer.secho("Reading timespans from Traggo 🦫⏱️")
        timespans = self._get_timespans(from_date, to_date)
        return map(self._convert_timespan, timespans)

    def start_timer(self, start_time: datetime, issue, type, note):
        document, vars = start_timer_mutation(start_time, issue=issue, type=type, note=note)
        self.traggo.execute(document, variable_values=vars)

    def stop_timer(self, stop_time):
        timers = self.traggo.execute(get_timers_query()).get("timers")
        if not timers:
            return

        timer_id = timers[0].get("id")

        document, vars = stop_timer_mutation(timer_id, stop_time)
        self.traggo.execute(document, variable_values=vars)
