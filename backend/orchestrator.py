from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
from backend.config import PARALLEL_MODELS
from backend.openrouter_client import call_chat_model
from backend.utils import is_valid_chat, parse_json_safe
import time
import json
import re

SYSTEM_HEALTH = ("Sen Longo AI'sın - kullanıcının kişisel sağlık asistanı. SADECE sağlık/supplement/laboratuvar konularında yanıt ver. "
                 "Off-topic'te kibarca reddet. Yanıtlar bilgilendirme amaçlıdır; tanı/tedavi için hekim gerekir. "
                 "DİL KURALI: Hangi dilde soru soruluyorsa o dilde cevap ver! "
                 "Türkçe soru → Türkçe cevap, İngilizce soru → İngilizce cevap! "
                 "KAYNAK/KAYNAKÇA EKLEME: Otomatik olarak link, site adı, referans veya citation EKLEME. Kullanıcı özellikle istemedikçe kaynak belirtme. "
                 "🎯 KİŞİSEL ASİSTAN TARZI: Kullanıcıya 'sen' diye hitap et, samimi ve destekleyici ol, önceki konuşmaları hatırladığını göster!")

SYSTEM_HEALTH_ENGLISH = ("You are Longo AI - the user's personal health assistant. Answer ONLY on health/supplement/laboratory topics. "
                          "Redeem off-topic requests. Answers are for informational purposes; a doctor is required for diagnosis/treatment. "
                          "CRITICAL: You MUST respond in ENGLISH language only! "
                          "IMPORTANT: Never use Turkish characters (ç, ğ, ı, ö, ş, ü) or Turkish words. "
                          "Your response must be 100% in English. If you cannot answer in English, do not answer at all. "
                          "🎯 PERSONAL ASSISTANT STYLE: Address the user as 'you', be warm and supportive, show that you remember previous conversations!")

def parallel_chat(messages: List[Dict[str, str]]) -> Dict[str, Any]:
    """Run parallel chat with multiple models, then synthesize with GPT-5"""
    try:
        # Dil algılama
        user_message = messages[-1]["content"] if messages else ""
        user_language = detect_language(user_message)
        
        if user_language == "english":
            system_prompt = SYSTEM_HEALTH_ENGLISH
        else:
            system_prompt = SYSTEM_HEALTH
        
        # Context'i system prompt'a ekle (main.py'den gelen context)
        if "context_data" in messages[0] and messages[0]["context_data"]:
            context = messages[0]["context_data"]
            system_prompt += "\n\nKULLANICI BİLGİLERİ:\n"
            if "isim" in context:
                system_prompt += f"İsim: {context['isim']}\n"
            if "tercihler" in context:
                system_prompt += f"Tercihler: {', '.join(context['tercihler'])}\n"
            if "hastaliklar" in context:
                system_prompt += f"Hastalıklar: {', '.join(context['hastaliklar'])}\n"
            if "yas" in context and context["yas"]:
                system_prompt += f"Yaş: {context['yas']}\n"
            if "cinsiyet" in context and context["cinsiyet"]:
                system_prompt += f"Cinsiyet: {context['cinsiyet']}\n"
            system_prompt += "\n\n🎯 KRİTİK KİŞİSEL ASİSTAN TALİMATI: Bu kullanıcı bilgilerini MUTLAKA dikkate al ve her yanıtında kullan! Eğer kullanıcının hastalıkları, alerjileri veya tercihleri varsa, bunları göz ardı etme. Her supplement önerisinde bu bilgileri dikkate al ve güvenli tavsiyeler ver. Context'i kullanmazsan yanıtın eksik olur. Sen bu kullanıcının kişisel sağlık asistanısın - önceki konuşmaları hatırla ve kişiselleştirilmiş yanıtlar ver!"
        
        # Update system message with detected language - system prompt'u her zaman ilk sıraya ekle
        updated_messages = [{"role": "system", "content": system_prompt}] + [
            msg for msg in messages if msg["role"] != "system"
        ]
        
        # Step 1: Single model call (optimized for GPT-5)
        responses = []
        if len(PARALLEL_MODELS) == 1:
            # Tek model - direkt çağır, ThreadPool gereksiz
            try:
                result = call_chat_model(PARALLEL_MODELS[0], updated_messages, 0.6, 800)
                if is_valid_chat(result["content"]):
                    responses.append({
                        "model": PARALLEL_MODELS[0],
                        "response": result["content"]
                    })
            except Exception as e:
                print(f"Chat model {PARALLEL_MODELS[0]} failed: {e}")
        else:
            # Çoklu model - paralel çağır
            with ThreadPoolExecutor(max_workers=len(PARALLEL_MODELS)) as executor:
                future_to_model = {
                    executor.submit(call_chat_model, model, updated_messages, 0.6, 800): model 
                    for model in PARALLEL_MODELS
                }
                
                for future in as_completed(future_to_model):
                    model = future_to_model[future]
                    try:
                        result = future.result()
                        if is_valid_chat(result["content"]):
                            responses.append({
                                "model": model,
                                "response": result["content"]
                            })
                    except Exception as e:
                        print(f"Chat model {model} failed: {e}")
                        # Rate limiting hatası varsa biraz bekle
                        if "429" in str(e) or "Too Many Requests" in str(e):
                            print(f"Rate limiting detected for {model}, waiting...")
                            time.sleep(2)
                        continue
        
        # Step 2: If no valid responses, fallback
        if not responses:
            print("All chat models failed, fallback to GPT-4o")
            return gpt4o_fallback(updated_messages)
        
        # Step 3: If only one response, return it directly
        if len(responses) == 1:
            cleaned = _sanitize_links(responses[0]["response"]) 
            return {
                "content": cleaned,
                "model_used": responses[0]["model"]
            }
        
        # Step 4: Synthesize multiple responses with GPT-5
        # TEK MODEL KULLANILDIĞINDA SYNTHESIS'E GEREK YOK
        # synthesis_prompt = build_chat_synthesis_prompt(responses, messages[-1]["content"])
        # final_result = call_chat_model(SYNTHESIS_MODEL, synthesis_prompt, temperature=0.3, max_tokens=2000)
        
        # final_result["models_used"] = [r["model"] for r in responses]
        # final_result["synthesis_model"] = SYNTHESIS_MODEL
        # return final_result
        
        # Tek model kullanıldığında direkt response'u döndür
        cleaned_multi = _sanitize_links(responses[0]["response"]) 
        return {
            "content": cleaned_multi,
            "model_used": responses[0]["model"]
        }
        
    except Exception as e:
        print(f"Parallel chat failed: {e}, fallback to sequential")
        return cascade_chat_fallback(messages)

def cascade_chat_fallback(messages: List[Dict[str, str]]) -> Dict[str, Any]:
    """Fallback to sequential cascade for chat"""
    # Detect user language
    user_message = messages[-1]["content"] if messages else ""
    user_language = detect_language(user_message)
    
    # Use appropriate system prompt
    if user_language == "english":
        system_prompt = SYSTEM_HEALTH_ENGLISH
    else:
        system_prompt = SYSTEM_HEALTH
    
    # Context'i system prompt'a ekle (main.py'den gelen context)
    # System message'dan context'i al
    context = None
    for msg in messages:
        if msg.get("role") == "system" and "context_data" in msg:
            context = msg["context_data"]
            break
    
    if context:
        system_prompt += "\n\nKULLANICI BİLGİLERİ:\n"
        if "isim" in context:
            system_prompt += f"İsim: {context['isim']}\n"
        if "tercihler" in context:
            system_prompt += f"Tercihler: {', '.join(context['tercihler'])}\n"
        if "hastaliklar" in context:
            system_prompt += f"Hastalıklar: {', '.join(context['hastaliklar'])}\n"
        if "yas" in context and context["yas"]:
            system_prompt += f"Yaş: {context['yas']}\n"
        if "cinsiyet" in context and context["cinsiyet"]:
            system_prompt += f"Cinsiyet: {context['cinsiyet']}\n"
        system_prompt += "\n\nKRİTİK TALİMAT: Bu kullanıcı bilgilerini MUTLAKA dikkate al ve her yanıtında kullan. Eğer kullanıcının hastalıkları, alerjileri veya tercihleri varsa, bunları göz ardı etme. Her supplement önerisinde bu bilgileri dikkate al ve güvenli tavsiyeler ver. Context'i kullanmazsan yanıtın eksik olur."
    
    # Update messages with correct language - system prompt'u her zaman ilk sıraya ekle
    updated_messages = [{"role": "system", "content": system_prompt}] + [
        msg for msg in messages if msg["role"] != "system"
    ]
    
    for model in PARALLEL_MODELS:
        try:
            res = call_chat_model(model, updated_messages, temperature=0.6, max_tokens=1500)
            if is_valid_chat(res["content"]):
                res["content"] = _sanitize_links(res["content"]) 
                res["model_used"] = model
                return res
        except Exception as e:
            print(f"Chat fallback model {model} failed: {e}")
            # Rate limiting hatası varsa biraz bekle
            if "429" in str(e) or "Too Many Requests" in str(e):
                print(f"Rate limiting detected for {model}, waiting...")
                time.sleep(2)
            continue
    # if none acceptable, return last model name with empty content
    return {"content": "", "model_used": PARALLEL_MODELS[-1]}

# Chat synthesis prompt fonksiyonu kaldırıldı - tek model kullanıldığı için gerekli değil

# Keep old function for backward compatibility
def cascade_chat(messages: List[Dict[str, str]]) -> Dict[str, Any]:
    return parallel_chat(messages)

def gpt4o_fallback(messages: List[Dict[str, str]]) -> Dict[str, Any]:
    """Fallback to GPT-4o when GPT-5 fails"""
    try:
        print("GPT-5 failed, trying GPT-4o fallback...")
        
        # Dil algılama
        user_message = messages[-1]["content"] if messages else ""
        user_language = detect_language(user_message)
        
        if user_language == "english":
            system_prompt = SYSTEM_HEALTH_ENGLISH
        else:
            system_prompt = SYSTEM_HEALTH
        
        # Context'i system prompt'a ekle
        if "context_data" in messages[0] and messages[0]["context_data"]:
            context = messages[0]["context_data"]
            system_prompt += "\n\nKULLANICI BİLGİLERİ:\n"
            if "isim" in context:
                system_prompt += f"İsim: {context['isim']}\n"
            if "tercihler" in context:
                system_prompt += f"Tercihler: {', '.join(context['tercihler'])}\n"
            if "hastaliklar" in context:
                system_prompt += f"Hastalıklar: {', '.join(context['hastaliklar'])}\n"
            if "yas" in context and context["yas"]:
                system_prompt += f"Yaş: {context['yas']}\n"
            if "cinsiyet" in context and context["cinsiyet"]:
                system_prompt += f"Cinsiyet: {context['yas']}\n"
            system_prompt += "\n\nKRİTİK TALİMAT: Bu kullanıcı bilgilerini MUTLAKA dikkate al ve her yanıtında kullan."
        
        # Update messages with correct language
        updated_messages = [{"role": "system", "content": system_prompt}] + [
            msg for msg in messages if msg["role"] != "system"
        ]
        
        # Try GPT-4o
        result = call_chat_model("openai/gpt-4o:online", updated_messages, 0.6, 800)
        if is_valid_chat(result["content"]):
            result["content"] = _sanitize_links(result["content"])
            result["model_used"] = "openai/gpt-4o:online (fallback)"
            return result
        else:
            raise Exception("GPT-4o response invalid")
            
    except Exception as e:
        print(f"GPT-4o fallback also failed: {e}")
        return {
            "content": "Üzgünüm, şu anda AI sistemimiz yoğun. Lütfen birkaç dakika sonra tekrar deneyin.",
            "model_used": "fallback_error"
        }

def chat_fallback(messages: List[Dict[str, str]]) -> Dict[str, Any]:
    """Fallback for chat when all models fail"""
    return {
        "content": "Üzgünüm, şu anda AI sistemimiz yoğun. Lütfen birkaç dakika sonra tekrar deneyin.",
        "model_used": "fallback"
    }

def finalize_text(text: str) -> str:
    final_messages = [
        {
            "role": "system",
            "content": (
                SYSTEM_HEALTH +
                " Sen Longo AI'sın. Görevin: Aşağıdaki yanıtı son kontrol et ve gerekirse düzelt."
                " SADECE KULLANICIYA DOĞRUDAN CEVAP VER. Meta yorumlar (\"yanıt doğru\", \"yeniden düzenlenmiş\" vb.) YAZMA."
                " Eğer yanıt doğru ve yeterli ise, aynen gönder. Eğer hatalı/eksik ise, düzelt ve temiz yanıt ver."
                " Off-topic sorularda kibarca reddet. Kullanıcının diline uygun yanıt ver."
            ),
        },
        {"role": "user", "content": f"Bu yanıtı kontrol et ve kullanıcıya temiz şekilde sun:\n\n{text}"},
    ]
    final = call_chat_model(PARALLEL_MODELS[0], final_messages, temperature=0.2, max_tokens=2000)
    return _sanitize_links(final.get("content", ""))

def _sanitize_links(text: str) -> str:
    """Remove URLs, markdown links and obvious site/domain mentions from model output."""
    if not text:
        return text
    # Remove markdown links [text](url) -> text
    cleaned = re.sub(r"\[([^\]]+)\]\((https?://[^\s)]+)\)", r"\1", text)
    # Remove raw URLs
    cleaned = re.sub(r"https?://\S+", "", cleaned)
    # Remove common domain mentions (with or without www)
    cleaned = re.sub(r"\b(?:www\.)?[A-Za-z0-9.-]+\.(?:com|org|net|io|ai|co|tr|edu|gov)(?:/[^\s]*)?", "", cleaned)
    # Remove numeric citation brackets like [1], [2]
    cleaned = re.sub(r"\[\s*\d+\s*\]", "", cleaned)
    # Remove parenthetical 'source:' notes
    cleaned = re.sub(r"\(\s*source\s*:[^)]*\)", "", cleaned, flags=re.IGNORECASE)
    # Remove empty parentheses left behind
    cleaned = re.sub(r"\(\s*\)", "", cleaned)
    # Fix common stray punctuation around parentheses
    cleaned = re.sub(r"\s*,\s*\)", ")", cleaned)
    cleaned = re.sub(r"\(\s*,\s*", "(", cleaned)
    # Collapse duplicate commas and spaces
    cleaned = re.sub(r",\s*,+", ", ", cleaned)
    # Collapse extra whitespace
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip()
    return cleaned



def build_synthesis_prompt(responses: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """Build prompt for GPT-5 to synthesize multiple model responses"""
    system_prompt = (
        SYSTEM_HEALTH + " Sen bir synthesis uzmanısın. "
        "Birden fazla AI modelin verdiği analiz sonuçlarını inceleyip, "
        "en doğru, tutarlı ve faydalı bir FINAL sonuç üret. "
        "\n\nKurallar:"
        "\n1. SADECE JSON formatında yanıt ver"
        "\n2. En tutarlı önerileri birleştir"
        "\n3. Çelişkili önerilerde en mantıklı olanı seç"
        "\n6. Tekrarlayan önerileri birleştir"
        "\n7. ÖNEMLI: Her öneri için 'source' alanı MUTLAKA 'consensus' olmalı"
    )
    
    # Format all responses for comparison
    responses_text = "\n\n=== MODEL RESPONSES ===\n"
    for i, resp in enumerate(responses, 1):
        responses_text += f"\nMODEL {i} ({resp['model']}):\n{resp['response']}\n"
    
    responses_text += "\n=== SYNTHESIS GÖREV ===\n"
    responses_text += (
        "Yukarıdaki tüm model yanıtlarını analiz et ve tek bir tutarlı JSON oluştur. "
        "En iyi önerileri birleştir, analysis'i geliştir, risk değerlendirmesini optimize et."
    )
    
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": responses_text}
    ]








def build_quiz_prompt(quiz_answers: Dict[str, Any], available_supplements: List[Dict[str, Any]] = None) -> List[Dict[str, str]]:
    """Build prompt for quiz analysis and supplement recommendations - ESNEK YAPI + DEFAULT SUPPLEMENTS"""
    
    # Quiz cevaplarını dinamik olarak işle
    profile = []
    for key, value in quiz_answers.items():
        if isinstance(value, list):
            profile.append(f"{key}: {', '.join(map(str, value))}")
        else:
            profile.append(f"{key}: {value}")
    
    user_profile_text = "\n".join(profile)
    
    # Ürün kataloğu bilgisi - TÜM ÜRÜNLERİ LİSTELE
    supplements_info = ""
    if available_supplements:
        supplements_info = f"\n\nTÜM KULLANILABİLİR ÜRÜNLER (Toplam: {len(available_supplements)}):\n"
        
        # Tüm ürünleri basit liste halinde göster
        for i, supplement in enumerate(available_supplements, 1):
            product_name = supplement.get('name', 'Bilinmeyen')
            product_id = supplement.get('id', 'ID yok')
            supplements_info += f"{i}. {product_name} (ID: {product_id})\n"
        
        supplements_info += f"\n💡 AI: Tüm bu ürünler arasından en uygun olanları seç!"
    else:
        supplements_info = "\n\n⚠️ Kullanılabilir ürün listesi bulunamadı. Default supplement'ler önerilecek."

    # Default supplement'ler ve alerji kontrolü
    default_supplements_info = """
    
    DEFAULT SUPPLEMENT'LER (Herkes için önerilen):
    1. D Vitamini - Kemik sağlığı ve bağışıklık için
    2. Omega-3 - Kalp ve beyin sağlığı için  
    3. Magnezyum - Kas ve sinir sistemi için
    4. B12 Vitamini - Enerji ve kan hücreleri için
    
    ALERJİ KONTROLÜ:
    - Eğer kullanıcının alerjisi varsa, o supplement'i default'tan çıkar
    - Alerji durumunda alternatif öner
    - Riskli durumlar varsa güvenli alternatifler öner
    
    ÖZEL DURUMLAR ANALİZİ:
    - Quiz'de 'Diğer' seçeneği varsa, o metni dikkatle analiz et
    - Kullanıcının yazdığı hastalıkları, alerjileri, özel durumları tespit et
    - Bu bilgilere göre supplement önerilerini güncelle
    - Riskli durumlar varsa güvenli alternatifler öner
    - Örnek: 'Diyabet hastasıyım' → şeker içeren supplement'leri çıkar, available_supplements'dan alternatif ekle
    - Örnek: 'Balık alerjim var' → Omega-3'ü çıkar, available_supplements'dan alternatif öner
    - Örnek: 'Kan sulandırıcı kullanıyorum' → Omega-3'ü çıkar, available_supplements'dan alternatif ekle
    - Örnek: 'Tiroit problemi var' → iyot içeren supplement'leri çıkar, available_supplements'dan alternatif ekle
    - Örnek: 'Böbrek problemi var' → yüksek doz vitamin'leri çıkar, available_supplements'dan alternatif ekle
    
    KİŞİSELLEŞTİRİLMİŞ ÖNERİLER:
    - Quiz cevaplarına göre ek 2-3 supplement öner
    - Sadece kullanılabilir ürünlerden seçim yap
    - Özel durumları dikkate alarak güvenli öneriler yap
    """
    
    schema = (
        "STRICT JSON ŞEMASI - SUPPLEMENT ÖNERİLERİ:\n"
        "{\n"
        '  "nutrition_advice": {\n'
        '    "title": "Beslenme Önerileri",\n'
        '    "recommendations": ["Öneri 1", "Öneri 2", "Öneri 3"]\n'
        "  },\n"
        '  "lifestyle_advice": {\n'
        '    "title": "Yaşam Tarzı Önerileri",\n'
        '    "recommendations": ["Öneri 1", "Öneri 2", "Öneri 3"]\n'
        "  },\n"
        '  "general_warnings": {\n'
        '    "title": "Genel Uyarılar",\n'
        '    "warnings": ["Uyarı 1", "Uyarı 2", "Uyarı 3"]\n'
        "  },\n"
        '  "supplement_recommendations": [\n'
        "    {\n"
        '      "name": "Ürün adı (kullanılabilir ürünlerden seç)",\n'
        '      "description": "Neden önerildiği",\n'
        '      "daily_dose": "Günlük doz",\n'
        '      "benefits": ["Faydaları"],\n'
        '      "warnings": ["Uyarılar"],\n'
        '      "priority": "high/medium/low",\n'
        '      "type": "default/personalized"\n'
        "    }\n"
        "  ]\n"
        "}\n\n"
        "ÖNEMLİ: 1) 4 DEFAULT + 2-3 PERSONALIZED = 6-7 supplement öner! "
        "2) DEFAULT: D Vitamini, Omega-3, Magnezyum, B12 (alerji kontrolü ile) "
        "3) PERSONALIZED: Quiz cevaplarına göre eksik değerler için "
        "4) SADECE kullanılabilir ürünlerden seçim yap! "
        "5) 'Diğer' seçeneğindeki özel durumları analiz et! "
        "SADECE VE SADECE bu JSON formatında yanıt ver. Hiçbir açıklama, metin ekleme."
    )
    
    system_prompt = (
        SYSTEM_HEALTH + " Sen bir supplement uzmanısın. "
        "Kullanıcının quiz cevaplarına göre beslenme önerileri, yaşam tarzı önerileri ve "
        "uygun supplement önerileri yap. E-ticaret sitesi için ürün önerileri hazırlıyorsun. "
        "1) 4 DEFAULT + 2-3 PERSONALIZED = 6-7 supplement öner! "
        "2) DEFAULT: D Vitamini, Omega-3, Magnezyum, B12 (alerji kontrolü ile) "
        "3) PERSONALIZED: Quiz cevaplarına göre eksik değerler için "
        "4) SADECE kullanılabilir ürünlerden öneri yap! "
        "5) 'Diğer' seçeneğindeki özel durumları dikkatle analiz et ve supplement önerilerini buna göre güncelle! "
        "6) Riskli durumlar varsa güvenli alternatifler öner! "
        "7) ÖNEMLİ: Sadece kullanıcıya verilen supplement listesinden öneri yap! "
        "8) Eğer listede yoksa, o supplement'i önerme! "
        "9) Kullanıcıya hiçbir şekilde ihtiyacı olmayan supplement önerme! "
        "10) Kullanıcının yaşı, cinsiyeti, sağlık durumu, alerjileri, kullandığı ilaçlar dikkate al! "
        "11) Riskli durumlar varsa o supplement'i önerme! "
        "12) Sadece gerçekten gerekli olan supplementleri öner! "
        "13) DİL: SADECE TÜRKÇE YANIT VER! İngilizce kelime, terim veya cümle kullanma!"
    )
    
    user_prompt = f"Kullanıcı profili:\n{user_profile_text}{supplements_info}{default_supplements_info}\n\n{schema}"
    
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]

def parallel_quiz_analyze(quiz_answers: Dict[str, Any], available_supplements: List[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Run quiz analysis with parallel LLMs and synthesis - ESNEK YAPI"""
    try:
        messages = build_quiz_prompt(quiz_answers, available_supplements)
        
        # Step 1: Single/multiple model call (optimized)
        responses = []
        if len(PARALLEL_MODELS) == 1:
            # Tek model - direkt çağır
            try:
                result = call_chat_model(PARALLEL_MODELS[0], messages, 0.2, 4000)
                if result and result.get("content"):
                    responses.append({
                        "model": PARALLEL_MODELS[0],
                        "response": result["content"]
                    })
            except Exception as e:
                print(f"Quiz model {PARALLEL_MODELS[0]} failed: {e}")
        else:
            # Çoklu model - paralel çağır
            with ThreadPoolExecutor(max_workers=len(PARALLEL_MODELS)) as executor:
                future_to_model = {
                    executor.submit(call_chat_model, model, messages, 0.2, 4000): model 
                    for model in PARALLEL_MODELS
                }
                
                for future in as_completed(future_to_model):
                    model = future_to_model[future]
                    try:
                        result = future.result()
                        # For quiz, we want any valid JSON response
                        if result["content"].strip():
                            responses.append({
                                "model": model,
                                "response": result["content"]
                            })
                    except Exception as e:
                        print(f"Quiz model {model} failed: {e}")
                        continue
        
        # Step 2: If no responses, fallback
        if not responses:
            print("All quiz models failed, fallback to GPT-4o")
            return gpt4o_quiz_fallback(quiz_answers, available_supplements)
        
        # Step 3: Tek model kullanıldığı için synthesis'e gerek yok - direkt response'u döndür
        cleaned_response = _sanitize_links(responses[0]["response"])
        return {
            "content": cleaned_response,
            "model_used": responses[0]["model"],
            "models_used": [r["model"] for r in responses]
        }
        
    except Exception as e:
        print(f"Quiz parallel analyze failed: {e}")
        return gpt4o_quiz_fallback(quiz_answers, available_supplements)

# Quiz synthesis prompt fonksiyonu kaldırıldı - tek model kullanıldığı için gerekli değil

def gpt4o_quiz_fallback(quiz_answers: Dict[str, Any], available_supplements: List[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Fallback to GPT-4o for quiz analysis when GPT-5 fails"""
    try:
        print("GPT-5 failed, trying GPT-4o fallback for quiz analysis...")
        
        # Build prompt for GPT-4o
        messages = build_quiz_prompt(quiz_answers, available_supplements)
        
        # Try GPT-4o
        result = call_chat_model("openai/gpt-4o:online", messages, 0.2, 4000)
        if result["content"].strip():
            result["content"] = _sanitize_links(result["content"])
            result["model_used"] = "openai/gpt-4o:online (fallback)"
            return result
        else:
            raise Exception("GPT-4o response invalid")
            
    except Exception as e:
        print(f"GPT-4o quiz fallback also failed: {e}")
        return quiz_fallback(quiz_answers, available_supplements)

def quiz_fallback(quiz_answers: Dict[str, Any], available_supplements: List[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Fallback quiz analysis if parallel fails"""
    messages = build_quiz_prompt(quiz_answers, available_supplements)
    for model in PARALLEL_MODELS:
        try:
            res = call_chat_model(model, messages, temperature=0.2, max_tokens=4000)
            if res["content"].strip():
                res["model_used"] = model
                return res
        except Exception as e:
            print(f"Quiz fallback model {model} failed: {e}")
            # Rate limiting hatası varsa biraz bekle
            if "429" in str(e) or "Too Many Requests" in str(e):
                print(f"Rate limiting detected for {model}, waiting...")
                time.sleep(2)
            continue
    
    # Ultimate fallback - QuizResponse schema'sına uygun
    return {
        "content": json.dumps({
            "success": True,
            "message": "Quiz analizi geçici olarak kullanılamıyor",
            "nutrition_advice": {"title": "Beslenme Önerileri", "recommendations": ["Sistem geçici olarak kullanılamıyor"]},
            "lifestyle_advice": {"title": "Yaşam Tarzı Önerileri", "recommendations": ["Sistem geçici olarak kullanılamıyor"]},
            "general_warnings": {"title": "Genel Uyarılar", "warnings": ["Sistem geçici olarak kullanılamıyor"]},
            "supplement_recommendations": [
                {"name": "D Vitamini", "description": "Default supplement", "priority": "high", "daily_dose": "1000 IU", "benefits": "Kemik sağlığı, bağışıklık sistemi", "warnings": "Doktor kontrolünde kullanın"},
                {"name": "Omega-3", "description": "Default supplement", "priority": "high", "daily_dose": "1000 mg", "benefits": "Kalp sağlığı, beyin fonksiyonu", "warnings": "Balık alerjisi varsa dikkat"},
                {"name": "Magnezyum", "description": "Default supplement", "priority": "high", "daily_dose": "400 mg", "benefits": "Kas fonksiyonu, sinir sistemi", "warnings": "Böbrek sorunu varsa dikkat"},
                {"name": "B12", "description": "Default supplement", "priority": "high", "daily_dose": "1000 mcg", "benefits": "Enerji metabolizması, sinir sistemi", "warnings": "Doktor kontrolünde kullanın"}
            ],
            "disclaimer": "Bu içerik bilgilendirme amaçlıdır; tıbbi tanı/tedavi için hekiminize başvurun."
        }),
        "model_used": "fallback"
    }

def build_single_lab_prompt(test_data: Dict[str, Any], historical_results: List[Dict[str, Any]] = None) -> List[Dict[str, str]]:
    """Build prompt for single lab test analysis with historical trend analysis"""
    
    # Test bilgilerini topla
    test_info = f"Test Adı: {test_data.get('name', 'Bilinmiyor')}\n"
    test_info += f"Sonuç: {test_data.get('value', 'Yok')}"
    
    if test_data.get('unit'):
        test_info += f" {test_data['unit']}"
    test_info += "\n"
    
    if test_data.get('reference_range'):
        test_info += f"Referans Aralığı: {test_data['reference_range']}\n"
    
    if test_data.get('status'):
        test_info += f"Test Durumu: {test_data['status']}\n"
    
    if test_data.get('test_date'):
        test_info += f"Test Tarihi: {test_data['test_date']}\n"
    
    if test_data.get('category'):
        test_info += f"Test Kategorisi: {test_data['category']}\n"
    
    if test_data.get('notes'):
        test_info += f"Ek Notlar: {test_data['notes']}\n"
    
    # Geçmiş sonuçlar varsa trend analizi ekle
    trend_analysis = ""
    if historical_results and len(historical_results) > 0:
        trend_analysis = "\n\n📊 GEÇMİŞ SONUÇLAR VE TREND ANALİZİ:\n"
        trend_analysis += "Tarih sırasına göre (en yeniden en eskiye):\n"
        
        # Tarihe göre sırala (en yeni önce)
        sorted_results = sorted(historical_results, key=lambda x: x.get('date', ''), reverse=True)
        
        for i, result in enumerate(sorted_results, 1):
            date = result.get('date', 'Tarih yok')
            value = result.get('value', 'Değer yok')
            status = result.get('status', 'Durum belirtilmemiş')
            lab = result.get('lab', 'Lab belirtilmemiş')
            notes = result.get('notes', '')
            
            trend_analysis += f"{i}. {date}: {value} {test_data.get('unit', '')} - {status}"
            if lab:
                trend_analysis += f" ({lab})"
            if notes:
                trend_analysis += f" - {notes}"
            trend_analysis += "\n"
        
        trend_analysis += "\n💡 TREND ANALİZİ YAPILACAK:\n"
        trend_analysis += "- Değerlerin zaman içindeki değişimi\n"
        trend_analysis += "- İyileşme/kötüleşme trendi\n"
        trend_analysis += "- Laboratuvar değişikliklerinin etkisi\n"
        trend_analysis += "- Genel sağlık durumu trendi\n"
    
    # Test sonucu analizi için detaylı yönlendirme
    analysis_guide = f"""
    
    LAB TEST ANALİZİ REHBERİ (TREND ANALİZİ İLE):
    
    TEST: {test_data.get('name', 'Bilinmiyor')}
    SONUÇ: {test_data.get('value', 'Yok')} {test_data.get('unit', '')}
    REFERANS: {test_data.get('reference_range', 'Belirtilmemiş')}
    DURUM: {test_data.get('status', 'Belirtilmemiş')}
    KATEGORİ: {test_data.get('category', 'Belirtilmemiş')}
    
    ANALİZ ADIMLARI:
    1. Test sonucunu değerlendir (sayısal veya metin)
    2. Referans aralığı varsa karşılaştır
    3. Sonucun normal, düşük, yüksek veya kritik olduğunu belirt
    4. Bu sonucun klinik anlamını açıkla
    5. Test kategorisine göre özel yorumlar yap
    6. GEÇMİŞ SONUÇLARLA TREND ANALİZİ YAP (varsa)
    7. Genel tıbbi takip önerileri ver (supplement önerisi verme!)
    8. SADECE ANALİZ YAP, SUPPLEMENT ÖNERİSİ VERME!
    
    TREND ANALİZİ (geçmiş sonuçlar varsa):
    - Değerlerin zaman içindeki değişimi nasıl?
    - İyileşme var mı, yoksa kötüleşme mi?
    - Hangi laboratuvarlarda test yapılmış?
    - Genel sağlık durumu trendi nasıl?
    
    ÖRNEKLER:
    - Hemoglobin 12.5 g/dL (Referans: 12.0-15.5) → Normal aralıkta, hafif düşük
    - Vitamin D 18 ng/mL (Referans: 30-100) → Düşük, kemik sağlığı için önemli
    - Kolesterol 250 mg/dL (Referans: <200) → Yüksek, kalp sağlığı için dikkat
    - CBC (Çoklu parametre) → Genel kan durumu değerlendirmesi gerekli
    
    ÖNEMLİ: SADECE ANALİZ YAP, SUPPLEMENT ÖNERİSİ VERME!
    """
    
    schema = (
        "STRICT JSON ŞEMASI - LAB ANALİZİ (TREND ANALİZİ İLE):\n"
        "{\n"
        '  "analysis": {\n'
        '    "summary": "Test sonucunun kısa yorumu (örn: Normal, Düşük, Yüksek, Kritik)",\n'
        '    "interpretation": "Sonucun anlamı ve önemi (detaylı açıklama)",\n'
        '    "reference_comparison": "Referans aralığı ile karşılaştırma (varsa sayısal analiz)",\n'
        '    "clinical_significance": "Klinik önemi (sağlık açısından ne anlama geliyor)",\n'
        '    "category_insights": "Test kategorisine özel yorumlar",\n'
        '    "trend_analysis": "Geçmiş sonuçlarla trend analizi (varsa)",\n'
        '    "follow_up_suggestions": "Takip önerileri (genel tıbbi öneri, supplement değil!)"\n'
        "  }\n"
        "}\n\n"
        "SADECE ANALİZ YAP, SUPPLEMENT ÖNERİSİ VERME! JSON formatında yanıt ver!"
    )
    
    system_prompt = (
        SYSTEM_HEALTH + " Sen bir laboratuvar sonuçları analiz uzmanısın. "
        "SADECE ANALİZ yap, supplement ya da ilaç önerisi verme. "
        "Sonuçları yorumla, klinik anlamını açıkla, genel tıbbi takip önerileri ver. "
        "Test sonucunu referans aralığı ile karşılaştır ve net bir yorum yap. "
        "GEÇMİŞ SONUÇLARLA TREND ANALİZİ YAP (varsa). "
        "Eksik veriler varsa bunları belirt ve gerekli ek testleri öner. "
        "Kullanıcının diline uygun yanıt ver. "
        "SUPPLEMENT ÖNERİSİ VERME! SADECE ANALİZ YAP! "
        "KAYNAK EKLEME: Otomatik olarak kaynak link'leri, referans'lar veya citation'lar ekleme! "
        "DİL: SADECE TÜRKÇE YANIT VER! İngilizce kelime, terim veya cümle kullanma!"
    )
    
    user_prompt = f"Laboratuvar test sonucu:\n{test_info}{trend_analysis}{analysis_guide}\n\n{schema}"
    
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]

def build_single_session_prompt(session_tests: List[Dict[str, Any]], session_date: str, laboratory: str) -> List[Dict[str, str]]:
    """Build prompt for single lab session analysis - Tek seans analizi"""
    
    # Seans bilgileri
    session_info = f"Test Seansı Bilgileri:\n"
    session_info += f"Laboratuvar: {laboratory}\n"
    session_info += f"Test Tarihi: {session_date}\n"
    session_info += f"Toplam Test Sayısı: {len(session_tests)}\n\n"
    
    # Test sonuçları
    tests_info = "Test Sonuçları:\n"
    for i, test in enumerate(session_tests, 1):
        tests_info += f"{i}. {test.get('name', 'Test')}: {test.get('value', 'Yok')} {test.get('unit', '')}"
        if test.get('reference_range'):
            tests_info += f" (Referans: {test['reference_range']})"
        if test.get('status'):
            tests_info += f" - {test['status']}"
        tests_info += "\n"
    
    # Test grupları analizi
    test_groups = {}
    normal_count = 0
    attention_count = 0
    
    for test in session_tests:
        # Category field'ı yoksa 'Genel' kullan
        category = test.get('category')
        if not category:
            category = 'Genel'
        
        if category not in test_groups:
            test_groups[category] = 0
        test_groups[category] += 1
        
        # Status field'ı yoksa normal say
        status = test.get('status')
        if status and status.lower() in ['normal', 'normal aralıkta']:
            normal_count += 1
        else:
            attention_count += 1
    
    groups_summary = "Test Grupları:\n"
    for group, count in test_groups.items():
        groups_summary += f" {group.upper()} ({count} test)\n"
    
    summary_stats = f"Test Sonuçları Özeti:\n"
    summary_stats += f"{len(session_tests)} Toplam Test\n"
    summary_stats += f"{normal_count} Normal Değer\n"
    summary_stats += f"{attention_count} Dikkat Gereken\n"
    
    # Basit talimat
    instructions = "ÖNEMLİ: Tek seans analizi yap, supplement önerisi verme, sadece genel sağlık yorumu ve önerileri ver! SADECE ANALİZ YAP!"
    
    system_prompt = (
        SYSTEM_HEALTH + " Sen bir laboratuvar seans analiz uzmanısın. "
        "Tek bir test seansındaki tüm testleri analiz et ve genel sağlık durumu yorumu yap. "
        "Test gruplarını kategorize et, normal/anormal sayılarını belirt. "
        "Genel sağlık önerileri ver ama supplement önerisi verme. "
        "SUPPLEMENT ÖNERİSİ VERME! SADECE ANALİZ YAP! "
        "Sadece bilgilendirme amaçlı yorum yap, tıbbi tanı koyma. "
        "\n\nDİL KURALLARI - ÇOK ÖNEMLİ:"
        "\n- SADECE TÜRKÇE KULLAN!"
        "\n- İngilizce kelime, terim, cümle KULLANMA!"
        "\n- Test adlarını Türkçe yaz: 'D Vitamini' (Vitamin D değil)"
        "\n- Kategori adlarını Türkçe yaz: 'Vitaminler' (Vitamins değil)"
        "\n- Tüm açıklamaları Türkçe yap!"
        "\n- İngilizce referans, kaynak, terim EKLEME!"
        "\n- Annotations'da bile İngilizce kullanma!"
        "\n- Sadece Türkçe kelimeler ve terimler kullan!"
        "\n\nÖNEMLİ: Yanıtını SADECE JSON formatında ver! Aşağıdaki yapıyı kullan:"
        '\n{\n'
        '  "genel_saglik_yorumu": "Genel sağlık yorumu buraya",\n'
        '  "sonuc": "Sonuç özeti buraya",\n'
        '  "test_sonuclari": {"Test Kategorisi": [{"test_adi": "Test Adı", "sonuc": "Sonuç", "referans_araligi": "Referans", "durum": "Normal/Anormal"}]},\n'
        '  "istatistik": {"normal": 0, "anormal": 1},\n'
        '  "toplam_test_sayisi": 1,\n'
        '  "oneriler": {"yasam_tarzi": ["Öneri 1"], "laboratuvar_takibi": ["Öneri 2"], "doktor_kontrolu": "Öneri 3"}\n'
        '}'
    )
    
    user_prompt = f"Laboratuvar seans bilgileri:\n{session_info}{tests_info}\n\n{instructions}"
    
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]

def build_multiple_lab_prompt(tests_data: List[Dict[str, Any]], session_count: int, available_supplements: List[Dict[str, Any]] = None, user_profile: Dict[str, Any] = None) -> List[Dict[str, str]]:
    """Build prompt for multiple lab tests general summary - ÜRÜN KATALOĞU ENTEGRASYONU"""
    
    tests_info = f"Toplam Test Seansı: {session_count}\n\n"
    tests_info += "Test Sonuçları:\n"
    for i, test in enumerate(tests_data, 1):
        tests_info += f"{i}. {test.get('name', 'Test')}: {test.get('value', 'Yok')} {test.get('unit', '')}"
        if test.get('reference_range'):
            tests_info += f" (Referans: {test['reference_range']})"
        tests_info += "\n"
    
    # Ürün kataloğu bilgisi - TÜM ÜRÜNLERİ LİSTELE
    supplements_info = ""
    if available_supplements:
        supplements_info = f"\n\nTÜM KULLANILABİLİR ÜRÜNLER (Toplam: {len(available_supplements)}):\n"
        
        # Tüm ürünleri basit liste halinde göster
        for i, supplement in enumerate(available_supplements, 1):
            product_name = supplement.get('name', 'Bilinmeyen')
            product_id = supplement.get('id', 'ID yok')
            supplements_info += f"{i}. {product_name} (ID: {product_id})\n"
        
        supplements_info += f"\n💡 AI: Tüm bu ürünler arasından en uygun olanları seç!"
    else:
        supplements_info = "\n\n⚠️ Kullanılabilir ürün listesi bulunamadı. Default supplement'ler önerilecek."

    # Kullanıcı profili bilgisi - SADECE RİSK FAKTÖRLERİ
    user_profile_info = ""
    if user_profile:
        risk_factors = []
        
        # Özel durumlar (alerji, hastalık, ilaç)
        if user_profile.get("diger"):
            risk_factors.append(f"Özel durum: {user_profile['diger']}")
        
        # Yaş risk faktörleri
        if user_profile.get("yas"):
            age = user_profile["yas"]
            if isinstance(age, str) and age.isdigit():
                age_num = int(age)
                if age_num >= 65:
                    risk_factors.append("Yaşlı hasta (65+)")
                elif age_num <= 18:
                    risk_factors.append("Genç hasta (18-)")
        
        # Hamilelik/emzirme
        if user_profile.get("hamilelik") or user_profile.get("emzirme"):
            risk_factors.append("Hamilelik/Emzirme dönemi")
        
        # Kronik hastalıklar
        chronic_conditions = ["diyabet", "kalp", "böbrek", "karaciğer", "tiroid"]
        for condition in chronic_conditions:
            if user_profile.get(condition):
                risk_factors.append(f"Kronik hastalık: {condition}")
        
        # İlaç kullanımı
        if user_profile.get("ilac_kullanimi"):
            risk_factors.append(f"İlaç kullanımı: {user_profile['ilac_kullanimi']}")
        
        if risk_factors:
            user_profile_info = f"\n\n⚠️ RİSK FAKTÖRLERİ:\n" + "\n".join(risk_factors)
            user_profile_info += "\n\nBu risk faktörleri lab test yorumunda dikkate alınmalıdır."
    
    schema = (
        "STRICT JSON ŞEMASI - LAB SUMMARY (YENİ FORMAT):\n"
        "{\n"
        '  "title": "Tüm Testlerin Genel Yorumu",\n'
        '  "genel_saglik_durumu": "Genel Sağlık Durumu Değerlendirmesi",\n'
        '  "test_sayisi": "Test Sayısı: X farklı test seansı",\n'
        '  "genel_durum": "Testlerin genel kapsamlı analizi varsa eski sonuçlarla karşılaştırma.",\n'
        '  "oneriler": ["Genel öneriler"],\n'
        '  "urun_onerileri": [\n'
        '    {\n'
        '    "name": "Ürün adı (kullanılabilir ürünlerden seç)",\n'
        '    "description": "Neden önerildiği",\n'
        '    "daily_dose": "Günlük doz",\n'
        '    "benefits": ["Faydaları"],\n'
        '    "warnings": ["Uyarılar"],\n'
        '    "priority": "high/medium/low"\n'
        '    }\n'
        "  ]\n"
        "}\n\n"
        "ÖNEMLİ: 1) Başlık, 2) Genel sağlık durumu, 3) Test sayısı, 4) Genel durum, 5) Öneriler, 6) EN SON ürün önerileri! "
        "Supplement önerilerinde SADECE kullanılabilir ürünlerden seçim yap! "
        "MUTLAKA urun_onerileri field'ını doldur! "
        "4-6 supplement öner! "
    )
    
    system_prompt = (
        SYSTEM_HEALTH + " Sen bir laboratuvar sonuçları ve sağlık danışmanlığı uzmanısın. "
        "Lab test sonuçlarını analiz et, genel sağlık durumunu değerlendir. "
        "Eksik değerler için uygun supplement önerileri yap. "
        "Tıbbi tanı koyma, sadece bilgilendirme amaçlı öneriler ver. "
        "ÖNEMLİ: 1) Başlık, 2) Genel sağlık durumu, 3) Test sayısı, 4) Genel durum, 5) Öneriler, 6) EN SON ürün önerileri! "
        "Supplement önerilerinde SADECE kullanılabilir ürünlerden seçim yap! "
        "MUTLAKA urun_onerileri field'ını doldur! "
        "4-6 supplement öner! "
        "Kullanıcıya hiçbir şekilde ihtiyacı olmayan supplement önerme! "
        "DİL: SADECE TÜRKÇE YANIT VER! İngilizce kelime, terim veya cümle kullanma!"
    )
    
    user_prompt = f"Laboratuvar test sonuçları:\n{tests_info}{supplements_info}{user_profile_info}\n\n{schema}"
    
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]

def parallel_single_lab_analyze(test_data: Dict[str, Any], historical_results: List[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Analyze single lab test with parallel LLMs and historical trend analysis"""
    try:
        messages = build_single_lab_prompt(test_data, historical_results)
        
        # Parallel analysis
        responses = []
        with ThreadPoolExecutor(max_workers=len(PARALLEL_MODELS)) as executor:
            future_to_model = {
                executor.submit(call_chat_model, model, messages, 0.3, 1200): model 
                for model in PARALLEL_MODELS
            }
            
            for future in as_completed(future_to_model):
                model = future_to_model[future]
                try:
                    result = future.result()
                    if result["content"].strip():
                        responses.append({
                            "model": model,
                            "response": result["content"]
                        })
                except Exception as e:
                    print(f"Single lab model {model} failed: {e}")
                    # Rate limiting hatası varsa biraz bekle
                    if "429" in str(e) or "Too Many Requests" in str(e):
                        print(f"Rate limiting detected for {model}, waiting...")
                        time.sleep(2)
                    continue
        
        if not responses:
            print("No successful responses, using GPT-4o fallback")
            return gpt4o_lab_fallback(test_data, historical_results)
        
        # Tek model kullanıldığı için synthesis'e gerek yok - direkt response'u döndür
        cleaned_response = _sanitize_links(responses[0]["response"])
        return {
            "content": cleaned_response,
            "model_used": responses[0]["model"],
            "models_used": [r["model"] for r in responses]
        }
        
    except Exception as e:
        print(f"Single lab analyze failed: {e}")
        return gpt4o_lab_fallback(test_data, historical_results)

def parallel_single_session_analyze(session_tests: List[Dict[str, Any]], session_date: str, laboratory: str) -> Dict[str, Any]:
    """Analyze single lab session with multiple tests - Tek seans analizi"""
    try:
        messages = build_single_session_prompt(session_tests, session_date, laboratory)
        
        # Single model analysis (optimized for GPT-5)
        responses = []
        if len(PARALLEL_MODELS) == 1:
            # Tek model - direkt çağır
            try:
                result = call_chat_model(PARALLEL_MODELS[0], messages, 0.3, 1500)
                
                if result and result.get("content") and result["content"].strip():
                    responses.append({
                        "model": PARALLEL_MODELS[0],
                        "response": result["content"]
                    })
            except Exception as e:
                # Production'da log yerine fallback kullan
                pass
        else:
            # Çoklu model - paralel çağır
            with ThreadPoolExecutor(max_workers=len(PARALLEL_MODELS)) as executor:
                future_to_model = {
                    executor.submit(call_chat_model, model, messages, 0.3, 1500): model 
                    for model in PARALLEL_MODELS
                }
                
                for future in as_completed(future_to_model):
                    model = future_to_model[future]
                    try:
                        result = future.result()
                        if result["content"].strip():
                            responses.append({
                                "model": model,
                                "response": result["content"]
                            })
                    except Exception as e:
                        print(f"Single session model {model} failed: {e}")
                        # Rate limiting hatası varsa biraz bekle
                        if "429" in str(e) or "Too Many Requests" in str(e):
                            time.sleep(2)
                        continue
        
        if not responses:
            print("No successful responses, using GPT-4o fallback")
            return gpt4o_session_fallback(session_tests, session_date, laboratory)
        
        # Tek model kullanıldığı için synthesis'e gerek yok - direkt AI response'u kullan
        ai_response = responses[0]["response"]
        
        # AI model'in response'unu schema'ya uygun hale getir
        try:
            if ai_response and isinstance(ai_response, str):
                # Markdown wrapper'ını temizle (```json ... ``` formatında olabilir)
                cleaned_response = ai_response.strip()
                if cleaned_response.startswith('```json'):
                    cleaned_response = cleaned_response[7:]  # ```json kısmını çıkar
                if cleaned_response.endswith('```'):
                    cleaned_response = cleaned_response[:-3]  # son ``` kısmını çıkar
                cleaned_response = cleaned_response.strip()
                
                # AI response'u parse et
                parsed_response = json.loads(cleaned_response) if cleaned_response.startswith('{') else {}
                
                # Schema'ya uygun response oluştur
                formatted_response = {
                    "session_info": {
                        "laboratory": laboratory,
                        "session_date": session_date,
                        "total_tests": len(session_tests)
                    },
                    "general_assessment": {
                        "clinical_meaning": parsed_response.get("genel_saglik_yorumu", "Test seansı analizi yapıldı"),
                        "overall_health_status": parsed_response.get("sonuc", "Genel sağlık durumu değerlendirildi")
                    },
                    "test_groups": parsed_response.get("test_sonuclari", {}),
                    "test_summary": {
                        "total_tests": parsed_response.get("toplam_test_sayisi", len(session_tests)),
                        "normal_count": parsed_response.get("istatistik", {}).get("normal", 0),
                        "attention_count": parsed_response.get("istatistik", {}).get("anormal", 0)
                    },
                    "general_recommendations": []
                }
                
                # Önerileri ekle
                oneriler = parsed_response.get("oneriler", {})
                if isinstance(oneriler, dict):
                    for category, items in oneriler.items():
                        if isinstance(items, list):
                            formatted_response["general_recommendations"].extend(items)
                        elif isinstance(items, str):
                            formatted_response["general_recommendations"].append(items)
                
                # Eğer öneri yoksa default ekle
                if not formatted_response["general_recommendations"]:
                    formatted_response["general_recommendations"] = ["Test sonuçlarınızı hekiminizle değerlendirin"]
                
                return {
                    "content": json.dumps(formatted_response, ensure_ascii=False),
                    "models_used": [r["model"] for r in responses]
                }
                
        except Exception as e:
            print(f"Response formatting failed: {e}")
            # Formatting başarısız olursa GPT-4o fallback kullan
            return gpt4o_session_fallback(session_tests, session_date, laboratory)
        
    except Exception as e:
        print(f"Single session analyze failed: {e}")
        return single_session_fallback(session_tests, session_date, laboratory)

def parallel_multiple_lab_analyze(tests_data: List[Dict[str, Any]], session_count: int, available_supplements: List[Dict[str, Any]] = None, user_profile: Dict[str, Any] = None) -> Dict[str, Any]:
    """Analyze multiple lab tests for general summary - ÜRÜN KATALOĞU ENTEGRASYONU"""
    try:
        messages = build_multiple_lab_prompt(tests_data, session_count, available_supplements, user_profile)
        
        # Parallel analysis
        responses = []
        with ThreadPoolExecutor(max_workers=len(PARALLEL_MODELS)) as executor:
            future_to_model = {
                executor.submit(call_chat_model, model, messages, 0.3, 2000): model 
                for model in PARALLEL_MODELS
            }
            
            for future in as_completed(future_to_model):
                model = future_to_model[future]
                try:
                    result = future.result()
                    if result["content"].strip():
                        responses.append({
                            "model": model,
                            "response": result["content"]
                        })
                except Exception as e:
                    # Rate limiting hatası varsa biraz bekle
                    if "429" in str(e) or "Too Many Requests" in str(e):
                        time.sleep(2)
                    continue
        
        if not responses:
            print("No successful responses, using GPT-4o fallback")
            return gpt4o_multiple_lab_fallback(tests_data, session_count, available_supplements, user_profile)
        
        # Tek model kullanıldığı için synthesis'e gerek yok - direkt response'u döndür
        cleaned_response = _sanitize_links(responses[0]["response"])
        return {
            "content": cleaned_response,
            "model_used": responses[0]["model"],
            "models_used": [r["model"] for r in responses]
        }
        
    except Exception as e:
        print(f"Multiple lab analyze failed: {e}")
        return gpt4o_multiple_lab_fallback(tests_data, session_count, available_supplements, user_profile)

# Session synthesis prompt fonksiyonu kaldırıldı - tek model kullanıldığı için gerekli değil

# Lab synthesis prompt fonksiyonu kaldırıldı - tek model kullanıldığı için gerekli değil

def gpt4o_lab_fallback(test_data: Dict[str, Any], historical_results: List[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Fallback to GPT-4o for lab analysis when GPT-5 fails"""
    try:
        print("GPT-5 failed, trying GPT-4o fallback for lab analysis...")
        
        # Build prompt for GPT-4o
        messages = build_single_lab_prompt(test_data, historical_results)
        
        # Try GPT-4o
        result = call_chat_model("openai/gpt-4o:online", messages, 0.3, 1200)
        if result["content"].strip():
            result["content"] = _sanitize_links(result["content"])
            result["models_used"] = ["openai/gpt-4o:online (fallback)"]
            return result
        else:
            raise Exception("GPT-4o response invalid")
            
    except Exception as e:
        print(f"GPT-4o lab fallback also failed: {e}")
    return {
            "content": "Laboratuvar analizi şu anda mevcut değil. Lütfen daha sonra tekrar deneyin.",
            "models_used": ["fallback_error"]
        }

def gpt4o_session_fallback(session_tests: List[Dict[str, Any]], session_date: str, laboratory: str) -> Dict[str, Any]:
    """Fallback to GPT-4o for session analysis when GPT-5 fails"""
    try:
        print("GPT-5 failed, trying GPT-4o fallback for session analysis...")
        
        # Build prompt for GPT-4o
        messages = build_single_session_prompt(session_tests, session_date, laboratory)
        
        # Try GPT-4o
        result = call_chat_model("openai/gpt-4o:online", messages, 0.3, 1500)
        if result["content"].strip():
            result["content"] = _sanitize_links(result["content"])
            result["models_used"] = ["openai/gpt-4o:online (fallback)"]
            return result
        else:
            raise Exception("GPT-4o response invalid")
            
    except Exception as e:
        print(f"GPT-4o session fallback also failed: {e}")
        return {
            "content": "Seans analizi şu anda mevcut değil. Lütfen daha sonra tekrar deneyin.",
            "models_used": ["fallback_error"]
        }

def gpt4o_multiple_lab_fallback(tests_data: List[Dict[str, Any]], session_count: int, available_supplements: List[Dict[str, Any]] = None, user_profile: Dict[str, Any] = None) -> Dict[str, Any]:
    """Fallback to GPT-4o for multiple lab analysis when GPT-5 fails"""
    try:
        print("GPT-5 failed, trying GPT-4o fallback for multiple lab analysis...")
        
        # Build prompt for GPT-4o
        messages = build_multiple_lab_prompt(tests_data, session_count, available_supplements, user_profile)
        
        # Try GPT-4o
        result = call_chat_model("openai/gpt-4o:online", messages, 0.3, 2500)
        if result["content"].strip():
            result["content"] = _sanitize_links(result["content"])
            result["models_used"] = ["openai/gpt-4o:online (fallback)"]
            return result
        else:
            raise Exception("GPT-4o response invalid")
            
    except Exception as e:
        print(f"GPT-4o multiple lab fallback also failed: {e}")
        return {
            "content": "Kapsamlı laboratuvar analizi şu anda mevcut değil. Lütfen daha sonra tekrar deneyin.",
            "models_used": ["fallback_error"]
        }

def single_session_fallback(session_tests: List[Dict[str, Any]], session_date: str, laboratory: str) -> Dict[str, Any]:
    """Fallback for single session analysis"""
    return {
        "content": json.dumps({
            "session_info": {
                "laboratory": laboratory,
                "session_date": session_date,
                "total_tests": len(session_tests)
            },
            "general_assessment": {
                "clinical_meaning": "Test seansı analizi geçici olarak kullanılamıyor",
                "overall_health_status": "Genel sağlık durumu değerlendirilemedi"
            },
            "test_groups": {},
            "test_summary": {
                "total_tests": len(session_tests),
                "normal_count": 0,
                "attention_count": 0
            },
            "general_recommendations": ["Sistem tekrar çalışır duruma geldiğinde test edin"]
        }, ensure_ascii=False),
        "model_used": "fallback"
    }

def single_lab_fallback(test_data: Dict[str, Any], historical_results: List[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Fallback for single lab analysis with historical results"""
    fallback_response = {
        "analysis": {
            "summary": "Test analizi geçici olarak kullanılamıyor",
            "interpretation": "Lütfen daha sonra tekrar deneyin",
            "reference_comparison": "Referans karşılaştırması yapılamadı",
            "clinical_significance": "Klinik önem değerlendirilemedi",
            "category_insights": "Kategori analizi yapılamadı",
            "trend_analysis": "Trend analizi yapılamadı" if historical_results else "Geçmiş sonuç yok",
            "follow_up_suggestions": ["Sistem tekrar çalışır duruma geldiğinde test edin"],
            "data_quality": "Veri kalitesi değerlendirilemedi"
        }
    }
    
    return {
        "content": json.dumps(fallback_response, ensure_ascii=False),
        "model_used": "fallback"
    }

def multiple_lab_fallback(tests_data: List[Dict[str, Any]], session_count: int, available_supplements: List[Dict[str, Any]] = None, user_profile: Dict[str, Any] = None) -> Dict[str, Any]:
    """Fallback for multiple lab analysis"""
    return {
        "content": f'{{"general_assessment": {{"overall_summary": "Analiz sistemi geçici olarak kullanılamıyor", "patterns_identified": [], "areas_of_concern": [], "positive_aspects": [], "metabolic_status": "Değerlendirilemedi", "nutritional_status": "Değerlendirilemedi"}}, "overall_status": "geçici_bakım", "lifestyle_recommendations": {{"exercise": [], "nutrition": [], "sleep": [], "stress_management": []}}, "supplement_recommendations": [], "test_details": {{}}}}',
        "model_used": "fallback"
    }

def analyze_lab_progress(current_tests: List[Dict[str, Any]], previous_tests: List[Dict[str, Any]], user_profile: Dict[str, Any] = None) -> Dict[str, Any]:
    """Lab test progress analizi - Eski vs yeni test sonuçları"""
    
    if not previous_tests:
        return {
            "progress_analysis": "İlk test sonuçları - karşılaştırma yapılamaz",
            "improvements": [],
            "trends": "Trend analizi için daha fazla test gerekli"
        }
    
    # Test sonuçlarını karşılaştır
    progress_info = f"Önceki test sayısı: {len(previous_tests)}\n"
    progress_info += f"Güncel test sayısı: {len(current_tests)}\n\n"
    
    # Test bazlı karşılaştırma
    comparisons = []
    for current_test in current_tests:
        test_name = current_test.get('name', 'Bilinmeyen')
        current_value = current_test.get('value', 'Yok')
        
        # Önceki testlerde aynı test var mı?
        previous_test = None
        for prev_test in previous_tests:
            if prev_test.get('name') == test_name:
                previous_test = prev_test
                break
        
        if previous_test:
            prev_value = previous_test.get('value', 'Yok')
            comparison = {
                "test_name": test_name,
                "previous_value": prev_value,
                "current_value": current_value,
                "change": "değişim analizi yapılacak"
            }
            comparisons.append(comparison)
    
    progress_info += f"Karşılaştırılan test sayısı: {len(comparisons)}\n"
    
    return {
        "progress_analysis": progress_info,
        "test_comparisons": comparisons,
        "overall_trend": "Genel trend analizi yapılacak",
        "recommendations": "Progress bazlı öneriler yapılacak"
    }

def detect_language(text: str) -> str:
    """Smart language detection - Only obvious English words vs Turkish default"""
    if not text:
        return "turkish"
    
    # Türkçe karakter sayısı
    turkish_chars = sum(1 for char in text if char in 'çğıöşüÇĞIÖŞÜ')
    if turkish_chars > 0:
        return "turkish"
    
    # İngilizce kelime sayısı
    english_words = ['the', 'and', 'for', 'you', 'are', 'with', 'this', 'that', 'have', 'will', 'can', 'get', 'like', 'from', 'they', 'know', 'want', 'time', 'good', 'make', 'look', 'go', 'now', 'think', 'just', 'come', 'see', 'well', 'way', 'take', 'into', 'year', 'your', 'good', 'some', 'could', 'them', 'people', 'other', 'than', 'then', 'look', 'only', 'come', 'over', 'think', 'also', 'back', 'after', 'use', 'two', 'how', 'our', 'work', 'first', 'well', 'way', 'even', 'new', 'want', 'because', 'any', 'these', 'give', 'day', 'most', 'us']
    
    words = text.lower().split()
    english_word_count = sum(1 for word in words if word in english_words)
    
    if english_word_count > len(words) * 0.3:  # %30'dan fazla İngilizce kelime
        return "english"
    else:
        return "turkish"
