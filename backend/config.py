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



MODERATION_MODEL = "google/gemini-2.5-flash"

MODERATION_TIMEOUT_MS = 10000  # 10 saniye (ücretli modeller için - hızlı)

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


