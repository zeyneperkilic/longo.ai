"""
Lab sonuçlarında AI-based risk detection modülü
LLM'e sorarak gerçekten high risk olan durumları tespit eder
"""
import json
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from datetime import datetime, timedelta


def detect_high_risk_with_ai(
    tests: List[Dict[str, Any]],
    ai_lab_summary: Dict[str, Any],
    db: Session,
    external_user_id: str,
    user_level: Optional[int] = None,
    lab_summary_id: Optional[int] = None,
    new_tests: Optional[List[Dict[str, Any]]] = None,
) -> Optional[Dict[str, Any]]:
    """
    AI kullanarak lab sonuçlarında gerçekten high risk olup olmadığını tespit et
    
    Args:
        tests: Tüm lab test sonuçları listesi (geçmiş + yeni)
        ai_lab_summary: AI'nin lab summary response'u
        db: Database session
        external_user_id: Kullanıcı ID'si
        user_level: Kullanıcı seviyesi
        lab_summary_id: İlgili lab_summary ai_messages kaydının ID'si
        new_tests: Yeni eklenen testler (is_new=True işaretli, duplicate kontrolü için)
        
    Returns:
        Risk tespit edildiyse risk bilgisi dict'i, yoksa None
    """
    try:
        from backend.openrouter_client import get_ai_response
        
        # Lab testlerini formatla - SADECE YENİ TESTLERİ GÖNDER (geçmiş testleri değil)
        # Geçmiş testler AI summary'de bahsediliyor olabilir, bu yüzden sadece yeni testlere bakmalıyız
        tests_to_analyze = new_tests if new_tests else tests  # Yeni testler varsa onları kullan
        
        tests_info = []
        for test in tests_to_analyze:
            test_info = f"- {test.get('name', 'Bilinmeyen')}: {test.get('value', 'N/A')}"
            if test.get('unit'):
                test_info += f" {test['unit']}"
            if test.get('reference_range'):
                test_info += f" (Referans: {test['reference_range']})"
            if test.get('status'):
                test_info += f" [Durum: {test['status']}]"
            tests_info.append(test_info)
        
        tests_text = "\n".join(tests_info)
        
        # AI summary'yi text'e çevir (ama sadece bu seansın özeti için kullanılacak)
        summary_text = json.dumps(ai_lab_summary, ensure_ascii=False, indent=2)
        
        # AI'ya risk detection sorusu
        system_prompt = """Sen bir tıbbi risk değerlendirme uzmanısın. Lab sonuçlarını analiz ederek gerçekten HIGH RISK olan durumları tespit ediyorsun.

ÖNEMLİ KURALLAR:
1. SADECE gerçekten ciddi, acil müdahale gerektiren durumları HIGH RISK olarak işaretle
2. Her referans dışı değer HIGH RISK değildir - hafif anormallikler normal olabilir
3. HIGH RISK kriterleri:
   - Kanser belirteçleri pozitif
   - Kritik organ fonksiyon bozuklukları (karaciğer, böbrek, kalp)
   - Acil müdahale gerektiren enfeksiyonlar
   - Ciddi anemi veya kanama riski
   - Diyabetik ketoasidoz riski
   - Kritik elektrolit dengesizlikleri
   - Ciddi hormonal bozukluklar
4. LOW/MEDIUM risk durumları:
   - Hafif vitamin eksiklikleri
   - Sınırda kolesterol değerleri
   - Normal varyasyonlar
   - Yaşla ilgili normal değişiklikler

SADECE JSON formatında yanıt ver:
{
  "is_high_risk": true/false,
  "risk_level": "high" veya "low" (sadece is_high_risk true ise),
  "risk_reason": "Kısa açıklama (sadece is_high_risk true ise)",
  "risky_tests": ["Test adı 1", "Test adı 2"] (sadece is_high_risk true ise)
}"""

        user_prompt = f"""LAB TEST SONUÇLARI (BU SEANS - YENİ EKLENEN TESTLER):
{tests_text}

ÖNEMLİ: SADECE YUKARIDAKİ TEST SONUÇLARINA BAK! Geçmiş testlere veya önceki seanslara bakma!
Eğer yukarıdaki testlerde TÜM DEĞERLER NORMAL ARALIKTAYSA → is_high_risk = false
Eğer yukarıdaki testlerde GERÇEKTEN CİDDİ BİR ANORMALLİK VARSA → is_high_risk = true

AI LAB ANALİZİ (SADECE REFERANS İÇİN):
{summary_text}

Bu lab sonuçlarında gerçekten HIGH RISK tespit eden bir durum var mı? 
- SADECE yukarıdaki test sonuçlarına bak
- Geçmiş testlere bakma
- Normal değerler → is_high_risk = false
- Ciddi anormallikler → is_high_risk = true

Yukarıdaki kurallara göre değerlendir ve SADECE JSON formatında yanıt ver."""

        # AI'ya sor (async fonksiyonu sync context'te çalıştır)
        print(f"🤖 AI'ya risk detection sorusu gönderiliyor...")
        import asyncio
        
        # Thread içinde async çalıştırmak için yeni event loop oluştur
        try:
            # Mevcut loop'u kontrol et
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                raise RuntimeError("Loop closed")
        except RuntimeError:
            # Yeni loop oluştur
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        try:
            ai_response = loop.run_until_complete(
                get_ai_response(
                    system_prompt=system_prompt,
                    user_message=user_prompt
                )
            )
            print(f"📥 AI response alındı (uzunluk: {len(ai_response) if ai_response else 0})")
        except Exception as ai_error:
            print(f"❌ AI response alma hatası: {ai_error}")
            import traceback
            traceback.print_exc()
            return None
        
        # Response'u parse et
        try:
            # JSON temizleme
            cleaned_response = ai_response.strip()
            if cleaned_response.startswith('```json'):
                json_start = cleaned_response.find('```json') + 7
                json_end = cleaned_response.find('```', json_start)
                if json_end != -1:
                    cleaned_response = cleaned_response[json_start:json_end].strip()
            elif cleaned_response.startswith('```'):
                json_start = cleaned_response.find('```') + 3
                json_end = cleaned_response.find('```', json_start)
                if json_end != -1:
                    cleaned_response = cleaned_response[json_start:json_end].strip()
            
            risk_data = json.loads(cleaned_response)
            print(f"📊 AI risk data parse edildi: is_high_risk={risk_data.get('is_high_risk')}")
            
            # High risk tespit edildiyse kaydet
            if risk_data.get('is_high_risk') == True:
                risk_level = risk_data.get('risk_level', 'high')
                risk_reason = risk_data.get('risk_reason', 'AI tarafından high risk tespit edildi')
                risky_tests = risk_data.get('risky_tests', [])
                
                # Duplicate kontrolü: Son 7 gün içinde aynı kullanıcı için high risk kaydı var mı?
                from backend.db import get_high_risk_users
                
                # Yeni testlerde risk varsa duplicate kontrolü yapma (mutlaka kayıt yap)
                has_new_test_risk = False
                if new_tests:
                    # Yeni testlerin adlarını çıkar
                    new_test_names = [t.get('name', '').lower().strip() for t in new_tests if t.get('name')]
                    # Riskli testlerden yeni testlerde olanları bul
                    risky_new_tests = [rt for rt in risky_tests if rt.lower().strip() in new_test_names]
                    if risky_new_tests:
                        has_new_test_risk = True
                        print(f"🆕 Yeni testlerde risk tespit edildi: {risky_new_tests}")
                
                # Duplicate kontrolü (sadece yeni testlerde risk yoksa)
                is_duplicate = False
                if not has_new_test_risk:
                    recent_risks = get_high_risk_users(
                        db=db,
                        external_user_id=external_user_id,
                        limit=5  # Son 5 kaydı kontrol et
                    )
                    
                    # Son 7 gün içindeki kayıtları filtrele
                    seven_days_ago = datetime.utcnow() - timedelta(days=7)
                    recent_risks_filtered = [
                        r for r in recent_risks 
                        if r.detected_at and r.detected_at >= seven_days_ago
                    ]
                    
                    # Duplicate kontrolü: Aynı riskli testler ve aynı risk seviyesi var mı?
                    if recent_risks_filtered:
                        for recent_risk in recent_risks_filtered:
                            recent_risky_tests = recent_risk.risky_tests or []
                            
                            # Riskli testleri karşılaştır (set kullanarak sıra farkını göz ardı et)
                            if (set(risky_tests) == set(recent_risky_tests) and 
                                recent_risk.risk_level == risk_level):
                                is_duplicate = True
                                print(f"⚠️ Duplicate risk kaydı tespit edildi: User ID {external_user_id}")
                                print(f"   Aynı riskli testler: {risky_tests}")
                                print(f"   Aynı risk seviyesi: {risk_level}")
                                print(f"   Önceki kayıt ID: {recent_risk.id}, Tarih: {recent_risk.detected_at}")
                                break
                
                # Duplicate değilse veya yeni riskli testler varsa kaydet
                if not is_duplicate:
                    from backend.db import create_high_risk_user
                    
                    risk_record = create_high_risk_user(
                        db=db,
                        external_user_id=external_user_id,
                        user_level=user_level,
                        lab_summary_id=lab_summary_id,
                        risk_level=risk_level,
                        risk_reason=risk_reason,
                        risky_tests=risky_tests,
                        ai_analysis=ai_response,
                    )
                    
                    print(f"🚨 HIGH RISK tespit edildi ve kaydedildi: User ID {external_user_id}, Risk Level: {risk_level}")
                    print(f"   Risk Reason: {risk_reason}")
                    print(f"   Risky Tests: {risky_tests}")
                    print(f"   Kayıt ID: {risk_record.id}")
                    
                    return {
                        'is_high_risk': True,
                        'risk_level': risk_level,
                        'risk_reason': risk_reason,
                        'risky_tests': risky_tests,
                        'risk_record_id': risk_record.id,
                        'is_new_risk': True,
                    }
                else:
                    # Duplicate ama bilgiyi döndür (kayıt yapılmadı)
                    print(f"ℹ️ Duplicate risk kaydı atlandı: User ID {external_user_id}")
                    return {
                        'is_high_risk': True,
                        'risk_level': risk_level,
                        'risk_reason': risk_reason,
                        'risky_tests': risky_tests,
                        'risk_record_id': None,
                        'is_new_risk': False,
                        'is_duplicate': True,
                    }
            else:
                print(f"✅ HIGH RISK tespit edilmedi: User ID {external_user_id}")
                return None
                
        except json.JSONDecodeError as e:
            print(f"⚠️ Risk detection AI response parse hatası: {e}")
            print(f"   Raw response: {ai_response[:200]}")
            return None
            
    except Exception as e:
        print(f"❌ Risk detection hatası: {e}")
        import traceback
        traceback.print_exc()
        return None

