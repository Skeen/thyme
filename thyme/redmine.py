# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
from collections.abc import Iterable
from typing import Any

from redminelib import Redmine
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
    def __init__(self, url: str, api_token: str, username: str | None = None):
        self._url = url
        self._api_token = api_token

        self.redmine = Redmine(url=url, key=api_token, impersonate=username)

    def as_user(self, username: str) -> "RedmineConnector":
        return RedmineConnector(self._url, self._api_token, username)

    def check_if_user_exists(self, username: str) -> bool:
        users = self.redmine.user.filter(name=username)
        users = list(filter(lambda user: user.login == username, users))
        return len(users) == 1

    def create_time_entries(
        self, engine: Engine, time_entries: Iterable[TimeEntry]
    ) -> tuple[int, int, int]:
        traggo_entries = {entry.id: entry for entry in time_entries}

        Session = sessionmaker(bind=engine)
        session = Session()

        traggo_ids_to_insert = set(traggo_entries.keys())
        existing_time_entries = (
            session.query(IDMapper)
            .filter(IDMapper.traggo_id.in_(traggo_ids_to_insert))
            .all()
        )

        mapper = {x.traggo_id: x.redmine_id for x in existing_time_entries}

        redmine_ids = [x.redmine_id for x in existing_time_entries]
        redmine_entries = {
            redmine_id: self.redmine.time_entry.get(redmine_id)
            for redmine_id in redmine_ids
        }
        updated = 0
        created = 0
        up_to_date = 0

        for traggo_id, entry in traggo_entries.items():
            if traggo_id in mapper:
                # UPDATE
                print(f"Updating {entry}")
                redmine_id = mapper[traggo_id]
                redmine_entry = redmine_entries[redmine_id]

                update_fields: dict[str, Any] = {}
                if entry.issue != int(redmine_entry.issue):
                    update_fields["issue_id"] = entry.issue
                if entry.date != redmine_entry.spent_on:
                    update_fields["spent_on"] = entry.date
                if entry.hours != redmine_entry.hours:
                    update_fields["hours"] = entry.hours
                if entry.description != redmine_entry.comments:
                    update_fields["comments"] = entry.description

                if not update_fields:
                    up_to_date += 1
                    print("No need for update!")
                    continue

                print(update_fields)
                self.redmine.time_entry.update(redmine_id, **update_fields)
                updated += 1
                print("Updated!")
            else:
                # INSERT
                print(f"Inserting {entry}")
                resource = self.redmine.time_entry.create(
                    issue_id=entry.issue,
                    spent_on=entry.date,
                    hours=entry.hours,
                    comments=entry.description,
                )
                mapping = IDMapper(redmine_id=resource.id, traggo_id=entry.id)
                session.add(mapping)
                created += 1
        session.commit()
        return updated, created, up_to_date
