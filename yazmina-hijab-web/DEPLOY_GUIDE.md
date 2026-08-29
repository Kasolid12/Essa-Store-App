# 🚀 Panduan Deploy Yazmina Hijab Web ke Rumahweb

## Overview

Yazmina Hijab Web terdiri dari 2 bagian:
1. **Backend** — FastAPI (Python) berjalan di port 8765
2. **Frontend** — React (Vite) yang di-build jadi static files

**Target:** Deploy ke Rumahweb Cloud Hosting atau VPS.

---

## Opsi 1: Cloud Hosting (cPanel) — RECOMMENDED

**Paket minimal:** Cloud Space 10 GB (Rp 120.000/bulan)

### Fitur yang Didukung
- ✅ Python & Node.JS
- ✅ SSH Access
- ✅ SSL Gratis (Let's Encrypt)
- ✅ Unlimited MariaDB (tapi kita pakai Neon PostgreSQL)
- ✅ Akses ke File Manager & Terminal

### Langkah Deploy

#### 1. Persiapan di Lokal

```bash
# Build frontend jadi static files
cd yazmina-hijab-web/frontend
npm run build
# Output: frontend/dist/ (file HTML, CSS, JS)
```

#### 2. Upload ke Hosting

**Via File Manager cPanel:**
1. Login cPanel → File Manager
2. Navigasi ke `/home/username/`
3. Buat folder `yazmina-hijab-web`
4. Upload seluruh folder `backend/` dan `frontend/dist/`

**Via SSH (lebih cepat):**
```bash
# Dari komputer lokal
scp -r yazmina-hijab-web/ username@server.rumahweb.com:/home/username/
```

#### 3. Setup Python App di cPanel

1. Login cPanel → **Software** → **Setup Python App**
2. Klik **Create Application**
3. Pilih Python version: **3.11** atau **3.12**
4. Application root: `/home/username/yazmina-hijab-web/backend`
5. Application startup file: `app/main.py`
6. Application URL: `/api` (atau subdomain)
7. Klik **Create**

#### 4. Install Dependencies

```bash
# Via SSH
cd /home/username/yazmina-hijab-web/backend
source venv/bin/activate
pip install -r requirements.txt
```

#### 5. Setup Environment

```bash
# Buat file .env
cat > .env << 'EOF'
DATABASE_URL=postgresql://neondb_owner:YOUR_PASSWORD@ep-YOUR-ENDPOINT.aws.neon.tech/neondb?sslmode=require
SECRET_KEY=your-random-secret-key-here
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_HOURS=12
APP_NAME=Yazmina Hijab
APP_VERSION=0.1.0
DEBUG=false
CORS_ORIGINS=https://yourdomain.com,http://yourdomain.com
EOF
```

#### 6. Setup Static Files (Frontend)

**Via .htaccess di public_html:**

```apache
# /home/username/public_html/.htaccess
RewriteEngine On

# API routes → FastAPI backend
RewriteRule ^api/(.*)$ /api/$1 [L]

# Everything else → React static files
RewriteCond %{REQUEST_FILENAME} !-f
RewriteCond %{REQUEST_FILENAME} !-d
RewriteRule ^(.*)$ /yazmina-hijab-web/frontend/dist/index.html [L]
```

**Atau gunakan subdomain:**
- `app.yourdomain.com` → FastAPI backend
- `yourdomain.com` → React frontend (static)

#### 7. Setup SSL

1. cPanel → **Security** → **SSL/TLS**
2. Atau **Let's Encrypt** → Issue SSL untuk domain

#### 8. Test

```bash
# Test backend
curl https://yourdomain.com/api/health

# Buka di browser
https://yourdomain.com
```

---

## Opsi 2: VPS Ubuntu — FULL CONTROL

**Paket minimal:** VPS 1 vCPU, 2 GB RAM (Rp 150.000/bulan)

### Kelebihan
- ✅ Full root access
- ✅ Bisa install apa saja
- ✅ Nginx + Gunicorn (performa lebih baik)
- ✅ Domain + SSL gratis

### Langkah Deploy

#### 1. Setup VPS

```bash
# SSH ke VPS
ssh root@YOUR_VPS_IP

# Update system
apt update && apt upgrade -y

# Install Python 3.11+
apt install python3.11 python3.11-venv python3-pip -y

# Install Nginx
apt install nginx -y

# Install supervisor (auto-restart)
apt install supervisor -y
```

#### 2. Upload Project

```bash
# Dari komputer lokal
scp -r yazmina-hijab-web/ root@YOUR_VPS_IP:/opt/

# Atau clone dari GitHub
cd /opt
git clone https://github.com/Kasolid12/Essa-Store-App.git
cd Essa-Store-App/yazmina-hijab-web
```

#### 3. Setup Backend

```bash
cd /opt/yazmina-hijab-web/backend

# Buat virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Buat .env
cat > .env << 'EOF'
DATABASE_URL=postgresql://neondb_owner:YOUR_PASSWORD@ep-YOUR-ENDPOINT.aws.neon.tech/neondb?sslmode=require
SECRET_KEY=your-random-secret-key-here
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_HOURS=12
APP_NAME=Yazmina Hijab
APP_VERSION=0.1.0
DEBUG=false
CORS_ORIGINS=https://yourdomain.com
EOF

# Setup admin
python setup_dev.py --auto
```

#### 4. Build Frontend

```bash
cd /opt/yazmina-hijab-web/frontend
npm install
npm run build
# Output: dist/
```

#### 5. Setup Gunicorn

```bash
# Install gunicorn
pip install gunicorn

# Test run
cd /opt/yazmina-hijab-web/backend
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker -b 127.0.0.1:8765
```

#### 6. Setup Supervisor (Auto-restart)

```bash
cat > /etc/supervisor/conf.d/yazmina-web.conf << 'EOF'
[program:yazmina-web]
command=/opt/yazmina-hijab-web/backend/venv/bin/gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker -b 127.0.0.1:8765
directory=/opt/yazmina-hijab-web/backend
user=www-data
autostart=true
autorestart=true
stderr_logfile=/var/log/yazmina-web/stderr.log
stdout_logfile=/var/log/yazmina-web/stdout.log
environment=
    PYTHONUNBUFFERED=1,
    DATABASE_URL="postgresql://neondb_owner:YOUR_PASSWORD@ep-YOUR-ENDPOINT.aws.neon.tech/neondb?sslmode=require",
    SECRET_KEY="your-random-secret-key"
EOF

# Buat folder log
mkdir -p /var/log/yazmina-web

# Reload supervisor
supervisorctl reread
supervisorctl update
supervisorctl start yazmina-web
```

#### 7. Setup Nginx

```bash
cat > /etc/nginx/sites-available/yazmina << 'EOF'
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;

    # Redirect to HTTPS
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com www.yourdomain.com;

    # SSL (Let's Encrypt)
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

    # Frontend (React static files)
    root /opt/yazmina-hijab-web/frontend/dist;
    index index.html;

    # API → Backend
    location /api/ {
        proxy_pass http://127.0.0.1:8765;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # React Router (SPA)
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Cache static assets
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
EOF

# Aktifkan site
ln -s /etc/nginx/sites-available/yazmina /etc/nginx/sites-enabled/
rm /etc/nginx/sites-enabled/default

# Test config
nginx -t

# Reload nginx
systemctl reload nginx
```

#### 8. Setup SSL (Let's Encrypt)

```bash
# Install certbot
apt install certbot python3-certbot-nginx -y

# Issue SSL certificate
certbot --nginx -d yourdomain.com -d www.yourdomain.com

# Auto-renew
certbot renew --dry-run
```

#### 9. Setup Firewall

```bash
# Allow HTTP/HTTPS
ufw allow 'Nginx Full'
ufw allow ssh
ufw enable
```

#### 10. Test

```bash
# Test backend
curl http://localhost:8765/api/health

# Test nginx
curl https://yourdomain.com/api/health

# Buka di browser
https://yourdomain.com
```

---

## Opsi 3: Deploy ke Cloud Gratis (Alternatif)

Jika ingin coba dulu sebelum bayar hosting:

### Railway.app (Recommended)
```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Init project
cd yazmina-hijab-web/backend
railway init

# Set env vars
railway variables set DATABASE_URL="postgresql://..."
railway variables set SECRET_KEY="..."

# Deploy
railway up
```

### Render.com
1. Push ke GitHub
2. Login render.com → New → Web Service
3. Connect GitHub repo
4. Build command: `cd backend && pip install -r requirements.txt`
5. Start command: `cd backend && gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker`
6. Set env vars

### Fly.io
```bash
curl -L https://fly.io/install.sh | sh
fly auth signup
fly launch
fly deploy
```

---

## Checklist Deploy

- [ ] Backend compile OK (`python -m py_compile app/main.py`)
- [ ] Frontend build OK (`npm run build`)
- [ ] `.env` sudah diisi dengan Neon URL + SECRET_KEY
- [ ] `CORS_ORIGINS` sudah diupdate ke domain production
- [ ] SSL sudah aktif
- [ ] `setup_dev.py --auto` sudah dijalankan (buat admin)
- [ ] Test login: `https://yourdomain.com` → admin/admin123
- [ ] Test API: `curl https://yourdomain.com/api/health`

---

## Troubleshooting

| Masalah | Solusi |
|---|---|
| 502 Bad Gateway | Cek apakah Gunicorn berjalan: `supervisorctl status` |
| CORS error | Update `CORS_ORIGINS` di `.env` |
| Static files 404 | Cek path `root` di Nginx config |
| Database connection | Test: `python -c "from app.database import engine; print(engine.url)"` |
| SSL error | Re-issue: `certbot --nginx -d yourdomain.com` |

---

## Biaya Estimasi

| Opsi | Biaya/bulan | Cocok Untuk |
|---|---|---|
| Cloud Hosting 10GB | Rp 120.000 | Uji coba, 1-5 user |
| Cloud Hosting 30GB | Rp 360.000 | Produksi, 5-20 user |
| VPS 1 vCPU 2GB | Rp 150.000 | Produksi, full control |
| Railway (free tier) | Gratis | Uji coba, 500 jam/bulan |
| Render (free tier) | Gratis | Uji coba, sleep 15 menit |

---

*Terakhir diperbarui: Agustus 2026*
