from datetime import date
from datetime import datetime
from datetime import timedelta
from typing import Iterable

import pytz
import typer
from gql import Client
from gql import gql
from gql.transport.requests import RequestsHTTPTransport
from graphql.language.ast import Document
from more_itertools import one
from pydantic import BaseModel

from model import TimeEntry
from util import hours_from_datetimes


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

    def _convert_date_to_datetime(self, input_date: date) -> datetime:
        # TODO: Make timezone configurable
        return pytz.utc.localize(datetime.combine(input_date, datetime.min.time()))

    def _get_timespan_query(self, from_date: date, to_date: date) -> Document:
        from_datetime = self._convert_date_to_datetime(from_date)
        to_datetime = self._convert_date_to_datetime(to_date) + timedelta(days=1)

        query = f"""
            {{
                timeSpans(
                    fromInclusive: "{from_datetime.isoformat()}",
                    toInclusive: "{to_datetime.isoformat()}"
                ) {{
                    timeSpans {{
                        note,
                        start,
                        end,
                        tags {{
                            key,
                            value
                        }}
                    }}
                }}
            }}
        """
        return gql(query)

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
        result = self.traggo.execute(self._get_timespan_query(from_date, to_date))
        timespans = result.get("timeSpans").get("timeSpans")
        return map(lambda x: TraggoTimeSpan.parse_from_dict(**x), timespans)

    def get_time_entries(self, from_date: date, to_date: date) -> Iterable[TimeEntry]:
        typer.secho("Reading timespans from Traggo 🦫⏱️")
        timespans = self._get_timespans(from_date, to_date)
        return map(self._convert_timespan, timespans)
