from sqlalchemy.orm import Session
from fastapi import Depends
from .database import get_db
from .models import Canonical, AltName
from .schema import CanonicalCreate, AltNameCreate

def insert_canonical(new_canonical: CanonicalCreate, db: Session = Depends(get_db)):
    created_canonical = Canonical(**new_canonical.model_dump())
    db.add(created_canonical)
    db.commit()
    db.refresh(created_canonical)

    return created_canonical

def insert_alt(new_alt: AltNameCreate, db: Session = Depends(get_db)):
    created_alt = AltName(**new_alt.model_dump())
    db.add(created_alt)
    db.commit()
    db.refresh(created_alt)

    return created_alt