# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
from asyncio import gather
from collections.abc import Awaitable
from collections.abc import Callable
from collections.abc import Generator
from datetime import date
from functools import partial
from typing import Any
from typing import cast

from fastapi import Depends
from fastapi import FastAPI
from fastapi import HTTPException
from fastapi import Request
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.engine.base import Engine
from starlette.status import HTTP_204_NO_CONTENT

from .config import Settings
from .redmine import Base
from .redmine import RedmineConnector
from .traggo import TraggoConnector


async def synchronize_entries(
    admin_traggo: TraggoConnector,
    admin_redmine: RedmineConnector,
    engine: Engine,
    from_date: date | None,
    to_date: date | None,
    user_id: int,
) -> dict[str, int]:
    if to_date and not from_date:
        from_date = to_date
    from_date = from_date or date.today()
    to_date = to_date or date.today()

    traggo = admin_traggo.impersonate(user_id)
    user_object = traggo.get_current_user()
    if user_object is None:
        raise HTTPException(
            status_code=404, detail="Provided user_id not found in Traggo"
        )
    if user_object["admin"]:
        raise HTTPException(
            status_code=403, detail="Refusing to synchronize Traggo admin user"
        )

    # Read entries from Traggo
    try:
        entries = list(traggo.get_time_entries(from_date, to_date))
    except ValidationError as exception:
        raise HTTPException(status_code=422, detail=str(exception))

    username = user_object["name"]
    if not admin_redmine.check_if_user_exists(username):
        raise HTTPException(
            status_code=404, detail="Provided user not found in Redmine"
        )

    # Send entries to Redmine
    redmine = admin_redmine.impersonate(username)
    updated, created, up_to_date, missing_issue = redmine.create_time_entries(
        engine, entries
    )

    return {
        "entries": len(entries),
        "updated": updated,
        "created": created,
        "up_to_date": up_to_date,
        "missing_issue": missing_issue,
    }


def extract_context(request: Request) -> dict[str, Any]:
    """Extract the request context from a request object.

    Args:
        request: The request object to extract the context from.

    Returns:
        The extracted context object.
    """
    return cast(dict[str, Any], request.app.state.context)


def extract_settings(context: dict[str, Any] = Depends(extract_context)) -> Settings:
    """Extract the settings object from the request context.

    Args:
        context: The request context to extract the settings from.

    Returns:
        The extracted settings object.
    """
    return cast(Settings, context["settings"])


def engine(
    settings: Settings = Depends(extract_settings),
) -> Generator[Engine, None, None]:
    engine = create_engine(settings.database_url)
    Base.metadata.create_all(engine)
    yield engine


def traggo(
    settings: Settings = Depends(extract_settings),
) -> Generator[TraggoConnector, None, None]:
    traggo = TraggoConnector(
        settings.traggo_url, settings.traggo_api_key.get_secret_value()
    )
    yield traggo


def redmine(
    settings: Settings = Depends(extract_settings),
) -> Generator[RedmineConnector, None, None]:
    redmine = RedmineConnector(
        settings.redmine_url, settings.redmine_api_key.get_secret_value()
    )
    yield redmine


def seeded_synchronize_entries(
    admin_traggo: TraggoConnector = Depends(traggo),
    admin_redmine: RedmineConnector = Depends(redmine),
    engine: Engine = Depends(engine),
) -> Callable[[date | None, date | None, int], Awaitable[dict[str, int]]]:
    return partial(synchronize_entries, admin_traggo, admin_redmine, engine)


def create_app() -> FastAPI:
    """Create a Thyme app.

    Returns:
        The newly constructed FastAPI app.
    """
    settings = Settings()

    context = {
        "name": "thyme",
        "settings": settings,
    }
    app = FastAPI(
        title=cast(str, context["name"]),
        contact={
            "name": "Magenta Aps",
            "url": "https://www.magenta.dk/",
            "email": "info@magenta.dk>",
        },
        license_info={
            "name": "MPL-2.0",
            "url": "https://www.mozilla.org/en-US/MPL/2.0/",
        },
        dependencies=[Depends(engine), Depends(traggo), Depends(redmine)],
    )
    app.state.context = context

    @app.get("/")
    async def index(request: Request) -> dict[str, str]:
        context: dict[str, Any] = request.app.state.context
        return {"name": context["name"]}

    @app.get("/health/live", status_code=HTTP_204_NO_CONTENT)
    async def liveness() -> None:
        """Endpoint to be used as a liveness probe for Kubernetes.

        Returns:
            None
        """
        return None

    @app.get("/health/ready", status_code=HTTP_204_NO_CONTENT)
    async def readiness() -> None:
        """Endpoint to be used as a readiness probe for Kubernetes.

        Returns:
            None
        """
        return None

    @app.post("/sync/")
    async def sync(
        from_date: date | None = None,
        to_date: date | None = None,
        admin_traggo: TraggoConnector = Depends(traggo),
        sync_entries: Callable[
            [date | None, date | None, int], Awaitable[dict[str, int]]
        ] = Depends(seeded_synchronize_entries),
    ) -> dict[int, bool]:
        """Synchronize all Traggo users in the given internal.

        Args:
            from_date: Start of the synchronization interval.
            to_date: End of the synchronization interval.
            admin_traggo:
                Traggo Connection with administative privileges to fetch all users.
            sync_entries:
                Seeded sync_entries function, to be called with interval and user id.

        Returns:
            A dictionary mapping Traggo user ids to synchronization success.
        """
        users = admin_traggo.get_all_users()
        user_ids = list(users.keys())
        tasks = [sync_entries(from_date, to_date, user_id) for user_id in user_ids]
        results = await gather(*tasks, return_exceptions=True)
        return {
            user_id: not isinstance(result, Exception)
            for user_id, result in zip(user_ids, results)
        }

    @app.post("/sync/{user_id}")
    async def sync_user(
        user_id: int,
        from_date: date | None = None,
        to_date: date | None = None,
        sync_entries: Callable[
            [date | None, date | None, int], Awaitable[dict[str, int]]
        ] = Depends(seeded_synchronize_entries),
    ) -> dict[str, int]:
        """Synchronize the specified Traggo user in the given internal.

        Args:
            user_id: Traggo ID of the user to synchronize.
            from_date: Start of the synchronization interval.
            to_date: End of the synchronization interval.
            sync_entries:
                Seeded sync_entries function, to be called with interval and user id.

        Returns:
            A dictionary detailing synchronization results.
            Stating how many entries were found, updated, crated and already up-to-date.
        """
        return await sync_entries(from_date, to_date, user_id)

    return app
