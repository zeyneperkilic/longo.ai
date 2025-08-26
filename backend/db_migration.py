#!/usr/bin/env python3
"""
Database Migration Script
SQLite'dan PostgreSQL'e geçiş için yardımcı script
"""

import os
import json
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from backend.db import Base, SessionLocal, User, Conversation, Message, LabTestHistory, AIInteraction

def migrate_to_postgresql():
    """SQLite'dan PostgreSQL'e veri taşıma"""
    
    # PostgreSQL bağlantısı
    pg_host = os.getenv("DB_HOST")
    pg_port = os.getenv("DB_PORT", "5432")
    pg_name = os.getenv("DB_NAME")
    pg_user = os.getenv("DB_USER")
    pg_password = os.getenv("DB_PASSWORD")
    
    if not all([pg_host, pg_name, pg_user, pg_password]):
        print("❌ PostgreSQL credentials eksik!")
        print("Şu environment variables'ları ayarlayın:")
        print("  DB_HOST, DB_NAME, DB_USER, DB_PASSWORD")
        return False
    
    # PostgreSQL engine
    pg_url = f"postgresql://{pg_user}:{pg_password}@{pg_host}:{pg_port}/{pg_name}"
    pg_engine = create_engine(pg_url)
    
    try:
        # PostgreSQL'de tabloları oluştur
        print("🔄 PostgreSQL'de tablolar oluşturuluyor...")
        Base.metadata.create_all(bind=pg_engine)
        print("✅ Tablolar oluşturuldu")
        
        # SQLite'dan veri oku
        print("📖 SQLite'dan veri okunuyor...")
        sqlite_session = SessionLocal()
        
        # Users
        users = sqlite_session.query(User).all()
        print(f"👥 {len(users)} kullanıcı bulundu")
        
        # Conversations
        conversations = sqlite_session.query(Conversation).all()
        print(f"💬 {len(conversations)} konuşma bulundu")
        
        # Messages
        messages = sqlite_session.query(Message).all()
        print(f"💭 {len(messages)} mesaj bulundu")
        
        # Lab tests
        lab_tests = sqlite_session.query(LabTestHistory).all()
        print(f"🔬 {len(lab_tests)} lab test bulundu")
        
        # AI interactions
        ai_interactions = sqlite_session.query(AIInteraction).all()
        print(f"🤖 {len(ai_interactions)} AI interaction bulundu")
        
        # PostgreSQL'e veri yaz
        print("💾 PostgreSQL'e veri yazılıyor...")
        pg_session = sessionmaker(bind=pg_engine)()
        
        # Users
        for user in users:
            # External user ID oluştur (email'den)
            external_user_id = user.email if user.email and user.email != "guest@example.com" else f"user_{user.id}"
            
            pg_user = User(
                id=user.id,
                external_user_id=external_user_id,
                email=user.email,
                plan=user.plan,
                global_context=user.global_context,
                created_at=user.created_at
            )
            pg_session.add(pg_user)
        
        # Conversations
        for conv in conversations:
            pg_conv = Conversation(
                id=conv.id,
                user_id=conv.user_id,
                started_at=conv.started_at,
                status=conv.status,
                title=conv.title
            )
            pg_session.add(pg_conv)
        
        # Messages
        for msg in messages:
            pg_msg = Message(
                id=msg.id,
                conversation_id=msg.conversation_id,
                user_id=msg.user_id,
                role=msg.role,
                content=msg.content,
                model_latency_ms=msg.model_latency_ms,
                response_id=msg.response_id,
                context_data=msg.context_data,
                created_at=msg.created_at
            )
            pg_session.add(pg_msg)
        
        # Lab tests
        for lab in lab_tests:
            pg_lab = LabTestHistory(
                id=lab.id,
                user_id=lab.user_id,
                test_date=lab.test_date,
                test_results=lab.test_results,
                analysis_result=lab.analysis_result,
                test_type=lab.test_type,
                created_at=lab.created_at
            )
            pg_session.add(pg_lab)
        
        # AI interactions
        for ai in ai_interactions:
            pg_ai = AIInteraction(
                id=ai.id,
                user_id=ai.user_id,
                interaction_type=ai.interaction_type,
                user_input=ai.user_input,
                ai_response=ai.ai_response,
                model_used=ai.model_used,
                interaction_metadata=ai.interaction_metadata,
                created_at=ai.created_at
            )
            pg_session.add(pg_ai)
        
        # Commit
        pg_session.commit()
        print("✅ Veri migration tamamlandı!")
        
        # Session'ları kapat
        sqlite_session.close()
        pg_session.close()
        
        return True
        
    except Exception as e:
        print(f"❌ Migration hatası: {e}")
        return False

def switch_to_postgresql():
    """Database tipini PostgreSQL'e çevir"""
    print("🔄 Database tipi PostgreSQL'e çevriliyor...")
    
    # Environment variable'ı güncelle
    os.environ["DB_TYPE"] = "postgresql"
    
    # Database'i yeniden başlat
    from backend.db import engine, SessionLocal
    print("✅ Database PostgreSQL'e geçti!")
    
    return True

if __name__ == "__main__":
    print("🚀 Database Migration Tool")
    print("=" * 40)
    
    choice = input("""
Seçenekler:
1. SQLite'dan PostgreSQL'e veri taşı
2. Database tipini PostgreSQL'e çevir
3. Çıkış

Seçiminiz (1-3): """)
    
    if choice == "1":
        migrate_to_postgresql()
    elif choice == "2":
        switch_to_postgresql()
    elif choice == "3":
        print("👋 Görüşürüz!")
    else:
        print("❌ Geçersiz seçim!")
