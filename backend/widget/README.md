# 🏥 Longo Health Widget

Bu widget, herhangi bir web sitesine entegre edilebilen Longo Sağlık Asistanı chat widget'ıdır.

## 📁 Dosya Yapısı

- `longo-health-widget.js` - Ana widget JavaScript kodu
- `longo-health-widget.css` - Widget stilleri
- `test-widget.html` - Test sayfası
- `README.md` - Bu dosya

## 🚀 Nasıl Test Edilir

### 1. Basit Test (Önerilen)

1. **Test sayfasını açın:**
   ```bash
   cd backend/widget
   open test-widget.html
   ```
   veya tarayıcıda `test-widget.html` dosyasını açın.

2. **Widget otomatik yüklenecektir** - sağ alt köşede görünür.

3. **Test kontrollerini kullanın:**
   - Plan seçici ile farklı kullanıcı planlarını test edin
   - Test butonları ile widget fonksiyonlarını kontrol edin
   - Manuel olarak widget'ı kullanın

### 2. Manuel Test

1. **Widget butonuna tıklayın** - chat penceresi açılır
2. **Farklı planları test edin:**
   - **Free**: Premium overlay görünür
   - **Premium**: Temel chat özellikleri
   - **Premium Plus**: Quick Actions + gelişmiş özellikler

### 3. API Test

Widget'ın API bağlantısını test etmek için:

1. **Console'u açın** (F12)
2. **Network sekmesini kontrol edin**
3. **Mesaj gönderin** ve API çağrılarını izleyin

## 🔧 Entegrasyon

### Basit Entegrasyon

```html
<!-- CSS dosyasını ekleyin -->
<link rel="stylesheet" href="path/to/longo-health-widget.css">

<!-- JavaScript dosyasını ekleyin -->
<script src="path/to/longo-health-widget.js"></script>

<!-- Kullanıcı bilgilerini ayarlayın -->
<script>
window.longoCurrentUserId = 'user_123';
window.longoCurrentUserPlan = 'premium'; // 'free', 'premium', 'premium_plus'
</script>
```

### Gelişmiş Entegrasyon

```html
<script>
// Widget yüklendikten sonra
window.addEventListener('load', function() {
    // Kullanıcı bilgilerini ayarlayın
    window.longoCurrentUserId = 'user_123';
    window.longoCurrentUserPlan = 'premium_plus';
    
    // Upgrade URL'lerini ayarlayın
    window.longoUpgradeToPremiumUrl = 'https://yoursite.com/upgrade-premium';
    window.longoUpgradeToPremiumPlusUrl = 'https://yoursite.com/upgrade-premium-plus';
});
</script>
```

## 🧪 Test Senaryoları

### ✅ Test Edilmesi Gerekenler

1. **Widget Yükleme**
   - Widget sayfa yüklendiğinde görünür mü?
   - CSS stilleri doğru uygulanıyor mu?

2. **Plan Kontrolü**
   - Free kullanıcılar premium overlay görüyor mu?
   - Premium kullanıcılar chat açabiliyor mu?
   - Premium Plus özellikleri görünüyor mu?

3. **Chat Fonksiyonları**
   - Chat penceresi açılıp kapanıyor mu?
   - Mesaj gönderimi çalışıyor mu?
   - Loading animasyonları görünüyor mu?

4. **Premium Özellikler**
   - Quick Actions butonları çalışıyor mu?
   - Plan badge'leri doğru görünüyor mu?

### 🐛 Bilinen Sorunlar

- **API bağlantısı**: Backend URL'ini kontrol edin
- **CSS yüklenmeme**: CSS dosya yolunu kontrol edin
- **Plan güncellememe**: Sayfa yeniden yüklenmeli

## 🔍 Debug

### Console Hataları

```javascript
// Widget durumunu kontrol edin
console.log('Widget:', document.getElementById('longo-health-widget'));
console.log('User Plan:', window.longoCurrentUserPlan);
console.log('User ID:', window.longoCurrentUserId);
```

### Network Hataları

1. **CORS hatası**: Backend CORS ayarlarını kontrol edin
2. **404 hatası**: API endpoint'lerini kontrol edin
3. **Auth hatası**: Username/password'ü kontrol edin

## 📱 Responsive Test

- **Desktop**: 1920x1080 ve üzeri
- **Tablet**: 768x1024
- **Mobile**: 375x667

## 🎯 Sonraki Adımlar

1. **Backend API'yi test edin**
2. **Farklı tarayıcılarda test edin**
3. **Performance testleri yapın**
4. **A/B testleri planlayın**

## 📞 Destek

Widget ile ilgili sorunlar için:
- Console hatalarını kontrol edin
- Network sekmesini inceleyin
- Test sayfasını kullanın
- Backend loglarını kontrol edin
