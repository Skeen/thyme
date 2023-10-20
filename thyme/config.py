# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
from pydantic import AnyHttpUrl
from pydantic import parse_obj_as
from pydantic import SecretStr
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    redmine_url: AnyHttpUrl = parse_obj_as(AnyHttpUrl, "https://redmine.magenta.dk")
    redmine_api_key: SecretStr

    traggo_url: AnyHttpUrl = parse_obj_as(AnyHttpUrl, "https://traggo.magentahosted.dk")
    traggo_api_key: SecretStr

    database_url: str = "sqlite:///thyme.db"
