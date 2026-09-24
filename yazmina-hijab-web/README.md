# 🌐 Yazmina Hijab — Web Version

> **Platform:** FastAPI (Python) + React (Vite) + PostgreSQL (Neon)  
> **Status:** Production-ready · **Theme:** Cyberpunk Industrial

Aplikasi operasional bisnis **Yazmina Hijab** versi web — akses dari browser, login admin, database terpusat di cloud.

## ✨ Fitur

| Fitur | Deskripsi |
|---|---|
| 🔐 **Login Admin** | JWT auth + httpOnly cookie |
| 📦 **SKU Management** | CRUD + search + filter |
| 👥 **Data Master** | Person (Karyawan, Klient, Supplier) CRUD |
| 📝 **Catatan Harian** | 4 tab: Cutting, Distribusi, Offline, Operasional |
| 💳 **Hutang & Pelunasan** | Batch payment, FIFO tracking |
| 💰 **Payroll & Bon** | Legacy + simulation mode, Excel import |
| 🧾 **Invoice & Piutang** | Client + FIFO tracking + deposit |
| 📈 **Profit Simulation** | Batch analyzer, tarif, history |
| 📦 **Stock Manager** | BigSeller Excel export |
| 📊 **Dashboard** | KPI + charts + profit analysis |

## 🚀 Quick Start

### 1. Clone & Install Dependencies

```bash
# Backend
cd backend
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate    # Linux/Mac
pip install -r requirements.txt

# Frontend
cd frontend
npm install
```

### 2. Konfigurasi

```bash
cd backend
cp .env.example .env
# Edit .env — isi DATABASE_URL (Neon PostgreSQL) dan SECRET_KEY
```

### 3. Buat Admin User

```bash
cd backend
python setup_dev.py --auto
```

### 4. Jalankan

```bash
# Backend (terminal 1)
cd backend
uvicorn app.main:app --reload  # → http://localhost:8000

# Frontend (terminal 2)
cd frontend
npm run dev                     # → http://localhost:5173
```

### 5. Login

Buka `http://localhost:5173` → Login:

- **Username:** admin
- **Password:** admin123

---

## 🏗️ Struktur Folder

```
yazmina-hijab-web/
├── backend/                     # FastAPI (Python)
│   ├── app/
│   │   ├── main.py             # Entry point + route registration
│   │   ├── config.py           # Settings (DATABASE_URL, SECRET_KEY, dll)
│   │   ├── database.py         # SQLAlchemy engine + sessionmaker
│   │   ├── auth.py             # JWT utils, login/logout/register
│   │   ├── models/             # SQLAlchemy ORM models
│   │   │   ├── __init__.py     # Model registry
│   │   │   ├── sku.py          # SKU master model
│   │   │   ├── person.py       # Person (Karyawan/Klient/Supplier)
│   │   │   ├── admin_user.py   # Admin auth model
│   │   │   ├── debt.py         # Hutang + pembayaran
│   │   │   ├── payroll.py      # Gaji + kenaikan gaji
│   │   │   ├── bon.py          # Kasbon bongko
│   │   │   ├── daily_notes.py  # Catatan harian (4 tab)
│   │   │   ├── client.py       # Client (piutang)
│   │   │   ├── invoice.py      # Piutang receivable/payment
│   │   │   ├── profit.py       # Profit history + tarif
│   │   │   └── modal_operasional.py
│   │   ├── schemas/            # Pydantic request/response schemas
│   │   ├── routers/            # API route modules
│   │   │   ├── auth.py
│   │   │   ├── sku.py
│   │   │   ├── person.py
│   │   │   ├── dashboard.py
│   │   │   ├── modal_operasional.py
│   │   │   ├── pengeluaran_offline.py
│   │   │   ├── hasil_cutting.py
│   │   │   ├── distribusi_cutting.py
│   │   │   ├── hutang.py
│   │   │   ├── gaji.py
│   │   │   ├── bon.py
│   │   │   ├── client.py
│   │   │   ├── invoice.py
│   │   │   ├── profit.py
│   │   │   └── stock.py
│   │   └── services/           # Business logic (optional)
│   ├── alembic/                # Database migrations
│   ├── create_admin.py         # Script create admin user
│   ├── setup_dev.py            # Idempotent dev setup
│   ├── requirements.txt        # Python dependencies
│   ├── Procfile               # Render/Koyeb start command
│   └── .env.example            # Config template
├── frontend/                    # React + Vite
│   ├── src/
│   │   ├── theme.css           # Cyberpunk industrial CSS tokens
│   │   ├── api/client.js       # API fetch wrapper (TanStack Query)
│   │   ├── App.jsx             # Router + auth provider
│   │   ├── main.jsx            # Entry point
│   │   ├── components/
│   │   │   ├── Sidebar.jsx     # Navigation sidebar (responsive)
│   │   │   ├── DataTable.jsx   # Reusable data table
│   │   │   └── Modal.jsx       # Reusable modal
│   │   └── pages/
│   │       ├── Login.jsx       # Login page
│   │       ├── Dashboard.jsx   # Dashboard analytics
│   │       ├── SkuPage.jsx     # SKU management
│   │       ├── PersonPage.jsx  # Person data master
│   │       ├── CatatanHarian.jsx
│   │       ├── HutangPelunasan.jsx
│   │       ├── PayrollBon.jsx
│   │       ├── Invoice.jsx
│   │       ├── ProfitSimulation.jsx
│   │       └── StockManager.jsx
│   ├── public/                 # Static assets (favicon, dll)
│   ├── package.json
│   ├── package-lock.json
│   └── vite.config.js          # Dev server + proxy config
├── Dockerfile                  # Multi-stage: Node build + Python runtime
├── .dockerignore               # Files excluded from Docker build
├── .gitignore                  # Files excluded from Git
├── render.yaml                 # Render.com deployment config
├── DEPLOY_GUIDE.md             # Full deployment guide
├── DEPLOY_RENDER.md            # Render-specific instructions
└── README.md                   # This file
```

---

## 📱 Responsif & Multi-Device

Aplikasi ini **responsif** — tampilan menyesuaikan untuk:

| Perangkat | Breakpoint | Perilaku |
|---|---|---|
| **Desktop** | > 1024px | Sidebar width 260px, KPI grid 4 kolom |
| **Tablet** | 768px–1024px | Sidebar 220px, padding lebih kecil, form grid 1 kolom |
| **Mobile** | < 768px | Sidebar off-canvas + hamburger, KPI 1 kolom, tabs scroll |
| **Small mobile** | < 480px | Extra compact, font lebih kecil |

### Klik ☰ di pojok kiri (mobile)

Tombol hamburger muncul di layar ≤ 1024px. Sidebar akan slide dari kiri.

---

## 🔗 Web ↔ Desktop Integration

Arsitektur aplikasi:

```
┌──────────────────────────────────────────┐
│     Browser (React SPA)                  │
│     https://your-app.koyeb.app           │
└──────────────┬───────────────────────────┘
               │ HTTPS / JSON
               ▼
┌──────────────────────────────────────────┐
│           FastAPI (Python)               │
│           uvicorn, port 8000             │
│                                           │
│   /api/*     → API endpoints (JSON)      │
│   /assets/*  → React static files        │
│   /*         → React SPA (index.html)    │
└──────────────┬───────────────────────────┘
               │ PostgreSQL protocol
               ▼
┌──────────────────────────────────────────┐
│        Neon PostgreSQL (Cloud)           │
│        Shared dengan Desktop App          │
└──────────────────────────────────────────┘

┌──────────────────────────────────────────┐
│        Desktop App (PySide6)             │
│        Jalan di komputer lokal           │
│        Koneksi ke Neon (sama)            │
└──────────────────────────────────────────┘
```

**Sinkronisasi:** Kedua aplikasi share data yang sama di cloud. Perubahan di desktop langsung terlihat di web, dan sebaliknya.

---

## 🛠 Tech Stack

| Layer | Technology | Versi |
|-------|-----------|-------|
| Backend | FastAPI | ≥ 0.115 |
| Backend | uvicorn (ASGI) | ≥ 0.34 |
| Backend | SQLAlchemy | ≥ 2.0.25 |
| Backend | psycopg2-binary | ≥ 2.9.9 |
| Backend | Pydantic | ≥ 2.0 |
| Backend | JWT (python-jose) | ≥ 3.3 |
| Backend | bcrypt | ≥ 4.0 |
| Frontend | React | 19.x |
| Frontend | Vite | latest |
| Frontend | TanStack Query | latest |
| Frontend | React Router | latest |
| Database | PostgreSQL | 18.x (Neon) |
| Auth | JWT + httpOnly cookie | — |

---

## 🌍 Deploy

### Opsi 1: Koyeb (GRATIS, Tanpa Kartu Kredit)

```bash
# Build & push ke GitHub
cd yazmina-hijab-web
git add .
git commit -m "Deploy to Koyeb"
git push origin main
```

1. Buka **https://app.koyeb.com** → Sign up with GitHub
2. Create Service → Git → Pilih repo `yazmina-hijab-web`
3. Config:
   - Builder: **Dockerfile**
   - Dockerfile: **yazmina-hijab-web/Dockerfile**
   - Port: **8000**
4. Environment Variables:
   - `DATABASE_URL` = `postgresql://user:pass@host/db?sslmode=require`
   - `SECRET_KEY` = random string (32 char)
   - `CORS_ORIGINS` = `https://your-app.koyeb.app`
5. Deploy → Tunggu 3-5 menit → Selesai!

### Opsi 2: Render (GRATIS)

Lihat `DEPLOY_RENDER.md` untuk instruksi.

### Opsi 3: Rumahweb Hosting

Lihat `DEPLOY_GUIDE.md` untuk instruksi (paket GROW minimal).

---

## 🔑 Environment Variables

| Variable | Perlu | Contoh |
|---|---|---|
| `DATABASE_URL` | ✅ | `postgresql://neondb_owner:xxx@ep-xxx...neon.tech/neondb?sslmode=require` |
| `SECRET_KEY` | ✅ | `a3f2...9c1b` (32+ karakter random) |
| `CORS_ORIGINS` | ✅ | `https://your-app.koyeb.app` atau `http://localhost:5173` |
| `APP_NAME` | ⚙️ | `Yazmina Hijab Web` |
| `APP_VERSION` | ⚙️ | `1.0.0` |

### Generate SECRET_KEY

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

---

## 📝 Catatan Penting

### 1. Database Shared

Desktop app dan web app **share database yang sama** (Neon PostgreSQL). Pastikan URL-Nya benar di `.env`.

### 2. Admin User

Setiap instalasi baru butuh admin user. Jalankan:

```bash
cd backend
python setup_dev.py --auto
```

### 3. Migrasi Database

Alembic migration sudah disiapkan. Jalankan saat diperlukan:

```bash
cd backend
alembic upgrade head
```

### 4. Cold Start (Free Tier)

Di hosting gratis (Koyeb/Render), aplikasi akan "tidur" saat idle dan bangun saat ada request (~10-30 detik). Ini normal untuk free tier.

---

## 📄 Lisensi

Aplikasi ini milik **Yazmina Hijab**.

---

## 🤝 Contact

- **Developer:** Kasolid
- **Repo:** https://github.com/Kasolid12/yazmina-hijab-web
