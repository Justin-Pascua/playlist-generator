from fastapi import APIRouter, Depends, status, HTTPException, Response
from fastapi.security.oauth2 import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from ..database import get_db
from ..schema import UserLogin, Token
from .. import auth_utils, models

router = APIRouter(
    prefix = '/authentication',
    tags = ['Authentication']
)

@router.post('/', response_model = Token)
def login(user_credentials: OAuth2PasswordRequestForm = Depends(), 
          db: Session = Depends(get_db)):
    """
    Login and generate JWT token
    """
    user = db.query(models.User).filter(
        models.User.username == user_credentials.username).first()

    if not user:
        raise HTTPException(status_code = status.HTTP_403_FORBIDDEN,
                            detail = f'Invalid Credentials')
    
    if not auth_utils.verify_password(user_credentials.password, user.password):
        raise HTTPException(status_code = status.HTTP_403_FORBIDDEN,
                            detail = 'Invalid Credentials')
    
    access_token = auth_utils.create_access_token(data = {'user_id': user.id})

    return {'access_token': access_token,
            'token_type': 'bearer'}

@router.get('/')
def auth_ping(current_user = Depends(auth_utils.get_current_user)):
    """
    Check that current user is valid
    """
    return {"detail": "success"}
    