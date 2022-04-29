# SPDX-FileCopyrightText: Magenta ApS
#
# SPDX-License-Identifier: MPL-2.0
"""Pytest fixtures."""
from collections.abc import AsyncGenerator
from collections.abc import Generator
from typing import TypeVar

import pytest
from _pytest.monkeypatch import MonkeyPatch
from fastapi import FastAPI
from fastapi.testclient import TestClient

from thyme.app import create_app


T = TypeVar("T")
YieldFixture = Generator[T, None, None]
AsyncYieldFixture = AsyncGenerator[T, None]


@pytest.fixture(scope="session")
def monkeysession() -> YieldFixture[MonkeyPatch]:
    with pytest.MonkeyPatch.context() as mp:
        yield mp


@pytest.fixture(autouse=True, scope="session")
def seed_default_metrics(monkeysession: MonkeyPatch) -> YieldFixture[None]:
    """Seed necessary default metrics to create an app.

    Args:
        monkeysession: pytest monkeypatcher to configure environment.

    Yields:
        None
    """
    monkeysession.setenv("DATABASE__URL", "sqlite:///:memory:")
    monkeysession.setenv("REDMINE_API_KEY", "FAKE_API_KEY")
    monkeysession.setenv("TRAGGO_API_KEY", "FAKE_API_KEY")
    yield


@pytest.fixture(scope="session")
def app() -> FastAPI:
    return create_app()


@pytest.fixture(scope="session")
def client(app: FastAPI) -> TestClient:
    return TestClient(app)
