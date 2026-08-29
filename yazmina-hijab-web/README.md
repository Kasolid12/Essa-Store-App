# 🌐 Yazmina Hijab — Web Version

> **Status:** Fase 0 — Fondasi · **Platform:** FastAPI (Python) + React (Vite)

Aplikasi operasional bisnis **Yazmina Hijab** versi web — akses dari browser, login admin, database terpusat.

## Arsitektur

```
Browser (React SPA) ←── HTTPS/JSON ──→ FastAPI (Python) ←──→ PostgreSQL (Neon)
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI + SQLAlchemy 2.0 |
| Frontend | React 19 + Vite + TanStack Query |
| Database | PostgreSQL (Neon) |
| Auth | JWT (httpOnly cookie) + bcrypt |
| Theme | Cyberpunk Industrial (CSS custom properties) |

## Quick Start

### 1. Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate    # Linux/Mac
pip install -r requirements.txt
cp .env.example .env          # Edit with your Neon URL + SECRET_KEY
python create_admin.py        # Create admin user
uvicorn app.main:app --reload # Run on http://127.0.0.1:8000
```

### 2. Frontend

```bash
cd frontend
npm install
npm run dev                   # Run on http://localhost:5173
```

### 3. Login

Open `http://localhost:5173` → login with admin credentials.

## Structure

```
yazmina-hijab-web/
├── backend/                  # FastAPI
│   ├── app/
│   │   ├── main.py           # Entry point
│   │   ├── config.py         # Settings from .env
│   │   ├── database.py       # Engine + session
│   │   ├── auth.py           # JWT + login/logout
│   │   ├── models/           # SQLAlchemy models
│   │   ├── schemas/          # Pydantic request/response
│   │   ├── routers/          # API routes per module
│   │   └── services/         # Business logic
│   ├── create_admin.py       # Create first admin
│   └── requirements.txt
├── frontend/                 # React + Vite
│   ├── src/
│   │   ├── theme.css         # Cyberpunk industrial tokens
│   │   ├── api/client.js     # API fetch wrapper
│   │   ├── pages/            # Login, Dashboard, etc.
│   │   ├── components/       # Sidebar, etc.
│   │   └── App.jsx           # Router + auth
│   └── package.json
└── README.md
```

## Roadmap

| Phase | Description |
|-------|-------------|
| **Fase 0** ✅ | Foundation: FastAPI + React skeleton, cyberpunk theme, login + JWT auth |
| **Fase 1** | Data & Master: SKU, Person, Client CRUD + Import Excel |
| **Fase 2** | Catatan Harian: 4 tab (Cutting, Distribusi, Pengeluaran, Modal) |
| **Fase 3** | Hutang & Pelunasan: multi-select, batch payment, PDF nota |
| **Fase 4** | Payroll & Bon: penjahit, pengsup, absensi, kasbon |
| **Fase 5** | Invoice & Stock: FIFO piutang, BigSeller export |
| **Fase 6** | Profit & Dashboard: full KPI queries, profit analysis |
| **Fase 7** | Data Migration: SQLite → server, verification |
| **Fase 8** | Deploy & Hardening: HTTPS, backup, go-live |
