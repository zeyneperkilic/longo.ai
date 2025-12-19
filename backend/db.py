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
        DATABASE_URL = f"postgresql+psycopg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
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

# User model removed - only ai_messages table is used in production




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


# High risk users table - Lab sonuçlarında high risk tespit edilen kullanıcılar
class HighRiskUser(Base):
    __tablename__ = "high_risk_users"
    id = Column(Integer, primary_key=True, index=True)
    external_user_id = Column(String, index=True, nullable=False)
    user_level = Column(Integer, nullable=True)
    lab_summary_id = Column(Integer, nullable=True)  # İlgili lab_summary ai_messages kaydının ID'si
    risk_level = Column(String, nullable=False)  # high, critical
    risk_reason = Column(Text, nullable=True)  # AI'nin risk tespit nedeni
    risky_tests = Column(JSON, nullable=True)  # Riskli testler listesi
    ai_analysis = Column(Text, nullable=True)  # AI'nin tam analizi
    detected_at = Column(DateTime, default=datetime.datetime.utcnow)
    notified = Column(Boolean, default=False)  # Mail gönderildi mi?
    notified_at = Column(DateTime, nullable=True)



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


def create_high_risk_user(
    db: Session,
    external_user_id: str,
    user_level: int | None,
    lab_summary_id: int | None,
    risk_level: str,
    risk_reason: str | None,
    risky_tests: list | None,
    ai_analysis: str | None,
):
    """High risk kullanıcı kaydı oluştur"""
    record = HighRiskUser(
        external_user_id=external_user_id,
        user_level=user_level,
        lab_summary_id=lab_summary_id,
        risk_level=risk_level,
        risk_reason=risk_reason,
        risky_tests=risky_tests,
        ai_analysis=ai_analysis,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def get_high_risk_users(
    db: Session,
    external_user_id: str | None = None,
    notified: bool | None = None,
    limit: int = 100,
):
    """High risk kullanıcıları sorgula"""
    query = db.query(HighRiskUser)
    if external_user_id:
        query = query.filter(HighRiskUser.external_user_id == external_user_id)
    if notified is not None:
        query = query.filter(HighRiskUser.notified == notified)
    return query.order_by(HighRiskUser.detected_at.desc()).limit(limit).all()
