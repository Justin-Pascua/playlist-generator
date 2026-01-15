from fastapi import FastAPI, Response, status, HTTPException, APIRouter
from .. import models, schema, utils

from typing import List
from ..schema import UserCreate, UserResponse 
from sqlalchemy.orm import Session
from fastapi import Depends
from ..database import get_db

router = APIRouter(
    prefix = '/users',
    tags = ['Users']
)

# to do: check if username is already taken
@router.post("/", status_code = status.HTTP_201_CREATED, response_model = UserResponse)
def create_user(user_input: UserCreate, db: Session = Depends(get_db)):
    
    # hash the password
    hashed_password = utils.hash(user_input.password)
    user_input.password = hashed_password
    
    new_user = models.User(**user_input.model_dump())
    
    db.add(new_user)
    db.commit() # error here if username already taken
    db.refresh(new_user)

    return new_user

@router.get("/{id}", response_model = UserResponse)
def get_user(id: int, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == id).first()

    if not user:
        raise HTTPException(status_code = status.HTTP_404_NOT_FOUND,
                            detail = f'User with id {id} does not exist')
    
    return user

