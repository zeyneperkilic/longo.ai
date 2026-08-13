"""TC Kimlik No doğrulama ve hash — düz TC asla saklanmaz / loglanmaz."""
from __future__ import annotations

import hashlib
import hmac
import os
import re


def normalize_tc(value: str | None) -> str:
    if value is None:
        return ""
    digits = re.sub(r"\D", "", str(value))
    return digits


def is_valid_tc_kimlik(value: str | None) -> bool:
    """Türkiye TC Kimlik No algoritması (11 hane)."""
    tc = normalize_tc(value)
    if len(tc) != 11 or not tc.isdigit():
        return False
    if tc[0] == "0":
        return False
    digits = [int(c) for c in tc]
    odd_sum = digits[0] + digits[2] + digits[4] + digits[6] + digits[8]
    even_sum = digits[1] + digits[3] + digits[5] + digits[7]
    check10 = (odd_sum * 7 - even_sum) % 10
    if check10 != digits[9]:
        return False
    if sum(digits[:10]) % 10 != digits[10]:
        return False
    return True


def _pepper() -> str:
    return (
        os.getenv("MEDICAL_ID_TC_PEPPER")
        or os.getenv("AUTH_PASSWORD")
        or "longopass-medical-id-dev-pepper"
    )


def hash_tc_kimlik(value: str) -> str:
    """One-way hash (pepper + SHA-256). Düz TC dönülmez."""
    tc = normalize_tc(value)
    raw = f"lp-medical-id:v1:{_pepper()}:{tc}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def verify_tc_kimlik(value: str, tc_hash: str | None) -> bool:
    if not tc_hash:
        return False
    candidate = hash_tc_kimlik(value)
    return hmac.compare_digest(candidate, tc_hash)
