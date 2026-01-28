from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from urllib.parse import quote_plus
from .config import settings

DB_PASSWORD_ENCODED = quote_plus(settings.MYSQL_PASSWORD)   # url encoding
DB_URL = f"{settings.MYSQL_PROTOCOL}://{settings.MYSQL_USER}:{DB_PASSWORD_ENCODED}@{settings.MYSQL_HOST}:{settings.MYSQL_PORT}/{settings.MYSQL_DB_NAME}"
engine = create_engine(DB_URL)

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