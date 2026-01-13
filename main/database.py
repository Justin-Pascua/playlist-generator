from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from urllib.parse import quote_plus
from .config import settings

DB_PASSWORD_ENCODED = quote_plus(settings.MYSQL_PASSWORD)   # url encoding
DB_URL = f"{settings.MYSQL_PROTOCOL}://{settings.MYSQL_USER}:{DB_PASSWORD_ENCODED}@{settings.MYSQL_HOST}:{settings.MYSQL_PORT}/{settings.DB_NAME}"
engine = create_engine(DB_URL, echo = True)

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