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
        extra = "allow"  # Bilinmeyen field'ları da kabul et

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

# Lab Analysis Schemas - ESNEK YAPI
class LabTestResult(BaseModel):
    name: str = Field(description="Test adı")
    value: str = Field(description="Test sonucu değeri")
    unit: Optional[str] = Field(default=None, description="Birim")
    reference_range: Optional[str] = Field(default=None, description="Referans aralığı")
    status: Optional[str] = Field(default=None, description="Test durumu")
    test_date: Optional[str] = Field(default=None, description="Test tarihi")
    notes: Optional[str] = Field(default=None, description="Ek notlar")
    category: Optional[str] = Field(default=None, description="Test kategorisi")
    
    # Extra fields için esnek yapı
    class Config:
        extra = "allow"

class HistoricalLabResult(BaseModel):
    date: str = Field(description="Test tarihi (YYYY-MM-DD)")
    value: str = Field(description="Test sonucu değeri")
    status: Optional[str] = Field(default=None, description="Test durumu (normal, yüksek, düşük, kritik)")
    lab: Optional[str] = Field(default=None, description="Laboratuvar adı")
    notes: Optional[str] = Field(default=None, description="Ek notlar")

class SingleLabRequest(BaseModel):
    test: LabTestResult
    historical_results: Optional[List[Dict[str, Any]]] = Field(
        default=None, 
        description="Geçmiş test sonuçları - herhangi bir format"
    )
    
    class Config:
        extra = "allow"

class SingleSessionRequest(BaseModel):
    session_tests: List[LabTestResult]
    session_date: str = Field(description="Test seansı tarihi")
    laboratory: str = Field(description="Laboratuvar adı")
    session_summary: Optional[Dict[str, Any]] = Field(
        default=None, 
        description="Seans özeti - herhangi bir format"
    )
    
    class Config:
        extra = "allow"

class MultipleLabRequest(BaseModel):
    tests: List[LabTestResult]
    total_test_sessions: int = Field(description="Toplam test seansı sayısı")
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
class ChatMessageRequest(BaseModel):
    text: str = Field(description="Kullanıcı mesajı")
    conversation_id: int = Field(description="Konuşma ID'si")
    
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

class LabBatchPayload(BaseModel):
    results: List[Dict[str, Any]]

class RecommendationItem(BaseModel):
    id: Optional[str] = None
    name: str
    reason: str
    source: Literal["consensus", "assistant"] = "consensus"

class AnalyzeResponse(BaseModel):
    recommendations: List[RecommendationItem] = Field(default_factory=list)
    analysis: Dict[str, Any] = Field(default_factory=dict)
    disclaimer: str = "Bu içerik bilgilendirme amaçlıdır; tıbbi tanı/tedavi için hekiminize başvurun."

