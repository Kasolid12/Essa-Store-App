# app_essa/ui/views/invoice_view.py
import os
import datetime
import traceback
from sqlalchemy import func
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QTableWidgetItem, QHeaderView, QMessageBox, QAbstractItemView,
    QGridLayout, QLineEdit, QGroupBox, QComboBox,
    QDateEdit
)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QColor

from ui.components.tables import CyberTable
from ui.components.buttons import CyberButton
from ui.components.dialogs import CopyableErrorDialog
from ui.theme import Theme
from data.database import SessionLocal
from data.models import PengeluaranOffline, Person, Client
from data.models.invoice import ClientReceivable, ClientReceivablePayment, PaymentAllocation
from utils.pdf_engine import generate_invoice_pdf


def compute_transaction_statuses(rows, sales_alloc, payment_alloc=None):
    """Hitung status LUNAS/PARTIAL/BELUM LUNAS per transaksi.

    Prioritas:
      1. Alokasi eksplisit (tabel payment_allocations) — mengikuti transaksi
         yang DIPILIH user saat pelunasan.
      2. Porsi pembayaran yang BELUM dialokasikan (data lama, atau kelebihan
         deposit di atas total transaksi terpilih) → fallback FIFO:
         diterapkan ke penjualan terlama yang masih belum lunas.

    rows: list of dict {jenis: 'Penjualan'|'Pembayaran', debit, credit, ...}
          baris Penjualan punya 'sid', baris Pembayaran punya 'pid'.
    sales_alloc: {sales_id: total nominal yang dialokasikan ke transaksi itu}
    payment_alloc: {payment_id: total nominal payment tsb yang sudah dialokasikan}
                   None/{} = semua pembayaran dianggap tanpa alokasi (FIFO penuh).
    Mengisi r['status'] dan r['_sisa'] (sisa belum dibayar) pada tiap baris.
    """
    EPS = 0.005  # toleransi pembulatan float rupiah
    fifo_queue = []  # penjualan yang masih punya sisa, terlama dulu

    for r in rows:
        if r["jenis"] != "Penjualan":
            continue
        allocated = sales_alloc.get(r.get("sid"), 0.0)
        r["_sisa"] = max(0.0, r["debit"] - allocated)
        if r["_sisa"] <= EPS:
            r["status"] = "LUNAS"
        elif allocated > EPS:
            r["status"] = "PARTIAL"
        else:
            r["status"] = "BELUM LUNAS"
            fifo_queue.append(r)

    payment_alloc = payment_alloc or {}
    for r in rows:
        if r["jenis"] != "Pembayaran":
            continue
        # Hanya porsi yang belum dialokasikan yang masuk FIFO
        # (mencegah double-count untuk pembayaran yang sudah dialokasikan)
        sisa_bayar = r["credit"] - payment_alloc.get(r.get("pid"), 0.0)
        while sisa_bayar > EPS and fifo_queue:
            oldest = fifo_queue[0]
            pay = min(sisa_bayar, oldest["_sisa"])
            oldest["_sisa"] -= pay
            sisa_bayar -= pay
            if oldest["_sisa"] <= EPS:
                oldest["status"] = "LUNAS"
                fifo_queue.pop(0)
            elif oldest["status"] == "BELUM LUNAS":
                oldest["status"] = "PARTIAL"
        r["status"] = "LUNAS"
    return rows


class InvoiceView(QWidget):
    def __init__(self, notifier=None):
        super().__init__()
        self.db = SessionLocal()
        self.notifier = notifier
        self.selected_client_id = None
        self.selected_client_type = None
        self.selected_sales = []
        self.total_tagihan = 0.0
        self.total_tagihan_all = 0

        self.setup_ui()
        self.load_clients()
        if self.notifier:
            self.notifier.database_changed.connect(self.refresh_harian_tables)

    def refresh_harian_tables(self):
        """Menyegarkan seluruh data jika ada perubahan di menu lain"""
        self.db.expire_all()
        self.load_clients()
        if self.selected_client_id:
            self.load_client_data(self.selected_client_id)

    # ====================================================================
    # SETUP UI
    # ====================================================================
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # --- HEADER ---
        header = QHBoxLayout()
        title = QLabel("INVOICE & PIUTANG")
        title.setStyleSheet(f"font-size: 24pt; font-weight: bold; color: {Theme.NEON_CYAN};")
        header.addWidget(title)
        header.addStretch()
        btn_refresh = CyberButton("REFRESH DATA")
        btn_refresh.clicked.connect(lambda: self.refresh_harian_tables())
        header.addWidget(btn_refresh)
        layout.addLayout(header)

        # --- CLIENT DROPDOWN ---
        client_row = QHBoxLayout()
        client_row.addWidget(QLabel("Pilih Klien:"))
        self.cb_client = QComboBox()
        self.cb_client.setMinimumWidth(300)
        self.cb_client.setStyleSheet(
            f"background-color: #15151a; color: {Theme.TEXT_MAIN};"
            f" padding: 8px; border: 1px solid #2d2d38; border-radius: 4px;"
        )
        self.cb_client.currentIndexChanged.connect(self.on_client_selected)
        client_row.addWidget(self.cb_client)
        client_row.addStretch()
        layout.addLayout(client_row)

        # --- LABEL TABEL ---
        info_label = QLabel(
            "PILIH BARIS PENJUALAN (centang) untuk cetak invoice — "
            "deposit diisi di bawah"
        )
        info_label.setStyleSheet(
            f"color: {Theme.TEXT_MUTED}; font-weight: bold; margin-top: 6px;"
        )
        layout.addWidget(info_label)

        # --- COMBINED TRANSACTION TABLE ---
        self.table = CyberTable()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "ID", "Tanggal", "Keterangan",
            "Debit (Rp)", "Kredit (Rp)", "Sisa (Rp)", "Status"
        ])
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.itemSelectionChanged.connect(self.on_row_selected)
        layout.addWidget(self.table, stretch=1)

        # ====================================================================
        # BOTTOM PANEL: SUMMARY + DEPOSIT + ACTIONS
        # ====================================================================
        bottom_frame = QFrame()
        bottom_frame.setObjectName("GridPanel")
        bottom_lay = QVBoxLayout(bottom_frame)
        bottom_lay.setSpacing(8)

        # --- RINGKASAN PIUTANG (2 baris grid) ---
        sum_grid = QGridLayout()
        sum_grid.setSpacing(10)

        # Baris 0
        sum_grid.addWidget(QLabel("Total Tagihan:"), 0, 0)
        self.lbl_total_tagihan = QLabel("Rp 0")
        self.lbl_total_tagihan.setStyleSheet(
            f"font-size: 14pt; font-weight: bold; color: {Theme.NEON_PINK};"
        )
        sum_grid.addWidget(self.lbl_total_tagihan, 0, 1)

        sum_grid.addWidget(QLabel("Total Dibayar:"), 0, 2)
        self.lbl_total_bayar = QLabel("Rp 0")
        self.lbl_total_bayar.setStyleSheet(
            "font-size: 14pt; font-weight: bold; color: #4CAF50;"
        )
        sum_grid.addWidget(self.lbl_total_bayar, 0, 3)

        # Baris 1
        sum_grid.addWidget(QLabel("Sisa Piutang:"), 1, 0)
        self.lbl_sisa = QLabel("Rp 0")
        self.lbl_sisa.setStyleSheet(
            "font-size: 16pt; font-weight: bold; color: #F44336;"
        )
        sum_grid.addWidget(self.lbl_sisa, 1, 1)

        sum_grid.addWidget(QLabel("Status:"), 1, 2)
        self.lbl_status = QLabel("-")
        self.lbl_status.setStyleSheet(
            "font-size: 14pt; font-weight: bold; color: #9E9E9E;"
        )
        sum_grid.addWidget(self.lbl_status, 1, 3)

        bottom_lay.addLayout(sum_grid)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("background-color: #2d2d38;")
        bottom_lay.addWidget(sep)

        # --- BARIS 1: DEPOSIT + DISKON + JATUH TEMPO ---
        invoice_opt_row = QHBoxLayout()
        invoice_opt_row.setSpacing(10)

        invoice_opt_row.addWidget(QLabel("Deposit (Rp):"))
        self.ent_deposit = QLineEdit("0")
        self.ent_deposit.setStyleSheet(
            f"font-size: 12pt; font-weight: bold; background: {Theme.BG_VOID};"
            f" color: {Theme.TEXT_MAIN}; padding: 4px;"
        )
        self.ent_deposit.setMaximumWidth(130)
        invoice_opt_row.addWidget(self.ent_deposit)

        invoice_opt_row.addWidget(QLabel("Diskon (Rp):"))
        self.ent_diskon = QLineEdit("0")
        self.ent_diskon.setStyleSheet(
            f"font-size: 12pt; font-weight: bold; background: {Theme.BG_VOID};"
            f" color: {Theme.NEON_PINK}; padding: 4px;"
        )
        self.ent_diskon.setMaximumWidth(120)
        invoice_opt_row.addWidget(self.ent_diskon)

        invoice_opt_row.addWidget(QLabel("Tgl Dep:"))
        self.date_deposit = QDateEdit()
        self.date_deposit.setDate(QDate.currentDate())
        self.date_deposit.setCalendarPopup(True)
        self.date_deposit.setStyleSheet(
            f"background: {Theme.BG_VOID}; color: {Theme.TEXT_MAIN}; padding: 4px;"
        )
        self.date_deposit.setMaximumWidth(130)
        invoice_opt_row.addWidget(self.date_deposit)

        invoice_opt_row.addWidget(QLabel("Jatuh Tempo:"))
        self.date_jatuh_tempo = QDateEdit()
        self.date_jatuh_tempo.setDate(QDate.currentDate().addDays(30))
        self.date_jatuh_tempo.setCalendarPopup(True)
        self.date_jatuh_tempo.setStyleSheet(
            f"background: {Theme.BG_VOID}; color: {Theme.NEON_YELLOW}; padding: 4px;"
        )
        self.date_jatuh_tempo.setMaximumWidth(130)
        invoice_opt_row.addWidget(self.date_jatuh_tempo)

        invoice_opt_row.addWidget(QLabel("Metode:"))
        self.cb_metode = QComboBox()
        self.cb_metode.addItems(["TUNAI", "TRANSFER"])
        self.cb_metode.setStyleSheet(
            f"background: #15151a; color: {Theme.TEXT_MAIN}; padding: 4px;"
        )
        self.cb_metode.setMaximumWidth(100)
        invoice_opt_row.addWidget(self.cb_metode)

        invoice_opt_row.addStretch()
        bottom_lay.addLayout(invoice_opt_row)

        # --- BARIS 2: ACTION BUTTONS ---
        action_row = QHBoxLayout()
        action_row.setSpacing(10)

        self.btn_print = CyberButton("CETAK INVOICE PDF")
        self.btn_print.setStyleSheet(
            f"background-color: {Theme.NEON_CYAN}; color: black;"
            f" font-weight: bold; font-size: 11pt; padding: 10px;"
        )
        self.btn_print.setEnabled(False)
        self.btn_print.clicked.connect(self._save_and_print)
        action_row.addWidget(self.btn_print)

        self.btn_hapus_payment = CyberButton("HAPUS PEMBAYARAN")
        self.btn_hapus_payment.setStyleSheet(
            f"background-color: {Theme.NEON_PINK}; color: white;"
            f" font-weight: bold; font-size: 11pt; padding: 10px;"
        )
        self.btn_hapus_payment.setEnabled(False)
        self.btn_hapus_payment.clicked.connect(self.delete_selected_payment)
        action_row.addWidget(self.btn_hapus_payment)

        action_row.addStretch()
        bottom_lay.addLayout(action_row)
        layout.addWidget(bottom_frame)

    # ====================================================================
    # LOAD CLIENTS
    # ====================================================================
    def load_clients(self):
        """Muat daftar klien dari tabel Client + legacy Person (KLIEN/SUPPLIER)."""
        prev_id = self.selected_client_id

        self.cb_client.blockSignals(True)
        self.cb_client.clear()
        self.cb_client.addItem("-- Pilih Klien --", None)

        # --- Load dari Client table (baru) ---
        clients = (
            self.db.query(Client)
            .filter(Client.is_deleted == 0)
            .order_by(Client.nama)
            .all()
        )
        for c in clients:
            # Simpan dengan prefix CLIENT_ untuk membedakan dari Person legacy
            self.cb_client.addItem(c.nama, f"CLIENT_{c.id}")

        # --- Load dari Person table (legacy — memiliki transaksi offline atau piutang) ---
        person_ids = (
            self.db.query(PengeluaranOffline.person_id)
            .filter(PengeluaranOffline.is_deleted == 0)
            .filter(PengeluaranOffline.person_id.isnot(None))
            .distinct()
            .all()
        )
        ids_from_sales = {r[0] for r in person_ids if r[0]}

        cr_ids = (
            self.db.query(ClientReceivable.person_id)
            .filter(ClientReceivable.person_id.isnot(None))
            .distinct()
            .all()
        )
        ids_from_cr = {r[0] for r in cr_ids if r[0]}

        all_person_ids = ids_from_sales | ids_from_cr
        persons = (
            self.db.query(Person)
            .filter(Person.id.in_(all_person_ids))
            .order_by(Person.nama)
            .all()
        ) if all_person_ids else []

        for p in persons:
            self.cb_client.addItem(f"{p.nama} (Person)", p.id)

        self.cb_client.blockSignals(False)

        if prev_id:
            idx = self.cb_client.findData(prev_id)
            if idx >= 0:
                self.cb_client.setCurrentIndex(idx)
                return

        if self.cb_client.count() > 1:
            self.cb_client.setCurrentIndex(1)

    # ====================================================================
    # CLIENT SELECTION
    # ====================================================================
    def on_client_selected(self, idx=None):
        """Dipanggil saat user memilih klien dari dropdown."""
        raw = self.cb_client.currentData()
        if not raw:
            self.selected_client_id = None
            self.selected_client_type = None
            self.reset_all()
            return
        
        # Deteksi apakah ini Client baru (prefix CLIENT_) atau Person lama
        if isinstance(raw, str) and raw.startswith("CLIENT_"):
            self.selected_client_id = int(raw.replace("CLIENT_", ""))
            self.selected_client_type = "client"
        else:
            self.selected_client_id = raw
            self.selected_client_type = "person"
        
        self.load_client_data(self.selected_client_id)

    def _get_filter_field(self, field_type="sales"):
        """Kembalikan field filter yang sesuai berdasarkan tipe klien."""
        if getattr(self, 'selected_client_type', None) == "client":
            if field_type == "sales":
                return PengeluaranOffline.client_id
            else:
                return ClientReceivable.client_id
        else:
            if field_type == "sales":
                return PengeluaranOffline.person_id
            else:
                return ClientReceivable.person_id

    def load_client_data(self, ref_id):
        """Muat kombinasi tabel + summary untuk satu klien."""
        self.selected_client_id = ref_id
        try:
            # Self-healing: recalculate receivable dari data nyata setiap load
            self._recalculate_receivable(ref_id)
            self.load_combined_table(ref_id)
            self.load_summary(ref_id)
        except Exception as e:
            # Safety net: rollback jika ada error database
            self.db.rollback()
            self.db.expire_all()
            # Tampilkan tabel kosong daripada crash
            self.table.setRowCount(0)
            self.lbl_total_tagihan.setText("Rp 0")
            self.lbl_total_bayar.setText("Rp 0")
            self.lbl_sisa.setText("Rp 0")
            self.lbl_status.setText("ERROR")
            self.lbl_status.setStyleSheet(
                f"font-size: 14pt; font-weight: bold; color: {Theme.NEON_PINK};"
            )
            QMessageBox.warning(
                self, "Error Database",
                f"Gagal memuat data klien:\n{str(e)}\n\n"
                f"Silakan coba refresh data atau pilih klien lain."
            )
        # Set deposit default, reset selection (dijalankan di luar try)
        self.ent_deposit.setText("0")
        self.ent_diskon.setText("0")
        self.date_deposit.setDate(QDate.currentDate())
        self.date_jatuh_tempo.setDate(QDate.currentDate().addDays(30))
        self.selected_sales = []

    # ====================================================================
    # COMBINED TRANSACTION TABLE (penjualan + pembayaran)
    # ====================================================================
    def load_combined_table(self, person_id):
        """Satu tabel penjualan + pembayaran dengan running balance & status
        per transaksi (alokasi pembayaran eksplisit, fallback FIFO)."""
        self.table.setRowCount(0)
        rows = self._get_combined_rows(person_id)
        if not rows:
            return

        sales_alloc, payment_alloc = self._get_allocations(person_id, rows)
        compute_transaction_statuses(rows, sales_alloc, payment_alloc)

        # Populasi tabel
        running = 0.0
        self.table.setRowCount(len(rows))
        for i, r in enumerate(rows):
            running += r["debit"] - r["credit"]

            # Kolom 0: ID transaksi (internal) + metadata untuk aksi lanjutan
            id_item = QTableWidgetItem(str(r.get("id", "")))
            id_item.setData(Qt.ItemDataRole.UserRole, {
                "id": r.get("id"),
                "sid": r.get("sid"),
                "debit": r["debit"],
                "credit": r["credit"],
            })
            self.table.setItem(i, 0, id_item)

            # Kolom 1: Tanggal
            self.table.setItem(i, 1, QTableWidgetItem(r["tanggal"]))

            # Kolom 2: Keterangan
            self.table.setItem(i, 2, QTableWidgetItem(r["keterangan"]))

            # Kolom 3: Debit (tagihan)
            debit_text = f"Rp {r['debit']:,.0f}" if r['debit'] > 0 else "-"
            debit_item = QTableWidgetItem(debit_text)
            debit_item.setTextAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )
            if r['jenis'] == "Penjualan":
                debit_item.setForeground(QColor(Theme.NEON_PINK))
            self.table.setItem(i, 3, debit_item)

            # Kolom 4: Kredit (pembayaran)
            kredit_text = f"Rp {r['credit']:,.0f}" if r['credit'] > 0 else "-"
            kredit_item = QTableWidgetItem(kredit_text)
            kredit_item.setTextAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )
            if r['credit'] > 0:
                kredit_item.setForeground(QColor("#4CAF50"))
            self.table.setItem(i, 4, kredit_item)

            # Kolom 5: Sisa (running balance)
            sisa_item = QTableWidgetItem(f"Rp {running:,.0f}")
            sisa_item.setTextAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )
            sisa_item.setForeground(
                QColor("#4CAF50") if running <= 0 else QColor("#F44336")
            )
            self.table.setItem(i, 5, sisa_item)

            # Kolom 6: Status (LUNAS/PARTIAL/BELUM LUNAS)
            status_item = QTableWidgetItem(r["status"])
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if r["status"] == "LUNAS":
                status_item.setForeground(QColor("#4CAF50"))
            elif r["status"] == "PARTIAL":
                status_item.setForeground(QColor("#FFC107"))
            else:
                status_item.setForeground(QColor("#F44336"))
            self.table.setItem(i, 6, status_item)

    def _get_combined_rows(self, ref_id):
        """Query + sort penjualan & pembayaran jadi list of dict."""
        sales_filter = self._get_filter_field("sales")
        rows = []
        client_name = ""

        # Penjualan offline — gunakan filter yang sesuai
        sales = (
            self.db.query(PengeluaranOffline)
            .filter(sales_filter == ref_id)
            .filter(PengeluaranOffline.is_deleted == 0)
            .order_by(PengeluaranOffline.tanggal, PengeluaranOffline.id)
            .all()
        )
        for s in sales:
            sku = s.sku.kode_sku if s.sku else "-"
            qty_str = f"{int(s.qty)}" if s.qty == int(s.qty) else f"{s.qty:g}"
            # Ambil nama dari client atau person
            if s.client:
                nama_pembeli = s.client.nama
            elif s.person:
                nama_pembeli = s.person.nama
            else:
                nama_pembeli = ""
            rows.append({
                "id": f"S{s.id}",
                "sid": s.id,
                "sort_key": (s.tanggal, 0, s.id),
                "tanggal": s.tanggal,
                "jenis": "Penjualan",
                "keterangan": f"{sku} x{qty_str}  |  {nama_pembeli}",
                "debit": float(s.total),
                "credit": 0.0,
            })
            if nama_pembeli:
                client_name = nama_pembeli

        # Pembayaran — gunakan filter yang sesuai
        receivable_filter = self._get_filter_field("receivable")
        receivable = (
            self.db.query(ClientReceivable)
            .filter(receivable_filter == ref_id)
            .first()
        )
        if receivable:
            payments = (
                self.db.query(ClientReceivablePayment)
                .filter(ClientReceivablePayment.receivable_id == receivable.id)
                .order_by(ClientReceivablePayment.tanggal_bayar, ClientReceivablePayment.id)
                .all()
            )
            for p in payments:
                rows.append({
                    "id": f"P{p.id}",
                    "pid": p.id,
                    "sort_key": (p.tanggal_bayar, 1, p.id),
                    "tanggal": p.tanggal_bayar,
                    "jenis": "Pembayaran",
                    "keterangan": f"Deposit ({p.metode})",
                    "debit": 0.0,
                    "credit": float(p.nominal_bayar),
                })

        # Sort by (tanggal, jenis=0 Penjualan dulu, 1 Pembayaran, id)
        rows.sort(key=lambda r: r["sort_key"])
        return rows

    def _get_allocations(self, ref_id, rows):
        """Ambil alokasi pembayaran untuk klien ini.

        Kembalikan (sales_alloc, payment_alloc):
          sales_alloc   : {sales_id: total nominal dialokasikan ke transaksi itu}
                          hanya untuk sales yang tampil di tabel.
          payment_alloc : {payment_id: total nominal payment tsb yang sudah
                          dialokasikan} — termasuk alokasi ke sales yang sudah
                          tidak tampil, agar porsi itu tidak di-FIFO dua kali.
        """
        sales_alloc, payment_alloc = {}, {}
        try:
            receivable_filter = self._get_filter_field("receivable")
            receivable = (
                self.db.query(ClientReceivable)
                .filter(receivable_filter == ref_id)
                .first()
            )
            if not receivable:
                return sales_alloc, payment_alloc
            visible = {int(r["sid"]) for r in rows if r.get("sid")}
            q = (
                self.db.query(
                    PaymentAllocation.payment_id,
                    PaymentAllocation.sales_id,
                    PaymentAllocation.nominal,
                )
                .join(ClientReceivablePayment,
                      PaymentAllocation.payment_id == ClientReceivablePayment.id)
                .filter(ClientReceivablePayment.receivable_id == receivable.id)
                .all()
            )
            for pid, sid, nominal in q:
                n = float(nominal or 0.0)
                pid, sid = int(pid), int(sid)
                payment_alloc[pid] = payment_alloc.get(pid, 0.0) + n
                if sid in visible:
                    sales_alloc[sid] = sales_alloc.get(sid, 0.0) + n
        except Exception:
            self.db.rollback()
            # gagal baca alokasi → seluruh pembayaran fallback FIFO
            return {}, {}
        return sales_alloc, payment_alloc

    # ====================================================================
    # SUMMARY
    # ====================================================================
    def load_summary(self, ref_id):
        """Hitung ringkasan piutang."""
        sales_filter = self._get_filter_field("sales")
        receivable_filter = self._get_filter_field("receivable")

        total_all = (
            self.db.query(func.coalesce(func.sum(PengeluaranOffline.total), 0.0))
            .filter(sales_filter == ref_id)
            .filter(PengeluaranOffline.is_deleted == 0)
            .scalar()
        ) or 0.0
        self.total_tagihan_all = total_all  # simpan buat fallback

        receivable = (
            self.db.query(ClientReceivable)
            .filter(receivable_filter == ref_id)
            .first()
        )

        total_bayar = 0.0
        sisa = 0.0

        if receivable:
            total_bayar = max(0.0, receivable.nominal - receivable.sisa)
            sisa = receivable.sisa
        else:
            sisa = total_all

        self.lbl_total_tagihan.setText(f"Rp {total_all:,.0f}")
        self.lbl_total_bayar.setText(f"Rp {total_bayar:,.0f}")
        self.lbl_sisa.setText(f"Rp {max(0, sisa):,.0f}")

        if sisa <= 0:
            self.lbl_status.setText("LUNAS")
            self.lbl_status.setStyleSheet(
                "font-size: 14pt; font-weight: bold; color: #4CAF50;"
            )
            self.lbl_sisa.setStyleSheet(
                "font-size: 16pt; font-weight: bold; color: #4CAF50;"
            )
        else:
            self.lbl_status.setText("BELUM LUNAS")
            self.lbl_status.setStyleSheet(
                "font-size: 14pt; font-weight: bold; color: #F44336;"
            )
            self.lbl_sisa.setStyleSheet(
                "font-size: 16pt; font-weight: bold; color: #F44336;"
            )

    # ====================================================================
    # SELECTION — hanya hitung PENJUALAN yang dipilih
    # ====================================================================
    def on_row_selected(self):
        """Saat baris dipilih — hanya hitung penjualan untuk cetak invoice."""
        if not self.selected_client_id:
            self._disable_actions()
            return

        selected_rows = set()
        for item in self.table.selectedItems():
            selected_rows.add(item.row())

        self.selected_sales = []
        self.total_tagihan = 0.0
        has_payment = False

        for row in sorted(selected_rows):  # urut baris tabel = urut tanggal
            jenis_item = self.table.item(row, 2)
            if not jenis_item:
                continue

            item0 = self.table.item(row, 0)
            meta = item0.data(Qt.ItemDataRole.UserRole) if item0 else None
            meta = meta if isinstance(meta, dict) else {}
            row_id = str(meta.get("id") or (item0.text() if item0 else ""))

            # Deteksi baris pembayaran (untuk tombol hapus)
            if row_id.startswith("P"):
                has_payment = True
                continue

            nominal = float(meta.get("debit") or 0.0)
            if nominal > 0:
                self.selected_sales.append(row)
                self.total_tagihan += nominal

        # Update label total tagihan sesuai baris yang dipilih
        if self.selected_sales:
            self.lbl_total_tagihan.setText(
                f"Rp {self.total_tagihan:,.0f}  (dari {len(self.selected_sales)} transaksi)"
            )
        else:
            self.lbl_total_tagihan.setText(f"Rp {getattr(self, 'total_tagihan_all', 0):,.0f}")

        self.btn_print.setEnabled(bool(self.selected_sales))
        self.btn_hapus_payment.setEnabled(has_payment)

    def _disable_actions(self):
        self.selected_sales = []
        self.total_tagihan = 0.0
        self.btn_print.setEnabled(False)
        self.btn_hapus_payment.setEnabled(False)
        self.ent_deposit.setText("0")
        self.ent_diskon.setText("0")

    def reset_all(self):
        """Reset saat tidak ada klien dipilih."""
        self.selected_client_id = None
        self.selected_sales = []
        self.total_tagihan = 0.0
        self.total_tagihan_all = 0
        self.table.setRowCount(0)
        self.lbl_total_tagihan.setText("Rp 0")
        self.lbl_total_bayar.setText("Rp 0")
        self.lbl_sisa.setText("Rp 0")
        self.lbl_status.setText("-")
        self.lbl_status.setStyleSheet("font-size: 14pt; font-weight: bold; color: #9E9E9E;")
        self.lbl_sisa.setStyleSheet("font-size: 16pt; font-weight: bold; color: #F44336;")
        self.btn_print.setEnabled(False)
        self.btn_hapus_payment.setEnabled(False)
        self.ent_deposit.setText("0")
        self.ent_diskon.setText("0")
        self.date_jatuh_tempo.setDate(QDate.currentDate().addDays(30))

    # ====================================================================
    # CLEAN RUPIAH
    # ====================================================================
    def clean_rupiah(self, val):
        if not val:
            return 0.0
        try:
            bersih = str(val).upper().replace("RP", "").replace(".", "").replace(",", "").replace(" ", "").strip()
            return float(bersih or 0)
        except Exception:
            return 0.0

    def _recalculate_receivable(self, ref_id):
        """Hitung ulang ClientReceivable dari total penjualan & pembayaran nyata."""
        sales_filter = self._get_filter_field("sales")
        receivable_filter = self._get_filter_field("receivable")

        try:
            total_tagihan = (
                self.db.query(func.coalesce(func.sum(PengeluaranOffline.total), 0.0))
                .filter(sales_filter == ref_id)
                .filter(PengeluaranOffline.is_deleted == 0)
                .scalar()
            ) or 0.0

            receivable = (
                self.db.query(ClientReceivable)
                .filter(receivable_filter == ref_id)
                .first()
            )

            total_bayar = 0.0
            if receivable:
                total_bayar = (
                    self.db.query(func.coalesce(func.sum(ClientReceivablePayment.nominal_bayar), 0.0))
                    .filter(ClientReceivablePayment.receivable_id == receivable.id)
                    .scalar()
                ) or 0.0

            sisa_baru = max(0.0, total_tagihan - total_bayar)

            if receivable:
                receivable.nominal = total_tagihan
                receivable.sisa = sisa_baru
                receivable.status = 'LUNAS' if sisa_baru <= 0 else 'OPEN'
            else:
                if total_tagihan > 0:
                    kwargs = {
                        'nominal': total_tagihan,
                        'sisa': sisa_baru,
                        'status': 'OPEN' if sisa_baru > 0 else 'LUNAS',
                    }
                    if self.selected_client_type == "client":
                        kwargs['client_id'] = ref_id
                    else:
                        kwargs['person_id'] = ref_id
                    receivable = ClientReceivable(**kwargs)
                    self.db.add(receivable)

            self.db.commit()
            return receivable

        except Exception:
            self.db.rollback()
            raise  # Biarkan caller (load_client_data) yang handle dan tampilkan pesan

    # ====================================================================
    # SAVE DEPOSIT + PRINT INVOICE PDF
    # ====================================================================
    def _save_and_print(self):
        """Simpan deposit ke database, lalu cetak invoice PDF."""
        if not self.selected_client_id or not self.selected_sales:
            return

        deposit = self.clean_rupiah(self.ent_deposit.text())
        if deposit < 0:
            QMessageBox.warning(self, "Error", "Deposit tidak boleh minus!")
            return

        tanggal = self.date_deposit.date().toString("yyyy-MM-dd")
        metode = self.cb_metode.currentText()

        # Konfirmasi: simpan deposit atau hanya cetak ulang?
        simpan_deposit = False
        if deposit > 0:
            reply = QMessageBox.question(
                self, "Konfirmasi Deposit",
                f"Simpan deposit Rp {deposit:,.0f} ke database?\n\n"
                f"Pilih YA jika ini pembayaran baru dari klien.\n"
                f"Pilih TIDAK jika hanya cetak ulang (deposit tidak disimpan).",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes,
            )
            simpan_deposit = (reply == QMessageBox.StandardButton.Yes)

        try:
            receivable_filter = self._get_filter_field("receivable")

            # --- SNAPSHOT baris penjualan terpilih SEBELUM refresh ---
            # (notifier bisa memicu reload yang mengosongkan seleksi di tengah proses)
            selected_meta = []
            for row in self.selected_sales:
                item0 = self.table.item(row, 0)
                meta = item0.data(Qt.ItemDataRole.UserRole) if item0 else None
                if isinstance(meta, dict) and str(meta.get("id") or "").startswith("S"):
                    selected_meta.append(meta)

            # --- HITUNG SISA PIUTANG KLIEN SAAT INI dari database ---
            receivable = (
                self.db.query(ClientReceivable)
                .filter(receivable_filter == self.selected_client_id)
                .first()
            )
            sisa_piutang = receivable.sisa if receivable else 0.0

            # --- SIMPAN DEPOSIT (jika dikonfirmasi) via recalculate ---
            if simpan_deposit:
                receivable = (
                    self.db.query(ClientReceivable)
                    .filter(receivable_filter == self.selected_client_id)
                    .first()
                )

                if not receivable:
                    # Buat receivable dulu baru bisa tambah payment
                    sales_filter = self._get_filter_field("sales")
                    total_tagihan = (
                        self.db.query(func.coalesce(func.sum(PengeluaranOffline.total), 0.0))
                        .filter(sales_filter == self.selected_client_id)
                        .filter(PengeluaranOffline.is_deleted == 0)
                        .scalar()
                    ) or 0.0
                    kwargs = {
                        'nominal': total_tagihan,
                        'sisa': total_tagihan,
                        'status': 'OPEN',
                    }
                    if self.selected_client_type == "client":
                        kwargs['client_id'] = self.selected_client_id
                    else:
                        kwargs['person_id'] = self.selected_client_id
                    receivable = ClientReceivable(**kwargs)
                    self.db.add(receivable)
                    self.db.flush()

                payment = ClientReceivablePayment(
                    receivable_id=receivable.id,
                    tanggal_bayar=tanggal,
                    nominal_bayar=deposit,
                    metode=metode,
                )
                self.db.add(payment)
                self.db.flush()  # butuh payment.id untuk alokasi

                # --- ALOKASI deposit ke transaksi yang DIPILIH user ---
                # (urut tanggal; cap per transaksi = SISA tagihannya agar
                #  transaksi yang sudah PARTIAL tidak ter-alokasi berlebih.
                #  Kelebihan deposit tidak dialokasikan → otomatis di-FIFO-kan
                #  ke transaksi terlama yang belum lunas saat ditampilkan)
                selected_sids = []
                for meta in selected_meta:
                    try:
                        selected_sids.append(int(str(meta["id"])[1:]))
                    except (ValueError, TypeError, KeyError):
                        continue

                existing_alloc = dict(
                    self.db.query(
                        PaymentAllocation.sales_id,
                        func.coalesce(func.sum(PaymentAllocation.nominal), 0.0),
                    )
                    .filter(PaymentAllocation.sales_id.in_(selected_sids))
                    .group_by(PaymentAllocation.sales_id)
                    .all()
                ) if selected_sids else {}

                sisa_deposit = float(deposit)
                for meta in selected_meta:
                    if sisa_deposit <= 0.005:
                        break
                    try:
                        sid = int(str(meta["id"])[1:])
                    except (ValueError, TypeError, KeyError):
                        continue
                    tagihan = float(meta.get("debit") or 0.0)
                    sisa_tagihan = max(0.0, tagihan - existing_alloc.get(sid, 0.0))
                    dialokasikan = min(sisa_deposit, sisa_tagihan)
                    if dialokasikan <= 0.005:
                        continue
                    self.db.add(PaymentAllocation(
                        payment_id=payment.id,
                        sales_id=sid,
                        nominal=dialokasikan,
                    ))
                    sisa_deposit -= dialokasikan

                # Recalculate dari data nyata (self-healing)
                self._recalculate_receivable(self.selected_client_id)

                if self.notifier:
                    self.notifier.database_changed.emit()

            # --- SISA PIUTANG TERKINI untuk PDF (deposit sudah diperhitungkan) ---
            if simpan_deposit:
                self.db.expire_all()
                receivable = (
                    self.db.query(ClientReceivable)
                    .filter(receivable_filter == self.selected_client_id)
                    .first()
                )
                sisa_piutang = receivable.sisa if receivable else 0.0

            # --- QUERY SALES DATA UNTUK PDF (dari snapshot seleksi) ---
            selected_ids = []
            for meta in selected_meta:
                try:
                    selected_ids.append(int(str(meta.get("id"))[1:]))
                except (ValueError, TypeError):
                    continue

            sales_data = []
            if selected_ids:
                sales_data = (
                    self.db.query(PengeluaranOffline)
                    .filter(PengeluaranOffline.id.in_(selected_ids))
                    .order_by(PengeluaranOffline.tanggal, PengeluaranOffline.id)
                    .all()
                )

            if not sales_data:
                QMessageBox.warning(self, "Error", "Tidak ada data penjualan untuk dicetak.")
                return

            # --- Ambil data klien (nama, alamat, telp) untuk PDF ---
            nama_klien = "Unknown"
            alamat_klien = None
            telp_klien = None

            if self.selected_client_type == "client":
                client = self.db.query(Client).get(self.selected_client_id)
                if client:
                    nama_klien = client.nama
                    alamat_klien = client.alamat
                    telp_klien = client.no_hp
            else:
                # Fallback ke Person (legacy)
                person = self.db.query(Person).get(self.selected_client_id)
                if person:
                    nama_klien = person.nama
                    alamat_klien = person.alamat
                    telp_klien = person.no_hp

            diskon = self.clean_rupiah(self.ent_diskon.text())
            if diskon < 0:
                QMessageBox.warning(self, "Error", "Diskon tidak boleh minus!")
                return
            tgl_jatuh_tempo = self.date_jatuh_tempo.date().toString("dd/MM/yyyy")

            # --- CETAK PDF via pdf_engine (dengan data klien lengkap) ---
            out_path = generate_invoice_pdf(
                sales_data=sales_data,
                nama_klien=nama_klien,
                total_tagihan=self.total_tagihan,
                sisa_piutang=sisa_piutang,
                deposit=deposit,
                tgl_deposit=tanggal,
                metode=metode,
                simpan_deposit=simpan_deposit,
                alamat_klien=alamat_klien,
                telp_klien=telp_klien,
                tgl_jatuh_tempo=tgl_jatuh_tempo,
                diskon=diskon,
            )

            os.startfile(out_path)
            self.table.clearSelection()

            # --- REFRESH ---
            self.load_client_data(self.selected_client_id)
            self.ent_deposit.setText("0")
            self.ent_diskon.setText("0")

            sisa_baru = max(0.0, sisa_piutang)  # sudah termasuk deposit baru (jika disimpan)
            if simpan_deposit:
                QMessageBox.information(
                    self, "Sukses",
                    f"Invoice berhasil dicetak!\n\n"
                    f"Deposit Rp {deposit:,.0f} tercatat.\n"
                    f"Sisa hutang baru: Rp {sisa_baru:,.0f}"
                )
            else:
                QMessageBox.information(
                    self, "Sukses",
                    "Invoice berhasil dicetak!"
                )

        except Exception as e:
            self.db.rollback()
            self.db.expire_all()
            CopyableErrorDialog(
                self, "Error",
                f"Gagal memproses invoice:\n\n{str(e)}\n\n--- FULL TRACEBACK ---\n{traceback.format_exc()}"
            ).exec()

    # ====================================================================
    # EXPORT EXCEL
    # ====================================================================
    def delete_selected_payment(self):
        """Hapus baris pembayaran (deposit) yang dipilih — undo accidental save."""
        if not self.selected_client_id:
            return

        selected_rows = set()
        for item in self.table.selectedItems():
            selected_rows.add(item.row())

        payment_ids = []
        for row in selected_rows:
            item0 = self.table.item(row, 0)
            meta = item0.data(Qt.ItemDataRole.UserRole) if item0 else None
            meta = meta if isinstance(meta, dict) else {}
            row_id = str(meta.get("id") or (item0.text() if item0 else ""))
            if row_id.startswith("P"):
                try:
                    payment_ids.append(int(row_id[1:]))
                except ValueError:
                    continue

        if not payment_ids:
            return

        reply = QMessageBox.question(
            self, "Konfirmasi Hapus",
            f"Hapus {len(payment_ids)} riwayat pembayaran?\n\n"
            f"Data deposit akan dihapus permanen dan sisa piutang "
            f"akan dikembalikan ke nilai sebelumnya.\n\n"
            f"Yakin ingin melanjutkan?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        try:
            for pid in payment_ids:
                payment = self.db.query(ClientReceivablePayment).get(pid)
                if payment:
                    self.db.delete(payment)

            # Recalculate dari data nyata (self-healing)
            self._recalculate_receivable(self.selected_client_id)

            if self.notifier:
                self.notifier.database_changed.emit()

            self.load_client_data(self.selected_client_id)
            QMessageBox.information(
                self, "Sukses",
                f"{len(payment_ids)} pembayaran berhasil dihapus.\n"
                f"Sisa piutang sudah diperbarui."
            )

        except Exception as e:
            self.db.rollback()
            self.db.expire_all()
            CopyableErrorDialog(
                self, "Error",
                f"Gagal menghapus pembayaran:\n\n{str(e)}\n\n--- FULL TRACEBACK ---\n{traceback.format_exc()}"
            ).exec()

    # ====================================================================
    # CLOSE
    # ====================================================================
    def closeEvent(self, event):
        self.db.close()
        super().closeEvent(event)
