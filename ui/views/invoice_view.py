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
from ui.theme import Theme
from data.database import SessionLocal
from data.models import PengeluaranOffline, Person
from data.models.invoice import ClientReceivable, ClientReceivablePayment
from utils.pdf_engine import generate_invoice_pdf


class InvoiceView(QWidget):
    def __init__(self, notifier=None):
        super().__init__()
        self.db = SessionLocal()
        self.notifier = notifier
        self.selected_client_id = None
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

        # --- DEPOSIT + ACTION ROW ---
        deposit_row = QHBoxLayout()
        deposit_row.setSpacing(10)
        deposit_row.addWidget(QLabel("Deposit (Rp):"))
        self.ent_deposit = QLineEdit("0")
        self.ent_deposit.setStyleSheet(
            f"font-size: 14pt; font-weight: bold; background: {Theme.BG_VOID};"
            f" color: {Theme.TEXT_MAIN}; padding: 4px;"
        )
        self.ent_deposit.setMaximumWidth(150)
        deposit_row.addWidget(self.ent_deposit)

        deposit_row.addWidget(QLabel("Tgl:"))
        self.date_deposit = QDateEdit()
        self.date_deposit.setDate(QDate.currentDate())
        self.date_deposit.setCalendarPopup(True)
        self.date_deposit.setStyleSheet(
            f"background: {Theme.BG_VOID}; color: {Theme.TEXT_MAIN}; padding: 4px;"
        )
        deposit_row.addWidget(self.date_deposit)

        deposit_row.addWidget(QLabel("Metode:"))
        self.cb_metode = QComboBox()
        self.cb_metode.addItems(["TUNAI", "TRANSFER"])
        self.cb_metode.setStyleSheet(
            f"background: #15151a; color: {Theme.TEXT_MAIN}; padding: 4px;"
        )
        deposit_row.addWidget(self.cb_metode)

        deposit_row.addStretch()

        self.btn_print = CyberButton("CETAK INVOICE PDF")
        self.btn_print.setStyleSheet(
            f"background-color: {Theme.NEON_CYAN}; color: black;"
            f" font-weight: bold; font-size: 11pt; padding: 10px;"
        )
        self.btn_print.setEnabled(False)
        self.btn_print.clicked.connect(self._save_and_print)
        deposit_row.addWidget(self.btn_print)

        self.btn_hapus_payment = CyberButton("HAPUS PEMBAYARAN")
        self.btn_hapus_payment.setStyleSheet(
            f"background-color: {Theme.NEON_PINK}; color: white;"
            f" font-weight: bold; font-size: 11pt; padding: 10px;"
        )
        self.btn_hapus_payment.setEnabled(False)
        self.btn_hapus_payment.clicked.connect(self.delete_selected_payment)
        deposit_row.addWidget(self.btn_hapus_payment)

        bottom_lay.addLayout(deposit_row)
        layout.addWidget(bottom_frame)

    # ====================================================================
    # LOAD CLIENTS
    # ====================================================================
    def load_clients(self):
        """Muat daftar klien yang memiliki transaksi offline atau piutang."""
        prev_id = self.selected_client_id

        self.cb_client.blockSignals(True)
        self.cb_client.clear()
        self.cb_client.addItem("-- Pilih Klien --", None)

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

        all_ids = ids_from_sales | ids_from_cr
        persons = (
            self.db.query(Person)
            .filter(Person.id.in_(all_ids))
            .order_by(Person.nama)
            .all()
        ) if all_ids else []

        for p in persons:
            self.cb_client.addItem(p.nama, p.id)

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
        self.selected_client_id = self.cb_client.currentData()
        if not self.selected_client_id:
            self.reset_all()
            return
        self.load_client_data(self.selected_client_id)

    def load_client_data(self, person_id):
        """Muat kombinasi tabel + summary untuk satu klien."""
        self.selected_client_id = person_id
        # Self-healing: recalculate receivable dari data nyata setiap load
        self._recalculate_receivable(person_id)
        self.load_combined_table(person_id)
        self.load_summary(person_id)
        # Set deposit default, reset selection
        self.ent_deposit.setText("0")
        self.date_deposit.setDate(QDate.currentDate())
        self.selected_sales = []

    # ====================================================================
    # COMBINED TRANSACTION TABLE (penjualan + pembayaran)
    # ====================================================================
    def load_combined_table(self, person_id):
        """Satu tabel penjualan + pembayaran dengan running balance & status FIFO."""
        self.table.setRowCount(0)
        rows = self._get_combined_rows(person_id)
        if not rows:
            return

        # Komputasi status FIFO: pembayaran diterapkan ke penjualan terlama dulu
        # Antrian = list of {idx, sisa_belum_dibayar}
        fifo_queue = []

        for i, r in enumerate(rows):
            if r["jenis"] == "Penjualan":
                fifo_queue.append({"idx": i, "sisa": r["debit"]})
                r["status"] = "BELUM LUNAS"
            else:  # Pembayaran
                sisa_bayar = r["credit"]
                while sisa_bayar > 0 and fifo_queue:
                    oldest = fifo_queue[0]
                    if sisa_bayar >= oldest["sisa"]:
                        # Penjualan ini LUNAS
                        sisa_bayar -= oldest["sisa"]
                        rows[oldest["idx"]]["status"] = "LUNAS"
                        fifo_queue.pop(0)
                    else:
                        # Penjualan ini PARTIAL (dibayar sebagian)
                        oldest["sisa"] -= sisa_bayar
                        rows[oldest["idx"]]["status"] = "PARTIAL"
                        sisa_bayar = 0
                r["status"] = "LUNAS"

        # Populasi tabel
        running = 0.0
        self.table.setRowCount(len(rows))
        for i, r in enumerate(rows):
            running += r["debit"] - r["credit"]

            # Kolom 0: ID transaksi (internal)
            id_item = QTableWidgetItem(str(r.get("id", "")))
            id_item.setData(Qt.ItemDataRole.UserRole, r.get("id"))
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

    def _get_combined_rows(self, person_id):
        """Query + sort penjualan & pembayaran jadi list of dict."""
        rows = []

        # Penjualan offline
        sales = (
            self.db.query(PengeluaranOffline)
            .filter(PengeluaranOffline.person_id == person_id)
            .filter(PengeluaranOffline.is_deleted == 0)
            .order_by(PengeluaranOffline.tanggal, PengeluaranOffline.id)
            .all()
        )
        for s in sales:
            sku = s.sku.kode_sku if s.sku else "-"
            rows.append({
                "id": f"S{s.id}",
                "sort_key": (s.tanggal, 0, s.id),
                "tanggal": s.tanggal,
                "jenis": "Penjualan",
                "keterangan": f"{sku} x{s.qty}  |  {s.person.nama if s.person else ''}",
                "debit": float(s.total),
                "credit": 0.0,
            })

        # Pembayaran
        receivable = (
            self.db.query(ClientReceivable)
            .filter(ClientReceivable.person_id == person_id)
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

    # ====================================================================
    # SUMMARY
    # ====================================================================
    def load_summary(self, person_id):
        """Hitung ringkasan piutang."""
        total_all = (
            self.db.query(func.coalesce(func.sum(PengeluaranOffline.total), 0.0))
            .filter(PengeluaranOffline.person_id == person_id)
            .filter(PengeluaranOffline.is_deleted == 0)
            .scalar()
        ) or 0.0
        self.total_tagihan_all = total_all  # simpan buat fallback

        receivable = (
            self.db.query(ClientReceivable)
            .filter(ClientReceivable.person_id == person_id)
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

        for row in selected_rows:
            jenis_item = self.table.item(row, 2)
            if not jenis_item:
                continue

            row_id = self.table.item(row, 0).text() if self.table.item(row, 0) else ""

            # Deteksi baris pembayaran (untuk tombol hapus)
            if row_id.startswith("P"):
                has_payment = True
                continue

            debit_str = self.table.item(row, 3).text() if self.table.item(row, 3) else "0"
            debit_str = debit_str.replace("Rp ", "").replace(",", "").strip()
            try:
                nominal = float(debit_str) if debit_str != "-" else 0.0
            except ValueError:
                nominal = 0.0

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

    def _recalculate_receivable(self, person_id):
        """Hitung ulang ClientReceivable dari total penjualan & pembayaran nyata."""
        total_tagihan = (
            self.db.query(func.coalesce(func.sum(PengeluaranOffline.total), 0.0))
            .filter(PengeluaranOffline.person_id == person_id)
            .filter(PengeluaranOffline.is_deleted == 0)
            .scalar()
        ) or 0.0

        receivable = (
            self.db.query(ClientReceivable)
            .filter(ClientReceivable.person_id == person_id)
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
                receivable = ClientReceivable(
                    person_id=person_id,
                    nominal=total_tagihan,
                    sisa=sisa_baru,
                    status='OPEN' if sisa_baru > 0 else 'LUNAS',
                )
                self.db.add(receivable)

        self.db.commit()
        return receivable

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
            # --- HITUNG SISA PIUTANG KLIEN SAAT INI dari database ---
            receivable = (
                self.db.query(ClientReceivable)
                .filter(ClientReceivable.person_id == self.selected_client_id)
                .first()
            )
            sisa_piutang = receivable.sisa if receivable else 0.0
            # Sisa hutang sebelumnya = sisa_piutang - total transaksi baru
            sisa_sebelum = max(0.0, sisa_piutang - self.total_tagihan)

            # --- SIMPAN DEPOSIT (jika dikonfirmasi) via recalculate ---
            if simpan_deposit:
                receivable = (
                    self.db.query(ClientReceivable)
                    .filter(ClientReceivable.person_id == self.selected_client_id)
                    .first()
                )

                if not receivable:
                    # Buat receivable dulu baru bisa tambah payment
                    total_tagihan = (
                        self.db.query(func.coalesce(func.sum(PengeluaranOffline.total), 0.0))
                        .filter(PengeluaranOffline.person_id == self.selected_client_id)
                        .filter(PengeluaranOffline.is_deleted == 0)
                        .scalar()
                    ) or 0.0
                    receivable = ClientReceivable(
                        person_id=self.selected_client_id,
                        nominal=total_tagihan,
                        sisa=total_tagihan,
                        status='OPEN',
                    )
                    self.db.add(receivable)
                    self.db.flush()

                payment = ClientReceivablePayment(
                    receivable_id=receivable.id,
                    tanggal_bayar=tanggal,
                    nominal_bayar=deposit,
                    metode=metode,
                )
                self.db.add(payment)

                # Recalculate dari data nyata (self-healing)
                self._recalculate_receivable(self.selected_client_id)

                if self.notifier:
                    self.notifier.database_changed.emit()
            # else: tidak menyimpan deposit — langsung cetak

            # --- QUERY SALES DATA UNTUK PDF ---
            selected_ids = []
            for row in self.selected_sales:
                id_item = self.table.item(row, 0)
                if id_item and id_item.text().startswith("S"):
                    try:
                        selected_ids.append(int(id_item.text()[1:]))
                    except ValueError:
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

            nama_klien = sales_data[0].person.nama if sales_data[0].person else "Unknown"

            # --- CETAK PDF via pdf_engine ---
            out_path = generate_invoice_pdf(
                sales_data=sales_data,
                nama_klien=nama_klien,
                total_tagihan=self.total_tagihan,
                sisa_piutang=sisa_piutang,
                deposit=deposit,
                tgl_deposit=tanggal,
                metode=metode,
                simpan_deposit=simpan_deposit,
            )

            os.startfile(out_path)
            self.table.clearSelection()

            # --- REFRESH ---
            self.load_client_data(self.selected_client_id)
            self.ent_deposit.setText("0")

            sisa_baru = max(0.0, sisa_piutang - deposit)
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
            QMessageBox.critical(
                self, "Error",
                f"Gagal memproses invoice:\n{str(e)}\n\n{traceback.format_exc()}"
            )

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
            id_item = self.table.item(row, 0)
            if id_item and id_item.text().startswith("P"):
                try:
                    payment_ids.append(int(id_item.text()[1:]))
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
            QMessageBox.critical(
                self, "Error",
                f"Gagal menghapus pembayaran:\n{str(e)}\n\n{traceback.format_exc()}"
            )

    # ====================================================================
    # CLOSE
    # ====================================================================
    def closeEvent(self, event):
        self.db.close()
        super().closeEvent(event)
