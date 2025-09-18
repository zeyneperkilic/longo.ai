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
        "Sen bir sağlık ve supplement AI moderatörüsün. Sadece 2 kategorili sınıflandır: Sağlıkla ve kişisel bilgilerle ilgili şeyler SAFE, off topic şeyler Block\n\n"
        "🔵 SAFE (örnekler):\n"
        "- Sağlık, supplement, beslenme, hafıza, tahlil, kan testi, lab\n"
        "- Kişisel bilgi, hastalık bilgisi, alerji\n"
        "- İlaç bilgisi (sadece supplement dozu), ameliyat bilgisi\n"
        "- Çok kısa selamlamalar (naber, günaydın, selam, merhaba)\n"
        "- Lab test inceleme ('lab test sonucumu incele', 'kan tahlilimi incele')\n"
        "- Quiz sonucu inceleme ('quiz sonucumu incele', 'test sonucumu incele')\n"
        "- Ambiguous sorular ('ne alayım?', 'bana bir şey öner', 'ne yapayım?') → SAFE ama sağlığa yönlendir\n"
        "- Konuşma devam ettirme cümleleri ('devam et', 'anlat', 'daha fazla', 'başka ne var')\n"
        "- Onay/red cümleleri ('evet', 'hayır', 'isterim', 'istemem', 'tamam', 'olur')\n"
        "- Normal sohbet cümleleri ('nasılsın', 'iyi misin', 'teşekkürler', 'rica ederim')\n"
        "- AI yetenek soruları ('ne yapabiliyorsun', 'neler yapabiliyorsun', 'hangi konularda yardımcı olabilirsin')\n"
        "- Genel konuşma cümleleri (sağlık dışı ama zararsız sohbet)\n"
        "- Sağlıkla ilgili her şey ama riskli konular dışında (ilaç, doz, antidepresan, teşhis vb.)\n\n"
        "🔴 BLOCK (örnekler):\n"
        "- Spor, eğlence, hava durumu, gündem\n"
        "- Kültür, tarih, kelime anlamı, etimoloji\n"
        "- İlaç dozu (reçeteli ilaçlar), teşhis\n"
        "- Tamamen sağlık dışı konular\n\n"
        "SADECE 'SAFE' veya 'BLOCK' döndür!"
    )
    
    usr = f"Kullanıcı sorusu: {text}"
    
    try:
        # Ana model: Moderation model
        out = None
        try:
            out = call_chat_model(MODERATION_MODEL,
                                  [{"role": "system", "content": sys}, {"role": "user", "content": usr}],
                                  temperature=0.1, max_tokens=5)
            print(f"✅ Moderation model başarılı")
        except Exception as e:
            print(f"❌ Moderation model hata: {e}")
            
            # Fallback: GPT-OSS-20B
            try:
                out = call_chat_model("openai/gpt-oss-20b:free",
                                      [{"role": "system", "content": sys}, {"role": "user", "content": usr}],
                                      temperature=0.1, max_tokens=5)
                print(f"✅ Moderation fallback (GPT-OSS-20B) başarılı")
            except Exception as e2:
                print(f"❌ Moderation fallback (GPT-OSS-20B) hata: {e2}")
                return "ALLOW"  # Fallback'te güvenli taraf
        
        label = (out.get("content") or "").strip().upper()
        
        # Normalize
        if "BLOCK" in label:
            return "BLOCK"
        else:
            return "SAFE"
        
    except Exception as e:
        print(f"LLM classification failed: {e}")
        return "SAFE"  # Güvenli default
