from fastapi import Header, HTTPException
from sqlalchemy.orm import Session
from db import SessionLocal, User

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_or_create_user(db: Session, user_id: str | None, plan_header: str | None):
    # For simplicity, use numeric string or create ephemeral users
    # If no user_id provided, create a guest user with id 0-like behavior
    if not user_id:
        # anonymous bucket per IP would be better; for demo create a dummy user id 1
        user = db.query(User).filter(User.email == "guest@example.com").first()
        if not user:
            user = User(email="guest@example.com", plan="free")
            db.add(user); db.commit(); db.refresh(user)
        return user

    email = f"user-{user_id}@example.com"
    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(email=email, plan="free")
        db.add(user); db.commit(); db.refresh(user)
    # allow plan override via header for testing
    if plan_header in ("free","premium") and user.plan != plan_header:
        user.plan = plan_header
        db.add(user); db.commit()
    return user
