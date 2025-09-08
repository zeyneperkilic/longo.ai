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
x-user-plan: free|premium|premium_plus  # Alternatif plan belirleme (şu an bu fallback)
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
    "health_goals": ["energy", "immunity", "sleep"],
    "activity_level": "moderate",
    "height": 175,
    "weight": 70,
    "allergies": ["gluten"],
    "medications": ["aspirin"],
    "health_conditions": ["diabetes"],
    "dietary_preferences": ["balanced", "vegetarian"],
    "supplement_experience": "beginner"
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
      "Protein açısından dengeli beslen, her öğünde kaliteli protein kaynağı ekle",
      "Bağışıklık desteği için C vitamini ve çinko içeren gıdaları artır"
    ]
  },
  "lifestyle_advice": {
    "title": "Yaşam Tarzı Önerileri",
    "recommendations": [
      "Düzenli uyku alışkanlığı oluştur (7-8 saat uyku)",
      "Haftada en az 3 gün orta düzey egzersiz yap"
    ]
  },
  "supplement_recommendations": [
    {
      "name": "Omega-3 Yağ Asitleri (Balık Yağı)",
      "description": "Kalp, beyin ve bağışıklık desteği için",
      "daily_dose": "1000 mg EPA+DHA",
      "benefits": ["Bağışıklığı destekler", "Enflamasyonu azaltır"],
      "warnings": ["Kan sulandırıcı ile dikkat edilmeli"],
      "priority": "high",
      "type": "recommended"
    }
  ],
  "default_supplements": [
    {
      "name": "D Vitamini",
      "description": "Kemik sağlığı ve bağışıklık için önemli",
      "daily_dose": "600-800 IU (doktorunuza danışın)",
      "benefits": ["Kalsiyum emilimini artırır", "Bağışıklık güçlendirir"],
      "warnings": ["Yüksek dozlarda toksik olabilir"],
      "priority": "high",
      "type": "default"
    }
  ],
  "personalized_supplements": [
    {
      "name": "Bağışıklık Destek Karışımı",
      "description": "Bağışıklık fonksiyonunu güçlendirmek için",
      "daily_dose": "Ürün etiketine göre",
      "benefits": ["Enfeksiyonlara karşı koruma", "Enerji seviyesini artırır"],
      "warnings": ["Bağışıklık sistemi aşırı uyarımı riskli olabilir"],
      "priority": "high",
      "type": "personalized"
    }
  ],
  "excluded_due_to_allergy": [],
  "allergy_alternatives": [],
  "special_conditions_analysis": {
    "detected_conditions": [],
    "risk_assessment": "Ciddi risk yok, alerji veya ilaç kullanımı bulunmuyor",
    "safety_recommendations": ["Takviyeleri doktoruna danışarak kullan", "Dengeli beslenmeye devam et"]
  },
  "disclaimer": "Bu içerik bilgilendirme amaçlıdır; tıbbi tanı/tedavi için hekiminize başvurun."
}
```

---

## 🔬 Lab Analysis Endpoints

### **POST** `/ai/lab/summary` - Lab Summary (Supplement Önerisi İLE)

Birden fazla lab test sonucunu analiz eder ve supplement önerileri verir.

#### Request Body
```json
{
  "tests": [
    {
      "name": "D Vitamini",
      "value": "15",
      "unit": "ng/mL",
      "reference_range": "30-100"
    },
    {
      "name": "B12 Vitamini",
      "value": "450",
      "unit": "pg/mL",
      "reference_range": "200-900"
    }
  ]
}
```

#### Response
```json
{
  "title": "Tüm Testlerin Genel Yorumu",
  "general_assessment": {
    "overall_summary": "Laboratuvar sonuçlarında D vitamini seviyesinin 15 ng/mL ile belirgin şekilde düşük olduğu görülüyor.",
    "patterns_identified": "Vitamin D düşüklüğü dikkat çekici bir bulgu.",
    "areas_of_concern": "D vitamini eksikliği uzun dönemde kemik sağlığını olumsuz etkileyebilir.",
    "positive_aspects": "B12 vitaminin normal düzeyde olması sinir sistemi açısından olumlu bir bulgudur."
  },
  "test_details": {
    "D Vitamini": {
      "interpretation": "15 ng/mL ile normalin belirgin altında.",
      "significance": "Kemik sağlığı, bağışıklık ve enerji için çok önemli.",
      "suggestions": "Takviye başlanmalı, güneş ışığından daha fazla faydalanılmalı."
    }
  },
  "supplement_recommendations": [
    {
      "name": "D Vitamini (ID: 165)",
      "description": "Düşük seviyeyi yükseltmek için temel takviye.",
      "daily_dose": "1000-2000 IU/gün (doktor kontrolünde daha yüksek olabilir)",
      "benefits": ["Kemik sağlığı", "Bağışıklık sistemi güçlendirme", "Enerji desteği"],
      "warnings": ["Kan düzeyleri kontrol edilmeden yüksek doz alınmamalıdır."],
      "priority": "high",
      "type": "lab_analysis"
    }
  ],
  "lifestyle_recommendations": {
    "exercise": [
      "Haftada en az 3-4 gün 30-40 dakika yürüyüş veya hafif egzersiz yap.",
      "Güneş ışığından faydalanarak açık havada egzersiz yapmaya çalış."
    ],
    "nutrition": [
      "Yağlı balıklar (somon, sardalya), yumurta sarısı ve mantar gibi D vitamini kaynaklarını diyetine ekle."
    ],
    "sleep": [
      "Her gün aynı saatte uyuyup uyanmaya çalış.",
      "Uyumadan önce mavi ışığı (telefon, bilgisayar) sınırlamaya çalış."
    ],
    "stress_management": [
      "Günlük 10-15 dk nefes egzersizleri veya meditasyon yap."
    ]
  },
  "overall_status": "dikkat_edilmeli",
  "test_count": 1,
  "disclaimer": "Bu içerik bilgilendirme amaçlıdır; tıbbi tanı/tedavi için hekiminize başvurun."
}
```

### **POST** `/ai/lab/session` - Lab Session (Sadece Analiz)

Tek seans lab test sonuçlarını analiz eder, supplement önerisi vermez.

#### Request Body
```json
{
  "tests": [
    {
      "name": "D Vitamini",
      "value": "15",
      "unit": "ng/mL",
      "reference_range": "30-100"
    },
    {
      "name": "B12 Vitamini",
      "value": "450",
      "unit": "pg/mL",
      "reference_range": "200-900"
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
    "total_tests": 2
  },
  "general_assessment": {
    "clinical_meaning": "Bu seanstaki iki testten biri normal, diğeri düşük. D Vitamini seviyen referans aralığının altında.",
    "overall_health_status": "1 anormal değer (D Vitamini düşük), 1 normal değer (B12 Vitamini normal)."
  },
  "test_groups": {
    "Vitaminler": [
      {
        "test_adi": "D Vitamini",
        "sonuc": "15 ng/mL",
        "referans_araligi": "30-100",
        "durum": "Anormal"
      },
      {
        "test_adi": "B12 Vitamini",
        "sonuc": "450 pg/mL",
        "referans_araligi": "200-900",
        "durum": "Normal"
      }
    ]
  },
  "test_summary": {
    "total_tests": 2,
    "normal_count": 1,
    "attention_count": 1
  },
  "general_recommendations": [
    "Güneş ışığından daha fazla yararlanmayı düşün, özellikle sabah ve öğle saatlerinde kısa süreli maruziyet faydalı olabilir.",
    "Dengeli beslenmeye özen göster, özellikle balık, yumurta, süt ürünleri gibi doğal D vitamini kaynaklarını beslenmene ekleyebilirsin.",
    "D Vitamini seviyeni 3-6 ay içinde tekrar kontrol ettirmen faydalı olur."
  ],
  "disclaimer": "Bu içerik bilgilendirme amaçlıdır; tıbbi tanı/tedavi için hekiminize başvurun."
}
```

### **POST** `/ai/lab/single` - Lab Single (Sadece Analiz)

Tek bir lab test sonucunu analiz eder, supplement önerisi vermez.

#### Request Body
```json
{
  "test": {
    "name": "D Vitamini",
    "value": "15",
    "unit": "ng/mL",
    "reference_range": "30-100"
  },
  "historical_results": [
    {
      "date": "2023-06-15",
      "value": "18",
      "status": "düşük",
      "lab": "Lab A",
      "notes": "Önceki test"
    }
  ]
}
```

#### Response
```json
{
  "analysis": {
    "summary": "Düşük",
    "interpretation": "D Vitamini sonucu 15 ng/mL olup referans aralığı olan 30-100 ng/mL'nin oldukça altında. Bu değer ciddi bir D vitamini eksikliğine işaret eder.",
    "reference_comparison": "Sonuç: 15 ng/mL. Referans aralığı: 30-100 ng/mL. Değer, alt sınırın %50'sinden bile düşük seviyede.",
    "clinical_significance": "D vitamini eksikliği kemik mineralizasyonunu bozabilir, osteopeni/osteoporoz, kas güçsüzlüğü, düşme riskinde artış ve bağışıklık sistemi fonksiyonlarında zayıflamaya yol açabilir.",
    "category_insights": "Bu test, 'Vitamin ve Mineral Profili' kategorisine girer. Vitamin D (25-hidroksi D) genellikle vücutta depolanan formu yansıtır.",
    "trend_analysis": "Geçmiş sonuçlara göre D vitamini seviyesi düşüş trendinde. 2023-06-15'te 18 ng/mL iken şu an 15 ng/mL'ye düşmüş.",
    "follow_up_suggestions": "Sonucun düşük olması nedeniyle, klinik semptomlar ile birlikte değerlendirilmesi gerekir. Hekim tarafından tekrar test yapılması, kalsiyum, fosfor ve parathormon seviyelerinin kontrol edilmesi faydalı olabilir.",
    "data_quality": "Test adı, sonucunu ve referans aralığını doğru bir şekilde içeriyor. Geçmiş sonuçlar da mevcut ve trend analizi yapılabildi."
  },
  "disclaimer": "Bu içerik bilgilendirme amaçlıdır; tıbbi tanı/tedavi için hekiminize başvurun."
}
```

---

## 💬 Chat Endpoints

### **POST** `/ai/chat/start` - Chat Başlat

Yeni bir chat konuşması başlatır.

#### Request Body
```json
{
  "message": "Merhaba, sağlık konusunda yardım istiyorum"
}
```

#### Response
```json
{
  "conversation_id": 1
}
```

### **POST** `/ai/chat` - Chat Mesajı

Chat konuşmasına mesaj gönderir.

#### Request Body
```json
{
  "conversation_id": 1,
  "message": "D vitamini eksikliğim var, ne önerirsin?"
}
```

#### Response
```json
{
  "conversation_id": 1,
  "reply": "D vitamini eksikliği için öncelikle güneş ışığından daha fazla yararlanmanı öneririm. Ayrıca yağlı balıklar, yumurta sarısı ve D vitamini ile zenginleştirilmiş süt ürünlerini beslenmene ekleyebilirsin. Doktorunla görüşerek uygun D vitamini takviyesi alabilirsin.",
  "latency_ms": 1250
}
```

---

## 🏥 Premium Plus Endpoint

### **POST** `/ai/premium-plus/lifestyle-recommendations`

Premium Plus kullanıcıları için kişiselleştirilmiş beslenme, spor ve egzersiz önerileri.

#### Request Body
```json
{
  "user_context": {
    "age": 30,
    "gender": "male",
    "health_goals": ["energy", "immunity"],
    "activity_level": "moderate"
  }
}
```

#### Response
```json
{
  "title": "Premium Plus Yaşam Tarzı Önerileri",
  "personalized_nutrition": {
    "daily_meal_plan": "Kişiselleştirilmiş beslenme planı...",
    "supplement_timing": "Takviye alma zamanları...",
    "hydration_plan": "Su tüketim planı..."
  },
  "exercise_recommendations": {
    "weekly_schedule": "Haftalık egzersiz programı...",
    "intensity_levels": "Yoğunluk seviyeleri...",
    "recovery_plan": "Toparlanma planı..."
  },
  "lifestyle_optimization": {
    "sleep_schedule": "Uyku düzeni...",
    "stress_management": "Stres yönetimi...",
    "work_life_balance": "İş-yaşam dengesi..."
  }
}
```

---

## 📊 User Management Endpoints

### **GET** `/users/{user_id}/global-context`

Kullanıcının global context bilgilerini getirir.

#### Response
```json
{
  "user_id": "test123",
  "global_context": {
    "yas": 30,
    "cinsiyet": "male",
    "hedef": ["energy", "immunity"],
    "aktivite": "moderate",
    "boy": 175,
    "kilo": 70
  }
}
```

### **GET** `/users/{external_user_id}/info`

Kullanıcı bilgilerini getirir.

#### Response
```json
{
  "user_id": "test123",
  "plan": "premium",
  "created_at": "2024-01-15T10:30:00Z",
  "last_active": "2024-01-15T14:20:00Z"
}
```

---

## 🔧 Utility Endpoints

### **GET** `/health`

Sistem sağlık durumunu kontrol eder.

#### Response
```json
{
  "status": "ok",
  "service": "longopass-ai"
}
```

### **GET** `/api/supplements.xml`

Mevcut supplement listesini XML formatında getirir.

#### Response
```xml
<?xml version="1.0" encoding="UTF-8"?>
<supplements>
  <supplement id="165">
    <name>D3 Vitamini</name>
    <category>Günlük Takviyeler</category>
    <description>Kemik sağlığı ve bağışıklık için</description>
  </supplement>
</supplements>
```



## 📝 Önemli Notlar

1. **Authentication**: Tüm endpoint'ler için `username` ve `password` header'ları zorunludur.

2. **User Management**: `x-user-id` ve `x-user-level` header'ları kullanıcı yönetimi için kullanılır.

3. **Supplement Önerileri**: Sadece `/ai/quiz` ve `/ai/lab/summary` endpoint'leri supplement önerisi verir.

4. **Lab Analizi**: `/ai/lab/session` ve `/ai/lab/single` endpoint'leri sadece analiz yapar, supplement önerisi vermez.

5. **Rate Limiting**: Production'da rate limiting uygulanmıştır.

6. **CORS**: Tüm origin'lerden gelen isteklere izin verilir.

7. **Response Format**: Tüm yanıtlar JSON formatındadır, HTML döndürülmez.

---

## 🚀 Frontend Entegrasyonu

### JavaScript Örneği
```javascript
// Quiz analizi
const quizResponse = await fetch('https://longo-ai.onrender.com/ai/quiz', {
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
      health_goals: ['energy', 'immunity']
    }
  })
});

const quizData = await quizResponse.json();
console.log(quizData.supplement_recommendations);
```

### cURL Örneği
```bash
curl -X POST "https://longo-ai.onrender.com/ai/quiz" \
  -H "username: longopass" \
  -H "password: 123456" \
  -H "x-user-id: user123" \
  -H "x-user-level: 2" \
  -H "Content-Type: application/json" \
  -d '{
    "quiz_answers": {
      "age": 30,
      "gender": "male",
      "health_goals": ["energy", "immunity"]
    }
  }'
```

---


