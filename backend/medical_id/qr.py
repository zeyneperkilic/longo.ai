"""QR PNG üretimi — qrcode yoksa SVG data URL fallback."""
from __future__ import annotations

from io import BytesIO


def make_qr_png_bytes(url: str) -> bytes:
    try:
        import qrcode
    except ImportError as e:
        raise RuntimeError(
            "qrcode paketi yüklü değil. requirements.txt içine qrcode ekleyin."
        ) from e

    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=8,
        border=2,
    )
    qr.add_data(url)
    qr.make(fit=True)

    try:
        img = qr.make_image(fill_color="#174A70", back_color="white")
    except Exception:
        # Pillow yoksa default factory
        img = qr.make_image()

    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
