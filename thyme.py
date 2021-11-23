import datetime
from copy import copy
from operator import attrgetter
from typing import Iterable
from typing import Optional

import typer
from more_itertools import bucket
from tabulate import tabulate

from model import TimeEntry
from redmine import RedmineConnector
from traggo import TraggoConnector

REDMINE_URL = "https://redmine.magenta-aps.dk/"
TRAGGO_URL = "https://traggo.moesgaard.dev"


def _parse_dates(
    date: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
) -> tuple[datetime.date, datetime.date]:
    if from_date:
        parsed_from_date = datetime.date.fromisoformat(from_date)
        if to_date:
            parsed_to_date = datetime.date.fromisoformat(to_date)
        else:
            parsed_to_date = datetime.date.today()
        typer.echo(f"Using date range {parsed_from_date} -> {parsed_to_date}")
    elif date:
        parsed_from_date = parsed_to_date = datetime.date.fromisoformat(date)
        typer.echo(f"Using date {parsed_from_date}")
    else:
        parsed_from_date = parsed_to_date = datetime.date.today()
        typer.echo(f"No date supplied. Using date {parsed_from_date}")

    return parsed_from_date, parsed_to_date


def _print_table(entries: list[TimeEntry]):
    buckets = bucket(entries, key=lambda x: x.date)
    bucket_keys = sorted(list(buckets))

    for key in bucket_keys:
        bucket_entries = list(buckets[key])
        entry_dicts = [entry.dict() for entry in bucket_entries]

        summed_hours = sum(map(attrgetter("hours"), bucket_entries))
        entry_dicts.append({"description": "Total", "hours": summed_hours})

        typer.secho(f"Entries for {key}:", fg=typer.colors.BLUE, bold=True)
        typer.echo(tabulate(entry_dicts, headers="keys"))
        typer.echo()


def _consolidate_entries(entries: Iterable[TimeEntry]) -> Iterable[TimeEntry]:
    buckets = bucket(entries, key=lambda x: (x.issue, x.description, x.date))
    bucket_values = [list(buckets[k]) for k in buckets]

    def create_consolidated_entry(entries: list[TimeEntry]) -> TimeEntry:
        summed_hours = sum(map(attrgetter("hours"), entries))
        entry = copy(entries[0])
        entry.hours = summed_hours
        return entry

    consolidated = map(create_consolidated_entry, bucket_values)

    return consolidated


def main(
    redmine_api_key: str = typer.Argument(..., envvar="REDMINE_API_KEY"),
    traggo_api_key: str = typer.Argument(..., envvar="TRAGGO_API_KEY"),
    redmine_url: str = typer.Argument(REDMINE_URL, envvar="REDMINE_URL"),
    traggo_url: str = typer.Argument(TRAGGO_URL, envvar="TRAGGO_URL"),
    date: Optional[str] = typer.Option(None, help="A single date to fetch."),
    from_date: Optional[str] = typer.Option(
        None, help="The lower bound of a date range to fetch. Is overridden by --date."
    ),
    to_date: Optional[str] = typer.Option(
        None, help="The upper bound of a date range to sync. Defaults to todays date."
    ),
    show_table: Optional[bool] = typer.Option(
        False, help="Pretty-print found time entries in a table"
    ),
):
    """
    Fetches time entries from Traggo, and creates them in Redmine.

    By default, fetches time entries for todays date.

    Can optionally search for other dates, or date ranges.

    """
    parsed_from_date, parsed_to_date = _parse_dates(date, from_date, to_date)

    traggo = TraggoConnector(url=traggo_url, api_token=traggo_api_key)
    entries = traggo.get_time_entries(parsed_from_date, parsed_to_date)
    entries = list(_consolidate_entries(entries))

    typer.echo(f"Found {len(entries)} entries")
    typer.echo()
    if not entries:
        typer.secho("Nothing to do 🕺", fg=typer.colors.YELLOW)
        raise typer.Exit()

    if show_table:
        _print_table(entries)

    create = typer.confirm("Create time entries in Redmine?", default=True)
    if not create:
        raise typer.Abort()

    # Send entries to Redmine
    redmine = RedmineConnector(redmine_url, redmine_api_key)
    redmine.create_time_entries(entries)


if __name__ == "__main__":
    typer.run(main)
