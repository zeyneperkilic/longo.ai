from fastapi import FastAPI, Depends, HTTPException, Header, Request, Query, Body
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
    QUIZ_LAB_ANALYSES_LIMIT, MILLISECOND_MULTIPLIER,
    MIN_LAB_TESTS_FOR_COMPARISON, AVAILABLE_TESTS
)
from backend.db import Base, engine, SessionLocal, create_ai_message, get_user_ai_messages, get_user_ai_messages_by_type
from backend.auth import get_db
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
        if x_user_level == 1:
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

def detect_language_simple(message: str) -> str:
    """Basit dil algılama - İngilizce/Türkçe kelime sayısına bak"""
    import re
    
    # Türkçe karakterler ve yaygın kelimeler
    turkish_patterns = [
        r'[çğıöşüÇĞIİÖŞÜ]',  # Türkçe karakterler
        r'\b(ve|veya|için|ile|bir|bu|şu|o|ben|sen|biz|siz|onlar)\b',  # Yaygın Türkçe kelimeler
        r'\b(merhaba|nasıl|neden|ne|hangi|kim|nerede|ne zaman)\b',  # Soru kelimeleri
        r'\b(sağlık|beslenme|vitamin|mineral|takviye|supplement)\b'  # Sağlık terimleri
    ]
    
    # İngilizce yaygın kelimeler
    english_patterns = [
        r'\b(hello|hi|how|what|why|when|where|who|which|can|could|would|should)\b',
        r'\b(health|nutrition|supplement|diet|exercise)\b',
        r'\b(and|or|for|with|the|a|an|this|that|i|you|we|they)\b'
    ]
    
    turkish_count = sum(len(re.findall(pattern, message, re.IGNORECASE)) for pattern in turkish_patterns)
    english_count = sum(len(re.findall(pattern, message, re.IGNORECASE)) for pattern in english_patterns)
    
    if english_count > turkish_count and english_count > 0:
        return "en"
    else:
        return "tr"

def build_chat_system_prompt() -> str:
    """Chat için system prompt oluştur"""
    return """Longopass'ın sağlık ve supplement konularında yardımcı olan AI asistanısın. Sadece 'sen kimsin' sorulduğunda 'Ben Longo' de.

🎯 GÖREVİN: Sadece sağlık, supplement, beslenme ve laboratuvar konularında yanıt ver.

🏷️ MARKA BİLGİSİ: Tüm supplement ve sağlık ürünleri LONGOPASS markasıdır. Marka sorulduğunda "Longopass markalı ürünler" de. Başka marka yok!

📱 LONGOPASS HAKKINDA:
- Longopass, kişiselleştirilmiş sağlık ve supplement platformudur
- Kullanıcıların sağlık bilincini geliştirmelerine yardımcı olur
- Lab test sonuçlarını ve sağlık verilerini takip etmelerini sağlar
- Kişiye özel supplement önerileri sunar
- Quiz ve lab analizleriyle detaylı sağlık değerlendirmesi yapar

🎁 ÜYELİK PAKETLERİ - SADECE 3 PAKET VAR:

**1. LONGO STARTER** (Giriş Seviyesi - ÜCRETSİZ)
- Online Quiz + AI Destekli İlk Rapor
- Sağlık Bülteni & Eğitim Videoları
- Sağlık Bilincini Geliştirme
- Ücretsiz Kullanım

**2. LONGO ESSENTIAL** (Genel Sağlık ve Takip Paketi - POPÜLER)
- Ev ve İşyerinde Test İmkanı
- Yıllık Tam Kapsamlı Test Paneli ile İleri Düzey Sağlık Analizi
- Kritik Değerleriniz için 4 Ayda Bir Takip Testleri
- Gelişmiş Kişisel Sağlık Paneli ile Sonuçlarınıza Tam Erişim
- Size Özel Kişiselleştirilmiş Ürün ve Test Önerileri
- AI Destekli Sağlık Modüllerine Tam Erişim
- Tüm Longopass Ürünlerinde %2,5 İndirim Oranı

**3. LONGO ULTIMATE** (İleri Sağlık, Takip ve Longevity Paketi - EN İYİ TEKLİF)
- Longo Essential Paketi'nin Tüm İçerikleri
- Kritik Değerleriniz için 3 Ayda Bir Takip Testleri
- Yılda Bir Defa Ücretsiz Metabolik Yaş Testi Paneli
- Doktor Online Görüşme İmkanı
- VIP Üyelik Desteği
- Beslenme Önerileri Ve Destekleri
- Spor & Egzersiz Destekleri
- Test Sonucunuza Bağlı AI Destekli Longevity Raporu ve Ürün Önerileri
- Tüm Longopass Ürünlerinde %5 İndirim Oranı

⚠️ KRİTİK UYARI - ÜYELİK PAKETLERİ:
- ÜYELİK PAKETİ ≠ SUPPLEMENT ÜRÜNLERİ! Bunlar farklı şeyler!
- SADECE 3 ÜYELİK PAKETI var: LONGO STARTER, LONGO ESSENTIAL, LONGO ULTIMATE
- "Denge Paketi", "Longevity Paketi", "Nöro Paketi" diye ÜYELİK paketi YOK! (Bunlar supplement ürünleri olabilir ama üyelik paketi değil!)
- Kullanıcı "üyelik paketi", "membership", "plan" sorarsa SADECE 3 üyelik paketini anlat
- Supplement ürünleri ayrı bir şey, üyelik paketleriyle KARIŞTIRMA!
- Kendi bilgini kullanma! Sadece yukarıda yazan bilgileri kullan!
- Bilmediğin şey sorulursa "Bu bilgiyi şu anda veremiyorum" de, uydurma!

🚫 KISITLAMALAR: 
- Sağlık dışında konulardan bahsetme
- Off-topic soruları kibarca sağlık alanına yönlendir
- Liste hakkında konuşma (kullanıcı listeyi görmemeli)

📚 AKADEMİK KAYNAKLAR:
- SADECE kullanıcı bilimsel/araştırma kanıtı isterse kaynak ver (örn: "çalışma göster", "araştırma ne diyor?", "bilimsel makale var mı?", "güncel araştırmalar neler?")
- Genel sağlık tavsiyesi, supplement önerisi veya sohbet yanıtlarında kaynak verme
- Kaynak verirken tıklanabilir markdown formatı kullan: [Çalışma Başlığı](https://pubmed.ncbi.nlm.nih.gov/...)
- Sadece PubMed, hakemli dergiler veya güvenilir tıbbi veritabanlarından bilimsel kaynaklar ver
- Açıkça istenmediği sürece kaynak ekleme

✨ SAĞLIK ODAĞI: Her konuyu sağlık alanına çek. Kullanıcı başka bir şeyden bahsederse, nazikçe sağlık konusuna yönlendir.

💡 YANIT STİLİ: Kısa, net ve anlaşılır ol. Sadece sağlık konusuna odaklan!

🎯 ÜRÜN ÖNERİSİ: SADECE kullanıcı açıkça "supplement öner", "ne alayım", "hangi ürünleri alayım" gibi öneri isterse ya da bir şikayeti varsa öner. Diğer durumlarda öneri yapma! Liste hakkında konuşma! Konuşmanın devamlılığını sağla, sürekli "ne önermemi istersin?" sorma!

🔄 KONUŞMA AKIŞI KURALLARI:
- Önceki mesajları OKU ve HATIRLA! Aynı öneriyi tekrar tekrar yapma!
- Kullanıcı "tamam", "anladım", "teşekkürler" derse, konuyu KAPATIP yeni bir konuya geç!
- "Başka bir sağlık konusunda yardımcı olabilir miyim?" gibi sorular sor
- Aynı ürünleri sürekli önerme, kullanıcı anladıysa farklı bir konuya geç
- Kullanıcının önceki mesajlarına göre davran, akıllı ol!

🚫 KESIN KURALLAR:
- SADECE kullanıcı açıkça öneri isterse ya da bir şikayeti varsa supplement öner
- Kullanıcı sormadan supplement önerisi yapma
- SADECE aşağıdaki listedeki ürünleri öner
- Liste dışından hiçbir ürün önerme
- Sağlık ve supplement dışında hiçbir konuşma yapma
- Off-topic soruları kesinlikle reddet
- Web sitelerinden link verme
- Liste hakkında konuşma (kullanıcı listeyi görmemeli)
- "Senin listende", "listende var", "Senin verdiğin liste" gibi ifadeler kullanma
- Sürekli "ne önermemi istersin?" sorma, konuşmanın devamlılığını sağla
- Sadece ürün isimlerini öner, gereksiz açıklama yapma
- AYNI ÖNERİYİ TEKRAR ETME! Kullanıcı anladıysa farklı konuya geç!

🚨 HAFıZA KURALI: Kullanıcı mesajında "🚨 LAB SONUÇLARI" veya "🚨 SAĞLIK QUIZ PROFİLİ" ile başlayan bölümler senin hafızandan! Bunlar için "hafızamdaki verilerine göre", "geçmiş analizlerine göre" de. "Paylaştığın/gönderdiğin" deme!"""

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
    
    # Eski IP'leri temizle (48 saatten eski)
    expired_ips = []
    for ip, data in ip_daily_limits.items():
        if current_time - data.get("reset_time", 0) > daily_reset_seconds * 2:  # 48 saat
            expired_ips.append(ip)
    
    for ip in expired_ips:
        del ip_daily_limits[ip]
    
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
    
    # Eski User+IP kombinasyonlarını temizle (48 saatten eski)
    expired_keys = []
    for key, data in ip_daily_limits.items():
        if current_time - data.get("reset_time", 0) > daily_reset_seconds * 2:  # 48 saat
            expired_keys.append(key)
    
    for key in expired_keys:
        del ip_daily_limits[key]
    
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
        reply = "Merhaba! Sağlık, supplement ve laboratuvar konularında yardımcı olabilirim. Size nasıl yardımcı olabilirim?"
        # User mesajını memory'ye ekle
        free_user_conversations[x_user_id]["messages"].append({"role": "user", "content": message_text})
        # AI yanıtını memory'ye ekle
        free_user_conversations[x_user_id]["messages"].append({"role": "assistant", "content": reply})
        return ChatResponse(conversation_id=1, reply=reply, latency_ms=0)
    
    # AI yanıtı için OpenRouter kullan
    try:
        from backend.openrouter_client import get_ai_response
        
        # Dil algılama
        import logging
        logger = logging.getLogger(__name__)
        detected_language = detect_language_simple(message_text)
        logger.info(f"🔍 DEBUG: Free chat - Detected language: {detected_language} for message: {message_text}")
        
        # Free kullanıcılar için güzel prompt
        if detected_language == "en":
            system_prompt = """You are Longopass's health assistant - helping with health and supplement topics.

🎯 YOUR TASK: Only respond to health, supplement, nutrition and laboratory topics.

🚫 RESTRICTIONS: 
- Don't talk about topics outside of health
- Politely redirect off-topic questions to health area
- Don't talk about the list (user shouldn't see the list)

📚 ACADEMIC SOURCES:
- ONLY provide sources if user asks for scientific/research evidence (e.g., "show me studies", "what does research say?", "are there scientific papers?", "what's the latest research?")
- DON'T provide sources for general health advice, supplement recommendations, or conversational responses
- When providing sources, use clickable markdown format: [Study Title](https://pubmed.ncbi.nlm.nih.gov/...)
- Only provide scientific/academic sources from PubMed, peer-reviewed journals, or reputable medical databases
- Don't add sources unless explicitly requested

✨ HEALTH FOCUS: Pull every topic to health area. If user talks about something else, politely redirect to health topic.

💡 RESPONSE STYLE: Be short, clear and understandable. Focus only on health topics!

🎯 PRODUCT RECOMMENDATION: ONLY recommend when user explicitly asks "recommend supplements", "what should I take", "which products should I buy" or has a complaint. Don't recommend in other cases! Don't talk about the list! Maintain conversation flow, don't constantly ask "what do you want me to recommend?"

🚫 STRICT RULES:
- ONLY recommend supplements when user explicitly asks or has a complaint
- Don't recommend supplements without being asked
- ONLY recommend products from the list below
- Don't recommend any products outside the list
- NEVER make up product names like "Ashwagandha Calm", "L-Theanine & Magnesium Balance", "Omega-3 Neuro Support", "Saffron Mood Boost"!
- If a product is not in the provided list, DON'T recommend it!
- Don't talk about anything other than health and supplements
- Strictly reject off-topic questions
- Don't talk about the list (user shouldn't see the list)

🏷️ BRAND INFO: All supplements and health products are LONGOPASS brand. When asked about brands, say "Longopass branded products". No other brands!

🌍 LANGUAGE: The user is writing in English. You MUST respond in English only! Do not use Turkish at all!"""
        else:
            system_prompt = """Adın Longo - sağlık ve supplement konularında yardımcı olan bir asistan. 

🎯 GÖREVİN: Sadece sağlık, supplement, beslenme ve laboratuvar konularında yanıt ver.

🏷️ MARKA BİLGİSİ: Tüm supplement ve sağlık ürünleri LONGOPASS markasıdır. Marka sorulduğunda "Longopass markalı ürünler" de. Başka marka yok!

🚫 KISITLAMALAR: 
- Sağlık dışında konulardan bahsetme
- Off-topic soruları kibarca sağlık alanına yönlendir
- Liste hakkında konuşma (kullanıcı listeyi görmemeli)

📚 AKADEMİK KAYNAKLAR:
- SADECE kullanıcı bilimsel/araştırma kanıtı isterse kaynak ver (örn: "çalışma göster", "araştırma ne diyor?", "bilimsel makale var mı?", "güncel araştırmalar neler?")
- Genel sağlık tavsiyesi, supplement önerisi veya sohbet yanıtlarında kaynak verme
- Kaynak verirken tıklanabilir markdown formatı kullan: [Çalışma Başlığı](https://pubmed.ncbi.nlm.nih.gov/...)
- Sadece PubMed, hakemli dergiler veya güvenilir tıbbi veritabanlarından bilimsel kaynaklar ver
- Açıkça istenmediği sürece kaynak ekleme

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
def chat_start(body: ChatStartRequest = Body(default={}),
               db: Session = Depends(get_db),
               x_user_id: str | None = Header(default=None),
               x_user_level: int | None = Header(default=None)):
    
    # Plan kontrolü
    user_plan = get_user_plan_from_headers(x_user_level)
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
    # User tablosu kullanılmıyor - sadece ai_messages ile çalışıyor
    
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
    # User tablosu kullanılmıyor - sadece ai_messages ile çalışıyor
    
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
    
    # DEBUG: User level ve plan kontrolü
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    print(f"🔍 DEBUG CHAT: x_user_level={x_user_level}, user_plan={user_plan}")
    logger.info(f"🔍 DEBUG CHAT: x_user_level={x_user_level}, user_plan={user_plan}")
    
    is_premium = user_plan in ["premium", "premium_plus"]
    print(f"🔍 DEBUG CHAT: is_premium={is_premium}")
    
    # Guest ve Free kullanıcılar için limiting
    client_ip = request.client.host if request else "unknown"
    
    if not x_user_level:  # Guest (null/undefined) - HİÇ KONUŞAMASIN
        # Guest kullanıcılar hiç konuşamaz, her zaman kayıt olma pop-up'ı göster
        return ChatResponse(
            conversation_id=req.conversation_id or 1,
            reply="LIMIT_POPUP:🎯 Chatbot'u kullanabilmek için ücretsiz kayıt olun! Premium özelliklere erişmek ve sınırsız soru sormak için üyelik paketlerimize göz atın.",
            latency_ms=0
        )
    elif x_user_level == 1:  # Free (hesap var) - Günde 10 mesaj
        can_chat, remaining = check_user_daily_limit(x_user_id, client_ip)
        if not can_chat:
            # Limit doldu pop-up'ı
            return ChatResponse(
                conversation_id=req.conversation_id or 1,
                reply="LIMIT_POPUP:🎯 Günlük 10 soru limitiniz doldu! Yarın tekrar konuşmaya devam edebilirsiniz. Longo Essential veya Longo Ultimate planlarından birine geçerek sınırsız soru sorma imkanına sahip olun!",
                latency_ms=0
            )
    
    # User ID validasyonu (Free: Session ID, Premium: Real ID)
    if not validate_chat_user_id(x_user_id or "", user_plan):
        raise HTTPException(status_code=400, detail="Premium kullanıcılar için gerçek user ID gerekli")
    
    # Free kullanıcılar için session-based chat
    if not is_premium:
        return await handle_free_user_chat(req, x_user_id)
    
    # Premium kullanıcılar için database-based chat
    # User tablosu kullanılmıyor - sadece ai_messages ile çalışıyor

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
    if not ok:
        # Fixed message - sadece ai_messages'a kaydedilecek
        reply = msg
        return ChatResponse(conversation_id=conversation_id, reply=reply, latency_ms=0)
    
    # XML'den supplement listesini ekle - Premium chat'te de ürün önerileri için
    # XML'den ürünleri çek (free chat'teki gibi)
    xml_products = get_xml_products()
    supplements_list = xml_products
    
    # Selamlama sonrası özel yanıt kontrolü
    txt = message_text.lower().strip()
    pure_greeting_keywords = [
        "selam", "naber", "günaydın", "merhaba",
        "iyi akşamlar", "iyi aksamlar", "iyi geceler", "iyi günler", "iyi gunler"
    ]
    
    # Eğer saf selamlama ise özel yanıt ver
    if any(kw == txt for kw in pure_greeting_keywords):
        reply = "Merhaba! Sağlık, supplement ve laboratuvar konularında yardımcı olabilirim. Size nasıl yardımcı olabilirim?"
        return ChatResponse(conversation_id=conversation_id, reply=reply, latency_ms=0)

    # Chat history'yi ai_messages'tan al (Message tablosu yerine)
    # TÜM chat mesajlarını al - conversation_id'ye bakmadan (premium özellik: her şeyi hatırlar)
    chat_messages = get_user_ai_messages_by_type(db, x_user_id, "chat", limit=CHAT_HISTORY_LIMIT)
    
    # ai_messages formatını history formatına çevir - conversation_id'ye bakmadan
    rows = []
    for msg in chat_messages:
        # User message
        if msg.request_payload and "message" in msg.request_payload:
            rows.append({"role": "user", "content": msg.request_payload["message"], "created_at": msg.created_at})
        # Assistant message
        if msg.response_payload and "reply" in msg.response_payload:
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
    
    # Dil algılama ve system prompt hazırlama
    import logging
    logger = logging.getLogger(__name__)
    detected_language = detect_language_simple(message_text)
    logger.info(f"🔍 DEBUG: Detected language: {detected_language} for message: {message_text}")
    system_prompt = build_chat_system_prompt()
    
    # Eğer İngilizce algılandıysa, system prompt'u tamamen İngilizce yap
    if detected_language == "en":
        system_prompt = """You are Longopass's health assistant - helping with health and supplement topics.

🎯 YOUR TASK: Only respond to health, supplement, nutrition and laboratory topics.

🏷️ BRAND INFO: All supplements and health products are LONGOPASS brand. When asked about brands, say "Longopass branded products". No other brands!

📱 ABOUT LONGOPASS:
- Longopass is a personalized health and supplement platform
- Helps users develop health awareness
- Enables tracking of lab test results and health data
- Provides personalized supplement recommendations
- Offers detailed health assessments through quizzes and lab analyses

🎁 MEMBERSHIP PACKAGES - ONLY 3 PACKAGES EXIST:

**1. LONGO STARTER** (Entry Level - FREE)
- Online Quiz + AI-Powered Initial Report
- Health Newsletter & Educational Videos
- Health Awareness Development
- Free to Use

**2. LONGO ESSENTIAL** (General Health and Tracking Package - POPULAR)
- Home and Office Testing Option
- Annual Comprehensive Test Panel with Advanced Health Analysis
- Follow-up Tests Every 4 Months for Critical Values
- Full Access to Advanced Personal Health Dashboard
- Personalized Product and Test Recommendations
- Full Access to AI-Powered Health Modules
- 2.5% Discount on All Longopass Products

**3. LONGO ULTIMATE** (Advanced Health, Tracking and Longevity Package - BEST OFFER)
- All Longo Essential Package Features
- Follow-up Tests Every 3 Months for Critical Values
- One Free Metabolic Age Test Panel Per Year
- Online Doctor Consultation Option
- VIP Membership Support
- Nutrition Recommendations and Support
- Sports & Exercise Support
- AI-Powered Longevity Report and Product Recommendations Based on Test Results
- 5% Discount on All Longopass Products

⚠️ CRITICAL WARNING - MEMBERSHIP PACKAGES:
- MEMBERSHIP PACKAGE ≠ SUPPLEMENT PRODUCTS! They are different things!
- ONLY 3 MEMBERSHIP PACKAGES exist: LONGO STARTER, LONGO ESSENTIAL, LONGO ULTIMATE
- There are NO membership packages like "Balance Pack", "Longevity Pack", "Neuro Pack"! (These might be supplement products but NOT membership packages!)
- There are NO membership packages like "Fertility Pack", "Fitness Pack", "Athletic Performance"!
- When users ask about "membership package", "membership", "plan", ONLY explain the 3 membership packages
- Supplement products are separate, DON'T CONFUSE them with membership packages!
- Don't use your own knowledge! Only use the information written above!
- If you don't know, say "I cannot provide that information right now", don't make it up!

🚫 RESTRICTIONS: 
- Don't talk about topics outside of health
- Politely redirect off-topic questions to health area
- Don't talk about the list (user shouldn't see the list)

📚 ACADEMIC SOURCES:
- ONLY provide sources if user asks for scientific/research evidence (e.g., "show me studies", "what does research say?", "are there scientific papers?", "what's the latest research?")
- DON'T provide sources for general health advice, supplement recommendations, or conversational responses
- When providing sources, use clickable markdown format: [Study Title](https://pubmed.ncbi.nlm.nih.gov/...)
- Only provide scientific/academic sources from PubMed, peer-reviewed journals, or reputable medical databases
- Don't add sources unless explicitly requested

✨ HEALTH FOCUS: Pull every topic to health area. If user talks about something else, politely redirect to health topic.

💡 RESPONSE STYLE: Be short, clear and understandable. Focus only on health topics!

🎯 PRODUCT RECOMMENDATION: ONLY recommend when user explicitly asks "recommend supplements", "what should I take", "which products should I buy" or has a complaint. Don't recommend in other cases! Don't talk about the list! Maintain conversation flow, don't constantly ask "what do you want me to recommend?"

🔄 CONVERSATION FLOW RULES:
- READ and REMEMBER previous messages! Don't repeat the same recommendation!
- If user says "okay", "got it", "thanks", CLOSE the topic and move to a new subject!
- Ask questions like "Can I help with another health topic?"
- Don't keep recommending the same products, if user understood, move to a different topic
- Act based on user's previous messages, be smart!

🚫 STRICT RULES:
- ONLY recommend supplements when user explicitly asks or has a complaint
- Don't recommend supplements without being asked
- ONLY recommend products from the list below
- Don't recommend any products outside the list
- NEVER make up product names like "Ashwagandha Calm", "L-Theanine & Magnesium Balance", "Omega-3 Neuro Support", "Saffron Mood Boost"!
- If a product is not in the provided list, DON'T recommend it!
- Don't talk about anything other than health and supplements
- Strictly reject off-topic questions
- Don't provide links from websites
- Don't talk about the list (user shouldn't see the list)
- Don't use phrases like "in your list", "from your list", "the list you provided"
- Don't constantly ask "what do you want me to recommend?", maintain conversation flow
- Only recommend product names, don't give unnecessary explanations
- DON'T REPEAT THE SAME RECOMMENDATION! If user understood, move to a different topic!

🚨 MEMORY RULE: Messages with "🚨 LAB RESULTS" or "🚨 HEALTH QUIZ PROFILE" are from your memory! Use phrases like "based on your previous data", "according to past analyses". Don't say "you shared/sent"!

🌍 LANGUAGE: The user is writing in English. You MUST respond in English only! Do not use Turkish at all!"""
        logger.info("🔍 DEBUG: Added English language instruction to system prompt")
    
    # 1.5. READ-THROUGH: Lab verisi global context'te yoksa DB'den çek
    # LAB VERİLERİ PROMPT'TAN TAMAMEN ÇIKARILDI - TOKEN TASARRUFU İÇİN
    # Lab verileri hala context'te tutuluyor ama prompt'a eklenmiyor
    
    # 2. Son mesajlardan yeni context bilgilerini çıkar (ONLY IF NEEDED)
    # ÖNEMLİ: Global context user bazında olmalı, conversation bazında değil!
    # Bu yüzden sadece yeni mesajdan context çıkar, eski mesajlardan değil
    # recent_messages = rows[-(CHAT_HISTORY_MAX-1):] if len(rows) > 0 else []
    new_context = {}
    
    # Yeni mesajdan context çıkar
    current_message_context = extract_user_context_hybrid(message_text, x_user_id) or {}
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
            if analysis.message_type and analysis.message_type.startswith(('quiz', 'lab_', 'test_')):
                system_prompt += f"- {analysis.message_type.upper()}: {analysis.created_at.strftime('%Y-%m-%d')}\n"
                # Analiz içeriğini de ekle
                if analysis.response_payload:
                    if analysis.message_type == "quiz" and "supplement_recommendations" in analysis.response_payload:
                        supplements = [s["name"] for s in analysis.response_payload["supplement_recommendations"][:3]]
                        system_prompt += f"  Önerilen supplementler: {', '.join(supplements)}\n"
                    elif analysis.message_type == "lab_single" and "test_name" in analysis.response_payload:
                        system_prompt += f"  Test: {analysis.response_payload['test_name']}\n"
        system_prompt += "\nBu bilgileri kullanarak daha kişiselleştirilmiş yanıtlar ver."

    # XML'den supplement listesini ekle - AI'ya ürün önerileri için (free chat gibi basit tut)
    xml_products = get_xml_products()
    supplements_list = xml_products
    
    # System message hazır
    history = [{"role": "system", "content": system_prompt, "context_data": user_context}]
    
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
    
    # Akıllı context ekleme - sadece gerekli olduğunda
    needs_context = False
    
    if rows:
        # 1. Tek kelime/fiil kontrolü
        single_words = ["devam", "açıkla", "anlat", "edelim", "yapalım", "kullan", "hazırla", "tamam", "olur", "evet", "hayır", "anladım", "teşekkürler"]
        if message_text.strip().lower() in single_words:
            needs_context = True
        
        # 2. Soru kelimeleri kontrolü (bağlam gerektirir)
        question_words = ["nasıl", "neden", "ne", "hangi", "kim", "nerede", "ne zaman", "kaç"]
        if any(word in message_text.lower() for word in question_words):
            needs_context = True
        
        # 3. Önceki mesajda supplement/ürün bahsedilmişse
        last_assistant_msg = ""
        for r in reversed(rows):
            if r['role'] == 'assistant':
                last_assistant_msg = r['content'].lower()
                break
        
        if any(word in last_assistant_msg for word in ["ürün", "supplement", "takviye", "öner", "kombinasyon"]):
            needs_context = True
        
        # 4. Kullanıcı "bu", "şu", "o" gibi referans kelimeler kullanmışsa
        reference_words = ["bu", "şu", "o", "bunun", "şunun", "onun", "buna", "şuna", "ona"]
        if any(word in message_text.lower() for word in reference_words):
            needs_context = True
    
    if needs_context and rows:
        context_message = "\n\n=== ÖNCEKİ KONUŞMA ===\n"
        for r in rows[-3:]:  # Son 3 mesaj yeterli
            if r['role'] == 'user':
                context_message += f"KULLANICI: {r['content']}\n"
            else:
                context_message += f"ASISTAN: {r['content']}\n"
        context_message += "\n=== ŞİMDİKİ SORU ===\n"
        context_message += f"KULLANICI: {message_text}\n"
        context_message += "\n=== TALİMAT ===\n"
        context_message += "Yukarıdaki konuşmayı oku ve şimdiki soruyu bağlamda anla! Kimlik sorularına kimlik cevabı ver, supplement sorularına supplement cevabı ver!\n"
        message_text = context_message
        print(f"🔍 DEBUG: Premium kullanıcı için akıllı context eklendi")
    
    # Kullanıcının güncel mesajını ekle
    history.append({"role": "user", "content": message_text})
    
    # XML supplement listesini her zaman ekle ama sadece açıkça istendiğinde ürün öner
    supplement_keywords = [
        "ne önerirsin", "ne öneriyorsun", "hangi ürün", "hangi takviye", "hangi supplement",
        "ne alayım", "ne almalıyım", "hangi vitamin", "ürün öner", "takviye öner", 
        "supplement öner", "ne kullanayım", "hangi marka", "önerdiğin ürün",
        "önerdiğin takviye", "önerdiğin supplement", "hangi ürünleri", "ne tavsiye edersin"
    ]
    is_supplement_request = any(keyword in message_text.lower() for keyword in supplement_keywords)
    
    # SADECE supplement isteği varsa ürün listesini ekle
    if is_supplement_request and supplements_list:
        supplements_info = f"\n\n🚨 MEVCUT ÜRÜNLER ({len(supplements_list)} ürün):\n"
        for i, product in enumerate(supplements_list, 1):
            category = product.get('category', 'Kategori Yok')
            product_id = product.get('id', '')
            supplements_info += f"{i}. {product['name']} ({category}) [ID: {product_id}]\n"
        
        supplements_info += "\n🚨 ÖNEMLİ: SADECE yukarıdaki listedeki ürünleri öner! Başka hiçbir ürün önerme! Kullanıcının ihtiyacına göre 3-5 ürün seç! Liste hakkında konuşma! Link verme! Ürün önerirken hem isim hem ID'yi belirt!"
        
        history.append({"role": "user", "content": supplements_info})
        print(f"🔍 DEBUG: Supplement isteği tespit edildi, {len(supplements_list)} ürün eklendi")
    else:
        print(f"🔍 DEBUG: Supplement isteği yok, ürün listesi eklenmedi")

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
    
    # AI'ın gerçekten ürün önerip önermediğini kontrol et
    recommended_products = None
    if is_supplement_request and supplements_list:
        print(f"🔍 DEBUG: Supplement isteği tespit edildi, {len(supplements_list)} ürün var")
        print(f"🔍 DEBUG: AI yanıtı: {final[:200]}...")
        
        # AI'ın gerçekten ürün önerip önermediğini kontrol et (daha sıkı)
        ai_recommending_products = any(keyword in final.lower() for keyword in [
            "öneriyorum", "öneririm", "öner", "şu ürün", "bu ürün", "şu takviye", "bu takviye", 
            "şu supplement", "bu supplement", "ürünler:", "takviyeler:", "supplementler:",
            "kombinasyon:", "şu kombinasyon", "bu kombinasyon", "ürün listesi", "takviye listesi"
        ])
        
        print(f"🔍 DEBUG: AI ürün öneriyor mu: {ai_recommending_products}")
        
        # AI ürün öneriyorsa sepete ekle butonları göster
        if ai_recommending_products:
            # AI'ın önerdiği ürünleri tespit et (basit keyword matching)
            recommended_products = []
            for product in supplements_list:  # TÜM ürünleri kontrol et
                product_name = product.get('name', '').lower()
                product_category = product.get('category', '').lower()
                
                # SADECE ID matching - daha kesin
                product_id = product.get('id', '')
                if (f"[id: {product_id}]" in final.lower() or
                    f"id: {product_id}" in final.lower() or
                    f"(id: {product_id})" in final.lower()):
                    
                    recommended_products.append({
                        "id": product.get('id', f"product_{len(recommended_products)}"),
                        "name": product.get('name', ''),
                        "category": product.get('category', ''),
                        "price": "299.99",  # Placeholder - gerçek fiyat XML'den gelecek
                        "image": f"https://longopass.myideasoft.com/images/{product.get('id', '')}.jpg"
                    })
                    print(f"🔍 DEBUG: Ürün eklendi: {product.get('name', '')}")
            
            print(f"🔍 DEBUG: Toplam {len(recommended_products)} ürün önerildi")
            print(f"🔍 DEBUG: Önerilen ürünler: {recommended_products}")
        else:
            print(f"🔍 DEBUG: AI ürün önermiyor, butonlar gösterilmeyecek")
    
    print(f"🔍 DEBUG: Response'a gönderilen products: {recommended_products}")
    print(f"🔍 DEBUG: Products count: {len(recommended_products) if recommended_products else 0}")
    
    return ChatResponse(
        conversation_id=conversation_id, 
        reply=final, 
        latency_ms=latency_ms,
        products=recommended_products
    )

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
                
                # Mevcut test listesini al
                from backend.config import AVAILABLE_TESTS
                available_tests_info = "\n".join([
                    f"- {test['test_name']} ({test['category']}): {test['description']}"
                    for test in AVAILABLE_TESTS
                ])
                
                ai_context = f"""
KULLANICI QUIZ CEVAPLARI:
{user_info}

MEVCUT TEST LİSTESİ (Sadece bunlardan seç):
{available_tests_info}

GÖREV: Quiz cevaplarına göre yukarıdaki listeden test öner. Maksimum 3 test öner.

KURALLAR:
- Aile hastalık geçmişi varsa ilgili testleri öner
- Yaş/cinsiyet risk faktörlerini değerlendir
- Sadece gerekli testleri öner
- Sadece yukarıdaki listeden seç

ÖNEMLİ: 
- Ailede diyabet varsa Şeker ve Diyabet Testi öner
- Ailede kalp hastalığı varsa Lipid ve Kolesterol Testi öner
- Yaş 40+ ise Vitamin ve Mineral Seviyeleri Testi öner
- Yaş 50+ ise Tümör Belirteçleri Testi öner
- Sadece gerçekten gerekli olan testleri öner

JSON formatında yanıt ver:
{{"recommended_tests": [{{"test_name": "Test Adı", "reason": "Neden önerildiği", "benefit": "Faydası"}}]}}
"""
                
                from backend.openrouter_client import get_ai_response
                ai_response = await get_ai_response(
                    system_prompt="Sen bir sağlık danışmanısın. Kullanıcının verilerine göre test önerileri yapıyorsun. KESINLIKLE link verme, sadece metin içeriği ver. Sadece JSON formatında kısa ve öz cevap ver.",
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
    
    # Gerekli field'ları kontrol et - daha esnek
    if not test_dict.get('name') and not test_dict.get('test_name'):
        raise HTTPException(400, "Test verisinde 'name' veya 'test_name' field'ı gerekli.")
    if not test_dict.get('value') and not test_dict.get('result'):
        raise HTTPException(400, "Test verisinde 'value' veya 'result' field'ı gerekli.")
    
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
    
    # Quiz verilerini al (ürün önerileri için)
    quiz_data = None
    try:
        quiz_messages = get_user_ai_messages_by_type(db, x_user_id, "quiz", limit=1)
        if quiz_messages and quiz_messages[0].request_payload:
            quiz_data = quiz_messages[0].request_payload
            print(f"🔍 DEBUG: Lab summary için quiz verisi bulundu: {quiz_data}")
    except Exception as e:
        print(f"🔍 DEBUG: Quiz verisi alınırken hata (sorun değil): {e}")
    
    # Use parallel multiple lab analysis with supplements
    total_sessions = body.total_test_sessions or 1  # Default 1
    res = parallel_multiple_lab_analyze(tests_dict, total_sessions, supplements_dict, body.user_profile, quiz_data)
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
            # Lab verisini al (tüm testler - geçmiş + yeni)
            if all_tests_dict:
                # Lab verisini AI'ya gönder
                lab_info_parts = []
                for test in all_tests_dict:
                    if "name" in test:
                        lab_info_parts.append(f"{test['name']}: {test.get('value', 'N/A')} ({test.get('reference_range', 'N/A')})")
                lab_info = f"Lab verileri: {', '.join(lab_info_parts)}\n"
                
                # Mevcut test listesini al
                from backend.config import AVAILABLE_TESTS
                available_tests_info = "\n".join([
                    f"- {test['test_name']} ({test['category']}): {test['description']}"
                    for test in AVAILABLE_TESTS
                ])
                
                ai_context = f"""
KULLANICI LAB SONUÇLARI:
{lab_info}

MEVCUT TEST LİSTESİ (Sadece bunlardan seç):
{available_tests_info}

GÖREV: Lab sonuçlarına göre yukarıdaki listeden test öner. Maksimum 3 test öner.

KURALLAR:
- Sadece anormal değerler için test öner
- Mevcut değerleri referans al
- Normal değerlere gereksiz test önerme
- Sadece yukarıdaki listeden seç

ÖNEMLİ:
- Düşük hemoglobin varsa Vitamin ve Mineral Seviyeleri Testi öner
- Yüksek glukoz varsa Şeker ve Diyabet Testi öner
- Anormal lipid değerleri varsa Lipid ve Kolesterol Testi öner
- Sadece gerçekten gerekli olan testleri öner

JSON formatında yanıt ver:
{{"recommended_tests": [{{"test_name": "Test Adı", "reason": "Mevcut değerlerinizle neden önerildiği", "benefit": "Faydası"}}]}}
"""
                
                from backend.openrouter_client import get_ai_response
                
                # AI'ya gönder
                ai_response = await get_ai_response(
                    system_prompt="Sen bir sağlık danışmanısın. Kullanıcının verilerine göre test önerileri yapıyorsun. KESINLIKLE link verme, sadece metin içeriği ver. Sadece JSON formatında kısa ve öz cevap ver.",
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
        if x_user_level == 1:
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
    system_prompt = f"""Adın Longo - Premium Plus kullanıcıları için özel beslenme danışmanısın.

GÖREVİN: Kullanıcının sağlık quiz profili ve lab verilerine göre kişiselleştirilmiş DETAYLI beslenme önerileri ver.

KULLANICI VERİLERİ:
{str(user_context)}

VERİ ANALİZİ:
- Quiz sonuçlarından yaş, cinsiyet, sağlık hedefleri, aktivite seviyesi
- Lab sonuçlarından vitamin/mineral eksiklikleri, sağlık durumu
- Bu verileri birleştirerek holistik beslenme yaklaşımı

YANIT FORMATI - SADECE JSON:
{{
  "general_advice": "Kullanıcının durumuna göre genel beslenme önerisi paragrafı (2-3 cümle)",
  "daily_calories": {{
    "min": 2000,
    "max": 2200,
    "unit": "kcal"
  }},
  "macro_distribution": {{
    "carbohydrate": {{
      "percentage": 40,
      "label": "Karbonhidrat"
    }},
    "protein": {{
      "percentage": 30,
      "label": "Protein"
    }},
    "fat": {{
      "percentage": 30,
      "label": "Yağ"
    }}
  }},
  "recommended_supplements": [
    {{
      "name": "Vitamin D",
      "dosage": "2000 IU",
      "note": "Opsiyonel açıklama"
    }},
    {{
      "name": "Omega-3",
      "dosage": "Balık yağı veya alg bazlı",
      "note": ""
    }}
  ],
  "hydration": {{
    "daily_target": "2.5-3L",
    "label": "Günlük Su Tüketimi",
    "tips": [
      "Sabah kalktığınızda 1-2 bardak su",
      "Her öğün öncesi 1 bardak su",
      "Egzersiz sonrası ekstra 500 ml",
      "İdrar rengi açık sarı olmalı"
    ]
  }},
  "avoid_foods": [
    "İşlenmiş gıdalar",
    "Aşırı şeker tüketimi",
    "Trans yağlar",
    "Gazlı içecekler"
  ],
  "recommended_habits": [
    "Düzenli öğün saatleri",
    "Porsiyon kontrolü",
    "Yavaş yemek yeme",
    "Renkli sebze tüketimi"
  ]
}}

ÖNEMLİ KURALLAR:
- SADECE JSON formatında yanıt ver
- Markdown kullanma (###, **, - gibi)
- KESINLIKLE link verme
- GENEL öneriler ver, spesifik günlük menü/program verme
- Her öneri için NEDEN açıkla
- Uygulanabilir ve pratik öneriler ver

DİL: SADECE TÜRKÇE YANIT VER!"""

    # User message'ı hazırla
    user_message = f"""Kullanıcının mevcut durumu:

KULLANICI BİLGİLERİ:
"""
    
    # Quiz verilerini ekle
    if user_context:
        user_message += f"\nQUIZ VERİLERİ:\n"
        for key, value in user_context.items():
            if value and key.startswith(('yas', 'cinsiyet', 'hedef', 'aktivite', 'boy', 'kilo', 'quiz_', 'beslenme', 'hastalik', 'ilac')):
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
        for test in lab_tests[:5]:  # İlk 5 test
            user_message += f"- {test.get('name', 'N/A')}: {test.get('value', 'N/A')} ({test.get('reference_range', 'N/A')})\n"
    
    user_message += f"""

Lütfen bu kullanıcı için GENEL beslenme önerileri hazırla. Spesifik günlük menü verme, genel beslenme prensipleri ver."""

    # AI çağrısı
    try:
        from backend.openrouter_client import get_ai_response
        ai_response = await get_ai_response(
            system_prompt=system_prompt,
            user_message=user_message,
            max_tokens=3000  # Diet recommendations için daha yüksek limit
        )
        
        # JSON parse et
        import json
        try:
            # Markdown code block'ları temizle
            cleaned_response = ai_response.strip()
            if cleaned_response.startswith('```json'):
                json_start = cleaned_response.find('```json') + 7
                json_end = cleaned_response.find('```', json_start)
                if json_end != -1:
                    cleaned_response = cleaned_response[json_start:json_end].strip()
            elif cleaned_response.startswith('```'):
                json_start = cleaned_response.find('```') + 3
                json_end = cleaned_response.find('```', json_start)
                if json_end != -1:
                    cleaned_response = cleaned_response[json_start:json_end].strip()
            
            recommendations_json = json.loads(cleaned_response)
        except json.JSONDecodeError as e:
            print(f"🔍 DEBUG: JSON parse hatası: {e}")
            # Fallback: Raw response döndür
            recommendations_json = {"raw_response": ai_response}
        
        # AI mesajını kaydet
        create_ai_message(
            db=db,
            external_user_id=x_user_id,
            message_type="diet_recommendations",
            request_payload={},
            response_payload={"recommendations": recommendations_json},
            model_used="openrouter"
        )
        
        return {
            "success": True,
            "message": "Beslenme önerileri hazırlandı",
            "recommendations": recommendations_json,
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
        if x_user_level == 1:
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
    system_prompt = f"""Adın Longo - Premium Plus kullanıcıları için özel egzersiz danışmanısın.

GÖREVİN: Kullanıcının sağlık quiz profili ve lab verilerine göre kişiselleştirilmiş DETAYLI egzersiz önerileri ver.

KULLANICI VERİLERİ:
{str(user_context)}

VERİ ANALİZİ:
- Quiz sonuçlarından yaş, cinsiyet, sağlık hedefleri, aktivite seviyesi
- Lab sonuçlarından sağlık durumu ve performans göstergeleri
- Bu verileri birleştirerek güvenli ve etkili egzersiz planı

YANIT FORMATI - SADECE JSON:
{{
  "general_advice": "Kullanıcının durumuna göre genel egzersiz önerisi paragrafı (2-3 cümle)",
  "lifestyle_tips": {{
    "sleep_recovery": {{
      "title": "Uyku ve Toparlanma",
      "target": "7-9 saat kaliteli uyku",
      "tips": [
        "Aynı saatlerde yatıp kalkın",
        "Yatak odası serin, karanlık ve sessiz olmalı",
        "Yatmadan 2 saat önce ekran kullanımını azaltın"
      ]
    }},
    "daily_activity": {{
      "title": "Günlük Aktivite",
      "tips": [
        "Günde en az 8000-10000 adım hedefleyin",
        "Oturma süresini her saat bölün (5 dk hareket)",
        "Merdiven kullanmayı tercih edin",
        "Parkta daha uzağa park edin"
      ]
    }},
    "stress_management": {{
      "title": "Stres Yönetimi",
      "tips": [
        "Günlük 10 dakika meditasyon veya nefes egzersizi",
        "Doğada vakit geçirin",
        "Hobilerinize zaman ayırın",
        "Sosyal bağlantılarınızı güçlendirin"
      ]
    }},
    "hydration": {{
      "title": "Hidrasyon",
      "tips": [
        "Günde en az 2-3 litre su için",
        "Antrenman sırasında sık sık su için",
        "Kafein alımını dengeleyin"
      ]
    }},
    "consistency": {{
      "title": "Düzenlilik",
      "tips": [
        "Egzersiz rutininize sadık kalın",
        "Kaçırılan günleri telafi etmeye çalışmayın",
        "İlerlemenizi kaydedin",
        "Haftalık hedefler belirleyin"
      ]
    }},
    "body_awareness": {{
      "title": "Vücut Dinleme",
      "tips": [
        "Aşırı yorgunluk hissediyorsanız ekstra dinlenme alın",
        "Ağrı ve rahatsızlıkları ciddiye alın",
        "Kademeli ilerleme prensibine uyun",
        "Overtraining belirtilerine dikkat edin"
      ]
    }},
    "motivation": {{
      "title": "Motivasyon İpuçları",
      "tips": [
        "Gerçekçi hedefler belirleyin",
        "İlerlemenizi fotoğraflarla kaydedin",
        "Egzersiz arkadaşı bulun",
        "Başarılarınızı kutlayın",
        "Çeşitlilik katın, sıkılmayın"
      ]
    }}
  }}
}}

ÖNEMLİ KURALLAR:
- SADECE JSON formatında yanıt ver
- Markdown kullanma (###, **, - gibi)
- KESINLIKLE link verme
- GENEL öneriler ver, spesifik günlük/haftalık program verme
- Her öneri için NEDEN açıkla
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
            if value and key.startswith(('yas', 'cinsiyet', 'hedef', 'aktivite', 'boy', 'kilo', 'quiz_', 'beslenme', 'hastalik', 'ilac')):
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
        for test in lab_tests[:5]:  # İlk 5 test
            user_message += f"- {test.get('name', 'N/A')}: {test.get('value', 'N/A')} ({test.get('reference_range', 'N/A')})\n"
    
    user_message += f"""

Lütfen bu kullanıcı için GENEL egzersiz önerileri hazırla. Spesifik günlük/haftalık program verme, genel egzersiz prensipleri ver."""

    # AI çağrısı
    try:
        from backend.openrouter_client import get_ai_response
        ai_response = await get_ai_response(
            system_prompt=system_prompt,
            user_message=user_message,
            max_tokens=3000  # Exercise recommendations için daha yüksek limit
        )
        
        # JSON parse et
        import json
        try:
            # Markdown code block'ları temizle
            cleaned_response = ai_response.strip()
            if cleaned_response.startswith('```json'):
                json_start = cleaned_response.find('```json') + 7
                json_end = cleaned_response.find('```', json_start)
                if json_end != -1:
                    cleaned_response = cleaned_response[json_start:json_end].strip()
            elif cleaned_response.startswith('```'):
                json_start = cleaned_response.find('```') + 3
                json_end = cleaned_response.find('```', json_start)
                if json_end != -1:
                    cleaned_response = cleaned_response[json_start:json_end].strip()
            
            recommendations_json = json.loads(cleaned_response)
        except json.JSONDecodeError as e:
            print(f"🔍 DEBUG: JSON parse hatası: {e}")
            # Fallback: Raw response döndür
            recommendations_json = {"raw_response": ai_response}
        
        # AI mesajını kaydet
        create_ai_message(
            db=db,
            external_user_id=x_user_id,
            message_type="exercise_recommendations",
            request_payload={},
            response_payload={"recommendations": recommendations_json},
            model_used="openrouter"
        )
        
        return {
            "success": True,
            "message": "Egzersiz önerileri hazırlandı",
            "recommendations": recommendations_json,
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
        if x_user_level == 1:
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
    system_prompt = f"""Adın Longo - Premium Plus kullanıcıları için özel beslenme, spor ve egzersiz danışmanısın.

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
   - Quiz verilerinden çıkarılan sağlık profili
   - Lab sonuçlarından tespit edilen durum
   - Risk faktörleri ve öncelikler
   - Egzersiz kapasitesi değerlendirmesi

2. 🏃‍♂️ DETAYLI EGZERSİZ PROGRAMI
   - Her egzersiz için NEDEN açıkla
   - Haftalık program (günler, süreler)
   - Kardiyovasküler egzersizler
   - Güç antrenmanı programı
   - Esneklik ve mobilite egzersizleri

3. 🥗 BESLENME ÖNERİLERİ
   - Egzersiz öncesi/sonrası beslenme
   - Hidrasyon stratejileri
   - Enerji için besin önerileri

4. ⚡ PERFORMANS İPUÇLARI
   - Egzersiz teknikleri
   - İlerleme stratejileri
   - Güvenlik önerileri

5. 📅 HAFTALIK PLAN ÖNERİSİ
   - Detaylı günlük program
   - Hedefler ve takip

ÖNEMLİ KURALLAR:
- KESINLIKLE link verme, sadece metin içeriği ver
- KESINLIKLE kaynak gösterme, sadece öneriler ver
- KESINLIKLE URL, web sitesi, kaynak belirtme
- Temiz ve okunabilir format kullan
- Detaylı ve kapsamlı analiz yap
- Her öneri için NEDEN açıkla
- Uygulanabilir ve pratik öneriler ver
- Sadece egzersiz önerileri ve programları ver

DİL: SADECE TÜRKÇE YANIT VER!"""

    # User message'ı hazırla
    user_message = f"""Kullanıcının mevcut durumu:

KULLANICI BİLGİLERİ:
"""
    
    # Quiz verilerini ekle
    if user_context:
        user_message += f"\nQUIZ VERİLERİ:\n"
        for key, value in user_context.items():
            if value and key.startswith(('yas', 'cinsiyet', 'hedef', 'aktivite', 'boy', 'kilo', 'quiz_', 'beslenme', 'hastalik', 'ilac')):
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
        # Quiz verilerini ekle - TÜM quiz verilerini ekle
        quiz_data_found = False
        for key, value in user_context.items():
            if value and key.startswith(('yas', 'cinsiyet', 'hedef', 'aktivite', 'boy', 'kilo', 'quiz_', 'beslenme', 'hastalik', 'ilac')):
                if not quiz_data_found:
                    user_message += f"\nGLOBAL QUIZ VERİLERİ:\n"
                    quiz_data_found = True
                user_message += f"- {key.upper()}: {value}\n"
        
        # Lab verilerini ekle - TÜM lab verilerini ekle
        lab_data_found = False
        for key, value in user_context.items():
            if value and key.startswith(('lab_', 'son_lab_', 'test_', 'vitamin_', 'mineral_')):
                if not lab_data_found:
                    user_message += f"\nGLOBAL LAB VERİLERİ:\n"
                    lab_data_found = True
                user_message += f"- {key.upper()}: {value}\n"
    
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



# ---------- TEST ÖNERİSİ ENDPOINT ----------

async def get_test_recommendations_internal(
    db: Session,
    x_user_id: str,
    user_plan: str,
    source: str,
    max_recommendations: int = 3
):
    """Internal test recommendations function"""
    # Source validation - daha esnek
    if not source or not source.startswith(('quiz', 'lab', 'test')):
        return None
    
    # Free kullanıcı engeli - Test önerileri premium özellik
    if user_plan == "free":
        return None
    
    # User ID validasyonu
    if not validate_chat_user_id(x_user_id or "", user_plan):
        return None
    
    # User tablosu kullanılmıyor - sadece ai_messages ile çalışıyor
    
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
                system_prompt="Sen bir sağlık danışmanısın. Kullanıcının verilerine göre test önerileri yapıyorsun. KESINLIKLE link verme, sadece metin içeriği ver. Sadece JSON formatında kısa ve öz cevap ver.",
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
    
    # Source validation - daha esnek
    if not source or not source.startswith(('quiz', 'lab', 'test')):
        raise HTTPException(status_code=400, detail="Source must start with 'quiz', 'lab', or 'test'")
    
    # Plan kontrolü
    user_plan = get_user_plan_from_headers(x_user_level)
    
    # Free kullanıcı engeli - Test önerileri premium özellik
    if user_plan == "free":
        raise HTTPException(status_code=403, detail="Test önerileri premium özelliktir")
    
    # User ID validasyonu
    if not validate_chat_user_id(x_user_id or "", user_plan):
        raise HTTPException(status_code=400, detail="Premium kullanıcılar için gerçek user ID gerekli")
    
    # User tablosu kullanılmıyor - sadece ai_messages ile çalışıyor
    
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
                system_prompt="Sen bir sağlık danışmanısın. Kullanıcının verilerine göre test önerileri yapıyorsun. KESINLIKLE link verme, sadece metin içeriği ver. Sadece JSON formatında kısa ve öz cevap ver.",
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
@app.post("/ai/premium-plus/metabolic-age-test")
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
    
    # Kapsamlı test paneli sayısını kontrol et (lab_summary mesajları)
    from backend.db import get_ai_messages
    comprehensive_test_count = 0
    first_comprehensive_test = None
    last_comprehensive_test = None
    
    try:
        lab_summary_messages = get_ai_messages(db, external_user_id=x_user_id, limit=100)
        for msg in lab_summary_messages:
            if msg.message_type == 'lab_summary':
                comprehensive_test_count += 1
                if not first_comprehensive_test:
                    first_comprehensive_test = msg
                last_comprehensive_test = msg
    except Exception as e:
        print(f"🔍 DEBUG: Lab summary mesajları alınırken hata: {e}")
    
    print(f"🔍 DEBUG: Kapsamlı test sayısı: {comprehensive_test_count}")
    
    # Longopass gelişim skoru hesaplama
    longopass_score = 0
    longopass_note = "Birden fazla kapsamlı test analizi gerekmektedir"
    
    if comprehensive_test_count >= 2:
        # İlk ve son testleri karşılaştır
        longopass_note = "İlk ve son kapsamlı test panelleri karşılaştırılarak hesaplandı"
        print(f"🔍 DEBUG: İlk test: {first_comprehensive_test.created_at if first_comprehensive_test else 'Yok'}")
        print(f"🔍 DEBUG: Son test: {last_comprehensive_test.created_at if last_comprehensive_test else 'Yok'}")
        # AI'ya bu bilgiyi gönderelim
    
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
    
    # Longopass gelişim skoru bilgisi
    ai_context += f"""

LONGOPASS GELİŞİM SKORU HESAPLAMA:
- Kapsamlı test paneli sayısı: {comprehensive_test_count}
- Durum: {'En az 2 test paneli var, karşılaştırma yapılabilir' if comprehensive_test_count >= 2 else 'Henüz yeterli test yok, skor 0 olmalı'}
"""
    
    if comprehensive_test_count >= 2 and first_comprehensive_test and last_comprehensive_test:
        ai_context += f"""- İlk test tarihi: {first_comprehensive_test.created_at.strftime('%Y-%m-%d') if first_comprehensive_test.created_at else 'Bilinmiyor'}
- Son test tarihi: {last_comprehensive_test.created_at.strftime('%Y-%m-%d') if last_comprehensive_test.created_at else 'Bilinmiyor'}
- İlk test verileri: {first_comprehensive_test.response_payload if hasattr(first_comprehensive_test, 'response_payload') else 'Veri yok'}
- Son test verileri: {last_comprehensive_test.response_payload if hasattr(last_comprehensive_test, 'response_payload') else 'Veri yok'}

ÖNEMLİ: İlk ve son test sonuçlarını karşılaştırarak gelişim skoru hesapla (0-100 arası). İyileşme varsa pozitif skor, kötüleşme varsa düşük skor ver.
"""
    else:
        ai_context += f"""
ÖNEMLİ: longopass_development_score.value = 0 olmalı (henüz en az 2 kapsamlı test paneli yok)
"""
    
    ai_context += f"""

GÖREV: Bu kullanıcının metabolik yaş testi sonucunu analiz et ve longevity raporu oluştur.

Aşağıdaki JSON formatında yanıt ver:

{{
    "longevity_report": {{
        "biological_age": {{
            "value": {req.metabolic_age},
            "real_age": {req.chronological_age},
            "difference": {req.metabolic_age - req.chronological_age},
            "status": "[X yaş genç/yaşlı veya Optimal]"
        }},
        "health_score": {{
            "value": [0-100 arası],
            "label": "[Çok İyi/İyi/Orta/Kötü]",
            "percentile": "[Üst %X'te]"
        }},
        "longopass_development_score": {{
            "value": 0,
            "note": "Birden fazla kapsamlı test analizi gerekmektedir"
        }},
        "metabolic_age": {{
            "value": [hesaplanan değer],
            "status": "[Harika/İyi/Orta/Kötü]"
        }}
    }},
    "detailed_analysis": {{
        "cardiovascular_health": {{
            "status": "[Mükemmel/İyi/Orta/Kötü]",
            "metrics": [
                {{"name": "VO2 Max", "value": "X ml/kg/dk", "status": "✓"}},
                {{"name": "Dinlenme Nabzı", "value": "X bpm", "status": "✓"}},
                {{"name": "Kan Basıncı", "value": "X/Y mmHg", "status": "✓"}}
            ]
        }},
        "metabolic_health": {{
            "status": "[Mükemmel/İyi/Orta/Kötü]",
            "metrics": [
                {{"name": "HbA1c", "value": "X%", "status": "✓/⚠️"}},
                {{"name": "Açlık Glukozu", "value": "X mg/dL", "status": "✓/⚠️"}}
            ]
        }},
        "inflammation_profile": {{
            "status": "[Mükemmel/İyi/Orta/Kötü]",
            "metrics": [
                {{"name": "hs-CRP", "value": "X mg/L", "status": "✓/⚠️"}},
                {{"name": "Homosistein", "value": "X μmol/L", "status": "✓/⚠️"}}
            ]
        }},
        "hormonal_balance": {{
            "status": "[Mükemmel/İyi/Orta/Kötü]",
            "metrics": [
                {{"name": "Tiroid (TSH)", "value": "X mIU/L", "status": "✓/⚠️"}},
                {{"name": "Vitamin D", "value": "X ng/mL", "status": "✓/⚠️"}}
            ]
        }},
        "cognitive_health": {{
            "status": "[Mükemmel/İyi/Orta/Kötü]",
            "metrics": [
                {{"name": "B12 Vitamini", "value": "X pg/mL", "status": "✓/⚠️"}},
                {{"name": "Omega-3 İndeksi", "value": "X%", "status": "✓/⚠️"}}
            ]
        }},
        "body_composition": {{
            "status": "[Mükemmel/İyi/Orta/Kötü]",
            "metrics": [
                {{"name": "BMI", "value": "X", "status": "✓/⚠️"}},
                {{"name": "Vücut Yağ Ora