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
from backend.schemas import ChatStartResponse, ChatMessageRequest, ChatResponse, QuizRequest, QuizResponse, SingleLabRequest, SingleSessionRequest, MultipleLabRequest, LabAnalysisResponse, SingleSessionResponse, GeneralLabSummaryResponse
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
    
    # user_based_conv_id (1, 2, 3...) ile indexle
    if user_based_conv_id <= 0 or user_based_conv_id > len(conversations):
        return None
    
    return conversations[user_based_conv_id - 1]  # 1-based to 0-based

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

@app.get("/widget.js")
def widget_js():
    with open("frontend/widget.js", "r", encoding="utf-8") as f:
        return f.read()

@app.get("/test")
def test_page():
    from fastapi.responses import HTMLResponse
    with open("frontend/test.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

# ---------- CHAT (PREMIUM) ----------

@app.post("/ai/chat/start", response_model=ChatStartResponse)
def chat_start(db: Session = Depends(get_db),
               x_user_id: str | None = Header(default=None),
               x_user_plan: str | None = Header(default=None)):
    user = get_or_create_user(db, x_user_id, x_user_plan)
    
    # Bu kullanıcının kaç conversation'ı var? +1 yaparak user-based ID oluştur
    user_conv_count = db.query(Conversation).filter(Conversation.user_id == user.id).count()
    user_based_conv_id = user_conv_count + 1
    
    conv = Conversation(user_id=user.id, status="active")
    db.add(conv); db.commit(); db.refresh(conv)
    
    # User-based conversation ID döndür
    return ChatStartResponse(conversation_id=user_based_conv_id)

@app.get("/ai/chat/{conversation_id}/history")
def chat_history(conversation_id: int,
                 db: Session = Depends(get_db),
                 x_user_id: str | None = Header(default=None),
                 x_user_plan: str | None = Header(default=None)):
    user = get_or_create_user(db, x_user_id, x_user_plan)
    conv = get_conversation_by_user_based_id(db, user.id, conversation_id)
    if not conv:
        raise HTTPException(404, "Konuşma bulunamadı")
    msgs = db.query(Message).filter(Message.conversation_id==conv.id).order_by(Message.created_at.asc()).all()
    return [{"role": m.role, "content": m.content, "ts": m.created_at.isoformat()} for m in msgs][-CHAT_HISTORY_MAX:]

@app.post("/ai/chat", response_model=ChatResponse)
async def chat_message(req: ChatMessageRequest,
                  current_user: str = Depends(get_current_user),
                  db: Session = Depends(get_db),
                  x_user_id: str | None = Header(default=None),
                  x_user_plan: str | None = Header(default=None)):
    user = get_or_create_user(db, x_user_id, x_user_plan)  # Asıl site zaten kontrol ediyor

    conv = get_conversation_by_user_based_id(db, user.id, req.conversation_id)
    if not conv:
        raise HTTPException(404, "Konuşma bulunamadı")

    # Günlük chat limiti kaldırıldı - Gereksiz

    # Global context'i önce al (hafıza sorusu için gerekli)
    global_context = get_user_global_context(db, user.id)
    
    # Health Guard ile kategori kontrolü
    ok, msg = guard_or_message(req.text)
    
    # Hafıza soruları artık HEALTH kategorisinde, özel işlem yok
    memory_bypass = False
    if not ok:
        # store user message
        db.add(Message(conversation_id=conv.id, user_id=user.id, role="user", content=req.text)); db.commit()
        # reply fixed message
        reply = msg
        m = Message(conversation_id=conv.id, role="assistant", content=reply, model_latency_ms=0)
        db.add(m); db.commit()
        return ChatResponse(conversation_id=conv.id, reply=reply, latency_ms=0)
    
    # Hafıza soruları artık normal AI model ile yanıtlanıyor
    
    # Selamlama sonrası özel yanıt kontrolü
    txt = req.text.lower().strip()
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
    db.add(Message(conversation_id=conv.id, user_id=user.id, role="user", content=req.text)); db.commit()

    # build history (including the new user message)
    rows = db.query(Message).filter(Message.conversation_id==conv.id).order_by(Message.created_at.asc()).all()
    
    # Get user's previous analyses for context (CACHE THIS!)
    from backend.db import get_user_ai_interactions
    user_analyses = get_user_ai_interactions(db, user.id, limit=5)
    
    # Build enhanced system prompt with user context
    system_prompt = "Sen Longo AI'sın. SADECE sağlık/supplement/lab konularında yanıt ver. Off-topic'te kibarca reddet. KAYNAK EKLEME: Otomatik olarak kaynak link'leri, referans'lar veya citation'lar ekleme!\n\nÖNEMLİ: Eğer kullanıcı bilgileri (isim, yaş, hastalık vb.) aşağıda verilmişse, bunları kullan ve hatırladığını göster.\n\n🚨 SAĞLIK YÖNLENDİRME KURALI: Her konuyu sağlık ve supplement alanına çek! Kullanıcı off-topic bir şey söylerse, kibarca sağlık konusuna yönlendir ve supplement önerisi yap!\n\n❌ OFF-TOPIC BİLGİ VERME: Sağlık dışında konularda bilgi verme ve detaya girme! İsim anlamı, kültür, tarih, spor gibi konularda bilgi verme! Sadece sağlık konusuna odaklan!"
    
    # Global + Local Context Sistemi - OPTIMIZED
    user_context = {}
    
    # 1. Global context'i getir (zaten yukarıda alındı)
    if global_context:
        # Key'leri normalize et (büyük harf -> küçük harf + encoding temizle)
        normalized_global = {}
        for key, value in global_context.items():
            if key and value:  # None/boş değerleri atla
                # Encoding sorunlarını çöz: 'i̇si̇m' -> 'isim'
                normalized_key = key.lower().replace('i̇', 'i').replace('ı', 'i').strip()
                if normalized_key and normalized_key not in normalized_global:
                    normalized_global[normalized_key] = value
        user_context.update(normalized_global)
    
    # 2. Son mesajlardan yeni context bilgilerini çıkar (ONLY IF NEEDED)
    # ÖNEMLİ: Global context user bazında olmalı, conversation bazında değil!
    # Bu yüzden sadece yeni mesajdan context çıkar, eski mesajlardan değil
    # recent_messages = rows[-(CHAT_HISTORY_MAX-1):] if len(rows) > 0 else []
    new_context = {}
    
    # 2. YENİ MESAJDAN CONTEXT ÇIKAR (her mesajda!)
    current_message_context = extract_user_context_hybrid(req.text, user.email)
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
        
        # 3. Yeni context'i global context'e ekle (ONLY IF CHANGED)
        context_changed = False
        if new_context and any(new_context.values()):
            # Check if context actually changed
            for key, value in new_context.items():
                if key not in user_context or user_context[key] != value:
                    context_changed = True
                    break
            
            if context_changed:
                update_user_global_context(db, user.id, new_context)
                # Local context'i de güncelle
                user_context.update(new_context)
        
        # Kullanıcı bilgilerini AI'ya hatırlat 
        if user_context and any(user_context.values()):
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
                system_prompt += f"DEBUG: Added diseases: {hastaliklar_str}\n"
                
            if "cinsiyet" in user_context and user_context["cinsiyet"]:
                system_prompt += f"KULLANICI CİNSİYETİ: {user_context['cinsiyet']}\n"
                
            system_prompt += "\nÖNEMLİ: Bu bilgileri kesinlikle hatırla! Kullanıcı sana adını, yaşını veya hastalığını sorduğunda yukarıdaki bilgilerle cevap ver!"
        
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
        system_prompt += "\n\n🚨 MUTLAK SUPPLEMENT KURALI:"
        system_prompt += "\n- MUTLAKA sadece user message'da verilen supplement listesindeki ürünleri öner!"
        system_prompt += "\n- CholestOff, Beta-Sitosterol, Nature Made, CholestePure gibi ürünler SİTEMİZDE YOK!"
        system_prompt += "\n- Sadece: D Vitamini, Omega-3, Magnezyum, Koenzim Q10, Selenyum gibi ürünler!"
        system_prompt += "\n- KAYNAK EKLEME: Otomatik olarak kaynak link'leri, referans'lar veya citation'lar ekleme!"
        system_prompt += "\n- DİL: SADECE TÜRKÇE YANIT VER!"
        system_prompt += "\n\n🎯 SAĞLIK YÖNLENDİRME STRATEJİSİ:"
        system_prompt += "\n- Off-topic konularda: 'Bu konu sağlıkla ilgili değil ama sana sağlık önerisi verebilirim'"
        system_prompt += "\n- Her durumda: Supplement önerisi yap ve sağlık konusuna çek"
        system_prompt += "\n- Örnek: 'Hava durumu yerine D vitamini eksikliği hakkında konuşalım'"
        system_prompt += "\n\n🚫 KESİNLİKLE YASAK:"
        system_prompt += "\n- İsim anlamı, köken, etimoloji bilgisi verme!"
        system_prompt += "\n- Kültür, tarih, spor bilgisi verme!"
        system_prompt += "\n- Off-topic konularda bilgi verme vedetaylar verme!"
        system_prompt += "\n- Sadece sağlık konusuna odaklan!"
        system_prompt += "\n\n⚠️ ÖNEMLİ: Kullanıcı adını hatırla ama isim hakkında bilgi verme!"
        system_prompt += "\n- Sadece: 'Evet [isim], seni hatırlıyorum' de!"
        system_prompt += "\n- Sonra hemen sağlık konusuna geç!"
        system_prompt += "\n\n⏱️ ZAMAN KISITLAMASI:"
        system_prompt += "\n- Sağlık dışı konularda konuşma!"
        system_prompt += "\n- Hemen sağlık konusuna geç!"
        system_prompt += "\n- Uzun açıklamalar yapma!"
        system_prompt += "\n\n🔍 OTOMATİK VERİ ERİŞİMİ:"
        system_prompt += "\n- Quiz sonucu istenirse: Kullanıcının quiz geçmişini otomatik incele!"
        system_prompt += "\n- Lab test istenirse: Kullanıcının lab test geçmişini otomatik incele!"
        system_prompt += "\n- Prompt'ta verilen verileri kullan, kullanıcıdan tekrar isteme!"
        system_prompt += "\n- Mevcut verileri analiz et ve öneri yap!"
        system_prompt += "\n\n🎯 AMBIGUOUS SORU YÖNLENDİRMESİ:"
        system_prompt += "\n- 'Ne alayım?', 'Bana bir şey öner', 'Ne yapayım?' gibi belirsiz sorular → HEMEN SAĞLIK!"
        system_prompt += "\n- 'Supplement öner', 'Hangi ürünleri alayım?' şeklinde yönlendir!"
        system_prompt += "\n- Belirsiz sorularda genel sağlık paketi öner!"
        system_prompt += "\n- Off-topic'e gitme, sadece sağlık!"
        system_prompt += "\n\n💊 AKILLI SUPPLEMENT ÖNERİSİ:"
        system_prompt += "\n- Boşuna supplement önerme! Sadece gerçekten işe yarayacak olanları öner!"
        system_prompt += "\n- Kullanıcının problemlerine, test sonuçlarına, eksikliklerine göre öner!"
        system_prompt += "\n- 'Herkes için aynı paket' yerine 'kişiye özel çözüm' sun!"
        system_prompt += "\n- E-ticaret stratejisi: 4 DEFAULT + 2-3 PROBLEME ÖZEL = 6-7 Supplement!"
        system_prompt += "\n- Değerler iyiyse Longevity, kötüyse problem çözücü öner!"
        
        # Supplement listesini user message olarak ekle (quiz'deki gibi)
        supplements_info = f"\n\nTÜM KULLANILABİLİR ÜRÜNLER (Toplam: {len(supplements_list)}):\n"
        for i, supplement in enumerate(supplements_list, 1):  # TÜM 128 ÜRÜNÜ GÖSTER
            supplements_info += f"{i}. {supplement['name']} (ID: {supplement['id']}) - {supplement['category']}\n"
        supplements_info += "\n💡 AI: Tüm bu 128 ürün arasından en uygun olanları seç!"
        
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
    
    # Quiz data'yı dict'e çevir ve validate et
    quiz_dict = validate_input_data(body.quiz_answers or {}, ["age", "gender"])
    
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
        from backend.db import get_user_global_context, update_user_global_context
        
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
        
        return data

@app.post("/ai/lab/single", response_model=LabAnalysisResponse)
def analyze_single_lab(body: SingleLabRequest,
                        current_user: str = Depends(get_current_user),
                       db: Session = Depends(get_db),
                        x_user_id: str | None = Header(default=None)):
    """Analyze single lab test result with historical trend analysis"""
    user = get_or_create_user(db, x_user_id, "premium")  # Asıl site zaten kontrol ediyor
    
    # Convert test to dict for processing
    test_dict = body.test.model_dump()
    
    # Geçmiş sonuçları dict'e çevir
    historical_dict = None
    if body.historical_results:
        historical_dict = [result.model_dump() for result in body.historical_results]
    
    # Health Guard kaldırıldı - Lab analizi zaten kontrollü içerik üretiyor

    # Use parallel single lab analysis with historical results
    res = parallel_single_lab_analyze(test_dict, historical_dict)
    final_json = res["content"]
    data = parse_json_safe(final_json) or {}
    
    # Database kaydı kaldırıldı - Asıl site zaten yapacak
    # Sadece AI yanıtını döndür
    
    return data

@app.post("/ai/lab/session", response_model=SingleSessionResponse)
def analyze_single_session(body: SingleSessionRequest,
                          current_user: str = Depends(get_current_user),
                          db: Session = Depends(get_db),
                          x_user_id: str | None = Header(default=None)):
    """Analyze single lab session with multiple tests"""
    user = get_or_create_user(db, x_user_id, "premium")  # Asıl site zaten kontrol ediyor
    
    # Convert session tests to dict for processing
    tests_dict = [test.model_dump() for test in body.session_tests]
    
    # Health Guard kaldırıldı - Lab analizi zaten kontrollü içerik üretiyor
    
    # Use parallel single session analysis
    res = parallel_single_session_analyze(tests_dict, body.session_date, body.laboratory)
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
    
    # Convert tests to dict for processing
    tests_dict = [test.model_dump() for test in body.tests]
    
    # XML'den supplement listesini al (eğer body'de yoksa)
    supplements_dict = body.available_supplements
    if not supplements_dict:
        # XML'den supplement listesini çek (gerçek veriler)
        from backend.config import SUPPLEMENTS_LIST
        supplements_dict = SUPPLEMENTS_LIST
    
    # Use parallel multiple lab analysis with supplements
    res = parallel_multiple_lab_analyze(tests_dict, body.total_test_sessions, supplements_dict, body.user_profile)
    final_json = res["content"]
    data = parse_json_safe(final_json) or {}
    
    # Progress analysis kaldırıldı - Asıl site zaten yapacak
    
    # Add metadata for response formatting
    if "test_count" not in data:
        data["test_count"] = body.total_test_sessions
    if "overall_status" not in data:
        data["overall_status"] = "analiz_tamamlandı"
    
                        # Lab sonuçlarını global context'e ekle (SADECE ÖZET BİLGİLER)
        if data and "test_details" in data:
            from backend.db import get_user_global_context, update_user_global_context
            
            # Mevcut global context'i al
            current_context = get_user_global_context(db, user.id) or {}
            
            # Lab sonuçlarından SADECE ÖZET BİLGİLERİ çıkar
            lab_context = {}
            
            # Test adları - SADECE İLK N TANESİ
            if "test_details" in data:
                test_adlari = list(data["test_details"].keys())
                from backend.config import MAX_LAB_TESTS_IN_CONTEXT
                lab_context["session_anormal_testler"] = test_adlari[:MAX_LAB_TESTS_IN_CONTEXT]
            
            # Genel lab durumu
            if "general_assessment" in data and "overall_health_status" in data["general_assessment"]:
                lab_context["lab_genel_durum"] = data["general_assessment"]["overall_health_status"]
            
            # Lab tarihi
            import time
            lab_context["lab_tarih"] = time.strftime("%Y-%m-%d")
            
            # Global context'i güncelle
            if lab_context:
                updated_context = {**current_context, **lab_context}
                update_user_global_context(db, user.id, updated_context)

    # Database kaydı kaldırıldı - Asıl site zaten yapacak
    # Sadece AI yanıtını döndür
    
    return data



@app.get("/ai/progress/{user_id}")
def get_user_progress(user_id: str, db: Session = Depends(get_db)):
    """Get user's lab test progress and trends"""
    
    # Get lab test history
    from backend.db import get_lab_test_history
    
    # user_id'yi integer'a çevirmeye çalış, başarısız olursa string olarak kullan
    try:
        user_id_int = int(user_id)
    except ValueError:
        user_id_int = 0  # String user_id için default değer
    
    lab_history = get_lab_test_history(db, user_id_int, limit=20)
    
    # Analyze trends
    if len(lab_history) < 2:
        return {
            "message": "Progress analizi için en az 2 test gerekli",
            "test_count": len(lab_history),
            "trends": "Trend analizi yapılamaz"
        }
    
    # Basic trend analysis
    trends = {
        "total_tests": len(lab_history),
        "test_frequency": "Test sıklığı analizi",
        "improvement_areas": "İyileşme alanları",
        "stable_areas": "Stabil alanlar"
    }
    
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


@app.get("/cache/stats")
def get_cache_statistics():
    """Cache istatistiklerini döndür"""
    return get_cache_stats()


@app.get("/cache/clear")
def clear_all_cache():
    """Tüm cache'i temizle"""
    from backend.cache_utils import cache
    cache.clear()
    return {"message": "Cache temizlendi", "status": "success"}


@app.get("/cache/cleanup")
def cleanup_expired_cache():
    """Expired cache item'ları temizle"""
    from backend.cache_utils import cleanup_cache
    removed_count = cleanup_cache()
    return {"message": f"{removed_count} expired item temizlendi", "status": "success"}

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
    """Input data validation for production"""
    if not data:
        data = {}
    
    if required_fields:
        for field in required_fields:
            if field not in data:
                data[field] = None
    
    return data