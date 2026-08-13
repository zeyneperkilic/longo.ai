"""Künye kilit ekranı HTML."""
from __future__ import annotations

import html


def render_unlock_page(token: str, error: str | None = None) -> str:
    err = f'<p class="error">{html.escape(error)}</p>' if error else ""
    return f"""<!DOCTYPE html>
<html lang="tr">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>LongoPass · Sağlık Künyesi</title>
  <style>
    :root {{ --navy:#174A70; --cyan:#25B8C7; --bg:#F5FAFC; --line:#D7EAF2; --muted:#2F526B; --danger:#B42318; }}
    body {{ margin:0; font-family:"Segoe UI",system-ui,sans-serif; background:linear-gradient(180deg,#E8F4FA,#fff); color:#163B59; }}
    .box {{ max-width:420px; margin:48px auto; padding:24px; background:#fff; border:1px solid var(--line); border-radius:16px; box-shadow:0 12px 30px rgba(22,59,89,.1); }}
    h1 {{ margin:0 0 8px; font-size:1.3rem; color:var(--navy); }}
    p {{ color:var(--muted); font-size:.92rem; }}
    label {{ display:block; font-weight:600; margin:16px 0 6px; }}
    input {{ width:100%; padding:12px 14px; border:1px solid var(--line); border-radius:10px; font-size:1rem; box-sizing:border-box; }}
    button {{ margin-top:16px; width:100%; padding:12px; border:0; border-radius:10px; background:linear-gradient(90deg,#174A70,#1F6F9F,#25B8C7); color:#fff; font-weight:700; font-size:1rem; cursor:pointer; }}
    .error {{ color:var(--danger); background:#FFF1F0; border:1px solid #F5C2C0; padding:10px 12px; border-radius:10px; }}
    .logo {{ font-weight:800; color:var(--navy); margin-bottom:12px; letter-spacing:0.02em; }}
  </style>
</head>
<body>
  <div class="box">
    <div class="logo">LONGOPASS</div>
    <h1>Sağlık Künyesi</h1>
    <p>Görüntülemek için erişim şifresini girin.</p>
    {err}
    <form method="post" action="/m/{html.escape(token)}/unlock" autocomplete="off">
      <label for="pin">Erişim şifresi</label>
      <input id="pin" name="pin" type="password" inputmode="numeric" maxlength="32" required placeholder="Şifre" />
      <button type="submit">Künyeyi Aç</button>
    </form>
  </div>
</body>
</html>
"""
