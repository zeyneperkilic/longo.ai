# Longopass Daily.co Video Call Widget

## Ne Yapar?

Widget sadece **"Görüşmeye Katıl" butonlarına davranış ekler**. Sayfa tasarımını yapmaz.

## 1. Ideasoft'a Ekle

```html
<!-- Sadece bu script'i ekle -->
<script src="https://longo-ai.onrender.com/widget/daily-embed.js"></script>
```

## 2. Butonları Hazırla

```html
<!-- Her randevu için bu butonu ekle -->
<button class="lp-join-call" data-meeting-id="12345">
    Görüşmeye Katıl
</button>
```

## 3. Konfigürasyon

```javascript
// Sayfa yüklendiğinde
window.LongopassDailyConfig = {
    joinEndpoint: '/ai/premium-plus/video-call/join',
    userId: 'user-123',
    userLevel: 3
};
```

## 4. Backend (Senin API'nde)

```python
@app.post("/ai/premium-plus/video-call/join")
async def join_video_call(payload: dict):
    meeting_id = payload.get("meeting_id")
    
    # Daily.co token oluştur
    token = create_daily_token(f"longopass-{meeting_id}")
    
    return {
        "success": True,
        "meetingUrl": f"https://longopass.daily.co/longopass-{meeting_id}",
        "token": token
    }
```

## 5. Özet

**Widget ne yapar:**
- Butonlara tıklanınca modal açar
- API'ye istek atar
- Daily.co video call başlatır

**Developer ne yapar:**
- Randevu sayfasını tasarlar
- Butonları yerleştirir
- API endpoint'ini oluşturur
