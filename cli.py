# SPDX-FileCopyrightText: Magenta ApS
# SPDX-License-Identifier: MPL-2.0
import datetime

import typer
from more_itertools.more import first

from thyme.app import Settings
from thyme.traggo import TraggoConnector
from thyme.util import parse_timestamp


app = typer.Typer()


@app.command()
def start(
    start_time: str = typer.Option(
        datetime.datetime.now().time().strftime("%H:%M"), prompt="Start time"
    ),
    issue: str = typer.Option("", prompt="Redmine ID"),
    type: str = typer.Option("", prompt="Type"),
    note: str = typer.Option("", prompt="Description"),
) -> None:
    """Starts a new timer.

    Args:
        start_time: The start-time of the new interval.
        issue: The issue number of the related redmine ticket.
        type: ???
        note: The note to attach to the new interval.
    """
    settings = Settings()
    traggo = TraggoConnector(
        url=settings.traggo_url, api_token=settings.traggo_api_key.get_secret_value()
    )

    parsed_start_time = parse_timestamp(start_time)
    traggo.start_timer(parsed_start_time, issue, type, note)

    typer.echo("")
    typer.echo("Timer started! 🚀")


@app.command()
def stop(
    stop_time: str = typer.Option(
        datetime.datetime.now().time().strftime("%H:%M"), prompt="Stop time"
    ),
) -> None:
    """Stops the currently running timer.

    Note:
        If more than one timer is running for whatever reason, the first one found
        will be stopped

    Args:
        stop_time: The stop-time of the interval.
    """
    settings = Settings()
    traggo = TraggoConnector(
        url=settings.traggo_url, api_token=settings.traggo_api_key.get_secret_value()
    )

    parsed_stop_time = parse_timestamp(stop_time)

    timers = traggo.get_timers()
    if not timers:
        typer.echo("No timer running")
        return
    timer = first(timers)

    traggo.stop_timer(timer, parsed_stop_time)

    typer.echo("")
    typer.echo("Timer stopped")


@app.command()
def edit() -> None:
    """Edits the currently running timer."""
    settings = Settings()
    traggo = TraggoConnector(
        url=settings.traggo_url, api_token=settings.traggo_api_key.get_secret_value()
    )
    timers = traggo.get_timers()
    if not timers:
        typer.echo("No timer running")
        return
    timer = first(timers)

    start = typer.prompt("Start time", default=timer.start.time().strftime("%H:%M"))
    timer.start = parse_timestamp(start)
    timer.issue = typer.prompt("Issue", default=timer.issue or "")
    timer.note = typer.prompt("Description", default=timer.note or "")
    timer.type = typer.prompt("Type", default=timer.type or "")

    traggo.update_timer(timer)

    typer.echo("")
    typer.echo("Timer updated")


@app.command()
def status() -> None:
    """Shows the status of the currently running timer."""
    typer.echo("Not yet implemented, lol 🤷")


if __name__ == "__main__":
    app()
