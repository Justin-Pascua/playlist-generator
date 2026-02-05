from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import SecretStr

class Settings(BaseSettings):
    BASE_URL: str

    model_config = SettingsConfigDict(env_file = '.env.dev', env_file_encoding = 'utf-8',
                                      extra = 'ignore')

settings = Settings()

