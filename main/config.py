from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    HF_TOKEN: str

    YT_API_KEY: str
    
    MYSQL_PROTOCOL: str
    MYSQL_HOST: str
    MYSQL_USER: str
    MYSQL_PORT: int
    MYSQL_PASSWORD: str
    MYSQL_DB_NAME: str

    GOOGLE_TOKEN: str
    GOOGLE_REFRESH_TOKEN: str
    GOOGLE_TOKEN_URI: str
    GOOGLE_CLIENT_ID: str
    GOOGLE_CLIENT_SECRET: str

    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int

    model_config = SettingsConfigDict(env_file = '.env.dev', env_file_encoding = 'utf-8')

settings = Settings()

