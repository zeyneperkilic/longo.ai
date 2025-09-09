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
  "genel_saglik_durumu": "Genel olarak kan değerlerin normal referans aralıklarında. Hemoglobin seviyen sağlıklı, bu da kansızlık bulgusu olmadığını gösteriyor. Glukoz düzeyin ise normal sınırlar içinde, yani diyabet riski açısından pozitif bir işaret.",
  "genel_durum": "İki seans sonuçlarını kıyasladığımda hemoglobin değerlerin (13.8 – 14.2 g/dL) stabil seyretmiş. Glukozun normal aralıkta (95 – 98 mg/dL) sabit. Ancak total kolesterol, önceki testlerde normal mi değil mi bilgimiz yok, ama şu anki 220 mg/dL yüksek çıkmış ve takibi önemli.",
  "oneriler": [
    "Doymuş yağlardan ve trans yağlardan uzak dur, daha çok zeytinyağı, avokado ve ceviz gibi sağlıklı yağlara yönel.",
    "Her gün en az 30 dakika tempolu yürüyüş veya benzeri aerobik egzersiz yap.",
    "Bol sebze, tam tahıl ve lif tüket; kırmızı et ve işlenmiş gıdaları azalt.",
    "Balık (özellikle somon, sardalya) en az haftada 2 kez tüketmeye çalış.",
    "Kan lipitlerini kontrol ettirmek için düzenli aralıklarla tekrar test yaptır."
  ],
  "urun_onerileri": [
    {
      "name": "Omega-3 Yağ Asitleri (Balık Yağı)",
      "description": "Kolesterolü dengelemeye, kalp ve damar sağlığını desteklemeye yardımcı olur.",
      "daily_dose": "1000-2000 mg EPA+DHA",
      "benefits": ["Triglisitleri ve kötü kolesterolü (LDL) düşürmeye destek olabilir", "Kalp sağlığını korur", "Beyin fonksiyonlarını destekler"],
      "warnings": ["Kan sulandırıcı ilaç kullanıyorsan doktora danışmalı"],
      "priority": "high"
    },
    {
      "name": "Koenzim Q10 (CoQ10)",
      "description": "Kalp-damar sağlığı ve hücresel enerji üretimi için faydalıdır.",
      "daily_dose": "100-200 mg",
      "benefits": ["Kalp kası sağlığını destekler", "Kolesterol ilaçlarının yan etkilerini azaltabilir", "Enerji seviyelerini artırır"],
      "warnings": ["Kan basıncı ilaçlarıyla etkileşebilir"],
      "priority": "high"
    },
    {
      "name": "Kurkumin (Zerdeçaldan)",
      "description": "Anti-inflamatuar etkisiyle damar sağlığını ve kolesterol metabolizmasını destekler.",
      "daily_dose": "500-1000 mg",
      "benefits": ["Kolesterol dengesine katkıda bulunabilir", "Antioksidan ve antiinflamatuar etki sağlar", "Karaciğer sağlığını destekler"],
      "warnings": ["Safra kesesi taşı olanlar dikkat etmeli"],
      "priority": "medium"
    },
    {
      "name": "Probiyotik",
      "description": "Bağırsak mikrobiyotasını düzenleyerek kolesterol seviyelerine dolaylı katkı sağlar.",
      "daily_dose": "CFA sayısı: 1-10 milyar",
      "benefits": ["Sindirim sağlığını iyileştirir", "Bağırsakta kolesterol metabolizmasını destekler", "Bağışıklığı güçlendirir"],
      "warnings": ["Bağışıklık yetmezliği olanlarda doktor kontrolü gerekir"],
      "priority": "medium"
    },
    {
      "name": "Selenyum",
      "description": "Antioksidan savunmayı güçlendirir ve kalp-damar sağlığına destek olur.",
      "daily_dose": "50-100 mcg",
      "benefits": ["Oksidatif stresi azaltır", "Tiroid fonksiyonlarını destekler", "Bağışıklığı güçlendirir"],
      "warnings": ["Yüksek dozda toksik etki gösterebilir"],
      "priority": "low"
    }
  ],
  "disclaimer": "Bu içerik bilgilendirme amaçlıdır; tıbbi tanı/tedavi için hekiminize başvurun.",
  "test_count": 2,
  "overall_status": "analiz_tamamlandı"
}
```

#### Strateji
- **5 supplement** (lab sonuçlarına göre)
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
  "session_tests": [
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
    "laboratory": "Acıbadem Lab",
    "session_date": "2024-01-15",
    "total_tests": 1
  },
  "general_assessment": {
    "clinical_meaning": "Bu laboratuvar seansında yalnızca D Vitamini testi yapılmış. Ölçülen değer 15 ng/mL olup, referans aralığı olan 30-100 ng/mL'nin altında. Bu sonuç D vitamini eksikliğini düşündürmektedir. D vitamini; kemik sağlığı, kas fonksiyonları, bağışıklık sistemi ve metabolik süreçler için oldukça önemlidir. Eksikliği uzun vadede kemik erimesi, kas güçsüzlüğü ve bağışıklık sorunlarına yol açabilir.",
    "overall_health_status": "D Vitamini seviyesi düşük bulunmuştur (eksiklik)."
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
    "Kalsiyum ve D vitamini içeren doğal besinleri (yağlı balıklar, yumurta sarısı, süt ürünleri) beslenmene ekle.",
    "Kapalı mekanlarda uzun süre kalmaktan kaçın, mümkün olduğunda açık havada aktif ol.",
    "D vitamini seviyesinin birkaç ay içinde yeniden ölçülmesi faydalı olacaktır.",
    "Düşük değerlerin kemik sağlığını etkileyip etkilemediğini görmek için kalsiyum ve fosfor gibi ek testler yapılabilir.",
    "D vitamini eksikliğinin nedeni ve tedavi yaklaşımı için bir hekim ile görüşmen gerekir."
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
  "title": "Test Sonucu Yorumu",
  "test_name": "D Vitamini (25-OH) Sonucu Değerlendirmesi",
  "last_result": "Son Test Sonucunuz: 15 ng/mL (Düşük)",
  "reference_range": "Referans Aralığı: 30-100 ng/mL",
  "test_analysis": "D vitamini düzeyin 15 ng/mL çıkmış ve bu değer referans aralığının (30-100 ng/mL) oldukça altında. 20 ng/mL altındaki sonuçlar genellikle 'eksiklik' düzeyi olarak kabul edilir. Bu durumda kemik sağlığın üzerinde olumsuz etkiler (örneğin osteomalazi riski, kemik yoğunluğunda azalma) oluşturabilir. Ayrıca bağışıklık ve metabolik fonksiyonlarda da rol oynadığı için düşük seviyeler genel sağlık açısından önemli olabilir. Bu test kategorisi vitamin ve mineral düzeylerini gösteren biyokimyasal parametreler arasında yer alır. Elimizde sadece 2024-01-15 tarihli tek bir ölçüm var, bu nedenle trend analizi yapılamıyor. Gelecek ölçümlerde bu değerin yükselip yükselmediği veya daha da düşüp düşmediği izlenmeli. Düzenli aralıklarla aynı laboratuvarda yapılacak tekrar testleri, gidişatı görmek açısından faydalı olur.",
  "disclaimer": "Bu yorum sadece bilgilendirme amaçlıdır. Kesin tanı ve tedavi için mutlaka doktorunuza başvurunuz."
}
```

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



