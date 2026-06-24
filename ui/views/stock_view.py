# app_essa/ui/views/stock_view.py
import os
import pandas as pd
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QTabWidget, QComboBox, QSpinBox, QDoubleSpinBox, QMessageBox, QFileDialog, QCompleter,
    QTableWidgetItem, QHeaderView
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QBrush

from ui.components.tables import CyberTable
from ui.components.buttons import CyberButton
from ui.theme import Theme
from data.database import SessionLocal
from data.models import SkuMaster

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

        self.tabs.addTab(self.tab_export, "STAGING & EXPORT (BIGSELLER)")
        
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

    def closeEvent(self, event):
        self.db.close()
        super().closeEvent(event)