# app_essa/ui/views/stock_view.py
import os
import pandas as pd
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QTabWidget, QComboBox, QSpinBox, QDoubleSpinBox, QMessageBox, QFileDialog, QCompleter,
    QTableWidgetItem, QHeaderView, QDateEdit, QAbstractItemView
)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QColor, QBrush

from ui.components.tables import CyberTable
from ui.components.buttons import CyberButton
from ui.theme import Theme
from data.database import SessionLocal
from data.models import SkuMaster, PengeluaranOffline

class StockView(QWidget):
    def __init__(self, notifier=None):
        super().__init__()
        self.db = SessionLocal()
        self.notifier = notifier
        self.staging_data = [] # Holds data for Excel Export
        self.setup_ui()
        self.load_sku_dropdown()
        if self.notifier:
            self.notifier.database_changed.connect(self.refresh_harian_tables)

    def refresh_harian_tables(self):
        """Menyegarkan seluruh grid tabel catatan harian jika ada perubahan data di menu lain"""
        self.db.expire_all()
        if hasattr(self, 'load_sku_dropdown'): self.load_sku_dropdown()
        if hasattr(self, 'load_offline_list'): self.load_offline_list()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # --- Page Header ---
        header_layout = QHBoxLayout()
        title = QLabel("INVENTORY & BIGSELLER SYNC")
        title.setStyleSheet(f"font-size: 24pt; font-weight: bold; color: {Theme.NEON_CYAN};")
        header_layout.addWidget(title)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        # --- Tabs ---
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(f"""
            QTabBar::tab {{
                background: {Theme.BG_VOID}; color: {Theme.TEXT_MUTED};
                border: 1px solid {Theme.BORDER_DIM}; padding: 10px 20px; font-weight: bold;
            }}
            QTabBar::tab:selected {{
                background: {Theme.BG_PANEL}; color: {Theme.NEON_CYAN};
                border-bottom: 2px solid {Theme.NEON_CYAN};
            }}
            QTabWidget::pane {{ border: 1px solid {Theme.BORDER_DIM}; top: -1px; }}
        """)

        self.setup_tab_export()
        self.setup_tab_offline_reduction()

        self.tabs.addTab(self.tab_export, "STAGING & EXPORT (BIGSELLER)")
        self.tabs.addTab(self.tab_offline_reduction, "PENGURANGAN STOK (DARI OFFLINE)")
        
        layout.addWidget(self.tabs)

    # ==========================================
    # TAB: BIGSELLER EXPORT STAGING
    # ==========================================
    def setup_tab_export(self):
        self.tab_export = QWidget()
        lay = QVBoxLayout(self.tab_export)
        
        # --- INPUT FORM ---
        frame_input = QFrame()
        frame_input.setObjectName("GridPanel")
        lay_input = QHBoxLayout(frame_input)
        
        self.combo_sku = QComboBox()
        self.combo_sku.setEditable(True)
        self.combo_sku.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.combo_sku.setMinimumWidth(300)
        
        # Setup Completer for easy searching
        completer = self.combo_sku.completer()
        if completer:
            completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
            completer.setFilterMode(Qt.MatchFlag.MatchContains)
            completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
            
        self.spin_qty = QSpinBox()
        self.spin_qty.setRange(1, 99999)
        self.spin_qty.setPrefix("Qty: ")
        
        self.spin_harga = QDoubleSpinBox()
        self.spin_harga.setRange(0, 999999999)
        self.spin_harga.setPrefix("Rp ")
        self.spin_harga.setToolTip("Harga Satuan (Opsional)")
        
        btn_add = CyberButton("TAMBAHKAN KE STAGING")
        btn_add.clicked.connect(self.add_to_staging)
        
        lay_input.addWidget(QLabel("Pilih SKU:"))
        lay_input.addWidget(self.combo_sku, stretch=1)
        lay_input.addWidget(self.spin_qty)
        lay_input.addWidget(self.spin_harga)
        lay_input.addWidget(btn_add)
        
        lay.addWidget(frame_input)

        # --- STAGING TABLE ---
        self.table_staging = CyberTable()
        self.table_staging.setColumnCount(4)
        self.table_staging.setHorizontalHeaderLabels(["Kode SKU", "Jumlah", "Harga Satuan", "Status"])
        self.table_staging.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        lay.addWidget(self.table_staging)
        
        # --- EXPORT BUTTONS ---
        lay_btn = QHBoxLayout()
        btn_delete = CyberButton("HAPUS BARIS", is_danger=True)
        btn_delete.clicked.connect(self.delete_staging_row)
        
        # Cyberpunk Outlined Style -> Solid on Hover (CYAN)
        btn_export_in = CyberButton("EXPORT PENAMBAHAN (IN)")
        btn_export_in.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: 2px solid {Theme.NEON_CYAN};
                color: {Theme.NEON_CYAN};
                font-weight: bold;
                padding: 10px 20px;
            }}
            QPushButton:hover {{
                background-color: {Theme.NEON_CYAN};
                color: #000000;
            }}
        """)
        btn_export_in.clicked.connect(self.export_stock_in)
        
        # Cyberpunk Outlined Style -> Solid on Hover (YELLOW)
        btn_export_out = CyberButton("EXPORT PENGURANGAN (OUT)")
        btn_export_out.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: 2px solid {Theme.NEON_YELLOW};
                color: {Theme.NEON_YELLOW};
                font-weight: bold;
                padding: 10px 20px;
            }}
            QPushButton:hover {{
                background-color: {Theme.NEON_YELLOW};
                color: #000000;
            }}
        """)
        btn_export_out.clicked.connect(self.export_stock_out)
        
        # --- THE FIX: Actually add the buttons to the layout! ---
        lay_btn.addWidget(btn_delete)
        lay_btn.addStretch()
        lay_btn.addWidget(btn_export_in)
        lay_btn.addWidget(btn_export_out)
        
        lay.addLayout(lay_btn)

    # ==========================================
    # LOGIC: STAGING & EXPORT
    # ==========================================
    def load_sku_dropdown(self):
        self.combo_sku.clear()
        skus = self.db.query(SkuMaster).filter(SkuMaster.is_active == 1).order_by(SkuMaster.kode_sku).all()
        for s in skus:
            self.combo_sku.addItem(s.kode_sku, s.kode_sku)

    def add_to_staging(self):
        sku_code = self.combo_sku.currentData()
        if not sku_code:
            QMessageBox.warning(self, "Error", "Pilih SKU yang valid dari dropdown!")
            return
            
        qty = self.spin_qty.value()
        harga = self.spin_harga.value()
        
        self.staging_data.append({
            "SKU": sku_code, "GTIN": "", "Qty": qty, 
            "Price": harga if harga > 0 else "", "ProdDate": "", "ExpDate": ""
        })
        
        row = self.table_staging.rowCount()
        self.table_staging.insertRow(row)
        self.table_staging.setItem(row, 0, QTableWidgetItem(sku_code))
        item_qty = QTableWidgetItem(f"{qty:,}")
        item_qty.setTextAlignment(Qt.AlignCenter)
        self.table_staging.setItem(row, 1, item_qty)
        self.table_staging.setItem(row, 2, QTableWidgetItem(f"Rp {harga:,.0f}" if harga > 0 else "-"))
        
        status = QTableWidgetItem("Siap Export")
        status.setForeground(QBrush(QColor(Theme.NEON_CYAN)))
        self.table_staging.setItem(row, 3, status)
        
        self.spin_qty.setValue(1)
        self.spin_harga.setValue(0)

    def delete_staging_row(self):
        selected = self.table_staging.selectedItems()
        if not selected: return
        
        # Get unique rows
        rows = sorted(list(set([item.row() for item in selected])), reverse=True)
        for r in rows:
            self.staging_data.pop(r)
            self.table_staging.removeRow(r)

    def export_stock_in(self):
        if not self.staging_data:
            QMessageBox.warning(self, "Peringatan", "Daftar staging masih kosong!")
            return
            
        df_raw = pd.DataFrame(self.staging_data)
        df_export = df_raw.rename(columns={
            "SKU": "*Nomor SKU\n(SKU atau GTIN Wajib Diisi)",
            "GTIN": "*GTIN\n(SKU atau GTIN Wajib Diisi)",
            "Qty": "*Jumlah Penambahan Stok",
            "Price": "Harga Satuan",
            "ProdDate": "Tanggal Produksi",
            "ExpDate": "Tanggal Kedaluwarsa"
        })

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Simpan File Impor Penambahan Stok",
            f"Penambahan_Stok_{datetime.today().strftime('%Y%m%d')}.xlsx",
            "Excel Files (*.xlsx)"
        )

        if file_path:
            try:
                df_export.to_excel(file_path, index=False, engine='openpyxl')
                
                QMessageBox.information(self, "Sukses", f"File berhasil disimpan di:\n{file_path}")
                
                self.staging_data.clear()
                self.table_staging.setRowCount(0)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Gagal menyimpan file: {e}")

    def export_stock_out(self):
        if not self.staging_data:
            QMessageBox.warning(self, "Peringatan", "Daftar staging masih kosong!")
            return
            
        df_raw = pd.DataFrame(self.staging_data)
        df_export = df_raw[['SKU', 'Qty']].rename(columns={
            "SKU": "*Nomor SKU",
            "Qty": "*Jumlah Pengurangan Stok"
        })

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Simpan File Impor Pengurangan Stok",
            f"Pengurangan_Stok_{datetime.today().strftime('%Y%m%d')}.xlsx",
            "Excel Files (*.xlsx)"
        )

        if file_path:
            try:
                df_export.to_excel(file_path, index=False, engine='openpyxl')
                
                QMessageBox.information(self, "Sukses", f"File berhasil disimpan di:\n{file_path}")
                
                self.staging_data.clear()
                self.table_staging.setRowCount(0)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Gagal menyimpan file: {e}")

    # ==========================================
    # TAB: PENGURANGAN STOK DARI PENGELUARAN OFFLINE
    # ==========================================
    def setup_tab_offline_reduction(self):
        """Tab staging pengurangan stok yang bersumber dari transaksi PengeluaranOffline."""
        self.tab_offline_reduction = QWidget()
        lay = QVBoxLayout(self.tab_offline_reduction)

        # --- Filter periode tanggal transaksi ---
        frame_filter = QFrame()
        frame_filter.setObjectName("GridPanel")
        lay_filter = QHBoxLayout(frame_filter)

        self.off_date_from = QDateEdit(QDate.currentDate().addMonths(-1))
        self.off_date_from.setCalendarPopup(True)
        self.off_date_to = QDateEdit(QDate.currentDate())
        self.off_date_to.setCalendarPopup(True)

        btn_reload = CyberButton("MUAT ULANG")
        btn_reload.clicked.connect(self.load_offline_list)

        lay_filter.addWidget(QLabel("Dari Tanggal:"))
        lay_filter.addWidget(self.off_date_from)
        lay_filter.addWidget(QLabel("s/d"))
        lay_filter.addWidget(self.off_date_to)
        lay_filter.addWidget(btn_reload)
        lay_filter.addStretch()

        lay.addWidget(frame_filter)

        # --- Tabel daftar transaksi pengeluaran offline ---
        lay.addWidget(QLabel("Daftar Transaksi Pengeluaran Offline (centang baris yang ingin di-stage):"))
        self.table_offline = CyberTable()
        self.table_offline.setColumnCount(7)
        self.table_offline.setHorizontalHeaderLabels(["", "ID", "Tanggal", "Kode SKU", "Nama Produk", "Qty", "Total (Rp)"])
        self.table_offline.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_offline.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        lay.addWidget(self.table_offline)

        # --- Tombol aksi list ---
        lay_btn_list = QHBoxLayout()
        btn_stage_checked = CyberButton("STAGE BARIS TERPILIH →")
        btn_stage_checked.clicked.connect(self.stage_checked_offline)
        btn_stage_all = CyberButton("STAGE SEMUA")
        btn_stage_all.clicked.connect(self.stage_all_offline)
        lay_btn_list.addWidget(btn_stage_checked)
        lay_btn_list.addWidget(btn_stage_all)
        lay_btn_list.addStretch()
        lay.addLayout(lay_btn_list)

        # --- Tabel staging offline reduction ---
        lay.addWidget(QLabel("Staging Pengurangan Stok (dari Offline):"))
        self.table_offline_staging = CyberTable()
        self.table_offline_staging.setColumnCount(4)
        self.table_offline_staging.setHorizontalHeaderLabels(["Kode SKU", "Jumlah", "Harga Satuan", "Sumber (ID Transaksi)"])
        self.table_offline_staging.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        lay.addWidget(self.table_offline_staging)

        # --- Tombol export & hapus ---
        lay_btn = QHBoxLayout()
        btn_delete = CyberButton("HAPUS BARIS", is_danger=True)
        btn_delete.clicked.connect(self.delete_offline_staging_row)

        btn_export_off = CyberButton("EXPORT PENGURANGAN (OUT)")
        btn_export_off.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: 2px solid {Theme.NEON_YELLOW};
                color: {Theme.NEON_YELLOW};
                font-weight: bold;
                padding: 10px 20px;
            }}
            QPushButton:hover {{
                background-color: {Theme.NEON_YELLOW};
                color: #000000;
            }}
        """)
        btn_export_off.clicked.connect(self.export_offline_stock_out)

        lay_btn.addWidget(btn_delete)
        lay_btn.addStretch()
        lay_btn.addWidget(btn_export_off)
        lay.addLayout(lay_btn)

        self.offline_staging_data = []  # [{SKU, Qty, Price, ref_id}]
        self.load_offline_list()

    def load_offline_list(self):
        """Muat ulang daftar PengeluaranOffline sesuai rentang tanggal filter."""
        from_date = self.off_date_from.date().toString("yyyy-MM-dd")
        to_date = self.off_date_to.date().toString("yyyy-MM-dd")

        rows = (self.db.query(PengeluaranOffline)
                .filter(PengeluaranOffline.is_deleted == 0)
                .filter(PengeluaranOffline.tanggal >= from_date)
                .filter(PengeluaranOffline.tanggal <= to_date)
                .order_by(PengeluaranOffline.tanggal.desc(), PengeluaranOffline.id.desc())
                .all())

        self.table_offline.setRowCount(0)
        for r, rec in enumerate(rows):
            self.table_offline.insertRow(r)

            chk = QTableWidgetItem()
            chk.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            chk.setCheckState(Qt.CheckState.Unchecked)
            self.table_offline.setItem(r, 0, chk)

            self.table_offline.setItem(r, 1, QTableWidgetItem(str(rec.id)))
            self.table_offline.setItem(r, 2, QTableWidgetItem(str(rec.tanggal)))

            kode = str(rec.sku.kode_sku) if rec.sku else "-"
            nama = str(rec.sku.nama_produk) if rec.sku else "-"
            self.table_offline.setItem(r, 3, QTableWidgetItem(kode))
            self.table_offline.setItem(r, 4, QTableWidgetItem(nama))

            item_qty = QTableWidgetItem(f"{rec.qty:g}")
            item_qty.setTextAlignment(Qt.AlignCenter)
            self.table_offline.setItem(r, 5, item_qty)

            item_total = QTableWidgetItem(f"{rec.total:,.0f}")
            item_total.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table_offline.setItem(r, 6, item_total)

    def stage_checked_offline(self):
        """Stage semua baris yang dicentang pada daftar transaksi offline."""
        staged = 0
        for r in range(self.table_offline.rowCount()):
            chk = self.table_offline.item(r, 0)
            if chk and chk.checkState() == Qt.CheckState.Checked:
                self._stage_offline_row(r)
                staged += 1
        if staged:
            QMessageBox.information(self, "Sukses", f"{staged} transaksi offline masuk ke staging pengurangan stok.")
        else:
            QMessageBox.warning(self, "Peringatan", "Tidak ada baris yang dicentang!")

    def stage_all_offline(self):
        """Stage seluruh baris pada daftar transaksi offline (tanpa perlu centang)."""
        if self.table_offline.rowCount() == 0:
            QMessageBox.warning(self, "Peringatan", "Daftar transaksi kosong!")
            return
        for r in range(self.table_offline.rowCount()):
            self._stage_offline_row(r)
        QMessageBox.information(self, "Sukses", f"{self.table_offline.rowCount()} transaksi offline masuk ke staging pengurangan stok.")

    def _stage_offline_row(self, row_index):
        """Ambil satu baris dari tabel daftar offline dan tambahkan ke staging."""
        id_item = self.table_offline.item(row_index, 1)
        if not id_item:
            return
        rec_id = int(id_item.text())
        rec = self.db.query(PengeluaranOffline).get(rec_id)
        if not rec:
            return

        kode = str(rec.sku.kode_sku) if rec.sku else None
        if not kode:
            QMessageBox.warning(self, "Lewati", f"Transaksi #{rec_id} dilewati: SKU tidak ditemukan.")
            return

        qty = int(rec.qty) if float(rec.qty).is_integer() else rec.qty
        harga = rec.harga_satuan or 0

        self.offline_staging_data.append({
            "SKU": kode, "Qty": qty, "Price": harga, "ref_id": rec.id
        })

        row = self.table_offline_staging.rowCount()
        self.table_offline_staging.insertRow(row)
        self.table_offline_staging.setItem(row, 0, QTableWidgetItem(kode))
        item_qty = QTableWidgetItem(f"{qty:g}")
        item_qty.setTextAlignment(Qt.AlignCenter)
        self.table_offline_staging.setItem(row, 1, item_qty)
        self.table_offline_staging.setItem(row, 2, QTableWidgetItem(f"Rp {harga:,.0f}" if harga > 0 else "-"))
        self.table_offline_staging.setItem(row, 3, QTableWidgetItem(f"PengeluaranOffline#{rec.id}"))

    def delete_offline_staging_row(self):
        selected = self.table_offline_staging.selectedItems()
        if not selected:
            return
        rows = sorted(list(set([item.row() for item in selected])), reverse=True)
        for r in rows:
            self.offline_staging_data.pop(r)
            self.table_offline_staging.removeRow(r)

    def export_offline_stock_out(self):
        """Export staging pengurangan stok dari offline ke Excel format BigSeller (kolom SKU + Qty)."""
        if not self.offline_staging_data:
            QMessageBox.warning(self, "Peringatan", "Daftar staging masih kosong!")
            return

        df_raw = pd.DataFrame(self.offline_staging_data)
        df_export = df_raw[['SKU', 'Qty']].rename(columns={
            "SKU": "*Nomor SKU",
            "Qty": "*Jumlah Pengurangan Stok"
        })

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Simpan File Impor Pengurangan Stok (Offline)",
            f"Pengurangan_Stok_Offline_{datetime.today().strftime('%Y%m%d')}.xlsx",
            "Excel Files (*.xlsx)"
        )

        if file_path:
            try:
                df_export.to_excel(file_path, index=False, engine='openpyxl')
                QMessageBox.information(self, "Sukses", f"File berhasil disimpan di:\n{file_path}")
                self.offline_staging_data.clear()
                self.table_offline_staging.setRowCount(0)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Gagal menyimpan file: {e}")

    def closeEvent(self, event):
        self.db.close()
        super().closeEvent(event)