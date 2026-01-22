from fastapi import FastAPI, Response, status, HTTPException, APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from typing import List
from .. import models, schema, utils

from ..schema import UserCreate, UserResponse 
from ..database import get_db

router = APIRouter(
    prefix = '/users',
    tags = ['Users']
)

@router.post("/", status_code = status.HTTP_201_CREATED, response_model = UserResponse)
def create_user(user_input: UserCreate, db: Session = Depends(get_db)):
    
    # hash the password
    hashed_password = utils.hash(user_input.password)
    user_input.password = hashed_password
    
    new_user = models.User(**user_input.model_dump())
    
    db.add(new_user)
    try:
        db.commit() 
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code = status.HTTP_409_CONFLICT, 
                            detail = f"Username ({new_user.username}) taken")
    db.refresh(new_user)

    return new_user

@router.get("/{id}", response_model = UserResponse)
def get_user(id: int, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == id).first()

    if not user:
        raise HTTPException(status_code = status.HTTP_404_NOT_FOUND,
                            detail = f'User with id {id} does not exist')
    
    return user

