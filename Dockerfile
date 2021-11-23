# -----------------------------------------------------------------
# SPDX-FileCopyrightText: 2021 Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
# -----------------------------------------------------------------

FROM python:3.9-slim

ENV PIP_DISABLE_PIP_VERSION_CHECK=on \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/code \
    POETRY_VERSION="1.1.6" \
    POETRY_VIRTUALENVS_CREATE=true \
    POETRY_VIRTUALENVS_IN_PROJECT=true

RUN pip install --no-cache-dir poetry==${POETRY_VERSION}
WORKDIR /code
COPY poetry.lock pyproject.toml /code/

RUN poetry install --no-dev --no-interaction 

COPY . /code

ENTRYPOINT [ "poetry", "run", "python", "thyme.py" ]
