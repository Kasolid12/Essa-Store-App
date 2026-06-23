# app_essa/ui/views/dashboard_view.py
"""Dashboard Essa Store.

Menampilkan 4 KPI utama (Total Hutang, Total Piutang, Gaji Karyawan, Profit
Produksi) dengan filter rentang waktu. Semua angka dihitung lewat fungsi di
`data/dashboard_queries.py` — view ini tidak punya query SQL sendiri.

Catatan rentang waktu:
- Hutang & Piutang  = SALDO TERKINI (snapshot), tidak terpengaruh filter tanggal
  karena fungsi query-nya memang tidak menerima rentang.
- Gaji Karyawan & Profit Produksi = difilter berdasarkan rentang tanggal aktif.
"""

import calendar
from datetime import date, timedelta

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QFrame, QDateEdit,
)
from PySide6.QtCore import Qt, QDate

from ui.theme import Theme
from ui.components.buttons import CyberButton
from data.database import SessionLocal
from data.dashboard_queries import (
    get_total_hutang_tersisa,
    get_total_piutang,
    get_akumulasi_gaji_karyawan,
    get_profit_produksi,
)


class DashboardView(QWidget):
    def __init__(self, notifier=None):
        super().__init__()
        self.db = SessionLocal()
        self.notifier = notifier

        # Rentang tanggal aktif (string 'YYYY-MM-DD'), default = bulan ini.
        today = date.today()
        self.tgl_mulai = today.replace(day=1).strftime("%Y-%m-%d")
        self.tgl_akhir = today.strftime("%Y-%m-%d")

        self.setup_ui()

        # Default tampilan: Bulan Ini (sekaligus refresh pertama).
        self.set_range_bulan_ini()

        # Auto-refresh bila ada perubahan data dari menu lain (mis. profit).
        if self.notifier:
            self.notifier.database_changed.connect(self.refresh_data)

    # ------------------------------------------------------------------ UI ---
    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(18)

        # --- HEADER: judul + tombol refresh ---
        header = QHBoxLayout()
        title = QLabel("Dashboard Essa Store")
        title.setStyleSheet(
            f"font-size: 26pt; font-weight: bold; color: {Theme.NEON_CYAN};"
        )
        header.addWidget(title)
        header.addStretch()

        btn_refresh = CyberButton("↻ REFRESH")
        btn_refresh.clicked.connect(self.refresh_data)
        header.addWidget(btn_refresh, 0, Qt.AlignmentFlag.AlignTop)
        main_layout.addLayout(header)

        # --- FILTER RENTANG WAKTU ---
        filter_frame = QFrame()
        filter_frame.setObjectName("GridPanel")
        filter_lay = QHBoxLayout(filter_frame)
        filter_lay.setContentsMargins(15, 12, 15, 12)
        filter_lay.setSpacing(10)

        btn_today = CyberButton("HARI INI")
        btn_week = CyberButton("MINGGU INI")
        btn_month = CyberButton("BULAN INI")
        btn_today.clicked.connect(self.set_range_hari_ini)
        btn_week.clicked.connect(self.set_range_minggu_ini)
        btn_month.clicked.connect(self.set_range_bulan_ini)

        self.date_mulai = self._make_date_edit()
        self.date_akhir = self._make_date_edit()

        btn_apply = CyberButton("TERAPKAN")
        btn_apply.clicked.connect(self.apply_custom_range)

        filter_lay.addWidget(btn_today)
        filter_lay.addWidget(btn_week)
        filter_lay.addWidget(btn_month)
        filter_lay.addStretch()
        filter_lay.addWidget(QLabel("Dari:"), 0, Qt.AlignmentFlag.AlignRight)
        filter_lay.addWidget(self.date_mulai)
        filter_lay.addWidget(QLabel("Sampai:"), 0, Qt.AlignmentFlag.AlignRight)
        filter_lay.addWidget(self.date_akhir)
        filter_lay.addWidget(btn_apply)
        main_layout.addWidget(filter_frame)

        # --- KETERANGAN PERIODE AKTIF ---
        self.lbl_range_info = QLabel("")
        self.lbl_range_info.setStyleSheet(f"color: {Theme.TEXT_MUTED};")
        main_layout.addWidget(self.lbl_range_info)

        # --- GRID 2x2 CARD ---
        grid = QGridLayout()
        grid.setSpacing(18)

        card_hutang, self.lbl_hutang = self._make_card(
            "Total Hutang Tersisa", Theme.NEON_PINK
        )
        card_piutang, self.lbl_piutang = self._make_card(
            "Total Piutang", Theme.NEON_YELLOW
        )
        card_gaji, self.lbl_gaji = self._make_card(
            "Gaji Karyawan", Theme.NEON_CYAN
        )
        card_profit, self.lbl_profit = self._make_card(
            "Profit Produksi", Theme.NEON_CYAN
        )

        grid.addWidget(card_hutang, 0, 0)
        grid.addWidget(card_piutang, 0, 1)
        grid.addWidget(card_gaji, 1, 0)
        grid.addWidget(card_profit, 1, 1)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        main_layout.addLayout(grid)

        # --- CATATAN KAKI ---
        note = QLabel(
            "* Hutang & Piutang menampilkan saldo terkini (tidak terpengaruh "
            "filter tanggal). Filter berlaku untuk Gaji Karyawan & Profit Produksi."
        )
        note.setWordWrap(True)
        note.setStyleSheet(f"color: {Theme.TEXT_MUTED}; font-size: 9pt;")
        main_layout.addWidget(note)

        main_layout.addStretch()

    def _make_date_edit(self):
        """QDateEdit dengan kalender popup, distyle agar konsisten dgn input field."""
        de = QDateEdit()
        de.setCalendarPopup(True)
        de.setDisplayFormat("yyyy-MM-dd")
        de.setDate(QDate.currentDate())
        de.setMinimumWidth(130)
        de.setStyleSheet(
            f"background-color: {Theme.BG_VOID}; border: 1px solid {Theme.BORDER_DIM}; "
            f"color: {Theme.NEON_CYAN}; padding: 6px;"
        )
        return de

    def _make_card(self, title, accent):
        """Bangun satu KPI card. Return (frame, label_nilai)."""
        card = QFrame()
        card.setMinimumHeight(130)
        card.setStyleSheet(
            f"""
            QFrame {{
                background-color: {Theme.BG_PANEL};
                border: 1px solid {Theme.BORDER_DIM};
                border-left: 4px solid {accent};
            }}
            QLabel {{ background-color: transparent; border: none; }}
            """
        )
        lay = QVBoxLayout(card)
        lay.setContentsMargins(20, 18, 20, 18)
        lay.setSpacing(10)

        lbl_title = QLabel(title.upper())
        lbl_title.setStyleSheet(
            f"color: {Theme.TEXT_MUTED}; font-size: 11pt; font-weight: bold; "
            f"letter-spacing: 1px;"
        )

        lbl_value = QLabel("Rp 0")
        lbl_value.setStyleSheet(self._value_style(accent))

        lay.addWidget(lbl_title)
        lay.addStretch()
        lay.addWidget(lbl_value, 0, Qt.AlignmentFlag.AlignRight)
        return card, lbl_value

    @staticmethod
    def _value_style(color):
        return (
            f"font-size: 22pt; font-weight: bold; color: {color}; "
            f"background: transparent; border: none;"
        )

    # -------------------------------------------------------------- HELPERS ---
    def format_rupiah(self, value):
        return f"Rp {value:,.0f}".replace(",", ".")

    def _apply_range(self, mulai: date, akhir: date):
        """Set rentang aktif, sinkronkan date picker, lalu refresh."""
        self.tgl_mulai = mulai.strftime("%Y-%m-%d")
        self.tgl_akhir = akhir.strftime("%Y-%m-%d")
        # Sinkronkan tampilan date picker (block sinyal supaya tidak memicu apa-apa)
        for de, d in ((self.date_mulai, mulai), (self.date_akhir, akhir)):
            de.blockSignals(True)
            de.setDate(QDate(d.year, d.month, d.day))
            de.blockSignals(False)
        self.refresh_data()

    # --------------------------------------------------------- RANGE PRESETS ---
    def set_range_hari_ini(self):
        today = date.today()
        self._apply_range(today, today)

    def set_range_minggu_ini(self):
        today = date.today()
        senin = today - timedelta(days=today.weekday())  # Senin minggu ini
        minggu = senin + timedelta(days=6)               # Minggu (akhir pekan)
        self._apply_range(senin, minggu)

    def set_range_bulan_ini(self):
        today = date.today()
        awal = today.replace(day=1)
        akhir_hari = calendar.monthrange(today.year, today.month)[1]
        akhir = today.replace(day=akhir_hari)
        self._apply_range(awal, akhir)

    def apply_custom_range(self):
        """Ambil rentang dari kedua date picker (tombol TERAPKAN)."""
        qd1 = self.date_mulai.date()
        qd2 = self.date_akhir.date()
        if qd1 > qd2:
            qd1, qd2 = qd2, qd1  # tukar bila terbalik
            self.date_mulai.setDate(qd1)
            self.date_akhir.setDate(qd2)
        self.tgl_mulai = qd1.toString("yyyy-MM-dd")
        self.tgl_akhir = qd2.toString("yyyy-MM-dd")
        self.refresh_data()

    # ----------------------------------------------------------- DATA RELOAD ---
    def refresh_data(self):
        """Tarik ulang semua KPI dari dashboard_queries dan render ke card."""
        # Buang cache session agar membaca kondisi DB terbaru.
        self.db.expire_all()
        try:
            hutang = get_total_hutang_tersisa(self.db)
            piutang = get_total_piutang(self.db)
            gaji = get_akumulasi_gaji_karyawan(self.db, self.tgl_mulai, self.tgl_akhir)
            profit = get_profit_produksi(self.db, self.tgl_mulai, self.tgl_akhir)
        except Exception as e:
            self.lbl_range_info.setText(f"Gagal memuat data dashboard: {e}")
            self.lbl_range_info.setStyleSheet(f"color: {Theme.NEON_PINK};")
            return

        self.lbl_hutang.setText(self.format_rupiah(hutang))
        self.lbl_piutang.setText(self.format_rupiah(piutang))
        self.lbl_gaji.setText(self.format_rupiah(gaji))
        self.lbl_profit.setText(self.format_rupiah(profit))

        # Warna Profit mengikuti tanda: hijau bila positif, pink bila rugi.
        profit_color = "#69F0AE" if profit >= 0 else Theme.NEON_PINK
        self.lbl_profit.setStyleSheet(self._value_style(profit_color))

        self.lbl_range_info.setText(
            f"Periode aktif (Gaji & Profit): {self.tgl_mulai}  s/d  {self.tgl_akhir}"
        )
        self.lbl_range_info.setStyleSheet(f"color: {Theme.TEXT_MUTED};")
