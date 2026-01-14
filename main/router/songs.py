from fastapi import FastAPI, Response, status, HTTPException, Depends, APIRouter
from sqlalchemy.orm import Session
from ..database import get_db
from ..schema import CanonicalCreate, AltNameCreate
from ..models import Canonical, AltName

router = APIRouter(
    prefix = "/songs",
    tags = ['Songs']
)

@router.get("/")
async def get_all_songs(get_alts: bool = False, get_links: bool = False, db: Session = Depends(get_db)):
    """
    Returns all songs in the database, and (optionally) alternate titles plus video links
    """
    # include query params to allow user to...
    # - get or not get all alternate titles
    # - get or not get alt titles
    result = db.query(Canonical).all()
    return result

@router.post("/")
async def create_song(new_canonical: CanonicalCreate, 
                      db: Session = Depends(get_db)):
    """
    Inserts a song title into the canonical_names table
    """
    created_canonical = Canonical(**new_canonical.model_dump())
    db.add(created_canonical)
    db.commit()
    db.refresh(created_canonical)
    return created_canonical

@router.post("/{id}")
async def get_song(id: int, db: Session = Depends(get_db)):
    """
    Returns a specified song from the database, including its alt names and link
    """
    pass

@router.get("/{id}/alt-names")
async def get_alt_names(id: int, db: Session = Depends(get_db)):
    pass

@router.post("/{id}/alt-names")
async def create_alt_name(id: int, new_alt: AltNameCreate, db: Session = Depends(get_db)):
    new_alt_dict = new_alt.model_dump()
    new_alt_dict['canonical_id'] = id
    created_alt = AltName(**new_alt_dict)
    db.add(created_alt)
    db.commit()
    db.refresh(created_alt)
    
    return created_alt

