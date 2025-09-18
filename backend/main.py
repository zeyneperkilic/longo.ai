from fastapi import FastAPI, Depends, HTTPException, Header, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
import json
import os
from functools import wraps
from collections import defaultdict
import requests
import xml.etree.ElementTree as ET
import time
from datetime import datetime

from backend.config import (
    ALLOWED_ORIGINS, CHAT_HISTORY_MAX, FREE_ANALYZE_LIMIT,
    XML_REQUEST_TIMEOUT, FREE_QUESTION_LIMIT, FREE_SESSION_TIMEOUT_SECONDS,
    CHAT_HISTORY_LIMIT, USER_ANALYSES_LIMIT, QUIZ_LAB_MESSAGES_LIMIT,
    AI_MESSAGES_LIMIT, AI_MESSAGES_LIMIT_LARGE, LAB_MESSAGES_LIMIT,
    QUIZ_LAB_ANALYSES_LIMIT, DEBUG_AI_MESSAGES_LIMIT, MILLISECOND_MULTIPLIER,
    MIN_LAB_TESTS_FOR_COMPARISON, AVAILABLE_TESTS
)
from backend.db import Base, engine, SessionLocal, create_ai_message, get_user_ai_messages, get_user_ai_messages_by_type, get_or_create_user_by_external_id
from backend.auth import get_db, get_or_create_user
from backend.schemas import ChatStartRequest, ChatStartResponse, ChatMessageRequest, ChatResponse, QuizRequest, QuizResponse, SingleLabRequest, SingleSessionRequest, MultipleLabRequest, LabAnalysisResponse, SingleSessionResponse, GeneralLabSummaryResponse, TestRecommendationRequest, TestRecommendationResponse, MetabolicAgeTestRequest, MetabolicAgeTestResponse
from backend.health_guard import guard_or_message
from backend.orchestrator import parallel_chat, parallel_quiz_analyze, parallel_single_lab_analyze, parallel_single_session_analyze, parallel_multiple_lab_analyze
from backend.utils import parse_json_safe, generate_response_id, extract_user_context_hybrid
from backend.cache_utils import cache_supplements




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
    """XML'den tüm ürün bilgilerini çek"""
    try:
        response = requests.get('https://longopass.myideasoft.com/output/7995561125', timeout=XML_REQUEST_TIMEOUT)
        root = ET.fromstring(response.text)
        products = []
        for item in root.findall('.//item'):
            product = {}
            
            # ID
            id_elem = item.find('id')
            if id_elem is not None and id_elem.text:
                product['id'] = id_elem.text.strip()
            
            # Label (ürün adı)
            label_elem = item.find('label')
            if label_elem is not None and label_elem.text:
                product['name'] = label_elem.text.strip()
            
            # Main Category
            category_elem = item.find('mainCategory')
            if category_elem is not None and category_elem.text:
                product['category'] = category_elem.text.strip()
            
            # Diğer alanları da ekle (varsa)
            for child in item:
                if child.tag not in ['id', 'label', 'mainCategory']:
                    if child.text:
                        product[child.tag] = child.text.strip()
            
            if product:  # En az bir alan varsa ekle
                products.append(product)
        
        return products
    except Exception as e:
        print(f"XML çekme hatası: {e}")
        return []

def get_standardized_lab_data(db, user_id, limit=5):
    """Tüm endpoint'ler için standart lab verisi - ham test verileri"""
    # Önce lab_summary'den dene (en kapsamlı)
    lab_summary = get_user_ai_messages_by_type(db, user_id, "lab_summary", limit)
    if lab_summary and lab_summary[0].request_payload and "tests" in lab_summary[0].request_payload:
        return lab_summary[0].request_payload["tests"]
    
    # Lab_summary yoksa lab_single'dan al
    lab_single = get_user_ai_messages_by_type(db, user_id, "lab_single", limit)
    tests = []
    for msg in lab_single:
        if msg.request_payload and "test" in msg.request_payload:
            tests.append(msg.request_payload["test"])
    
    return tests

def get_user_context_for_message(user_context: dict, user_analyses: list) -> tuple[str, str]:
    """Lab ve quiz verilerini user message için hazırla"""
    lab_info = ""
    quiz_info = ""
    
    # Lab verilerini user message'a ekle
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
    
    # Quiz verilerini user message'a ekle
    if user_analyses:
        quiz_analyses = [a for a in user_analyses if a.message_type == "quiz"]
        if quiz_analyses:
            latest_quiz = quiz_analyses[0]  # En son quiz
            if latest_quiz.request_payload:
                # Ham quiz cevaplarını al
                quiz_info = f"🚨 SAĞLIK QUIZ PROFİLİ (KULLANICI VERİSİ):\n"
                for key, value in latest_quiz.request_payload.items():
                    if value and value != 'N/A':
                        quiz_info += f"- {key}: {value}\n"
                quiz_info += "\n"
    
    return lab_info, quiz_info

def get_user_plan_from_headers(x_user_level: int | None) -> str:
    """Header'lardan user plan'ı belirle - sadece x_user_level kullan"""
    if x_user_level is not None:
        if x_user_level == 0 or x_user_level == 1:
            return "free"
        elif x_user_level == 2:
            return "premium"
        elif x_user_level == 3:
            return "premium_plus"
        else:
            return "free"  # Default fallback
    else:
        # x_user_level gelmezse (üye değilse) free olarak kabul et
        return "free"

def build_chat_system_prompt() -> str:
    """Chat için system prompt oluştur"""
    return """Sen Longo AI'sın. SADECE sağlık/supplement/lab konularında yanıt ver. Off-topic'te kibarca reddet. KAYNAK EKLEME: Otomatik olarak kaynak link'leri, referans'lar veya citation'lar ekleme!

🚨 ÇOK ÖNEMLİ: Kullanıcı mesajında "🚨 LAB SONUÇLARI" veya "🚨 SAĞLIK QUIZ PROFİLİ" ile başlayan bölümler var. Bu bilgiler kullanıcının yazdığı DEĞİL! Bunlar senin hafızanda olan geçmiş veriler! Kullanıcı sadece son cümlesini yazdı, diğer bilgiler senin hafızandan.

❌ YANLIŞ İFADELER KULLANMA:
- "paylaştığın için teşekkür ederim" 
- "sen yazdın"
- "sen söyledin"
- "sen belirttin"

✅ DOĞRU İFADELER KULLAN:
- "Geçmiş quiz sonuçlarına göre..."
- "Lab sonuçlarında gördüğüm kadarıyla..."
- "Hafızamda olan verilere göre..."
- "Önceki analizlerde..."

🚨 SAĞLIK YÖNLENDİRME KURALI: Her konuyu sağlık ve supplement alanına çek! Kullanıcı off-topic bir şey söylerse, kibarca sağlık konusuna yönlendir ve supplement önerisi yap!

❌ OFF-TOPIC BİLGİ VERME: Sağlık dışında konularda bilgi verme ve detaya girme! Kısa ve net cevaplar ver, sadece sağlık konusuna odaklan!

💡 YANIT STİLİ: 
- Kullanıcı sadece selamladıysa, önce selamlaş, sonra geçmiş verilerini hatırladığını göster
- Öneri istemediği sürece agresif supplement önerisi yapma
- Doğal ve akıcı konuş
- Geçmiş sağlık quizprofili/lab verileri varsa, bunları kullanarak kişiselleştirilmiş yanıt ver
- Sürekli bilgi isteme
- Sohbetin devamını sağla, her mesajda yeni konuşma başlatma
- Kullanıcının önceki mesajlarına referans ver ve bağlantı kur
- Önceki mesajlarda ne konuştuğunu hatırla ve devam et
- Aynı konuyu tekrar tekrar sorma, önceki cevapları kullan"""

def add_user_context_to_prompt(system_prompt: str, user_context: dict) -> str:
    """Kullanıcı bilgilerini system prompt'a ekle"""
    if not user_context or not any(user_context.values()):
        return system_prompt + "\n\nGenel sağlık ve supplement konularında yardımcı ol. Kullanıcı bilgileri yoksa genel öneriler ver ve listeden mantıklı ürün öner.\n\n🍎 BESLENME ÖNERİSİ KURALLARI:\n- Kullanıcı 'beslenme önerisi ver' derse, SADECE beslenme tavsiyeleri ver!\n- Beslenme önerisi istenince supplement önerme!\n- Sadece doğal besinler, yemek önerileri, beslenme programı ver!\n- Supplement önerisi sadece kullanıcı özel olarak 'supplement öner' derse yap!"
    
    system_prompt += "\n\n=== KULLANICI BİLGİLERİ ===\n"
    
    # String ve integer değerler için özel format
    if "isim" in user_context and user_context["isim"]:
        system_prompt += f"KULLANICI ADI: {user_context['isim']}\n"
        
    if "yas" in user_context and user_context["yas"]:
        system_prompt += f"KULLANICI YAŞI: {user_context['yas']} yaşında\n"
        
    if "tercihler" in user_context and user_context["tercihler"]:
        tercihler_str = ', '.join(user_context['tercihler']) if isinstance(user_context['tercihler'], list) else str(user_context['tercihler'])
        system_prompt += f"KULLANICI TERCİHLERİ: {tercihler_str}\n"
        
    if "hastaliklar" in user_context and user_context["hastaliklar"]:
        hastaliklar_str = ', '.join(user_context['hastaliklar']) if isinstance(user_context['hastaliklar'], list) else str(user_context['hastaliklar'])
        system_prompt += f"HASTALIKLAR: {hastaliklar_str}\n"
        
    if "cinsiyet" in user_context and user_context["cinsiyet"]:
        system_prompt += f"KULLANICI CİNSİYETİ: {user_context['cinsiyet']}\n"
    
    # Lab verilerini de göster - LAB SUMMARY BİLGİLERİ
    if "lab_gecmisi" in user_context and user_context["lab_gecmisi"]:
        system_prompt += f"LAB TEST GEÇMİŞİ (Son 1 Yıl):\n"
        for i, lab in enumerate(user_context["lab_gecmisi"], 1):
            system_prompt += f"{i}. {lab.get('ozet', '')}\n"
    
    # Lab summary bilgileri (en güncel)
    if "lab_genel_durum" in user_context and user_context["lab_genel_durum"]:
        system_prompt += f"\nLAB GENEL DURUM: {user_context['lab_genel_durum']}\n"
        
    if "lab_summary" in user_context and user_context["lab_summary"]:
        system_prompt += f"LAB ÖZET: {user_context['lab_summary']}\n"
    
    if "lab_tarih" in user_context and user_context["lab_tarih"]:
        system_prompt += f"LAB TARİH: {user_context['lab_tarih']}\n"
        
    system_prompt += "\nÖNEMLİ: Bu bilgileri kesinlikle hatırla! Kullanıcı sana adını, yaşını, hastalığını veya lab sonuçlarını sorduğunda yukarıdaki bilgilerle cevap ver!"
    
    return system_prompt

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

# IP-based limiting for guest users (no account)
ip_daily_limits = {}  # {ip: {"count": int, "reset_time": timestamp}}

def check_ip_daily_limit(client_ip: str) -> tuple[bool, int]:
    """Guest kullanıcılar için IP-based günlük limit kontrolü"""
    import time
    current_time = time.time()
    
    # 24 saat = 86400 saniye
    daily_reset_seconds = 86400
    
    if client_ip not in ip_daily_limits:
        # İlk kez gelen IP
        ip_daily_limits[client_ip] = {
            "count": 0,
            "reset_time": current_time + daily_reset_seconds
        }
    
    ip_data = ip_daily_limits[client_ip]
    
    # 24 saat geçmişse reset et
    if current_time >= ip_data["reset_time"]:
        ip_data["count"] = 0
        ip_data["reset_time"] = current_time + daily_reset_seconds
    
    # Limit kontrolü
    if ip_data["count"] >= FREE_QUESTION_LIMIT:
        return False, 0  # Limit aşıldı
    
    # Limit artır
    ip_data["count"] += 1
    remaining = FREE_QUESTION_LIMIT - ip_data["count"]
    
    return True, remaining

def check_user_daily_limit(user_id: str, client_ip: str) -> tuple[bool, int]:
    """Free kullanıcılar için User ID + IP kombinasyonu ile günlük limit kontrolü"""
    import time
    current_time = time.time()
    
    # User ID + IP kombinasyonu için unique key
    user_ip_key = f"{user_id}_{client_ip}"
    
    # 24 saat = 86400 saniye
    daily_reset_seconds = 86400
    
    if user_ip_key not in ip_daily_limits:
        # İlk kez gelen User ID + IP kombinasyonu
        ip_daily_limits[user_ip_key] = {
            "count": 0,
            "reset_time": current_time + daily_reset_seconds
        }
    
    user_ip_data = ip_daily_limits[user_ip_key]
    
    # 24 saat geçmişse reset et
    if current_time >= user_ip_data["reset_time"]:
        user_ip_data["count"] = 0
        user_ip_data["reset_time"] = current_time + daily_reset_seconds
    
    # Limit kontrolü
    if user_ip_data["count"] >= FREE_QUESTION_LIMIT:
        return False, 0  # Limit aşıldı
    
    # Limit artır
    user_ip_data["count"] += 1
    remaining = FREE_QUESTION_LIMIT - user_ip_data["count"]
    
    return True, remaining

async def handle_free_user_chat(req: ChatMessageRequest, x_user_id: str):
    """Free kullanıcılar için session-based chat handler"""
    from backend.cache_utils import get_session_question_count, increment_session_question_count
    
    # Session-based question count kontrolü
    question_count = get_session_question_count(x_user_id)
    
    # Free kullanıcı soru limiti kontrolü
    if question_count >= FREE_QUESTION_LIMIT:
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
        if current_time - data["last_activity"] > FREE_SESSION_TIMEOUT_SECONDS:
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
        conversation_history = free_user_conversations[x_user_id]["messages"][-CHAT_HISTORY_LIMIT:] if len(free_user_conversations[x_user_id]["messages"]) > 0 else []
        
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
                category = product.get('category', 'Kategori Yok')
                user_message += f"{i}. {product['name']} ({category})\n"
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
               x_user_id: str | None = Header(default=None)):
    
    # Plan kontrolü
    user_plan = "free"  # Free chat için sabit
    is_premium = user_plan in ["premium", "premium_plus"]
    
    # User ID validasyonu (Free: Session ID, Premium: Real ID)
    if not validate_chat_user_id(x_user_id or "", user_plan):
        raise HTTPException(status_code=400, detail="Premium kullanıcılar için gerçek user ID gerekli")
    
    # Free kullanıcılar için session-based conversation
    if not is_premium:
        # Free kullanıcılar için basit conversation ID (session-based)
        from backend.cache_utils import get_session_question_count
        question_count = get_session_question_count(x_user_id or "anonymous")
        
        # Free kullanıcı soru limiti kontrolü
        if question_count >= FREE_QUESTION_LIMIT:
            return ChatStartResponse(
                conversation_id=0,
                detail="🎯 Günlük 10 soru limitiniz doldu! Yarın tekrar konuşmaya devam edebilirsiniz. 💡 Premium plana geçerek sınırsız soru sorma imkanına sahip olun!"
            )
        
        # Free kullanıcılar için session-based conversation ID
        return ChatStartResponse(conversation_id=1)  # Her zaman 1, session'da takip edilir
    
    # Premium kullanıcılar için yeni conversation ID oluştur
    user = get_or_create_user(db, x_user_id, user_plan)
    
    # Yeni conversation ID oluştur (timestamp-based)
    new_conversation_id = int(time.time() * MILLISECOND_MULTIPLIER)  # Millisecond timestamp
    
    return ChatStartResponse(conversation_id=new_conversation_id)

@app.get("/ai/chat/{conversation_id}/history")
def chat_history(conversation_id: int,
                 db: Session = Depends(get_db),
                 x_user_id: str | None = Header(default=None)):
    
    # Plan kontrolü
    user_plan = "free"  # Free chat için sabit
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
                  x_user_level: int | None = Header(default=None),
                  request: Request = None):
    
    # Plan kontrolü
    user_plan = get_user_plan_from_headers(x_user_level)
    
    is_premium = user_plan in ["premium", "premium_plus"]
    
    # Guest ve Free kullanıcılar için limiting
    client_ip = request.client.host if request else "unknown"
    
    if not x_user_level or x_user_level == 0:  # Guest (null/undefined/0)
        can_chat, remaining = check_ip_daily_limit(client_ip)
        if not can_chat:
            raise HTTPException(
                status_code=429, 
                detail=f"Günlük soru limitiniz aşıldı. 24 saat sonra tekrar deneyin. (Kalan: {remaining})"
            )
    elif x_user_level == 1:  # Free (hesap var)
        can_chat, remaining = check_user_daily_limit(x_user_id, client_ip)
        if not can_chat:
            raise HTTPException(
                status_code=429, 
                detail=f"Günlük soru limitiniz aşıldı. 24 saat sonra tekrar deneyin. (Kalan: {remaining})"
            )
    
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
        "selam", "naber", "günaydın", "merhaba",
        "iyi akşamlar", "iyi aksamlar", "iyi geceler", "iyi günler", "iyi gunler"
    ]
    
    # Eğer saf selamlama ise özel yanıt ver
    if any(kw == txt for kw in pure_greeting_keywords):
        reply = "Merhaba! Ben Longo AI. Sağlık, supplement ve laboratuvar konularında yardımcı olabilirim. Size nasıl yardımcı olabilirim?"
        return ChatResponse(conversation_id=conversation_id, reply=reply, latency_ms=0)

    # Chat history'yi ai_messages'tan al (Message tablosu yerine)
    chat_messages = get_user_ai_messages_by_type(db, x_user_id, "chat", limit=CHAT_HISTORY_LIMIT)
    
    # ai_messages formatını history formatına çevir - sadece bu conversation'a ait
    rows = []
    for msg in chat_messages:
        # User message - conversation_id kontrolü (string/int karşılaştırması)
        if msg.request_payload and "message" in msg.request_payload and str(msg.request_payload.get("conversation_id")) == str(conversation_id):
            rows.append({"role": "user", "content": msg.request_payload["message"], "created_at": msg.created_at})
        # Assistant message - aynı conversation_id'ye ait olmalı
        if msg.response_payload and "reply" in msg.response_payload and msg.request_payload and str(msg.request_payload.get("conversation_id")) == str(conversation_id):
            rows.append({"role": "assistant", "content": msg.response_payload["reply"], "created_at": msg.created_at})
    
    # Conversation history'yi tarih sırasına göre sırala
    rows.sort(key=lambda x: x["created_at"])
    
    # Get user's previous analyses for context (CACHE THIS!)
    user_analyses = get_user_ai_messages(db, x_user_id, limit=USER_ANALYSES_LIMIT)
    
    # Global + Local Context Sistemi - OPTIMIZED
    user_context = {}
    
    
    # Lab verilerini helper fonksiyon ile al
    lab_tests = get_standardized_lab_data(db, x_user_id, 20)
    
    # Lab ve quiz verilerini user message için hazırla
    lab_info, quiz_info = get_user_context_for_message(user_context, user_analyses)
    
    # Helper'dan gelen lab verilerini de ekle
    if lab_tests:
        lab_info = f"🚨 LAB SONUÇLARI (KULLANICI VERİSİ):\n"
        for test in lab_tests[:2]:  # İlk 2 test
            lab_info += f"- {test.get('name', 'N/A')}: {test.get('value', 'N/A')} ({test.get('reference_range', 'N/A')})\n"
        lab_info += "\n"
    
    # Lab ve quiz bilgilerini user message'a ekle
    if lab_info or quiz_info:
        enhanced_message = message_text
        if lab_info:
            enhanced_message = lab_info + enhanced_message
        if quiz_info:
            enhanced_message = quiz_info + enhanced_message
        user_message = enhanced_message
    else:
        user_message = message_text
    
    # Build enhanced system prompt with user context
    system_prompt = build_chat_system_prompt()
    
    # 1.5. READ-THROUGH: Lab verisi global context'te yoksa DB'den çek
    # LAB VERİLERİ PROMPT'TAN TAMAMEN ÇIKARILDI - TOKEN TASARRUFU İÇİN
    # Lab verileri hala context'te tutuluyor ama prompt'a eklenmiyor
    
    # 2. Son mesajlardan yeni context bilgilerini çıkar (ONLY IF NEEDED)
    # ÖNEMLİ: Global context user bazında olmalı, conversation bazında değil!
    # Bu yüzden sadece yeni mesajdan context çıkar, eski mesajlardan değil
    # recent_messages = rows[-(CHAT_HISTORY_MAX-1):] if len(rows) > 0 else []
    new_context = {}
    
    # Yeni mesajdan context çıkar
    current_message_context = extract_user_context_hybrid(message_text, user.email) or {}
    for key, value in current_message_context.items():
        normalized_key = key.strip().lower()
        if normalized_key and value:
            if normalized_key not in new_context:
                new_context[normalized_key] = value
            elif isinstance(value, list) and isinstance(new_context[normalized_key], list):
                new_context[normalized_key] = list(set(new_context[normalized_key] + value))
            else:
                new_context[normalized_key] = value
    
    # Yeni context'i global context'e ekle
    if new_context and any(new_context.values()):
        context_changed = any(key not in user_context or user_context[key] != value 
                            for key, value in new_context.items())
        if context_changed:
            user_context.update(new_context)
    
    # Kullanıcı bilgilerini system prompt'a ekle
    system_prompt = add_user_context_to_prompt(system_prompt, user_context)
    
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
    system_prompt += "\n- Değerler iyiyse veya kullanıcı Longevity derse Longevity ürünler öner, kötüyse problem çözücü öner!"
    
    # Lab ve quiz verilerini user message için hazırla
    lab_info, quiz_info = get_user_context_for_message(user_context, user_analyses)
    
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
    
    # System message hazır
    
    history = [{"role": "system", "content": system_prompt, "context_data": user_context}]
    
    # Lab verilerini user message olarak ekle
    if lab_info:
        history.append({"role": "user", "content": lab_info})
    
    # Supplement listesi sadece supplement önerisi istenirse ekle
    if any(keyword in message_text.lower() for keyword in ["vitamin", "supplement", "takviye", "öner", "hangi", "ne önerirsin"]):
        history.append({"role": "user", "content": supplements_info})
    
    # Quiz verilerini ai_messages'tan çek
    quiz_messages = get_user_ai_messages_by_type(db, x_user_id, "quiz", limit=QUIZ_LAB_MESSAGES_LIMIT)
    
    # Quiz verilerini ekle - Ham quiz cevapları (diğer endpoint'ler gibi)
    if quiz_messages:
        quiz_info = "\n\n=== QUIZ BİLGİLERİ ===\n"
        for msg in quiz_messages:
            if msg.request_payload:
                quiz_info += f"QUIZ TARİHİ: {msg.created_at.strftime('%Y-%m-%d')}\n"
                quiz_info += f"QUIZ CEVAPLARI: {msg.request_payload}\n\n"
        history.append({"role": "user", "content": quiz_info})
    
    # Lab verilerini ekle - Sadece helper'dan gelen veriler (diğer endpoint'ler gibi)
    if lab_tests:
        lab_info = "\n\n=== LAB BİLGİLERİ ===\n"
        lab_info += "LAB TEST SONUÇLARI:\n"
        for test in lab_tests[:3]:  # İlk 3 test
            lab_info += f"- {test.get('name', 'N/A')}: {test.get('value', 'N/A')} {test.get('unit', '')} (Referans: {test.get('reference_range', 'N/A')})\n"
        history.append({"role": "user", "content": lab_info})
    
    # Chat history
    for r in rows[-(CHAT_HISTORY_MAX-1):]:
        history.append({"role": r["role"], "content": r["content"]})
    
    # Kullanıcının güncel mesajını ekle
    history.append({"role": "user", "content": message_text})

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
        pass  # Silent fail for production
    
    return ChatResponse(conversation_id=conversation_id, reply=final, latency_ms=latency_ms)

# ---------- ANALYZE (FREE: one-time), LAB ----------


@app.post("/ai/quiz", response_model=QuizResponse)
async def analyze_quiz(body: QuizRequest,
                 current_user: str = Depends(get_current_user),
                 db: Session = Depends(get_db),
                 x_user_id: str | None = Header(default=None),
                 x_user_level: int | None = Header(default=None)):
    """Quiz endpoint - Sadece AI model işlemi, asıl site entegrasyonu için optimize edildi"""
    
    # Logger tanımla
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    # Plan kontrolü
    user_plan = get_user_plan_from_headers(x_user_level)
    
    # User ID validasyonu (Free: Session ID, Premium: Real ID)
    if not validate_chat_user_id(x_user_id or "", user_plan):
        raise HTTPException(status_code=400, detail="Premium kullanıcılar için gerçek user ID gerekli")
    
    # User tablosu kullanılmıyor - sadece ai_messages ile çalışıyor
    
    # Quiz data'yı dict'e çevir ve validate et - TAMAMEN ESNEK
    logger.info(f"🔍 DEBUG: Body quiz_answers: {body.quiz_answers}")
    logger.info(f"🔍 DEBUG: Body dict: {body.dict()}")
    
    # Eğer quiz_answers boşsa, body'nin kendisini kullan
    if body.quiz_answers:
        quiz_dict = validate_input_data(body.quiz_answers, [])
    else:
        # Body'nin kendisini kullan (quiz_answers field'ı yoksa)
        body_dict = body.dict()
        body_dict.pop('available_supplements', None)  # Supplement field'ını çıkar
        quiz_dict = validate_input_data(body_dict, [])
    
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
            request_payload=quiz_dict,
            response_payload=data,
            model_used="openrouter"
        )
    except Exception as e:
        pass  # Silent fail for production
    
    # Test recommendations ekle (sadece premium+ kullanıcılar için)
    logger.info(f"🔍 DEBUG: User plan: {user_plan}")
    if user_plan in ["premium", "premium_plus"]:
        try:
            # Quiz verisini al (yeni gönderilen veri)
            logger.info(f"🔍 DEBUG: Quiz dict: {quiz_dict}")
            if quiz_dict:
                # Quiz verisini AI'ya gönder
                quiz_info_parts = []
                for key, value in quiz_dict.items():
                    if isinstance(value, list):
                        quiz_info_parts.append(f"{key}: {', '.join(map(str, value))}")
                    else:
                        quiz_info_parts.append(f"{key}: {value}")
                user_info = f"Quiz verileri: {', '.join(quiz_info_parts)}\n"
                
                ai_context = f"""
KULLANICI QUIZ CEVAPLARI:
{user_info}

GÖREV: Quiz cevaplarına göre test öner. Maksimum 3 test öner.

KURALLAR:
- Aile hastalık geçmişi varsa ilgili testleri öner
- Yaş/cinsiyet risk faktörlerini değerlendir
- Sadece gerekli testleri öner

ÖNEMLİ: 
- Ailede diyabet varsa HbA1c, açlık kan şekeri testleri öner
- Ailede kalp hastalığı varsa lipid profili, kardiyovasküler testler öner
- Yaş 40+ ise genel sağlık taraması testleri öner
- Yaş 50+ ise kanser tarama testleri öner
- Sadece gerçekten gerekli olan testleri öner

JSON formatında yanıt ver:
{{"recommended_tests": [{{"test_name": "Test Adı", "reason": "Neden önerildiği", "benefit": "Faydası"}}]}}
"""
                
                from backend.openrouter_client import get_ai_response
                ai_response = await get_ai_response(
                    system_prompt="Sen bir sağlık danışmanısın. Kullanıcının verilerine göre test önerileri yapıyorsun. Sadece JSON formatında kısa ve öz cevap ver.",
                    user_message=ai_context
                )
                
                # Debug: AI response'u log et
                logger.info(f"🔍 DEBUG: Quiz AI response: {ai_response}")
                
                # AI response'unu parse et
                import json
                try:
                    cleaned_response = ai_response.strip()
                    if cleaned_response.startswith('```json'):
                        json_start = cleaned_response.find('```json') + 7
                        json_end = cleaned_response.find('```', json_start)
                        if json_end != -1:
                            cleaned_response = cleaned_response[json_start:json_end].strip()
                        else:
                            cleaned_response = cleaned_response[json_start:].strip()
                    elif cleaned_response.startswith('```'):
                        json_start = cleaned_response.find('```') + 3
                        json_end = cleaned_response.find('```', json_start)
                        if json_end != -1:
                            cleaned_response = cleaned_response[json_start:json_end].strip()
                        else:
                            cleaned_response = cleaned_response[json_start:].strip()
                    
                    cleaned_response = cleaned_response.replace('\n', ' ').replace('\r', '')
                    if not cleaned_response.strip().endswith('}'):
                        last_brace = cleaned_response.rfind('}')
                        if last_brace != -1:
                            cleaned_response = cleaned_response[:last_brace + 1]
                        else:
                            cleaned_response = '{"recommended_tests": []}'
                    
                    parsed_response = json.loads(cleaned_response)
                    if "recommended_tests" in parsed_response:
                        recommended_tests = parsed_response["recommended_tests"][:3]
                        
                        # Response oluştur
                        test_rec_response = {
                            "title": "Test Önerileri",
                            "recommended_tests": recommended_tests,
                            "analysis_summary": "Quiz verilerine göre analiz tamamlandı",
                            "disclaimer": "Bu öneriler bilgilendirme amaçlıdır. Test yaptırmadan önce doktorunuza danışın."
                        }
                        
                        data["test_recommendations"] = test_rec_response
                except Exception as parse_error:
                    logger.error(f"🔍 DEBUG: Quiz test recommendations parse hatası: {parse_error}")
                    
        except Exception as e:
            logger.error(f"🔍 DEBUG: Quiz test recommendations hatası: {e}")
    
    # Return quiz response
    return data

@app.post("/ai/lab/single", response_model=LabAnalysisResponse)
def analyze_single_lab(body: SingleLabRequest,
                        current_user: str = Depends(get_current_user),
                       db: Session = Depends(get_db),
                        x_user_id: str | None = Header(default=None),
                        x_user_level: int | None = Header(default=None)):
    """Analyze single lab test result with historical trend analysis"""
    
    # Plan kontrolü
    user_plan = get_user_plan_from_headers(x_user_level)
    
    # Free kullanıcı engeli - Lab testleri premium özellik
    if user_plan == "free":
        raise HTTPException(status_code=403, detail="Lab test analizi premium özelliktir")
    
    # User ID validasyonu (Free: Session ID, Premium: Real ID)
    if not validate_chat_user_id(x_user_id or "", user_plan):
        raise HTTPException(status_code=400, detail="Premium kullanıcılar için gerçek user ID gerekli")
    
    # User tablosu kullanılmıyor - sadece ai_messages ile çalışıyor
    
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
        prior_msgs = get_ai_messages(db, external_user_id=x_user_id, limit=AI_MESSAGES_LIMIT)
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
        pass  # Silent fail for production
    
    return data

@app.post("/ai/lab/session", response_model=SingleSessionResponse)
def analyze_single_session(body: SingleSessionRequest,
                          current_user: str = Depends(get_current_user),
                          db: Session = Depends(get_db),
                          x_user_id: str | None = Header(default=None),
                          x_user_level: int | None = Header(default=None)):
    """Analyze single lab session with multiple tests"""
    
    # Plan kontrolü
    user_plan = get_user_plan_from_headers(x_user_level)
    
    # Free kullanıcı engeli - Lab testleri premium özellik
    if user_plan == "free":
        raise HTTPException(status_code=403, detail="Lab test analizi premium özelliktir")
    
    # User ID validasyonu (Free: Session ID, Premium: Real ID)
    if not validate_chat_user_id(x_user_id or "", user_plan):
        raise HTTPException(status_code=400, detail="Premium kullanıcılar için gerçek user ID gerekli")
    
    # User tablosu kullanılmıyor - sadece ai_messages ile çalışıyor
    
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
    session_date = body.session_date or body.date or datetime.now().strftime("%Y-%m-%d")
    laboratory = body.laboratory or body.lab or "Bilinmeyen Laboratuvar"
    
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
async def analyze_multiple_lab_summary(body: MultipleLabRequest,
                                 current_user: str = Depends(get_current_user),
                                 db: Session = Depends(get_db),
                                 x_user_id: str | None = Header(default=None),
                                 x_user_level: int | None = Header(default=None)):
    """Generate general summary of multiple lab tests with supplement recommendations and progress tracking"""
    
    # Plan kontrolü
    user_plan = get_user_plan_from_headers(x_user_level)
    
    # Free kullanıcı engeli - Lab testleri premium özellik
    if user_plan == "free":
        raise HTTPException(status_code=403, detail="Lab test analizi premium özelliktir")
    
    # User ID validasyonu (Free: Session ID, Premium: Real ID)
    if not validate_chat_user_id(x_user_id or "", user_plan):
        raise HTTPException(status_code=400, detail="Premium kullanıcılar için gerçek user ID gerekli")
    
    # User tablosu kullanılmıyor - sadece ai_messages ile çalışıyor
    
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
        prior_msgs = get_ai_messages(db, external_user_id=x_user_id, limit=AI_MESSAGES_LIMIT_LARGE)
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
    
    # Test recommendations ekle (sadece premium+ kullanıcılar için)
    if user_plan in ["premium", "premium_plus"]:
        try:
            # Lab verisini al (yeni gönderilen veri)
            if all_tests_dict:
                # Lab verisini AI'ya gönder
                lab_info_parts = []
                for test in all_tests_dict:
                    if "name" in test:
                        lab_info_parts.append(f"{test['name']}: {test.get('value', 'N/A')} ({test.get('reference_range', 'N/A')})")
                lab_info = f"Lab verileri: {', '.join(lab_info_parts)}\n"
                
                ai_context = f"""
KULLANICI LAB SONUÇLARI:
{lab_info}

GÖREV: Lab sonuçlarına göre test öner. Maksimum 3 test öner.

KURALLAR:
- Sadece anormal değerler için test öner
- Mevcut değerleri referans al
- Normal değerlere gereksiz test önerme

ÖNEMLİ:
- Düşük hemoglobin varsa demir, ferritin testleri öner
- Yüksek glukoz varsa HbA1c, OGTT testleri öner
- Anormal lipid değerleri varsa kardiyovasküler testler öner
- Sadece gerçekten gerekli olan testleri öner

JSON formatında yanıt ver:
{{"recommended_tests": [{{"test_name": "Test Adı", "reason": "Mevcut değerlerinizle neden önerildiği", "benefit": "Faydası"}}]}}
"""
                
                from backend.openrouter_client import get_ai_response
                
                # AI'ya gönder
                ai_response = await get_ai_response(
                    system_prompt="Sen bir sağlık danışmanısın. Kullanıcının verilerine göre test önerileri yapıyorsun. Sadece JSON formatında kısa ve öz cevap ver.",
                    user_message=ai_context
                )
                
                # AI response'unu parse et
                import json
                try:
                    cleaned_response = ai_response.strip()
                    if cleaned_response.startswith('```json'):
                        json_start = cleaned_response.find('```json') + 7
                        json_end = cleaned_response.find('```', json_start)
                        if json_end != -1:
                            cleaned_response = cleaned_response[json_start:json_end].strip()
                        else:
                            cleaned_response = cleaned_response[json_start:].strip()
                    elif cleaned_response.startswith('```'):
                        json_start = cleaned_response.find('```') + 3
                        json_end = cleaned_response.find('```', json_start)
                        if json_end != -1:
                            cleaned_response = cleaned_response[json_start:json_end].strip()
                        else:
                            cleaned_response = cleaned_response[json_start:].strip()
                    
                    cleaned_response = cleaned_response.replace('\n', ' ').replace('\r', '')
                    if not cleaned_response.strip().endswith('}'):
                        last_brace = cleaned_response.rfind('}')
                        if last_brace != -1:
                            cleaned_response = cleaned_response[:last_brace + 1]
                        else:
                            cleaned_response = '{"recommended_tests": []}'
                    
                    parsed_response = json.loads(cleaned_response)
                    if "recommended_tests" in parsed_response:
                        recommended_tests = parsed_response["recommended_tests"][:3]
                        
                        # Response oluştur
                        test_rec_response = {
                            "title": "Test Önerileri",
                            "recommended_tests": recommended_tests,
                            "analysis_summary": "Lab verilerine göre analiz tamamlandı",
                            "disclaimer": "Bu öneriler bilgilendirme amaçlıdır. Test yaptırmadan önce doktorunuza danışın."
                        }
                        
                        data["test_recommendations"] = test_rec_response
                except Exception as parse_error:
                    print(f"🔍 DEBUG: Lab summary test recommendations parse hatası: {parse_error}")
                    
        except Exception as e:
            print(f"🔍 DEBUG: Lab summary test recommendations hatası: {e}")
    
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
    lab_messages = get_ai_messages(db, external_user_id=user_id, message_type="lab_single", limit=LAB_MESSAGES_LIMIT)
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
    if len(lab_history) >= MIN_LAB_TESTS_FOR_COMPARISON:
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

@app.post("/ai/premium-plus/diet-recommendations")
async def premium_plus_diet_recommendations(
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
    x_user_id: str | None = Header(default=None),
    x_user_level: int | None = Header(default=None)
):
    """Premium Plus kullanıcıları için detaylı beslenme önerileri"""
    
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
        user_plan = "free"
    
    if user_plan != "premium_plus":
        raise HTTPException(
            status_code=403, 
            detail="Bu özellik sadece Premium Plus kullanıcıları için mevcuttur"
        )
    
    # User ID validasyonu
    if not x_user_id:
        raise HTTPException(status_code=400, detail="User ID gerekli")
    
    # Quiz geçmişini al
    quiz_messages = get_user_ai_messages_by_type(db, x_user_id, "quiz", QUIZ_LAB_ANALYSES_LIMIT)
    
    # Lab analizlerini al - Helper fonksiyon kullan
    lab_tests = get_standardized_lab_data(db, x_user_id, 20)
    
    # Veri kontrolü - En az bir veri kaynağı olmalı
    has_quiz_data = quiz_messages and any(msg.request_payload for msg in quiz_messages)
    has_lab_data = lab_tests and len(lab_tests) > 0
    
    if not has_quiz_data and not has_lab_data:
        raise HTTPException(
            status_code=400, 
            detail="Kişiselleştirilmiş beslenme önerileri için önce quiz yapmanız veya lab sonuçlarınızı paylaşmanız gerekiyor. Lütfen önce sağlık quizini tamamlayın veya lab test sonuçlarınızı girin."
        )
    
    # AI'ya gönderilecek context'i hazırla
    user_context = {}
    
    # Quiz verilerini context'e ekle
    if quiz_messages:
        user_context["quiz_data"] = []
        for msg in quiz_messages:
            if msg.request_payload:
                user_context["quiz_data"].append(msg.request_payload)
    
    # Lab verilerini context'e ekle
    if lab_tests:
        user_context["lab_data"] = {
            "tests": lab_tests
        }
    
    # System prompt - Sadece beslenme odaklı
    system_prompt = f"""Sen Longo AI'sın - Premium Plus kullanıcıları için özel beslenme danışmanısın.

GÖREVİN: Kullanıcının sağlık quiz profili ve lab verilerine göre kişiselleştirilmiş DETAYLI beslenme önerileri ver.

KULLANICI VERİLERİ:
{str(user_context)}

VERİ ANALİZİ:
- Quiz sonuçlarından yaş, cinsiyet, sağlık hedefleri, aktivite seviyesi
- Lab sonuçlarından vitamin/mineral eksiklikleri, sağlık durumu
- Bu verileri birleştirerek holistik beslenme yaklaşımı

YANIT FORMATI:
1. MEVCUT DURUM ANALİZİ
   - Kullanıcının quiz verilerinden çıkarılan sağlık profili
   - Lab sonuçlarından tespit edilen eksiklikler/riskler
   - Genel sağlık durumu değerlendirmesi

2. DETAYLI BESLENME ÖNERİLERİ
   - Her öneri için NEDEN açıkla
   - Lab sonuçlarına göre eksik vitamin/mineraller için spesifik besin önerileri
   - Quiz'deki hedeflere uygun makro besin dağılımı (karbonhidrat, protein, yağ)
   - Öğün planlama ve porsiyon önerileri (gram cinsinden)
   - Supplement ile beslenme dengesi
   - Su tüketimi ve hidrasyon stratejileri
   - Besin kombinasyonları ve emilim ipuçları

3. ÖĞÜN PLANLAMA
   - Kahvaltı, öğle, akşam yemeği önerileri
   - Ara öğün stratejileri
   - Egzersiz öncesi/sonrası beslenme
   - Haftalık menü önerileri

4. PERFORMANS BESLENMESİ
   - Enerji seviyelerini optimize eden besinler
   - Kas gelişimi için protein kaynakları
   - Anti-inflamatuar besinler
   - Bağışıklık güçlendirici besinler

5. HAFTALIK MENÜ ÖNERİSİ
   - Detaylı menü planı
   - Porsiyon miktarları

6. SUPPLEMENT ÖNERİLERİ
   - Hangi supplement'lerin neden gerekli olduğu
   - Dozaj önerileri

KISITLAMALAR:
- Sadece genel öneriler, tıbbi tavsiye değil
- Diyetisyen yerine geçmez
- Güvenlik öncelikli yaklaşım

DİL: SADECE TÜRKÇE YANIT VER!"""

    # User message'ı hazırla
    user_message = f"""Kullanıcının mevcut durumu:

KULLANICI BİLGİLERİ:
"""
    
    # Quiz verilerini ekle
    if user_context:
        user_message += f"\nQUIZ VERİLERİ:\n"
        for key, value in user_context.items():
            if value and key in ['yas', 'cinsiyet', 'hedef', 'aktivite', 'boy', 'kilo', 'quiz_sonuc', 'quiz_summary', 'quiz_gecmisi']:
                user_message += f"- {key.upper()}: {value}\n"
    
    # Quiz geçmişini ekle
    if quiz_messages:
        user_message += f"\nSON SAĞLIK QUIZ PROFİLİ:\n"
        for msg in quiz_messages[-1:]:  # En son quiz
            if msg.request_payload:
                user_message += f"- Quiz verileri: {msg.request_payload}\n"
    
    # Lab analizlerini ekle
    if lab_tests:
        user_message += f"\nLAB ANALİZLERİ:\n"
        for test in lab_tests[:2]:  # İlk 2 test
            user_message += f"- {test.get('name', 'N/A')}: {test.get('value', 'N/A')} ({test.get('reference_range', 'N/A')})\n"
    
    # Global context'ten tüm verileri ekle
    if user_context:
        # Quiz verilerini ekle
        quiz_keys = ['yas', 'cinsiyet', 'hedef', 'aktivite', 'boy', 'kilo', 'quiz_supplements', 'quiz_priority', 'quiz_tarih']
        quiz_data_found = False
        for key in quiz_keys:
            if key in user_context and user_context[key]:
                if not quiz_data_found:
                    user_message += f"\nGLOBAL QUIZ VERİLERİ:\n"
                    quiz_data_found = True
                user_message += f"- {key.upper()}: {user_context[key]}\n"
        
        # Lab verilerini ekle
        lab_keys = ['lab_gecmisi', 'lab_genel_durum', 'lab_summary', 'lab_tarih', 'son_lab_test', 'son_lab_deger', 'son_lab_durum']
        lab_data_found = False
        for key in lab_keys:
            if key in user_context and user_context[key]:
                if not lab_data_found:
                    user_message += f"\nGLOBAL LAB VERİLERİ:\n"
                    lab_data_found = True
                user_message += f"- {key.upper()}: {user_context[key]}\n"
    
    user_message += f"""

Lütfen bu kullanıcı için DETAYLI beslenme önerileri hazırla. Sadece beslenme odaklı, kapsamlı ve uygulanabilir öneriler ver."""

    # AI çağrısı
    try:
        from backend.openrouter_client import get_ai_response
        ai_response = await get_ai_response(
            system_prompt=system_prompt,
            user_message=user_message
        )
        
        # AI mesajını kaydet
        create_ai_message(
            db=db,
            external_user_id=x_user_id,
            message_type="diet_recommendations",
            request_payload={},
            response_payload={"recommendations": ai_response},
            model_used="openrouter"
        )
        
        return {
            "success": True,
            "message": "Beslenme önerileri hazırlandı",
            "recommendations": ai_response,
            "disclaimer": "Bu öneriler bilgilendirme amaçlıdır. Tıbbi kararlar için doktorunuza danışın."
        }
        
    except Exception as e:
        print(f"🔍 DEBUG: Diet recommendations hatası: {e}")
        raise HTTPException(status_code=500, detail=f"Beslenme önerileri hazırlanırken hata: {str(e)}")

@app.post("/ai/premium-plus/exercise-recommendations")
async def premium_plus_exercise_recommendations(
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
    x_user_id: str | None = Header(default=None),
    x_user_level: int | None = Header(default=None)
):
    """Premium Plus kullanıcıları için detaylı egzersiz önerileri"""
    
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
        user_plan = "free"
    
    if user_plan != "premium_plus":
        raise HTTPException(
            status_code=403, 
            detail="Bu özellik sadece Premium Plus kullanıcıları için mevcuttur"
        )
    
    # User ID validasyonu
    if not x_user_id:
        raise HTTPException(status_code=400, detail="User ID gerekli")
    
    # Quiz geçmişini al
    quiz_messages = get_user_ai_messages_by_type(db, x_user_id, "quiz", QUIZ_LAB_ANALYSES_LIMIT)
    
    # Lab analizlerini al - Helper fonksiyon kullan
    lab_tests = get_standardized_lab_data(db, x_user_id, 20)
    
    # Veri kontrolü - En az bir veri kaynağı olmalı
    has_quiz_data = quiz_messages and any(msg.request_payload for msg in quiz_messages)
    has_lab_data = lab_tests and len(lab_tests) > 0
    
    if not has_quiz_data and not has_lab_data:
        raise HTTPException(
            status_code=400, 
            detail="Kişiselleştirilmiş egzersiz önerileri için önce quiz yapmanız veya lab sonuçlarınızı paylaşmanız gerekiyor. Lütfen önce sağlık quizini tamamlayın veya lab test sonuçlarınızı girin."
        )
    
    # AI'ya gönderilecek context'i hazırla
    user_context = {}
    
    # Quiz verilerini context'e ekle
    if quiz_messages:
        user_context["quiz_data"] = []
        for msg in quiz_messages:
            if msg.request_payload:
                user_context["quiz_data"].append(msg.request_payload)
    
    # Lab verilerini context'e ekle
    if lab_tests:
        user_context["lab_data"] = {
            "tests": lab_tests
        }
    
    # System prompt - Sadece egzersiz odaklı
    system_prompt = f"""Sen Longo AI'sın - Premium Plus kullanıcıları için özel egzersiz danışmanısın.

GÖREVİN: Kullanıcının sağlık quiz profili ve lab verilerine göre kişiselleştirilmiş DETAYLI egzersiz önerileri ver.

KULLANICI VERİLERİ:
{str(user_context)}

VERİ ANALİZİ:
- Quiz sonuçlarından yaş, cinsiyet, sağlık hedefleri, aktivite seviyesi
- Lab sonuçlarından sağlık durumu ve performans göstergeleri
- Bu verileri birleştirerek güvenli ve etkili egzersiz planı

YANIT FORMATI:
1. MEVCUT DURUM ANALİZİ
   - Kullanıcının quiz verilerinden çıkarılan fitness profili
   - Lab sonuçlarından tespit edilen sağlık durumu
   - Mevcut kondisyon seviyesi değerlendirmesi
   - Egzersiz hedefleri ve kısıtlamalar

2. DETAYLI EGZERSİZ PROGRAMI
   - Her öneri için NEDEN açıkla
   - Kullanıcının yaşına, kondisyonuna ve hedeflerine uygun
   - Haftalık program önerisi (kaç gün, ne kadar süre)
   - Kardiyovasküler, güç antrenmanı, esneklik dengesi
   - Başlangıç seviyesi için güvenli ve sürdürülebilir
   - Spesifik egzersiz hareketleri ve set/tekrar sayıları

3. GÜÇ ANTRENMANI
   - Vücut ağırlığı ve ağırlık antrenmanları
   - Kas gruplarına göre egzersiz dağılımı
   - Progresyon stratejileri
   - Form ve teknik önerileri

4. KARDİYOVASKÜLER
   - Koşu, yürüyüş, bisiklet önerileri
   - HIIT ve steady-state kardio dengesi
   - Kalp atış hızı hedefleri
   - Sürdürülebilir kardio programı

5. ESNEKLİK VE MOBİLİTE
   - Stretching ve yoga önerileri
   - Günlük mobilite rutinleri
   - Recovery ve rahatlama egzersizleri
   - Postür düzeltme egzersizleri

6. PERFORMANS VE RECOVERY
   - Egzersiz öncesi/sonrası rutinler
   - Uyku ve recovery önerileri
   - Sakatlanma önleme stratejileri
   - Motivasyon ve sürdürülebilirlik ipuçları

7. HAFTALIK PROGRAM ÖNERİSİ
   - Detaylı haftalık program
   - Günlük egzersiz planı

KISITLAMALAR:
- Sadece genel öneriler, tıbbi tavsiye değil
- Kişisel antrenör yerine geçmez
- Güvenlik öncelikli yaklaşım

DİL: SADECE TÜRKÇE YANIT VER!"""

    # User message'ı hazırla
    user_message = f"""Kullanıcının mevcut durumu:

KULLANICI BİLGİLERİ:
"""
    
    # Quiz verilerini ekle
    if user_context:
        user_message += f"\nQUIZ VERİLERİ:\n"
        for key, value in user_context.items():
            if value and key in ['yas', 'cinsiyet', 'hedef', 'aktivite', 'boy', 'kilo', 'quiz_sonuc', 'quiz_summary', 'quiz_gecmisi']:
                user_message += f"- {key.upper()}: {value}\n"
    
    # Quiz geçmişini ekle
    if quiz_messages:
        user_message += f"\nSON SAĞLIK QUIZ PROFİLİ:\n"
        for msg in quiz_messages[-1:]:  # En son quiz
            if msg.request_payload:
                user_message += f"- Quiz verileri: {msg.request_payload}\n"
    
    # Lab analizlerini ekle
    if lab_tests:
        user_message += f"\nLAB ANALİZLERİ:\n"
        for test in lab_tests[:2]:  # İlk 2 test
            user_message += f"- {test.get('name', 'N/A')}: {test.get('value', 'N/A')} ({test.get('reference_range', 'N/A')})\n"
    
    # Global context'ten tüm verileri ekle
    if user_context:
        # Quiz verilerini ekle
        quiz_keys = ['yas', 'cinsiyet', 'hedef', 'aktivite', 'boy', 'kilo', 'quiz_supplements', 'quiz_priority', 'quiz_tarih']
        quiz_data_found = False
        for key in quiz_keys:
            if key in user_context and user_context[key]:
                if not quiz_data_found:
                    user_message += f"\nGLOBAL QUIZ VERİLERİ:\n"
                    quiz_data_found = True
                user_message += f"- {key.upper()}: {user_context[key]}\n"
        
        # Lab verilerini ekle
        lab_keys = ['lab_gecmisi', 'lab_genel_durum', 'lab_summary', 'lab_tarih', 'son_lab_test', 'son_lab_deger', 'son_lab_durum']
        lab_data_found = False
        for key in lab_keys:
            if key in user_context and user_context[key]:
                if not lab_data_found:
                    user_message += f"\nGLOBAL LAB VERİLERİ:\n"
                    lab_data_found = True
                user_message += f"- {key.upper()}: {user_context[key]}\n"
    
    user_message += f"""

Lütfen bu kullanıcı için DETAYLI egzersiz önerileri hazırla. Sadece egzersiz odaklı, kapsamlı ve uygulanabilir öneriler ver."""

    # AI çağrısı
    try:
        from backend.openrouter_client import get_ai_response
        ai_response = await get_ai_response(
            system_prompt=system_prompt,
            user_message=user_message
        )
        
        # AI mesajını kaydet
        create_ai_message(
            db=db,
            external_user_id=x_user_id,
            message_type="exercise_recommendations",
            request_payload={},
            response_payload={"recommendations": ai_response},
            model_used="openrouter"
        )
        
        return {
            "success": True,
            "message": "Egzersiz önerileri hazırlandı",
            "recommendations": ai_response,
            "disclaimer": "Bu öneriler bilgilendirme amaçlıdır. Tıbbi kararlar için doktorunuza danışın."
        }
        
    except Exception as e:
        print(f"🔍 DEBUG: Exercise recommendations hatası: {e}")
        raise HTTPException(status_code=500, detail=f"Egzersiz önerileri hazırlanırken hata: {str(e)}")

@app.post("/ai/premium-plus/lifestyle-recommendations")
async def premium_plus_lifestyle_recommendations(
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
    x_user_id: str | None = Header(default=None),
    x_user_level: int | None = Header(default=None)
):
    """Premium Plus kullanıcıları için beslenme, spor ve egzersiz önerileri"""
    
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
        user_plan = "free"
    
    if user_plan != "premium_plus":
        raise HTTPException(
            status_code=403, 
            detail="Bu özellik sadece Premium Plus kullanıcıları için mevcuttur"
        )
    
    # User ID validasyonu
    if not x_user_id:
        raise HTTPException(status_code=400, detail="User ID gerekli")
    
    # User tablosu kullanılmıyor - sadece ai_messages ile çalışıyor
    
    # Quiz geçmişini al
    quiz_messages = get_user_ai_messages_by_type(db, x_user_id, "quiz", QUIZ_LAB_ANALYSES_LIMIT)
    
    # Lab analizlerini al - Helper fonksiyon kullan
    lab_tests = get_standardized_lab_data(db, x_user_id, 20)
    
    # AI'ya gönderilecek context'i hazırla
    user_context = {}
    
    # Quiz verilerini context'e ekle
    if quiz_messages:
        user_context["quiz_data"] = []
        for msg in quiz_messages:
            if msg.request_payload:
                user_context["quiz_data"].append(msg.request_payload)
    
    # Lab verilerini context'e ekle
    if lab_tests:
        user_context["lab_data"] = {
            "tests": lab_tests
        }
    
    # System prompt - Premium Plus özel
    system_prompt = f"""Sen Longo AI'sın - Premium Plus kullanıcıları için özel beslenme, spor ve egzersiz danışmanısın.

🎯 GÖREVİN: Kullanıcının sağlık quiz profili ve lab verilerine göre kişiselleştirilmiş beslenme, spor ve egzersiz önerileri ver.

📊 KULLANICI VERİLERİ:
{str(user_context)}

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

KULLANICI BİLGİLERİ:
"""
    
    # Quiz verilerini ekle
    if user_context:
        user_message += f"\nQUIZ VERİLERİ:\n"
        for key, value in user_context.items():
            if value and key in ['yas', 'cinsiyet', 'hedef', 'aktivite', 'boy', 'kilo', 'quiz_sonuc', 'quiz_summary', 'quiz_gecmisi']:
                user_message += f"- {key.upper()}: {value}\n"
    
    # Quiz geçmişini ekle
    if quiz_messages:
        user_message += f"\nSON SAĞLIK QUIZ PROFİLİ:\n"
        for msg in quiz_messages[-1:]:  # En son quiz
            if msg.request_payload:
                user_message += f"- Quiz verileri: {msg.request_payload}\n"
    
    # Lab analizlerini ekle
    if lab_tests:
        user_message += f"\nLAB ANALİZLERİ:\n"
        for test in lab_tests[:2]:  # İlk 2 test
            user_message += f"- {test.get('name', 'N/A')}: {test.get('value', 'N/A')} ({test.get('reference_range', 'N/A')})\n"
    
    # Global context'ten tüm verileri ekle
    if user_context:
        # Quiz verilerini ekle
        quiz_keys = ['yas', 'cinsiyet', 'hedef', 'aktivite', 'boy', 'kilo', 'quiz_supplements', 'quiz_priority', 'quiz_tarih']
        quiz_data_found = False
        for key in quiz_keys:
            if key in user_context and user_context[key]:
                if not quiz_data_found:
                    user_message += f"\nGLOBAL QUIZ VERİLERİ:\n"
                    quiz_data_found = True
                user_message += f"- {key.upper()}: {user_context[key]}\n"
        
        # Lab verilerini ekle
        lab_keys = ['lab_gecmisi', 'lab_genel_durum', 'lab_summary', 'lab_tarih', 'son_lab_test', 'son_lab_deger', 'son_lab_durum']
        lab_data_found = False
        for key in lab_keys:
            if key in user_context and user_context[key]:
                if not lab_data_found:
                    user_message += f"\nGLOBAL LAB VERİLERİ:\n"
                    lab_data_found = True
                user_message += f"- {key.upper()}: {user_context[key]}\n"
    
    user_message += f"""

Bu bilgilere göre kullanıcı için kapsamlı beslenme, spor ve egzersiz önerileri hazırla. 
Kişiselleştirilmiş, sürdürülebilir ve güvenli bir program öner.

ÖNEMLİ: Response'u şu JSON formatında ver:

{{
  "nutrition_plan": "Beslenme önerileri buraya...",
  "exercise_plan": "Spor ve egzersiz programı buraya...",
  "lifestyle_tips": "Yaşam tarzı önerileri buraya..."
}}

Sadece bu 3 field'ı doldur, başka hiçbir şey ekleme!"""

    # AI'ya gönder
    try:
        from backend.openrouter_client import get_ai_response
        
        reply = await get_ai_response(system_prompt, user_message)
        
        # AI response'unu parse et
        try:
            import json
            parsed_reply = json.loads(reply)
            
            return {
                "status": "success",
                "nutrition_plan": parsed_reply.get("nutrition_plan", ""),
                "exercise_plan": parsed_reply.get("exercise_plan", ""),
                "lifestyle_tips": parsed_reply.get("lifestyle_tips", ""),
                "quiz_count": len(quiz_messages) if quiz_messages else 0,
                "lab_count": len(lab_tests) if lab_tests else 0
            }
        except json.JSONDecodeError:
            # JSON parse edilemezse eski formatı kullan
            return {
                "status": "success",
                "nutrition_plan": reply,
                "exercise_plan": "",
                "lifestyle_tips": "",
                "quiz_count": len(quiz_messages) if quiz_messages else 0,
                "lab_count": len(lab_tests) if lab_tests else 0
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
        ai_messages = get_ai_messages(db, external_user_id=x_user_id, limit=DEBUG_AI_MESSAGES_LIMIT)
        
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

# ---------- TEST ÖNERİSİ ENDPOINT ----------

async def get_test_recommendations_internal(
    db: Session,
    x_user_id: str,
    user_plan: str,
    source: str,
    max_recommendations: int = 3
):
    """Internal test recommendations function"""
    # Source validation
    if source not in ["quiz", "lab"]:
        return None
    
    # Free kullanıcı engeli - Test önerileri premium özellik
    if user_plan == "free":
        return None
    
    # User ID validasyonu
    if not validate_chat_user_id(x_user_id or "", user_plan):
        return None
    
    user = get_or_create_user(db, x_user_id, user_plan)
    
    try:
        # 1. Source'a göre veri toplama
        user_context = {}
        analysis_summary = ""
        
        if source == "quiz":
            # Sadece quiz verisi al
            quiz_messages = get_user_ai_messages_by_type(db, x_user_id, "quiz", QUIZ_LAB_ANALYSES_LIMIT)
            if quiz_messages:
                user_context["quiz_data"] = [msg.request_payload for msg in quiz_messages]
                analysis_summary = "Quiz verilerine göre analiz tamamlandı."
        
        elif source == "lab":
            # Sadece lab verisi al
            lab_tests = get_standardized_lab_data(db, x_user_id, 20)
            if lab_tests:
                user_context["lab_data"] = {
                    "tests": lab_tests
                }
                analysis_summary = "Lab verilerine göre analiz tamamlandı."
            else:
                # Lab verisi yoksa, yeni gönderilen veriyi kullan
                # Bu durumda lab summary endpoint'inden çağrılıyor olabilir
                analysis_summary = "Yeni lab verilerine göre analiz tamamlandı."
        
        # 2. Daha önce baktırılan testleri AI'ya bildir
        taken_test_names = []
        if "lab_data" in user_context and "tests" in user_context["lab_data"]:
            # Lab testlerinden test isimlerini çıkar
            for test in user_context["lab_data"]["tests"]:
                if "name" in test:
                    taken_test_names.append(test["name"])
        
        # 3. AI ile kişiselleştirilmiş öneri sistemi
        recommended_tests = []
        
        # AI'ya gönderilecek context'i hazırla
        quiz_count = len(user_context.get("quiz_data", [])) if "quiz_data" in user_context else 0
        lab_count = len(user_context.get("lab_data", {}).get("tests", [])) if "lab_data" in user_context else 0
        
        # Quiz verisi flexible olarak AI'ya gönder
        user_info = ""
        if "quiz_data" in user_context and user_context["quiz_data"]:
            quiz = user_context["quiz_data"][0]  # Son quiz
            # Quiz verisini flexible olarak formatla
            quiz_info_parts = []
            for key, value in quiz.items():
                if isinstance(value, list):
                    quiz_info_parts.append(f"{key}: {', '.join(map(str, value))}")
                else:
                    quiz_info_parts.append(f"{key}: {value}")
            user_info = f"Quiz verileri: {', '.join(quiz_info_parts)}\n"
        
        lab_info = ""
        if "lab_data" in user_context and user_context["lab_data"].get("tests"):
            lab_info = "Lab testleri:\n"
            for test in user_context["lab_data"]["tests"][:2]:
                if "name" in test:
                    lab_info += f"- {test['name']}: {test.get('value', 'N/A')} ({test.get('reference_range', 'N/A')})\n"
        
        # Daha önce yapılan testleri ekle
        taken_tests_info = ""
        if taken_test_names:
            taken_tests_info = f"\nDaha önce yapılan testler: {', '.join(taken_test_names)}\nBu testleri önerme!\n"
        
        # Source'a göre AI context hazırla
        if source == "quiz":
            ai_context = f"""
KULLANICI QUIZ CEVAPLARI:
{user_info}

{taken_tests_info}

GÖREV: Quiz cevaplarına göre test öner. Maksimum 3 test öner.

KURALLAR:
- Aile hastalık geçmişi varsa ilgili testleri öner
- Yaş/cinsiyet risk faktörlerini değerlendir
- Sadece gerekli testleri öner


ÖNEMLİ: 
- Ailede diyabet varsa HbA1c, açlık kan şekeri testleri öner
- Ailede kalp hastalığı varsa lipid profili, kardiyovasküler testler öner
- Yaş 40+ ise genel sağlık taraması testleri öner
- Yaş 50+ ise kanser tarama testleri öner
- Sadece gerçekten gerekli olan testleri öner

JSON formatında yanıt ver:
{{"recommended_tests": [{{"test_name": "Test Adı", "reason": "Neden önerildiği", "benefit": "Faydası"}}]}}
"""
        
        elif source == "lab":
            ai_context = f"""
MEVCUT LAB SONUÇLARI:
{lab_info}

{taken_tests_info}

GÖREV: Lab sonuçlarına göre test öner. Maksimum 3 test öner.

KURALLAR:
- Sadece anormal değerler için test öner
- Mevcut değerleri referans al
- Normal değerlere gereksiz test önerme

JSON formatında yanıt ver:
{{"recommended_tests": [{{"test_name": "Test Adı", "reason": "Mevcut değerlerinizle neden önerildiği", "benefit": "Faydası"}}]}}
"""
        
        try:
            from backend.openrouter_client import get_ai_response
            
            # AI'ya gönder
            ai_response = await get_ai_response(
                system_prompt="Sen bir sağlık danışmanısın. Kullanıcının verilerine göre test önerileri yapıyorsun. Sadece JSON formatında kısa ve öz cevap ver.",
                user_message=ai_context
            )
            
            # AI response'unu parse et
            import json
            try:
                # JSON parse etmeyi dene
                parsed_response = json.loads(ai_response)
                if "recommended_tests" in parsed_response:
                    recommended_tests = parsed_response["recommended_tests"][:max_recommendations]
                else:
                    raise ValueError("AI response format hatası")
            except (json.JSONDecodeError, ValueError, KeyError) as parse_error:
                # AI response'u temizle ve tekrar dene
                cleaned_response = ai_response.strip()
                if cleaned_response.startswith('```json'):
                    json_start = cleaned_response.find('```json') + 7
                    json_end = cleaned_response.find('```', json_start)
                    if json_end != -1:
                        cleaned_response = cleaned_response[json_start:json_end].strip()
                    else:
                        cleaned_response = cleaned_response[json_start:].strip()
                elif cleaned_response.startswith('```'):
                    json_start = cleaned_response.find('```') + 3
                    json_end = cleaned_response.find('```', json_start)
                    if json_end != -1:
                        cleaned_response = cleaned_response[json_start:json_end].strip()
                    else:
                        cleaned_response = cleaned_response[json_start:].strip()
                
                try:
                    cleaned_response = cleaned_response.replace('\n', ' ').replace('\r', '')
                    if not cleaned_response.strip().endswith('}'):
                        last_brace = cleaned_response.rfind('}')
                        if last_brace != -1:
                            cleaned_response = cleaned_response[:last_brace + 1]
                        else:
                            cleaned_response = '{"recommended_tests": []}'
                    
                    parsed_response = json.loads(cleaned_response)
                    if "recommended_tests" in parsed_response:
                        recommended_tests = parsed_response["recommended_tests"][:max_recommendations]
                    else:
                        raise ValueError("Temizlenmiş AI response format hatası")
                except:
                    raise ValueError("AI response parse edilemedi")
                
        except Exception as e:
            print(f"🔍 DEBUG: AI test önerisi hatası: {e}")
            return None
        
        # Response oluştur
        response_data = {
            "title": "Test Önerileri",
            "recommended_tests": recommended_tests,
            "analysis_summary": analysis_summary or "Kullanıcı verisi bulunamadı",
            "disclaimer": "Bu öneriler bilgilendirme amaçlıdır. Test yaptırmadan önce doktorunuza danışın."
        }
        
        return response_data
        
    except Exception as e:
        print(f"🔍 DEBUG: Test recommendations internal hatası: {e}")
        return None

@app.post("/ai/test-recommendations", response_model=TestRecommendationResponse)
async def get_test_recommendations(body: TestRecommendationRequest,
                                 current_user: str = Depends(get_current_user),
                                 db: Session = Depends(get_db),
                                 x_user_id: str | None = Header(default=None),
                                 x_user_level: int | None = Header(default=None),
                                 source: str = Query(description="Data source: quiz or lab")):
    """Premium/Premium Plus kullanıcılar için kişiselleştirilmiş test önerileri"""
    
    # Source validation
    if source not in ["quiz", "lab"]:
        raise HTTPException(status_code=400, detail="Source must be 'quiz' or 'lab'")
    
    # Plan kontrolü
    user_plan = get_user_plan_from_headers(x_user_level)
    
    # Free kullanıcı engeli - Test önerileri premium özellik
    if user_plan == "free":
        raise HTTPException(status_code=403, detail="Test önerileri premium özelliktir")
    
    # User ID validasyonu
    if not validate_chat_user_id(x_user_id or "", user_plan):
        raise HTTPException(status_code=400, detail="Premium kullanıcılar için gerçek user ID gerekli")
    
    user = get_or_create_user(db, x_user_id, user_plan)
    
    try:
        # 1. Source'a göre veri toplama
        user_context = {}
        analysis_summary = ""
        
        if source == "quiz":
            # Sadece quiz verisi al
            quiz_messages = get_user_ai_messages_by_type(db, x_user_id, "quiz", QUIZ_LAB_ANALYSES_LIMIT)
            print(f"🔍 DEBUG: Quiz messages found: {len(quiz_messages) if quiz_messages else 0}")
            if quiz_messages:
                user_context["quiz_data"] = [msg.request_payload for msg in quiz_messages]
                analysis_summary = "Quiz verilerine göre analiz tamamlandı."
                print(f"🔍 DEBUG: Quiz data: {user_context['quiz_data']}")
        
        elif source == "lab":
            # Sadece lab verisi al
            lab_tests = get_standardized_lab_data(db, x_user_id, 20)
            if lab_tests:
                user_context["lab_data"] = {
                    "tests": lab_tests
                }
                analysis_summary = "Lab verilerine göre analiz tamamlandı."
        
        # 2. Daha önce baktırılan testleri AI'ya bildir
        taken_test_names = []
        if body.exclude_taken_tests and "lab_data" in user_context and "tests" in user_context["lab_data"]:
            # Lab testlerinden test isimlerini çıkar
            for test in user_context["lab_data"]["tests"]:
                if "name" in test:
                    test_name = test["name"]
                    taken_test_names.append(test_name)
        
        # 3. Tüm testleri AI'ya ver (filtreleme yapma)
        available_tests = AVAILABLE_TESTS
        
        # 4. AI ile kişiselleştirilmiş öneri sistemi
        recommended_tests = []
        
        # AI'ya gönderilecek context'i hazırla
        quiz_count = len(user_context.get("quiz_data", [])) if "quiz_data" in user_context else 0
        lab_count = len(user_context.get("lab_data", {}).get("tests", [])) if "lab_data" in user_context else 0
        
        # Quiz verisi flexible olarak AI'ya gönder
        user_info = ""
        if "quiz_data" in user_context and user_context["quiz_data"]:
            quiz = user_context["quiz_data"][0]  # Son quiz
            # Quiz verisini flexible olarak formatla
            quiz_info_parts = []
            for key, value in quiz.items():
                if isinstance(value, list):
                    quiz_info_parts.append(f"{key}: {', '.join(map(str, value))}")
                else:
                    quiz_info_parts.append(f"{key}: {value}")
            user_info = f"Quiz verileri: {', '.join(quiz_info_parts)}\n"
        
        lab_info = ""
        if "lab_data" in user_context and user_context["lab_data"].get("tests"):
            lab_info = "Lab testleri:\n"
            for test in user_context["lab_data"]["tests"][:2]:
                if "name" in test:
                    lab_info += f"- {test['name']}: {test.get('value', 'N/A')} ({test.get('reference_range', 'N/A')})\n"
        
        # Daha önce yapılan testleri ekle
        taken_tests_info = ""
        if taken_test_names:
            taken_tests_info = f"\nDaha önce yapılan testler: {', '.join(taken_test_names)}\nBu testleri önerme!\n"
        
        # Source'a göre AI context hazırla
        if source == "quiz":
            print(f"🔍 DEBUG: Quiz user_info: {user_info}")
            print(f"🔍 DEBUG: Quiz taken_tests_info: {taken_tests_info}")
            
            ai_context = f"""
KULLANICI QUIZ CEVAPLARI:
{user_info}

{taken_tests_info}

GÖREV: Quiz cevaplarına göre test öner. Maksimum 3 test öner.

KURALLAR:
- Aile hastalık geçmişi varsa ilgili testleri öner
- Yaş/cinsiyet risk faktörlerini değerlendir
- Sadece gerekli testleri öner

ÖNEMLİ: 
- Ailede diyabet varsa HbA1c, açlık kan şekeri testleri öner
- Ailede kalp hastalığı varsa lipid profili, kardiyovasküler testler öner
- Yaş 40+ ise genel sağlık taraması testleri öner
- Yaş 50+ ise kanser tarama testleri öner
- Sadece gerçekten gerekli olan testleri öner

JSON formatında yanıt ver:
{{"recommended_tests": [{{"test_name": "Test Adı", "reason": "Neden önerildiği", "benefit": "Faydası"}}]}}
"""
        
        elif source == "lab":
            ai_context = f"""
MEVCUT LAB SONUÇLARI:
{lab_info}

{taken_tests_info}

GÖREV: Lab sonuçlarına göre test öner. Maksimum 3 test öner.

KURALLAR:
- Sadece anormal değerler için test öner
- Mevcut değerleri referans al
- Normal değerlere gereksiz test önerme

JSON formatında yanıt ver:
{{"recommended_tests": [{{"test_name": "Test Adı", "reason": "Mevcut değerlerinizle neden önerildiği", "benefit": "Faydası"}}]}}
"""
        
        try:
            from backend.openrouter_client import get_ai_response
            
            # AI'ya gönder
            ai_response = await get_ai_response(
                system_prompt="Sen bir sağlık danışmanısın. Kullanıcının verilerine göre test önerileri yapıyorsun. Sadece JSON formatında kısa ve öz cevap ver.",
                user_message=ai_context
            )
            
            print(f"🔍 DEBUG: AI Response for {source}: {ai_response}")
            
            # AI response'unu parse et
            import json
            try:
                # JSON parse etmeyi dene
                parsed_response = json.loads(ai_response)
                if "recommended_tests" in parsed_response:
                    recommended_tests = parsed_response["recommended_tests"][:body.max_recommendations]
                    print(f"🔍 DEBUG: AI önerileri başarılı: {len(recommended_tests)} adet")
                else:
                    raise ValueError("AI response format hatası")
            except (json.JSONDecodeError, ValueError, KeyError) as parse_error:
                print(f"🔍 DEBUG: JSON parse hatası: {parse_error}")
                print(f"🔍 DEBUG: Raw response: {ai_response}")
                
                # AI response'u temizle ve tekrar dene
                cleaned_response = ai_response.strip()
                if cleaned_response.startswith('```json'):
                    # ```json ile başlayan kısmı çıkar
                    json_start = cleaned_response.find('```json') + 7
                    json_end = cleaned_response.find('```', json_start)
                    if json_end != -1:
                        cleaned_response = cleaned_response[json_start:json_end].strip()
                    else:
                        cleaned_response = cleaned_response[json_start:].strip()
                elif cleaned_response.startswith('```'):
                    # Sadece ``` ile başlayan kısmı çıkar
                    json_start = cleaned_response.find('```') + 3
                    json_end = cleaned_response.find('```', json_start)
                    if json_end != -1:
                        cleaned_response = cleaned_response[json_start:json_end].strip()
                    else:
                        cleaned_response = cleaned_response[json_start:].strip()
                
                try:
                    # JSON'u daha agresif temizle
                    cleaned_response = cleaned_response.replace('\n', ' ').replace('\r', '')
                    
                    # Eğer JSON kesilmişse, son kısmı tamamla
                    if not cleaned_response.strip().endswith('}'):
                        last_brace = cleaned_response.rfind('}')
                        if last_brace != -1:
                            cleaned_response = cleaned_response[:last_brace + 1]
                        else:
                            # Hiç } yoksa, basit bir response oluştur
                            cleaned_response = '{"recommended_tests": []}'
                    
                    parsed_response = json.loads(cleaned_response)
                    if "recommended_tests" in parsed_response:
                        recommended_tests = parsed_response["recommended_tests"][:body.max_recommendations]
                        print(f"🔍 DEBUG: Temizlenmiş AI önerileri başarılı: {len(recommended_tests)} adet")
                    else:
                        raise ValueError("Temizlenmiş AI response format hatası")
                except:
                    # Son çare: AI response parse edilemezse fallback
                    raise ValueError("AI response parse edilemedi")
                
        except Exception as e:
            print(f"🔍 DEBUG: AI test önerisi hatası: {e}")
            # Fallback kaldırıldı - AI çalışmazsa hata ver
            raise HTTPException(status_code=500, detail=f"AI test önerisi oluşturulamadı: {str(e)}")
        
        # 5. Response oluştur
        response_data = {
            "title": "Test Önerileri",
            "recommended_tests": recommended_tests,
            "analysis_summary": analysis_summary or "Kullanıcı verisi bulunamadı",
            "disclaimer": "Bu öneriler bilgilendirme amaçlıdır. Test yaptırmadan önce doktorunuza danışın."
        }
        
        # AI mesajını kaydet
        create_ai_message(
            db=db,
            external_user_id=x_user_id,
            message_type="test_recommendations",
            request_payload=body.model_dump(),
            response_payload=response_data,
            model_used="test_recommendations_ai"
        )
        
        return response_data
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Test önerisi oluşturulurken hata: {str(e)}")

# Metabolik Yaş Testi - Premium Plus (Test sonucu analizi)
@app.post("/ai/premium-plus/metabolic-age-test", response_model=MetabolicAgeTestResponse)
async def metabolic_age_test(
    req: MetabolicAgeTestRequest,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
    x_user_id: str | None = Header(default=None),
    x_user_level: int | None = Header(default=None)
):
    """Metabolik yaş testi - Premium Plus kullanıcıları için longevity raporu"""
    
    # Plan kontrolü - sadece Premium Plus
    user_plan = get_user_plan_from_headers(x_user_level)
    if user_plan != "premium_plus":
        raise HTTPException(
            status_code=403, 
            detail="Bu özellik sadece Premium Plus kullanıcıları için kullanılabilir"
        )
    
    if not x_user_id:
        raise HTTPException(status_code=400, detail="x-user-id gerekli")
    
    # Quiz verilerini al (sadece ek bilgi için)
    quiz_messages = get_user_ai_messages_by_type(db, x_user_id, "quiz", limit=QUIZ_LAB_ANALYSES_LIMIT)
    quiz_data = {}
    
    if quiz_messages and quiz_messages[0].request_payload:
        quiz_data = quiz_messages[0].request_payload
    
    # Lab verilerini al (sadece ek bilgi için)
    lab_tests = get_standardized_lab_data(db, x_user_id, limit=20)
    
    # AI context oluştur - Metabolik yaş testi sonucu + quiz + lab
    ai_context = f"""
METABOLİK YAŞ TESTİ SONUCU:
- Kronolojik Yaş: {req.chronological_age}
- Metabolik Yaş: {req.metabolic_age}
- Yaş Farkı: {req.metabolic_age - req.chronological_age} yaş
- Test Tarihi: {req.test_date or 'Belirtilmemiş'}
- Test Yöntemi: {req.test_method or 'Belirtilmemiş'}
- Test Notları: {req.test_notes or 'Yok'}
"""
    
    # Ek veriler varsa ekle
    if req.additional_data:
        ai_context += "\nEK TEST VERİLERİ:\n"
        for key, value in req.additional_data.items():
            ai_context += f"- {key}: {value}\n"

    ai_context += f"""

QUIZ VERİLERİ (Sağlık Profili):
- Sağlık Hedefleri: {quiz_data.get('health_goals', 'N/A')}
- Aile Öyküsü: {quiz_data.get('family_history', 'N/A')}
- Mevcut İlaçlar: {quiz_data.get('current_medications', 'N/A')}
- Yaşam Tarzı: {quiz_data.get('lifestyle', 'N/A')}
- Beslenme: {quiz_data.get('diet', 'N/A')}
- Uyku Kalitesi: {quiz_data.get('sleep_quality', 'N/A')}
- Stres Seviyesi: {quiz_data.get('stress_level', 'N/A')}
- Egzersiz Sıklığı: {quiz_data.get('exercise_frequency', 'N/A')}

LAB TEST SONUÇLARI (Biyokimyasal Durum):
"""
    
    if lab_tests:
        for test in lab_tests[:5]:  # İlk 5 test
            ai_context += f"- {test.get('name', 'N/A')}: {test.get('value', 'N/A')} {test.get('unit', '')} (Referans: {test.get('reference_range', 'N/A')})\n"
    else:
        ai_context += "Lab test verisi bulunamadı.\n"
    
    ai_context += f"""

GÖREV: Bu kullanıcının metabolik yaş testi sonucunu analiz et ve longevity raporu oluştur.

Aşağıdaki JSON formatında yanıt ver:

{{
    "chronological_age": {req.chronological_age},
    "metabolic_age": {req.metabolic_age},
    "age_difference": {req.metabolic_age - req.chronological_age},
    "biological_age_status": "[genç/yaşlı/normal]",
    "longevity_score": [0-100 arası skor],
    "health_span_prediction": "[sağlıklı yaşam süresi tahmini]",
    "risk_factors": ["risk faktörü 1", "risk faktörü 2"],
    "protective_factors": ["koruyucu faktör 1", "koruyucu faktör 2"],
    "longevity_factors": [
        {{
            "factor_name": "Faktör adı",
            "current_status": "Mevcut durum",
            "impact_score": [1-10 arası],
            "recommendation": "Öneri"
        }}
    ],
    "personalized_recommendations": ["öneri 1", "öneri 2"],
    "future_health_outlook": "[gelecek sağlık durumu tahmini]",
    "analysis_summary": "[genel analiz özeti paragrafı]"
}}

ÖNEMLİ:
- Metabolik yaş testi sonucunu (kronolojik yaş vs metabolik yaş) analiz et
- Quiz ve lab verilerini de dikkate alarak longevity skorunu 0-100 arasında ver
- Risk ve koruyucu faktörleri belirle
- Kişiselleştirilmiş öneriler ver
- Gelecek sağlık durumunu tahmin et
"""
    
    # AI çağrısı
    try:
        from backend.openrouter_client import get_ai_response
        ai_response = await get_ai_response(
            system_prompt="Sen bir longevity uzmanısın. Kullanıcının verilerine göre metabolik yaş analizi yapıyorsun. Sadece JSON formatında kısa ve öz cevap ver.",
            user_message=ai_context
        )
        
        # JSON parse et
        try:
            # Markdown code block'ları temizle
            if "```json" in ai_response:
                ai_response = ai_response.split("```json")[1].split("```")[0]
            elif "```" in ai_response:
                ai_response = ai_response.split("```")[1].split("```")[0]
            
            # Son } karakterine kadar al
            last_brace = ai_response.rfind("}")
            if last_brace != -1:
                ai_response = ai_response[:last_brace + 1]
            
            result = json.loads(ai_response.strip())
        except json.JSONDecodeError as e:
            print(f"JSON parse hatası: {e}")
            print(f"AI Response: {ai_response}")
            # Fallback response
            result = {
                "chronological_age": req.chronological_age,
                "metabolic_age": req.chronological_age + 2,
                "age_difference": 2,
                "biological_age_status": "normal",
                "longevity_score": 75,
                "health_span_prediction": "Orta düzeyde sağlıklı yaşam süresi bekleniyor",
                "risk_factors": ["Stres seviyesi yüksek", "Egzersiz eksikliği"],
                "protective_factors": ["Dengeli beslenme", "Düzenli uyku"],
                "longevity_factors": [
                    {
                        "factor_name": "Stres Yönetimi",
                        "current_status": "Yüksek stres",
                        "impact_score": 8,
                        "recommendation": "Meditasyon ve nefes egzersizleri"
                    }
                ],
                "personalized_recommendations": ["Stres yönetimi", "Düzenli egzersiz"],
                "future_health_outlook": "Orta düzeyde sağlıklı yaşam süresi",
                "analysis_summary": "Metabolik yaş analizi tamamlandı. Kronolojik yaşınız ile metabolik yaşınız arasındaki fark değerlendirildi."
            }
        
        # Response oluştur
        response_data = {
            "success": True,
            "message": "Metabolik yaş analizi tamamlandı",
            "chronological_age": result.get("chronological_age", req.chronological_age),
            "metabolic_age": result.get("metabolic_age", req.chronological_age),
            "age_difference": result.get("age_difference", 0),
            "biological_age_status": result.get("biological_age_status", "normal"),
            "longevity_score": result.get("longevity_score", 75),
            "health_span_prediction": result.get("health_span_prediction", "Analiz tamamlandı"),
            "risk_factors": result.get("risk_factors", []),
            "protective_factors": result.get("protective_factors", []),
            "longevity_factors": result.get("longevity_factors", []),
            "personalized_recommendations": result.get("personalized_recommendations", []),
            "future_health_outlook": result.get("future_health_outlook", "Analiz tamamlandı"),
            "analysis_summary": result.get("analysis_summary", "Metabolik yaş analizi tamamlandı. Kronolojik yaşınız ile metabolik yaşınız arasındaki fark değerlendirildi."),
            "disclaimer": "Bu analiz bilgilendirme amaçlıdır. Tıbbi kararlar için doktorunuza danışın."
        }
        
        # AI mesajını kaydet
        create_ai_message(
            db=db,
            external_user_id=x_user_id,
            message_type="metabolic_age_test",
            request_payload=req.model_dump(),
            response_payload=response_data,
            model_used="metabolic_age_ai"
        )
        
        return response_data
        
    except Exception as e:
        print(f"Metabolik yaş testi hatası: {e}")
        raise HTTPException(status_code=500, detail=f"Metabolik yaş analizi sırasında hata: {str(e)}")