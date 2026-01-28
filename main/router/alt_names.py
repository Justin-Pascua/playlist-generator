from fastapi import FastAPI, Response, status, HTTPException, Depends, APIRouter

from sqlalchemy import select, func
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from typing import List, Optional

from ..database import get_db
from ..schema import AltNameCreate, AltNameResponse, AltNameUpdate
from ..models import Canonical, AltName
from .. import auth_utils

router = APIRouter(
    prefix = "/alt-names",
    tags = ['Alternate Names']
)

# ALT NAMES
@router.post("/", response_model = AltNameResponse, status_code = status.HTTP_201_CREATED)
async def create_alt_name(new_alt: AltNameCreate, 
                          db: Session = Depends(get_db),
                          current_user = Depends(auth_utils.get_current_user)):
    """
    Create an alt name 
    """
    canonical = db.scalar(select(Canonical)
                          .where(Canonical.id == new_alt.canonical_id))

    if not canonical:
        raise HTTPException(status_code = status.HTTP_400_BAD_REQUEST,
                            detail = "Canonical id must point to an existing song")

    if canonical.user_id != current_user.id:
        raise HTTPException(status_code = status.HTTP_403_FORBIDDEN,
                            detail="You do not have access to the resource specified by this canonical id")
    
    created_alt = AltName(
        user_id = current_user.id, 
        **new_alt.model_dump())
    db.add(created_alt)
    
    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(status_code = status.HTTP_409_CONFLICT, 
                            detail = "Alt name already exists")

    db.refresh(created_alt)
    
    return created_alt

@router.get("/", response_model = List[AltNameResponse])
async def get_all_alt_names(canonical_id: int = None, 
                            db: Session = Depends(get_db),
                            current_user = Depends(auth_utils.get_current_user)):
    """
    Get all alt names 
    """
    stmt = select(AltName).where(AltName.user_id == current_user.id)
    if canonical_id:
        stmt = stmt.where(AltName.canonical_id == canonical_id)
    
    # .all() needed for if-statement
    result = db.execute(stmt).scalars().all()

    if not result:
        raise HTTPException(status_code = status.HTTP_404_NOT_FOUND,
                            detail = f"No alt names found")
    
    return result

@router.get("/{id}", response_model = AltNameResponse)
async def get_alt_name(id: int,
                       db: Session = Depends(get_db),
                       current_user = Depends(auth_utils.get_current_user)):
    """
    Get a specified alt name
    """

    alt_name = db.execute(select(AltName)
                         .where(AltName.id == id)).scalars().first()

    if not alt_name:
        raise HTTPException(status_code = status.HTTP_404_NOT_FOUND,
                            detail = f"Alt name not found")

    if alt_name.user_id != current_user.id:
        raise HTTPException(status_code = status.HTTP_403_FORBIDDEN,
                            detail = f"You do have access to this alt name")

    return alt_name

@router.patch("/{id}")
async def update_alt_name(id: int, 
                          new_alt: AltNameUpdate,
                          db: Session = Depends(get_db),
                          current_user = Depends(auth_utils.get_current_user)):
    """
    Update an alt name's title and/or which canonical title it points to
    """
    alt_name = db.scalar(select(AltName).where(AltName.id == id))
    if not alt_name:
        raise HTTPException(status_code = status.HTTP_404_NOT_FOUND,
                            detail = f"Alt name not found")
    if alt_name.user_id != current_user.id:
        raise HTTPException(status_code = status.HTTP_403_FORBIDDEN,
                            detail = f"You do not have access to this alt name")

    if new_alt.title is not None:
        alt_name.title = new_alt.title
    if new_alt.canonical_id is not None:
        canonical = db.scalar(select(Canonical).where(Canonical.id == new_alt.canonical_id))
        
        if not canonical:
            raise HTTPException(status_code = status.HTTP_403_FORBIDDEN,
                                detail = "Provided canonical id does not exist")
        if canonical.user_id != current_user.id:
            raise HTTPException(status_code = status.HTTP_403_FORBIDDEN,
                                detail = "You do not have access to the resource specified by the canonical id")
        
        alt_name.canonical_id = new_alt.canonical_id

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code = status.HTTP_409_CONFLICT,
                            detail = f"This change conflicts with an existing alt name")
    
    db.refresh(alt_name)
    return alt_name
    
@router.delete("/{id}")
async def delete_alt_name(id: int,
                          db: Session = Depends(get_db),
                          current_user = Depends(auth_utils.get_current_user)):
    """
    Delete a specified alt name
    """
    alt_name = db.scalar(select(AltName).where(AltName.id == id))
    if not alt_name:
        raise HTTPException(status_code = status.HTTP_404_NOT_FOUND,
                            detail = f"Alt name not found")
    if alt_name.user_id != current_user.id:
        raise HTTPException(status_code = status.HTTP_403_FORBIDDEN,
                            detail = f"You do not have access to this alt name")
    
    db.delete(alt_name)
    db.commit()

    return Response(status_code = status.HTTP_204_NO_CONTENT)


