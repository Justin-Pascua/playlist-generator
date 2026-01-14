import jwt
from jwt import PyJWTError
import datetime
from datetime import timedelta
from . import schema, database, models
from fastapi import Depends, status, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from .config import settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl = 'login')

SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES

def create_access_token(data: dict):
    # copy input dictionary so that input is not modified
    to_encode = data.copy()
    
    # get time x mins from now
    expire = datetime.datetime.now(datetime.UTC) + timedelta(minutes = ACCESS_TOKEN_EXPIRE_MINUTES)

    # add expiration field to dict
    to_encode.update({'exp': expire})

    # generate jwt
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm = ALGORITHM)

    return encoded_jwt

def verify_access_token(token: str, credentials_exception):
    try:
        # get payload from user's token
        payload = jwt.decode(token, SECRET_KEY, algorithms = [ALGORITHM])
        
        # get values stored in payload. In our case, it's just one value 
        id: str = payload.get('user_id')
        if id is None:
            raise credentials_exception
        
        # check that payload matches schema
        token_data = schema.TokenData(id = id)

    except PyJWTError:
        raise credentials_exception
    
    return token_data

def get_current_user(token: str = Depends(oauth2_scheme),
                     db: Session = Depends(database.get_db)):
    credentials_exception = HTTPException(status_code = status.HTTP_401_UNAUTHORIZED,
                                          detail = f'Could not validate credentials',
                                          headers = {'WWW-Authenticate': 'Bearer'})
    
    token_data = verify_access_token(token, credentials_exception)

    user = db.query(models.User).filter(models.User.id == token_data.id).first()

    return user

