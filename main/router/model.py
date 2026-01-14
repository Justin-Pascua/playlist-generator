from fastapi import FastAPI, Response, status, HTTPException, Depends, APIRouter
from sqlalchemy.orm import Session
from ..database import get_db
from ..schema import CanonicalCreate

router = APIRouter(
    prefix = "/model",
    tags = ['Model']
)

@router.post("/model")
async def call_model():
    # Discord bot passes raw Discord message here
    # API calls model and generates output 
    return {"model output": "output str here"}