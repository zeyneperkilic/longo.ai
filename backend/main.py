from fastapi import FastAPI, Depends, HTTPException, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
import json, time
import os
from functools import wraps
from collections import defaultdict
import time

from backend.config import ALLOWED_ORIGINS, CHAT_HISTORY_MAX, FREE_ANALYZE_LIMIT
from backend.db import Base, engine, SessionLocal, User, Conversation, Message, get_user_global_context, update_user_global_context
from backend.auth import get_db, get_or_create_user
from backend.schemas import ChatStartRequest, ChatStartResponse, ChatMessageRequest, ChatResponse, QuizRequest, QuizResponse, SingleLabRequest, SingleSessionRequest, MultipleLabRequest, LabAnalysisResponse, SingleSessionResponse, GeneralLabSummaryResponse
from backend.health_guard import guard_or_message
from backend.orchestrator import parallel_chat, parallel_quiz_analyze, parallel_single_lab_analyze, parallel_single_session_analyze, parallel_multiple_lab_analyze
from backend.utils import parse_json_safe, generate_response_id, extract_user_context_hybrid
from backend.cache_utils import cache_supplements, cache_user_context, cache_model_response, get_cache_stats

# Rate limiting removed for production - will be implemented properly later
# request_counts = defaultdict(list)  # Removed to prevent memory leak
# RATE_LIMIT_WINDOW = 60
# RATE_LIMIT_MAX_REQUESTS = 100

# def rate_limit(func):  # Removed to prevent memory leak
#     ... removed ...

# Basic Authentication
def check_basic_auth(username: str, password: str):
    """Basit authentication kontrolü"""
    from backend.config import AUTH_USERNAME, AUTH_PASSWORD
    if username == AUTH_USERNAME and password == AUTH_PASSWORD:
        return True
    return False

def get_current_user(username: str = Header(None), password: str = Header(None)):
    """Header'dan username/password al ve kontrol et"""
    if not username or not password:
        raise HTTPException(status_code=401, detail="Username ve password gerekli")
    
    if not check_basic_auth(username, password):
        raise HTTPException(status_code=401, detail="Geçersiz kullanıcı adı veya şifre")
    
    return username

def get_conversation_by_user_based_id(db: Session, user_id: int, user_based_conv_id: int) -> Conversation:
    """User-based conversation ID ile gerçek conversation'ı bul"""
    # Kullanıcının conversation'larını tarihe göre sırala (eskiden yeniye)
    conversations = db.query(Conversation).filter(Conversation.user_id == user_id).order_by(Conversation.started_at.asc()).all()
    
    # user_based_conv_id (1, 2,3...) ile indexle
    if user_based_conv_id <= 0 or user_based_conv_id > len(conversations):
        return None
    
    return conversations[user_based_conv_id - 1]  # 1-based to 0-based

def validate_chat_user_id(user_id: str, user_plan: str) -> bool:
    """Chat için user ID validasyonu (Free: Session ID, Premium: Real ID)"""
    if user_plan in ['premium', 'premium_plus']:
        # Premium için session ID kabul etme
        return not user_id.startswith('session-')
    else:
        # Free için her türlü ID kabul et
        return True

app = FastAPI(title="Longopass AI Gateway")

# Security middleware for production
if os.getenv("ENVIRONMENT") == "production":
    # Trusted host middleware
    app.add_middleware(
        TrustedHostMiddleware, 
        allowed_hosts=["*"]  # Configure specific hosts in production
    )
    
    # Production'da CORS'u kısıtla
    if ALLOWED_ORIGINS == ["*"]:
        print("⚠️  WARNING: CORS is open to all origins in production!")
        print("   Set ALLOWED_ORIGINS environment variable for security")

# Create database tables
Base.metadata.create_all(bind=engine)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS if ALLOWED_ORIGINS!=["*"] else ["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],  # Restrict to needed methods only
    allow_headers=["*"],
)

# Serve widget js and static frontend (optional)
# app.mount("/static", StaticFiles(directory="frontend"), name="static")

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "longopass-ai"}

@app.get("/widget/longo-health-widget.js")
def widget_js():
    with open("backend/widget/longo-health-widget.js", "r", encoding="utf-8") as f:
        return f.read()

@app.get("/widget/longo-health-widget.css")
def widget_css():
    with open("backend/widget/longo-health-widget.css", "r", encoding="utf-8") as f:
        return f.read()

@app.get("/widget/demo.html")
def demo_page():
    from fastapi.responses import HTMLResponse
    with open("backend/widget/demo.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

@app.get("/widget/longo.jpeg")
def longo_image():
    from fastapi.responses import FileResponse
    return FileResponse("backend/widget/longo.jpeg")

# ---------- FREE USER SESSION-BASED CHAT ----------

async def handle_free_user_chat(req: ChatMessageRequest, x_user_id: str):
    """Free kullanıcılar için session-based chat handler"""
    from backend.cache_utils import get_session_question_count, increment_session_question_count
    
    # Session-based question count kontrolü
    question_count = get_session_question_count(x_user_id)
    
    # 10 soru limiti kontrolü
    if question_count >= 10:
        return ChatResponse(
            conversation_id=0,
            reply="LIMIT_POPUP:🎯 Günlük 10 soru limitiniz doldu! Yarın tekrar konuşmaya devam edebilirsiniz. 💡 Premium plana geçerek sınırsız soru sorma imkanına sahip olun!",
            latency_ms=0
        )
    
    # Soru sayısını artır
    increment_session_question_count(x_user_id)
    
    # Health Guard ile kategori kontrolü
    message_text = req.text or req.message
    if not message_text:
        raise HTTPException(400, "Mesaj metni gerekli")
    
    ok, msg = guard_or_message(message_text)
    if not ok:
        return ChatResponse(conversation_id=0, reply=msg, latency_ms=0)
    
    # Selamlama kontrolü
    txt = message_text.lower().strip()
    pure_greeting_keywords = [
        "selam", "naber", "günaydın", "gunaydin",
        "iyi akşamlar", "iyi aksamlar", "iyi geceler", "iyi günler", "iyi gunler"
    ]
    
    if any(kw == txt for kw in pure_greeting_keywords):
        reply = f"Merhaba! Ben Longo AI. Sadece sağlık, supplement ve laboratuvar konularında yardımcı olabilirim. Size nasıl yardımcı olabilirim? (Kalan soru: {10 - question_count})"
        return ChatResponse(conversation_id=0, reply=reply, latency_ms=0)
    
    # AI yanıtı için OpenRouter kullan
    try:
        from backend.openrouter_client import get_ai_response
        
        # Free kullanıcılar için güzel prompt
        system_prompt = """Sen Longo AI'sın - sağlık ve supplement konularında yardımcı olan dost canlısı bir asistan. 

🎯 GÖREVİN: Sadece sağlık, supplement, beslenme ve laboratuvar konularında yanıt ver.

💬 KONUŞMA TARZI: Samimi, destekleyici ve yardımsever ol. Kullanıcıya "sen" diye hitap et.

🚫 KISITLAMALAR: 
- Sağlık dışında konulardan bahsetme
- Off-topic soruları kibarca sağlık alanına yönlendir
- Kaynak link'leri veya referans'lar ekleme

✨ SAĞLIK ODAĞI: Her konuyu sağlık ve supplement alanına çek. Kullanıcı başka bir şeyden bahsederse, nazikçe sağlık konusuna yönlendir.

💡 YANIT STİLİ: Kısa, net ve anlaşılır ol. Sadece sağlık konusuna odaklan!"""
        
        # Kalan soru sayısını belirt
        user_message = f"{message_text}\n\nNot: Bu kullanıcının kalan soru hakkı: {10 - question_count}"
        
        ai_response = await get_ai_response(
            system_prompt=system_prompt,
            user_message=user_message,
            model="openai/gpt-5-chat:online"  # Tüm kullanıcılar için aynı kalite
        )
        
        # Kalan soru sayısını yanıta ekle
        reply = f"{ai_response}\n\n💡 Kalan soru hakkınız: {10 - question_count - 1}"
        
        return ChatResponse(conversation_id=0, reply=reply, latency_ms=0)
        
    except Exception as e:
        print(f"Free user chat error: {e}")
        return ChatResponse(
            conversation_id=0,
            reply="Üzgünüm, şu anda yanıt veremiyorum. Lütfen daha sonra tekrar deneyin.",
            latency_ms=0
        )

# ---------- PREMIUM USER DATABASE-BASED CHAT ----------

@app.post("/ai/chat/start", response_model=ChatStartResponse)
def chat_start(body: ChatStartRequest = None,
               db: Session = Depends(get_db),
               x_user_id: str | None = Header(default=None),
               x_user_plan: str | None = Header(default=None)):
    
    # Plan kontrolü
    user_plan = x_user_plan or "free"
    is_premium = user_plan in ["premium", "premium_plus"]
    
    # User ID validasyonu (Free: Session ID, Premium: Real ID)
    if not validate_chat_user_id(x_user_id or "", user_plan):
        raise HTTPException(status_code=400, detail="Premium kullanıcılar için gerçek user ID gerekli")
    
    # Free kullanıcılar için session-based conversation
    if not is_premium:
        # Free kullanıcılar için basit conversation ID (session-based)
        from backend.cache_utils import get_session_question_count
        question_count = get_session_question_count(x_user_id or "anonymous")
        
        # 10 soru limiti kontrolü
        if question_count >= 10:
            return ChatStartResponse(
                conversation_id=0,
                detail="🎯 Günlük 10 soru limitiniz doldu! Yarın tekrar konuşmaya devam edebilirsiniz. 💡 Premium plana geçerek sınırsız soru sorma imkanına sahip olun!"
            )
        
        # Free kullanıcılar için session-based conversation ID
        return ChatStartResponse(conversation_id=1)  # Her zaman 1, session'da takip edilir
    
    # Premium kullanıcılar için database-based conversation
    user = get_or_create_user(db, x_user_id, user_plan)
    
    # Bu kullanıcının kaç conversation'ı var? +1 yaparak user-based ID oluştur
    user_conv_count = db.query(Conversation).filter(Conversation.user_id == user.id).count()
    user_based_conv_id = user_conv_count + 1
    
    conv = Conversation(user_id=user.id, status="active")
    db.add(conv); db.commit(); db.refresh(conv)
    
    # User-based conversation ID döndür (kullanıcı deneyimi için)
    return ChatStartResponse(conversation_id=user_based_conv_id)

@app.get("/ai/chat/{conversation_id}/history")
def chat_history(conversation_id: int,
                 db: Session = Depends(get_db),
                 x_user_id: str | None = Header(default=None),
                 x_user_plan: str | None = Header(default=None)):
    
    # Plan kontrolü
    user_plan = x_user_plan or "free"
    is_premium = user_plan in ["premium", "premium_plus"]
    
    # User ID validasyonu (Free: Session ID, Premium: Real ID)
    if not validate_chat_user_id(x_user_id or "", user_plan):
        raise HTTPException(status_code=400, detail="Premium kullanıcılar için gerçek user ID gerekli")
    
    # Free kullanıcılar için session-based history (boş)
    if not is_premium:
        return []  # Free kullanıcılar için geçmiş yok
    
    # Premium kullanıcılar için database-based history
    user = get_or_create_user(db, x_user_id, user_plan)
    
    # User-based conversation ID'yi real DB ID'ye çevir
    conv = get_conversation_by_user_based_id(db, user.id, conversation_id)
    if not conv:
        raise HTTPException(404, "Konuşma bulunamadı")
    
    # Güvenlik için user ID kontrolü ekle
    msgs = db.query(Message).filter(
        Message.conversation_id == conv.id,
        Message.user_id == user.id
    ).order_by(Message.created_at.asc()).all()
    
    return [{"role": m.role, "content": m.content, "ts": m.created_at.isoformat()} for m in msgs][-CHAT_HISTORY_MAX:]

@app.post("/ai/chat", response_model=ChatResponse)
async def chat_message(req: ChatMessageRequest,
                  current_user: str = Depends(get_current_user),
                  db: Session = Depends(get_db),
                  x_user_id: str | None = Header(default=None),
                  x_user_plan: str | None = Header(default=None)):
    
    # Plan kontrolü
    user_plan = x_user_plan or "free"
    is_premium = user_plan in ["premium", "premium_plus"]
    
    # User ID validasyonu (Free: Session ID, Premium: Real ID)
    if not validate_chat_user_id(x_user_id or "", user_plan):
        raise HTTPException(status_code=400, detail="Premium kullanıcılar için gerçek user ID gerekli")
    
    # Free kullanıcılar için session-based chat
    if not is_premium:
        return await handle_free_user_chat(req, x_user_id)
    
    # Premium kullanıcılar için database-based chat
    user = get_or_create_user(db, x_user_id, user_plan)

    # FLEXIBLE INPUT HANDLING - Asıl site'dan herhangi bir format gelebilir
    conversation_id = req.conversation_id or req.conv_id
    if not conversation_id:
        raise HTTPException(400, "Conversation ID gerekli")
    
    # User-based conversation ID'yi real DB ID'ye çevir
    conv = get_conversation_by_user_based_id(db, user.id, conversation_id)
    if not conv:
        raise HTTPException(404, "Konuşma bulunamadı")

    # Global context'i önce al (hafıza sorusu için gerekli)
    global_context = get_user_global_context(db, user.id)
    
    # FLEXIBLE INPUT HANDLING - Asıl site'dan herhangi bir format gelebilir
    message_text = req.text or req.message
    if not message_text:
        raise HTTPException(400, "Mesaj metni gerekli")
    
    # Health Guard ile kategori kontrolü
    ok, msg = guard_or_message(message_text)
    
    # Hafıza soruları artık HEALTH kategorisinde, özel işlem yok
    memory_bypass = False
    if not ok:
        # store user message
        db.add(Message(conversation_id=conv.id, user_id=user.id, role="user", content=message_text)); db.commit()
        # reply fixed message
        reply = msg
        m = Message(conversation_id=conv.id, role="assistant", content=reply, model_latency_ms=0)
        db.add(m); db.commit()
        return ChatResponse(conversation_id=conv.id, reply=reply, latency_ms=0)
    
    # Hafıza soruları artık normal AI model ile yanıtlanıyor
    
    # Selamlama sonrası özel yanıt kontrolü
    txt = message_text.lower().strip()
    pure_greeting_keywords = [
        "selam", "naber", "günaydın", "gunaydin",
        "iyi akşamlar", "iyi aksamlar", "iyi geceler", "iyi günler", "iyi gunler"
    ]
    
    # Eğer saf selamlama ise özel yanıt ver
    if any(kw == txt for kw in pure_greeting_keywords):
        reply = "Merhaba! Ben Longo AI. Sadece sağlık, supplement ve laboratuvar konularında yardımcı olabilirim. Size nasıl yardımcı olabilirim?"
        m = Message(conversation_id=conv.id, role="assistant", content=reply, model_latency_ms=0)
        db.add(m); db.commit()
        return ChatResponse(conversation_id=conv.id, reply=reply, latency_ms=0)

    # store user message FIRST
    db.add(Message(conversation_id=conv.id, user_id=user.id, role="user", content=message_text)); db.commit()

    # build history (including the new user message)
    rows = db.query(Message).filter(Message.conversation_id==conv.id).order_by(Message.created_at.asc()).all()
    
    # Get user's previous analyses for context (CACHE THIS!)
    from backend.db import get_user_ai_interactions
    user_analyses = get_user_ai_interactions(db, user.id, limit=5)
    
    # Build enhanced system prompt with user context
    system_prompt = "Sen Longo AI'sın. SADECE sağlık/supplement/lab konularında yanıt ver. Off-topic'te kibarca reddet. KAYNAK EKLEME: Otomatik olarak kaynak link'leri, referans'lar veya citation'lar ekleme!\n\nÖNEMLİ: Eğer kullanıcı bilgileri (isim, yaş, hastalık vb.) aşağıda verilmişse, bunları kullan ve hatırladığını göster.\n\n🚨 SAĞLIK YÖNLENDİRME KURALI: Her konuyu sağlık ve supplement alanına çek! Kullanıcı off-topic bir şey söylerse, kibarca sağlık konusuna yönlendir ve supplement önerisi yap!\n\n❌ OFF-TOPIC BİLGİ VERME: Sağlık dışında konularda bilgi verme ve detaya girme! Kısa ve net cevaplar ver,Sadece sağlık konusuna odaklan!"
    
    # Global + Local Context Sistemi - OPTIMIZED
    user_context = {}
    
    # 1. Global context'i getir (zaten yukarıda alındı)
    if global_context:
        # Key'leri normalize et (büçük harf -> küçük harf + encoding temizle)
        normalized_global = {}
        for key, value in global_context.items():
            if key and value:  # None/boş değerleri atla
                # Encoding sorunlarını çöz: 'i̇si̇m' -> 'isim'
                normalized_key = key.lower().replace('i̇', 'i').replace('ı', 'i').strip()
                if normalized_key and normalized_key not in normalized_global:
                    normalized_global[normalized_key] = value  # ✅ DOĞRU KEY!
        user_context.update(normalized_global)
    
    # 1.5. READ-THROUGH: Lab verisi global context'te yoksa DB'den çek
    # LAB VERİLERİ PROMPT'TAN TAMAMEN ÇIKARILDI - TOKEN TASARRUFU İÇİN
    # Lab verileri hala context'te tutuluyor ama prompt'a eklenmiyor
    
    # 2. Son mesajlardan yeni context bilgilerini çıkar (ONLY IF NEEDED)
    # ÖNEMLİ: Global context user bazında olmalı, conversation bazında değil!
    # Bu yüzden sadece yeni mesajdan context çıkar, eski mesajlardan değil
    # recent_messages = rows[-(CHAT_HISTORY_MAX-1):] if len(rows) > 0 else []
    new_context = {}
    
    # 2. YENİ MESAJDAN CONTEXT ÇIKAR (opsiyonel - context yoksa da çalışsın)
    current_message_context = extract_user_context_hybrid(message_text, user.email) or {}
    for key, value in current_message_context.items():
        # Key'i normalize et (encoding sorunlarını çöz)
        normalized_key = key.strip().lower()
        if normalized_key and value:  # Boş değerleri atla
            if normalized_key not in new_context:
                new_context[normalized_key] = value
            elif isinstance(value, list) and isinstance(new_context[normalized_key], list):
                # Listeleri birleştir (duplicate'ları kaldır)
                new_context[normalized_key] = list(set(new_context[normalized_key] + value))
            else:
                # String değerleri güncelle
                new_context[normalized_key] = value
    
    # 3. YENİ CONTEXT'İ GLOBAL CONTEXT'E EKLE (DÖNGÜ DIŞINDA!)
    context_changed = False
    if new_context and any(new_context.values()):
        # Check if context actually changed
        for key, value in new_context.items():
            if key not in user_context or user_context[key] != value:
                context_changed = True
                break
        
        if context_changed:
            # Mevcut global context'i al ve merge et (overwrite etme!)
            current_global = get_user_global_context(db, user.id) or {}
            updated_context = {**current_global, **new_context}
            update_user_global_context(db, user.id, updated_context)
            # Local context'i de güncelle
            user_context.update(new_context)
    
    # 4. KULLANICI BİLGİLERİNİ AI'YA HATIRLAT (LAB VERİLERİ ÇIKARILDI)
    print(f"🔍 DEBUG: Chat endpoint'inde user_context: {user_context}")
    
    if user_context and any(user_context.values()):
        system_prompt += "\n\n=== KULLANICI BİLGİLERİ ===\n"
        print(f"🔍 DEBUG: Kullanıcı bilgileri prompt'a ekleniyor...")
        
        # String ve integer değerler için özel format
        if "isim" in user_context and user_context["isim"]:
            system_prompt += f"KULLANICI ADI: {user_context['isim']}\n"
            print(f"🔍 DEBUG: Kullanıcı adı eklendi: {user_context['isim']}")
            
        if "yas" in user_context and user_context["yas"]:
            system_prompt += f"KULLANICI YAŞI: {user_context['yas']} yaşında\n"
            print(f"🔍 DEBUG: Kullanıcı yaşı eklendi: {user_context['yas']}")
            
        if "tercihler" in user_context and user_context["tercihler"]:
            tercihler_str = ', '.join(user_context['tercihler']) if isinstance(user_context['tercihler'], list) else str(user_context['tercihler'])
            system_prompt += f"KULLANICI TERCİHLERİ: {tercihler_str}\n"
            print(f"🔍 DEBUG: Kullanıcı tercihleri eklendi: {tercihler_str}")
            
        if "hastaliklar" in user_context and user_context["hastaliklar"]:
            hastaliklar_str = ', '.join(user_context['hastaliklar']) if isinstance(user_context['hastaliklar'], list) else str(user_context['hastaliklar'])
            system_prompt += f"HASTALIKLAR: {hastaliklar_str}\n"
            print(f"🔍 DEBUG: Hastalıklar eklendi: {hastaliklar_str}")
            
        if "cinsiyet" in user_context and user_context["cinsiyet"]:
            system_prompt += f"KULLANICI CİNSİYETİ: {user_context['cinsiyet']}\n"
            print(f"🔍 DEBUG: Kullanıcı cinsiyeti eklendi: {user_context['cinsiyet']}")
        
        # Lab verilerini de göster
        if "son_lab_test" in user_context and user_context["son_lab_test"]:
            system_prompt += f"SON LAB TEST: {user_context['son_lab_test']}\n"
            print(f"🔍 DEBUG: Son lab test eklendi: {user_context['son_lab_test']}")
            
        if "son_lab_deger" in user_context and user_context["son_lab_deger"]:
            system_prompt += f"SON LAB DEĞER: {user_context['son_lab_deger']}\n"
            print(f"🔍 DEBUG: Son lab değer eklendi: {user_context['son_lab_deger']}")
            
        if "son_lab_durum" in user_context and user_context["son_lab_durum"]:
            system_prompt += f"SON LAB DURUM: {user_context['son_lab_durum']}\n"
            print(f"🔍 DEBUG: Son lab durum eklendi: {user_context['son_lab_durum']}")
            
        if "lab_tarih" in user_context and user_context["lab_tarih"]:
            system_prompt += f"LAB TARİH: {user_context['lab_tarih']}\n"
            print(f"🔍 DEBUG: Lab tarih eklendi: {user_context['lab_tarih']}")
            
        print(f"🔍 DEBUG: Final system prompt lab verileri ile hazırlandı!")
        system_prompt += "\nÖNEMLİ: Bu bilgileri kesinlikle hatırla! Kullanıcı sana adını, yaşını, hastalığını veya lab sonuçlarını sorduğunda yukarıdaki bilgilerle cevap ver!"
    else:
        # Context yoksa default prompt ekle
        print(f"🔍 DEBUG: User context boş, default prompt kullanılıyor!")
        system_prompt += "\n\nGenel sağlık ve supplement konularında yardımcı ol. Kullanıcı bilgileri yoksa genel öneriler ver ve listeden mantıklı ürün öner."

    # User analyses context - OPTIMIZED (only add if exists)
    if user_analyses:
        system_prompt += "\n\nKULLANICI GEÇMİŞİ:\n"
        for analysis in user_analyses:
            if analysis.interaction_type in ["quiz", "lab_single", "lab_multiple"]:
                system_prompt += f"- {analysis.interaction_type.upper()}: {analysis.created_at.strftime('%Y-%m-%d')}\n"
        system_prompt += "\nBu bilgileri kullanarak daha kişiselleştirilmiş yanıtlar ver."

    # XML'den supplement listesini ekle - AI'ya ürün önerileri için
    from backend.config import SUPPLEMENTS_LIST
    supplements_list = SUPPLEMENTS_LIST
    
    # Supplement listesi kuralları (quiz'deki gibi)
    system_prompt += "\n- MUTLAKA sadece user message'da verilen supplement listesindeki ürünleri öner başka ürün sakın önerme!"
    system_prompt += "\n- Sakın ürünlerin id'lerini, Otomatik olarak kaynak link'leri, referans'lar veya citation'lar ekleme!"
    system_prompt += "\n- DİL: SADECE TÜRKÇE YANIT VER!"
    system_prompt += "\n\n🎯 SAĞLIK YÖNLENDİRME STRATEJİSİ:"
    system_prompt += "\n- Off-topic konularda: 'Bu konu sağlıkla ilgili değil ama sana sağlık önerisi verebilirim'"
    system_prompt += "\n- Her durumda Supplement önerisi yapma sadece ihtiyaç varsa yap ve sağlık konusuna çek"
    system_prompt += "\n- Örnek: 'Hava durumu yerine D vitamini eksikliği hakkında konuşalım'"
    system_prompt += "\n- Uzun açıklamalar yapma!"
    system_prompt += "\n- Quiz sonucu istenirse: Kullanıcının quiz geçmişini otomatik incele!"
    system_prompt += "\n- Mevcut verileri analiz et ve öneri yap!"
    system_prompt += "\n- 'Ne alayım?', 'Bana bir şey öner', 'Ne yapayım?' gibi belirsiz sorular → HEMEN SAĞLIK!"
    system_prompt += "\n- 'Supplement öner', 'Hangi ürünleri alayım?' şeklinde yönlendir!"
    system_prompt += "\n- Boşuna supplement önerme! Sadece gerçekten işe yarayacak olanları öner!"
    system_prompt += "\n- E-ticaret stratejisi: 4 DEFAULT + 2-3 PROBLEME ÖZEL = 6-7 Supplement!"
    system_prompt += "\n- Değerler iyiyse Longevity, kötüyse problem çözücü öner!"
    
    # Supplement listesini user message olarak ekle (quiz'deki gibi)
    # Kategori bazlı gruplandırma - token tasarrufu için
    categories = list(set([s['category'] for s in supplements_list]))
    supplements_info = f"\n\nTOPLAM ÜRÜN: {len(supplements_list)} supplement\n"
    supplements_info += f"KATEGORİLER: {', '.join(categories)}\n"
    supplements_info += " AI: Aşağıdaki kategorilere göre gruplandırılmış ürünlerden en uygun olanları seç!\n\n"
    
    # Her kategori için ürünleri grupla
    for category in categories:
        category_products = [s for s in supplements_list if s['category'] == category]
        supplements_info += f" {category.upper()} ({len(category_products)} ürün):\n"
        for i, supplement in enumerate(category_products, 1):
            supplements_info += f"  {i}. {supplement['name']} (ID: {supplement['id']})\n"
        supplements_info += "\n"
    
    supplements_info += "💡 AI: Tüm bu 128 ürün arasından en uygun olanları seç!"
    
    # Context'i ilk message'a ekle
    
    # System message
    history = [{"role": "system", "content": system_prompt, "context_data": user_context}]
    
    # Supplement listesi user message olarak ekle (quiz'deki gibi)
    history.append({"role": "user", "content": supplements_info})
    
    # Chat history
    for r in rows[-(CHAT_HISTORY_MAX-1):]:
        history.append({"role": r.role, "content": r.content})

    # parallel chat with synthesis
    start = time.time()
    try:
        res = parallel_chat(history)
        final = res["content"]
        used_model = res.get("model_used","unknown")
    except Exception as e:
        # Production'da log yerine fallback kullan
        from backend.orchestrator import chat_fallback
        fallback_res = chat_fallback(history)
        final = fallback_res["content"]
        used_model = fallback_res["model_used"]
    
    latency_ms = int((time.time()-start)*1000)

    # Response ID oluştur ve context bilgilerini sakla
    response_id = generate_response_id()
    
    # Assistant message'ı response ID ve context ile kaydet
    m = Message(
        conversation_id=conv.id, 
        role="assistant", 
        content=final, 
        model_latency_ms=latency_ms,
        response_id=response_id,
        context_data=user_context
    )
    db.add(m); db.commit(); db.refresh(m)
    
    # AI interaction kaydı ekle (progress tracking için)
    try:
        from backend.db import create_ai_interaction
        create_ai_interaction(
            db=db,
            user_id=user.id,
            interaction_type="chat",
            user_input=message_text,
            ai_response=final,
            model_used=used_model,
            interaction_metadata={
                "conversation_id": conv.id,
                "response_id": response_id,
                "latency_ms": latency_ms,
                "context_keys": list(user_context.keys()) if user_context else []
            }
        )
    except Exception as e:
        # Database yazma hatası olsa bile chat mesajı kaydedildi
        print(f"Chat AI interaction kaydı hatası: {e}")
    
    # Global context'i güncelle (yeni bilgiler varsa) - OPTIMIZED
    if new_context and context_changed:
        current_global = get_user_global_context(db, user.id)
        if current_global:
            # Mevcut context ile birleştir
            updated_context = {**current_global, **new_context}
            # None değerleri temizle
            updated_context = {k: v for k, v in updated_context.items() if v is not None}
            update_user_global_context(db, user.id, updated_context)
        else:
            # Yeni global context oluştur
            update_user_global_context(db, user.id, new_context)
    
    # Database kaydı kaldırıldı - Asıl site zaten yapacak
    # Sadece chat yanıtını döndür
    
    return ChatResponse(conversation_id=conv.id, reply=final, latency_ms=latency_ms)

# ---------- ANALYZE (FREE: one-time), LAB ----------

def count_user_analyses(db: Session, user_id: int) -> int:
    # Count 'analyze' requests stored as system messages tagged? Simpler: count assistant messages with model_name like 'analyze'
    return db.query(Message).filter(Message.user_id==user_id, Message.role=="assistant", Message.model_name=="analyze").count()

@app.post("/ai/quiz", response_model=QuizResponse)
async def analyze_quiz(body: QuizRequest,
                 current_user: str = Depends(get_current_user),
                 db: Session = Depends(get_db),
                 x_user_id: str | None = Header(default=None),
                 x_user_plan: str | None = Header(default=None)):
    """Quiz endpoint - Sadece AI model işlemi, asıl site entegrasyonu için optimize edildi"""
    
    user = get_or_create_user(db, x_user_id, x_user_plan)
    
    # Quiz data'yı dict'e çevir ve validate et - TAMAMEN ESNEK
    quiz_dict = validate_input_data(body.quiz_answers or {}, [])  # Required fields yok, her şeyi kabul et
    
    # XML'den supplement listesini al (eğer body'de yoksa)
    from backend.config import SUPPLEMENTS_LIST
    supplements_dict = body.available_supplements or SUPPLEMENTS_LIST
    
    # Use parallel quiz analysis with supplements
    res = parallel_quiz_analyze(quiz_dict, supplements_dict)
    final_json = res["content"]
    
    data = parse_json_safe(final_json) or {}

    if not data:
        # Fallback: Default response döndür
        data = {
            "success": True,
            "message": "Quiz analizi tamamlandı",
            "nutrition_advice": {
                "title": "Beslenme Önerileri",
                "recommendations": [
                    "Dengeli beslenme programı uygulayın",
                    "Bol sebze ve meyve tüketin",
                    "Yeterli protein alımına dikkat edin"
                ]
            },
            "lifestyle_advice": {
                "title": "Yaşam Tarzı Önerileri",
                "recommendations": [
                    "Düzenli egzersiz yapın",
                    "Yeterli uyku alın",
                    "Stres yönetimi teknikleri uygulayın"
                ]
            },
            "general_warnings": {
                "title": "Genel Uyarılar",
                "warnings": [
                    "Doktorunuza danışmadan supplement kullanmayın",
                    "Alerjik reaksiyonlara dikkat edin"
                ]
            },
            "supplement_recommendations": [
                {
                    "name": "D Vitamini",
                    "description": "Kemik sağlığı ve bağışıklık için",
                    "daily_dose": "600-800 IU (doktorunuza danışın)",
                    "benefits": ["Kalsiyum emilimini artırır", "Bağışıklık güçlendirir"],
                    "warnings": ["Yüksek dozlarda toksik olabilir"],
                    "priority": "high"
                },
                {
                    "name": "Omega-3",
                    "description": "Kalp ve beyin sağlığı için",
                    "daily_dose": "1000-2000 mg (doktorunuza danışın)",
                    "benefits": ["Kalp sağlığını destekler", "Beyin fonksiyonlarını artırır"],
                    "warnings": ["Kan sulandırıcı ilaçlarla etkileşebilir"],
                    "priority": "high"
                }
            ],
            "disclaimer": "Bu içerik bilgilendirme amaçlıdır; tıbbi tanı/tedavi için hekiminize başvurun."
        }
    
    # Quiz sonuçlarını global context'e ekle (SADECE ÖZET BİLGİLER)
    if data and "supplement_recommendations" in data:
        from backend.db import get_user_global_context, update_user_global_context, create_ai_interaction
        
        # Mevcut global context'i al
        current_context = get_user_global_context(db, user.id) or {}
        
        # Quiz sonuçlarından SADECE ÖZET BİLGİLERİ çıkar
        quiz_context = {}
        
        # Quiz cevaplarından temel bilgi çıkar
        if "age" in quiz_dict:
            quiz_context["yas"] = str(quiz_dict["age"])
        if "gender" in quiz_dict:
            quiz_context["cinsiyet"] = quiz_dict["gender"]
        if "health_goals" in quiz_dict:
            quiz_context["tercihler"] = quiz_dict["health_goals"]
        
        # Supplement önerilerinden SADECE İLK N TANESİNİ al
        if "supplement_recommendations" in data:
            all_supplements = [s["name"] for s in data["supplement_recommendations"]]
            from backend.config import MAX_SUPPLEMENTS_IN_CONTEXT
            quiz_context["quiz_supplements"] = all_supplements[:MAX_SUPPLEMENTS_IN_CONTEXT]
        
        # Priority supplement'lerden SADECE İLK N TANESİNİ al
        if "supplement_recommendations" in data:
            priority_supplements = [s["name"] for s in data["supplement_recommendations"] if s.get("priority") == "high"]
            from backend.config import MAX_PRIORITY_SUPPLEMENTS
            quiz_context["quiz_priority"] = priority_supplements[:MAX_PRIORITY_SUPPLEMENTS]
        
        # Quiz tarihini ekle
        import time
        quiz_context["quiz_tarih"] = time.strftime("%Y-%m-%d")
        
        # Global context'i güncelle
        if quiz_context:
            updated_context = {**current_context, **quiz_context}
            update_user_global_context(db, user.id, updated_context)
        
        # AI interaction kaydı ekle (progress tracking için)
        try:
            create_ai_interaction(
                db=db,
                user_id=user.id,
                interaction_type="quiz",
                user_input=str(quiz_dict),
                ai_response=str(data),
                model_used="parallel_quiz_analyze",
                interaction_metadata={"supplement_count": len(data.get("supplement_recommendations", []))}
            )
        except Exception as e:
            # Database yazma hatası olsa bile global context güncellendi
            print(f"Quiz database kaydı hatası: {e}")
    
    # Return quiz response
    return data

@app.post("/ai/lab/single", response_model=LabAnalysisResponse)
def analyze_single_lab(body: SingleLabRequest,
                        current_user: str = Depends(get_current_user),
                       db: Session = Depends(get_db),
                        x_user_id: str | None = Header(default=None),
                        x_user_plan: str | None = Header(default=None)):
    """Analyze single lab test result with historical trend analysis"""
    user = get_or_create_user(db, x_user_id, x_user_plan or "premium")
    
    # Convert test to dict for processing
    test_dict = body.test.model_dump()
    
    # Geçmiş sonuçları zaten dict formatında
    historical_dict = body.historical_results
    
    # Health Guard kaldırıldı - Lab analizi zaten kontrollü içerik üretiyor

    # Use parallel single lab analysis with historical results
    res = parallel_single_lab_analyze(test_dict, historical_dict)
    final_json = res["content"]
    data = parse_json_safe(final_json) or {}
    
    # Lab sonuçlarını global context'e ekle (QUIZ GİBİ)
    if data and "analysis" in data:
        from backend.db import get_user_global_context, update_user_global_context, create_ai_interaction
        
        print(f"🔍 DEBUG: Lab endpoint'inde user context güncelleme başladı")
        print(f"🔍 DEBUG: User ID: {user.id}")
        
        # Mevcut global context'i al
        current_context = get_user_global_context(db, user.id) or {}
        print(f"🔍 DEBUG: Mevcut context: {current_context}")
        
        # Lab sonuçlarından ÖZET BİLGİLERİ çıkar
        lab_context = {}
        
        # Test adı
        if "name" in test_dict:
            lab_context["son_lab_test"] = test_dict["name"]
            print(f"🔍 DEBUG: Test adı eklendi: {test_dict['name']}")
        
        # Test değeri ve durumu
        if "value" in test_dict:
            lab_context["son_lab_deger"] = str(test_dict["value"])
            print(f"🔍 DEBUG: Test değeri eklendi: {test_dict['value']}")
        
        # Test birimi
        if "unit" in test_dict:
            lab_context["son_lab_birim"] = test_dict["unit"]
            print(f"🔍 DEBUG: Test birimi eklendi: {test_dict['unit']}")
        
        # Referans aralığı
        if "reference_range" in test_dict:
            lab_context["son_lab_referans"] = test_dict["reference_range"]
            print(f"🔍 DEBUG: Referans aralığı eklendi: {test_dict['reference_range']}")
        
        # AI analiz sonucu
        if "analysis" in data and "summary" in data["analysis"]:
            lab_context["son_lab_durum"] = data["analysis"]["summary"]
            print(f"🔍 DEBUG: Lab durumu eklendi: {data['analysis']['summary']}")
        
        # Lab tarihi
        import time
        lab_context["lab_tarih"] = time.strftime("%Y-%m-%d")
        print(f"🔍 DEBUG: Lab tarihi eklendi: {lab_context['lab_tarih']}")
        
        print(f"🔍 DEBUG: Oluşturulan lab_context: {lab_context}")
        
        # Global context'i güncelle
        if lab_context:
            updated_context = {**current_context, **lab_context}
            print(f"🔍 DEBUG: Güncellenecek context: {updated_context}")
            update_user_global_context(db, user.id, updated_context)
            print(f"🔍 DEBUG: Context güncellendi!")
        else:
            print(f"🔍 DEBUG: Lab context boş, güncelleme yapılmadı!")
        
        # AI interaction kaydı ekle
        try:
            create_ai_interaction(
                db=db,
                user_id=user.id,
                interaction_type="lab_single",
                user_input=str(test_dict),
                ai_response=str(data),
                model_used="parallel_single_lab_analyze",
                interaction_metadata={"test_name": test_dict.get("name", "unknown")}
            )
            print(f"🔍 DEBUG: AI interaction kaydı eklendi!")
        except Exception as e:
            print(f"🔍 DEBUG: Lab single database kaydı hatası: {e}")
    else:
        print(f"🔍 DEBUG: Lab endpoint'inde data veya analysis yok!")
        print(f"🔍 DEBUG: Data: {data}")
    
    return data

@app.post("/ai/lab/session", response_model=SingleSessionResponse)
def analyze_single_session(body: SingleSessionRequest,
                          current_user: str = Depends(get_current_user),
                          db: Session = Depends(get_db),
                          x_user_id: str | None = Header(default=None)):
    """Analyze single lab session with multiple tests"""
    user = get_or_create_user(db, x_user_id, "premium")  # Asıl site zaten kontrol ediyor
    
    # FLEXIBLE INPUT HANDLING - Asıl site'dan herhangi bir format gelebilir
    tests_dict = []
    
    # 1. Önce body.session_tests'i dene
    if body.session_tests:
        tests_dict = [test.model_dump() for test in body.session_tests]
    # 2. Yoksa body.tests'i dene
    elif body.tests:
        tests_dict = body.tests
    # 3. Hiçbiri yoksa boş liste
    else:
        tests_dict = []
    
    # 4. Eğer tests_dict boşsa, default test oluştur
    if not tests_dict:
        tests_dict = [
            {
                "name": "Test Sonucu",
                "value": "Veri bulunamadı",
                "unit": "N/A",
                "reference_range": "N/A"
            }
        ]
    
    # Health Guard kaldırıldı - Lab analizi zaten kontrollü içerik üretiyor
    
    # Use parallel single session analysis with flexible input
    session_date = body.session_date or body.date or "2024-01-15"  # Default date
    laboratory = body.laboratory or body.lab or "Laboratuvar"  # Default lab name
    
    res = parallel_single_session_analyze(tests_dict, session_date, laboratory)
    final_json = res["content"]
    data = parse_json_safe(final_json) or {}
    
    # Database kaydı kaldırıldı - Asıl site zaten yapacak
    # Sadece AI yanıtını döndür
    
    return data

@app.post("/ai/lab/summary", response_model=GeneralLabSummaryResponse)
def analyze_multiple_lab_summary(body: MultipleLabRequest,
                                 current_user: str = Depends(get_current_user),
                                 db: Session = Depends(get_db),
                                 x_user_id: str | None = Header(default=None)):
    """Generate general summary of multiple lab tests with supplement recommendations and progress tracking"""
    user = get_or_create_user(db, x_user_id, "premium")  # Asıl site zaten kontrol ediyor
    
    # FLEXIBLE INPUT HANDLING - Asıl site'dan herhangi bir format gelebilir
    tests_dict = []
    
    # 1. Önce body.tests'i dene
    if body.tests:
        tests_dict = [test.model_dump() for test in body.tests]
    # 2. Yoksa body.lab_results'i dene
    elif body.lab_results:
        tests_dict = body.lab_results
    # 3. Hiçbiri yoksa boş liste
    else:
        tests_dict = []
    
    # 4. Eğer tests_dict boşsa, default test oluştur
    if not tests_dict:
        tests_dict = [
            {
                "name": "Test Sonucu",
                "value": "Veri bulunamadı",
                "unit": "N/A",
                "reference_range": "N/A"
            }
        ]
    
    # XML'den supplement listesini al (eğer body'de yoksa)
    supplements_dict = body.available_supplements
    if not supplements_dict:
        # XML'den supplement listesini çek (gerçek veriler)
        from backend.config import SUPPLEMENTS_LIST
        supplements_dict = SUPPLEMENTS_LIST
    
    # Use parallel multiple lab analysis with supplements
    total_sessions = body.total_test_sessions or 1  # Default 1
    res = parallel_multiple_lab_analyze(tests_dict, total_sessions, supplements_dict, body.user_profile)
    final_json = res["content"]
    data = parse_json_safe(final_json) or {}
    
    # Progress analysis kaldırıldı - Asıl site zaten yapacak
    
    # Add metadata for response formatting
    if "test_count" not in data:
        data["test_count"] = total_sessions
    if "overall_status" not in data:
        data["overall_status"] = "analiz_tamamlandı"
    
    # Lab sonuçlarını global context'e ekle (SADECE ÖZET BİLGİLER)
    if data and "test_details" in data:
        from backend.db import get_user_global_context, update_user_global_context, create_lab_test_record, create_ai_interaction
        
        # Mevcut global context'i al
        current_context = get_user_global_context(db, user.id) or {}
        
        # Lab sonuçlarından SADECE ÖZET BİLGİLERİ çıkar
        lab_context = {}
        
        # Test adları - SADECE İLK N TANESİ
        if "test_details" in data:
            test_adlari = list(data["test_details"].keys())
            from backend.config import MAX_LAB_TESTS_IN_CONTEXT
            lab_context["session_anormal_testler"] = test_adlari[:MAX_LAB_TESTS_IN_CONTEXT]
        
        # Genel lab durumu - AI response'a göre ayarla
        if "overall_status" in data:
            lab_context["lab_genel_durum"] = data["overall_status"]
        elif "general_assessment" in data and "overall_health_status" in data["general_assessment"]:
            lab_context["lab_genel_durum"] = data["general_assessment"]["overall_health_status"]
        elif "general_assessment" in data and "overall_summary" in data["general_assessment"]:
            lab_context["lab_genel_durum"] = data["general_assessment"]["overall_summary"]
        elif "general_assessment" in data and "metabolic_status" in data["general_assessment"]:
            lab_context["lab_genel_durum"] = data["general_assessment"]["metabolic_status"]
        
        # Lab tarihi
        import time
        lab_context["lab_tarih"] = time.strftime("%Y-%m-%d")
        
        # Global context'i güncelle
        if lab_context:
            updated_context = {**current_context, **lab_context}
            update_user_global_context(db, user.id, updated_context)
        
        # Database'e lab test kaydı yaz (read-through sistemi için)
        try:
            create_lab_test_record(
                db=db,
                user_id=user.id,
                test_results=tests_dict,
                analysis_result=data,
                test_type="multiple"
            )
            
            # AI interaction kaydı da ekle
            create_ai_interaction(
                db=db,
                user_id=user.id,
                interaction_type="lab_multiple",
                user_input=str(tests_dict),
                ai_response=str(data),
                model_used="parallel_multiple_lab_analyze",
                interaction_metadata={"test_count": total_sessions}
            )
        except Exception as e:
            # Database yazma hatası olsa bile global context güncellendi
            print(f"Lab test database kaydı hatası: {e}")
    
    # Database kaydı tamamlandı - Artık read-through sistemi çalışacak
    
    return data



@app.get("/users/{user_id}/global-context")
def get_user_global_context_endpoint(user_id: str, db: Session = Depends(get_db)):
    """Get user's global context for debugging"""

    from backend.db import get_user_by_external_id, get_user_global_context

    # external_user_id ile kullanıcıyı bul
    user = get_user_by_external_id(db, user_id)
    if not user:
        raise HTTPException(404, "Kullanıcı bulunamadı")

    # Global context'i al
    global_context = get_user_global_context(db, user.id) or {}

    return {
        "user_id": user_id,
        "global_context": global_context,
        "context_keys": list(global_context.keys()) if global_context else []
    }

@app.get("/ai/progress/{user_id}")
def get_user_progress(user_id: str, db: Session = Depends(get_db)):
    """Get user's lab test progress and trends"""
    
    # Get lab test history using external_user_id
    from backend.db import get_lab_test_history, get_user_by_external_id
    
    # external_user_id ile kullanıcıyı bul
    user = get_user_by_external_id(db, user_id)
    if not user:
        raise HTTPException(404, "Kullanıcı bulunamadı")
    
    lab_history = get_lab_test_history(db, user.id, limit=20)
    
    # Analyze trends
    if len(lab_history) < 2:
        return {
            "message": "Progress analizi için en az 2 test gerekli",
            "test_count": len(lab_history),
            "trends": "Trend analizi yapılamaz"
        }
    
    # Real trend analysis - Compare lab results
    trends = {
        "total_tests": len(lab_history),
        "test_frequency": f"Son {len(lab_history)} test yapıldı",
        "improvement_areas": [],
        "stable_areas": [],
        "worsening_areas": []
    }
    
    # Compare test results if we have at least 2 tests
    if len(lab_history) >= 2:
        latest_test = lab_history[0]  # Most recent
        previous_test = lab_history[1]  # Previous
        
        if latest_test.test_results and previous_test.test_results:
            # Extract test names and values for comparison
            latest_results = {}
            previous_results = {}
            
            # Parse test results (handle both list and dict formats)
            if isinstance(latest_test.test_results, list):
                for test in latest_test.test_results:
                    if isinstance(test, dict) and 'name' in test:
                        latest_results[test['name']] = test
            elif isinstance(latest_test.test_results, dict):
                latest_results = latest_test.test_results
                
            if isinstance(previous_test.test_results, list):
                for test in previous_test.test_results:
                    if isinstance(test, dict) and 'name' in test:
                        previous_results[test['name']] = test
            elif isinstance(previous_test.test_results, dict):
                previous_results = previous_test.test_results
            
            # Compare each test
            for test_name in set(latest_results.keys()) & set(previous_results.keys()):
                latest = latest_results[test_name]
                previous = previous_results[test_name]
                
                # Try to extract numeric values for comparison
                try:
                    latest_val = float(str(latest.get('value', '0')).replace(',', ''))
                    previous_val = float(str(previous.get('value', '0')).replace(',', ''))
                    
                    if latest_val > previous_val:
                        trends["improvement_areas"].append(f"{test_name}: {previous_val} → {latest_val} (İyileşme)")
                    elif latest_val < previous_val:
                        trends["worsening_areas"].append(f"{test_name}: {previous_val} → {latest_val} (Bozulma)")
                    else:
                        trends["stable_areas"].append(f"{test_name}: {latest_val} (Stabil)")
                except (ValueError, TypeError):
                    # Non-numeric values, just mark as stable
                    trends["stable_areas"].append(f"{test_name}: Değer karşılaştırılamadı")
    
    # If no trends found, add default message
    if not trends["improvement_areas"] and not trends["worsening_areas"] and not trends["stable_areas"]:
        trends["stable_areas"].append("Trend analizi için yeterli veri yok")
    
    return {
        "user_id": user_id,
        "lab_test_history": [
            {
                "test_date": record.test_date.isoformat(),
                "test_type": record.test_type,
                "test_count": len(record.test_results) if record.test_results else 0
            }
            for record in lab_history
        ],
        "trends": trends,
        "recommendations": "Progress bazlı öneriler"
    }

@app.get("/api/supplements.xml")
@cache_supplements(ttl_seconds=3600)  # 1 saat cache
def get_supplements_xml():
    """XML feed endpoint - Ana site için supplement listesi"""
    from fastapi.responses import Response
    from backend.config import SUPPLEMENTS_LIST
    
    # Gerçek supplement verileri (config'den)
    supplements = SUPPLEMENTS_LIST
    
    # XML oluştur
    xml_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<supplements>
    <total_count>{len(supplements)}</total_count>
    <last_updated>{time.strftime('%Y-%m-%d %H:%M:%S')}</last_updated>
    <products>"""
    
    for supplement in supplements:
        xml_content += f"""
        <product id="{supplement['id']}">
            <name>{supplement['name']}</name>
            <category>{supplement['category']}</category>
            <available>true</available>
        </product>"""
    
    xml_content += """
    </products>
</supplements>"""
    
    return Response(xml_content, media_type="application/xml")


# Production'da cache endpoint'leri güvenlik riski oluşturabilir - kaldırıldı
# @app.get("/cache/stats")
# def get_cache_statistics():
#     """Cache istatistiklerini döndür"""
#     return get_cache_stats()

# @app.get("/cache/clear")
# def clear_all_cache():
#     """Tüm cache'i temizle"""
#     from backend.cache_utils import cache
#     cache.clear()
#     return {"message": "Cache temizlendi", "status": "success"}

# @app.get("/cache/cleanup")
# def cleanup_expired_cache():
#     """Expired cache item'ları temizle"""
#     from backend.cache_utils import cleanup_cache
#     removed_count = cleanup_cache()
#     return {"message": f"{removed_count} expired item temizlendi", "status": "success"}

@app.get("/users/{external_user_id}/info")
def get_user_info(external_user_id: str, db: Session = Depends(get_db)):
    """Kullanıcı bilgilerini getir (production için test)"""
    from backend.db import get_user_by_external_id
    
    user = get_user_by_external_id(db, external_user_id)
    if not user:
        raise HTTPException(404, "Kullanıcı bulunamadı")
    
    return {
        "user_id": user.id,
        "external_user_id": user.external_user_id,
        "plan": user.plan,
        "conversation_count": len(user.conversations),
        "created_at": user.created_at.isoformat(),
        "global_context_keys": list(user.global_context.keys()) if user.global_context else []
    }

# Global error handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global error handler for production"""
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": "Bir hata oluştu. Lütfen daha sonra tekrar deneyin.",
            "type": str(type(exc).__name__)
        }
    )

# Input validation helper
def validate_input_data(data: dict, required_fields: list = None) -> dict:
    """Input data validation for production - TAMAMEN ESNEK"""
    if not data:
        data = {}
    
    # Required fields için default değer ata (ama strict validation yapma)
    if required_fields:
        for field in required_fields:
            if field not in data:
                data[field] = None
    
    # Her türlü input'u kabul et (string, int, float, dict, list)
    # Pydantic schema'lar zaten extra = "allow" ile esnek
    return data