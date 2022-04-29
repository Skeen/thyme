# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
from datetime import date
from datetime import datetime
from datetime import timedelta
from typing import Any

from gql import gql

from .util import convert_date_to_datetime


Document = Any


def get_timespan_query(from_date: date, to_date: date) -> Document:
    from_datetime = convert_date_to_datetime(from_date)
    to_datetime = convert_date_to_datetime(to_date) + timedelta(days=1)

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


def get_timers_query() -> Document:
    document = """
        query Trackers {
            timers {
                id,
                note,
                start,
                tags {
                    key,
                    value
                }
            }
        }
    """
    return gql(document)


def start_timer_mutation(
    start_time: datetime,
    issue: str | None = None,
    type: str | None = None,
    note: str | None = "",
) -> tuple[Document, dict]:
    tags = []
    if issue:
        tags.append({"key": "issue", "value": issue})
    if type:
        tags.append({"key": "type", "value": type})

    document = """
        mutation StartTimer($start: Time!, $tags: [InputTimeSpanTag!], $note: String!) {
            createTimeSpan(start: $start, tags: $tags, note: $note) {
                id
            }
        }
    """
    variables = {
        "start": start_time.isoformat(),
        "note": note,
        "tags": tags,
    }
    return gql(document), variables


def stop_timer_mutation(timer_id: str, end_time: datetime) -> tuple[Document, dict]:
    document = """
        mutation StopTimer($id: Int!, $end: Time!) {
            stopTimeSpan(id: $id, end: $end) {
                id,
                end
            }
        }
    """
    variables = {
        "id": timer_id,
        "end": end_time.isoformat(),
    }
    return gql(document), variables


def update_timer_mutation() -> Document:
    document = """
        mutation UpdateTimer(
            $id: Int!, $start: Time!, $tags: [InputTimeSpanTag!], $note: String!
        ) {
            updateTimeSpan(id: $id, start: $start, tags: $tags, note: $note) {
                id,
                note,
                start,
                tags {
                    key,
                    value
                }
            }
        }
    """
    return gql(document)
