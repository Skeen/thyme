# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
from collections.abc import Iterable
from typing import Any

from pydantic import AnyHttpUrl
from redminelib import Redmine  # type: ignore
from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy.engine.base import Engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from .model import TimeEntry


Base = declarative_base()


class IDMapper(Base):
    __tablename__ = "idmapper"
    id = Column(Integer, primary_key=True)
    redmine_id = Column(Integer)
    traggo_id = Column(Integer)


class RedmineConnector:
    def __init__(self, url: AnyHttpUrl, api_token: str) -> None:
        self._url = url
        self._api_token = api_token

        self.redmine = Redmine(url=str(url), key=api_token)

    def create_time_entries(
        self, engine: Engine, time_entries: Iterable[TimeEntry]
    ) -> tuple[int, int, int, int]:
        traggo_entries = {entry.id: entry for entry in time_entries}

        Session = sessionmaker(bind=engine)
        session = Session()

        traggo_ids = set(traggo_entries.keys())

        existing_time_entries = (
            session.query(IDMapper).filter(IDMapper.traggo_id.in_(traggo_ids)).all()
        )
        mapper = {x.traggo_id: x.redmine_id for x in existing_time_entries}

        found_traggo_ids = set(mapper.keys())
        traggo_ids_to_update = traggo_ids.intersection(found_traggo_ids)
        traggo_ids_to_insert = traggo_ids.difference(found_traggo_ids)

        updated = 0
        up_to_date = 0
        missing_issue = 0

        for traggo_id in traggo_ids_to_update:
            entry = traggo_entries[traggo_id]
            print("Updating", entry)

            issue = entry.get_issue()
            if issue is None:
                missing_issue += 1
                print("Missing issue on entry", entry.date, entry.note)
                continue

            redmine_id = mapper[traggo_id]
            redmine_entry = self.redmine.time_entry.get(redmine_id)

            update_fields: dict[str, Any] = {}
            if issue != int(redmine_entry.issue):
                update_fields["issue_id"] = issue
            if entry.date != redmine_entry.spent_on:
                update_fields["spent_on"] = entry.date
            if entry.hours != redmine_entry.hours:
                update_fields["hours"] = entry.hours
            if entry.note != redmine_entry.comments:
                update_fields["comments"] = entry.note

            if not update_fields:
                up_to_date += 1
                print("No need for update!")
                continue

            print(update_fields)
            self.redmine.time_entry.update(redmine_id, **update_fields)
            updated += 1
            print("Updated!")

        created = 0
        for traggo_id in traggo_ids_to_insert:
            entry = traggo_entries[traggo_id]
            print("Inserting", entry)

            issue = entry.get_issue()
            if issue is None:
                missing_issue += 1
                print("Missing issue on entry", entry.date, entry.note)
                continue

            resource = self.redmine.time_entry.create(
                issue_id=int(issue),
                spent_on=entry.date,
                hours=entry.hours,
                comments=entry.note,
            )
            mapping = IDMapper(redmine_id=resource.id, traggo_id=entry.id)
            session.add(mapping)
            session.commit()
            created += 1

        return updated, created, up_to_date, missing_issue
