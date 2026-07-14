<p align="center">
  <img src="https://img.shields.io/badge/ESSA%20STORE-v0.8-00F0FF?style=for-the-badge&labelColor=090A0F" alt="ESSA STORE v0.8"/>
  <img src="https://img.shields.io/badge/PySide6-6.6%2B-00F0FF?style=for-the-badge&labelColor=090A0F" alt="PySide6"/>
  <img src="https://img.shields.io/badge/SQLAlchemy-2.0%2B-00F0FF?style=for-the-badge&labelColor=090A0F" alt="SQLAlchemy"/>
  <img src="https://img.shields.io/badge/Python-3.11%2B-00F0FF?style=for-the-badge&labelColor=090A0F" alt="Python"/>
</p>

# ⚡ ESSA STORE — Unified Operations Platform

**ESSA STORE** is a desktop-based business operations management system built with Python and PySide6 (Qt). It features a distinctive **cyberpunk industrial UI** — dark, neon-accented, and grid-focused — designed for fast daily data entry and operational oversight.

> Built for small-to-medium retail & production businesses that need an all-in-one tool for daily records, payroll, stock management, invoicing, and financial simulation — no internet required.

---

## ✨ Features

### 📋 Catatan Harian (Daily Records)
Track daily production output (cutting & distribution), operational expenses (`ModalOperasional`), and offline spending (`PengeluaranOffline`).

### 💰 Hutang & Pelunasan (Debt & Payments)
Manage debt entries and payment plans with full ledger history (`DebtEntry`, `DebtPayment`).

### 👔 Payroll & Bon (Payroll & Advances)
- **Payroll runs** with per-worker line items (`SalaryRun`, `SalaryLineItem`)
- **Bon system** (employee advances) with balance tracking (`BonBalance`, `BonMovement`)
- **Attendance records** and **Pengsup reconciliation**
- Export salary slips as PDF

### 📦 Stock Manager
Track stock movements (`StockMovement`) with full audit logging (`AuditLog`). Supports stock additions and reductions.

### 🧾 Invoice & Piutang (Invoices & Receivables)
Generate invoices with line items (`Invoice`, `InvoiceLine`), manage client receivables and track payment status (`ClientReceivable`, `ClientReceivablePayment`). Exports as PDF.

### 📊 Profit Simulation
Run profit projections and scenarios with history tracking (`ProfitHistory`).

### 🗃️ Data Manager
Master data management including:
- **SKU Master** — product catalog
- **Garapan Rate** / **Tarif Master** — pricing & rate tables
- **Person** — employee & client registry
- **App Settings** — application configuration

### 🎛️ Dashboard
Central overview showing key metrics, recent activity, and quick status at a glance.

---

## 🖥️ Screenshots

> *(Screenshots coming soon — the app runs as a native desktop window with a dark cyberpunk theme, cyan neon accents, and sharp grid-based panels.)*

---

## 🏗️ Architecture

```
essa-store-app/
├── main.py                      # Application entry point
├── requirements.txt             # Python dependencies
├── alembic.ini                  # Alembic DB migration config
├── .gitignore                   # Git ignore rules
│
├── data/                        # Data layer
│   ├── database.py              # SQLAlchemy engine & session
│   ├── dashboard_queries.py     # Dashboard aggregate queries
│   ├── excel_importer.py        # Excel import utilities
│   ├── models/                  # SQLAlchemy ORM models
│   │   ├── base.py              # DeclarativeBase
│   │   ├── sku.py               # SkuMaster
│   │   ├── person.py            # Person (employees, clients)
│   │   ├── master.py            # GarapanRate, TarifMaster, AppSetting
│   │   ├── catatan_harian.py    # Daily records models
│   │   ├── debt.py              # Debt & payment models
│   │   ├── bon.py               # Bon (advance) models
│   │   ├── salary.py            # Payroll models
│   │   ├── invoice.py           # Invoice & receivable models
│   │   ├── stock_audit.py       # Stock movement & audit
│   │   └── profit_history.py    # Profit simulation history
│   └── migrations/              # Alembic database migrations
│       ├── env.py
│       ├── script.py.mako
│       └── versions/            # Migration version scripts
│
├── ui/                          # User interface layer
│   ├── theme.py                 # Cyberpunk theme (colors, stylesheet)
│   ├── components/              # Reusable UI widgets
│   │   ├── buttons.py           # CyberButton custom widget
│   │   └── tables.py            # Custom table widgets
│   └── views/                   # Application views (one per module)
│       ├── dashboard_view.py
│       ├── harian_view.py       # Catatan Harian
│       ├── hutang_view.py       # Hutang & Pelunasan
│       ├── gaji_view.py         # Payroll & Bon
│       ├── stock_view.py        # Stock Manager
│       ├── invoice_view.py      # Invoice & Piutang
│       ├── profit_view.py       # Profit Simulation
│       └── master_view.py       # Data Manager
│
└── utils/                       # Utilities
    ├── backup_engine.py         # Automatic database backup
    └── pdf_engine.py            # PDF generation (invoices, slips, receipts)
```

### Tech Stack

| Component | Technology |
|-----------|-----------|
| **GUI Framework** | [PySide6](https://doc.qt.io/qtforpython-6/) (Qt 6 for Python) |
| **Database ORM** | [SQLAlchemy](https://www.sqlalchemy.org/) 2.0+ |
| **Database** | SQLite (local file-based) |
| **Migrations** | [Alembic](https://alembic.sqlalchemy.org/) |
| **PDF Generation** | [ReportLab](https://www.reportlab.com/) |
| **Excel Export** | [OpenPyXL](https://openpyxl.readthedocs.io/) + [Pandas](https://pandas.pydata.org/) |
| **Logging** | [Loguru](https://loguru.readthedocs.io/) |

---

## 🚀 Getting Started

### Prerequisites
- Python 3.11 or higher
- pip (Python package manager)

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/YOUR_USERNAME/essa-store-app.git
cd essa-store-app

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the application
python main.py
```

The application will automatically:
- Create the SQLite database file (`essa.db`) on first run
- Apply any pending database migrations
- Sync master tariff data for the payroll dropdown
- Launch the main window

### First Run

On first launch, you'll see the **Dashboard** view. Use the sidebar navigation to access each module. Start by adding your master data (SKUs, rates, persons) in the **Data Manager**, then proceed with daily operations.

---

## 🎨 Theming

The app features a **cyberpunk industrial** dark theme:

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

All theme variables are defined in `ui/theme.py` and can be customized globally.

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

## 🔄 Database Backups

The app automatically creates database backups in the `backups/` directory when the application exits. The backup engine (`utils/backup_engine.py`) timestamps each backup file for recovery purposes.

---

## 🧑‍💻 Development

### Database Migrations

After modifying models in `data/models/`, generate a new migration:

```bash
alembic revision --autogenerate -m "description_of_change"
alembic upgrade head
```

### Adding a New View

1. Create a new view file in `ui/views/`
2. Register the view class in `main.py` (see `switch_page()` method)
3. Add a sidebar button in `build_sidebar()`

---

## 🛠️ Built With

- **[PySide6](https://doc.qt.io/qtforpython-6/)** — Official Python binding for the Qt 6 framework
- **[SQLAlchemy 2.0](https://www.sqlalchemy.org/)** — Python SQL toolkit and ORM
- **[Alembic](https://alembic.sqlalchemy.org/)** — Lightweight database migration tool
- **[ReportLab](https://www.reportlab.com/)** — PDF generation library
- **[OpenPyXL](https://openpyxl.readthedocs.io/)** — Excel file reading/writing
- **[Pandas](https://pandas.pydata.org/)** — Data manipulation and analysis
- **[Loguru](https://loguru.readthedocs.io/)** — Python logging library

---

## 📝 License

This project is developed for internal business operations.

---

<p align="center">
  <sub>Built with Python & Qt · ESSA STORE Operations OS v0.8</sub>
  <br>
  <sub>⚡ Cyberpunk · Industrial · Offline-First ⚡</sub>
</p>
