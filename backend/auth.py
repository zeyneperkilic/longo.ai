from fastapi import Header, HTTPException
from sqlalchemy.orm import Session
from backend.db import SessionLocal
import time

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# get_or_create_user function removed - User model not used in production
# All user data is managed via external_user_id in ai_messages table
