from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import SecretStr

class Settings(BaseSettings):
    YT_API_KEY: SecretStr
    
    MYSQL_PROTOCOL: SecretStr
    MYSQL_HOST: SecretStr
    MYSQL_USER: SecretStr
    MYSQL_PORT: int
    MYSQL_PASSWORD: SecretStr
    MYSQL_DB_NAME: SecretStr

    GOOGLE_TOKEN: SecretStr
    GOOGLE_REFRESH_TOKEN: SecretStr
    GOOGLE_TOKEN_URI: SecretStr
    GOOGLE_CLIENT_ID: SecretStr
    GOOGLE_CLIENT_SECRET: SecretStr

    SECRET_KEY: SecretStr
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int

    model_config = SettingsConfigDict(env_file = '.env.dev', env_file_encoding = 'utf-8',
                                      extra = 'ignore')

settings = Settings()

