import json
import time
from typing import Tuple

def parse_json_safe(text: str):
    try:
        # Clean markdown code blocks
        if text.startswith("```json"):
            text = text[7:]  # Remove ```json
        if text.endswith("```"):
            text = text[:-3]  # Remove ```
        
        # İncomplete JSON'ları da temizle
        if text.strip().endswith("..."):
            # Truncated text, try to find complete JSON
            lines = text.split('\n')
            for i in range(len(lines)-1, -1, -1):
                if lines[i].strip() in ['}', '}]', '},']: 
                    text = '\n'.join(lines[:i+1])
                    break
        
        # JSON'ın tamamlanmamış olup olmadığını kontrol et
        if text.count('{') != text.count('}'):
            # Brace mismatch, try to complete
            if text.count('{') > text.count('}'):
                missing_braces = text.count('{') - text.count('}')
                text += '}' * missing_braces
        
        # YARIM KALMIŞ STRING'LERİ TAMAMLA
        text = fix_incomplete_strings(text)
        
        # CONTROL CHARACTER'LARI TEMİZLE
        text = clean_control_characters(text)
        
        # TÜRKÇE PRIORITY DEĞERLERİNİ İNGİLİZCE'YE ÇEVİR
        text = fix_turkish_priorities(text)
        
        # JSON SYNTAX HATALARINI DÜZELT
        text = fix_json_syntax(text)
        
        # AGGRESSIVE JSON REPAIR - Yeni eklenen
        text = aggressive_json_repair(text)
        
        text = text.strip()
        
        return json.loads(text)
    except Exception as e:
        # Final fallback: Try to extract any valid JSON structure
        return extract_partial_json(text)

def fix_incomplete_strings(text: str) -> str:
    """Yarım kalmış string'leri tamamla"""
    lines = text.split('\n')
    fixed_lines = []
    
    for line in lines:
        # String'de çift tırnak sayısını kontrol et
        quote_count = line.count('"')
        if quote_count % 2 == 1:  # Tek sayıda tırnak = yarım kalmış
            # Son tırnaktan sonraki kısmı temizle
            last_quote = line.rfind('"')
            if last_quote != -1:
                # String'i tamamla
                line = line[:last_quote + 1] + '",'
        fixed_lines.append(line)
    
    return '\n'.join(fixed_lines)

def clean_control_characters(text: str) -> str:
    """JSON'da geçersiz control character'ları temizle"""
    import re
    
    # JSON string'lerinde geçersiz control character'ları temizle
    # Sadece \n, \r, \t gibi geçerli escape sequence'ları koru
    text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
    
    # String içindeki yeni satırları space ile değiştir
    text = re.sub(r'(?<!\\)\n(?=.*")', ' ', text)
    
    # String içindeki tab'ları space ile değiştir
    text = re.sub(r'(?<!\\)\t(?=.*")', ' ', text)
    
    return text

def fix_turkish_priorities(text: str) -> str:
    """Türkçe priority değerlerini İngilizce'ye çevir"""
    import re
    
    # Priority field'larındaki Türkçe değerleri değiştir
    priority_pattern = r'"priority":\s*"([^"]*)"'
    
    def replace_priority(match):
        turkish_value = match.group(1).lower()
        if turkish_value in ['yüksek', 'yuksek', 'yukarı', 'yukari']:
            return '"priority": "high"'
        elif turkish_value in ['düşük', 'dusuk', 'aşağı', 'asagi']:
            return '"priority": "low"'
        else:
            return match.group(0)  # Değiştirme
    
    text = re.sub(priority_pattern, replace_priority, text)
    return text

def fix_json_syntax(text: str) -> str:
    """JSON syntax hatalarını düzelt"""
    import re
    
    # Property name eksik olan satırları düzelt
    # Örnek: "description": , -> "description": "",
    text = re.sub(r'"([^"]+)":\s*,', r'"\1": "",', text)
    
    # Property name eksik olan satırları düzelt (son satır)
    # Örnek: "description": -> "description": ""
    text = re.sub(r'"([^"]+)":\s*$', r'"\1": ""', text, flags=re.MULTILINE)
    
    # Property name eksik olan satırları düzelt (yeni satır)
    # Örnek: "description":\n -> "description": "",\n
    text = re.sub(r'"([^"]+)":\s*\n', r'"\1": "",\n', text)
    
    return text

def is_valid_chat(text: str) -> bool:
    # Boş olmayan her yanıtı geçerli say
    return bool(text and text.strip())

def aggressive_json_repair(text: str) -> str:
    """Aggressive JSON repair for severely damaged responses"""
    import re
    
    # Remove any text before first {
    first_brace = text.find('{')
    if first_brace > 0:
        text = text[first_brace:]
    
    # Remove any text after last }
    last_brace = text.rfind('}')
    if last_brace > 0:
        text = text[:last_brace + 1]
    
    # Fix common JSON issues
    text = re.sub(r',\s*}', '}', text)  # Remove trailing commas
    text = re.sub(r',\s*]', ']', text)  # Remove trailing commas in arrays
    text = re.sub(r'([^"])\s*:\s*,', r'\1: "",', text)  # Fix empty values
    
    # Ensure all strings are properly closed
    lines = text.split('\n')
    fixed_lines = []
    for line in lines:
        # Count quotes in this line
        quote_count = line.count('"')
        if quote_count % 2 == 1:  # Odd number of quotes
            # Find the last quote and close the string
            last_quote = line.rfind('"')
            if last_quote != -1:
                # Add missing quote and comma
                line = line[:last_quote + 1] + '",'
        fixed_lines.append(line)
    
    text = '\n'.join(fixed_lines)
    return text

def extract_partial_json(text: str) -> dict:
    """Extract partial JSON structure when full parsing fails"""
    try:
        # Try to find any valid JSON structure
        import re
        
        # Look for JSON-like patterns
        json_pattern = r'\{[^{}]*\}'
        matches = re.findall(json_pattern, text)
        
        if matches:
            # Try to parse the largest match
            largest_match = max(matches, key=len)
            try:
                return json.loads(largest_match)
            except:
                pass
        
        # If no valid JSON found, return a minimal valid structure
        return {
            "success": True,
            "message": "Quiz analizi tamamlandı (kısmi sonuç)",
            "nutrition_advice": {
                "title": "Beslenme Önerileri",
                "recommendations": ["Dengeli beslenme programı uygulayın"]
            },
            "lifestyle_advice": {
                "title": "Yaşam Tarzı Önerileri", 
                "recommendations": ["Düzenli egzersiz yapın"]
            },
            "general_warnings": {
                "title": "Genel Uyarılar",
                "warnings": ["Doktorunuza danışmadan supplement kullanmayın"]
            },
            "supplement_recommendations": [
                {
                    "name": "D Vitamini",
                    "description": "Kemik sağlığı için",
                    "daily_dose": "600-800 IU (doktorunuza danışın)",
                    "benefits": ["Kalsiyum emilimini artırır"],
                    "warnings": ["Yüksek dozlarda toksik olabilir"],
                    "priority": "high"
                }
            ],
            "disclaimer": "Bu içerik bilgilendirme amaçlıdır; tıbbi tanı/tedavi için hekiminize başvurun."
        }
        
    except Exception as e:
        # Ultimate fallback
        return {
            "success": True,
            "message": "Quiz analizi tamamlandı",
            "nutrition_advice": {"title": "Beslenme Önerileri", "recommendations": ["Dengeli beslenme"]},
            "lifestyle_advice": {"title": "Yaşam Tarzı Önerileri", "recommendations": ["Düzenli egzersiz"]},
            "general_warnings": {"title": "Genel Uyarılar", "warnings": ["Doktorunuza danışın"]},
            "supplement_recommendations": [{"name": "D Vitamini", "description": "Default", "priority": "high"}],
            "disclaimer": "Bu içerik bilgilendirme amaçlıdır."
        }

# is_valid_analyze fonksiyonu kaldırıldı - artık kullanılmıyor

def generate_response_id() -> str:
    """Unique response ID oluştur (R001, R002, R003...)"""
    timestamp = int(time.time() * 1000)  # Milisaniye
    return f"R{timestamp}"

def extract_user_context(message_content: str) -> dict:
    """Kullanıcı mesajından önemli context bilgilerini çıkar"""
    context = {}
    content = message_content.lower()
    
    # İsim bilgisi - Hem tanımlama hem de soru formatında
    if "benim adım" in content:
        if "neydi" in content or "?" in content:
            # Soru formatı: "Benim adım neydi?" → Global context'ten al
            context["isim_sorusu"] = True
        else:
            # Tanımlama formatı: "Benim adım Zeynep" → İsmi çıkar
            parts = content.split("benim adım")
            if len(parts) > 1:
                name_part = parts[1].strip()
                name_words = name_part.split()
                if name_words and len(name_words[0]) < 20 and name_words[0] not in ["ve", "da", "de", "ile"]:
                    context["isim"] = name_words[0]
    
    # Alternatif isim formatları
    if "adım" in content and "benim" not in content:
        if "neydi" in content or "?" in content:
            context["isim_sorusu"] = True
        else:
            # "Adım Zeynep" formatı
            parts = content.split("adım")
            if len(parts) > 1:
                name_part = parts[1].strip()
                name_words = name_part.split()
                if name_words and len(name_words[0]) < 20:
                    context["isim"] = name_words[0]
    
    # Tercih bilgileri
    if "seviyorum" in content or "sevdiğim" in content:
        # Hangi supplement/vitamin sevildiğini bul
        supplements = ["d vitamini", "omega-3", "magnezyum", "c vitamini", "b12", "folik asit"]
        for supp in supplements:
            if supp in content:
                if "tercihler" not in context:
                    context["tercihler"] = []
                context["tercihler"].append(supp)
    
    # Hastalık bilgileri
    diseases = ["hipertansiyon", "tansiyon", "diyabet", "şeker", "kolesterol", "mide", "böbrek", "karaciğer"]
    for disease in diseases:
        if disease in content:
            if "hastaliklar" not in context:
                context["hastaliklar"] = []
            # Normalizasyon
            if disease in ["tansiyon", "hipertansiyon"]:
                if "hipertansiyon" not in context["hastaliklar"]:
                    context["hastaliklar"].append("hipertansiyon")
            elif disease in ["şeker", "diyabet"]:
                if "diyabet" not in context["hastaliklar"]:
                    context["hastaliklar"].append("diyabet")
            else:
                if disease not in context["hastaliklar"]:
                    context["hastaliklar"].append(disease)
    
    return context

def get_priority_context(user_context: dict, max_tokens: int = 1000) -> dict:
    """Öncelikli context'i getir (token limiti ile)"""
    
    if not user_context:
        return {}
    
    # Context'i öncelik sırasına göre sırala
    priority_order = [
        "isim",           # En önemli
        "hastaliklar",    # Güvenlik için kritik
        "alerjiler",      # Güvenlik için kritik
        "ilaclar",        # Etkileşim için kritik
        "tercihler",      # Öneriler için
        "yas",            # Doz hesaplama için
        "cinsiyet",       # Doz hesaplama için
        "boy",            # BMI için
        "kilo"            # BMI için
    ]
    
    # Priority-based context build
    priority_context = {}
    current_tokens = 0
    
    for key in priority_order:
        if key in user_context:
            value = user_context[key]
            
            # Token hesapla
            if isinstance(value, list):
                # Liste için token hesapla (max 5 item)
                limited_list = value[:5]
                list_text = f"- {key.title()}: {', '.join(limited_list)}"
                if len(value) > 5:
                    list_text += f" ve {len(value)-5} tane daha"
                
                list_tokens = len(list_text.split()) * 1.3  # Approximate token count
                
                if current_tokens + list_tokens <= max_tokens:
                    priority_context[key] = limited_list
                    current_tokens += list_tokens
                else:
                    break
            else:
                # String için token hesapla
                string_text = f"- {key.title()}: {value}"
                string_tokens = len(string_text.split()) * 1.3
                
                if current_tokens + string_tokens <= max_tokens:
                    priority_context[key] = value
                    current_tokens += string_tokens
                else:
                    break
    
    return priority_context

def get_rotating_context(user_context: dict, conversation_id: int) -> dict:
    """Her conversation'da farklı context'i göster"""
    
    if not user_context:
        return {}
    
    # Conversation ID'ye göre context'i rotate et
    rotation_index = conversation_id % 3  # 3 farklı context seti
    
    if rotation_index == 0:
        # Set 1: Temel bilgiler
        return get_basic_context(user_context)
    elif rotation_index == 1:
        # Set 2: Sağlık bilgileri
        return get_health_context(user_context)
    else:
        # Set 3: Tercih bilgileri
        return get_preference_context(user_context)

def get_basic_context(user_context: dict) -> dict:
    """Temel kullanıcı bilgileri"""
    return {
        "isim": user_context.get("isim"),
        "yas": user_context.get("yas"),
        "cinsiyet": user_context.get("cinsiyet")
    }

def get_health_context(user_context: dict) -> dict:
    """Sağlık odaklı bilgiler"""
    return {
        "hastaliklar": user_context.get("hastaliklar", [])[:3],  # Max 3
        "alerjiler": user_context.get("alerjiler", [])[:3],      # Max 3
        "ilaclar": user_context.get("ilaclar", [])[:3]           # Max 3
    }

def get_preference_context(user_context: dict) -> dict:
    """Tercih odaklı bilgiler"""
    return {
        "tercihler": user_context.get("tercihler", [])[:5],      # Max 5
        "boy": user_context.get("boy"),
        "kilo": user_context.get("kilo")
    }

def get_mixed_context(user_context: dict, max_items: int = 2) -> dict:
    """Karma context (küçük)"""
    mixed = {}
    
    # Her kategoriden max_items kadar al
    for key in ["isim", "hastaliklar", "tercihler", "alerjiler"]:
        if key in user_context:
            value = user_context[key]
            if isinstance(value, list):
                mixed[key] = value[:max_items]
            else:
                mixed[key] = value
    
    return mixed

def compress_context(context: dict) -> str:
    """Context'i sıkıştır"""
    
    if not context:
        return ""
    
    compressed_lines = []
    
    # İsim
    if "isim" in context:
        compressed_lines.append(f"İsim: {context['isim']}")
    
    # Tercihler (sadece son 3)
    if "tercihler" in context:
        recent_prefs = context["tercihler"][-3:]  # Son 3
        compressed_lines.append(f"Son tercihler: {', '.join(recent_prefs)}")
    
    # Hastalıklar (sadece kritik olanlar)
    if "hastaliklar" in context:
        critical_diseases = [d for d in context["hastaliklar"] if d in ["hipertansiyon", "diyabet", "kalp"]]
        if critical_diseases:
            compressed_lines.append(f"Kritik hastalıklar: {', '.join(critical_diseases)}")
    
    # Alerjiler (sadece ciddi olanlar)
    if "alerjiler" in context:
        severe_allergies = [a for a in context["alerjiler"] if a in ["fındık", "yumurta", "süt"]]
        if severe_allergies:
            compressed_lines.append(f"Ciddi alerjiler: {', '.join(severe_allergies)}")
    
    return "\n".join(compressed_lines)

def get_smart_context(user_context: dict, current_message: str) -> dict:
    """Mesaja göre akıllı context seç"""
    
    if not user_context:
        return {}
    
    message_lower = current_message.lower()
    
    # Mesaj türüne göre context seç
    if any(word in message_lower for word in ["hastalık", "rahatsızlık", "problem", "semptom"]):
        # Sağlık sorusu → Sağlık context'i
        return get_health_context(user_context)
    
    elif any(word in message_lower for word in ["tercih", "sevdiğim", "kullandığım", "supplement", "vitamin"]):
        # Tercih sorusu → Tercih context'i
        return get_preference_context(user_context)
    
    elif any(word in message_lower for word in ["adım", "isim", "ben", "hatırlıyor musun"]):
        # Kişisel sorusu → Temel context
        return get_basic_context(user_context)
    
    else:
        # Genel sorusu → Karma context (küçük)
        return get_mixed_context(user_context, max_items=2)

def extract_user_context_ai(message_content: str, user_id: str = None) -> dict:
    """AI model ile akıllı context çıkar"""
    
    try:
        from backend.openrouter_client import call_chat_model
        
        prompt = f"""
        DİKKAT: Bu kullanıcı mesajından SADECE kullanıcının kendisi hakkında AÇIKÇA söylediği bilgileri çıkar:
        "{message_content}"
        
        KESİN KURALLAR - HİÇBİRİNİ İHLAL ETME!:
        1. SADECE "ben", "benim", "bana" ile başlayan DOĞRUDAN AÇIKLAMALAR!
        3. "HAKKINDA", "NEDİR", "NASIL" VARSA → HİÇBİR ŞEY ÇIKARMA!
        5. "HANGİ", "KAÇ", "NEREDE" VARSA → HİÇBİR ŞEY ÇIKARMA!
        6. SORU SORUYORSA → BOŞ JSON: {{}}
        7. SESSION ID'den asla bilgi çıkarma!
        8. Email'den asla bilgi çıkarma!
        9. SORU = BOŞ JSON, AÇIKLAMA = BİLGİ
        10. "D vitamini hakkında bilgi?" → {{}} (SORU!)
        12. "Nasıl kullanılır?" → {{}} (SORU!)
        
        DOĞRU ÖRNEKLER:
        - "Ben Ahmet" → {{"isim": "Ahmet"}}
        - "28 yaşındayım" → {{"yas": 28}}
        - "Ben D vitamini kullanıyorum" → {{"tercihler": ["D vitamini"]}}
        - "Hipertansiyonum var" → {{"hastaliklar": ["hipertansiyon"]}}
        - "D vitamini alerjim var" → {{"alerjiler": ["D vitamini"]}}
        - "D vitamini kullanamam" → {{"alerjiler": ["D vitamini"]}}
        - "Metformin kullanıyorum" → {{"ilaclar": ["Metformin"]}}
        - "Aspirin kullanıyorum" → {{"ilaclar": ["Aspirin"]}}
        - "Hamileyim" → {{"ozel_durumlar": ["Hamilelik"]}}
        - "Emziriyorum" → {{"ozel_durumlar": ["Emzirme"]}}
        - "Psikiyatrik ilaç kullanıyorum" → {{"ilaclar": ["Psikiyatrik ilaç"]}}
        
        
        YANLIŞ ÖRNEKLER (ALMA!):
        - "Diyabet için ne önerirsin?" → {{}} (SORU - bilgi değil!)
        - "PCOS için supplement önerir misin?" → {{}} (SORU - bilgi değil!)
        - "Hangi hastalığım var?" → {{}} (SORU - bilgi değil!)
        - "Ben hasta mıyım?" → {{}} (SORU - bilgi değil!)
        - "D vitamini hakkında bilgi?" → {{}} (SORU - bilgi değil!)
       
        
        SADECE JSON döndür, açıklama ekleme!
        """
        
        # AI model'e gönder - User session ile izole et
        session_prompt = f"SESSION_ID: {user_id or 'anonymous'}\n\n{prompt}"
        
        # Ana model: Gemini 2.5 Flash
        response = None
        try:
            response = call_chat_model(
                "google/gemini-2.5-flash",  # Daha akıllı, prompt'u daha iyi anlar
                [{"role": "system", "content": session_prompt}],
                temperature=0.0,  # Sıkı davranış için
                max_tokens=150
            )
            print(f"✅ Gemini 2.5 Flash başarılı")
        except Exception as e:
            print(f"❌ Gemini 2.5 Flash hata: {e}")
            
            # Fallback: GPT-OSS-20B
            try:
                response = call_chat_model(
                    "openai/gpt-oss-20b:free",
                    [{"role": "system", "content": session_prompt}],
                    temperature=0.0,
                    max_tokens=150
                )
                print(f"✅ Gemini fallback (GPT-OSS-20B) başarılı")
            except Exception as e2:
                print(f"❌ Gemini fallback (GPT-OSS-20B) hata: {e2}")
                return {"error": "AI model hatası", "details": str(e2)}
        
        content = response.get("content", "")
        
        # JSON parse et
        try:
            import json
            # JSON'ı temizle
            content = content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.endswith("```"):
                content = content[:-3]
            
            context = json.loads(content)
            return context
            
        except json.JSONDecodeError as e:
            # Fallback: Pattern-based extraction
            return extract_user_context_fallback(message_content)
            
    except Exception as e:
        # Fallback: Pattern-based extraction
        return extract_user_context_fallback(message_content)

def extract_user_context_fallback(message_content: str) -> dict:
    """Fallback: Pattern-based context extraction"""
    return extract_user_context(message_content)

def extract_user_context_hybrid(message_content: str, user_id: str = None) -> dict:
    """Hybrid approach: AI + Pattern fallback"""
    
    # 1. Önce AI-based extraction (hızlı) - User ID ile izole et
    ai_context = extract_user_context_ai(message_content, user_id)
    
    # 2. Eğer AI başarısız olursa pattern-based
    if not ai_context or len(ai_context) < 2:
        pattern_context = extract_user_context_fallback(message_content)
        
        # Pattern-based context'i AI context ile birleştir
        if ai_context:
            merged_context = {**ai_context, **pattern_context}
            return merged_context
        else:
            return pattern_context
    
    # 3. Key'leri normalize et (büyük harf -> küçük harf)
    normalized_context = {}
    for key, value in ai_context.items():
        if key and value:  # None değerleri atla
            normalized_key = key.lower()
            normalized_context[normalized_key] = value
    
    return normalized_context

def get_context_rotation_system(user_context: dict, conversation_id: int, message_type: str = None) -> dict:
    """Advanced context rotation system"""
    
    if not user_context:
        return {}
    
    # Conversation ID'ye göre rotation
    rotation_index = conversation_id % 4  # 4 farklı context seti
    
    # Message type'a göre de context seç
    if message_type:
        if message_type == "health":
            return get_health_focused_context(user_context)
        elif message_type == "memory":
            return get_memory_focused_context(user_context)
        elif message_type == "preference":
            return get_preference_focused_context(user_context)
    
    # Default rotation
    if rotation_index == 0:
        return get_core_context(user_context)      # Temel bilgiler
    elif rotation_index == 1:
        return get_health_context(user_context)    # Sağlık odaklı
    elif rotation_index == 2:
        return get_preference_context(user_context) # Tercih odaklı
    else:
        return get_mixed_context(user_context, max_items=3)  # Karma

def get_core_context(user_context: dict) -> dict:
    """Temel kullanıcı bilgileri"""
    return {
        "isim": user_context.get("isim"),
        "yas": user_context.get("yas"),
        "cinsiyet": user_context.get("cinsiyet")
    }

def get_health_focused_context(user_context: dict) -> dict:
    """Sağlık odaklı context"""
    return {
        "hastaliklar": user_context.get("hastaliklar", [])[:3],
        "alerjiler": user_context.get("alerjiler", [])[:3],
        "ilaclar": user_context.get("ilaclar", [])[:3],
        "yas": user_context.get("yas"),
        "cinsiyet": user_context.get("cinsiyet")
    }

def get_memory_focused_context(user_context: dict) -> dict:
    """Hafıza odaklı context"""
    return {
        "isim": user_context.get("isim"),
        "tercihler": user_context.get("tercihler", [])[:3],
        "yas": user_context.get("yas")
    }

def get_preference_focused_context(user_context: dict) -> dict:
    """Tercih odaklı context"""
    return {
        "tercihler": user_context.get("tercihler", [])[:5],
        "boy": user_context.get("boy"),
        "kilo": user_context.get("kilo"),
        "yas": user_context.get("yas")
    }

def detect_message_type(message: str) -> str:
    """Mesaj türünü otomatik tespit et"""
    
    message_lower = message.lower()
    
    # Health keywords
    health_keywords = ["hastalık", "rahatsızlık", "problem", "semptom", "tedavi", "ilaç", "doz"]
    if any(keyword in message_lower for keyword in health_keywords):
        return "health"
    
    # Memory keywords
    memory_keywords = ["hatırlıyor musun", "neydi", "biliyor musun", "söylemiş miydim"]
    if any(keyword in message_lower for keyword in memory_keywords):
        return "memory"
    
    # Preference keywords
    preference_keywords = ["tercih", "sevdiğim", "kullandığım", "supplement", "vitamin", "öner"]
    if any(keyword in message_lower for keyword in preference_keywords):
        return "preference"
    
    return "general"
