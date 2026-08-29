# 🚀 Deploy Gratis ke Render.com

## Kenapa Render.com?

- ✅ **Gratis** (free tier: 750 jam/bulan)
- ✅ **SSL gratis** (HTTPS otomatis)
- ✅ **Auto deploy** dari GitHub
- ✅ **Support Python & Node.js**
- ⚠️ **Limitation:** App sleep setelah 15 menit idle (bangun otomatis saat diakses)

---

## Langkah Deploy (Step by Step)

### Step 1: Push ke GitHub

Pastikan kode sudah di-push ke GitHub:

```bash
cd "D:/Hasil Minggu Ini/Essa-Store-App"
git push origin main
```

### Step 2: Buat Akun Render

1. Buka https://render.com
2. Klik **"Get Started for Free"**
3. Daftar dengan **GitHub account** (paling mudah)

### Step 3: Create Web Service

1. Login ke Render Dashboard
2. Klik **"New +"** → **"Web Service"**
3. Klik **"Build and deploy from a Git repo"** → **"Next"**
4. Connect GitHub repository: **Kasolid12/Essa-Store-App**
5. Klik **"Connect"**

### Step 4: Configure Service

Isi konfigurasi berikut:

| Field | Value |
|---|---|
| **Name** | `yazmina-hijab-web` |
| **Region** | `Singapore` (paling dekat) |
| **Branch** | `main` |
| **Runtime** | `Python 3` |
| **Build Command** | `cd frontend && npm install && npm run build && cd ../backend && pip install -r requirements.txt` |
| **Start Command** | `cd backend && gunicorn app.main:app -w 2 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:$PORT` |
| **Plan** | `Free` |

### Step 5: Set Environment Variables

Klik tab **"Environment"** → tambahkan:

| Key | Value |
|---|---|
| `DATABASE_URL` | `postgresql://neondb_owner:YOUR_PASSWORD@ep-YOUR-ENDPOINT.aws.neon.tech/neondb?sslmode=require` |
| `SECRET_KEY` | (klik "Generate" untuk random string) |
| `JWT_ALGORITHM` | `HS256` |
| `ACCESS_TOKEN_EXPIRE_HOURS` | `12` |
| `APP_NAME` | `Yazmina Hijab` |
| `APP_VERSION` | `1.0.0` |
| `DEBUG` | `false` |
| `CORS_ORIGINS` | `https://yazmina-hijab.onrender.com` |
| `PYTHON_VERSION` | `3.11.0` |

> **Ganti** `YOUR_PASSWORD` dan `YOUR_ENDPOINT` dengan Neon credentials kamu.

### Step 6: Deploy

1. Klik **"Create Web Service"**
2. Tunggu proses build (~3-5 menit)
3. Setelah selesai, klik URL yang muncul (contoh: `https://yazmina-hijab.onrender.com`)

### Step 7: Setup Admin User

Setelah deploy selesai, buka terminal di Render:

1. Buka Web Service → **"Shell"** tab
2. Jalankan:

```bash
cd backend
python setup_dev.py --auto
```

### Step 8: Test

Buka browser → `https://yazmina-hijab.onrender.com`

Login: `admin` / `admin123`

---

## Update CORS Setelah Deploy

Setelah tahu URL production, update `CORS_ORIGINS` di Render:

1. Render Dashboard → Web Service → **"Environment"**
2. Update `CORS_ORIGINS` → `https://yazmina-hijab.onrender.com`
3. Save → auto redeploy

---

## Troubleshooting

| Masalah | Solusi |
|---|---|
| **Build gagal** | Cek log di Render → "Events" tab |
| **App sleep** | Normal di free tier. Akses URL → bangun otomatis (~30 detik) |
| **Database error** | Cek `DATABASE_URL` di Environment Variables |
| **CORS error** | Update `CORS_ORIGINS` |
| **502 error** | Cek logs → biasanya dependency belum terinstall |

### Cek Logs

Render Dashboard → Web Service → **"Logs"** tab

---

## Biaya

| Item | Biaya |
|---|---|
| Render Free Tier | Gratis (750 jam/bulan) |
| Neon PostgreSQL | Gratis (free tier) |
| Domain | Gratis (bawaan `.onrender.com`) |
| **Total** | **Gratis!** |

---

## Upgrade Nanti

Jika app sudah stabil dan butuh performa lebih:

| Plan | Harga | Fitur |
|---|---|---|
| Free | $0 | 750 jam/bulan, sleep 15 menit |
| Starter | $7/bulan | No sleep, 512MB RAM |
| Standard | $25/bulan | 2GB RAM, auto-scale |

---

*Terakhir diperbarui: Agustus 2026*
