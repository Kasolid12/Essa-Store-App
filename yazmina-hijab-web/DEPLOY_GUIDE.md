# 🚀 Panduan Deploy Yazmina Hijab Web

## Ringkasan Opsi Deploy

| Opsi | Biaya | Kartu Kredit | Kesulitan | Status |
|---|---|---|---|---|
| **[Koyeb](#opsi-1-koyeb-gratis)** | Gratis | ❌ Tidak perlu | ⭐ Mudah | ✅ **Recommended** |
| [Render](#opsi-2-render-gratis) | Gratis | ⚠️ Kadang diminta | ⭐ Mudah | ✅ Alternatif |
| [Rumahweb](#opsi-3-rumahweb-hosting) | Rp 30rb/bln | ❌ Tidak perlu | ⭐⭐ Sedang | ✅ Kalau sudah punya hosting |

> **Rekomendasi:** Mulai dari **Koyeb** (gratis, tanpa kartu kredit, paling mudah).

---

## Opsi 1: Koyeb (GRATIS) ✅ Recommended

### Kenapa Koyeb?

- ✅ **Tidak butuh kartu kredit** — daftar langsung deploy
- ✅ **Full server** (bukan serverless) — FastAPI berjalan normal
- ✅ **Free forever** — bukan trial
- ✅ **Auto-deploy dari GitHub** — push = deploy
- ✅ **Docker support** — sudah ada Dockerfile

### Langkah 1: Siapkan GitHub

Pastikan kode sudah di-push ke GitHub:

```bash
cd "D:/Hasil Minggu Ini/Essa-Store-App"
git add .
git commit -m "Deploy to Koyeb"
git push origin main
```

### Langkah 2: Daftar Koyeb

1. Buka **https://app.koyeb.com**
2. Klik **Sign up** → pilih **Sign up with GitHub**
3. Authorize Koyeb untuk akses repo kamu
4. **Selesai!** Tidak diminta kartu kredit

### Langkah 3: Create Service

1. Klik **Create Service** → pilih **Git**
2. Pilih repo **Kasolid12/Essa-Store-App**
3. Isi config:

```
Name:           yazmina-hijab
Builder:        Dockerfile
Dockerfile Path: yazmina-hijab-web/Dockerfile
Port:           8000
```

4. Klik **Advanced** → tambah **Environment Variables**:

```
DATABASE_URL    = postgresql://neondb_owner:xxx@ep-xxx.ap-southeast-1.aws.neon.tech/neondb?sslmode=require
SECRET_KEY      = <buat random string panjang>
CORS_ORIGINS    = https://yazmina-hijab.koyeb.app
APP_NAME        = Yazmina Hijab Web
APP_VERSION     = 1.0.0
```

5. Klik **Deploy** → tunggu 3-5 menit

### Langkah 4: Aplikasi Live!

Setelah deploy selesai, Koyeb memberikan URL:

```
https://yazmina-hijab.koyeb.app
```

Buka di browser → Login dengan:
- **Username:** admin
- **Password:** admin123

### Arsitektur Deploy

```
Koyeb (Free)
├── Docker Container
│   ├── FastAPI Backend (uvicorn, port 8000)
│   │   ├── /api/* → API endpoints
│   │   ├── /assets/* → React static files
│   │   └── /* → React SPA (index.html)
│   └── Frontend (React built inside Docker)
└── Neon PostgreSQL (Cloud) ← sudah terkoneksi
```

### Update Deploy

Setiap kali ada perubahan kode:

```bash
git add .
git commit -m "Update fitur xyz"
git push origin main
# Koyeb otomatis rebuild & deploy (~3-5 menit)
```

### Limitasi Free Tier

- 1 service
- 512MB RAM
- 100 jam/bulan (auto-sleep saat idle, wake ~10-30 detik)
- Custom domain memerlukan upgrade

---

## Opsi 2: Render (GRATIS)

> **Catatan:** Render kadang meminta kartu kredit saat registrasi. Kalau kamu sudah berhasil registrasi tanpa kartu kredit, ini alternatif yang bagus.

### Langkah Deploy

1. Buka **https://render.com** → Daftar dengan GitHub
2. **New +** → **Web Service** → Connect repo **Kasolid12/Essa-Store-App**
3. Isi config:

```
Name:           yazmina-hijab
Runtime:        Docker
Dockerfile:     yazmina-hijab-web/Dockerfile
Port:           8000
```

4. Set **Environment Variables** (sama seperti Koyeb)
5. **Create Web Service** → Tunggu 5-10 menit

### Limitasi Free Tier

- 750 jam/bulan
- Auto-sleep setelah 15 menit idle
- Cold start 30-50 detik

---

## Opsi 3: Rumahweb Hosting

> **Catatan:** Paket SEED tidak support Python. Minimal paket **GROW** (Rp 29.900/bln) atau **BLOOM** (Rp 49.900/bln).

### Langkah Deploy

1. Login cPanel → **Setup Python App** → **Create Application**
2. Upload backend via File Manager atau SSH
3. Install dependencies via Terminal:

```bash
cd ~/yazmina-hijab-web/backend
pip install -r requirements.txt
```

4. Buat `.env` dengan Neon URL
5. Upload `frontend/dist/` ke folder yang benar
6. Restart Python App

> Panduan lengkap: lihat bagian [Deploy ke Rumahweb](#opsi-3-rumahweb-hosting) di bawah.

---

## Environment Variables

Berikut semua env vars yang dibutuhkan:

| Variable | Required | Contoh |
|---|---|---|
| `DATABASE_URL` | ✅ | `postgresql://user:pass@host/db?sslmode=require` |
| `SECRET_KEY` | ✅ | `my-super-secret-key-123456` |
| `CORS_ORIGINS` | ✅ | `https://your-app.koyeb.app` |
| `APP_NAME` | ⚙️ | `Yazmina Hijab Web` |
| `APP_VERSION` | ⚙️ | `1.0.0` |

### Generate SECRET_KEY

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### Buat Admin User

Setelah deploy pertama kali, jalankan sekali:

```bash
cd backend
python setup_dev.py --auto
```

Atau buat manual via API:

```bash
curl -X POST https://your-app.koyeb.app/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'
```

---

## Troubleshooting

### App tidak bisa diakses
- Cek logs di dashboard Koyeb/Render
- Pastikan `DATABASE_URL` benar dan bisa diakses dari internet
- Pastikan Neon database tidak sleeping (free tier punya limit)

### Cold start lambat
- Koyeb: ~10-30 detik wake dari sleep
- Render: ~30-50 detik cold start
- Ini normal untuk free tier

### Error "could not translate host name"
- Cek `DATABASE_URL` di env vars
- Pastikan Neon database masih active (buka Neon dashboard)

### Admin user hilang
- Jalankan `python setup_dev.py --auto` atau buat ulang via API
- Data di Neon persist, tidak hilang saat deploy baru

---

## Arsitektur Final

```
┌─────────────────────────────────────────────────┐
│                  USER (Browser)                  │
│              https://your-app.koyeb.app          │
└──────────────────────┬──────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────┐
│              Koyeb / Render (Free)              │
│  ┌───────────────────────────────────────────┐  │
│  │  FastAPI Backend (uvicorn, port 8000)     │  │
│  │                                           │  │
│  │  /api/*  → API endpoints (JSON)           │  │
│  │  /assets → React static files             │  │
│  │  /*      → React SPA (index.html)         │  │
│  └───────────────────────────────────────────┘  │
└──────────────────────┬──────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────┐
│            Neon PostgreSQL (Cloud)              │
│         Shared dengan Desktop App               │
│                                                 │
│  1,022 SKUs · 316 Hutang · 182 Gaji · ...     │
└─────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────┐
│            Desktop App (PySide6)                │
│         Jalan di komputer lokal                 │
│         Koneksi ke Neon yang sama               │
└─────────────────────────────────────────────────┘
```

### Sinkronisasi Data

```
Desktop App ←→ Neon PostgreSQL ←→ Web App
```

Kedua aplikasi share data yang sama di cloud. Perubahan di desktop langsung terlihat di web, dan sebaliknya.

---

## Estimasi Biaya

```
Koyeb (Free):    Rp 0/bulan
Neon DB (Free):  Rp 0/bulan
Domain (.com):   Rp 0 (optional, bisa pakai .koyeb.app gratis)
─────────────────────────────────
Total:           Rp 0/bulan (GRATIS!)
```

Kalau butuh custom domain + always-on:
```
Koyeb Pro:       ~$5/bulan (~Rp 80.000)
Domain .com:     ~Rp 150.000/tahun (~Rp 12.500/bulan)
─────────────────────────────────
Total:           ~Rp 92.500/bulan
```
