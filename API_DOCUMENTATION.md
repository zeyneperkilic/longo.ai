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
x-user-level: 0|1|2|3           # Kullanıcı seviyesi (opsiyonel, default: 0)
```

**Plan Mapping:**
- `0` veya `1` → **Free** (10 soru limiti)
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
  "disclaimer": "Bu içerik bilgilendirme amaçlıdır; tıbbi tanı/tedavi için hekiminize başvurun."
}
```

#### Strateji
- **4 DEFAULT + 3 PERSONALIZED = 7 supplement**
- **DEFAULT**: D Vitamini, Omega-3, Magnezyum, B12
- **PERSONALIZED**: Quiz cevaplarına göre (energy hedefi için Probiyotik, CoQ10, Kurkumin)

---

## 🧬 Lab Summary Endpoint

### **POST** `/ai/lab/summary`

Laboratuvar test sonuçlarının genel analizi ve supplement önerileri.

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

Tek bir laboratuvar seansının analizi (supplement önerisi YOK).

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

Tek bir test sonucunun detaylı analizi (supplement önerisi YOK).

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

## 🏆 Premium Plus Endpoint

### **POST** `/ai/premium-plus/lifestyle-recommendations`

Premium Plus kullanıcıları için kişiselleştirilmiş beslenme, spor ve egzersiz önerileri. Kullanıcının quiz ve lab verilerini kullanır.

#### Request Body
```json
{}
```
**Not:** Request body boş olmalı. Kullanıcı verileri header'lardan ve AI hafızasından alınır.

#### Response
```json
{
  "status": "success",
  "nutrition_plan": "Günlük beslenmende dengeli makro dağılımını hedefle: %40 kompleks karbonhidrat (tam tahıllar, kinoa, yulaf), %30 kaliteli protein (balık, tavuk, baklagiller, yumurta), %30 sağlıklı yağ (zeytinyağı, avokado, fındık). Vitamin/mineral desteği için koyu yeşil yapraklı sebzeler (ıspanak, brokoli), demir açısından kırmızı et veya mercimek, C vitamini için turunçgiller ve biber ekle.",
  "exercise_plan": "Haftada en az 4 gün egzersiz: 2 gün kuvvet antrenmanı (tam vücut odaklı: squat, plank, şınav, direnç lastiği çalışmaları), 2 gün kardiyo (tempolu yürüyüş, bisiklet, yüzme). Başlangıçta 30-40 dk yeterli; kondisyon arttıkça süreyi 45-60 dk'ya çıkar.",
  "lifestyle_tips": "Günde en az 2-2.5 litre su iç, özellikle antrenman günlerinde extra 500 ml ekle. Uyku kalitesini artırmak için her gün aynı saatte yat-kalk düzeni oluştur, 7-8 saat uyumayı hedefle. Stres yönetimi için nefes egzersizi veya kısa meditasyon önerilir.",
  "quiz_count": 1,
  "lab_count": 1
}
```

#### Özellik
- **AI Hafızası**: Quiz ve lab sonuçlarını hatırlar
- **Kişiselleştirilmiş Öneriler**: Geçmiş verileri kullanarak beslenme, spor ve egzersiz planı verir
- **3 Ayrı Bölüm**: `nutrition_plan`, `exercise_plan`, `lifestyle_tips` olarak ayrılmış
- **Premium Plus Only**: Sadece `x-user-level: 3` kullanıcıları erişebilir
- **Temiz Response**: User context dahil edilmez, sadece öneriler

---

## 🧪 Test Recommendations Endpoint

### **POST** `/ai/test-recommendations`

Premium ve Premium Plus kullanıcıları için kişiselleştirilmiş test önerileri. Kullanıcının quiz ve lab verilerini analiz ederek **sadece anormal değerler için** en uygun testleri önerir.

#### Request Body
```json
{
  "user_analysis": true,
  "exclude_taken_tests": true,
  "max_recommendations": 10
}
```

#### Request Parameters
- `user_analysis` (boolean): Kullanıcı verilerini analiz et (zorunlu: true)
- `exclude_taken_tests` (boolean): Daha önce yapılan testleri hariç tut (zorunlu: true)
- `max_recommendations` (integer): Maksimum öneri sayısı (1-10 arası, default: 3)

#### Özellikler
- **Akıllı Analiz**: Sadece anormal/düşük/yüksek lab değerleri için test önerir
- **Kişiselleştirilmiş**: Kullanıcının mevcut değerlerini referans alarak açıklama yapar
- **Gereksiz Test Önleme**: Normal değerlere "kontrol amaçlı" test önermez
- **Maksimum 10 Test**: Boş yere test önermez, sadece gerekli olanları önerir

#### Response
```json
{
  "title": "Test Önerileri",
  "recommended_tests": [
    {
      "test_name": "HbA1c (Glikozillenmiş Hemoglobin)",
      "reason": "Glukozunuz 110 mg/dL (referans: 70-100) ile hafif yüksek. Bu, insülin direnci veya prediyabet riski göstergesi olabilir. HbA1c testi, son 2-3 aylık ortalama kan şekeri düzeyinizi değerlendirmeye yardımcı olur.",
      "benefit": "Diyabet veya prediyabet riskinizi erken tespit ederek, yaşam tarzı değişiklikleri veya tedaviye erken başlamanıza olanak tanır."
    },
    {
      "test_name": "Serum Demir, Ferritin ve Total Demir Bağlama Kapasitesi (TIBC)",
      "reason": "Hemoglobininiz 11.8 g/dL (referans: 12-16) ile hafif düşük. Bu, demir eksikliği anemisini düşündürebilir. Ferritin ve demir testleri vücuttaki demir depolarını değerlendirir.",
      "benefit": "Demir eksikliğiniz olup olmadığını netleştirerek doğru tedavi (ör. demir takviyesi) planlanmasına yardımcı olur."
    },
    {
      "test_name": "Vitamin B12 ve Folat",
      "reason": "Hemoglobininiz düşük (11.8 g/dL). Demir dışında B12 ve folat eksiklikleri de kansızlığa sebep olabilir.",
      "benefit": "Aneminin nedeni B12/Folat eksikliğine bağlıysa doğru tedavi planlanır."
    }
  ],
  "analysis_summary": "Kişiselleştirilmiş analiz tamamlandı.",
  "disclaimer": "Bu öneriler bilgilendirme amaçlıdır. Test yaptırmadan önce doktorunuza danışın."
}
```

#### Özellik
- **AI Tabanlı**: Kullanıcının quiz ve lab verilerini analiz eder
- **Akıllı Analiz**: Sadece anormal değerler için test önerir
- **Kişiselleştirilmiş**: Mevcut değerleri referans alarak açıklama yapar
- **Gereksiz Test Önleme**: Normal değerlere "kontrol amaçlı" test önermez
- **Akıllı Filtreleme**: Daha önce yapılan testleri otomatik olarak hariç tutar
- **Tıbbi Mantık**: Test sonuçlarına göre ilgili testleri önerir
- **Premium Only**: Sadece `x-user-level: 2` (Premium) ve `x-user-level: 3` (Premium Plus) kullanıcıları erişebilir

#### Strateji
- **Quiz Verisi**: Yaş, cinsiyet, hastalıklar, hedefler analiz edilir
- **Lab Verisi**: Mevcut test sonuçları değerlendirilir
- **AI Analizi**: Tüm veriler AI tarafından analiz edilerek en uygun testler belirlenir
- **Test Listesi**: 18 farklı test kategorisinden öneriler yapılır

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

// Premium Plus endpoint (Request body boş!)
const premiumResponse = await fetch('https://longo-ai.onrender.com/ai/premium-plus/lifestyle-recommendations', {
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

const premiumData = await premiumResponse.json();
console.log(premiumData.nutrition_plan);
console.log(premiumData.exercise_plan);
console.log(premiumData.lifestyle_tips);

// Test Recommendations endpoint (Premium ve Premium Plus)
const testRecResponse = await fetch('https://longo-ai.onrender.com/ai/test-recommendations', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',  // ZORUNLU!
    'username': 'longopass',             // ZORUNLU!
    'password': '123456',                // ZORUNLU!
    'x-user-id': 'user123',              // ZORUNLU!
    'x-user-level': 2                    // ZORUNLU! (2=Premium, 3=Premium Plus)
  },
  body: JSON.stringify({
    user_analysis: true,
    exclude_taken_tests: true,
    max_recommendations: 10
  })
});

const testRecData = await testRecResponse.json();
console.log(testRecData.recommended_tests);
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

# Premium Plus endpoint (Request body boş!)
curl -X POST "https://longo-ai.onrender.com/ai/premium-plus/lifestyle-recommendations" \
  -H "Content-Type: application/json" \    # ZORUNLU!
  -H "username: longopass" \               # ZORUNLU!
  -H "password: 123456" \                  # ZORUNLU!
  -H "x-user-id: test123" \                # ZORUNLU!
  -H "x-user-level: 3" \                   # ZORUNLU! (3=Premium Plus)
  -d '{}'                                  # BOŞ OBJECT!

# Test Recommendations endpoint (Premium ve Premium Plus)
curl -X POST "https://longo-ai.onrender.com/ai/test-recommendations" \
  -H "Content-Type: application/json" \    # ZORUNLU!
  -H "username: longopass" \               # ZORUNLU!
  -H "password: 123456" \                  # ZORUNLU!
  -H "x-user-id: test123" \                # ZORUNLU!
  -H "x-user-level: 2" \                   # ZORUNLU! (2=Premium, 3=Premium Plus)
  -d '{
    "user_analysis": true,
    "exclude_taken_tests": true,
    "max_recommendations": 10
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
    'x-user-level': userLevel  // 0=Free, 1=Free, 2=Premium, 3=Premium Plus
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




