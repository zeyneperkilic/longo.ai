from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Literal, Dict, Any

# Quiz Schemas - ESNEK YAPI (Production için)
class QuizRequest(BaseModel):
    quiz_answers: Dict[str, Any] = Field(
        description="Herhangi bir quiz formatı - frontend'den nasıl gelirse gelsin kabul et",
        default_factory=dict
    )
    available_supplements: Optional[List[Dict[str, Any]]] = Field(
        description="Database'den gelen ürün kataloğu - opsiyonel",
        default_factory=list
    )
    
    # Extra fields için esnek yapı
    class Config:
        extra = "allow"

class SupplementRecommendation(BaseModel):
    name: str = Field(description="Supplement adı")
    description: str = Field(description="Açıklama")
    daily_dose: str = Field(description="Günlük doz")
    benefits: List[str] = Field(description="Faydaları")
    warnings: List[str] = Field(description="Uyarılar")
    priority: Literal["high", "medium", "low"] = Field(default="medium")
    
    class Config:
        extra = "allow"

class NutritionAdvice(BaseModel):
    title: str = "Beslenme Önerileri"
    recommendations: List[str]
    
    class Config:
        extra = "allow"

class LifestyleAdvice(BaseModel):
    title: str = "Yaşam Tarzı Önerileri" 
    recommendations: List[str]
    
    class Config:
        extra = "allow"

class GeneralWarnings(BaseModel):
    title: str = "Genel Uyarılar"
    warnings: List[str]
    
    class Config:
        extra = "allow"

class TestRecommendation(BaseModel):
    test_name: str = Field(description="Test adı")
    reason: str = Field(description="Neden önerildiği")
    benefit: str = Field(description="Kullanıcıya sağlayacağı fayda")
    
    class Config:
        extra = "allow"

class TestRecommendations(BaseModel):
    title: str = "Test Önerileri"
    recommended_tests: List[TestRecommendation] = Field(default_factory=list)
    analysis_summary: str = "Analiz tamamlandı"
    disclaimer: str = "Bu öneriler bilgilendirme amaçlıdır. Test yaptırmadan önce doktorunuza danışın."
    
    class Config:
        extra = "allow"

# Lab Analysis Schemas - ESNEK YAPI
class LabTestResult(BaseModel):
    # TÜM FIELD'LAR OPSİYONEL - Asıl site'dan herhangi bir format gelebilir
    name: Optional[str] = Field(default=None, description="Test adı")
    test_name: Optional[str] = Field(default=None, description="Test adı (alternatif)")
    value: Optional[Any] = Field(default=None, description="Test sonucu değeri - herhangi bir tip")
    unit: Optional[str] = Field(default=None, description="Birim")
    reference_range: Optional[str] = Field(default=None, description="Referans aralığı")
    status: Optional[str] = Field(default=None, description="Test durumu")
    test_date: Optional[str] = Field(default=None, description="Test tarihi")
    date: Optional[str] = Field(default=None, description="Test tarihi (alternatif)")
    notes: Optional[str] = Field(default=None, description="Ek notlar")
    category: Optional[str] = Field(default=None, description="Test kategorisi")
    
    # Extra fields için esnek yapı
    class Config:
        extra = "allow"

class HistoricalLabResult(BaseModel):
    date: str = Field(description="Test tarihi (YYYY-MM-DD)")
    value: Any = Field(description="Test sonucu değeri - herhangi bir tip (string, int, float)")
    status: Optional[str] = Field(default=None, description="Test durumu (normal, yüksek, düşük, kritik)")
    lab: Optional[str] = Field(default=None, description="Laboratuvar adı")
    notes: Optional[str] = Field(default=None, description="Ek notlar")
    
    class Config:
        extra = "allow"

class SingleLabRequest(BaseModel):
    test: LabTestResult
    historical_results: Optional[List[Dict[str, Any]]] = Field(
        default=None, 
        description="Geçmiş test sonuçları - herhangi bir format"
    )
    
    class Config:
        extra = "allow"

class SingleSessionRequest(BaseModel):
    # TÜM FIELD'LAR OPSİYONEL - Asıl site'dan herhangi bir format gelebilir
    session_tests: Optional[List[LabTestResult]] = Field(default_factory=list, description="Test seansı sonuçları")
    tests: Optional[List[Dict[str, Any]]] = Field(default_factory=list, description="Test sonuçları (alternatif)")
    session_date: Optional[str] = Field(default=None, description="Test seansı tarihi")
    date: Optional[str] = Field(default=None, description="Test tarihi (alternatif)")
    laboratory: Optional[str] = Field(default=None, description="Laboratuvar adı")
    lab: Optional[str] = Field(default=None, description="Laboratuvar adı (alternatif)")
    session_summary: Optional[Dict[str, Any]] = Field(
        default=None, 
        description="Seans özeti - herhangi bir format"
    )
    
    class Config:
        extra = "allow"

class MultipleLabRequest(BaseModel):
    # TÜM FIELD'LAR OPSİYONEL - Asıl site'dan herhangi bir format gelebilir
    tests: Optional[List[LabTestResult]] = Field(default_factory=list, description="Test sonuçları")
    lab_results: Optional[List[Dict[str, Any]]] = Field(default_factory=list, description="Test sonuçları (alternatif)")
    total_test_sessions: Optional[int] = Field(default=1, description="Toplam test seansı sayısı")
    available_supplements: Optional[List[Dict[str, Any]]] = Field(
        default=None, 
        description="Database'den gelen ürün kataloğu"
    )
    user_profile: Optional[Dict[str, Any]] = Field(
        default=None, 
        description="Kullanıcı profili - herhangi bir format"
    )
    
    class Config:
        extra = "allow"

# Chat Schemas - ESNEK YAPI
class ChatStartRequest(BaseModel):
    # TÜM FIELD'LAR OPSİYONEL - Asıl site'dan herhangi bir format gelebilir
    # Boş body kabul et, herhangi bir field eklenebilir
    class Config:
        extra = "allow"

class ChatStartResponse(BaseModel):
    conversation_id: int = Field(description="Konuşma ID'si")
    
    class Config:
        extra = "allow"

class ChatMessageRequest(BaseModel):
    # TÜM FIELD'LAR OPSİYONEL - Asıl site'dan herhangi bir format gelebilir
    text: Optional[str] = Field(default=None, description="Kullanıcı mesajı")
    message: Optional[str] = Field(default=None, description="Kullanıcı mesajı (alternatif)")
    conversation_id: Optional[int] = Field(default=None, description="Konuşma ID'si")
    conv_id: Optional[int] = Field(default=None, description="Konuşma ID'si (alternatif)")
    
    # Extra fields için esnek yapı
    class Config:
        extra = "allow"

# Response Schemas - ESNEK YAPI
class ChatResponse(BaseModel):
    conversation_id: int
    reply: str
    latency_ms: int
    
    class Config:
        extra = "allow"

class QuizResponse(BaseModel):
    success: bool = True
    message: str = "Quiz analizi tamamlandı"
    nutrition_advice: Optional[Dict[str, Any]] = Field(default_factory=dict)
    lifestyle_advice: Optional[Dict[str, Any]] = Field(default_factory=dict)
    general_warnings: Optional[Dict[str, Any]] = Field(default_factory=dict)
    supplement_recommendations: Optional[List[Dict[str, Any]]] = Field(default_factory=list)
    test_recommendations: Optional[TestRecommendations] = Field(default=None, description="Test önerileri (Premium+ kullanıcılar için)")
    disclaimer: str = "Bu içerik bilgilendirme amaçlıdır; tıbbi tanı/tedavi için hekiminize başvurun."
    
    class Config:
        extra = "allow"

# Lab Response Schemas - ESNEK YAPI
class LabAnalysisResponse(BaseModel):
    title: str = "Test Sonucu Yorumu"
    test_name: Optional[str] = Field(default="Test Adı Sonucu Değerlendirmesi")
    last_result: Optional[str] = Field(default="Son Test Sonucunuz: X değer Durum")
    reference_range: Optional[str] = Field(default="Referans Aralığı: X-Y birim")
    test_analysis: Optional[str] = Field(default="Test analizi ve trend analizi")
    disclaimer: str = "Bu yorum sadece bilgilendirme amaçlıdır. Kesin tanı ve tedavi için mutlaka doktorunuza başvurunuz."
    
    class Config:
        extra = "allow"

class SingleSessionResponse(BaseModel):
    title: str = "Test Seansı Analizi"
    session_info: Optional[Dict[str, Any]] = Field(default_factory=dict)
    general_assessment: Optional[Dict[str, Any]] = Field(default_factory=dict)
    test_groups: Optional[Dict[str, Any]] = Field(default_factory=dict)
    test_summary: Optional[Dict[str, Any]] = Field(default_factory=dict)
    general_recommendations: Optional[List[str]] = Field(default_factory=list)
    disclaimer: str = "Bu içerik bilgilendirme amaçlıdır; tıbbi tanı/tedavi için hekiminize başvurun."
    
    class Config:
        extra = "allow"

class GeneralLabSummaryResponse(BaseModel):
    title: str = "Tüm Testlerin Genel Yorumu"
    genel_saglik_durumu: Optional[str] = Field(default="Genel Sağlık Durumu Değerlendirmesi")
    genel_durum: Optional[str] = Field(default="Testlerin genel kapsamlı analizi varsa eski sonuçlarla karşılaştırma.")
    oneriler: Optional[List[str]] = Field(default_factory=list)
    urun_onerileri: Optional[List[Dict[str, Any]]] = Field(default_factory=list)
    test_recommendations: Optional[TestRecommendations] = Field(default=None, description="Test önerileri (Premium+ kullanıcılar için)")
    disclaimer: str = "Bu içerik bilgilendirme amaçlıdır; tıbbi tanı/tedavi için hekiminize başvurun."
    
    class Config:
        extra = "allow"

# Legacy schemas for compatibility
class AnalyzePayload(BaseModel):
    payload: Dict[str, Any]
    
    class Config:
        extra = "allow"

class LabBatchPayload(BaseModel):
    results: List[Dict[str, Any]]
    
    class Config:
        extra = "allow"

class RecommendationItem(BaseModel):
    id: Optional[str] = None
    name: str
    reason: str
    source: Literal["consensus", "assistant"] = "consensus"
    
    class Config:
        extra = "allow"

class AnalyzeResponse(BaseModel):
    recommendations: List[RecommendationItem] = Field(default_factory=list)
    analysis: Dict[str, Any] = Field(default_factory=dict)
    disclaimer: str = "Bu içerik bilgilendirme amaçlıdır; tıbbi tanı/tedavi için hekiminize başvurun."
    
    class Config:
        extra = "allow"

# Test Önerisi Schemas
class TestRecommendationRequest(BaseModel):
    user_analysis: bool = Field(default=True, description="Kullanıcı analizi yap")
    exclude_taken_tests: bool = Field(default=True, description="Baktırılan testleri çıkar")
    max_recommendations: int = Field(default=3, description="Maksimum öneri sayısı")
    
    class Config:
        extra = "allow"

class TestRecommendation(BaseModel):
    test_name: str = Field(description="Test adı")
    reason: str = Field(description="Neden önerildiği")
    benefit: str = Field(description="Kullanıcıya sağlayacağı fayda")
    
    class Config:
        extra = "allow"

class TestRecommendationResponse(BaseModel):
    title: str = "Test Önerileri"
    recommended_tests: List[TestRecommendation]
    analysis_summary: str = Field(description="Kullanıcı analiz özeti")
    disclaimer: str = "Bu öneriler bilgilendirme amaçlıdır. Test yaptırmadan önce doktorunuza danışın."
    
    class Config:
        extra = "allow"

# Metabolik Yaş Testi - Premium Plus
class MetabolicAgeTestRequest(BaseModel):
    """Metabolik yaş testi isteği - Flexible data structure"""
    # Temel bilgiler (zorunlu)
    chronological_age: int = Field(description="Kronolojik yaş")
    
    # Diğer tüm alanlar optional - hangi veriler gelirse gelsin
    gender: Optional[str] = Field(default=None, description="Cinsiyet")
    height: Optional[float] = Field(default=None, description="Boy (cm)")
    weight: Optional[float] = Field(default=None, description="Kilo (kg)")
    body_fat_percentage: Optional[float] = Field(default=None, description="Vücut yağ oranı (%)")
    muscle_mass: Optional[float] = Field(default=None, description="Kas kütlesi (kg)")
    resting_heart_rate: Optional[int] = Field(default=None, description="Dinlenme kalp atışı (bpm)")
    blood_pressure_systolic: Optional[int] = Field(default=None, description="Sistolik tansiyon (mmHg)")
    blood_pressure_diastolic: Optional[int] = Field(default=None, description="Diyastolik tansiyon (mmHg)")
    sleep_hours: Optional[float] = Field(default=None, description="Günlük uyku saati")
    exercise_frequency: Optional[str] = Field(default=None, description="Egzersiz sıklığı")
    stress_level: Optional[str] = Field(default=None, description="Stres seviyesi")
    diet_quality: Optional[str] = Field(default=None, description="Beslenme kalitesi")
    smoking_status: Optional[str] = Field(default=None, description="Sigara durumu")
    alcohol_consumption: Optional[str] = Field(default=None, description="Alkol tüketimi")
    family_longevity: Optional[str] = Field(default=None, description="Aile uzun yaşam öyküsü")
    chronic_conditions: Optional[List[str]] = Field(default=[], description="Kronik hastalıklar")
    medications: Optional[List[str]] = Field(default=[], description="Kullanılan ilaçlar")
    
    # Ek flexible alanlar için
    additional_data: Optional[Dict[str, Any]] = Field(default={}, description="Ek veriler")
    
    class Config:
        extra = "allow"  # Ek alanlara izin ver

class LongevityFactor(BaseModel):
    """Uzun yaşam faktörü"""
    factor_name: str = Field(description="Faktör adı")
    current_status: str = Field(description="Mevcut durum")
    impact_score: int = Field(description="Etki skoru (1-10)")
    recommendation: str = Field(description="Öneri")
    
    class Config:
        extra = "allow"

class MetabolicAgeTestResponse(BaseModel):
    """Metabolik yaş testi yanıtı"""
    success: bool = True
    message: str = "Metabolik yaş analizi tamamlandı"
    
    # Temel bilgiler
    chronological_age: int = Field(description="Kronolojik yaş")
    metabolic_age: int = Field(description="Hesaplanan metabolik yaş")
    age_difference: int = Field(description="Yaş farkı (metabolik - kronolojik)")
    biological_age_status: str = Field(description="Biyolojik yaş durumu")
    
    # Analiz sonuçları
    longevity_score: int = Field(description="Uzun yaşam skoru (0-100)")
    health_span_prediction: str = Field(description="Sağlıklı yaşam süresi tahmini")
    risk_factors: List[str] = Field(description="Risk faktörleri")
    protective_factors: List[str] = Field(description="Koruyucu faktörler")
    
    # Detaylı analiz
    longevity_factors: List[LongevityFactor] = Field(description="Uzun yaşam faktörleri")
    personalized_recommendations: List[str] = Field(description="Kişiselleştirilmiş öneriler")
    
    # Gelecek projeksiyonu
    future_health_outlook: str = Field(description="Gelecek sağlık durumu")
    
    disclaimer: str = "Bu analiz bilgilendirme amaçlıdır. Tıbbi kararlar için doktorunuza danışın."
    
    class Config:
        extra = "allow"

