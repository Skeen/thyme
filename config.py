from functools import lru_cache

from pydantic import BaseSettings
from pydantic import AnyHttpUrl

class Settings(BaseSettings):
    redmine_url: AnyHttpUrl
    redmine_api_key: str
    traggo_url: AnyHttpUrl
    traggo_api_key: str

    class Config:
        env_file = '.env'
        env_file_encoding = 'utf-8'

@lru_cache()
def get_settings() -> Settings:
    return Settings()
