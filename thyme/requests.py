# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
from datetime import datetime
from typing import Any

from gql import gql

Document = Any


def get_timespan_query() -> Document:
    query = """
        query FetchTimespans(
            $cursor: InputCursor, $from: Time, $to: Time
        ) {
            timeSpans(
                fromInclusive: $from, toInclusive: $to, cursor: $cursor
            ) {
                timeSpans {
                    id
                    note
                    start
                    end
                    tags {
                        key
                        value
                    }
                }
                cursor {
                  hasMore
                  startId
                  offset
                  pageSize
                }
            }
        }
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
