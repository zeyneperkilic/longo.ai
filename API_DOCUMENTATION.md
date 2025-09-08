# Longopass AI Gateway - API Dokümantasyonu

## 📋 Genel Bilgiler

**Base URL:** `https://longo-ai.onrender.com`  
**Authentication:** Basic Auth (Header'da username/password)  
**Content-Type:** `application/json`  
**Response Format:** JSON

### 🔐 Authentication Headers
```http
username: longopass
password: 123456
```

### 👤 User Management Headers
```http
x-user-id: unique_user_id        # Kullanıcı ID'si
x-user-level: 0|1|2|3           # Kullanıcı seviyesi (0=free, 1=free, 2=premium, 3=premium_plus)
```

---

## 🧪 Quiz Endpoint

### **POST** `/ai/quiz`

Kişiselleştirilmiş supplement önerileri ve beslenme tavsiyeleri alır.

#### Request Body
```json
{
  "quiz_answers": {
    "age": 30,
    "gender": "male",
    "health_goals": ["energy"]
  }
}
```

#### Response
```json
{
  "success": true,
  "message": "Quiz analizi tamamlandı",
  "nutrition_advice": {
    "title": "Beslenme Önerileri",
    "recommendations": [
      "Günlük protein alımını artır, özellikle kahvaltıda kaliteli protein tüket.",
      "Enerji seviyeni korumak için rafine karbonhidratları sınırlayıp kompleks karbonhidratlara (yulaf, tam tahıl, bakliyat) ağırlık ver.",
      "Yeterli su tüket ve dehidrasyonu önlemek için gün içinde düzenli sıvı al."
    ]
  },
  "lifestyle_advice": {
    "title": "Yaşam Tarzı Önerileri",
    "recommendations": [
      "Düzenli uyku rutini oluştur (günde 7-8 saat uyku).",
      "Gün içine kısa egzersiz molaları ekleyerek enerjini yükselt.",
      "Stres yönetimi için nefes egzersizi veya meditasyonu günlük rutine kat."
    ]
  },
  "general_warnings": {
    "title": "Genel Uyarılar",
    "warnings": [
      "Takviyeleri doktor kontrolü olmadan yüksek dozlarda kullanma.",
      "Sürekli yorgunluk ve enerji düşüklüğü yaşıyorsan altta yatan tıbbi bir durum olabilir, hekime danış.",
      "Kafeinli ürünleri aşırıya kaçmadan kullan, gece uykunu bozabilir."
    ]
  },
  "supplement_recommendations": [
    {
      "name": "D Vitamini (ID: 164)",
      "description": "Kemik sağlığı, bağışıklık desteği ve enerji regülasyonu için temel.",
      "daily_dose": "1000-2000 IU",
      "benefits": ["Bağışıklık sistemini destekler", "Enerji seviyesini iyileştirir", "Kemik sağlığını korur"],
      "warnings": ["Yüksek dozlarda toksisite riski olabilir."],
      "priority": "high",
      "type": "default"
    },
    {
      "name": "Omega-3 Yağ Asitleri (Balık Yağı) (ID: 179)",
      "description": "Beyin fonksiyonları ve enerji metabolizması için gerekli.",
      "daily_dose": "1000 mg",
      "benefits": ["Beyin sağlığını destekler", "Kalp sağlığını korur", "Enflamasyonu azaltır"],
      "warnings": ["Kan sulandırıcı ilaçlarla etkileşebilir."],
      "priority": "high",
      "type": "default"
    },
    {
      "name": "Magnezyum (ID: 176)",
      "description": "Kas, sinir sistemi ve enerji üretimi için hayati.",
      "daily_dose": "200-400 mg",
      "benefits": ["Kas fonksiyonlarını destekler", "Yorgunluğu azaltır", "Uyku kalitesini artırır"],
      "warnings": ["Yüksek dozda ishal yapabilir."],
      "priority": "high",
      "type": "default"
    },
    {
      "name": "B12 Vitamini (ID: 154)",
      "description": "Enerji metabolizması ve kırmızı kan hücresi oluşumu için kritik.",
      "daily_dose": "500-1000 mcg",
      "benefits": ["Enerji artışı sağlar", "Sinir sistemini korur", "Kan hücrelerini destekler"],
      "warnings": ["B12 eksikliği uzun vadede ciddi sorunlara yol açabilir."],
      "priority": "high",
      "type": "default"
    },
    {
      "name": "Koenzim Q10 (ID: 221)",
      "description": "Enerji üretiminde görev alır, hücresel enerji seviyesini destekler.",
      "daily_dose": "100-200 mg",
      "benefits": ["Enerji artışı sağlar", "Kalp sağlığını destekler", "Mitokondri fonksiyonlarını güçlendirir"],
      "warnings": ["Kan basıncı ilaçları ile etkileşebilir."],
      "priority": "medium",
      "type": "personalized"
    },
    {
      "name": "Ginseng (ID: 214)",
      "description": "Fiziksel ve zihinsel enerjiyi artırır, yorgunlukla mücadele eder.",
      "daily_dose": "200-400 mg",
      "benefits": ["Enerjiyi artırır", "Odaklanmayı destekler", "Yorgunluk hissini azaltır"],
      "warnings": ["Fazla kullanımda uykusuzluk yapabilir."],
      "priority": "medium",
      "type": "personalized"
    },
    {
      "name": "Enerji ve Odaklanma Formülü (ID: 263)",
      "description": "Enerjiyi ve mental performansı artırmak için özel kombine formül.",
      "daily_dose": "1 kapsül",
      "benefits": ["Dayanıklılığı artırır", "Odaklanmayı güçlendirir", "Enerji metabolizmasını destekler"],
      "warnings": ["Kafein içerebilir, gece kullanımı uyku sorununa yol açabilir."],
      "priority": "medium",
      "type": "personalized"
    }
  ],
  "disclaimer": "Bu içerik bilgilendirme amaçlıdır; tıbbi tanı/tedavi için hekiminize başvurun."
}
```

#### Strateji
- **4 DEFAULT + 3 PERSONALIZED = 7 supplement**
- **DEFAULT**: D Vitamini, Omega-3, Magnezyum, B12
- **PERSONALIZED**: Quiz cevaplarına göre (energy hedefi için Koenzim Q10, Ginseng, Enerji Formülü)

---

## 🧬 Lab Summary Endpoint

### **POST** `/ai/lab/summary`

Laboratuvar test sonuçlarının genel analizi ve supplement önerileri.

#### Request Body
```json
{
  "tests": [
    {
      "name": "D Vitamini",
      "value": "15",
      "unit": "ng/mL",
      "reference_range": "30-100"
    }
  ]
}
```

#### Response
```json
{
  "title": "Tüm Testlerin Genel Yorumu",
  "general_assessment": {
    "overall_summary": "Mevcut laboratuvar sonucunda yalnızca D vitamini testi yapılmış. Sonuç 15 ng/mL çıkmış, bu da referans aralığına (30-100 ng/mL) göre belirgin şekilde düşük. Bu durum D vitamini eksikliğini gösteriyor.",
    "patterns_identified": "Tek belirgin patern D vitamini eksikliği.",
    "areas_of_concern": "D vitamini düşüklüğü kemik sağlığı, bağışıklık sistemi, kas fonksiyonları ve ruh hali üzerinde olumsuz etkiler yapabilir.",
    "positive_aspects": "Test yapılarak farkındalık oluşmuş. Erken dönemde tedbir alınabilir.",
    "metabolic_status": "Eksik D vitamini metabolizmayı, enerji seviyelerini ve bağışıklığı olumsuz etkileyebilir.",
    "nutritional_status": "Güneşten yeterince faydalanmama veya D vitamini içeren besinlerin az alımı söz konusu olabilir."
  },
  "test_details": {
    "D Vitamini": {
      "interpretation": "Sonuç 15 ng/mL ile düşük. Bu düzey klinik olarak D vitamini eksikliğiyle uyumlu.",
      "significance": "D vitamini kalsiyum emilimi, kemik sağlığı, kas ve bağışıklık fonksiyonları için kritik. Eksiklik kronik yorgunluk, kemik ağrıları, sık enfeksiyonlar yapabilir.",
      "suggestions": "D3 vitamini takviyesi başlanmalı, magnezyum ve K2 vitamini ile desteklenmeli. 8-12 hafta sonra tekrar test ile düzey kontrol edilmeli."
    }
  },
  "supplement_recommendations": [
    {
      "name": "D3 Vitamini (ID: 165)",
      "description": "D vitamini seviyen belirgin şekilde düşük (15 ng/mL). Kemik sağlığı, bağışıklık sistemi ve enerji dengesi için kritik.",
      "daily_dose": "2000-4000 IU/gün (doktor kontrolüyle kademeli artırılabilir)",
      "benefits": ["Bağışıklık sistemini güçlendirir", "Kemik ve kas sağlığını destekler", "Ruh halini dengeler"],
      "warnings": ["Aşırı doz hiperkalsemiye neden olabilir, düzenli kan tahlili ile takip edilmeli"],
      "priority": "high",
      "type": "lab_analysis"
    },
    {
      "name": "Omega-3 Yağ Asitleri (Balık Yağı) (ID: 179)",
      "description": "Omega-3, D vitamini ile sinerjik çalışır. Anti-enflamatuar etkisi sayesinde bağışıklık ve kalp sağlığına destek olur.",
      "daily_dose": "1000 mg/gün (EPA + DHA toplamı)",
      "benefits": ["Kalp-damar sağlığını korur", "Beyin ve ruh halini destekler", "Enflamasyonu azaltır"],
      "warnings": ["Kan sulandırıcı ilaç kullananlar doktora danışmalı"],
      "priority": "medium",
      "type": "lab_analysis"
    },
    {
      "name": "Magnezyum (ID: 176)",
      "description": "D vitamini, magnezyum olmadan etkili çalışamaz. Kas gevşemesi, uyku kalitesi ve sinir sistemi sağlığı için destek.",
      "daily_dose": "200-400 mg/gün",
      "benefits": ["Uyku kalitesini artırır", "Kas kramplarını önler", "Sinir sistemini destekler"],
      "warnings": ["Böbrek yetmezliği olanlarda dikkat edilmeli"],
      "priority": "medium",
      "type": "lab_analysis"
    },
    {
      "name": "K2 Vitamini (ID: 171)",
      "description": "D vitamini ile birlikte alındığında kalsiyumun doğru yerlere (kemik/diş) yönlendirilmesine yardımcı olur.",
      "daily_dose": "90-120 mcg/gün",
      "benefits": ["Kemik mineralizasyonunu destekler", "D vitamininin etkinliğini artırır"],
      "warnings": ["Kan sulandırıcı ilaç kullananlarda dikkat edilmeli"],
      "priority": "high",
      "type": "lab_analysis"
    }
  ],
  "disclaimer": "Bu içerik bilgilendirme amaçlıdır; tıbbi tanı/tedavi için hekiminize başvurun.",
  "overall_status": "dikkat_edilmeli",
  "lifestyle_recommendations": {
    "exercise": [
      "Haftada en az 3 gün, 30-45 dakika tempolu yürüyüş veya hafif koşu.",
      "Ağırlık veya direnç egzersizleriyle kemik ve kas sağlığını güçlendirme."
    ],
    "nutrition": [
      "Somon, sardalya, uskumru gibi yağlı balıklara haftada 2 kez yer ver.",
      "Yumurta sarısı ve D vitamini ile zenginleştirilmiş süt ürünleri tüket.",
      "Güneş ışığından (özellikle kollar ve bacaklar açık şekilde) günde 15-20 dakika faydalan."
    ],
    "sleep": [
      "Günde 7-8 saat kaliteli uyku hedefle.",
      "Uyumadan önce ekran kullanımını azalt."
    ],
    "stress_management": [
      "Günlük nefes egzersizleri veya 10 dakikalık meditasyon yap.",
      "Stresli günlerde kısa yürüyüşler yaparak zihni rahatlat."
    ]
  },
  "test_count": 1
}
```

#### Strateji
- **4 DEFAULT + 1 PERSONALIZED = 5 supplement**
- **DEFAULT**: D3 Vitamini, Omega-3, Magnezyum, B12
- **PERSONALIZED**: Lab sonuçlarına göre (D vitamini düşükse K2 eklenir)
- **Detaylı lab analizi** ve genel değerlendirme
- **Yaşam tarzı önerileri** dahil

---

## 🔬 Lab Session Endpoint

### **POST** `/ai/lab/session`

Tek bir laboratuvar seansının analizi (supplement önerisi YOK).

#### Request Body
```json
{
  "tests": [
    {
      "name": "D Vitamini",
      "value": "15",
      "unit": "ng/mL",
      "reference_range": "30-100"
    }
  ]
}
```

#### Response
```json
{
  "title": "Test Seansı Analizi",
  "session_info": {
    "laboratory": "Laboratuvar",
    "session_date": "2024-01-15",
    "total_tests": 1
  },
  "general_assessment": {
    "clinical_meaning": "Bu testte sadece D Vitamini düzeyin ölçülmüş ve düşük bulunmuş. D Vitamini, kemik sağlığı, bağışıklık fonksiyonları, kas gücü ve genel metabolizma için kritik bir vitamindir.",
    "overall_health_status": "D Vitamini düşüklüğü mevcut. Genel sağlık açısından destekleyici önlemler alınmalı ve doktor kontrolü önerilir."
  },
  "test_groups": {
    "Vitaminler": [
      {
        "test_adi": "D Vitamini",
        "sonuc": "15 ng/mL",
        "referans_araligi": "30-100 ng/mL",
        "durum": "Anormal"
      }
    ]
  },
  "test_summary": {
    "total_tests": 1,
    "normal_count": 0,
    "attention_count": 1
  },
  "general_recommendations": [
    "Güneş ışığından daha fazla faydalanmaya çalış (özellikle sabah saatlerinde kısa süreli güneşlenme).",
    "D Vitamini açısından zengin gıdaları (yağlı balık, yumurta, süt ürünleri gibi) düzenli tüketmeye dikkat et.",
    "3-6 ay içerisinde D Vitamini düzeyi tekrar ölçülmeli.",
    "Kalsiyum, Fosfor ve Parathormon testleri gerekiyorsa destekleyici olarak kontrol edilebilir.",
    "D Vitamini değerlerinin düşüklüğü konusunda hekimle görüşüp sana özel bir tedavi veya yaşam tarzı planı belirlenmesi faydalı olur."
  ],
  "disclaimer": "Bu içerik bilgilendirme amaçlıdır; tıbbi tanı/tedavi için hekiminize başvurun."
}
```

#### Özellik
- **Sadece analiz, supplement önerisi YOK**
- **Test grupları** ve kategoriler
- **Genel öneriler** dahil

---

## 🧪 Lab Single Endpoint

### **POST** `/ai/lab/single`

Tek bir test sonucunun detaylı analizi (supplement önerisi YOK).

#### Request Body
```json
{
  "test": {
    "name": "D Vitamini",
    "value": "15",
    "unit": "ng/mL",
    "reference_range": "30-100"
  }
}
```

#### Response
```json
{
  "analysis": {
    "summary": "Düşük",
    "interpretation": "D vitamini düzeyi 15 ng/mL, referans aralığı olan 30-100 ng/mL'nin oldukça altında. Bu durum D vitamini yetersizliği ile uyumlu.",
    "reference_comparison": "Sonuç: 15 ng/mL | Referans: 30-100 ng/mL → Normal aralığın altında.",
    "clinical_significance": "D vitamini; kemik sağlığı, kalsiyum metabolizması ve bağışıklık sistemi için kritik öneme sahiptir. Bu düzeyde (15 ng/mL) özellikle kemik mineral yoğunluğunda azalma, kas güçsüzlüğü, kırık riskinde artış ve bağışıklık fonksiyonlarında zayıflama görülebilir.",
    "category_insights": "Bu test endokrinoloji ve metabolizma alanında değerlendirilir. Özellikle kemik sağlığı (osteoporoz riski), kalsiyum dengesi ve genel bağışıklık fonksiyonları üzerine önemli ipuçları verir.",
    "trend_analysis": "Geçmiş sonuç paylaşılmadığı için trend analizi yapılamıyor. Tek noktada düşük değer mevcut.",
    "follow_up_suggestions": "Sonucun düşük çıkması nedeniyle hekim ile görüşüp D vitamini eksikliğine yönelik ayrıntılı değerlendirme yapılması uygun olur. Ayrıca kalsiyum ve parathormon düzeylerinin de kontrol edilmesi faydalı olabilir.",
    "data_quality": "Tek bir ölçüm sonucu mevcut. Ölçümün hangi laboratuvarda, hangi yöntemle yapıldığı belirtilmemiş. Geçmiş değerler olmadığından trend analizi sınırlı."
  },
  "disclaimer": "Bu içerik bilgilendirme amaçlıdır; tıbbi tanı/tedavi için hekiminize başvurun."
}
```

#### Özellik
- **Sadece analiz, supplement önerisi YOK**
- **Detaylı yorum** ve klinik anlam
- **Kategori analizi** ve takip önerileri

---

## 💬 Chat Endpoint

### **POST** `/ai/chat/start`

Chat oturumu başlatır.

#### Request Body
```json
{}
```

#### Response
```json
{
  "success": true,
  "message": "Chat oturumu başlatıldı",
  "session_id": "unique_session_id"
}
```

### **POST** `/ai/chat`

Chat mesajı gönderir.

#### Request Body
```json
{
  "message": "Merhaba, nasılsın?",
  "session_id": "unique_session_id"
}
```

#### Response
```json
{
  "success": true,
  "response": "Merhaba! Ben Longo AI'yım. Sağlık ve beslenme konularında sana yardımcı olabilirim. Nasıl yardımcı olabilirim?",
  "session_id": "unique_session_id"
}
```

---

## 🏆 Premium Plus Endpoint

### **POST** `/ai/premium-plus/lifestyle-recommendations`

Premium Plus kullanıcıları için kişiselleştirilmiş beslenme, spor ve egzersiz önerileri.

#### Request Body
```json
{}
```

#### Response
```json
{
  "success": true,
  "message": "Premium Plus lifestyle önerileri hazırlandı",
  "recommendations": {
    "nutrition": ["Beslenme önerileri"],
    "exercise": ["Egzersiz önerileri"],
    "lifestyle": ["Yaşam tarzı önerileri"]
  }
}
```

---

## 📊 Endpoint Özeti

| Endpoint | Supplement Önerisi | Analiz | Kullanıcı Seviyesi |
|----------|-------------------|--------|-------------------|
| **Quiz** | ✅ 4 default + 3 personalized | ✅ | Tüm seviyeler |
| **Lab Summary** | ✅ 4 default + 1 personalized | ✅ | Premium+ |
| **Lab Session** | ❌ | ✅ | Premium+ |
| **Lab Single** | ❌ | ✅ | Premium+ |
| **Chat** | ❌ | ❌ | Tüm seviyeler |
| **Premium Plus** | ❌ | ✅ | Premium Plus |

---

## 🔧 Frontend Integration

### JavaScript Example
```javascript
// Quiz endpoint
const response = await fetch('https://longo-ai.onrender.com/ai/quiz', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'username': 'longopass',
    'password': '123456',
    'x-user-id': 'user123',
    'x-user-level': '2'
  },
  body: JSON.stringify({
    quiz_answers: {
      age: 30,
      gender: 'male',
      health_goals: ['energy']
    }
  })
});

const data = await response.json();
console.log(data.supplement_recommendations);
```

### cURL Example
```bash
curl -X POST "https://longo-ai.onrender.com/ai/quiz" \
  -H "username: longopass" \
  -H "password: 123456" \
  -H "x-user-id: test123" \
  -H "x-user-level: 2" \
  -H "Content-Type: application/json" \
  -d '{
    "quiz_answers": {
      "age": 30,
      "gender": "male",
      "health_goals": ["energy"]
    }
  }'
```

---

## ⚠️ Error Codes

| Code | Açıklama |
|------|----------|
| 400 | Bad Request - Geçersiz istek |
| 401 | Unauthorized - Kimlik doğrulama hatası |
| 403 | Forbidden - Yetkisiz erişim |
| 404 | Not Found - Endpoint bulunamadı |
| 500 | Internal Server Error - Sunucu hatası |

---

## 📝 Notlar

- Tüm endpoint'ler Türkçe yanıt verir
- **Quiz**: 4 default + 3 personalized supplement önerisi
- **Lab Summary**: 4 default + 1 personalized supplement önerisi (lab sonuçlarına göre)
- **Lab Session ve Lab Single**: Sadece analiz yapar, supplement önerisi yok
- User level kontrolü tüm endpoint'lerde uygulanır
- CORS desteği mevcuttur