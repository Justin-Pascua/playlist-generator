from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from urllib.parse import quote_plus
from .config import settings

DB_USER = settings.MYSQL_USER.get_secret_value()
DB_PASSWORD_ENCODED = quote_plus(settings.MYSQL_PASSWORD.get_secret_value()).replace('%', '%%')   # url encoding
DB_HOST = settings.MYSQL_HOST.get_secret_value()
DB_PORT = settings.MYSQL_PORT
DB_NAME = settings.MYSQL_DB_NAME.get_secret_value()

DB_URL = f"mysql+mysqlconnector://{DB_USER}:{DB_PASSWORD_ENCODED}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

engine = create_engine(
    DB_URL,
    pool_pre_ping = True,
    pool_recycle = 1800,
)

Session = sessionmaker(
    autocommit = False, 
    autoflush = False, 
    bind = engine)

Base = declarative_base()

def get_db():
    db = Session()
    try:
        yield db
    finally:
        db.close()