from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import SecretStr

class Settings(BaseSettings):
    DISCORD_TOKEN: SecretStr
    DISCORD_DEV_SERVER_ID: SecretStr
    YT_API_KEY: SecretStr

    model_config = SettingsConfigDict(env_file = '.env.dev', env_file_encoding = 'utf-8',
                                      extra = 'ignore')

settings = Settings()

