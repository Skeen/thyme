# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
from collections.abc import Callable
from collections.abc import Iterator
from typing import TypeVar
from unittest.mock import AsyncMock
from unittest.mock import call
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from thyme.app import seeded_synchronize_entries
from thyme.app import traggo


def test_root(client: TestClient) -> None:
    """Test the root endpoint.

    Args:
        client: App-bound test-client.
    """
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"name": "thyme"}


def test_liveness(client: TestClient) -> None:
    """Test the Kubernetes liveness endpoint.

    Args:
        client: App-bound test-client.
    """
    response = client.get("/health/live")
    assert response.status_code == 204


def test_readiness(client: TestClient) -> None:
    """Test the Kubernetes readiness endpoint.

    Args:
        client: App-bound test-client.
    """
    response = client.get("/health/ready")
    assert response.status_code == 204


T = TypeVar("T")


def yielder(value: T) -> Callable[[], Iterator[T]]:
    """Helper function to yield the given value.

    Args:
        value: The value to be yielded by the returned function.

    Returns:
        A function which yields 'value' when called.
    """

    def wrapper() -> Iterator[T]:
        yield value

    return wrapper


@pytest.mark.parametrize(
    "usermap",
    [
        # No users
        {},
        # Admin user
        {1: {"admin": True, "name": "admin"}},
        # Ordinary user
        {2: {"admin": False, "name": "emil"}},
        # Multiple users
        {
            1: {"admin": True, "name": "admin"},
            2: {"admin": False, "name": "emil"},
            3: {"admin": False, "name": "john"},
        },
    ],
)
def test_sync(
    app: FastAPI,
    client: TestClient,
    usermap: dict[int, dict],
) -> None:
    """Test the synchronize all endpoint calls sync_entries.

    Args:
        app: The FastAPI app under test.
        client: App-bound test-client.
        usermap: Traggo user-map.
    """
    traggo_mock = MagicMock()
    traggo_mock.get_all_users.return_value = usermap
    app.dependency_overrides[traggo] = yielder(traggo_mock)

    sync_entries = AsyncMock()
    sync_entries.side_effect = ValueError()
    app.dependency_overrides[seeded_synchronize_entries] = lambda: sync_entries

    response = client.post("/sync/")
    assert response.status_code == 200
    assert response.json() == {str(user_id): False for user_id in usermap.keys()}

    traggo_mock.get_all_users.assert_called_once_with()
    sync_entries.assert_has_calls(
        [call(None, None, user_id) for user_id in usermap.keys()]
    )


def test_sync_user(app: FastAPI, client: TestClient) -> None:
    """Test the synchronize single user endpoint calls sync_entries.

    Args:
        app: The FastAPI app under test.
        client: App-bound test-client.
    """
    result = {
        "entries": 1 + 2 + 3,
        "updated": 3,
        "created": 2,
        "up_to_date": 1,
    }
    sync_entries = AsyncMock()
    sync_entries.return_value = result
    app.dependency_overrides[seeded_synchronize_entries] = lambda: sync_entries

    response = client.post("/sync/42")
    assert response.status_code == 200
    assert response.json() == result

    sync_entries.assert_called_once_with(None, None, 42)
