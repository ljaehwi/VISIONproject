from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_ignore_empty=True)

    database_url: str = Field('postgresql+asyncpg://aca:aca@localhost:5432/aca', validation_alias='DATABASE_URL')
    static_dir: str = 'app/static'
    static_url: str = '/static'
    image_subdir: str = 'images'
    log_level: str = 'INFO'


settings = Settings()
