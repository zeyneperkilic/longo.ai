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
    
    # SADECE çok net, kısa selamlamalar için hızlı izin
    if txt in ["naber", "günaydın", "gunaydin", "selam", "merhaba"]:
        return "SAFE"
    

    sys = (
        "Sen bir sağlık ve supplement AI moderatörüsün. Sadece 2 kategorili sınıflandır:\n\n"
        "🔵 SAFE (Sadece şunlar):\n"
        "- Sağlık, supplement, beslenme, hafıza, tahlil, kan testi, lab\n"
        "- Kişisel bilgi, hastalık bilgisi, alerji\n"
        "- İlaç bilgisi (sadece supplement dozu), ameliyat bilgisi\n"
        "- Çok kısa selamlamalar (naber, günaydın, selam, merhaba)\n"
        "- Hafıza soruları ('beni hatırlıyor musun?', 'beni tanıyor musun?', 'benim adım ne?')\n"
        "- Kişisel bilgi soruları ('benim adım ne?', 'benim yaşım ne?', 'benim hastalığım ne?')\n"
        "- Lab test inceleme ('lab test sonucumu incele', 'kan tahlilimi incele')\n"
        "- Quiz sonucu inceleme ('quiz sonucumu incele', 'test sonucumu incele')\n"
        "- Ambiguous sorular ('ne alayım?', 'bana bir şey öner', 'ne yapayım?') → SAFE ama sağlığa yönlendir\n"
        "- Sağlıkla ilgili her şey ama riskli konular dışında (ilaç, doz, antidepresan, teşhis vb.)"
        "🔴 BLOCK (Şunlar):\n"
        "- Spor, eğlence, hava durumu, gündem\n"
        "- Kültür, tarih, kelime anlamı, etimoloji\n"
        "- İlaç dozu (reçeteli ilaçlar), teşhis\n"
        "- Selamlama + ekstra içerik (örn: 'Merhaba, hava nasıl?')\n"
        "- Sağlık + off-topic karışımı\n\n"
        "- Sağlıkla ilgili olmayan başka konular block ama sohbet ediyorsa sağlık alanına kayarak sohbete devam edilebilir"
        "📋 ÖRNEKLER:\n"
        "SAFE: 'D vitamini alayım mı?', 'Ben D vitamini alerjim var', 'Kaç mg D vitamini alayım?'\n"
        "BLOCK: 'Futbol maçı ne zaman?', 'Bugün hava nasıl?', 'Merhaba, hangi film izleyeyim?', 'Aspirin kaç mg alayım?'\n\n"
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
