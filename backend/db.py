from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Enum, ForeignKey, Boolean, JSON
from sqlalchemy.orm import sessionmaker, declarative_base, relationship, Session
import datetime
import os

# Database configuration - Support both local SQLite and production PostgreSQL
DB_TYPE = os.getenv("DB_TYPE", "sqlite")  # sqlite or postgresql

if DB_TYPE == "postgresql":
    # Production: Use main site's PostgreSQL database
    DB_HOST = os.getenv("DB_HOST")
    DB_PORT = os.getenv("DB_PORT", "5432")
    DB_NAME = os.getenv("DB_NAME")
    DB_USER = os.getenv("DB_USER")
    DB_PASSWORD = os.getenv("DB_PASSWORD")
    
    # Check if all required PostgreSQL variables are set
    if all([DB_HOST, DB_NAME, DB_USER, DB_PASSWORD]):
        DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
        engine = create_engine(
            DATABASE_URL,
            pool_size=20,        # 20 connection hazır tut
            max_overflow=30,     # 30 ek connection oluştur
            pool_pre_ping=True   # Connection'ları test et
        )
        print(f"Connected to PostgreSQL database: {DB_HOST}:{DB_PORT}/{DB_NAME} with connection pooling")
    else:
        print("PostgreSQL credentials incomplete, falling back to SQLite")
        DB_TYPE = "sqlite"
        DB_PATH = os.getenv("DB_PATH", "./app.db")
        DATABASE_URL = f"sqlite:///{DB_PATH}"
        engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
        print(f"Using SQLite database: {DB_PATH}")

if DB_TYPE == "sqlite":
    # Local development or fallback: Use SQLite
    DB_PATH = os.getenv("DB_PATH", "./app.db")
    DATABASE_URL = f"sqlite:///{DB_PATH}"
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
    print(f"Using SQLite database: {DB_PATH}")

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    external_user_id = Column(String, unique=True, index=True, nullable=True)  # Asıl site'den gelen unique ID
    email = Column(String, unique=True, index=True, nullable=True)
    plan = Column(String, default="free")  # 'free' or 'premium'
    created_at = Column(DateTime, default=datetime.datetime.utcnow)






# Simpler, single-table logging for all AI messages without user table dependency
class AIMessage(Base):
    __tablename__ = "ai_messages"
    id = Column(Integer, primary_key=True, index=True)
    external_user_id = Column(String, index=True, nullable=True)
    message_type = Column(String, index=True)  # chat, quiz, lab_single, lab_session, lab_summary
    request_payload = Column(JSON, nullable=True)
    response_payload = Column(JSON, nullable=True)
    model_used = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)



def create_ai_message(
    db: Session,
    external_user_id: str | None,
    message_type: str,
    request_payload: dict | None,
    response_payload: dict | None,
    model_used: str | None = None,
):
    """Log a unified AI message row without requiring a User record."""
    record = AIMessage(
        external_user_id=external_user_id,
        message_type=message_type,
        request_payload=request_payload,
        response_payload=response_payload,
        model_used=model_used,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record

def get_ai_messages(
    db: Session,
    external_user_id: str | None = None,
    message_type: str | None = None,
    limit: int = 50,
):
    """Query ai_messages optionally filtered by external_user_id and/or message_type."""
    query = db.query(AIMessage)
    if external_user_id:
        query = query.filter(AIMessage.external_user_id == external_user_id)
    if message_type:
        query = query.filter(AIMessage.message_type == message_type)
    return query.order_by(AIMessage.created_at.desc()).limit(limit).all()

def get_user_ai_messages_by_type(db: Session, external_user_id: str, message_type: str, limit: int = 10):
    """Get user's AI messages by type (replacement for get_user_ai_interactions)"""
    return get_ai_messages(db, external_user_id=external_user_id, message_type=message_type, limit=limit)

def get_user_ai_messages(db: Session, external_user_id: str, limit: int = 10):
    """Get all user's AI messages (replacement for get_user_ai_interactions)"""
    return get_ai_messages(db, external_user_id=external_user_id, limit=limit)

def get_or_create_user_by_external_id(db: Session, external_user_id: str, plan: str = "free") -> User:
    """External user ID ile kullanıcıyı bul veya oluştur"""
    if not external_user_id:
        raise ValueError("External user ID gerekli")
    
    # Önce external_user_id ile ara
    user = db.query(User).filter(User.external_user_id == external_user_id).first()
    
    if not user:
        # Yeni kullanıcı oluştur
        user = User(
            external_user_id=external_user_id,
            plan=plan,
            global_context={}
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    
    return user

def get_user_by_external_id(db: Session, external_user_id: str) -> User:
    """External user ID ile kullanıcıyı bul"""
    if not external_user_id:
        return None
    
    return db.query(User).filter(User.external_user_id == external_user_id).first()

