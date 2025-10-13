from typing import Tuple
from backend.config import HEALTH_MODE, MODERATION_MODEL
from backend.openrouter_client import call_chat_model
import time


_last_llm_call = 0
_min_interval = 10.0  # 10 saniye minimum interval (OpenRouter rate limit için)

def guard_or_message(text: str) -> Tuple[bool, str]:
    """Basit Health Guard - Sadece 2 kategori: SAFE vs BLOCK"""
    
    # LLM ile basit sınıflandırma
    try:
        label = classify_topic_simple(text)
        print(f"Health guard classification: {text[:50]}... -> {label}")
        
        if label == "BLOCK":
            return False, "Üzgünüm, Longo bu konuda yorum yapamıyor. Sadece supplement ve temel sağlık konularında yardımcı olabilirim."
        else:  # SAFE
            return True, ""
            
    except Exception as e:
        print(f"Health guard failed: {e}, allowing request")
        return True, ""

# ---------- Basit Topic Classifier ----------

def classify_topic_simple(text: str) -> str:
    """LLM-Centric 2 kategorili sınıflandırma: SAFE vs BLOCK"""
    txt = (text or "").lower().strip()
    
    # SADECE çok net, kısa selamlamalar ve AI kimlik soruları için hızlı izin
    safe_quick_list = [
        "naber", "günaydın", "gunaydin", "selam", "merhaba",
        "sen kimsin", "kimsin", "sen kimsin?", "kimsin?",
        "adın ne", "adın ne?", "ismin ne", "ismin ne?",
        "senin adın ne", "senin ismin ne", "adın", "ismin",
        "sen ne", "ne yapıyorsun", "kim",
        "beni tanıyor musun", "beni tanıyor musun?",
        "benim adım ne", "benim adım ne?", "benim ismim ne", "benim ismim ne?",
        "tanıyor musun", "tanıyor musun?"
    ]
    if txt in safe_quick_list:
        return "SAFE"
    
    # Longopass kelimesi geçiyorsa direkt SAFE
    if "longopass" in txt or "longo pass" in txt:
        return "SAFE"

    sys = (
        "Sen bir sağlık ve supplement AI moderatörüsün. Sadece 2 kategorili sınıflandır:\n\n"
        "🔵 SAFE (varsayılan - çoğu şey SAFE):\n"
        "- Sağlık, supplement, beslenme, hafıza, tahlil, kan testi, lab → SAFE\n"
        "- LONGOPASS marka adı ve ürünleri → HER ZAMAN SAFE!\n"
        "- Kişisel bilgi, hastalık bilgisi, alerji → SAFE\n"
        "- TÜM KONUŞMA CÜMLELERİ: Selamlaşmalar, onaylar ('evet', 'hayır', 'tamam', 'olur', 'anladım', 'teşekkürler'), devam ettirme ('devam et', 'anlat', 'hazırla', 'yap', 'ver', 'göster', 'söyle'), sorular ('nasılsın', 'naber') → HER ZAMAN SAFE!\n"
        "- Konuşmanın doğal akışı içindeki TÜM KELİMELER → Varsayılan SAFE!\n"
        "- Eğer emin değilsen → SAFE!\n\n"
        "🔴 BLOCK (sadece çok net off-topic konular):\n"
        "- Film/dizi adı ve yorumu (örn: 'Avatar filmini nasıl buldun?', 'Game of Thrones'u izledin mi?')\n"
        "- Spor maçları ve takımlar (örn: 'Fenerbahçe maçını izledin mi?', 'Messi mi Ronaldo mu?')\n"
        "- Teknoloji ürün karşılaştırması (örn: 'iPhone mı Samsung mu?', 'Hangi bilgisayarı alayım?')\n"
        "- Siyaset, gündem, ekonomi haberleri\n"
        "- Müzik albümleri, şarkı sözleri, sanatçı yorumları\n\n"
        "⚠️ KRİTİK KURALLAR:\n"
        "1. Tek kelimeler (hazırla, yap, ver, söyle, göster, anlat, devam) → HER ZAMAN SAFE!\n"
        "2. Kısa cümleler (< 5 kelime) → Genelde SAFE!\n"
        "3. Sağlık/supplement bağlamında her şey → SAFE!\n"
        "4. Emin değilsen → SAFE! (Yanlışlıkla BLOCK yapma!)\n\n"
        "SADECE 'SAFE' veya 'BLOCK' döndür!"
    )
    
    usr = f"Kullanıcı sorusu: {text}"
    
    try:
        out = call_chat_model(MODERATION_MODEL,
                              [{"role": "system", "content": sys}, {"role": "user", "content": usr}],
                              temperature=0.1, max_tokens=5)
        
        label = (out.get("content") or "").strip().upper()
        
        # Normalize
        if "BLOCK" in label:
            return "BLOCK"
        else:
            return "SAFE"
        
    except Exception as e:
        print(f"LLM classification failed: {e}")
        return "SAFE"  # Güvenli default
