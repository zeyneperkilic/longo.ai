# Longopass AI Gateway - API Dokümantasyonu

## 📋 Genel Bilgiler

**Base URL:** `https://longo-ai.onrender.com`  
**Authentication:** Basic Auth (Header'da username/password)  
**Content-Type:** `application/json`  
**Response Format:** JSON

### 🔐 Authentication Headers (Zorunlu)
```http
username: longopass
password: 123456
```

### 👤 User Management Headers
```http
x-user-id: unique_user_id        # Kullanıcı ID'si (zorunlu)
x-user-level: 1|2|3             # Kullanıcı seviyesi (opsiyonel)
```

**Plan Mapping:**
- `1` → **Free** (10 soru limiti)
- `2` → **Premium** (Sınırsız + Lab analizi)
- `3` → **Premium Plus** (Tüm özellikler)
- Header gelmezse → **Free** (üye değilse)

### 📝 Content-Type Header (Zorunlu)
```http
Content-Type: application/json
```
**TÜM POST endpoint'leri için zorunlu!**

---

## 🧪 Quiz Endpoint

### **POST** `/ai/quiz`

Kişiselleştirilmiş supplement önerileri ve beslenme tavsiyeleri alır.

#### Request Body
```json
{
  "quiz_data": {
    "age": 30,
    "gender": "female",
    "health_conditions": [],
    "current_supplements": [],
    "goals": ["energy", "immunity"]
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
      "Günlük olarak taze sebze ve meyve tüketimini artır, özellikle yeşil yapraklı sebzeleri önceliklendir.",
      "Rafine karbonhidrat ve şekerden uzak dur, bunun yerine tam tahılları tercih et.",
      "Su tüketimini artırarak günde en az 2-2.5 litre su içmeye özen göster."
    ]
  },
  "lifestyle_advice": {
    "title": "Yaşam Tarzı Önerileri",
    "recommendations": [
      "Her gün en az 20-30 dakika yürüyüş veya hafif egzersiz yap.",
      "Uyku kalitesini iyileştirmek için düzenli uyku saatleri oluştur.",
      "Stresi azaltmak için nefes egzersizleri, yoga veya meditasyon yapmayı dene."
    ]
  },
  "general_warnings": {
    "title": "Genel Uyarılar",
    "warnings": [
      "Takviyeleri kullanmadan önce doktoruna danışmayı unutma.",
      "Önerilen günlük dozları aşma.",
      "Eğer kronik hastalığın veya düzenli kullandığın ilaçların varsa, etkileşim riskine karşı dikkatli ol."
    ]
  },
  "supplement_recommendations": [
    {
      "name": "D Vitamini (ID: 164)",
      "description": "Kemik sağlığı, bağışıklık sistemi ve genel enerji için destek sağlar.",
      "daily_dose": "1000-2000 IU",
      "benefits": ["Kemik sağlığını korur", "Bağışıklık sistemini güçlendirir", "Enerji seviyelerini destekler"],
      "warnings": ["Yüksek dozda alımı böbrek taşı riskini artırabilir."],
      "priority": "high",
      "type": "default"
    },
    {
      "name": "Omega-3 Yağ Asitleri (Balık Yağı) (ID: 179)",
      "description": "Kalp ve beyin sağlığı için gerekli esansiyel yağ asitlerini sağlar.",
      "daily_dose": "1000 mg",
      "benefits": ["Kalp sağlığını destekler", "Hafıza ve odaklanmayı artırır", "İltihaplanmayı azaltır"],
      "warnings": ["Kan sulandırıcı ilaç kullananlar doktor kontrolünde kullanmalı."],
      "priority": "high",
      "type": "default"
    },
    {
      "name": "Magnezyum (ID: 176)",
      "description": "Kas ve sinir sistemi sağlığını destekler, uyku kalitesini artırır.",
      "daily_dose": "300-400 mg",
      "benefits": ["Kas kramplarını azaltır", "Stresi hafifletir", "Uyku kalitesini artırır"],
      "warnings": ["Fazla kullanımda ishal yapabilir."],
      "priority": "high",
      "type": "default"
    },
    {
      "name": "B12 (Kobalamin) (ID: 154)",
      "description": "Sinir sistemi, kırmızı kan hücreleri üretimi ve enerji metabolizmasını destekler.",
      "daily_dose": "500-1000 mcg",
      "benefits": ["Enerji seviyelerini destekler", "Kansızlığı önler", "Sinir sistemini korur"],
      "warnings": ["B12 fazlalığı genellikle zararsızdır ancak böbrek sorunları olanlarda dikkat edilmeli."],
      "priority": "high",
      "type": "default"
    },
    {
      "name": "Probiyotik (ID: 181)",
      "description": "Bağırsak sağlığı ve bağışıklık sistemi için destek sağlar.",
      "daily_dose": "10-20 milyar CFU",
      "benefits": ["Sindirim sistemini düzenler", "Bağışıklık direncini artırır", "Bağırsak florasını dengeler"],
      "warnings": ["Bağışıklık sistemi baskılanmış kişiler dikkatle kullanmalı."],
      "priority": "medium",
      "type": "personalized"
    },
    {
      "name": "Koenzim Q10 (CoQ10) (ID: 221)",
      "description": "Hücrelerde enerji üretimini destekler, kalp sağlığına katkıda bulunur.",
      "daily_dose": "100-200 mg",
      "benefits": ["Kalp sağlığını destekler", "Enerji üretimini artırır", "Antioksidan etki sağlar"],
      "warnings": ["Kan basıncı düşürücü ilaçlarla birlikte dikkatli kullanılmalı."],
      "priority": "medium",
      "type": "personalized"
    },
    {
      "name": "Kurkumin (Zerdeçaldan) (ID: 224)",
      "description": "Güçlü anti-inflamatuar ve antioksidan özelliklere sahip.",
      "daily_dose": "500-1000 mg",
      "benefits": ["İltihaplanmayı azaltır", "Eklem sağlığını destekler", "Antioksidan koruma sağlar"],
      "warnings": ["Safra kesesi taşı olanlar dikkatle kullanmalı."],
      "priority": "medium",
      "type": "personalized"
    }
  ],
  "test_recommendations": {
    "title": "Test Önerileri",
    "recommended_tests": [
      {
        "test_name": "Vitamin B12 ve Metilmalonik Asit (MMA) Testi",
        "reason": "Vegan beslenme nedeniyle B12 eksikliği riski yüksek",
        "benefit": "B12 eksikliğinin erken tespiti ve sinir sistemi sağlığının korunması"
      },
      {
        "test_name": "25-OH D Vitamini Testi",
        "reason": "D vitamini eksikliği yaygın ve kemik sağlığı için kritik",
        "benefit": "Kemik yoğunluğu ve bağışıklık sistemi sağlığının değerlendirilmesi"
      }
    ],
    "analysis_summary": "Quiz verilerine göre analiz tamamlandı",
    "disclaimer": "Bu öneriler bilgilendirme amaçlıdır. Test yaptırmadan önce doktorunuza danışın."
  },
  "disclaimer": "Bu içerik bilgilendirme amaçlıdır; tıbbi tanı/tedavi için hekiminize başvurun."
}
```

#### Strateji
- **4 DEFAULT + 3 PERSONALIZED = 7 supplement**
- **DEFAULT**: D Vitamini, Omega-3, Magnezyum, B12
- **PERSONALIZED**: Quiz cevaplarına göre (energy hedefi için Probiyotik, CoQ10, Kurkumin)

---

## 📊 Lab Endpoint'leri Karşılaştırması

| Endpoint | Amaç | Test Sayısı | Supplement Önerisi | Test Önerisi | Kullanım Senaryosu |
|----------|------|-------------|-------------------|--------------|-------------------|
| `/ai/lab/single` | Tek test analizi | 1 | ❌ | ❌ | Tek test sonucunun detaylı analizi |
| `/ai/lab/session` | Seans analizi | 1+ (aynı gün) | ❌ | ❌ | Aynı gün yapılan testlerin birlikte analizi |
| `/ai/lab/summary` | Genel analiz | 1+ (tüm testler) | ✅ | ✅ | Tüm testlerin genel değerlendirmesi |

---

## 🧬 Lab Summary Endpoint

### **POST** `/ai/lab/summary`

**TÜM LAB TESTLERİNİN GENEL ANALİZİ** - Birden fazla test sonucunun bir arada değerlendirilmesi ve supplement önerileri.

**Kullanım:** Tüm testlerin genel sağlık durumu analizi için kullanılır.

**Ne zaman kullanılır:**
- Kullanıcının tüm lab testlerinin genel değerlendirmesi
- Supplement önerileri isteniyorsa
- Test önerileri isteniyorsa
- Genel sağlık durumu raporu isteniyorsa

#### Request Body
```json
{
  "test_count": 2,
  "tests": [
    {
      "name": "Vitamin D",
      "value": 18,
      "unit": "ng/mL",
      "reference_range": "30-100 ng/mL"
    },
    {
      "name": "Hemoglobin",
      "value": 13.5,
      "unit": "g/dL",
      "reference_range": "12-16 g/dL"
    }
  ]
}
```

#### Response
```json
{
  "title": "Tüm Testlerin Genel Yorumu",
  "genel_saglik_durumu": "Test sonuçların genel olarak dengeli görünüyor. Hemoglobin referans aralığında olduğundan kansızlık görünmüyor. Ancak D vitamini ciddi derecede düşük (18 ng/mL, alt sınır 30 ng/mL). Bu da kemik sağlığı, bağışıklık ve enerji üzerinde olumsuz etkilere yol açabilir.",
  "genel_durum": "Mevcut tek seanslık testte en önemli bulgu D vitamini eksikliği. Daha önceki seanslarla kıyaslama olmadığından trend analizi yapılamıyor. Hemoglobin normal; bu da beslenme açısından yeterli demir desteği olduğunu gösteriyor. Ancak düşük D vitamini kemik sağlığı ve güneş yetersizliği açısından risk oluşturuyor.",
  "oneriler": [
    "Haftada en az 3-4 gün 20 dakika güneş görmeyi alışkanlık haline getir.",
    "D vitamini desteğini düzenli olarak kullanmaya başla ve tekrar testle takip et.",
    "Kalsiyum ve magnezyumdan zengin gıdaları (yoğurt, badem, yeşil yapraklı sebzeler) beslenmene ekle.",
    "Güçlü bağışıklık için yeterli uyku, düzenli egzersiz ve dengeli beslenmeye dikkat et.",
    "Bol su içmeye devam et, bu vitaminlerin metabolizmasına yardımcı olur."
  ],
  "urun_onerileri": [
    {
      "name": "D3 Vitamini (ID: 165)",
      "description": "Düzeyi düşük çıkan D vitaminini yükseltmek için en temel ve gerekli destek.",
      "daily_dose": "1000-2000 IU (eksiklik düzeyine göre doktor kontrolünde daha yüksek doz kullanılabilir)",
      "benefits": ["Kemik ve diş sağlığı", "Bağışıklık güçlenmesi", "Kas fonksiyonlarını destekleme"],
      "warnings": ["Fazla dozda alımı toksisiteye yol açabilir", "Kalsiyum ile birlikte kullanıldığında dikkat edilmeli"],
      "priority": "high"
    },
    {
      "name": "K2 Vitamini (ID: 171)",
      "description": "D vitamini ile birlikte alındığında kalsiyumun doğru şekilde kemiklere yönlenmesine yardımcı olur.",
      "daily_dose": "90-120 mcg",
      "benefits": ["Kemik yoğunluğunu destekler", "D vitamininin etkinliğini artırır", "Damar kalsifikasyonunu azaltır"],
      "warnings": ["Kan sulandırıcı ilaç kullananlarda dikkat edilmeli"],
      "priority": "high"
    },
    {
      "name": "Magnezyum (ID: 176)",
      "description": "D vitamini metabolizmasında kritik rol oynar, kas rahatlamasını ve enerji üretimini destekler.",
      "daily_dose": "200-400 mg",
      "benefits": ["Kas kramplarını azaltır", "Kemik sağlığını destekler", "Uyku kalitesini artırır"],
      "warnings": ["Böbrek hastalarında doktor kontrolünde kullanılmalı"],
      "priority": "medium"
    },
    {
      "name": "Omega-3 Yağ Asitleri (Balık Yağı) (ID: 179)",
      "description": "Bağışıklık, damar sağlığı ve beyin fonksiyonlarını destekleyici genel bir sağlıklı yaşam desteği.",
      "daily_dose": "1000 mg EPA+DHA",
      "benefits": ["Kalp-damar sağlığını korur", "Anti-inflamatuar etki sağlar", "Beyin fonksiyonlarını destekler"],
      "warnings": ["Kan sulandırıcı ilaçlarla birlikte dikkat edilmeli"],
      "priority": "medium"
    },
    {
      "name": "Kadınlar için Sağlıklı Yaşam Multivitamini (ID: 251)",
      "description": "Genel vitamin-mineral desteği sağlayarak bağışıklık ve enerji ihtiyacını dengeler.",
      "daily_dose": "1 tablet",
      "benefits": ["Genel enerji artışı", "Beslenme eksikliklerini tamamlar", "Bağışıklığı güçlendirir"],
      "warnings": ["Fazladan vitamin takviyesi ile birlikte aşırı doz riski olabilir"],
      "priority": "low"
    }
  ],
  "test_recommendations": {
    "title": "Test Önerileri",
    "recommended_tests": [
      {
        "test_name": "25-OH D Vitamini Tekrar Testi",
        "reason": "D vitamini seviyeniz ciddi düşük (18; normal 30-100)",
        "benefit": "Kemik sağlığı, bağışıklık ve metabolizma için eksikliği teyit ederek takviye planına yön verir"
      },
      {
        "test_name": "Kalsiyum ve Fosfor Testi",
        "reason": "D vitamini eksikliği kalsiyum emilimini etkileyebilir",
        "benefit": "Kemik sağlığı için kalsiyum-fosfor dengesinin değerlendirilmesi"
      }
    ],
    "analysis_summary": "Lab verilerine göre analiz tamamlandı",
    "disclaimer": "Bu öneriler bilgilendirme amaçlıdır. Test yaptırmadan önce doktorunuza danışın."
  },
  "disclaimer": "Bu içerik bilgilendirme amaçlıdır; tıbbi tanı/tedavi için hekiminize başvurun.",
  "test_count": 1,
  "overall_status": "analiz_tamamlandı"
}
```

#### Strateji
- **5 supplement** (lab sonuçlarına göre)
- **Detaylı lab analizi** ve genel değerlendirme
- **Yaşam tarzı önerileri** dahil
- **Test sayısı** ve genel durum değerlendirmesi

---

## 🔬 Lab Session Endpoint

### **POST** `/ai/lab/session`

**TEK BİR LAB SEANSININ ANALİZİ** - Aynı gün yapılan birden fazla testin birlikte değerlendirilmesi (supplement önerisi YOK).

**Kullanım:** Aynı gün yapılan testlerin seans analizi için kullanılır.

**Ne zaman kullanılır:**
- Aynı gün yapılan birden fazla testin birlikte değerlendirilmesi
- Seans bazında test sonuçlarının analizi
- Supplement önerisi istenmiyorsa
- Sadece test analizi isteniyorsa

#### Request Body
```json
{
  "laboratory": "Test Lab",
  "test_date": "2024-01-15",
  "session_tests": [
    {
      "name": "Vitamin D",
      "value": 18,
      "unit": "ng/mL",
      "reference_range": "30-100 ng/mL"
    }
  ]
}
```

#### Response
```json
{
  "title": "Test Seansı Analizi",
  "session_info": {
    "laboratory": "Test Lab",
    "session_date": "2024-01-15",
    "total_tests": 1
  },
  "general_assessment": {
    "clinical_meaning": "Bu test seansında sadece D Vitamini ölçülmüş. Sonucun 18 ng/mL olması, referans aralığının (30-100 ng/mL) altında kaldığını gösteriyor. Bu durum D vitamini eksikliğine işaret edebilir. D vitamini bağışıklık sistemi, kemik sağlığı ve kas fonksiyonları için önemli bir vitamindir. Eksikliği özellikle kış aylarında, güneş ışığının az olduğu dönemlerde daha sık görülür.",
    "overall_health_status": "D Vitamini düşük bulundu."
  },
  "test_groups": {
    "Vitaminler": [
      {
        "test_adi": "D Vitamini",
        "sonuc": "18 ng/mL",
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
    "Gün ışığından daha fazla yararlanmaya çalış (özellikle sabah ve öğle saatlerinde).",
    "D vitamini yönünden zengin yiyecekleri (ör. yağlı balık, yumurta sarısı) beslenmene ekleyebilirsin.",
    "Düzenli olarak açık havada yürüyüş yapmaya özen göster.",
    "D vitamini seviyeni 3-6 ay içinde tekrar kontrol ettirmen faydalı olabilir.",
    "Bu sonuçla birlikte doktoruna başvurarak ayrıntılı değerlendirme yaptırman önemli. Eksikliğin derecesine ve kişisel sağlık durumuna göre uygun yaklaşımı hekim belirleyecektir."
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

**TEK BİR TEST SONUCUNUN DETAYLI ANALİZİ** - Sadece bir test sonucunun derinlemesine değerlendirilmesi (supplement önerisi YOK).

**Kullanım:** Tek bir test sonucunun detaylı analizi için kullanılır.

**Ne zaman kullanılır:**
- Sadece bir test sonucunun detaylı analizi
- Test sonucunun derinlemesine değerlendirilmesi
- Supplement önerisi istenmiyorsa
- Tek test odaklı analiz isteniyorsa

#### Request Body
```json
{
  "test": {
    "name": "Vitamin D",
    "value": 18,
    "unit": "ng/mL",
    "reference_range": "30-100 ng/mL"
  }
}
```

#### Response
```json
{
  "title": "Test Sonucu Yorumu",
  "test_name": "Vitamin D Sonucu Değerlendirmesi",
  "last_result": "Son Test Sonucunuz: 18 ng/mL (Düşük)",
  "reference_range": "Referans Aralığı: 30-100 ng/mL",
  "test_analysis": "25-Hidroksi Vitamin D testi kemik ve mineral metabolizması açısından kritik bir parametredir. Senin sonucun 18 ng/mL olup, referans aralığının (30-100 ng/mL) belirgin şekilde altındadır. Bu değer 'Vitamin D yetersizliği' kategorisine girer. D vitamininin düşük olması, kalsiyum emilimini ve kemik sağlığını olumsuz etkileyebilir, uzun vadede kas güçsüzlüğü, kemik erimesi ve bağışıklık fonksiyonlarında zayıflamaya yol açabilir. Şu an elimizde sadece tek bir sonuç var, bu yüzden trend analizi yapılamıyor. Eğer geçmişteki sonuçlar da olsaydı, düşüş mü yoksa artış mı olduğu net olarak değerlendirilebilirdi. Genel olarak, bu sonucun sağlık açısından önemli olduğu ve tıbbi takip gerektirdiğini söyleyebilirim.",
  "disclaimer": "Bu yorum sadece bilgilendirme amaçlıdır. Kesin tanı ve tedavi için mutlaka doktorunuza başvurunuz."
}
```

---

## 💬 Chat Endpoints

### **POST** `/ai/chat/start`

Yeni bir chat oturumu başlatır.

#### Request Body
```json
{}
```

#### Response
```json
{
  "conversation_id": 1757499211313
}
```

#### Özellik
- **Free Users**: `conversation_id = 1` (session-based)
- **Premium Users**: Unique timestamp-based ID

---

### **POST** `/ai/chat`

Chat mesajı gönderir ve AI hafızasını kullanır.

#### Request Body
```json
{
  "text": "Hangi takviyeleri önerdin bana?",
  "conversation_id": 1757421486962
}
```

#### Response
```json
{
  "conversation_id": 1757421486962,
  "reply": "Merhaba! Seninle daha önce yaptığımız quiz ve laboratuvar sonuçlarında özellikle D vitamini eksikliği öne çıkmıştı...",
  "latency_ms": 6176
}
```

#### Özellik
- **AI Hafızası**: Quiz ve lab sonuçlarını hatırlar
- **Kişiselleştirilmiş Yanıtlar**: Geçmiş verileri kullanarak öneriler verir
- **Conversation ID**: Her yeni chat penceresi için farklı ID kullanın

---

## 🏆 Premium Plus Endpoints

### **POST** `/ai/premium-plus/diet-recommendations`

Premium Plus kullanıcıları için detaylı beslenme önerileri. **Kullanıcının quiz ve lab verilerine göre kişiselleştirilmiş** öneriler verir.

#### Request Body
```json
{}
```

#### Response
```json
{
  "success": true,
  "message": "Beslenme önerileri hazırlandı",
  "recommendations": "## 1. 📊 MEVCUT DURUM ANALİZİ\n- Hedefler: Enerji dengesini sağlama, yağ oranını kontrol etme...\n\n## 2. 🥗 DETAYLI BESLENME ÖNERİLERİ\n- Karbonhidrat: %45 – Tam tahıllar, kinoa...\n- Protein: %25 – Tavuk, hindi, balık...\n- Yağ: %30 – Zeytinyağı, avokado...\n\n## 3. 🍽️ ÖĞÜN PLANLAMA\n- Kahvaltı: Yulaf ezmesi (50 g)...\n- Öğle: Izgara tavuk 150 g...\n\n## 4. ⚡ PERFORMANS BESLENMESİ\n- Egzersiz öncesi: Muz + yulaf...\n- Egzersiz sonrası: Whey protein...",
  "disclaimer": "Bu öneriler bilgilendirme amaçlıdır. Tıbbi kararlar için doktorunuza danışın."
}
```

#### Özellikler
- **Kişiselleştirilmiş öneriler:** Quiz ve lab verilerine göre özelleştirilmiş beslenme planı
- **Detaylı beslenme önerileri:** Lab sonuçlarına göre eksik vitamin/mineraller için spesifik besin önerileri
- **Makro besin dağılımı:** Karbonhidrat, protein, yağ oranları
- **Öğün planlama:** Kahvaltı, öğle, akşam yemeği önerileri
- **Performans beslenmesi:** Egzersiz öncesi/sonrası beslenme
- **Haftalık menü:** Detaylı menü önerileri
- **Supplement önerileri:** Beslenme ile birlikte takviye önerileri

#### cURL Örneği
```bash
curl -X POST "https://longo-ai.onrender.com/ai/premium-plus/diet-recommendations" \
  -H "Content-Type: application/json" \
  -H "username: longopass" \
  -H "password: 123456" \
  -H "x-user-id: user123" \
  -H "x-user-level: 3" \
  -d '{}'
```

---

### **POST** `/ai/premium-plus/exercise-recommendations`

Premium Plus kullanıcıları için detaylı egzersiz önerileri. **Kullanıcının quiz ve lab verilerine göre kişiselleştirilmiş** öneriler verir.

#### Request Body
```json
{}
```

#### Response
```json
{
  "success": true,
  "message": "Egzersiz önerileri hazırlandı",
  "recommendations": "## 1. 📊 MEVCUT DURUM ANALİZİ\n- Hedef: Genel kondisyon geliştirme...\n\n## 2. 🏃‍♂️ DETAYLI EGZERSİZ PROGRAMI\n- Haftada 4-5 gün, 45-60 dakika...\n- 2 gün kuvvet ağırlıklı\n- 2 gün kardiyo ağırlıklı\n\n## 3. 💪 GÜÇ ANTRENMANI\n- Şınav (3x8-12)\n- Squat (3x10-12)\n- Plank (3x30-45 sn)\n\n## 4. 🏃‍♀️ KARDİYOVASKÜLER\n- Steady-State Kardiyo (30-40 dk)\n- HIIT (20 dk)\n\n## 5. 🧘‍♀️ ESNEKLİK VE MOBİLİTE\n- Stretching ve yoga önerileri...",
  "disclaimer": "Bu öneriler bilgilendirme amaçlıdır. Tıbbi kararlar için doktorunuza danışın."
}
```

#### Özellikler
- **Kişiselleştirilmiş öneriler:** Quiz ve lab verilerine göre özelleştirilmiş egzersiz planı
- **Detaylı egzersiz programı:** Haftalık program önerisi (kaç gün, ne kadar süre)
- **Güç antrenmanı:** Vücut ağırlığı ve ağırlık antrenmanları
- **Kardiyovasküler:** Koşu, yürüyüş, bisiklet önerileri
- **Esneklik ve mobilite:** Stretching ve yoga önerileri
- **Performans ve recovery:** Egzersiz öncesi/sonrası rutinler
- **Progresyon stratejileri:** Set/tekrar sayıları ve ilerleme planı

#### cURL Örneği
```bash
curl -X POST "https://longo-ai.onrender.com/ai/premium-plus/exercise-recommendations" \
  -H "Content-Type: application/json" \
  -H "username: longopass" \
  -H "password: 123456" \
  -H "x-user-id: user123" \
  -H "x-user-level: 3" \
  -d '{}'
```

### **POST** `/ai/premium-plus/lifestyle-recommendations` (Deprecated)

**⚠️ Bu endpoint artık kullanılmıyor!** Lütfen yukarıdaki 2 ayrı endpoint'i kullanın:
- **Beslenme için:** `/ai/premium-plus/diet-recommendations`
- **Egzersiz için:** `/ai/premium-plus/exercise-recommendations`

#### Request Body
```json
{}
```
**Not:** Request body boş olmalı. Kullanıcı verileri header'lardan ve AI hafızasından alınır.

#### Response
```json
{
  "success": true,
  "message": "Lifestyle önerileri hazırlandı",
  "recommendations": "## 1. 📊 MEVCUT DURUM ANALİZİ\n- Hedefler: Enerji dengesini sağlama, yağ oranını kontrol etme...\n\n## 2. 🥗 BESLENME ÖNERİLERİ\n- Karbonhidrat: %45 – Tam tahıllar, kinoa...\n- Protein: %25 – Tavuk, hindi, balık...\n- Yağ: %30 – Zeytinyağı, avokado...\n\n## 3. 🏃‍♂️ EGZERSİZ ÖNERİLERİ\n- Haftada 4-5 gün, 45-60 dakika...\n- 2 gün kuvvet ağırlıklı\n- 2 gün kardiyo ağırlıklı\n\n## 4. ⚡ YAŞAM TARZI İPUÇLARI\n- Su tüketimi ve hidrasyon...\n- Uyku kalitesi...\n- Stres yönetimi...",
  "disclaimer": "Bu öneriler bilgilendirme amaçlıdır. Tıbbi kararlar için doktorunuza danışın."
}
```

#### Özellikler
- **AI Hafızası**: Quiz ve lab sonuçlarını hatırlar
- **Kişiselleştirilmiş Öneriler**: Geçmiş verileri kullanarak beslenme, spor ve egzersiz planı verir
- **Birleşik Response**: Beslenme, egzersiz ve yaşam tarzı önerileri tek response'da
- **Premium Plus Only**: Sadece `x-user-level: 3` kullanıcıları erişebilir
- **Temiz Response**: User context dahil edilmez, sadece öneriler
- **⚠️ Deprecated**: Bu endpoint artık kullanılmıyor, ayrı endpoint'leri kullanın

---

## 🧪 Test Recommendations (Entegre)

**⚠️ ÖNEMLİ:** Test önerileri artık ayrı bir endpoint değil, **Quiz** ve **Lab Summary** endpoint'lerine entegre edilmiştir!

### Quiz Endpoint'inde Test Önerileri
Quiz endpoint'i (`/ai/quiz`) artık test önerilerini de içerir:
```json
{
  "test_recommendations": {
    "title": "Test Önerileri",
    "recommended_tests": [
      {
        "test_name": "Vitamin B12 ve Metilmalonik Asit (MMA) Testi",
        "reason": "Vegan beslenme nedeniyle B12 eksikliği riski yüksek",
        "benefit": "B12 eksikliğinin erken tespiti ve sinir sistemi sağlığının korunması"
      }
    ],
    "analysis_summary": "Quiz verilerine göre analiz tamamlandı"
  }
}
```

### Lab Summary Endpoint'inde Test Önerileri
Lab Summary endpoint'i (`/ai/lab/summary`) de test önerilerini içerir:
```json
{
  "test_recommendations": {
    "title": "Test Önerileri",
    "recommended_tests": [
      {
        "test_name": "25-OH D Vitamini Tekrar Testi",
        "reason": "D vitamini seviyeniz ciddi düşük (18; normal 30-100)",
        "benefit": "Kemik sağlığı, bağışıklık ve metabolizma için eksikliği teyit ederek takviye planına yön verir"
      }
    ],
    "analysis_summary": "Lab verilerine göre analiz tamamlandı"
  }
}
```

#### Özellikler
- **Entegre Sistem**: Test önerileri artık ana endpoint'lerde
- **Quiz Tabanlı**: Quiz cevaplarına göre test önerileri
- **Lab Tabanlı**: Lab sonuçlarına göre test önerileri
- **AI Tabanlı**: Kullanıcının verilerini analiz eder
- **Akıllı Analiz**: Sadece gerekli testleri önerir
- **Kişiselleştirilmiş**: Mevcut verileri referans alarak açıklama yapar

---

## 🔧 Frontend Integration

### JavaScript Example
```javascript
// Quiz endpoint
const response = await fetch('https://longo-ai.onrender.com/ai/quiz', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',  // ZORUNLU!
    'username': 'longopass',             // ZORUNLU!
    'password': '123456',                // ZORUNLU!
    'x-user-id': 'user123',              // ZORUNLU!
    'x-user-level': 2                    // Opsiyonel (2=Premium)
  },
  body: JSON.stringify({
    quiz_data: {
      age: 30,
      gender: 'female',
      health_conditions: [],
      current_supplements: [],
      goals: ['energy', 'immunity']
    }
  })
});

const data = await response.json();
console.log(data.supplement_recommendations);

// Premium Plus endpoints (Request body boş!)
const dietResponse = await fetch('https://longo-ai.onrender.com/ai/premium-plus/diet-recommendations', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',  // ZORUNLU!
    'username': 'longopass',             // ZORUNLU!
    'password': '123456',                // ZORUNLU!
    'x-user-id': 'user123',              // ZORUNLU!
    'x-user-level': 3                    // ZORUNLU! (Premium Plus için)
  },
  body: JSON.stringify({})               // BOŞ OBJECT!
});

const exerciseResponse = await fetch('https://longo-ai.onrender.com/ai/premium-plus/exercise-recommendations', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',  // ZORUNLU!
    'username': 'longopass',             // ZORUNLU!
    'password': '123456',                // ZORUNLU!
    'x-user-id': 'user123',              // ZORUNLU!
    'x-user-level': 3                    // ZORUNLU! (Premium Plus için)
  },
  body: JSON.stringify({})               // BOŞ OBJECT!
});

const dietData = await dietResponse.json();
const exerciseData = await exerciseResponse.json();
console.log(dietData.recommendations);
console.log(exerciseData.recommendations);

// Test önerileri artık Quiz ve Lab Summary endpoint'lerinde entegre!
// Quiz endpoint'inden test önerileri al
const quizResponse = await fetch('https://longo-ai.onrender.com/ai/quiz', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'username': 'longopass',
    'password': '123456',
    'x-user-id': 'user123',
    'x-user-level': 2
  },
  body: JSON.stringify({
    quiz_data: {
      age: 30,
      gender: 'female',
      health_conditions: [],
      current_supplements: [],
      goals: ['energy', 'immunity']
    }
  })
});

const quizData = await quizResponse.json();
console.log(quizData.test_recommendations); // Test önerileri burada!

// Lab Summary endpoint'inden test önerileri al
const labSummaryResponse = await fetch('https://longo-ai.onrender.com/ai/lab/summary', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'username': 'longopass',
    'password': '123456',
    'x-user-id': 'user123',
    'x-user-level': 2
  },
  body: JSON.stringify({
    tests: [
      {name: "Vitamin D", value: 18, unit: "ng/mL", reference_range: "30-100 ng/mL"}
    ]
  })
});

const labSummaryData = await labSummaryResponse.json();
console.log(labSummaryData.test_recommendations); // Test önerileri burada!
```

### cURL Example
```bash
# Quiz endpoint
curl -X POST "https://longo-ai.onrender.com/ai/quiz" \
  -H "Content-Type: application/json" \    # ZORUNLU!
  -H "username: longopass" \               # ZORUNLU!
  -H "password: 123456" \                  # ZORUNLU!
  -H "x-user-id: test123" \                # ZORUNLU!
  -H "x-user-level: 2" \                   # Opsiyonel (2=Premium)
  -d '{
    "quiz_data": {
      "age": 30,
      "gender": "female",
      "health_conditions": [],
      "current_supplements": [],
      "goals": ["energy", "immunity"]
    }
  }'

# Premium Plus endpoints (Request body boş!)
# Beslenme önerileri
curl -X POST "https://longo-ai.onrender.com/ai/premium-plus/diet-recommendations" \
  -H "Content-Type: application/json" \    # ZORUNLU!
  -H "username: longopass" \               # ZORUNLU!
  -H "password: 123456" \                  # ZORUNLU!
  -H "x-user-id: test123" \                # ZORUNLU!
  -H "x-user-level: 3" \                   # ZORUNLU! (3=Premium Plus)
  -d '{}'                                  # BOŞ OBJECT!

# Egzersiz önerileri
curl -X POST "https://longo-ai.onrender.com/ai/premium-plus/exercise-recommendations" \
  -H "Content-Type: application/json" \    # ZORUNLU!
  -H "username: longopass" \               # ZORUNLU!
  -H "password: 123456" \                  # ZORUNLU!
  -H "x-user-id: test123" \                # ZORUNLU!
  -H "x-user-level: 3" \                   # ZORUNLU! (3=Premium Plus)
  -d '{}'                                  # BOŞ OBJECT!

# Test önerileri artık Quiz ve Lab Summary endpoint'lerinde entegre!
# Quiz endpoint'inden test önerileri al
curl -X POST "https://longo-ai.onrender.com/ai/quiz" \
  -H "Content-Type: application/json" \
  -H "username: longopass" \
  -H "password: 123456" \
  -H "x-user-id: test123" \
  -H "x-user-level: 2" \
  -d '{
    "quiz_data": {
      "age": 30,
      "gender": "female",
      "health_conditions": [],
      "current_supplements": [],
      "goals": ["energy", "immunity"]
    }
  }'

# Lab Summary endpoint'inden test önerileri al
curl -X POST "https://longo-ai.onrender.com/ai/lab/summary" \
  -H "Content-Type: application/json" \
  -H "username: longopass" \
  -H "password: 123456" \
  -H "x-user-id: test123" \
  -H "x-user-level: 2" \
  -d '{
    "tests": [
      {"name": "Vitamin D", "value": 18, "unit": "ng/mL", "reference_range": "30-100 ng/mL"}
    ]
  }'
```

---

## 🔄 Lab Test Entegrasyonu - Asıl Site Tarafında

### 📋 Genel Yaklaşım

Lab test sonuçları girildikten sonra **otomatik olarak 3 endpoint'e** istek atılmalıdır:

1. **Lab Single** - Her test için ayrı ayrı analiz
2. **Lab Session** - Tüm testler bir seans olarak analiz  
3. **Lab Summary** - Tüm testlerin genel analizi

### 💻 JavaScript Entegrasyon Örneği

```javascript
// Lab test sonuçları girildikten sonra otomatik çalışacak fonksiyon
async function processLabResults(labData) {
  const userId = getCurrentUserId();
  const userLevel = getCurrentUserLevel();
  
  const headers = {
    'Content-Type': 'application/json',
    'username': 'longopass',
    'password': '123456',
    'x-user-id': userId,
    'x-user-level': userLevel  // 1=Free, 2=Premium, 3=Premium Plus
  };

  try {
    // 1. Her test için Lab Single analizi
    for (const test of labData.tests) {
      await fetch('/ai/lab/single', {
        method: 'POST',
        headers: headers,
        body: JSON.stringify({
          test: test
        })
      });
    }

    // 2. Tüm testler için Lab Session analizi
    await fetch('/ai/lab/session', {
      method: 'POST',
      headers: headers,
      body: JSON.stringify({
        session_tests: labData.tests,
        session_date: labData.session_date,
        laboratory: labData.laboratory
      })
    });

    // 3. Tüm testler için Lab Summary analizi
    await fetch('/ai/lab/summary', {
      method: 'POST',
      headers: headers,
      body: JSON.stringify({
        tests: labData.tests,
        total_test_sessions: 1
      })
    });

    console.log('Lab analizleri tamamlandı');
  } catch (error) {
    console.error('Lab analizi hatası:', error);
  }
}

// Kullanım örneği
const labData = {
  tests: [
    {name: "Hemoglobin", value: "15.2", unit: "g/dL", reference_range: "12-16 g/dL"},
    {name: "Glukoz", value: "95", unit: "mg/dL", reference_range: "70-100 mg/dL"},
    {name: "Kolesterol", value: "180", unit: "mg/dL", reference_range: "<200 mg/dL"}
  ],
  session_date: "2024-01-15",
  laboratory: "Acıbadem Lab"
};

// Lab data girildikten sonra otomatik çalıştır
processLabResults(labData);
```

---

## 🧬 Metabolik Yaş Testi (Premium Plus)

### **POST** `/ai/premium-plus/metabolic-age-test`

Metabolik yaş testi sonucunu analiz eder ve longevity raporu oluşturur.

**Sadece Premium Plus kullanıcıları için!**

#### Request Body
```json
{
  "chronological_age": 35,
  "metabolic_age": 26,
  "test_date": "2024-01-15",
  "test_method": "Biyoimpedans analizi",
  "test_notes": "Düşük vücut yağ oranı, yüksek kas kütlesi",
  "additional_data": {
    "body_fat_percentage": 18,
    "muscle_mass": 48,
    "fitness_level": "advanced"
  }
}
```

#### Response
```json
{
  "success": true,
  "message": "Metabolik yaş analizi tamamlandı",
  "chronological_age": 35,
  "metabolic_age": 26,
  "age_difference": -9,
  "biological_age_status": "genç",
  "longevity_score": 88,
  "health_span_prediction": "Ortalamanın üzerinde sağlıklı yaşam süresi",
  "risk_factors": ["Objektif lab verilerinin olmaması"],
  "protective_factors": ["Düşük vücut yağ oranı", "Yüksek kas kütlesi"],
  "longevity_factors": [
    {
      "factor_name": "Vücut kompozisyonu",
      "current_status": "Yaşa göre optimal",
      "impact_score": 9,
      "recommendation": "Kas kütlesini korumaya odaklan"
    }
  ],
  "personalized_recommendations": [
    "Kan tahlilleri ile metabolik risklerin düzenli takibini yap",
    "Uyku, stres ve beslenme alışkanlıklarına dair günlük kayıt tut"
  ],
  "future_health_outlook": "Sağlıklı yaşlanma eğilimi güçlü",
  "analysis_summary": "Metabolik yaşınız kronolojik yaşınızdan 9 yaş daha genç çıkmış. Bu durum, vücut kompozisyonunuzun yaşınıza göre çok iyi durumda olduğunu gösteriyor. Düşük vücut yağ oranı ve yüksek kas kütlesi, sağlıklı yaşlanma için güçlü bir temel oluşturuyor.",
  "disclaimer": "Bu analiz bilgilendirme amaçlıdır. Tıbbi kararlar için doktorunuza danışın."
}
```

#### Özellikler
- **Test sonucu analizi:** Kronolojik vs metabolik yaş karşılaştırması
- **Quiz + Lab entegrasyonu:** Mevcut sağlık verilerini dikkate alır
- **Longevity skoru:** 0-100 arası sağlık puanı
- **Kişiselleştirilmiş öneriler:** Test sonucuna göre özel tavsiyeler
- **Risk faktörleri:** Potansiyel sağlık riskleri
- **Koruyucu faktörler:** Mevcut avantajlar
- **Analiz paragrafı:** Genel değerlendirme ve özet

#### cURL Örneği
```bash
curl -X POST "https://longo-ai.onrender.com/ai/premium-plus/metabolic-age-test" \
  -H "Content-Type: application/json" \
  -H "username: longopass" \
  -H "password: 123456" \
  -H "x-user-id: user123" \
  -H "x-user-level: 3" \
  -d '{
    "chronological_age": 35,
    "metabolic_age": 26,
    "test_date": "2024-01-15",
    "test_method": "Biyoimpedans analizi",
    "test_notes": "Düşük vücut yağ oranı, yüksek kas kütlesi",
    "additional_data": {
      "body_fat_percentage": 18,
      "muscle_mass": 48,
      "fitness_level": "advanced"
    }
  }'
```

---

## 🍎 Premium Plus - Beslenme Önerileri

### **POST** `/ai/premium-plus/diet-recommendations`

**Erişim:** Sadece Premium Plus (x-user-level: 3)

Kullanıcının quiz ve lab verilerine göre kişiselleştirilmiş beslenme önerileri alır.

#### Request Headers
```http
Content-Type: application/json
username: longopass
password: 123456
x-user-id: user123
x-user-level: 3
```

#### Request Body
```json
{}
```
*Not: Body boş gönderilir. Quiz ve lab verileri otomatik olarak kullanıcı ID'sine göre çekilir.*

#### Response Format
```json
{
  "success": true,
  "message": "Beslenme önerileri hazırlandı",
  "recommendations": {
    "general_advice": "Kullanıcının durumuna göre genel beslenme önerisi paragrafı",
    "daily_calories": {
      "min": 2000,
      "max": 2200,
      "unit": "kcal"
    },
    "macro_distribution": {
      "carbohydrate": {
        "percentage": 40,
        "label": "Karbonhidrat"
      },
      "protein": {
        "percentage": 30,
        "label": "Protein"
      },
      "fat": {
        "percentage": 30,
        "label": "Yağ"
      }
    },
    "recommended_supplements": [
      {
        "name": "Vitamin D",
        "dosage": "2000 IU",
        "note": "Güneş ışığı eksikliği için"
      },
      {
        "name": "Omega-3",
        "dosage": "Balık yağı veya alg bazlı",
        "note": "Kalp sağlığı için"
      }
    ],
    "hydration": {
      "daily_target": "2.5-3L",
      "label": "Günlük Su Tüketimi",
      "tips": [
        "Sabah kalktığınızda 1-2 bardak su",
        "Her öğün öncesi 1 bardak su",
        "Egzersiz sonrası ekstra 500 ml",
        "İdrar rengi açık sarı olmalı"
      ]
    },
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
  },
  "disclaimer": "Bu öneriler bilgilendirme amaçlıdır. Tıbbi kararlar için doktorunuza danışın."
}
```

#### cURL Örneği
```bash
curl -X POST "https://longo-ai.onrender.com/ai/premium-plus/diet-recommendations" \
  -H "Content-Type: application/json" \
  -H "username: longopass" \
  -H "password: 123456" \
  -H "x-user-id: user123" \
  -H "x-user-level: 3" \
  -d '{}'
```

#### Özellikler
- **Otomatik veri çekme:** Quiz ve lab sonuçları kullanıcı ID'sine göre otomatik alınır
- **Kalori hesaplama:** Kişiye özel günlük kalori aralığı
- **Makro dağılımı:** Yüzde bazlı karbonhidrat/protein/yağ oranları
- **Supplement önerileri:** Eksikliklere göre takviye önerileri
- **Hidrasyon rehberi:** Detaylı su tüketimi ipuçları
- **Kaçınılacaklar/Önerilecekler:** Beslenme alışkanlıkları listeleri

---

## 🏃 Premium Plus - Egzersiz Önerileri

### **POST** `/ai/premium-plus/exercise-recommendations`

**Erişim:** Sadece Premium Plus (x-user-level: 3)

Kullanıcının quiz ve lab verilerine göre kişiselleştirilmiş egzersiz ve yaşam tarzı önerileri alır.

#### Request Headers
```http
Content-Type: application/json
username: longopass
password: 123456
x-user-id: user123
x-user-level: 3
```

#### Request Body
```json
{}
```
*Not: Body boş gönderilir. Quiz ve lab verileri otomatik olarak kullanıcı ID'sine göre çekilir.*

#### Response Format
```json
{
  "success": true,
  "message": "Egzersiz önerileri hazırlandı",
  "recommendations": {
    "general_advice": "Kullanıcının durumuna göre genel egzersiz önerisi paragrafı",
    "lifestyle_tips": {
      "sleep_recovery": {
        "title": "Uyku ve Toparlanma",
        "target": "7-9 saat kaliteli uyku",
        "tips": [
          "Aynı saatlerde yatıp kalkın",
          "Yatak odası serin, karanlık ve sessiz olmalı",
          "Yatmadan 2 saat önce ekran kullanımını azaltın"
        ]
      },
      "daily_activity": {
        "title": "Günlük Aktivite",
        "tips": [
          "Günde en az 8000-10000 adım hedefleyin",
          "Oturma süresini her saat bölün (5 dk hareket)",
          "Merdiven kullanmayı tercih edin",
          "Parkta daha uzağa park edin"
        ]
      },
      "stress_management": {
        "title": "Stres Yönetimi",
        "tips": [
          "Günlük 10 dakika meditasyon veya nefes egzersizi",
          "Doğada vakit geçirin",
          "Hobilerinize zaman ayırın",
          "Sosyal bağlantılarınızı güçlendirin"
        ]
      },
      "hydration": {
        "title": "Hidrasyon",
        "tips": [
          "Günde en az 2-3 litre su için",
          "Antrenman sırasında sık sık su için",
          "Kafein alımını dengeleyin"
        ]
      },
      "consistency": {
        "title": "Düzenlilik",
        "tips": [
          "Egzersiz rutininize sadık kalın",
          "Kaçırılan günleri telafi etmeye çalışmayın",
          "İlerlemenizi kaydedin",
          "Haftalık hedefler belirleyin"
        ]
      },
      "body_awareness": {
        "title": "Vücut Dinleme",
        "tips": [
          "Aşırı yorgunluk hissediyorsanaz ekstra dinlenme alın",
          "Ağrı ve rahatsızlıkları ciddiye alın",
          "Kademeli ilerleme prensibine uyun",
          "Overtraining belirtilerine dikkat edin"
        ]
      },
      "motivation": {
        "title": "Motivasyon İpuçları",
        "tips": [
          "Gerçekçi hedefler belirleyin",
          "İlerlemenizi fotoğraflarla kaydedin",
          "Egzersiz arkadaşı bulun",
          "Başarılarınızı kutlayın",
          "Çeşitlilik katın, sıkılmayın"
        ]
      }
    }
  },
  "disclaimer": "Bu öneriler bilgilendirme amaçlıdır. Tıbbi kararlar için doktorunuza danışın."
}
```

#### cURL Örneği
```bash
curl -X POST "https://longo-ai.onrender.com/ai/premium-plus/exercise-recommendations" \
  -H "Content-Type: application/json" \
  -H "username: longopass" \
  -H "password: 123456" \
  -H "x-user-id: user123" \
  -H "x-user-level: 3" \
  -d '{}'
```

#### Özellikler
- **Otomatik veri çekme:** Quiz ve lab sonuçları kullanıcı ID'sine göre otomatik alınır
- **Yaşam tarzı kategorileri:** 7 farklı kategori (uyku, aktivite, stres, su, düzenlilik, vücut dinleme, motivasyon)
- **Emoji destekli:** 😴, 🚶, 🧘, 💧, 📅, ❤️, 💡 ile frontend'de görsel gösterim
- **Kişiselleştirilmiş:** Kullanıcının yaşı, hedefi ve lab sonuçlarına göre özel ipuçları

---

## 🧬 Premium Plus - Metabolik Yaş ve Longevity Raporu

### **POST** `/ai/premium-plus/metabolic-age-test`

**Erişim:** Sadece Premium Plus (x-user-level: 3)

Kullanıcının metabolik yaş test sonucunu analiz ederek detaylı longevity raporu oluşturur.

#### Request Headers
```http
Content-Type: application/json
username: longopass
password: 123456
x-user-id: user123
x-user-level: 3
```

#### Request Body
```json
{
  "chronological_age": 40,
  "metabolic_age": 35,
  "gender": "male",
  "height": 175,
  "weight": 80,
  "body_fat_percentage": 20,
  "resting_heart_rate": 62,
  "blood_pressure_systolic": 120,
  "blood_pressure_diastolic": 78,
  "sleep_hours": 7,
  "stress_level": 5,
  "exercise_frequency": 4,
  "smoking": false,
  "alcohol_consumption": 2,
  "diet_quality": 7,
  "family_history_diabetes": false,
  "family_history_heart_disease": false,
  "test_date": "2024-01-15",
  "test_method": "Biyoimpedans analizi",
  "test_notes": "Düzenli egzersiz yapıyor",
  "additional_data": {
    "vo2_max": 45,
    "flexibility_score": 8
  }
}
```

#### Response Format
```json
{
  "success": true,
  "message": "Longevity raporu hazırlandı",
  "report": {
    "longevity_report": {
      "biological_age": {
        "value": 35,
        "real_age": 40,
        "difference": -5,
        "status": "5 yaş daha genç"
      },
      "health_score": {
        "value": 85,
        "label": "Çok İyi",
        "percentile": "Üst %15'te"
      },
      "longopass_development_score": {
        "value": 78,
        "note": "İlk ve son kapsamlı test panelleri karşılaştırılarak hesaplandı"
      },
      "metabolic_age": {
        "value": 35,
        "status": "Harika"
      }
    },
    "detailed_analysis": {
      "cardiovascular_health": {
        "status": "İyi",
        "metrics": [
          {"name": "VO2 Max", "value": "42 ml/kg/dk", "status": "✓"},
          {"name": "Dinlenme Nabzı", "value": "62 bpm", "status": "✓"},
          {"name": "Kan Basıncı", "value": "120/78 mmHg", "status": "✓"}
        ]
      },
      "metabolic_health": {
        "status": "Mükemmel",
        "metrics": [
          {"name": "HbA1c", "value": "5.0%", "status": "✓"},
          {"name": "Açlık Glukozu", "value": "88 mg/dL", "status": "✓"}
        ]
      },
      "inflammation_profile": {
        "status": "İyi",
        "metrics": [
          {"name": "hs-CRP", "value": "0.8 mg/L", "status": "✓"},
          {"name": "Homosistein", "value": "8.5 μmol/L", "status": "✓"}
        ]
      },
      "hormonal_balance": {
        "status": "İyi",
        "metrics": [
          {"name": "Tiroid (TSH)", "value": "2.0 mIU/L", "status": "✓"},
          {"name": "Vitamin D", "value": "38 ng/mL", "status": "✓"}
        ]
      },
      "cognitive_health": {
        "status": "İyi",
        "metrics": [
          {"name": "B12 Vitamini", "value": "380 pg/mL", "status": "✓"},
          {"name": "Omega-3 İndeksi", "value": "6.5%", "status": "✓"}
        ]
      },
      "body_composition": {
        "status": "İyi",
        "metrics": [
          {"name": "BMI", "value": "26.1", "status": "✓"},
          {"name": "Vücut Yağ Oranı", "value": "20%", "status": "✓"},
          {"name": "Kas Kütlesi", "value": "İdeal", "status": "✓"}
        ]
      }
    },
    "personalized_improvements": [
      {
        "category": "Vitamin D ve Omega-3",
        "recommendation": "Güneş maruziyetini artır veya D3+K2 takviyesi değerlendir",
        "priority": "high"
      },
      {
        "category": "Kardiyovasküler dayanıklılık",
        "recommendation": "Haftada 3 gün 30-40 dk orta tempolu kardiyo ile VO2 Max'i artır",
        "priority": "medium"
      }
    ]
  },
  "disclaimer": "Bu analiz bilgilendirme amaçlıdır. Tıbbi kararlar için doktorunuza danışın."
}
```

#### cURL Örneği
```bash
curl -X POST "https://longo-ai.onrender.com/ai/premium-plus/metabolic-age-test" \
  -H "Content-Type: application/json" \
  -H "username: longopass" \
  -H "password: 123456" \
  -H "x-user-id: user123" \
  -H "x-user-level: 3" \
  -d '{
    "chronological_age": 40,
    "metabolic_age": 35,
    "gender": "male",
    "height": 175,
    "weight": 80,
    "body_fat_percentage": 20,
    "resting_heart_rate": 62,
    "blood_pressure_systolic": 120,
    "blood_pressure_diastolic": 78,
    "sleep_hours": 7,
    "stress_level": 5,
    "exercise_frequency": 4,
    "smoking": false,
    "alcohol_consumption": 2,
    "diet_quality": 7,
    "family_history_diabetes": false,
    "family_history_heart_disease": false
  }'
```

#### Özellikler
- **Longevity skoru:** Biyolojik yaş, sağlık skoru, metabolik yaş değerlendirmesi
- **Longopass gelişim skoru:** En az 2 kapsamlı test paneli varsa ilk ve son testler karşılaştırılır (0-100 arası)
- **6 kategori analiz:** Kardiyovasküler, Metabolik, Enflamasyon, Hormonal, Bilişsel, Vücut kompozisyonu
- **Metrikler:** Her kategori için detaylı ölçümler (✓ normal, ⚠️ dikkat)
- **Kişiselleştirilmiş iyileştirmeler:** Öncelik sıralamalı öneriler (high/medium/low)
- **Quiz + Lab entegrasyonu:** Mevcut sağlık verileri otomatik dahil edilir

#### Longopass Gelişim Skoru Nasıl Hesaplanır?
- **0 puan:** Henüz en az 2 kapsamlı test paneli yapılmamış
- **1-100 puan:** İlk ve son kapsamlı test panelleri karşılaştırılarak hesaplanır
  - Değerlerde iyileşme varsa → Yüksek skor (70-100)
  - Değerlerde kötüleşme varsa → Düşük skor (0-50)
  - Karışık sonuçlar → Orta skor (50-70)

---

