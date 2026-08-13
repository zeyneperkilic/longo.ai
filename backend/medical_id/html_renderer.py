"""Sağlık künyesi HTML render — patron draft'ının V1 özeti (acil + quiz + lab)."""
from __future__ import annotations

import html


def _esc(value) -> str:
    if value is None:
        return "—"
    return html.escape(str(value))


def _row(label: str, value) -> str:
    return f"""
    <div class="row">
      <div class="label">{_esc(label)}</div>
      <div class="value">{_esc(value)}</div>
    </div>
    """


def render_health_card_html(data: dict) -> str:
    em = data.get("emergency_summary") or {}
    quiz_rows = data.get("quiz_rows") or []
    labs = data.get("labs") or []

    quiz_html = ""
    if quiz_rows:
        quiz_html = "".join(_row(r["label"], r["value"]) for r in quiz_rows)
    else:
        quiz_html = '<p class="empty">Quiz verisi henüz yok.</p>'

    lab_rows = ""
    if labs:
        for lab in labs:
            unit = f" {lab['unit']}" if lab.get("unit") else ""
            status = f" · {lab['status']}" if lab.get("status") else ""
            date = f'<div class="meta">{_esc(lab.get("date"))}</div>' if lab.get("date") else ""
            lab_rows += f"""
            <div class="lab-item">
              <div class="lab-name">{_esc(lab.get("name"))}</div>
              <div class="lab-value">{_esc(lab.get("value"))}{html.escape(unit)}{html.escape(status)}</div>
              <div class="meta">Ref: {_esc(lab.get("reference_range"))}</div>
              {date}
            </div>
            """
    else:
        lab_rows = '<p class="empty">Lab sonucu henüz yok.</p>'

    age_line = em.get("age") or "—"
    if em.get("birth_date"):
        age_line = f"{em.get('birth_date')} / {em.get('age') or '—'}"

    return f"""<!DOCTYPE html>
<html lang="tr">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>LongoPass · Kişisel Sağlık Künyesi</title>
  <style>
    :root {{
      --navy: #174A70;
      --blue: #1F6F9F;
      --cyan: #25B8C7;
      --bg: #F5FAFC;
      --card: #ffffff;
      --line: #D7EAF2;
      --text: #163B59;
      --muted: #2F526B;
      --danger: #B42318;
      --warn-bg: #FFF4ED;
      --warn-border: #F7C6A8;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "Segoe UI", system-ui, -apple-system, sans-serif;
      background: linear-gradient(180deg, #E8F4FA 0%, var(--bg) 40%, #ffffff 100%);
      color: var(--text);
      line-height: 1.45;
    }}
    .wrap {{ max-width: 720px; margin: 0 auto; padding: 20px 16px 48px; }}
    .brand {{
      display: flex; align-items: center; justify-content: space-between;
      margin-bottom: 16px;
    }}
    .logo {{
      font-weight: 800; letter-spacing: 0.02em; color: var(--navy); font-size: 1.15rem;
    }}
    .badge {{
      background: #DFF3FA; color: var(--navy); border: 1px solid #BFDCE8;
      border-radius: 999px; padding: 6px 12px; font-size: 0.75rem; font-weight: 600;
    }}
    h1 {{
      margin: 0 0 6px; font-size: 1.55rem; color: var(--navy);
    }}
    .subtitle {{ color: var(--muted); margin: 0 0 18px; font-size: 0.92rem; }}
    .card {{
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: 16px;
      box-shadow: 0 10px 28px rgba(22, 59, 89, 0.08);
      padding: 18px 16px;
      margin-bottom: 14px;
    }}
    .card h2 {{
      margin: 0 0 12px; font-size: 1rem; color: var(--navy);
      display: flex; align-items: center; gap: 8px;
    }}
    .card h2 .dot {{
      width: 8px; height: 8px; border-radius: 50%; background: var(--cyan); display: inline-block;
    }}
    .emergency {{
      border-color: var(--warn-border);
      background: linear-gradient(180deg, var(--warn-bg), #ffffff);
    }}
    .row {{
      display: grid; grid-template-columns: 140px 1fr; gap: 8px;
      padding: 8px 0; border-bottom: 1px solid #EEF5F9;
    }}
    .row:last-child {{ border-bottom: none; }}
    .label {{ color: var(--muted); font-size: 0.82rem; font-weight: 600; }}
    .value {{ color: var(--text); font-size: 0.95rem; word-break: break-word; }}
    .lab-item {{
      padding: 10px 0; border-bottom: 1px solid #EEF5F9;
    }}
    .lab-item:last-child {{ border-bottom: none; }}
    .lab-name {{ font-weight: 700; color: var(--navy); }}
    .lab-value {{ margin-top: 2px; }}
    .meta {{ color: var(--muted); font-size: 0.8rem; margin-top: 2px; }}
    .empty {{ color: var(--muted); margin: 0; }}
    .disclaimer {{
      font-size: 0.8rem; color: var(--muted); background: #fff;
      border: 1px dashed var(--line); border-radius: 12px; padding: 12px 14px;
    }}
    .updated {{ font-size: 0.8rem; color: var(--muted); margin-top: 8px; }}
    @media (max-width: 520px) {{
      .row {{ grid-template-columns: 1fr; gap: 2px; }}
    }}
  </style>
</head>
<body>
  <div class="wrap">
    <div class="brand">
      <div class="logo">LONGOPASS</div>
      <div class="badge">Medical ID · V1</div>
    </div>
    <h1>Kişisel Sağlık Künyesi</h1>
    <p class="subtitle">Personal Health Record · Acil durum ve sağlık görüşmeleri için özet</p>

    <section class="card emergency">
      <h2><span class="dot"></span> Acil Sağlık Özeti</h2>
      {_row("Ad Soyad", em.get("full_name"))}
      {_row("Doğum / Yaş", age_line)}
      {_row("Cinsiyet", em.get("sex") or "—")}
      {_row("Kan Grubu", em.get("blood_type"))}
      {_row("Kritik Alerjiler", em.get("allergies"))}
      {_row("Kritik İlaçlar", em.get("medications"))}
      {_row("Aktif Tanılar", em.get("diagnoses"))}
      {_row("Acil Temas", em.get("emergency_contact") or "—")}
      {_row("Özel Husus", em.get("notes") or "—")}
      <div class="updated">Son güncelleme: {_esc(data.get("updated_at"))}</div>
    </section>

    <section class="card">
      <h2><span class="dot"></span> Sağlık Profili (Quiz)</h2>
      {quiz_html}
    </section>

    <section class="card">
      <h2><span class="dot"></span> Laboratuvar Sonuçları</h2>
      {lab_rows}
    </section>

    <p class="disclaimer">{_esc(data.get("disclaimer"))}</p>
  </div>
</body>
</html>
"""
