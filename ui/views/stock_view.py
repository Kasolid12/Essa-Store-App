# app_essa/ui/views/stock_view.py
import os
import pandas as pd
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, 
    QLineEdit, QTableWidgetItem, QHeaderView, QTabWidget,
    QComboBox, QSpinBox, QDoubleSpinBox, QMessageBox, QFileDialog, QCompleter
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QBrush, QFont
from sqlalchemy import func

from ui.components.tables import CyberTable
from ui.components.buttons import CyberButton
from ui.theme import Theme
from data.database import SessionLocal
from data.models import SkuMaster, HasilCutting, DistribusiCutting, PengeluaranOffline

class StockView(QWidget):
    def __init__(self):
        super().__init__()
        self.db = SessionLocal()
        self.staging_data = [] # Holds data for Excel Export
        self.setup_ui()
        self.load_stock_data()
        self.load_sku_dropdown()

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

        self.setup_tab_dashboard()
        self.setup_tab_export()

        self.tabs.addTab(self.tab_dashboard, "LIVE DASHBOARD")
        self.tabs.addTab(self.tab_export, "STAGING & EXPORT (BIGSELLER)")
        
        layout.addWidget(self.tabs)

    # ==========================================
    # TAB 1: LIVE DASHBOARD
    # ==========================================
    def setup_tab_dashboard(self):
        self.tab_dashboard = QWidget()
        layout = QVBoxLayout(self.tab_dashboard)
        
        # Search Bar
        top_lay = QHBoxLayout()
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Cari SKU atau Nama Produk...")
        self.search_bar.setFixedWidth(300)
        self.search_bar.textChanged.connect(self.filter_table)
        top_lay.addWidget(self.search_bar)
        
        btn_refresh = CyberButton("REFRESH DATA")
        btn_refresh.clicked.connect(self.load_stock_data)
        top_lay.addWidget(btn_refresh)
        top_lay.addStretch()
        layout.addLayout(top_lay)

        # Summary Widgets
        summary_layout = QHBoxLayout()
        self.lbl_tot_sku = self.create_summary_card("TOTAL SKU AKTIF", "0")
        self.lbl_tot_cut = self.create_summary_card("TOTAL PRODUKSI (CUTTING)", "0 Pcs", Theme.NEON_CYAN)
        self.lbl_tot_wip = self.create_summary_card("SEDANG DIJAHIT (WIP)", "0 Pcs", Theme.NEON_YELLOW)
        self.lbl_tot_out = self.create_summary_card("TERJUAL OFFLINE", "0 Pcs", Theme.NEON_PINK)
        
        summary_layout.addWidget(self.lbl_tot_sku)
        summary_layout.addWidget(self.lbl_tot_cut)
        summary_layout.addWidget(self.lbl_tot_wip)
        summary_layout.addWidget(self.lbl_tot_out)
        layout.addLayout(summary_layout)

        # Main Data Table
        self.table = CyberTable()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "Kode SKU", "Nama Produk", "Total Cutting (In)", 
            "Di Penjahit (WIP)", "Terjual Offline (Out)", "SISA ESTIMASI"
        ])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table)

    def create_summary_card(self, title, value, color=Theme.TEXT_MAIN):
        card = QFrame()
        card.setObjectName("GridPanel")
        lay = QVBoxLayout(card)
        
        lbl_title = QLabel(title)
        lbl_title.setStyleSheet(f"color: {Theme.TEXT_MUTED}; font-size: 10pt; font-weight: bold;")
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        lbl_val = QLabel(value)
        lbl_val.setStyleSheet(f"color: {color}; font-size: 20pt; font-weight: bold;")
        lbl_val.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        lay.addWidget(lbl_title)
        lay.addWidget(lbl_val)
        return card

    # ==========================================
    # TAB 2: BIGSELLER EXPORT STAGING
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
    # LOGIC: DASHBOARD
    # ==========================================
    def load_stock_data(self):
        self.table.setRowCount(0)
        skus = self.db.query(SkuMaster).filter(SkuMaster.is_active == 1).order_by(SkuMaster.kode_sku).all()
        global_cut, global_wip, global_out = 0, 0, 0
        
        self.table.setRowCount(len(skus))
        for row, sku in enumerate(skus):
            tot_cut = self.db.query(func.sum(HasilCutting.qty)).filter(HasilCutting.sku_id == sku.id).scalar() or 0
            tot_wip = self.db.query(func.sum(DistribusiCutting.qty)).filter(DistribusiCutting.sku_id == sku.id).scalar() or 0
            tot_out = self.db.query(func.sum(PengeluaranOffline.qty)).filter(PengeluaranOffline.sku_id == sku.id).scalar() or 0
            
            sisa_estimasi = tot_cut - tot_out
            global_cut += tot_cut; global_wip += tot_wip; global_out += tot_out

            self.table.setItem(row, 0, QTableWidgetItem(sku.kode_sku))
            self.table.setItem(row, 1, QTableWidgetItem(sku.nama_produk))
            self._set_number_item(self.table, row, 2, tot_cut)
            self._set_number_item(self.table, row, 3, tot_wip, Theme.NEON_YELLOW)
            self._set_number_item(self.table, row, 4, tot_out, Theme.NEON_PINK)
            
            item_sisa = QTableWidgetItem(f"{sisa_estimasi:,}")
            item_sisa.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_sisa.setForeground(QBrush(QColor(Theme.NEON_CYAN)))
            font = QFont(); font.setBold(True); item_sisa.setFont(font)
            self.table.setItem(row, 5, item_sisa)

        self.lbl_tot_sku.findChildren(QLabel)[1].setText(f"{len(skus):,}")
        self.lbl_tot_cut.findChildren(QLabel)[1].setText(f"{global_cut:,} Pcs")
        self.lbl_tot_wip.findChildren(QLabel)[1].setText(f"{global_wip:,} Pcs")
        self.lbl_tot_out.findChildren(QLabel)[1].setText(f"{global_out:,} Pcs")

    def filter_table(self, text):
        search_term = text.lower()
        for row in range(self.table.rowCount()):
            kode = self.table.item(row, 0).text().lower()
            nama = self.table.item(row, 1).text().lower()
            self.table.setRowHidden(row, not (search_term in kode or search_term in nama))

    def _set_number_item(self, table, row, col, val, color=None):
        item = QTableWidgetItem(f"{val:,}")
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        if color: item.setForeground(QBrush(QColor(color)))
        table.setItem(row, col, item)

    # ==========================================
    # LOGIC: STAGING & EXPORT
    # ==========================================
    def load_sku_dropdown(self):
        self.combo_sku.clear()
        skus = self.db.query(SkuMaster).filter(SkuMaster.is_active == 1).order_by(SkuMaster.kode_sku).all()
        for s in skus:
            self.combo_sku.addItem(f"[{s.kode_sku}] {s.nama_produk}", s.kode_sku)

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
        self._set_number_item(self.table_staging, row, 1, qty)
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

    def closeEvent(self, event):
        self.db.close()
        super().closeEvent(event)