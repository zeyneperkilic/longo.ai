import os
from dotenv import load_dotenv

load_dotenv()

# API Configuration
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
if not OPENROUTER_API_KEY:
    raise ValueError("OPENROUTER_API_KEY environment variable is required")

OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")

# Authentication
AUTH_USERNAME = os.getenv("AUTH_USERNAME", "longopass")
AUTH_PASSWORD = os.getenv("AUTH_PASSWORD", "change_this_password")

# ASIL ÜCRETLİ MODELLER (Production için - şu an aktif)
PARALLEL_MODELS = [
    "openai/gpt-5-chat:online"
]



PARALLEL_TIMEOUT_MS = 15000  # 15 saniye (ücretli modeller için - hızlı)
CHAT_HISTORY_MAX = 20
FREE_ANALYZE_LIMIT = 1

HEALTH_MODE = "topic"

# Security: CORS origins from environment
ALLOWED_ORIGINS_STR = os.getenv("ALLOWED_ORIGINS", "*")
if ALLOWED_ORIGINS_STR == "*":
    ALLOWED_ORIGINS = ["*"]
else:
    ALLOWED_ORIGINS = [origin.strip() for origin in ALLOWED_ORIGINS_STR.split(",")]

LOG_PROVIDER_RAW = True
RETENTION_DAYS = 365

# Safety and rate limits
PRESCRIPTION_BLOCK = True
# DAILY_CHAT_LIMIT = 100  # KALDIRILDI - Gereksiz

# Context limits for production
MAX_SUPPLEMENTS_IN_CONTEXT = 7  # Maximum supplements to store in context
MAX_PRIORITY_SUPPLEMENTS = 5    # Maximum priority supplements to store
MAX_LAB_TESTS_IN_CONTEXT = 5   # Maximum lab tests to store in context



MODERATION_MODEL = "google/gemini-2.5-flash"

MODERATION_TIMEOUT_MS = 10000  # 10 saniye (ücretli modeller için - hızlı)

# Magic Numbers - Config'e taşındı
XML_REQUEST_TIMEOUT = 10  # XML request timeout saniye
FREE_QUESTION_LIMIT = 10  # Free kullanıcı günlük soru limiti
FREE_SESSION_TIMEOUT_SECONDS = 7200  # Free session timeout (2 saat)
CHAT_HISTORY_LIMIT = 10  # Chat history limiti
USER_ANALYSES_LIMIT = 5  # User analyses limiti
QUIZ_LAB_MESSAGES_LIMIT = 5  # Quiz/lab messages limiti
AI_MESSAGES_LIMIT = 50  # AI messages limiti
AI_MESSAGES_LIMIT_LARGE = 100  # Büyük AI messages limiti
LAB_MESSAGES_LIMIT = 20  # Lab messages limiti
QUIZ_LAB_ANALYSES_LIMIT = 3  # Quiz/lab analyses limiti
DEBUG_AI_MESSAGES_LIMIT = 10  # Debug AI messages limiti
MILLISECOND_MULTIPLIER = 1000  # Millisecond çarpanı
MIN_LAB_TESTS_FOR_COMPARISON = 2  # Lab test karşılaştırması için minimum test sayısı

# XML Supplement Listesi - Tüm endpoint'lerde kullanılacak
SUPPLEMENTS_LIST = [
    {"id": 247, "name": "Zeaksantin", "category": "Longevity"},
    {"id": 246, "name": "Viniferin", "category": "Longevity"},
    {"id": 245, "name": "Vanadyum", "category": "Longevity"},
    {"id": 244, "name": "Ürolitin A", "category": "Longevity"},
    {"id": 243, "name": "Triphala", "category": "Longevity"},
    {"id": 242, "name": "TMG (Trimetilglisin)", "category": "Longevity"},
    {"id": 241, "name": "Taurin", "category": "Longevity"},
    {"id": 240, "name": "Spermidin", "category": "Longevity"},
    {"id": 239, "name": "Silika", "category": "Longevity"},
    {"id": 238, "name": "Şilajit", "category": "Longevity"},
    {"id": 237, "name": "Selenyum", "category": "Longevity"},
    {"id": 236, "name": "Resveratrol", "category": "Longevity"},
    {"id": 235, "name": "Pterostilben", "category": "Longevity"},
    {"id": 234, "name": "NMN / NR", "category": "Longevity"},
    {"id": 233, "name": "N-Asetil Sistein (NAC)", "category": "Longevity"},
    {"id": 232, "name": "NAD+", "category": "Longevity"},
    {"id": 231, "name": "MSM (Metilsülfonilmetan)", "category": "Longevity"},
    {"id": 230, "name": "Melatonin", "category": "Longevity"},
    {"id": 229, "name": "Lutein-Zeaksantin", "category": "Longevity"},
    {"id": 228, "name": "L-Sistein", "category": "Longevity"},
    {"id": 227, "name": "L-Karnitin", "category": "Longevity"},
    {"id": 226, "name": "Likopen", "category": "Longevity"},
    {"id": 225, "name": "L-Ergotiyonin", "category": "Longevity"},
    {"id": 224, "name": "Kurkumin (Zerdeçaldan)", "category": "Longevity"},
    {"id": 223, "name": "Kollajen Peptit", "category": "Longevity"},
    {"id": 222, "name": "Kolin", "category": "Longevity"},
    {"id": 221, "name": "Koenzim Q10 (CoQ10)", "category": "Longevity"},
    {"id": 220, "name": "Kersetin", "category": "Longevity"},
    {"id": 219, "name": "Karotenoid", "category": "Longevity"},
    {"id": 218, "name": "Karnosin", "category": "Longevity"},
    {"id": 217, "name": "Honokiol", "category": "Longevity"},
    {"id": 216, "name": "Hiyalüronik Asit", "category": "Longevity"},
    {"id": 215, "name": "Glisin", "category": "Longevity"},
    {"id": 214, "name": "Ginseng", "category": "Longevity"},
    {"id": 213, "name": "Ginkgo Biloba", "category": "Longevity"},
    {"id": 212, "name": "Fisetin", "category": "Longevity"},
    {"id": 211, "name": "Bromelain", "category": "Longevity"},
    {"id": 210, "name": "Beta-Glukan", "category": "Longevity"},
    {"id": 209, "name": "Berberin", "category": "Longevity"},
    {"id": 208, "name": "Bacopa Monnieri", "category": "Longevity"},
    {"id": 207, "name": "Astaksantin", "category": "Longevity"},
    {"id": 206, "name": "Ashwagandha", "category": "Longevity"},
    {"id": 205, "name": "Ashitaba Ekstraktı", "category": "Longevity"},
    {"id": 204, "name": "Apigenin", "category": "Longevity"},
    {"id": 203, "name": "Alfa Lipoik Asit", "category": "Longevity"},
    {"id": 181, "name": "Probiyotik", "category": "Günlük Takviyeler"},
    {"id": 180, "name": "Potasyum", "category": "Günlük Takviyeler"},
    {"id": 179, "name": "Omega-3 Yağ Asitleri (Balık Yağı)", "category": "Günlük Takviyeler"},
    {"id": 177, "name": "Molibden", "category": "Günlük Takviyeler"},
    {"id": 176, "name": "Magnezyum", "category": "Günlük Takviyeler"},
    {"id": 175, "name": "Lutein", "category": "Günlük Takviyeler"},
    {"id": 174, "name": "Krom", "category": "Günlük Takviyeler"},
    {"id": 173, "name": "Kondroitin", "category": "Günlük Takviyeler"},
    {"id": 172, "name": "Kalsiyum", "category": "Günlük Takviyeler"},
    {"id": 171, "name": "K2 Vitamini", "category": "Günlük Takviyeler"},
    {"id": 170, "name": "İyot", "category": "Günlük Takviyeler"},
    {"id": 169, "name": "Glukozamin", "category": "Günlük Takviyeler"},
    {"id": 168, "name": "Fosfor", "category": "Günlük Takviyeler"},
    {"id": 248, "name": "Erkekler için Günlük Temel Takviye", "category": "Multi Vitaminler"},
    {"id": 249, "name": "Erkekler için Total Sağlık Multivitamini", "category": "Multi Vitaminler"},
    {"id": 250, "name": "Erkekler için Canlılık Kompleksi", "category": "Multi Vitaminler"},
    {"id": 251, "name": "Kadınlar için Sağlıklı Yaşam Multivitamini", "category": "Multi Vitaminler"},
    {"id": 252, "name": "Kadınlar için Aktif Yaşam Multivitamini", "category": "Multi Vitaminler"},
    {"id": 253, "name": "Kadınlar için Komple Multivitamin", "category": "Multi Vitaminler"},
    {"id": 254, "name": "50+ için Günlük Destek", "category": "Multi Vitaminler"},
    {"id": 255, "name": "50+ Komple Sağlık Multivitamini", "category": "Multi Vitaminler"},
    {"id": 256, "name": "Altın Çağ Multivitamini", "category": "Multi Vitaminler"},
    {"id": 257, "name": "Çocuklar için Günlük Multivitamin", "category": "Multi Vitaminler"},
    {"id": 258, "name": "Çocuk Multivitamin Sakızları", "category": "Multi Vitaminler"},
    {"id": 259, "name": "Çocuklar için Balık Yağı + Multivitamin Şurubu", "category": "Multi Vitaminler"},
    {"id": 260, "name": "Çocuklar için Çiğneme Formunda C Vitamini + Multivitamin", "category": "Multi Vitaminler"},
    {"id": 261, "name": "Günlük Destek Multivitamini", "category": "Multi Vitaminler"},
    {"id": 262, "name": "Total Canlılık Multivitamini", "category": "Multi Vitaminler"},
    {"id": 263, "name": "Enerji ve Odaklanma Formülü", "category": "Multi Vitaminler"},
    {"id": 264, "name": "50+ Yaşa Özel Karışım", "category": "İhtiyaca Özel Ürünler"},
    {"id": 265, "name": "Adrenal Destek Karışımı", "category": "İhtiyaca Özel Ürünler"},
    {"id": 266, "name": "Alerji Rahatlatma Karışımı", "category": "İhtiyaca Özel Ürünler"},
    {"id": 267, "name": "Anti-İnflamatuar Destek Karışımı", "category": "İhtiyaca Özel Ürünler"},
    {"id": 268, "name": "Antioksidan Süper Gıda Karışımı", "category": "İhtiyaca Özel Ürünler"},
    {"id": 269, "name": "Antioksidanlar", "category": "İhtiyaca Özel Ürünler"},
    {"id": 270, "name": "Bağırsak Sağlığı", "category": "İhtiyaca Özel Ürünler"},
    {"id": 271, "name": "Bağışıklık Destek Karışımı", "category": "İhtiyaca Özel Ürünler"},
    {"id": 272, "name": "Beyin Sağlığı Karışımı", "category": "İhtiyaca Özel Ürünler"},
    {"id": 273, "name": "Bilişsel Gerilemeyi Önleme Karışımı", "category": "İhtiyaca Özel Ürünler"},
    {"id": 274, "name": "Cilt Parlaklığı Karışımı", "category": "İhtiyaca Özel Ürünler"},
    {"id": 275, "name": "Demir Eksikliği Karışımı", "category": "İhtiyaca Özel Ürünler"},
    {"id": 276, "name": "Detoksifikasyon Karışımı", "category": "İhtiyaca Özel Ürünler"},
    {"id": 277, "name": "Doğurganlık ve Üreme Sağlığı Karışımı", "category": "İhtiyaca Özel Ürünler"},
    {"id": 278, "name": "Eklem ve Kemik Sağlığı Karışımı", "category": "İhtiyaca Özel Ürünler"},
    {"id": 279, "name": "Enerji ve Canlılık Karışımı", "category": "İhtiyaca Özel Ürünler"},
    {"id": 280, "name": "Fitness ve Atletik Performans Karışımı", "category": "İhtiyaca Özel Ürünler"},
    {"id": 281, "name": "Gençlik Karışımı", "category": "İhtiyaca Özel Ürünler"},
    {"id": 282, "name": "Göz Sağlığı Karışımı", "category": "İhtiyaca Özel Ürünler"},
    {"id": 283, "name": "Histamin İntoleransı Karışımı", "category": "İhtiyaca Özel Ürünler"},
    {"id": 284, "name": "Hücresel Sağlık Karışımı", "category": "İhtiyaca Özel Ürünler"},
    {"id": 285, "name": "Kalp Sağlığı Karışımı", "category": "İhtiyaca Özel Ürünler"},
    {"id": 286, "name": "Kan Şekeri Düzenleyici Karışım", "category": "İhtiyaca Özel Ürünler"},
    {"id": 287, "name": "Karaciğer Desteği Karışımı", "category": "İhtiyaca Özel Ürünler"},
    {"id": 288, "name": "Karaciğer Detoks Karışımı", "category": "İhtiyaca Özel Ürünler"},
    {"id": 289, "name": "Kardiyo Destek Karışımı", "category": "İhtiyaca Özel Ürünler"},
    {"id": 290, "name": "Kemik Sağlığı Karışımı", "category": "İhtiyaca Özel Ürünler"},
    {"id": 291, "name": "Libido Artırma Karışımı", "category": "İhtiyaca Özel Ürünler"},
    {"id": 292, "name": "Migren Yönetimi Karışımı", "category": "İhtiyaca Özel Ürünler"},
    {"id": 293, "name": "Prebiyotik Karışım", "category": "İhtiyaca Özel Ürünler"},
    {"id": 294, "name": "Ruh Hali ve Kaygı Yönetimi Karışımı", "category": "İhtiyaca Özel Ürünler"},
    {"id": 295, "name": "Saç Sağlığı Karışımı", "category": "İhtiyaca Özel Ürünler"},
    {"id": 296, "name": "Sindirim Enzimi Karışımı", "category": "İhtiyaca Özel Ürünler"},
    {"id": 297, "name": "Stres Yönetimi Karışımı", "category": "İhtiyaca Özel Ürünler"},
    {"id": 298, "name": "Tam Vücut Sağlığı Karışımı", "category": "İhtiyaca Özel Ürünler"},
    {"id": 299, "name": "Tiroid Sağlığı Karışımı", "category": "İhtiyaca Özel Ürünler"},
    {"id": 300, "name": "Uyku İyileştirme Karışımı", "category": "İhtiyaca Özel Ürünler"},
    {"id": 301, "name": "Yorgunluk Önleyici Karışım", "category": "İhtiyaca Özel Ürünler"},
    {"id": 167, "name": "E Vitamini", "category": "Günlük Takviyeler"},
    {"id": 166, "name": "Demir", "category": "Günlük Takviyeler"},
    {"id": 165, "name": "D3 Vitamini", "category": "Günlük Takviyeler"},
    {"id": 164, "name": "D Vitamini", "category": "Günlük Takviyeler"},
    {"id": 163, "name": "Çinko", "category": "Günlük Takviyeler"},
    {"id": 162, "name": "C Vitamini", "category": "Günlük Takviyeler"},
    {"id": 161, "name": "Bor", "category": "Günlük Takviyeler"},
    {"id": 160, "name": "B9 Vitamini (Folik Asit)", "category": "Günlük Takviyeler"},
    {"id": 159, "name": "B7 Vitamini (Biotin)", "category": "Günlük Takviyeler"},
    {"id": 158, "name": "B6 Vitamini", "category": "Günlük Takviyeler"},
    {"id": 157, "name": "B5 Vitamini (Pantotenik Asit)", "category": "Günlük Takviyeler"},
    {"id": 156, "name": "B3 Vitamini (Niasin)", "category": "Günlük Takviyeler"},
    {"id": 155, "name": "B2 Vitamini (Riboflavin)", "category": "Günlük Takviyeler"},
    {"id": 154, "name": "B12 (Kobalamin)", "category": "Günlük Takviyeler"},
    {"id": 150, "name": "B1 Vitamini (Tiamin)", "category": "Günlük Takviyeler"},
    {"id": 147, "name": "A Vitamini", "category": "Günlük Takviyeler"}
]

# Test Önerisi Endpoint'i için - Satışta Olan Testler
AVAILABLE_TESTS = [
    {
        "test_id": "vitamin_mineral",
        "test_name": "Vitamin ve Mineral Seviyeleri Testi",
        "description": "Vücutta eksik veya fazla bulunan vitamin ve mineralleri analiz etmek için yapılan bir testtir. Bağışıklık sistemi, kemik sağlığı ve enerji seviyelerini değerlendirmeye yardımcı olur.",
        "price": 0.00,
        "category": "Vitaminler",
        "priority": "high"
    },
    {
        "test_id": "tumor_markers",
        "test_name": "Tümör Belirteçleri Testi",
        "description": "Kanser belirteçlerini analiz ederek erken tanı ve takibi sağlamak için yapılan bir testtir. Prostat, meme, karaciğer, akciğer ve sindirim sistemi kanserleri için kullanılır.",
        "price": 0.00,
        "category": "Kanser",
        "priority": "high"
    },
    {
        "test_id": "hormone",
        "test_name": "Hormon Testi",
        "description": "Tiroid, üreme hormonları ve stres hormonlarını analiz ederek metabolik ve hormonal dengeyi değerlendirmek için yapılan bir testtir. Adet düzensizlikleri, tiroid hastalıkları ve stres hormonları ile ilgili bilgiler sağlar.",
        "price": 0.00,
        "category": "Hormonlar",
        "priority": "high"
    },
    {
        "test_id": "heavy_metals",
        "test_name": "Ağır Metal Testi",
        "description": "Vücutta toksik ağır metal seviyelerini tespit etmek için yapılan bir testtir. Kurşun, cıva, arsenik gibi metallere maruz kalma düzeyini analiz eder.",
        "price": 0.00,
        "category": "Toksikoloji",
        "priority": "medium"
    },
    {
        "test_id": "diabetes",
        "test_name": "Şeker ve Diyabet Testi",
        "description": "Kan şekerini ve insülin seviyelerini kontrol ederek diyabet ve insülin direnci riskini belirlemek için yapılan bir testtir. HbA1c testi ile uzun vadeli kan şekeri kontrolü sağlanır.",
        "price": 0.00,
        "category": "Metabolizma",
        "priority": "high"
    },
    {
        "test_id": "lipid_cholesterol",
        "test_name": "Lipid ve Kolesterol Testi",
        "description": "Kan yağlarını analiz ederek kalp hastalığı ve damar tıkanıklığı riskini değerlendirmekte kullanılan bir testtir. İyi (HDL) ve kötü (LDL) kolesterol seviyelerinin takibini sağlar.",
        "price": 0.00,
        "category": "Kardiyovasküler",
        "priority": "high"
    },
    {
        "test_id": "skin_health",
        "test_name": "Cilt Sağlığı Testi",
        "description": "Cilt, saç ve tırnak sağlığı için gerekli olan vitamin ve minerallerin seviyelerini belirlemek için yapılan bir testtir. Biotin eksikliği, alerjik reaksiyonlar ve cilt hassasiyeti hakkında bilgi verir.",
        "price": 0.00,
        "category": "Cilt Sağlığı",
        "priority": "medium"
    },
    {
        "test_id": "eye_health",
        "test_name": "Göz Sağlığı Testi",
        "description": "Göz sağlığını destekleyen vitamin ve antioksidan seviyelerini belirlemek için yapılan bir testtir. Görme kaybı, katarakt ve göz yorgunluğunu önlemeye yardımcı olur.",
        "price": 0.00,
        "category": "Göz Sağlığı",
        "priority": "medium"
    },
    {
        "test_id": "digestive_system",
        "test_name": "Bağırsak ve Sindirim Sistemi Testi",
        "description": "Bağırsak sağlığını, gıda intoleranslarını ve sindirim enzimlerinin etkinliğini değerlendirmek için yapılan bir testtir. Çölyak hastalığı, bağırsak enfeksiyonları ve sindirim sistemi hastalıklarını belirlemede kullanılır.",
        "price": 0.00,
        "category": "Sindirim",
        "priority": "high"
    },
    {
        "test_id": "kidney_function",
        "test_name": "Böbrek Fonksiyonları Testi",
        "description": "Böbreklerin toksinleri ne kadar iyi filtrelediğini belirlemek, idrar yolları hastalıklarını ve böbrek yetmezliği riskini değerlendirmek için yapılan bir testtir.",
        "price": 0.00,
        "category": "Böbrek",
        "priority": "high"
    },
    {
        "test_id": "liver_function",
        "test_name": "Karaciğer Fonksiyonları Testi",
        "description": "Karaciğer enzimlerini, protein seviyelerini ve safra fonksiyonlarını değerlendirerek karaciğerin sağlığını belirlemek için yapılan bir testtir. Hepatit, siroz ve yağlı karaciğer hastalıkları teşhisinde kullanılır.",
        "price": 0.00,
        "category": "Karaciğer",
        "priority": "high"
    },
    {
        "test_id": "cardiovascular",
        "test_name": "Kalp ve Damar Sağlığı Testi",
        "description": "Kalp krizi riski, damar sağlığı ve kolesterol seviyelerini değerlendirmek için yapılan bir testtir. Kardiyovasküler hastalıkları önlemek ve erken teşhis etmek için kullanılır.",
        "price": 0.00,
        "category": "Kardiyovasküler",
        "priority": "high"
    },
    {
        "test_id": "brain_function",
        "test_name": "Beyin Fonksiyonları Testi",
        "description": "Beyin kimyasallarını analiz ederek nörolojik ve psikiyatrik hastalıkları değerlendirmek için yapılan bir testtir. Depresyon, anksiyete ve nörolojik bozuklukların belirlenmesine yardımcı olur.",
        "price": 0.00,
        "category": "Nöroloji",
        "priority": "medium"
    },
    {
        "test_id": "general_health",
        "test_name": "Genel Sağlık Testi",
        "description": "Kırmızı ve beyaz kan hücrelerinin, trombosit seviyelerinin ve enfeksiyon belirteçlerinin değerlendirilmesi için yapılan bir testtir. Anemi, bağışıklık sistemi hastalıkları ve enfeksiyon riskinin belirlenmesine yardımcı olur.",
        "price": 0.00,
        "category": "Genel Sağlık",
        "priority": "high"
    },
    {
        "test_id": "biomarkers",
        "test_name": "Bio-Markers / Hastalık Belirteçleri",
        "description": "Alzheimer, Parkinson, demans ve kanser gibi hastalıkların belirteçlerini analiz etmek için yapılan bir testtir. Erken teşhis ve önleyici sağlık planlaması yapmaya yardımcı olur.",
        "price": 3470.56,
        "category": "Biyomarker",
        "priority": "high"
    },
    {
        "test_id": "neurological_genetic",
        "test_name": "Nörolojik ve Genetik Testler",
        "description": "Genetik yapı ve nörotransmitter seviyelerini değerlendirerek nörolojik hastalık risklerini belirlemek için yapılan bir testtir. Hafıza, konsantrasyon ve psikolojik rahatsızlıklarla ilgili ipuçları sağlar.",
        "price": 0.00,
        "category": "Genetik",
        "priority": "medium"
    },
    {
        "test_id": "biochemical_inflammation",
        "test_name": "Biyokimyasal ve İltihap Testleri",
        "description": "Enflamasyon (iltihap) seviyelerini ölçerek bağışıklık sisteminin tepkisini analiz etmek için yapılan bir testtir. Kronik hastalıkların ve otoimmün hastalıkların belirlenmesine yardımcı olur.",
        "price": 0.00,
        "category": "İnflamasyon",
        "priority": "high"
    },
    {
        "test_id": "metabolic_health",
        "test_name": "Metabolik ve Genel Sağlık Testleri",
        "description": "Metabolik yaş, enerji üretimi ve temel sağlık parametrelerini değerlendirmek için yapılan bir testtir. Bireyin biyolojik yaşını belirleyerek genel sağlık durumunu analiz eder.",
        "price": 0.00,
        "category": "Metabolizma",
        "priority": "high"
    }
]


