# 🚀 Render Deployment Guide

## 📋 Ön Gereksinimler

1. **Render hesabı** (ücretsiz)
2. **OpenRouter API key** (https://openrouter.ai/)
3. **Git repository** (GitHub, GitLab, etc.)

## 🔧 Şimdilik SQLite ile Deploy (Database bilgileri yok)

### 1. Repository'yi Render'a Bağla

1. Render Dashboard'a git
2. "New +" → "Web Service"
3. GitHub repository'yi seç
4. Branch: `main` (veya `master`)

### 2. Build Settings

- **Name**: `longopass-ai`
- **Environment**: `Python 3`
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`

### 3. Environment Variables

```bash
# Zorunlu
OPENROUTER_API_KEY=your_openrouter_api_key_here
AUTH_PASSWORD=your_secure_password_here

# Opsiyonel (varsayılan değerler kullanılacak)
ENVIRONMENT=production
DB_TYPE=sqlite
DB_PATH=/opt/render/project/src/app.db
ALLOWED_ORIGINS=*
HEALTH_MODE=topic
PRESCRIPTION_BLOCK=true
CHAT_HISTORY_MAX=20
FREE_ANALYZE_LIMIT=1
```

### 4. Deploy Et

- "Create Web Service" butonuna tıkla
- Build tamamlanana kadar bekle (5-10 dakika)
- URL'yi not al (örn: `https://longopass-ai.onrender.com`)

## 🔄 PostgreSQL'e Geçiş (Database bilgileri geldiğinde)

### 1. Environment Variables Güncelle

```bash
# Database bilgileri
DB_TYPE=postgresql
DB_HOST=your_database_host
DB_PORT=5432
DB_NAME=your_database_name
DB_USER=your_database_user
DB_PASSWORD=your_database_password

# CORS origins (güvenlik için)
ALLOWED_ORIGINS=https://yoursite.com,https://www.yoursite.com
```

### 2. Migration Script'i Çalıştır

```bash
# Render'da terminal aç
cd /opt/render/project/src
python backend/db_migration.py

# Seçenek 1: Veri taşı
# Seçenek 2: Database tipini değiştir
```

### 3. Render.yaml Güncelle

```yaml
# Database bilgileri geldiğinde bu kısmı aktif et:
- key: DB_TYPE
  value: postgresql
- key: DB_HOST
  fromDatabase:
    name: longopass-db
    property: host
- key: DB_PORT
  fromDatabase:
    name: longopass-db
    property: port
- key: DB_NAME
  fromDatabase:
    name: longopass-db
    property: database
- key: DB_USER
  fromDatabase:
    name: longopass-db
    property: user
- key: DB_PASSWORD
  fromDatabase:
    name: longopass-db
    property: password

# Ve databases kısmını ekle:
databases:
  - name: longopass-db
    databaseName: longopass
    user: longopass_user
```

## 🧪 Test Et

### 1. Health Check

```bash
curl https://your-app.onrender.com/health
# Beklenen: {"status": "ok", "service": "longopass-ai"}
```

### 2. Authentication Test

```bash
curl -H "username: longopass" \
     -H "password: your_password" \
     https://your-app.onrender.com/ai/chat/start
```

### 3. API Test

```bash
# Quiz endpoint
curl -X POST https://your-app.onrender.com/ai/quiz \
  -H "username: longopass" \
  -H "password: your_password" \
  -H "Content-Type: application/json" \
  -d '{"quiz_answers": {"age": "25", "gender": "male"}}'
```

## 🔒 Güvenlik Kontrolleri

- [ ] AUTH_PASSWORD güçlü mü?
- [ ] ALLOWED_ORIGINS kısıtlandı mı?
- [ ] Rate limiting çalışıyor mu?
- [ ] Database credentials güvenli mi?

## 🚨 Sorun Giderme

### Build Hatası
```bash
# Requirements.txt'de psycopg2-binary var mı?
# Python version 3.11+ mi?
```

### Database Hatası
```bash
# DB_TYPE=sqlite olarak ayarlandı mı?
# DB_PATH doğru mu?
```

### API Hatası
```bash
# OPENROUTER_API_KEY doğru mu?
# Authentication headers var mı?
```

## 📞 Destek

- **Render Docs**: https://render.com/docs
- **FastAPI Docs**: https://fastapi.tiangolo.com/
- **SQLAlchemy Docs**: https://docs.sqlalchemy.org/

## 🎯 Sonraki Adımlar

1. ✅ SQLite ile deploy et
2. ⏳ Database bilgilerini bekle
3. 🔄 PostgreSQL'e geç
4. 🧪 Test et
5. 🚀 Production'a al
