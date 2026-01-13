from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    HF_TOKEN: str
    
    MYSQL_PROTOCOL: str
    MYSQL_HOST: str
    MYSQL_USER: str
    MYSQL_PORT: int
    MYSQL_PASSWORD: str
    DB_NAME: str

    model_config = SettingsConfigDict(env_file = '.env', env_file_encoding = 'utf-8')

settings = Settings()

