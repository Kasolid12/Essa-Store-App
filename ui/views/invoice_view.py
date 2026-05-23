# app_essa/ui/views/invoice_view.py
import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QTableWidgetItem, QHeaderView, QMessageBox
)
from PySide6.QtCore import Qt

from ui.components.tables import CyberTable
from ui.components.buttons import CyberButton
from ui.theme import Theme
from data.database import SessionLocal
from data.models import PengeluaranOffline
from utils.pdf_engine import generate_invoice_pdf

class InvoiceView(QWidget):
    def __init__(self):
        super().__init__()
        self.db = SessionLocal()
        self.selected_sale_id = None
        self.setup_ui()
        self.load_sales_data()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # --- Page Header ---
        header_layout = QHBoxLayout()
        title = QLabel("INVOICE & PENJUALAN DASHBOARD")
        title.setStyleSheet(f"font-size: 24pt; font-weight: bold; color: {Theme.NEON_CYAN};")
        header_layout.addWidget(title)
        header_layout.addStretch()
        
        # Action Button
        self.btn_print = CyberButton("CETAK INVOICE TERPILIH")
        self.btn_print.setEnabled(False)
        self.btn_print.clicked.connect(self.print_selected_invoice)
        header_layout.addWidget(self.btn_print)
        
        layout.addLayout(header_layout)

        # --- Data Table ---
        self.table = CyberTable()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "ID Penjualan", "Tanggal", "Nama Pembeli", "SKU Produk", 
            "Qty", "Harga Satuan", "Total Transaksi"
        ])
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table.itemSelectionChanged.connect(self.on_row_selected)
        layout.addWidget(self.table)

    def load_sales_data(self):
        self.table.setRowCount(0)
        # Fetch the latest 100 offline sales
        sales = self.db.query(PengeluaranOffline).order_by(PengeluaranOffline.tanggal.desc(), PengeluaranOffline.id.desc()).limit(100).all()
        
        self.table.setRowCount(len(sales))
        for row, sale in enumerate(sales):
            self.table.setItem(row, 0, QTableWidgetItem(str(sale.id)))
            self.table.setItem(row, 1, QTableWidgetItem(sale.tanggal))
            self.table.setItem(row, 2, QTableWidgetItem(sale.person.nama if sale.person else "Unknown"))
            self.table.setItem(row, 3, QTableWidgetItem(sale.sku.nama_produk if sale.sku else "Unknown"))
            
            qty_item = QTableWidgetItem(f"{sale.qty:,}")
            qty_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 4, qty_item)
            
            harga_item = QTableWidgetItem(f"Rp {sale.harga_satuan:,.0f}")
            harga_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row, 5, harga_item)
            
            total_item = QTableWidgetItem(f"Rp {sale.total:,.0f}")
            total_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            total_item.setForeground(Qt.GlobalColor.green)
            self.table.setItem(row, 6, total_item)

    def on_row_selected(self):
        selected = self.table.selectedItems()
        if not selected:
            self.selected_sale_id = None
            self.btn_print.setEnabled(False)
            return
            
        self.selected_sale_id = int(self.table.item(selected[0].row(), 0).text())
        self.btn_print.setEnabled(True)

    def print_selected_invoice(self):
        if not self.selected_sale_id: return
        
        try:
            # Trigger the PDF Engine
            pdf_path = generate_invoice_pdf(self.selected_sale_id)
            
            # Auto-open the PDF
            os.startfile(pdf_path)
            
            self.table.clearSelection()
            self.btn_print.setEnabled(False)
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Gagal mencetak invoice: {e}")

    def closeEvent(self, event):
        self.db.close()
        super().closeEvent(event)