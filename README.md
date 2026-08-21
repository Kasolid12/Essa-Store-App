<p align="center">
  <img src="https://img.shields.io/badge/YAZMINA%20HIJAB-v0.8-00F0FF?style=for-the-badge&labelColor=090A0F" alt="Yazmina Hijab v0.8"/>
  <img src="https://img.shields.io/badge/PySide6-6.6%2B-00F0FF?style=for-the-badge&labelColor=090A0F" alt="PySide6"/>
  <img src="https://img.shields.io/badge/SQLAlchemy-2.0%2B-00F0FF?style=for-the-badge&labelColor=090A0F" alt="SQLAlchemy"/>
  <img src="https://img.shields.io/badge/Python-3.11%2B-00F0FF?style=for-the-badge&labelColor=090A0F" alt="Python"/>
  <img src="https://img.shields.io/badge/PostgreSQL-Neon-00F0FF?style=for-the-badge&labelColor=090A0F" alt="Neon PostgreSQL"/>
</p>

# ⚡ YAZMINA HIJAB — Unified Operations Platform

**A complete, offline-first business operations system** for retail & garment production businesses. Built with Python and PySide6 (Qt), Yazmina Hijab unifies daily production records, debt management, payroll & employee advances, stock control, invoicing, and profit simulation into a single fast desktop application — **with optional multi-device cloud synchronization via Neon PostgreSQL**.

> Designed to keep working **100% offline**. Internet is only used — when available — to back up your data to the cloud and keep multiple computers in sync.

---

## ✨ Highlights

| | |
|---|---|
| 🖥️ **Desktop app, cyberpunk industrial UI** | Dark theme with neon accents, built for fast daily data entry |
| 🌐 **Offline-first** | Every feature works with zero internet connection |
| ☁️ **Cloud backup & multi-device sync** | Two-way sync with Neon PostgreSQL (optional) |
| ☁️ **Manual sync & live status** | One-click **SYNC NOW** button + cloud status indicator in the sidebar |
| 🧾 **PDF & Excel exports** | Invoices, receipts, salary slips, stock reports |
| 🔒 **Triple data safety** | Local SQLite + automatic local backups + cloud mirror |
| 🗄️ **26 relational tables** | Fully normalized, managed with SQLAlchemy 2.0 + Alembic migrations |

---

## 🧩 Features

### 📋 Catatan Harian (Daily Records)
Track daily production output (cutting & distribution), operational expenses, and offline spending.

### 💰 Hutang & Pelunasan (Debt & Payments)
Full ledger for debt entries and payments — including material (modal) debt and production-linked records.

### 👔 Payroll & Bon (Payroll & Employee Advances)
- Payroll runs with per-worker line items (borongan, pengsup, daily-wage teams)
- **Bon** (employee advance) system with live balance tracking
- Attendance records with overtime (lembur) calculation
- Export salary slips as **PDF**

### 📦 Stock Manager
Track stock movements with full audit logging; supports additions, reductions, and adjustments.

### 🧾 Invoice & Piutang (Invoices & Receivables)
Generate invoices with line items, manage client receivables and payment status. Export as **PDF**.

### 📊 Profit Simulation
Run profit projections and store calculation history.

### 🗃️ Data Manager
Master data: SKU product catalog, pricing/rate tables, persons (employees, clients, suppliers), and app settings.

### 🎛️ Dashboard
Central overview of key metrics — debt, receivables, payroll, and profit — refreshed live.

---

## 🏗️ Architecture

```
yazmina-hijab/
├── main.py                      # Application entry point
├── start_app.bat                # ★ Windows launcher (double-click) — uses the same Python as your terminal
├── requirements.txt             # Python dependencies
├── alembic.ini                  # Alembic DB migration config
├── .env                         # Cloud credentials (NOT committed)
│
├── data/                        # Data layer
│   ├── database.py              # SQLAlchemy engines (SQLite + cloud)
│   ├── dashboard_queries.py     # Dashboard aggregate queries
│   ├── excel_importer.py        # Excel import utilities
│   ├── models/                  # 26 SQLAlchemy ORM models
│   └── migrations/              # Alembic migration scripts
│
├── ui/                          # User interface layer
│   ├── theme.py                 # Cyberpunk theme (colors, stylesheet)
│   ├── components/              # Reusable UI widgets
│   └── views/                   # One view per module
│
└── utils/                       # Utilities
    ├── cloud_sync.py            # ★ Two-way cloud synchronization engine
    ├── sync_tables.py           # Table processing order (parents → children)
    ├── backup_engine.py         # Automatic local database backups
    └── pdf_engine.py            # PDF generation (invoices, slips, receipts)
```

### Tech Stack

| Component | Technology |
|-----------|------------|
| **GUI Framework** | [PySide6](https://doc.qt.io/qtforpython-6/) (Qt 6 for Python) |
| **ORM** | [SQLAlchemy](https://www.sqlalchemy.org/) 2.0+ |
| **Local Database** | SQLite (`essa.db`, file-based, offline-first) |
| **Cloud Database** | [Neon](https://neon.tech) PostgreSQL (serverless) — optional |
| **Migrations** | [Alembic](https://alembic.sqlalchemy.org/) |
| **PDF Generation** | [ReportLab](https://www.reportlab.com/) |
| **Excel Export** | [OpenPyXL](https://openpyxl.readthedocs.io/) + [Pandas](https://pandas.pydata.org/) |
| **Logging** | [Loguru](https://loguru.readthedocs.io/) |

---

## ☁️ Cloud Sync (Multi-Device)

- **Offline-first by design** — the app never depends on the internet; cloud is a mirror, not a requirement.
- **Two-way sync** runs automatically when the app **opens** (background thread) and **closes**: local → cloud (backup) and cloud → local (multi-device).
- **ID mapping layer** (`sync_id_map`) prevents the classic "both devices start at id 1" collision — each row keeps a definitive identity across devices.
- **Conflict resolution** via *last-write-wins* (`updated_at`) plus **per-row device ownership** (`created_by_device` / `updated_by_device`).
- **Safe deletes** — a device only removes rows it has seen (mapped), with tombstone protection against overwriting another device's newer edits.
- **Resilient** — unique-index conflicts are skipped per-row (with a console warning), never aborting the whole sync.
- **Manual control** — a **SYNC NOW** button in the sidebar with a live cloud status indicator (configured / syncing / last sync time / error).

📖 Deep technical explanation: [`CLOUD_SYSTEM.md`](CLOUD_SYSTEM.md)
📖 Migration guide (step-by-step): [`CLOUD_DATABASE_GUIDE.md`](CLOUD_DATABASE_GUIDE.md)

---

## 🚀 Getting Started

### Prerequisites
- Python 3.11+
- pip

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/YOUR_USERNAME/yazmina-hijab.git
cd yazmina-hijab

# 2. (Recommended) Create a virtual environment
python -m venv venv
source venv/Scripts/activate      # Windows (Git Bash); see INSTALL_GUIDE for others

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the application
#    Recommended: double-click start_app.bat (Windows) — it uses the same
#    Python as your terminal and verifies cloud dependencies first.
python main.py
```

> 💡 **On Windows, prefer `start_app.bat` over double-clicking `main.py`.**
> Double-clicking `main.py` can open it with a *different* Python that lacks the
> cloud driver (`psycopg2`), which silently disables cloud sync. The launcher
> uses the exact Python that works from your terminal.

The app automatically creates `essa.db`, applies any pending migrations, syncs payroll tariff master data, and opens the dashboard.

> 📦 **Full setup guide for new devices** (including moving your data and enabling cloud sync): [`INSTALL_GUIDE.md`](INSTALL_GUIDE.md)

### First Run

Start from the **Dashboard**, then add master data (SKUs, rates, persons) in the **Data Manager** before daily operations.

---

## 🎨 Theming

A cyberpunk industrial dark theme, fully defined in `ui/theme.py`:

```
🎨 Color Palette
─────────────────────────────────
BG_VOID     #090A0F   ████  Deep void background
BG_PANEL    #161925   ████  Panel surfaces
TEXT_MAIN   #E0E0E0   ████  Primary text
TEXT_MUTED  #8B93A5   ████  Muted / secondary text
NEON_CYAN   #00F0FF   ████  Primary accent / action
NEON_PINK   #FF003C   ████  Danger / delete
NEON_YELLOW #FCE205   ████  Warnings / pending
BORDER_DIM  #2A2E45   ████  Grid lines
```

---

## 📄 Export Formats

| Document | Format | Module |
|----------|--------|--------|
| Invoices | PDF | Invoice & Piutang |
| Receipts (Modal) | PDF | Hutang & Pelunasan |
| Salary Slips (Borongan) | PDF | Payroll & Bon |
| Employee Pay Slips | PDF | Payroll & Bon |
| Stock Reports | XLSX | Stock Manager |
| Attendance Format | XLSX | Payroll & Bon |

---

## 🔄 Data Safety

1. **Local database** — `essa.db` (SQLite), always the working copy.
2. **Automatic local backups** — copied to `backups/` on every app exit (last 30 kept).
3. **Cloud mirror (optional)** — two-way sync to Neon PostgreSQL; a new device can pull all data on first launch.

---

## 🧑‍💻 Development

### Database Migrations

After modifying models in `data/models/`:

```bash
alembic revision --autogenerate -m "description_of_change"
alembic upgrade head            # local (SQLite)
CLOUD_DATABASE_URL=... alembic upgrade head   # cloud (Postgres)
```

### Running the Two-Device Sync Tests

```bash
python scripts/_test_twoway.py   # 18-step E2E: ID collision, LWW, deletes, ownership
python scripts/_verify_all_counts.py  # local vs cloud row-count check
```

### Adding a New View

1. Create the view file in `ui/views/`.
2. Register it in `main.py` (`switch_page()`).
3. Add a sidebar button in `build_sidebar()`.

---

## 📚 Documentation

| Document | Purpose |
|---|---|
| [`README.md`](README.md) | This file — overview & quick start |
| [`INSTALL_GUIDE.md`](INSTALL_GUIDE.md) | Setup on a new device, moving data, troubleshooting |
| [`CLOUD_DATABASE_GUIDE.md`](CLOUD_DATABASE_GUIDE.md) | Step-by-step cloud migration guide (Fase 0–7) |
| [`CLOUD_SYSTEM.md`](CLOUD_SYSTEM.md) | How the cloud sync engine works, technically |

---

## 🛠️ Built With

- **[PySide6](https://doc.qt.io/qtforpython-6/)** — official Python binding for Qt 6
- **[SQLAlchemy 2.0](https://www.sqlalchemy.org/)** — Python SQL toolkit & ORM
- **[Alembic](https://alembic.sqlalchemy.org/)** — database migrations
- **[Neon PostgreSQL](https://neon.tech)** — serverless cloud database
- **[ReportLab](https://www.reportlab.com/)** — PDF generation
- **[OpenPyXL](https://openpyxl.readthedocs.io/)** — Excel read/write
- **[Pandas](https://pandas.pydata.org/)** — data manipulation
- **[Loguru](https://loguru.readthedocs.io/)** — logging

---

## 📝 License

Internal business software — developed for the operational needs of Yazmina Hijab. Not licensed for redistribution without permission.

---

<p align="center">
  <sub>Built with Python & Qt · Yazmina Hijab Operations OS v0.8</sub>
  <br>
  <sub>⚡ Cyberpunk · Industrial · Offline-First · Cloud-Ready ⚡</sub>
</p>
