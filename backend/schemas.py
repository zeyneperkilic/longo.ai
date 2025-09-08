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
    default_supplements: Optional[List[Dict[str, Any]]] = Field(default_factory=list)
    personalized_supplements: Optional[List[Dict[str, Any]]] = Field(default_factory=list)
    excluded_due_to_allergy: Optional[List[str]] = Field(default_factory=list)
    allergy_alternatives: Optional[List[str]] = Field(default_factory=list)
    special_conditions_analysis: Optional[Dict[str, Any]] = Field(default_factory=dict)
    disclaimer: str = "Bu içerik bilgilendirme amaçlıdır; tıbbi tanı/tedavi için hekiminize başvurun."
    
    class Config:
        extra = "allow"

# Lab Response Schemas - ESNEK YAPI
class LabAnalysisResponse(BaseModel):
    analysis: Dict[str, Any] = Field(default_factory=dict)
    disclaimer: str = "Bu içerik bilgilendirme amaçlıdır; tıbbi tanı/tedavi için hekiminize başvurun."
    
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
    general_assessment: Optional[Dict[str, Any]] = Field(default_factory=dict)
    test_details: Optional[Dict[str, Any]] = Field(default_factory=dict)
    supplement_recommendations: Optional[List[Dict[str, Any]]] = Field(default_factory=list)
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

