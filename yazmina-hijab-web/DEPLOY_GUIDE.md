# 🚀 Panduan Deploy Yazmina Hijab Web ke Rumahweb Unlimited Hosting

## ✅ Status: BISA Deploy!

Rumahweb Unlimited Hosting **mendukung Python & FastAPI** pada paket **GROW** dan **BLOOM**.

### Cek Paket Hosting Kamu

| Paket | Harga | Python | SSH | RAM | Status |
|---|---|---|---|---|---|
| **SEED** | Rp 17.900/bln | ❌ Tidak | ❌ Tidak | 512MB | ❌ Tidak cukup |
| **GROW** | Rp 29.900/bln | ✅ Ya | ✅ Ya | 1GB | ✅ Bisa (minimal) |
| **BLOOM** | Rp 49.900/bln | ✅ Ya | ✅ Ya | 2GB | ✅ Recommended |

> **Cara cek paket:** Login cPanel → lihat di bagian atas atau menu "Statistics"

---

## Persiapan Sebelum Deploy

### 1. Pastikan Paket Mendukung Python

Login cPanel → cari menu **"Setup Python App"** di bagian **Software**.

- ✅ **Ada menu "Setup Python App"** → Paket kamu mendukung Python
- ❌ **Tidak ada menu** → Paket kamu tidak mendukung (SEED), perlu upgrade

### 2. Build Frontend di Lokal

```bash
cd yazmina-hijab-web/frontend
npm install
npm run build
# Output: folder dist/ (berisi index.html, CSS, JS)
```

### 3. Siapkan File yang Perlu Diupload

```
yazmina-hijab-web/
├── backend/
│   ├── app/                    ← Upload semua
│   ├── requirements.txt        ← Upload
│   ├── setup_dev.py            ← Upload
│   └── .env                    ← Buat baru di server
├── frontend/
│   └── dist/                   ← Upload (hasil build)
└── .htaccess                   ← Buat baru di public_html
```

---

## Langkah Deploy (Step by Step)

### Step 1: Login cPanel

1. Buka `https://yourdomain.com:2083` atau `https://server.rumahweb.com:2083`
2. Masukkan username & password cPanel

### Step 2: Setup Python App

1. Cari menu **"Setup Python App"** di bagian **Software**
2. Klik **"Create Application"**
3. Isi konfigurasi:
   - **Python Version:** `3.11` atau `3.12` (pilih yang tersedia)
   - **Application Root:** `yazmina-hijab-web/backend`
   - **Application URL:** `(kosongkan untuk akses via domain utama)`
   - **Application Startup File:** `app/main.py`
4. Klik **"Create"**

### Step 3: Upload File Backend

**Via File Manager cPanel:**

1. Buka **File Manager**
2. Navigasi ke `/home/username/yazmina-hijab-web/`
3. Upload folder `backend/app/` dan `backend/requirements.txt` dan `backend/setup_dev.py`

**Via SSH (lebih cepat):**

```bash
# Dari komputer lokal
scp -r yazmina-hijab-web/backend/ username@server:/home/username/yazmina-hijab-web/backend/
```

### Step 4: Install Dependencies via Terminal

1. Buka **Terminal** di cPanel (atau SSH)
2. Jalankan perintah berikut:

```bash
# Aktifkan virtual environment
source /home/username/virtualenv/yazmina-hijab-web/3.11/bin/activate

# Install dependencies
cd /home/username/yazmina-hijab-web/backend
pip install -r requirements.txt

# Install gunicorn (untuk production)
pip install gunicorn
```

> **Catatan:** Path virtual environment mungkin berbeda. Lihat di menu Python App → ada info "source" command.

### Step 5: Buat File .env

```bash
cd /home/username/yazmina-hijab-web/backend

cat > .env << 'EOF'
DATABASE_URL=postgresql://neondb_owner:YOUR_PASSWORD@ep-YOUR-ENDPOINT.aws.neon.tech/neondb?sslmode=require
SECRET_KEY=ganti-dengan-random-string-yang-panjang
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_HOURS=12
APP_NAME=Yazmina Hijab
APP_VERSION=0.1.0
DEBUG=false
CORS_ORIGINS=https://yourdomain.com,http://yourdomain.com
EOF
```

**Ganti:**
- `YOUR_PASSWORD` → password Neon kamu
- `YOUR_ENDPOINT` → endpoint Neon kamu
- `yourdomain.com` → domain kamu
- `SECRET_KEY` → random string (bisa generate di https://randomkeygen.com)

### Step 6: Setup Admin User

```bash
cd /home/username/yazmina-hijab-web/backend
source /home/username/virtualenv/yazmina-hijab-web/3.11/bin/activate
python setup_dev.py --auto
```

### Step 7: Upload Frontend (Static Files)

1. Buka **File Manager** → navigasi ke `/home/username/public_html/`
2. Buat folder `app` → upload isi `frontend/dist/` ke dalamnya
3. Hasilnya:
   ```
   public_html/
   ├── app/
   │   ├── index.html
   │   └── assets/
   │       ├── index-xxx.js
   │       └── index-xxx.css
   └── .htaccess
   ```

### Step 8: Buat .htaccess

Buat file `.htaccess` di `/home/username/public_html/`:

```apache
RewriteEngine On

# Redirect API ke FastAPI backend (via Passenger)
RewriteCond %{REQUEST_URI} ^/api/
RewriteRule ^api/(.*)$ /app/main.py/$1 [L,QSA]

# Frontend: serve static files
RewriteCond %{REQUEST_FILENAME} !-f
RewriteCond %{REQUEST_FILENAME} !-d
RewriteRule ^(.*)$ /app/index.html [L]
```

**Atau cara yang lebih simpel (tanpa .htaccess复杂):**

Letakkan frontend di `public_html/` langsung:

```
public_html/
├── index.html          ← dari frontend/dist/
├── assets/             ← dari frontend/dist/assets/
├── api/                ← symlink ke backend (atau proxy)
└── .htaccess
```

### Step 9: Restart Python App

1. Kembali ke cPanel → **Setup Python App**
2. Klik **"Restart"** pada aplikasi yang sudah dibuat
3. Tunggu beberapa detik

### Step 10: Test

```bash
# Test backend
curl https://yourdomain.com/api/health

# Buka di browser
https://yourdomain.com
```

---

## Konfigurasi Alternative: Subdomain untuk API

Jika `.htaccess` rumit, gunakan subdomain terpisah:

### Backend (API)
```
api.yourdomain.com → FastAPI backend
```

**Setup di cPanel:**
1. **Subdomains** → buat `api` → document root: `/home/username/yazmina-hijab-web/backend`
2. **Setup Python App** → Application URL: `api.yourdomain.com`

### Frontend
```
yourdomain.com → React static files
```

**Setup di cPanel:**
1. Document root: `/home/username/public_html/`
2. Upload `frontend/dist/` ke sana

### Update CORS

```bash
# Di .env backend
CORS_ORIGINS=https://yourdomain.com,https://api.yourdomain.com
```

### Update Frontend API URL

```javascript
// Di frontend/src/api/client.js
const API_BASE = 'https://api.yourdomain.com/api';
```

---

## Troubleshooting

| Masalah | Solusi |
|---|---|
| **Menu "Setup Python App" tidak ada** | Paket hosting tidak mendukung Python. Upgrade ke GROW atau BLOOM |
| **502 Bad Gateway** | Cek Python App status → Restart |
| **ModuleNotFoundError** | Jalankan `pip install` lagi via Terminal |
| **Database connection error** | Cek file `.env`, pasti Neon URL benar |
| **CORS error** | Update `CORS_ORIGINS` di `.env` |
| **Static files 404** | Cek path upload di File Manager |
| **Python App tidak bisa start** | Cek error log: File Manager → `stderr.log` |

### Cek Error Log

```
File Manager → /home/username/yazmina-hijab-web/backend/stderr.log
```

---

## Tips Performa (Paket GROW 1GB RAM)

1. **Gunakan Gunicorn** (bukan uvicorn langsung):
   ```bash
   gunicorn app.main:app -w 2 -k uvicorn.workers.UvicornWorker -b 127.0.0.1:8765
   ```
   `-w 2` = 2 worker (hemat RAM)

2. **Nonaktifkan DEBUG:**
   ```
   DEBUG=false
   ```

3. **Cache static assets** via `.htaccess`:
   ```apache
   <IfModule mod_expires.c>
     ExpiresActive On
     ExpiresByType text/css "access plus 1 year"
     ExpiresByType application/javascript "access plus 1 year"
   </IfModule>
   ```

---

## Estimasi Biaya

| Item | Biaya |
|---|---|
| Hosting GROW (Rp 29.900/bulan) | Rp 29.900 |
| Domain .com (tahun pertama gratis di BLOOM) | Rp 0 - 150.000/tahun |
| Neon PostgreSQL (free tier) | Gratis |
| **Total** | **~Rp 30.000/bulan** |

---

## Ringkasan URL

| Service | URL |
|---|---|
| cPanel | `https://yourdomain.com:2083` |
| Frontend | `https://yourdomain.com` |
| Backend API | `https://yourdomain.com/api` |
| Neon Dashboard | `https://console.neon.tech` |

---

*Terakhir diperbarui: Agustus 2026*
