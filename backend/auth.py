from fastapi import Header, HTTPException
from sqlalchemy.orm import Session
from backend.db import SessionLocal, User
import time

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_or_create_user(db: Session, user_id: str | None, plan_header: str | None):
    """External user ID ile kullanıcıyı bul veya oluştur"""
    if not user_id:
        # Anonymous user için default ID oluştur
        user_id = f"anon_{int(time.time())}"
        plan_header = "free"
    
    # External user ID ile kullanıcıyı bul veya oluştur
    from backend.db import get_or_create_user_by_external_id
    
    # Plan override kontrolü
    plan = plan_header if plan_header in ("free", "premium") else "free"
    
    user = get_or_create_user_by_external_id(db, user_id, plan)
    
    # Plan güncellemesi gerekirse
    if plan_header in ("free", "premium") and user.plan != plan_header:
        user.plan = plan_header
        db.add(user)
        db.commit()
        db.refresh(user)
    
    return user
