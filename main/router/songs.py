from fastapi import FastAPI, Response, status, HTTPException, Depends, APIRouter
from sqlalchemy.orm import Session
from ..database import get_db
from ..utils import insert_canonical
from ..schema import CanonicalCreate

router = APIRouter(
    prefix = "/songs",
    tags = ['Songs']
)

@router.get("/")
async def get_all_songs():
    # include query params to allow user to get or not get all alternate titles
    return {"message": "no songs yet"}

@router.post("/")
async def create_song(new_canonical: CanonicalCreate, 
                      db: Session = Depends(get_db)):
    created_canonical = insert_canonical(new_canonical, db)
    return created_canonical