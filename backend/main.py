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
import requests
import xml.etree.ElementTree as ET

from backend.config import ALLOWED_ORIGINS, CHAT_HISTORY_MAX, FREE_ANALYZE_LIMIT
from backend.db import Base, engine, SessionLocal, create_ai_message, get_user_ai_messages, get_user_ai_messages_by_type, get_or_create_user_by_external_id
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


def validate_chat_user_id(user_id: str, user_plan: str) -> bool:
    """Chat için user ID validasyonu (Free: Session ID, Premium: Real ID)"""
    if user_plan in ['premium', 'premium_plus']:
        # Premium için session ID kabul etme
        return not user_id.startswith('session-')
    else:
        # Free için her türlü ID kabul et
        return True

def get_xml_products():
    """XML'den 74 ürünü çek - Free kullanıcılar için"""
    try:
        response = requests.get('https://s2.digitalfikirler.com/longopass/Longopass-DF-quiz-urunler.xml', timeout=10)
        root = ET.fromstring(response.text)
        products = []
        for item in root.findall('.//item'):
            label_elem = item.find('label')
            if label_elem is not None and label_elem.text:
                # CDATA içeriğini temizle
                product_name = label_elem.text.strip()
                products.append({'name': product_name})
        print(f"🔍 DEBUG: XML'den {len(products)} ürün çekildi")
        return products
    except Exception as e:
        print(f"🔍 DEBUG: XML ürünleri çekme hatası: {e}")
        return []

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
    allow_origins=["*"],  # Geçici olarak tüm origin'lere izin ver
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],  # OPTIONS for CORS preflight
    allow_headers=["*"],
)

# Serve widget js and static frontend
app.mount("/widget", StaticFiles(directory="backend/widget"), name="widget")

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

# Global free user conversation memory (basit dict)
free_user_conversations = {}
import time

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
    
    # Free user conversation memory'yi başlat (timestamp ile)
    if x_user_id not in free_user_conversations:
        free_user_conversations[x_user_id] = {
            "messages": [],
            "last_activity": time.time()
        }
    
    # Eski session'ları temizle (2 saatten eski)
    current_time = time.time()
    expired_users = []
    for user_id, data in free_user_conversations.items():
        if current_time - data["last_activity"] > 7200:  # 2 saat = 7200 saniye
            expired_users.append(user_id)
    
    for user_id in expired_users:
        del free_user_conversations[user_id]
        print(f"🔍 DEBUG: Eski session temizlendi: {user_id}")
    
    # Son aktivite zamanını güncelle
    free_user_conversations[x_user_id]["last_activity"] = current_time
    
    # Health Guard ile kategori kontrolü - SIKI KONTROL
    message_text = req.text or req.message
    if not message_text:
        raise HTTPException(400, "Mesaj metni gerekli")
    
    ok, msg = guard_or_message(message_text)
    if not ok:
        # User mesajını memory'ye ekle
        free_user_conversations[x_user_id]["messages"].append({"role": "user", "content": message_text})
        # AI yanıtını memory'ye ekle
        free_user_conversations[x_user_id]["messages"].append({"role": "assistant", "content": msg})
        # Log to ai_messages
        try:
            create_ai_message(
                db=db,
                external_user_id=x_user_id,
                message_type="chat",
                request_payload={"message": message_text, "conversation_id": 1},
                response_payload={"reply": msg, "conversation_id": 1},
                model_used="health_guard"
            )
        except Exception as e:
            print(f"🔍 DEBUG: Chat ai_messages kaydı hatası: {e}")
        
        return ChatResponse(conversation_id=1, reply=msg, latency_ms=0)
    
    # Ekstra kontrol: Sağlık/supplement dışı konuları reddet
    txt = message_text.lower().strip()
    off_topic_keywords = [
        "hava durumu", "spor", "futbol", "film", "müzik", "oyun", "teknoloji",
        "siyaset", "ekonomi", "haber", "eğlence", "seyahat", "alışveriş"
    ]
    
    if any(keyword in txt for keyword in off_topic_keywords):
        reply = "Üzgünüm, sağlık, supplement ve laboratuvar konularında yardımcı olabilirim. Size sağlık konusunda nasıl yardımcı olabilirim?"
        # User mesajını memory'ye ekle
        free_user_conversations[x_user_id]["messages"].append({"role": "user", "content": message_text})
        # AI yanıtını memory'ye ekle
        free_user_conversations[x_user_id]["messages"].append({"role": "assistant", "content": reply})
        return ChatResponse(conversation_id=1, reply=reply, latency_ms=0)
    
    # Selamlama kontrolü
    txt = message_text.lower().strip()
    pure_greeting_keywords = [
        "selam", "naber", "günaydın", "gunaydin",
        "iyi akşamlar", "iyi aksamlar", "iyi geceler", "iyi günler", "iyi gunler"
    ]
    
    if any(kw == txt for kw in pure_greeting_keywords):
        reply = "Merhaba! Ben Longo AI. Sağlık, supplement ve laboratuvar konularında yardımcı olabilirim. Size nasıl yardımcı olabilirim?"
        # User mesajını memory'ye ekle
        free_user_conversations[x_user_id]["messages"].append({"role": "user", "content": message_text})
        # AI yanıtını memory'ye ekle
        free_user_conversations[x_user_id]["messages"].append({"role": "assistant", "content": reply})
        return ChatResponse(conversation_id=1, reply=reply, latency_ms=0)
    
    # AI yanıtı için OpenRouter kullan
    try:
        from backend.openrouter_client import get_ai_response
        
        # Free kullanıcılar için güzel prompt
        system_prompt = """Sen Longo AI'sın - sağlık ve supplement konularında yardımcı olan dost canlısı bir asistan. 

🎯 GÖREVİN: Sadece sağlık, supplement, beslenme ve laboratuvar konularında yanıt ver.


🚫 KISITLAMALAR: 
- Sağlık dışında konulardan bahsetme
- Off-topic soruları kibarca sağlık alanına yönlendir
- Kaynak link'leri veya referans'lar ekleme
- Web sitelerinden link verme
- Liste hakkında konuşma (kullanıcı listeyi görmemeli)

✨ SAĞLIK ODAĞI: Her konuyu sağlık alanına çek. Kullanıcı başka bir şeyden bahsederse, nazikçe sağlık konusuna yönlendir.

💡 YANIT STİLİ: Kısa, net ve anlaşılır ol. Sadece sağlık konusuna odaklan!

🎯 ÜRÜN ÖNERİSİ: SADECE kullanıcı açıkça "supplement öner", "ne alayım", "hangi ürünleri alayım" gibi öneri isterse ya da bir şikayeti varsa öner. Diğer durumlarda öneri yapma! Liste hakkında konuşma! Konuşmanın devamlılığını sağla, sürekli "ne önermemi istersin?" sorma!

🚫 KESIN KURALLAR:
- SADECE kullanıcı açıkça öneri isterse ya da bir şikayeti varsa supplement öner
- Kullanıcı sormadan supplement önerisi yapma
- SADECE aşağıdaki listedeki ürünleri öner
- Liste dışından hiçbir ürün önerme
- Sağlık ve supplement dışında hiçbir konuşma yapma
- Off-topic soruları kesinlikle reddet
- Web sitelerinden link verme
- Liste hakkında konuşma (kullanıcı listeyi görmemeli)
- Liste hakkında konuşma! Kullanıcı listeyi vermiyor, ona söyleme! "Senin listende", "listende var" gibi ifadeler kullanma
- "Senin verdiğin liste" gibi ifadeler kullanma
- Sürekli "ne önermemi istersin?" sorma, konuşmanın devamlılığını sağla
- Sadece ürün isimlerini öner, açıklama yapma"""
        
        # XML'den ürünleri çek
        xml_products = get_xml_products()
        
        # Conversation history'yi al (son 5 mesaj)
        conversation_history = free_user_conversations[x_user_id]["messages"][-10:] if len(free_user_conversations[x_user_id]["messages"]) > 0 else []
        
        # Kullanıcı mesajını hazırla
        user_message = message_text
        
        # Conversation history'yi context olarak ekle
        if conversation_history:
            context_message = "\n\n=== KONUŞMA GEÇMİŞİ ===\n"
            for msg in conversation_history[-5:]:  # Son 5 mesajı al
                context_message += f"{msg['role'].upper()}: {msg['content']}\n"
            user_message = context_message + "\n" + user_message
            print(f"🔍 DEBUG: Free kullanıcı için {len(conversation_history)} mesaj geçmişi eklendi")
        
        # XML ürünlerini user message'a ekle
        if xml_products:
            user_message += f"\n\n🚨 SADECE BU ÜRÜNLERİ ÖNER ({len(xml_products)} ürün):\n"
            for i, product in enumerate(xml_products, 1):
                user_message += f"{i}. {product['name']}\n"
            user_message += "\n🚨 ÖNEMLİ: SADECE yukarıdaki listedeki ürünleri öner! Başka hiçbir ürün önerme! Kullanıcının ihtiyacına göre 3-5 ürün seç! Liste hakkında konuşma! Link verme!"
            print(f"🔍 DEBUG: Free kullanıcı için {len(xml_products)} XML ürünü eklendi")
        
        ai_response = await get_ai_response(
            system_prompt=system_prompt,
            user_message=user_message,
            model="openai/gpt-5-chat:online"  # Tüm kullanıcılar için aynı kalite
        )
        
        # AI yanıtını al
        reply = ai_response
        
        # User mesajını memory'ye ekle
        free_user_conversations[x_user_id]["messages"].append({"role": "user", "content": message_text})
        # AI yanıtını memory'ye ekle
        free_user_conversations[x_user_id]["messages"].append({"role": "assistant", "content": reply})
        
        return ChatResponse(conversation_id=1, reply=reply, latency_ms=0)
        
    except Exception as e:
        print(f"Free user chat error: {e}")
        reply = "Üzgünüm, şu anda yanıt veremiyorum. Lütfen daha sonra tekrar deneyin."
        # User mesajını memory'ye ekle
        free_user_conversations[x_user_id]["messages"].append({"role": "user", "content": message_text})
        # AI yanıtını memory'ye ekle
        free_user_conversations[x_user_id]["messages"].append({"role": "assistant", "content": reply})
        return ChatResponse(conversation_id=1, reply=reply, latency_ms=0)

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
    
    # Premium kullanıcılar için yeni conversation ID oluştur
    user = get_or_create_user(db, x_user_id, user_plan)
    
    # Yeni conversation ID oluştur (timestamp-based)
    import time
    new_conversation_id = int(time.time() * 1000)  # Millisecond timestamp
    
    return ChatStartResponse(conversation_id=new_conversation_id)

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
    
    # Sadece bu conversation'a ait chat mesajlarını al
    chat_messages = get_user_ai_messages_by_type(db, x_user_id, "chat", limit=CHAT_HISTORY_MAX)
    
    # ai_messages formatını chat history formatına çevir
    history = []
    for msg in chat_messages:
        if msg.request_payload and "message" in msg.request_payload and msg.request_payload.get("conversation_id") == conversation_id:
            # User message
            history.append({
                "role": "user", 
                "content": msg.request_payload["message"], 
                "ts": msg.created_at.isoformat()
            })
        if msg.response_payload and "reply" in msg.response_payload:
            # Assistant message
            history.append({
                "role": "assistant", 
                "content": msg.response_payload["reply"], 
                "ts": msg.created_at.isoformat()
            })
    
    return history[-CHAT_HISTORY_MAX:]

@app.post("/ai/chat", response_model=ChatResponse)
async def chat_message(req: ChatMessageRequest,
                  current_user: str = Depends(get_current_user),
                  db: Session = Depends(get_db),
                  x_user_id: str | None = Header(default=None),
                  x_user_plan: str | None = Header(default=None),
                  x_user_level: int | None = Header(default=None)):
    
    # Plan kontrolü - Yeni sistem: userLevel bazlı
    if x_user_level is not None:
        if x_user_level == 0 or x_user_level == 1:
            user_plan = "free"
        elif x_user_level == 2:
            user_plan = "premium"
        elif x_user_level == 3:
            user_plan = "premium_plus"
        else:
            user_plan = "free"  # Default fallback
    else:
        # Eski sistem fallback
        user_plan = x_user_plan or "free"
    
    is_premium = user_plan in ["premium", "premium_plus"]
    
    # User ID validasyonu (Free: Session ID, Premium: Real ID)
    if not validate_chat_user_id(x_user_id or "", user_plan):
        raise HTTPException(status_code=400, detail="Premium kullanıcılar için gerçek user ID gerekli")
    
    # Free kullanıcılar için session-based chat
    if not is_premium:
        return await handle_free_user_chat(req, x_user_id)
    
    # Premium kullanıcılar için database-based chat
    user = get_or_create_user_by_external_id(db, x_user_id, user_plan)

    # FLEXIBLE INPUT HANDLING - Asıl site'dan herhangi bir format gelebilir
    conversation_id = req.conversation_id or req.conv_id
    if not conversation_id:
        raise HTTPException(400, "Conversation ID gerekli")
    
    # Conversation ID artık sadece referans için kullanılıyor

    
    # FLEXIBLE INPUT HANDLING - Asıl site'dan herhangi bir format gelebilir
    message_text = req.text or req.message
    if not message_text:
        raise HTTPException(400, "Mesaj metni gerekli")
    
    # Health Guard ile kategori kontrolü
    ok, msg = guard_or_message(message_text)
    
    # Hafıza soruları artık HEALTH kategorisinde, özel işlem yok
    memory_bypass = False
    if not ok:
        # Fixed message - sadece ai_messages'a kaydedilecek
        reply = msg
        return ChatResponse(conversation_id=conversation_id, reply=reply, latency_ms=0)
    
    # Hafıza soruları artık normal AI model ile yanıtlanıyor
    
    # Selamlama sonrası özel yanıt kontrolü
    txt = message_text.lower().strip()
    pure_greeting_keywords = [
        "selam", "naber", "günaydın", "gunaydin",
        "iyi akşamlar", "iyi aksamlar", "iyi geceler", "iyi günler", "iyi gunler"
    ]
    
    # Eğer saf selamlama ise özel yanıt ver
    if any(kw == txt for kw in pure_greeting_keywords):
        reply = "Merhaba! Ben Longo AI. Sağlık, supplement ve laboratuvar konularında yardımcı olabilirim. Size nasıl yardımcı olabilirim?"
        return ChatResponse(conversation_id=conversation_id, reply=reply, latency_ms=0)

    # Chat history'yi ai_messages'tan al (Message tablosu yerine)
    chat_messages = get_user_ai_messages_by_type(db, x_user_id, "chat", limit=10)
    
    # ai_messages formatını history formatına çevir
    rows = []
    for msg in chat_messages:
        if msg.request_payload and "message" in msg.request_payload:
            rows.append({"role": "user", "content": msg.request_payload["message"], "created_at": msg.created_at})
        if msg.response_payload and "reply" in msg.response_payload:
            rows.append({"role": "assistant", "content": msg.response_payload["reply"], "created_at": msg.created_at})
    
    # Get user's previous analyses for context (CACHE THIS!)
    user_analyses = get_user_ai_messages(db, x_user_id, limit=5)
    
    # Global + Local Context Sistemi - OPTIMIZED
    user_context = {}
    
    
    # Lab verilerini user message'a da ekle (AI'nin kesinlikle görmesi için)
    lab_info = ""
    
    # Önce global context'ten dene
    if user_context and "son_lab_test" in user_context and user_context["son_lab_test"]:
        lab_info = f"🚨 LAB SONUÇLARI (KULLANICI VERİSİ):\n"
        lab_info += f"SON LAB TEST: {user_context['son_lab_test']}\n"
        
        if "son_lab_deger" in user_context and user_context["son_lab_deger"]:
            lab_info += f"SON LAB DEĞER: {user_context['son_lab_deger']}\n"
            
        if "son_lab_durum" in user_context and user_context["son_lab_durum"]:
            lab_info += f"SON LAB DURUM: {user_context['son_lab_durum']}\n"
            
        if "lab_tarih" in user_context and user_context["lab_tarih"]:
            lab_info += f"LAB TARİH: {user_context['lab_tarih']}\n"
        
        lab_info += "\n"
        print(f"🔍 DEBUG: Lab verileri global context'ten user message'a eklendi!")
    
    # Global context'te yoksa ai_messages'tan al
    if not lab_info and user_analyses:
        lab_analyses = [a for a in user_analyses if a.message_type == "lab_single"]
        if lab_analyses:
            latest_lab = lab_analyses[0]  # En son lab
            if latest_lab.response_payload and "test_name" in latest_lab.response_payload:
                lab_info = f"🚨 LAB SONUÇLARI (KULLANICI VERİSİ):\n"
                lab_info += f"SON LAB TEST: {latest_lab.response_payload['test_name']}\n"
                if "last_result" in latest_lab.response_payload:
                    lab_info += f"SON LAB DEĞER: {latest_lab.response_payload['last_result']}\n"
                lab_info += "\n"
                print(f"🔍 DEBUG: Lab verileri ai_messages'tan user message'a eklendi!")
    
    # Quiz verilerini user message'a da ekle (AI'nin kesinlikle görmesi için)
    quiz_info = ""
    if user_analyses:
        quiz_analyses = [a for a in user_analyses if a.message_type == "quiz"]
        if quiz_analyses:
            latest_quiz = quiz_analyses[0]  # En son quiz
            if latest_quiz.response_payload and "supplement_recommendations" in latest_quiz.response_payload:
                supplements = [s["name"] for s in latest_quiz.response_payload["supplement_recommendations"][:3]]
                quiz_info = f"🚨 QUIZ SONUÇLARI (KULLANICI VERİSİ):\n"
                quiz_info += f"ÖNERİLEN SUPPLEMENTLER: {', '.join(supplements)}\n\n"
                print(f"🔍 DEBUG: Quiz verileri user message'a da eklendi!")
    
    # Lab ve quiz bilgileri artık ai_messages'a kaydedilecek
    if lab_info or quiz_info:
        enhanced_message = message_text
        if lab_info:
            enhanced_message = lab_info + enhanced_message
        if quiz_info:
            enhanced_message = quiz_info + enhanced_message
        print(f"🔍 DEBUG: User message lab/quiz bilgileri ile güncellendi!")
    
    # Build enhanced system prompt with user context
    system_prompt = "Sen Longo AI'sın. SADECE sağlık/supplement/lab konularında yanıt ver. Off-topic'te kibarca reddet. KAYNAK EKLEME: Otomatik olarak kaynak link'leri, referans'lar veya citation'lar ekleme!\n\nÖNEMLİ: Eğer kullanıcı bilgileri (isim, yaş, hastalık vb.) aşağıda verilmişse, bunları kullan ve hatırladığını göster.\n\n🚨 SAĞLIK YÖNLENDİRME KURALI: Her konuyu sağlık ve supplement alanına çek! Kullanıcı off-topic bir şey söylerse, kibarca sağlık konusuna yönlendir ve supplement önerisi yap!\n\n❌ OFF-TOPIC BİLGİ VERME: Sağlık dışında konularda bilgi verme ve detaya girme! Kısa ve net cevaplar ver,Sadece sağlık konusuna odaklan!"
    
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
            # Local context'i güncelle
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
        
        # Lab verilerini de göster - LAB SUMMARY BİLGİLERİ
        if "lab_gecmisi" in user_context and user_context["lab_gecmisi"]:
            system_prompt += f"LAB TEST GEÇMİŞİ (Son 1 Yıl):\n"
            for i, lab in enumerate(user_context["lab_gecmisi"], 1):
                system_prompt += f"{i}. {lab.get('ozet', '')}\n"
            print(f"🔍 DEBUG: Lab geçmişi eklendi: {len(user_context['lab_gecmisi'])} test")
        
        # Lab summary bilgileri (en güncel)
        if "lab_genel_durum" in user_context and user_context["lab_genel_durum"]:
            system_prompt += f"\nLAB GENEL DURUM: {user_context['lab_genel_durum']}\n"
            print(f"🔍 DEBUG: Lab genel durum eklendi: {user_context['lab_genel_durum']}")
            
        if "lab_summary" in user_context and user_context["lab_summary"]:
            system_prompt += f"LAB ÖZET: {user_context['lab_summary']}\n"
            print(f"🔍 DEBUG: Lab özet eklendi: {user_context['lab_summary']}")
        
        if "lab_tarih" in user_context and user_context["lab_tarih"]:
            system_prompt += f"LAB TARİH: {user_context['lab_tarih']}\n"
            print(f"🔍 DEBUG: Lab tarih eklendi: {user_context['lab_tarih']}")
            
        print(f"🔍 DEBUG: Final system prompt lab verileri ile hazırlandı!")
        system_prompt += "\nÖNEMLİ: Bu bilgileri kesinlikle hatırla! Kullanıcı sana adını, yaşını, hastalığını veya lab sonuçlarını sorduğunda yukarıdaki bilgilerle cevap ver!"
    else:
        # Context yoksa default prompt ekle
        print(f"🔍 DEBUG: User context boş, default prompt kullanılıyor!")
        system_prompt += "\n\nGenel sağlık ve supplement konularında yardımcı ol. Kullanıcı bilgileri yoksa genel öneriler ver ve listeden mantıklı ürün öner.\n\n🍎 BESLENME ÖNERİSİ KURALLARI:\n- Kullanıcı 'beslenme önerisi ver' derse, SADECE beslenme tavsiyeleri ver!\n- Beslenme önerisi istenince supplement önerme!\n- Sadece doğal besinler, yemek önerileri, beslenme programı ver!\n- Supplement önerisi sadece kullanıcı özel olarak 'supplement öner' derse yap!"
    
    # User analyses context - OPTIMIZED (only add if exists)
    if user_analyses:
        system_prompt += "\n\nKULLANICI GEÇMİŞİ:\n"
        for analysis in user_analyses:
            if analysis.message_type in ["quiz", "lab_single", "lab_session", "lab_summary"]:
                system_prompt += f"- {analysis.message_type.upper()}: {analysis.created_at.strftime('%Y-%m-%d')}\n"
                # Analiz içeriğini de ekle
                if analysis.response_payload:
                    if analysis.message_type == "quiz" and "supplement_recommendations" in analysis.response_payload:
                        supplements = [s["name"] for s in analysis.response_payload["supplement_recommendations"][:3]]
                        system_prompt += f"  Önerilen supplementler: {', '.join(supplements)}\n"
                    elif analysis.message_type == "lab_single" and "test_name" in analysis.response_payload:
                        system_prompt += f"  Test: {analysis.response_payload['test_name']}\n"
        system_prompt += "\nBu bilgileri kullanarak daha kişiselleştirilmiş yanıtlar ver."

    # XML'den supplement listesini ekle - AI'ya ürün önerileri için
    from backend.config import SUPPLEMENTS_LIST
    supplements_list = SUPPLEMENTS_LIST
    
    # Supplement listesi kuralları (quiz'deki gibi)
    system_prompt += "\n- Sakın ürünlerin id'lerini kullanıcıya gösterme!"
    system_prompt += "\n- Liste hakkında konuşma! Kullanıcı listeyi vermiyor, ona söyleme! 'Senin listende', 'listende var' gibi ifadeler kullanma!"
    system_prompt += "\n- Otomatik olarak kaynak link'leri, referans'lar veya citation'lar ekleme!"
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
    system_prompt += "\n- Boşuna supplement önerme! Sadece gerçekten işe yarayacak olanları öner!\n- Kullanıcıya hiçbir şekilde ihtiyacı olmayan supplement önerme!\n- Kullanıcının yaşı, cinsiyeti, sağlık durumu, alerjileri, kullandığı ilaçlar dikkate al!\n- Riskli durumlar varsa o supplement'i önerme!\n- Kullanıcı özel olarak supplement istemiyorsa, sadece gerçekten gerekli olanları öner!"
    system_prompt += "\n- E-ticaret stratejisi: 4 DEFAULT + 2-3 PROBLEME ÖZEL = 6-7 Supplement!"
    system_prompt += "\n- Değerler iyiyse Longevity, kötüyse problem çözücü öner!"
    
    # Lab verilerini user message'a da ekle (AI'nin kesinlikle görmesi için)
    lab_info = ""
    if user_context and "son_lab_test" in user_context and user_context["son_lab_test"]:
        lab_info = f"🚨 LAB SONUÇLARI (KULLANICI VERİSİ):\n"
        lab_info += f"SON LAB TEST: {user_context['son_lab_test']}\n"
        
        if "son_lab_deger" in user_context and user_context["son_lab_deger"]:
            lab_info += f"SON LAB DEĞER: {user_context['son_lab_deger']}\n"
            
        if "son_lab_durum" in user_context and user_context["son_lab_durum"]:
            lab_info += f"SON LAB DURUM: {user_context['son_lab_durum']}\n"
            
        if "lab_tarih" in user_context and user_context["lab_tarih"]:
            lab_info += f"LAB TARİH: {user_context['lab_tarih']}\n"
        
        lab_info += "\n"
        print(f"🔍 DEBUG: Lab verileri user message'a da eklendi!")
    
    # Quiz verilerini user message'a da ekle (AI'nin kesinlikle görmesi için)
    quiz_info = ""
    if user_analyses:
        quiz_analyses = [a for a in user_analyses if a.message_type == "quiz"]
        if quiz_analyses:
            latest_quiz = quiz_analyses[0]  # En son quiz
            if latest_quiz.response_payload and "supplement_recommendations" in latest_quiz.response_payload:
                supplements = [s["name"] for s in latest_quiz.response_payload["supplement_recommendations"][:3]]
                quiz_info = f"🚨 QUIZ SONUÇLARI (KULLANICI VERİSİ):\n"
                quiz_info += f"ÖNERİLEN SUPPLEMENTLER: {', '.join(supplements)}\n\n"
                print(f"🔍 DEBUG: Quiz verileri user message'a da eklendi!")
    
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
            supplements_info += f"  {i}. {supplement['name']}\n"
        supplements_info += "\n"
    
    supplements_info += "🚨 ÖNEMLİ: SADECE yukarıdaki listedeki ürünleri öner! Başka hiçbir ürün önerme! Kullanıcının ihtiyacına göre 3-5 ürün seç! Liste hakkında konuşma! Kullanıcı listeyi vermiyor, ona söyleme! 'Senin için listedeki', 'listede var', 'Senin listende' gibi ifadeler kullanma! Link verme! Ürün ID'lerini kullanıcıya gösterme!\n\n🎯 SUPPLEMENT ÖNERİSİ KURALLARI:\n- SADECE kullanıcının gerçek ihtiyacı olan supplementleri öner!\n- Kullanıcıya hiçbir şekilde ihtiyacı olmayan supplement önerme!\n- Kullanıcının yaşı, cinsiyeti, sağlık durumu, alerjileri, kullandığı ilaçlar dikkate al!\n- Riskli durumlar varsa o supplement'i önerme!\n- Kullanıcı özel olarak supplement istemiyorsa, sadece gerçekten gerekli olanları öner!\n- Boşuna supplement önerme! Sadece gerçekten işe yarayacak olanları öner!"
    
    # Context'i ilk message'a ekle
    
    # System message
    print(f"🔍 DEBUG: Final system prompt:")
    print(f"🔍 DEBUG: {system_prompt}")
    print(f"🔍 DEBUG: Prompt uzunluğu: {len(system_prompt)} karakter")
    
    history = [{"role": "system", "content": system_prompt, "context_data": user_context}]
    
    # Lab verilerini user message olarak ekle (AI'nin kesinlikle görmesi için)
    if lab_info:
        history.append({"role": "user", "content": lab_info})
        print(f"🔍 DEBUG: Lab user message history'e eklendi!")
    
    # Supplement listesi user message olarak ekle (quiz'deki gibi)
    history.append({"role": "user", "content": supplements_info})
    
    # Quiz ve Lab verilerini ai_messages'tan çek ve AI'ya gönder
    quiz_messages = get_user_ai_messages_by_type(db, x_user_id, "quiz", limit=5)
    lab_single_messages = get_user_ai_messages_by_type(db, x_user_id, "lab_single", limit=5)
    lab_session_messages = get_user_ai_messages_by_type(db, x_user_id, "lab_session", limit=5)
    lab_summary_messages = get_user_ai_messages_by_type(db, x_user_id, "lab_summary", limit=5)
    
    # Quiz verilerini ekle
    if quiz_messages:
        quiz_info = "\n\n=== QUIZ BİLGİLERİ ===\n"
        for msg in quiz_messages:
            if msg.response_payload and "supplement_recommendations" in msg.response_payload:
                quiz_info += f"QUIZ TARİHİ: {msg.created_at.strftime('%Y-%m-%d')}\n"
                quiz_info += f"QUIZ SONUÇLARI: {msg.response_payload.get('nutrition_advice', {}).get('recommendations', [])}\n"
                quiz_info += f"ÖNERİLEN SUPPLEMENTLER: {[s.get('name', '') for s in msg.response_payload.get('supplement_recommendations', [])]}\n\n"
        history.append({"role": "user", "content": quiz_info})
        print(f"🔍 DEBUG: Quiz bilgileri user message'a eklendi")
    
    # Lab verilerini ekle
    lab_info = "\n\n=== LAB BİLGİLERİ ===\n"
    
    # Lab Single verileri
    if lab_single_messages:
        lab_info += "LAB TEST SONUÇLARI:\n"
        for msg in lab_single_messages:
            if msg.request_payload and "test" in msg.request_payload:
                test = msg.request_payload["test"]
                lab_info += f"- {test.get('name', '')}: {test.get('value', '')} {test.get('unit', '')} (Referans: {test.get('reference_range', '')})\n"
    
    # Lab Session verileri
    if lab_session_messages:
        lab_info += "\nLAB SEANS SONUÇLARI:\n"
        for msg in lab_session_messages:
            if msg.request_payload and "session_tests" in msg.request_payload:
                for test in msg.request_payload["session_tests"]:
                    lab_info += f"- {test.get('name', '')}: {test.get('value', '')} {test.get('unit', '')} (Referans: {test.get('reference_range', '')})\n"
    
    # Lab Summary verileri
    if lab_summary_messages:
        lab_info += "\nLAB ÖZET ANALİZLERİ:\n"
        for msg in lab_summary_messages:
            if msg.response_payload:
                lab_info += f"GENEL DURUM: {msg.response_payload.get('genel_saglik_durumu', '')}\n"
                lab_info += f"ÖNERİLER: {msg.response_payload.get('oneriler', [])}\n"
                lab_info += f"ÖNERİLEN SUPPLEMENTLER: {[s.get('name', '') for s in msg.response_payload.get('urun_onerileri', [])]}\n\n"
    
    if lab_info != "\n\n=== LAB BİLGİLERİ ===\n":
        history.append({"role": "user", "content": lab_info})
        print(f"🔍 DEBUG: Lab bilgileri user message'a eklendi")
    
    # Chat history
    for r in rows[-(CHAT_HISTORY_MAX-1):]:
        history.append({"role": r["role"], "content": r["content"]})

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
    
    # Assistant message artık ai_messages'a kaydedilecek
    
    # AI interaction kaydı kaldırıldı - create_ai_message kullanılıyor
    
    
    # Database kaydı kaldırıldı - Asıl site zaten yapacak
    # Sadece chat yanıtını döndür
    
    # Log to ai_messages
    try:
        create_ai_message(
            db=db,
            external_user_id=x_user_id,
            message_type="chat",
            request_payload={"message": message_text, "conversation_id": conversation_id},
            response_payload={"reply": final, "conversation_id": conversation_id},
            model_used="openrouter"
        )
    except Exception as e:
        print(f"🔍 DEBUG: Chat ai_messages kaydı hatası: {e}")
    
    return ChatResponse(conversation_id=conversation_id, reply=final, latency_ms=latency_ms)

# ---------- ANALYZE (FREE: one-time), LAB ----------


@app.post("/ai/quiz", response_model=QuizResponse)
async def analyze_quiz(body: QuizRequest,
                 current_user: str = Depends(get_current_user),
                 db: Session = Depends(get_db),
                 x_user_id: str | None = Header(default=None),
                 x_user_plan: str | None = Header(default=None),
                 x_user_level: int | None = Header(default=None)):
    """Quiz endpoint - Sadece AI model işlemi, asıl site entegrasyonu için optimize edildi"""
    
    # Plan kontrolü - Yeni sistem: userLevel bazlı
    if x_user_level is not None:
        if x_user_level == 0 or x_user_level == 1:
            user_plan = "free"
        elif x_user_level == 2:
            user_plan = "premium"
        elif x_user_level == 3:
            user_plan = "premium_plus"
        else:
            user_plan = "free"  # Default fallback
    else:
        # Eski sistem fallback
        user_plan = x_user_plan or "free"
    
    user = get_or_create_user(db, x_user_id, user_plan)
    
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
    
    
    # Log to ai_messages
    try:
        create_ai_message(
                db=db,
            external_user_id=x_user_id,
            message_type="quiz",
            request_payload=body.dict(),
            response_payload=data,
            model_used="openrouter"
        )
    except Exception as e:
        print(f"🔍 DEBUG: Quiz ai_messages kaydı hatası: {e}")
    
    # Return quiz response
    
    # Return quiz response
    return data

@app.post("/ai/lab/single", response_model=LabAnalysisResponse)
def analyze_single_lab(body: SingleLabRequest,
                        current_user: str = Depends(get_current_user),
                       db: Session = Depends(get_db),
                        x_user_id: str | None = Header(default=None),
                        x_user_plan: str | None = Header(default=None),
                        x_user_level: int | None = Header(default=None)):
    """Analyze single lab test result with historical trend analysis"""
    
    # Plan kontrolü - Yeni sistem: userLevel bazlı
    if x_user_level is not None:
        if x_user_level == 0 or x_user_level == 1:
            user_plan = "free"
        elif x_user_level == 2:
            user_plan = "premium"
        elif x_user_level == 3:
            user_plan = "premium_plus"
        else:
            user_plan = "free"  # Default fallback
    else:
        # Eski sistem fallback
        user_plan = x_user_plan or "premium"
    
    user = get_or_create_user(db, x_user_id, user_plan)
    
    # Convert test to dict for processing
    test_dict = body.test.model_dump()
    
    # Test verisi validation
    if not test_dict:
        raise HTTPException(400, "Test verisi boş olamaz.")
    
    # Gerekli field'ları kontrol et
    required_fields = ['name', 'value']
    for field in required_fields:
        if field not in test_dict or not test_dict[field]:
            raise HTTPException(400, f"Test verisinde '{field}' field'ı gerekli ve boş olamaz.")
    
    # YENİ: Geçmiş sonuçları ai_messages tablosundan topla (yalnızca ham test değerleri)
    from backend.db import get_ai_messages
    historical_results = []
    current_test_name = (test_dict.get('name') or '').lower().strip()

    try:
        # Son 50 ai_messages kaydını al ve gez
        prior_msgs = get_ai_messages(db, external_user_id=x_user_id, limit=50)
        for msg in prior_msgs:
            if not msg or not msg.request_payload:
                continue
            payload = msg.request_payload
            msg_date = msg.created_at.isoformat() if getattr(msg, 'created_at', None) else None

            # lab_single: payload.test
            if msg.message_type == 'lab_single' and isinstance(payload.get('test'), dict):
                pt = payload['test']
                if (pt.get('name') or '').lower().strip() == current_test_name:
                    item = {
                        'name': pt.get('name'),
                        'value': pt.get('value'),
                        'unit': pt.get('unit'),
                        'reference_range': pt.get('reference_range'),
                        'status': pt.get('status'),
                        'date': msg_date,
                    }
                    historical_results.append(item)

            # lab_session: payload.session_tests veya payload.tests
            elif msg.message_type == 'lab_session':
                tests_list = []
                if isinstance(payload.get('session_tests'), list):
                    tests_list = payload['session_tests']
                elif isinstance(payload.get('tests'), list):
                    tests_list = payload['tests']
                for pt in tests_list:
                    if isinstance(pt, dict) and (pt.get('name') or '').lower().strip() == current_test_name:
                        item = {
                            'name': pt.get('name'),
                            'value': pt.get('value'),
                            'unit': pt.get('unit'),
                            'reference_range': pt.get('reference_range'),
                            'status': pt.get('status'),
                            'date': msg_date,
                        }
                        historical_results.append(item)

            # lab_summary: payload.tests veya payload.lab_results
            elif msg.message_type == 'lab_summary':
                tests_list = []
                if isinstance(payload.get('tests'), list):
                    tests_list = payload['tests']
                elif isinstance(payload.get('lab_results'), list):
                    tests_list = payload['lab_results']
                for pt in tests_list:
                    if isinstance(pt, dict) and (pt.get('name') or '').lower().strip() == current_test_name:
                        item = {
                            'name': pt.get('name'),
                            'value': pt.get('value'),
                            'unit': pt.get('unit'),
                            'reference_range': pt.get('reference_range'),
                            'status': pt.get('status'),
                            'date': msg_date,
                        }
                        historical_results.append(item)
    except Exception as e:
        print(f"🔍 DEBUG: ai_messages'tan geçmiş lab sonuçlarını çekerken hata: {e}")

    # Body'den gelen geçmiş sonuçları da ekle (varsa)
    if body.historical_results:
        historical_results.extend(body.historical_results)

    historical_dict = historical_results
    
    # Health Guard kaldırıldı - Lab analizi zaten kontrollü içerik üretiyor

    # Use parallel single lab analysis with historical results
    res = parallel_single_lab_analyze(test_dict, historical_dict)
    final_json = res["content"]
    data = parse_json_safe(final_json) or {}
    
    
    # Log to ai_messages
    try:
        create_ai_message(
            db=db,
            external_user_id=x_user_id,
            message_type="lab_single",
            request_payload=body.dict(),
            response_payload=data,
            model_used="openrouter"
        )
    except Exception as e:
        print(f"🔍 DEBUG: Lab Single ai_messages kaydı hatası: {e}")
    
    return data

@app.post("/ai/lab/session", response_model=SingleSessionResponse)
def analyze_single_session(body: SingleSessionRequest,
                          current_user: str = Depends(get_current_user),
                          db: Session = Depends(get_db),
                          x_user_id: str | None = Header(default=None),
                          x_user_plan: str | None = Header(default=None),
                          x_user_level: int | None = Header(default=None)):
    """Analyze single lab session with multiple tests"""
    
    # Plan kontrolü - Yeni sistem: userLevel bazlı
    if x_user_level is not None:
        if x_user_level == 0 or x_user_level == 1:
            user_plan = "free"
        elif x_user_level == 2:
            user_plan = "premium"
        elif x_user_level == 3:
            user_plan = "premium_plus"
        else:
            user_plan = "free"  # Default fallback
    else:
        # Eski sistem fallback
        user_plan = x_user_plan or "premium"  # Asıl site zaten kontrol ediyor
    
    user = get_or_create_user(db, x_user_id, user_plan)
    
    # FLEXIBLE INPUT HANDLING - Asıl site'dan herhangi bir format gelebilir
    tests_dict = []
    
    # 1. Önce body.session_tests'i dene (Pydantic model listesi)
    if body.session_tests:
        tests_dict = [test.model_dump() for test in body.session_tests]
    # 2. Yoksa body.tests'i dene (raw dict listesi)
    elif body.tests:
        tests_dict = body.tests
    # 3. Hiçbiri yoksa hata ver
    else:
        raise HTTPException(400, "Test verisi bulunamadı. 'session_tests' veya 'tests' field'ı gerekli.")
    
    # Format standardizasyonu - her zaman dict listesi olmalı
    if not isinstance(tests_dict, list):
        raise HTTPException(400, "Test verisi liste formatında olmalı.")
    
    # Boş liste kontrolü
    if not tests_dict:
        raise HTTPException(400, "Test verisi boş olamaz.")
    
    # Health Guard kaldırıldı - Lab analizi zaten kontrollü içerik üretiyor
    
    # Use parallel single session analysis with flexible input
    session_date = body.session_date or body.date or "2024-01-15"  # Default date
    laboratory = body.laboratory or body.lab or "Laboratuvar"  # Default lab name
    
    res = parallel_single_session_analyze(tests_dict, session_date, laboratory)
    final_json = res["content"]
    data = parse_json_safe(final_json) or {}
    
    # Database kaydı kaldırıldı - Asıl site zaten yapacak
    # Sadece AI yanıtını döndür
    
    # Log to ai_messages
    try:
        create_ai_message(
            db=db,
            external_user_id=x_user_id,
            message_type="lab_session",
            request_payload=body.dict(),
            response_payload=data,
            model_used="openrouter"
        )
    except Exception as e:
        print(f"🔍 DEBUG: Lab Session ai_messages kaydı hatası: {e}")
    
    return data

@app.post("/ai/lab/summary", response_model=GeneralLabSummaryResponse)
def analyze_multiple_lab_summary(body: MultipleLabRequest,
                                 current_user: str = Depends(get_current_user),
                                 db: Session = Depends(get_db),
                                 x_user_id: str | None = Header(default=None),
                                 x_user_plan: str | None = Header(default=None),
                                 x_user_level: int | None = Header(default=None)):
    """Generate general summary of multiple lab tests with supplement recommendations and progress tracking"""
    
    # Plan kontrolü - Yeni sistem: userLevel bazlı
    if x_user_level is not None:
        if x_user_level == 0 or x_user_level == 1:
            user_plan = "free"
        elif x_user_level == 2:
            user_plan = "premium"
        elif x_user_level == 3:
            user_plan = "premium_plus"
        else:
            user_plan = "free"  # Default fallback
    else:
        # Eski sistem fallback
        user_plan = x_user_plan or "premium"  # Asıl site zaten kontrol ediyor
    
    user = get_or_create_user(db, x_user_id, user_plan)
    
    # FLEXIBLE INPUT HANDLING - Asıl site'dan herhangi bir format gelebilir
    new_tests_dict = []
    
    # 1. Önce body.tests'i dene (Pydantic model listesi)
    if body.tests:
        new_tests_dict = [test.model_dump() for test in body.tests]
    # 2. Yoksa body.lab_results'i dene (raw dict listesi)
    elif body.lab_results:
        new_tests_dict = body.lab_results
    # 3. Hiçbiri yoksa hata ver
    else:
        raise HTTPException(400, "Test verisi bulunamadı. 'tests' veya 'lab_results' field'ı gerekli.")
    
    # Format standardizasyonu - her zaman dict listesi olmalı
    if not isinstance(new_tests_dict, list):
        raise HTTPException(400, "Test verisi liste formatında olmalı.")
    
    # Boş liste kontrolü
    if not new_tests_dict:
        raise HTTPException(400, "Test verisi boş olamaz.")
    
    # YENİ: Geçmiş testleri ai_messages'tan derle + yeni testleri ekle
    all_tests_dict = []

    from backend.db import get_ai_messages
    try:
        prior_msgs = get_ai_messages(db, external_user_id=x_user_id, limit=100)
        for msg in prior_msgs:
            if not msg or not msg.request_payload:
                continue
            payload = msg.request_payload
            msg_date = msg.created_at.isoformat() if getattr(msg, 'created_at', None) else None

            if msg.message_type == 'lab_single' and isinstance(payload.get('test'), dict):
                pt = payload['test']
                test_with_date = {**pt}
                test_with_date['test_date'] = msg_date or 'Geçmiş'
                all_tests_dict.append(test_with_date)

            elif msg.message_type == 'lab_session':
                tests_list = []
                if isinstance(payload.get('session_tests'), list):
                    tests_list = payload['session_tests']
                elif isinstance(payload.get('tests'), list):
                    tests_list = payload['tests']
                for pt in tests_list:
                    if isinstance(pt, dict):
                        test_with_date = {**pt}
                        test_with_date['test_date'] = msg_date or 'Geçmiş'
                        all_tests_dict.append(test_with_date)

            elif msg.message_type == 'lab_summary':
                tests_list = []
                if isinstance(payload.get('tests'), list):
                    tests_list = payload['tests']
                elif isinstance(payload.get('lab_results'), list):
                    tests_list = payload['lab_results']
                for pt in tests_list:
                    if isinstance(pt, dict):
                        test_with_date = {**pt}
                        test_with_date['test_date'] = msg_date or 'Geçmiş'
                        all_tests_dict.append(test_with_date)
    except Exception as e:
        print(f"🔍 DEBUG: ai_messages'tan geçmiş lab testlerini çekerken hata: {e}")

    # Yeni testleri ekle
    for test in new_tests_dict:
        test_with_date = test.copy()
        test_with_date['test_date'] = 'Yeni Seans'
        test_with_date['lab_name'] = 'Yeni Lab'
        all_tests_dict.append(test_with_date)
    
    # Eğer hiç test yoksa, default test oluştur
    if not all_tests_dict:
        all_tests_dict = [
            {
                "name": "Test Sonucu",
                "value": "Veri bulunamadı",
                "unit": "N/A",
                "reference_range": "N/A",
                "test_date": "Yeni Seans",
                "lab_name": "Yeni Lab"
            }
        ]
    
    tests_dict = all_tests_dict
    
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
    
    
    # Database kaydı tamamlandı - Artık read-through sistemi çalışacak
    
    # Log to ai_messages
    try:
        create_ai_message(
                db=db,
            external_user_id=x_user_id,
            message_type="lab_summary",
            request_payload=body.dict(),
            response_payload=data,
            model_used="openrouter"
        )
    except Exception as e:
        print(f"🔍 DEBUG: Lab Summary ai_messages kaydı hatası: {e}")
    
    return data







@app.get("/ai/progress/{user_id}")
def get_user_progress(user_id: str, db: Session = Depends(get_db)):
    """Get user's lab test progress and trends"""
    
    # Get lab test history from ai_messages
    from backend.db import get_ai_messages, get_user_by_external_id
    
    # external_user_id ile kullanıcıyı bul
    user = get_user_by_external_id(db, user_id)
    if not user:
        raise HTTPException(404, "Kullanıcı bulunamadı")
    
    # Get lab tests from ai_messages
    lab_messages = get_ai_messages(db, external_user_id=user_id, message_type="lab_single", limit=20)
    lab_history = []
    
    # Convert ai_messages to lab_history format
    for msg in lab_messages:
        if msg.request_payload and "test" in msg.request_payload:
            test_data = msg.request_payload["test"]
            lab_history.append({
                "id": msg.id,
                "test_date": msg.created_at,
                "test_type": "single",
                "test_results": {"tests": [test_data]}
            })
    
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

@app.post("/ai/chat/clear-session")
def clear_free_user_session(x_user_id: str | None = Header(default=None)):
    """Free kullanıcının session'ını temizle"""
    if x_user_id and x_user_id in free_user_conversations:
        del free_user_conversations[x_user_id]
        return {"message": "Session temizlendi", "user_id": x_user_id}
    return {"message": "Session bulunamadı", "user_id": x_user_id}

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

# ---------- PREMIUM PLUS BESLENME/SPOR/EGZERSİZ ÖNERİLERİ ----------

@app.post("/ai/premium-plus/lifestyle-recommendations")
async def premium_plus_lifestyle_recommendations(
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
    x_user_id: str | None = Header(default=None),
    x_user_plan: str | None = Header(default=None),
    x_user_level: int | None = Header(default=None)
):
    """Premium Plus kullanıcıları için beslenme, spor ve egzersiz önerileri"""
    
    # Plan kontrolü - Yeni sistem: userLevel bazlı
    if x_user_level is not None:
        if x_user_level == 3:
            user_plan = "premium_plus"
        else:
            user_plan = "free"  # Premium Plus değilse free
    else:
        # Eski sistem fallback
        user_plan = x_user_plan or "free"
    
    if user_plan != "premium_plus":
        raise HTTPException(
            status_code=403, 
            detail="Bu özellik sadece Premium Plus kullanıcıları için mevcuttur"
        )
    
    # User ID validasyonu
    if not x_user_id:
        raise HTTPException(status_code=400, detail="User ID gerekli")
    
    # Kullanıcıyı bul/oluştur
    user = get_or_create_user(db, x_user_id, user_plan)
    
    # Quiz geçmişini al (basit implementasyon - quiz tablosu yok)
    quiz_history = []  # TODO: Quiz geçmişi için ayrı tablo gerekli
    
    # Lab analizlerini al
    lab_analyses = get_user_ai_messages_by_type(db, x_user_id, "lab_single", limit=3)
    
    # AI'ya gönderilecek context'i hazırla
    user_context = {}
    
    # System prompt - Premium Plus özel
    system_prompt = """Sen Longo AI'sın - Premium Plus kullanıcıları için özel beslenme, spor ve egzersiz danışmanısın.

🎯 GÖREVİN: Kullanıcının quiz sonuçları ve lab verilerine göre kişiselleştirilmiş beslenme, spor ve egzersiz önerileri ver.

📊 VERİ ANALİZİ:
- Quiz sonuçlarından yaş, cinsiyet, sağlık hedefleri, aktivite seviyesi
- Lab sonuçlarından vitamin/mineral eksiklikleri, sağlık durumu
- Bu verileri birleştirerek holistik yaklaşım

🏃‍♂️ SPOR/EGZERSİZ ÖNERİLERİ:
- Kullanıcının yaşına, kondisyonuna ve hedeflerine uygun
- Haftalık program önerisi (kaç gün, ne kadar süre)
- Kardiyovasküler, güç antrenmanı, esneklik dengesi
- Başlangıç seviyesi için güvenli ve sürdürülebilir

🥗 BESLENME ÖNERİLERİ:
- Lab sonuçlarına göre eksik vitamin/mineraller için besin önerileri
- Quiz'deki hedeflere uygun makro besin dağılımı
- Öğün planlama ve porsiyon önerileri
- Supplement ile beslenme dengesi

⚡ ENERJİ VE PERFORMANS:
- Egzersiz öncesi/sonrası beslenme
- Hidrasyon stratejileri
- Uyku ve recovery önerileri

🚫 KISITLAMALAR:
- Sadece genel öneriler, tıbbi tavsiye değil
- Kişisel antrenör veya diyetisyen yerine geçmez
- Güvenlik öncelikli yaklaşım

💡 YANIT FORMATI:
1. 📊 MEVCUT DURUM ANALİZİ
2. 🏃‍♂️ SPOR/EGZERSİZ PROGRAMI
3. 🥗 BESLENME ÖNERİLERİ
4. ⚡ PERFORMANS İPUÇLARI
5. 📅 HAFTALIK PLAN ÖNERİSİ

DİL: SADECE TÜRKÇE YANIT VER!"""

    # User message'ı hazırla
    user_message = f"""Kullanıcının mevcut durumu:

📊 KULLANICI BİLGİLERİ:
"""
    
    # Quiz verilerini ekle
    if user_context:
        user_message += f"\n📋 QUIZ VERİLERİ:\n"
        for key, value in user_context.items():
            if value and key in ['yas', 'cinsiyet', 'hedef', 'aktivite', 'boy', 'kilo', 'quiz_sonuc', 'quiz_summary', 'quiz_gecmisi']:
                user_message += f"- {key.upper()}: {value}\n"
    
    # Quiz geçmişini ekle
    if quiz_history:
        user_message += f"\n📋 SON QUIZ SONUÇLARI:\n"
        for quiz in quiz_history[-1:]:  # En son quiz
            if quiz.get('summary'):
                user_message += f"- {quiz['summary']}\n"
    
    # Lab analizlerini ekle
    if lab_analyses:
        user_message += f"\n🧪 LAB ANALİZLERİ:\n"
        for analysis in lab_analyses[-1:]:  # En son analiz
            if hasattr(analysis, 'summary') and analysis.summary:
                user_message += f"- {analysis.summary}\n"
            elif isinstance(analysis, dict) and analysis.get('summary'):
                user_message += f"- {analysis['summary']}\n"
    
    # Global context'ten tüm verileri ekle
    if user_context:
        # Quiz verilerini ekle
        quiz_keys = ['yas', 'cinsiyet', 'hedef', 'aktivite', 'boy', 'kilo', 'quiz_supplements', 'quiz_priority', 'quiz_tarih']
        quiz_data_found = False
        for key in quiz_keys:
            if key in user_context and user_context[key]:
                if not quiz_data_found:
                    user_message += f"\n📋 GLOBAL QUIZ VERİLERİ:\n"
                    quiz_data_found = True
                user_message += f"- {key.upper()}: {user_context[key]}\n"
        
        # Lab verilerini ekle
        lab_keys = ['lab_gecmisi', 'lab_genel_durum', 'lab_summary', 'lab_tarih', 'son_lab_test', 'son_lab_deger', 'son_lab_durum']
        lab_data_found = False
        for key in lab_keys:
            if key in user_context and user_context[key]:
                if not lab_data_found:
                    user_message += f"\n🧪 GLOBAL LAB VERİLERİ:\n"
                    lab_data_found = True
                user_message += f"- {key.upper()}: {user_context[key]}\n"
    
    user_message += f"""

Bu bilgilere göre kullanıcı için kapsamlı beslenme, spor ve egzersiz önerileri hazırla. 
Kişiselleştirilmiş, sürdürülebilir ve güvenli bir program öner."""

    # AI'ya gönder
    try:
        from backend.openrouter_client import get_ai_response
        
        reply = await get_ai_response(system_prompt, user_message)
        
        return {
            "status": "success",
            "recommendations": reply,
            "user_context": user_context,
            "quiz_count": len(quiz_history),
            "lab_count": len(lab_analyses)
        }
        
    except Exception as e:
        print(f"❌ Premium Plus lifestyle recommendations error: {e}")
        raise HTTPException(status_code=500, detail="Öneriler oluşturulurken hata oluştu")

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

@app.get("/debug/database")
def debug_database(current_user: str = Depends(get_current_user),
                   db: Session = Depends(get_db),
                   x_user_id: str | None = Header(default=None)):
    """Debug endpoint to check database contents"""
    try:
        from backend.db import get_or_create_user_by_external_id, get_ai_messages
        
        # User bilgilerini al
        user = get_or_create_user_by_external_id(db, x_user_id, "free")
        
        # AI messages
        ai_messages = get_ai_messages(db, external_user_id=x_user_id, limit=10)
        
        return {
            "user_id": user.id,
            "external_user_id": user.external_user_id,
            "plan": user.plan,
            "ai_messages_count": len(ai_messages),
            "ai_messages": [
                {
                    "id": msg.id,
                    "message_type": msg.message_type,
                    "created_at": msg.created_at.isoformat() if msg.created_at else None,
                    "model_used": msg.model_used
                } for msg in ai_messages
            ]
        }
    except Exception as e:
        return {"error": str(e), "type": type(e).__name__}

@app.get("/ai/messages")
def get_ai_messages_endpoint(
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
    x_user_id: str | None = Header(default=None),
    message_type: str | None = None,
    limit: int = 50
):
    """Get AI messages for debugging"""
    try:
        from backend.db import get_ai_messages
        messages = get_ai_messages(db, external_user_id=x_user_id, message_type=message_type, limit=limit)
        
        return {
            "success": True,
            "count": len(messages),
            "messages": [
                {
                    "id": msg.id,
                    "external_user_id": msg.external_user_id,
                    "message_type": msg.message_type,
                    "model_used": msg.model_used,
                    "created_at": msg.created_at.isoformat() if msg.created_at else None,
                    "request_payload": msg.request_payload,
                    "response_payload": msg.response_payload
                } for msg in messages
            ]
        }
    except Exception as e:
        return {"error": str(e), "type": type(e).__name__}