"""Sağlık künyesi verisini mevcut ai_messages (quiz + lab) + opsiyonel profil ile derler."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from backend.db import get_user_ai_messages_by_type


def _pick(d: dict | None, *keys: str, default: Any = None) -> Any:
    if not d:
        return default
    for key in keys:
        value = d.get(key)
        if value is not None and value != "" and value != "N/A":
            return value
    return default


def _normalize_lab_item(item: dict) -> dict:
    name = _pick(item, "name", "test_name", "testName", default="Test")
    value = _pick(item, "value", "result", "last_result", default="—")
    unit = _pick(item, "unit", default="")
    ref = _pick(item, "reference_range", "referenceRange", "ref", default="—")
    status = _pick(item, "status", default="")
    date = _pick(item, "test_date", "date", default="")
    return {
        "name": str(name),
        "value": str(value),
        "unit": str(unit) if unit else "",
        "reference_range": str(ref),
        "status": str(status) if status else "",
        "date": str(date) if date else "",
    }


def _extract_labs(db: Session, user_id: str, limit: int = 40) -> list[dict]:
    """En güncel lab setini çıkar (lab_summary öncelikli)."""
    # 1) lab_summary
    summaries = get_user_ai_messages_by_type(db, user_id, "lab_summary", limit=3)
    for msg in summaries:
        payload = msg.request_payload or {}
        tests = payload.get("tests") or payload.get("lab_results") or []
        if isinstance(tests, list) and tests:
            return [_normalize_lab_item(t) for t in tests if isinstance(t, dict)]

    # 2) lab_session
    sessions = get_user_ai_messages_by_type(db, user_id, "lab_session", limit=3)
    for msg in sessions:
        payload = msg.request_payload or {}
        tests = payload.get("session_tests") or payload.get("tests") or []
        if isinstance(tests, list) and tests:
            return [_normalize_lab_item(t) for t in tests if isinstance(t, dict)]

    # 3) lab_single birleştir
    singles = get_user_ai_messages_by_type(db, user_id, "lab_single", limit=limit)
    labs = []
    for msg in singles:
        payload = msg.request_payload or {}
        test = payload.get("test")
        if isinstance(test, dict):
            item = _normalize_lab_item(test)
            if not item.get("date") and getattr(msg, "created_at", None):
                item["date"] = msg.created_at.strftime("%d.%m.%Y")
            labs.append(item)
    return labs


def _extract_quiz(db: Session, user_id: str) -> dict:
    messages = get_user_ai_messages_by_type(db, user_id, "quiz", limit=1)
    if not messages:
        return {}
    payload = messages[0].request_payload or {}
    # Bazı isteklerde quiz_answers altında gelir
    answers = payload.get("quiz_answers")
    if isinstance(answers, dict) and answers:
        return answers
    # Flat payload — meta alanları çıkar
    skip = {"available_supplements", "availableSupplements"}
    return {k: v for k, v in payload.items() if k not in skip and v not in (None, "", "N/A")}


def _quiz_display_rows(quiz: dict) -> list[dict]:
    """Quiz dict → okunabilir satırlar (ham key'ler korunur, label güzelleştirilir)."""
    label_map = {
        "age": "Yaş",
        "age_range": "Yaş Aralığı",
        "sex": "Cinsiyet",
        "gender": "Cinsiyet",
        "height": "Boy",
        "weight": "Kilo",
        "blood_type": "Kan Grubu",
        "allergies": "Alerjiler",
        "allergy": "Alerjiler",
        "medications": "İlaçlar",
        "current_medications": "Güncel İlaçlar",
        "chronic_conditions": "Kronik Durumlar",
        "family_history": "Aile Öyküsü",
        "health_goals": "Sağlık Hedefleri",
        "lifestyle": "Yaşam Tarzı",
        "diet": "Beslenme",
        "sleep_quality": "Uyku",
        "sleep": "Uyku",
        "stress_level": "Stres",
        "stress": "Stres",
        "exercise_frequency": "Egzersiz",
        "activity": "Aktivite",
        "smoking": "Sigara",
        "alcohol": "Alkol",
        "pregnancy": "Gebelik",
    }
    rows = []
    for key, value in quiz.items():
        if isinstance(value, (dict, list)):
            display = ", ".join(str(x) for x in value) if isinstance(value, list) else str(value)
        else:
            display = str(value)
        label = label_map.get(key, key.replace("_", " ").title())
        rows.append({"key": key, "label": label, "value": display})
    return rows


def build_health_card_data(
    db: Session,
    external_user_id: str,
    profile_snapshot: dict | None = None,
) -> dict:
    """
    Künye için birleşik veri.
    profile_snapshot: Ideasoft'tan gelen kayıt bilgileri (ad, doğum tarihi, kan grubu vb.)
    Quiz'deki yaş aralığı yerine net yaş/doğum tarihi buradan gelir — sonradan eklenebilir.
    """
    profile = profile_snapshot or {}
    quiz = _extract_quiz(db, external_user_id)
    labs = _extract_labs(db, external_user_id)

    # Acil özet: profil öncelikli, yoksa quiz
    full_name = _pick(profile, "full_name", "name", "ad_soyad", "adSoyad")
    birth_date = _pick(profile, "birth_date", "birthDate", "dogum_tarihi")
    age = _pick(profile, "age", "yas") or _pick(quiz, "age", "age_range")
    sex = _pick(profile, "sex", "gender", "cinsiyet") or _pick(quiz, "sex", "gender")
    blood_type = _pick(profile, "blood_type", "bloodType", "kan_grubu") or _pick(quiz, "blood_type")
    allergies = _pick(profile, "allergies", "kritik_alerjiler") or _pick(quiz, "allergies", "allergy")
    medications = _pick(profile, "medications", "critical_medications") or _pick(
        quiz, "current_medications", "medications"
    )
    diagnoses = _pick(profile, "diagnoses", "active_diagnoses", "chronic_conditions") or _pick(
        quiz, "chronic_conditions"
    )
    emergency_contact = _pick(profile, "emergency_contact", "acil_temas")
    notes = _pick(profile, "emergency_notes", "special_notes")

    updated_at = datetime.utcnow().strftime("%d.%m.%Y %H:%M")

    return {
        "external_user_id": external_user_id,
        "updated_at": updated_at,
        "profile": profile,
        "emergency_summary": {
            "full_name": full_name or "Belirtilmemiş",
            "birth_date": birth_date,
            "age": age,
            "sex": sex,
            "blood_type": blood_type or "Bilinmiyor",
            "allergies": allergies or "Bilinmiyor",
            "medications": medications or "Bilinmiyor",
            "diagnoses": diagnoses or "Bilinmiyor",
            "emergency_contact": emergency_contact,
            "notes": notes,
        },
        "quiz_rows": _quiz_display_rows(quiz),
        "has_quiz": bool(quiz),
        "labs": labs,
        "has_labs": bool(labs),
        "disclaimer": (
            "Bu belge acil durumlarda ve sağlık hizmeti görüşmelerinde kullanılmak üzere "
            "hazırlanmıştır. Tek başına tıbbi rapor veya reçete yerine geçmez. "
            "Sağlık kararlarınız için hekiminize danışınız."
        ),
    }
