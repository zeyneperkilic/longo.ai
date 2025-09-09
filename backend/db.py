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
    global_context = Column(JSON, nullable=True)  # Global user context (name, preferences, diseases)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    conversations = relationship("Conversation", back_populates="user")

class Conversation(Base):
    __tablename__ = "conversations"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    started_at = Column(DateTime, default=datetime.datetime.utcnow)
    status = Column(String, default="active")  # active/closed
    title = Column(String, nullable=True)

    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation")

class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"))
    user_id = Column(Integer, nullable=True)
    role = Column(String)  # system/user/assistant
    content = Column(Text)
    model_latency_ms = Column(Integer, nullable=True)
    response_id = Column(String, nullable=True)  # Unique response identifier
    context_data = Column(JSON, nullable=True)  # Important context (name, preferences, etc.)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    conversation = relationship("Conversation", back_populates="messages")



class LabTestHistory(Base):
    __tablename__ = "lab_test_history"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    test_date = Column(DateTime, default=datetime.datetime.utcnow)
    test_results = Column(JSON)  # Lab test sonuçları
    analysis_result = Column(JSON)  # AI analiz sonucu
    test_type = Column(String, default="multiple")  # single/multiple
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class AIInteraction(Base):
    __tablename__ = "ai_interactions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    interaction_type = Column(String)  # chat, quiz, lab_single, lab_multiple
    user_input = Column(Text, nullable=True)  # User input (quiz answers, lab results, chat message)
    ai_response = Column(Text)  # AI response
    model_used = Column(String, nullable=True)  # Which AI model was used
    interaction_metadata = Column(JSON, nullable=True)  # Additional data (latency, tokens, cost, etc.)
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

def get_lab_test_history(db: Session, user_id: int, limit: int = 10):
    """Kullanıcının lab test geçmişini getir"""
    return db.query(LabTestHistory).filter(
        LabTestHistory.user_id == user_id
    ).order_by(
        LabTestHistory.test_date.desc()
    ).limit(limit).all()

def create_lab_test_record(db: Session, user_id: int, test_results: dict, analysis_result: dict, test_type: str = "multiple"):
    """Yeni lab test kaydı oluştur"""
    lab_record = LabTestHistory(
        user_id=user_id,
        test_results=test_results,
        analysis_result=analysis_result,
        test_type=test_type
    )
    db.add(lab_record)
    db.commit()
    db.refresh(lab_record)
    return lab_record

def create_ai_interaction(db: Session, user_id: int, interaction_type: str, user_input: str = None, 
                         ai_response: str = None, model_used: str = None, interaction_metadata: dict = None):
    """AI interaction kaydı oluştur"""
    interaction = AIInteraction(
        user_id=user_id,
        interaction_type=interaction_type,
        user_input=user_input,
        ai_response=ai_response,
        model_used=model_used,
        interaction_metadata=interaction_metadata
    )
    db.add(interaction)
    db.commit()
    db.refresh(interaction)
    return interaction

def get_user_ai_interactions(db: Session, user_id: int, limit: int = 10):
    """Kullanıcının AI interaction geçmişini getir"""
    return db.query(AIInteraction).filter(
        AIInteraction.user_id == user_id
    ).order_by(
        AIInteraction.created_at.desc()
    ).limit(limit).all()

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

def get_or_create_user_by_external_id(db