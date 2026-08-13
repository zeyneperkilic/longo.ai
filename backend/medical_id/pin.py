"""Künye kilidi — şimdilik sabit PIN (1234). Sonra TC Kimlik'e geçilecek."""
from __future__ import annotations

import hashlib
import hmac
import os


DEFAULT_MEDICAL_ID_PIN = os.getenv("MEDICAL_ID_DEFAULT_PIN", "1234")


def _pepper() -> str:
    return (
        os.getenv("MEDICAL_ID_PIN_PEPPER")
        or os.getenv("AUTH_PASSWORD")
        or "longopass-medical-id-dev-pepper"
    )


def hash_pin(value: str | None) -> str:
    pin = (value or "").strip()
    raw = f"lp-medical-id-pin:v1:{_pepper()}:{pin}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def verify_pin(value: str | None, pin_hash: str | None) -> bool:
    """
    pin_hash yoksa (eski kayıt) varsayılan PIN ile aç.
    İleride TC doğrulamaya geçince bu modül değişir.
    """
    candidate = (value or "").strip()
    if pin_hash:
        return hmac.compare_digest(hash_pin(candidate), pin_hash)
    return hmac.compare_digest(candidate, DEFAULT_MEDICAL_ID_PIN)


def default_pin_hash() -> str:
    return hash_pin(DEFAULT_MEDICAL_ID_PIN)
