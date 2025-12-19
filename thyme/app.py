# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
import asyncio
from datetime import date

from sqlalchemy import create_engine

from .config import Settings
from .redmine import Base
from .redmine import RedmineConnector
from .traggo import TraggoConnector


async def main() -> None:
    settings = Settings()

    engine = create_engine(settings.database_url)
    Base.metadata.create_all(engine)

    traggo = TraggoConnector(
        settings.traggo_url, settings.traggo_api_key.get_secret_value()
    )

    redmine = RedmineConnector(
        settings.redmine_url, settings.redmine_api_key.get_secret_value()
    )

    from_date = date.today()
    to_date = date.today()

    if traggo.is_admin():
        raise ValueError("Refusing to synchronize Traggo admin user")

    # Read entries from Traggo
    entries = list(traggo.get_time_entries(from_date, to_date))
    updated, created, up_to_date, missing_issue = redmine.create_time_entries(
        engine, entries
    )

    print(
        {
            "entries": len(entries),
            "updated": updated,
            "created": created,
            "up_to_date": up_to_date,
            "missing_issue": missing_issue,
        }
    )


def run() -> None:
    asyncio.run(main())


if __name__ == "__main__":
    run()
