from typing import Iterable

import typer
from redminelib import Redmine

from model import TimeEntry


class RedmineConnector:
    def __init__(self, url: str, api_key: str):
        self.redmine = Redmine(url=url, key=api_key)

    def create_time_entries(self, time_entries: Iterable[TimeEntry]):
        typer.secho("Creating time entries in Redmine ⛰️🔴⛏️")
        for entry in time_entries:
            self.redmine.time_entry.create(
                issue_id=entry.issue,
                spent_on=entry.date,
                hours=entry.hours,
                comments=entry.description,
            )
