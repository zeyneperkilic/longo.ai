"""Sağlık künyesi verisini form + lab ile derler. Quiz kullanılmaz."""
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
    summaries = get_user_ai_messages_by_type(db, user_id, "lab_summary", limit=3)
    for msg in summaries:
        payload = msg.request_payload or {}
        tests = payload.get("tests") or payload.get("lab_results") or []
        if isinstance(tests, list) and tests:
            return [_normalize_lab_item(t) for t in tests if isinstance(t, dict)]

    sessions = get_user_ai_messages_by_type(db, user_id, "lab_session", limit=3)
    for msg in sessions:
        payload = msg.request_payload or {}
        tests = payload.get("session_tests") or payload.get("tests") or []
        if isinstance(tests, list) and tests:
            return [_normalize_lab_item(t) for t in tests if isinstance(t, dict)]

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


def _merge_profile(form_data: dict | None, profile_snapshot: dict | None) -> dict:
    """form.emergency + form.personal + diğer düz alanlar + legacy profile birleşimi."""
    merged: dict = {}
    if profile_snapshot:
        merged.update(profile_snapshot)
    form = form_data or {}
    flat_sections = (
        "personal",
        "emergency",
        "lifestyle",
        "accessibility",
        "womens_health",
        "mens_health",
        "directives",
        "notes",
    )
    for section in flat_sections:
        part = form.get(section)
        if isinstance(part, dict):
            merged.update(part)
    list_keys = {
        "allergies",
        "medications",
        "diagnoses",
        "emergency_contacts",
        "drug_intolerances",
        "past_conditions",
        "surgeries",
        "hospitalizations",
        "supplements",
        "vaccinations",
        "family_history",
        "devices",
        "doctors",
    }
    for k, v in form.items():
        if k not in flat_sections and k not in list_keys and not isinstance(v, (list, dict)):
            merged[k] = v
    return merged


def _list_section_rows(items: list | None, fields: list[tuple[str, str]]) -> list[str]:
    if not items or not isinstance(items, list):
        return []
    lines = []
    for item in items:
        if not isinstance(item, dict):
            continue
        parts = []
        for key, label in fields:
            val = item.get(key)
            if val:
                parts.append(f"{label}: {val}")
        if parts:
            lines.append(" · ".join(parts))
    return lines


def build_health_card_data(
    db: Session,
    external_user_id: str,
    profile_snapshot: dict | None = None,
    form_data: dict | None = None,
) -> dict:
    profile = _merge_profile(form_data, profile_snapshot)
    labs = _extract_labs(db, external_user_id)
    form = form_data or {}

    full_name = _pick(profile, "full_name", "name", "ad_soyad", "adSoyad")
    birth_date = _pick(profile, "birth_date", "birthDate", "dogum_tarihi")
    age = _pick(profile, "age", "yas")
    sex = _pick(profile, "sex", "gender", "cinsiyet")
    blood_type = _pick(profile, "blood_type", "bloodType", "kan_grubu")
    allergies = _pick(profile, "critical_allergies", "allergies", "kritik_alerjiler")
    medications = _pick(profile, "critical_medications", "medications")
    diagnoses = _pick(profile, "active_diagnoses", "diagnoses", "chronic_conditions")
    notes = _pick(profile, "special_notes", "emergency_notes")

    contacts = form.get("emergency_contacts") if isinstance(form.get("emergency_contacts"), list) else []
    emergency_contact = _pick(profile, "emergency_contact", "acil_temas")
    if not emergency_contact and contacts:
        c0 = contacts[0] if isinstance(contacts[0], dict) else {}
        emergency_contact = " · ".join(
            str(x) for x in [c0.get("name"), c0.get("relation"), c0.get("phone")] if x
        )

    allergy_lines = _list_section_rows(
        form.get("allergies") if isinstance(form.get("allergies"), list) else None,
        [("allergen", "Alerjen"), ("type", "Tür"), ("reaction", "Reaksiyon"), ("severity", "Şiddet"), ("plan", "Plan")],
    )
    medication_lines = _list_section_rows(
        form.get("medications") if isinstance(form.get("medications"), list) else None,
        [("name", "İlaç"), ("dose", "Doz"), ("frequency", "Sıklık"), ("reason", "Neden"), ("prescriber", "Hekim")],
    )
    diagnosis_lines = _list_section_rows(
        form.get("diagnoses") if isinstance(form.get("diagnoses"), list) else None,
        [("name", "Tanı"), ("status", "Durum"), ("treatment", "Tedavi"), ("doctor", "Hekim")],
    )
    supplement_lines = _list_section_rows(
        form.get("supplements") if isinstance(form.get("supplements"), list) else None,
        [("name", "Ürün"), ("dose", "Doz"), ("frequency", "Sıklık"), ("purpose", "Amaç")],
    )
    surgery_lines = _list_section_rows(
        form.get("surgeries") if isinstance(form.get("surgeries"), list) else None,
        [("date", "Tarih"), ("procedure", "İşlem"), ("hospital", "Kurum"), ("complications", "Komplikasyon")],
    )
    vaccine_lines = _list_section_rows(
        form.get("vaccinations") if isinstance(form.get("vaccinations"), list) else None,
        [("name", "Aşı"), ("date", "Tarih"), ("dose", "Doz"), ("next_due", "Sonraki")],
    )
    family_lines = _list_section_rows(
        form.get("family_history") if isinstance(form.get("family_history"), list) else None,
        [("relation", "Yakınlık"), ("condition", "Hastalık"), ("age_at_diagnosis", "Tanı yaşı")],
    )
    doctor_lines = _list_section_rows(
        form.get("doctors") if isinstance(form.get("doctors"), list) else None,
        [("name", "Hekim"), ("specialty", "Branş"), ("phone", "İletişim"), ("next_appointment", "Randevu")],
    )
    device_lines = _list_section_rows(
        form.get("devices") if isinstance(form.get("devices"), list) else None,
        [("device", "Cihaz"), ("location", "Yer"), ("model", "Model"), ("mri_safe", "MR")],
    )
    intolerance_lines = _list_section_rows(
        form.get("drug_intolerances") if isinstance(form.get("drug_intolerances"), list) else None,
        [("drug", "İlaç"), ("effect", "Yan etki"), ("alternative", "Alternatif")],
    )
    past_lines = _list_section_rows(
        form.get("past_conditions") if isinstance(form.get("past_conditions"), list) else None,
        [("name", "Hastalık"), ("period", "Dönem"), ("outcome", "Sonuç")],
    )
    hospital_lines = _list_section_rows(
        form.get("hospitalizations") if isinstance(form.get("hospitalizations"), list) else None,
        [("dates", "Tarih"), ("reason", "Neden"), ("diagnosis", "Tanı"), ("outcome", "Sonuç")],
    )

    return {
        "external_user_id": external_user_id,
        "updated_at": datetime.utcnow().strftime("%d.%m.%Y %H:%M"),
        "profile": profile,
        "form_data": form,
        "emergency_summary": {
            "full_name": full_name or "Belirtilmemiş",
            "birth_date": birth_date,
            "age": age,
            "sex": sex,
            "blood_type": blood_type or "Bilinmiyor",
            "allergies": allergies or ("; ".join(allergy_lines) if allergy_lines else "Bilinmiyor"),
            "medications": medications or ("; ".join(medication_lines) if medication_lines else "Bilinmiyor"),
            "diagnoses": diagnoses or ("; ".join(diagnosis_lines) if diagnosis_lines else "Bilinmiyor"),
            "emergency_contact": emergency_contact,
            "notes": notes,
            "pregnancy_status": _pick(profile, "pregnancy_status"),
            "implants_devices": _pick(profile, "implants_devices"),
            "communication_support": _pick(profile, "communication_support"),
            "phone": _pick(profile, "phone"),
            "family_doctor": _pick(profile, "family_doctor"),
            "preferred_hospital": _pick(profile, "preferred_hospital"),
            "height_cm": _pick(profile, "height_cm"),
            "weight_kg": _pick(profile, "weight_kg"),
        },
        "allergy_lines": allergy_lines,
        "medication_lines": medication_lines,
        "diagnosis_lines": diagnosis_lines,
        "supplement_lines": supplement_lines,
        "surgery_lines": surgery_lines,
        "vaccine_lines": vaccine_lines,
        "family_lines": family_lines,
        "doctor_lines": doctor_lines,
        "device_lines": device_lines,
        "intolerance_lines": intolerance_lines,
        "past_lines": past_lines,
        "hospital_lines": hospital_lines,
        "contact_lines": _list_section_rows(
            contacts,
            [("name", "Ad"), ("relation", "Yakınlık"), ("phone", "Tel"), ("notes", "Not")],
        ),
        "labs": labs,
        "has_labs": bool(labs),
        "has_form": bool(form),
        "disclaimer": (
            "Bu belge acil durumlarda ve sağlık hizmeti görüşmelerinde kullanılmak üzere "
            "hazırlanmıştır. Tek başına tıbbi rapor veya reçete yerine geçmez. "
            "Sağlık kararlarınız için hekiminize danışınız."
        ),
    }
