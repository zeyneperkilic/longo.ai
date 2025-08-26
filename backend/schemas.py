from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Literal, Dict, Any

# Quiz Schemas - ESNEK YAPI
class QuizRequest(BaseModel):
    quiz_answers: Dict[str, Any] = Field(description="Herhangi bir quiz formatı - frontend'den gelecek")
    available_supplements: List[Dict[str, Any]] = Field(description="Database'den gelen ürün kataloğu")

class SupplementRecommendation(BaseModel):
    name: str = Field(description="Supplement adı")
    description: str = Field(description="Açıklama")
    daily_dose: str = Field(description="Günlük doz")
    benefits: List[str] = Field(description="Faydaları")
    warnings: List[str] = Field(description="Uyarılar")
    priority: Literal["high", "medium", "low"] = Field(default="medium")

class NutritionAdvice(BaseModel):
    title: str = "Beslenme Önerileri"
    recommendations: List[str]

class LifestyleAdvice(BaseModel):
    title: str = "Yaşam Tarzı Önerileri" 
    recommendations: List[str]

class GeneralWarnings(BaseModel):
    title: str = "Genel Uyarılar"
    warnings: List[str]

class QuizResponse(BaseModel):
    success: bool = True
    message: str = "Online Sağlık Quizini Başarıyla Tamamladınız"
    nutrition_advice: NutritionAdvice
    lifestyle_advice: LifestyleAdvice
    general_warnings: GeneralWarnings
    supplement_recommendations: List[SupplementRecommendation]
    disclaimer: str = "Bu içerik bilgilendirme amaçlıdır; tıbbi tanı/tedavi için hekiminize başvurun."

# Lab Analysis Schemas
class LabTestResult(BaseModel):
    name: str = Field(description="Test adı (örn: Hemoglobin, Vitamin D, CBC)")
    value: str = Field(description="Test sonucu değeri (sayısal veya metin)")
    unit: Optional[str] = Field(default=None, description="Birim (mg/dL, ng/mL, vs.) - opsiyonel")
    reference_range: Optional[str] = Field(default=None, description="Referans aralığı - opsiyonel")
    status: Optional[str] = Field(default=None, description="Test durumu (normal, yüksek, düşük, kritik)")
    test_date: Optional[str] = Field(default=None, description="Test tarihi (YYYY-MM-DD)")
    notes: Optional[str] = Field(default=None, description="Ek notlar veya açıklamalar")
    category: Optional[str] = Field(default=None, description="Test kategorisi (kan, idrar, hormon, vs.)")

class HistoricalLabResult(BaseModel):
    date: str = Field(description="Test tarihi (YYYY-MM-DD)")
    value: str = Field(description="Test sonucu değeri")
    status: Optional[str] = Field(default=None, description="Test durumu (normal, yüksek, düşük, kritik)")
    lab: Optional[str] = Field(default=None, description="Laboratuvar adı")
    notes: Optional[str] = Field(default=None, description="Ek notlar")

class SingleLabRequest(BaseModel):
    test: LabTestResult
    historical_results: Optional[List[HistoricalLabResult]] = Field(default=None, description="Geçmiş test sonuçları - trend analizi için")

class SingleSessionRequest(BaseModel):
    session_tests: List[LabTestResult] = Field(description="Tek seans içindeki tüm testler")
    session_date: str = Field(description="Test seansı tarihi (YYYY-MM-DD)")
    laboratory: str = Field(description="Laboratuvar adı")
    session_summary: Optional[Dict[str, Any]] = Field(default=None, description="Seans özeti (test sayısı, normal/anormal sayısı)")

class MultipleLabRequest(BaseModel):
    tests: List[LabTestResult]
    total_test_sessions: int = Field(description="Toplam test seansı sayısı")
    available_supplements: Optional[List[Dict[str, Any]]] = Field(default=None, description="Database'den gelen ürün kataloğu")
    user_profile: Optional[Dict[str, Any]] = Field(default=None, description="Opsiyonel kullanıcı profili")

class LabAnalysisResponse(BaseModel):
    analysis: Dict[str, Any] = Field(default_factory=dict)
    disclaimer: str = "Bu içerik bilgilendirme amaçlıdır; tıbbi tanı/tedavi için hekiminize başvurun."

class SingleSessionResponse(BaseModel):
    title: str = "Test Seansı Analizi"
    
    # Seans bilgileri
    session_info: Dict[str, Any] = Field(description="Seans bilgileri: tarih, laboratuvar, test sayısı")
    
    # Genel test yorumu
    general_assessment: Dict[str, Any] = Field(description="Seansın genel değerlendirmesi")
    
    # Test grupları ve özet
    test_groups: Dict[str, Any] = Field(description="Test grupları ve sayıları")
    
    # Test sonuçları özeti
    test_summary: Dict[str, Any] = Field(description="Normal, dikkat gereken test sayıları")
    
    # Genel öneriler
    general_recommendations: List[str] = Field(description="Genel sağlık önerileri")
    
    disclaimer: str = "Bu içerik bilgilendirme amaçlıdır; tıbbi tanı/tedavi için hekiminize başvurun."

class GeneralLabSummaryResponse(BaseModel):
    title: str = "Tüm Testlerin Genel Yorumu"
    
    # Kısa analiz - Tüm testlerin genel değerlendirmesi
    general_assessment: Dict[str, Any] = Field(default_factory=dict, description="Genel sağlık durumu değerlendirmesi")
    test_count: int = Field(description="Toplam test sayısı")
    overall_status: str = Field(description="Genel durum: normal, dikkat_edilmeli, kritik")
    
    # Günlük hayat tavsiyeleri
    lifestyle_recommendations: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="Günlük hayat önerileri: egzersiz, beslenme, uyku, stres yönetimi"
    )
    
    # Supplement önerileri - Eksik değerler için
    supplement_recommendations: List[SupplementRecommendation] = Field(
        default_factory=list,
        description="Lab sonuçlarına göre önerilen supplementler"
    )
    
    # Test bazlı detaylar
    test_details: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict,
        description="Her test için detaylı yorum ve öneriler"
    )
    
    disclaimer: str = "Bu içerik bilgilendirme amaçlıdır; tıbbi tanı/tedavi için hekiminize başvurun."

# Legacy schemas for compatibility
class AnalyzePayload(BaseModel):
    payload: Dict[str, Any]

class LabBatchPayload(BaseModel):
    results: List[Dict[str, Any]]

class ChatStartResponse(BaseModel):
    conversation_id: int

class ChatMessageRequest(BaseModel):
    conversation_id: int
    text: str

class ChatResponse(BaseModel):
    conversation_id: int
    reply: str
    latency_ms: int

class RecommendationItem(BaseModel):
    id: Optional[str] = None
    name: str
    reason: str
    source: Literal["consensus", "assistant"] = "consensus"

class AnalyzeResponse(BaseModel):
    recommendations: List[RecommendationItem] = Field(default_factory=list)
    analysis: Dict[str, Any] = Field(default_factory=dict)
    disclaimer: str = "Bu içerik bilgilendirme amaçlıdır; tıbbi tanı/tedavi için hekiminize başvurun."

