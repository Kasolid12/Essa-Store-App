# app_essa/ui/views/invoice_view.py
import os
import datetime
import traceback
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QTableWidgetItem, QHeaderView, QMessageBox, QAbstractItemView,
    QGridLayout, QLineEdit, QGroupBox, QFileDialog
)
from PySide6.QtCore import Qt

from ui.components.tables import CyberTable
from ui.components.buttons import CyberButton
from ui.theme import Theme
from data.database import SessionLocal
from data.models import PengeluaranOffline

class InvoiceView(QWidget):
    def __init__(self):
        super().__init__()
        self.db = SessionLocal()
        self.selected_sales = []
        self.total_tagihan = 0.0
        
        self.setup_ui()
        self.load_sales_data()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # --- Page Header ---
        header_layout = QHBoxLayout()
        title = QLabel("INVOICE & PELUNASAN MULTI-TRANSAKSI")
        title.setStyleSheet(f"font-size: 24pt; font-weight: bold; color: {Theme.NEON_CYAN};")
        header_layout.addWidget(title)
        header_layout.addStretch()
        
        btn_refresh = CyberButton("🔄 REFRESH DATA")
        btn_refresh.clicked.connect(self.load_sales_data)
        header_layout.addWidget(btn_refresh)
        layout.addLayout(header_layout)

        # --- Data Table ---
        self.table = CyberTable()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "ID Penjualan", "Tanggal", "Nama Pembeli", "Kode SKU", 
            "Qty", "Harga Satuan", "Total Transaksi"
        ])
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        
        # MENGAKTIFKAN MULTI-SELECTION
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.itemSelectionChanged.connect(self.on_row_selected)
        layout.addWidget(self.table)

        # --- PANEL KALKULASI & PEMBAYARAN ---
        pay_group = QGroupBox("KALKULASI & PELUNASAN (DRAFT INVOICE)")
        pay_group.setStyleSheet(f"""
            QGroupBox {{ color: {Theme.NEON_YELLOW}; font-weight: bold; border: 1px solid #2d2d38; padding: 15px; margin-top: 10px; }}
        """)
        pay_lay = QGridLayout(pay_group)

        # Kolom Kiri
        pay_lay.addWidget(QLabel("Klien Terpilih:"), 0, 0)
        self.lbl_klien = QLabel("-")
        self.lbl_klien.setStyleSheet("font-size: 14pt; font-weight: bold; color: white;")
        pay_lay.addWidget(self.lbl_klien, 0, 1)

        pay_lay.addWidget(QLabel("Total Tagihan Terpilih:"), 1, 0)
        self.lbl_total = QLabel("Rp 0")
        self.lbl_total.setStyleSheet(f"font-size: 16pt; font-weight: bold; color: {Theme.NEON_PINK};")
        pay_lay.addWidget(self.lbl_total, 1, 1)

        # Kolom Tengah (Pembayaran)
        pay_lay.addWidget(QLabel("DIBAYAR SAAT INI (Rp):"), 0, 2, alignment=Qt.AlignmentFlag.AlignRight)
        self.ent_dibayar = QLineEdit("0")
        self.ent_dibayar.setStyleSheet(f"font-size: 14pt; font-weight: bold; background: {Theme.BG_VOID}; color: {Theme.TEXT_MAIN};")
        self.ent_dibayar.textChanged.connect(self.kalkulasi_sisa)
        pay_lay.addWidget(self.ent_dibayar, 0, 3)

        pay_lay.addWidget(QLabel("SISA HUTANG BARU:"), 1, 2, alignment=Qt.AlignmentFlag.AlignRight)
        self.lbl_sisa = QLabel("Rp 0")
        self.lbl_sisa.setStyleSheet("font-size: 16pt; font-weight: bold; color: #4CAF50;")
        pay_lay.addWidget(self.lbl_sisa, 1, 3)

        # Kolom Kanan (Tombol Aksi)
        self.btn_print = CyberButton("🖨️ CETAK INVOICE PDF")
        self.btn_print.setStyleSheet(f"background-color: {Theme.NEON_CYAN}; color: black; font-weight: bold; font-size: 11pt; padding: 10px;")
        self.btn_print.setEnabled(False)
        self.btn_print.clicked.connect(self.print_multi_invoice)
        pay_lay.addWidget(self.btn_print, 0, 4, 2, 1)

        self.btn_export = CyberButton("📊 EXPORT EXCEL")
        self.btn_export.setStyleSheet(f"background-color: #FFC107; color: black; font-weight: bold; font-size: 11pt; padding: 10px;")
        self.btn_export.setEnabled(False)
        self.btn_export.clicked.connect(self.export_to_excel)
        pay_lay.addWidget(self.btn_export, 0, 5, 2, 1)

        layout.addWidget(pay_group)

    def load_sales_data(self):
        self.table.setRowCount(0)
        sales = self.db.query(PengeluaranOffline).filter(PengeluaranOffline.person_id != None).order_by(PengeluaranOffline.tanggal.desc(), PengeluaranOffline.id.desc()).limit(150).all()
        
        self.table.setRowCount(len(sales))
        for row, sale in enumerate(sales):
            self.table.setItem(row, 0, QTableWidgetItem(str(sale.id)))
            self.table.setItem(row, 1, QTableWidgetItem(sale.tanggal))
            self.table.setItem(row, 2, QTableWidgetItem(sale.person.nama if sale.person else "Unknown"))
            
            # --- PERBAIKAN: Menampilkan KODE SKU di UI Tabel ---
            self.table.setItem(row, 3, QTableWidgetItem(sale.sku.kode_sku if sale.sku else "Unknown"))
            # ---------------------------------------------------
            
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
        selected_rows = list(set([item.row() for item in self.table.selectedItems()]))
        
        if not selected_rows:
            self.reset_panel()
            return

        nama_klien_pertama = self.table.item(selected_rows[0], 2).text()
        
        for row in selected_rows:
            nama_cek = self.table.item(row, 2).text()
            if nama_cek != nama_klien_pertama:
                QMessageBox.warning(self, "Pilihan Tidak Valid", "Anda hanya bisa memilih banyak transaksi untuk 1 Klien yang sama!")
                self.table.clearSelection()
                self.reset_panel()
                return

        self.selected_sales = []
        self.total_tagihan = 0.0
        
        for row in selected_rows:
            sale_id = int(self.table.item(row, 0).text())
            total_str = self.table.item(row, 6).text().replace("Rp ", "").replace(",", "")
            self.selected_sales.append(sale_id)
            self.total_tagihan += float(total_str)

        self.lbl_klien.setText(nama_klien_pertama)
        self.lbl_total.setText(f"Rp {self.total_tagihan:,.0f}")
        self.btn_print.setEnabled(True)
        self.btn_export.setEnabled(True)
        self.kalkulasi_sisa()

    def clean_rupiah(self, val):
        if not val: return 0.0
        try:
            bersih = str(val).upper().replace("RP", "").replace(".", "").replace(",", "").replace(" ", "").strip()
            return float(bersih or 0)
        except: 
            return 0.0

    def kalkulasi_sisa(self):
        dibayar = self.clean_rupiah(self.ent_dibayar.text())
        sisa = self.total_tagihan - dibayar
        self.lbl_sisa.setText(f"Rp {max(0, sisa):,.0f}")
        if sisa <= 0:
            self.lbl_sisa.setStyleSheet("font-size: 16pt; font-weight: bold; color: #4CAF50;")
        else:
            self.lbl_sisa.setStyleSheet("font-size: 16pt; font-weight: bold; color: #F44336;")

    def reset_panel(self):
        self.selected_sales = []
        self.total_tagihan = 0.0
        self.lbl_klien.setText("-")
        self.lbl_total.setText("Rp 0")
        self.lbl_sisa.setText("Rp 0")
        self.ent_dibayar.setText("0")
        self.btn_print.setEnabled(False)
        self.btn_export.setEnabled(False)

    # ==========================================
    # LOGIKA EXPORT EXCEL
    # ==========================================
    def export_to_excel(self):
        if not self.selected_sales: return
        
        try:
            import pandas as pd
            
            sales_data = self.db.query(PengeluaranOffline).filter(PengeluaranOffline.id.in_(self.selected_sales)).all()
            if not sales_data: return
            
            data_export = []
            for item in sales_data:
                data_export.append({
                    "id": item.id,
                    "tanggal": item.tanggal,
                    "person_id": item.person_id,
                    "nama_klien": item.person.nama if item.person else "-",
                    "sku_id": item.sku_id,
                    # --- PERBAIKAN: Menuliskan KODE SKU di Excel ---
                    "kode_sku": item.sku.kode_sku if item.sku else "-",
                    # -----------------------------------------------
                    "qty": item.qty,
                    "harga_satuan": item.harga_satuan,
                    "total": item.total
                })
                
            df = pd.DataFrame(data_export)
            
            nama_klien = self.lbl_klien.text().replace(" ", "_")
            tgl_sekarang = datetime.datetime.now().strftime("%Y%m%d")
            default_name = f"Export_Pelunasan_{nama_klien}_{tgl_sekarang}.xlsx"
            
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Simpan Export Excel", default_name, "Excel Files (*.xlsx)"
            )
            
            if file_path:
                df.to_excel(file_path, index=False)
                QMessageBox.information(self, "Sukses", f"Data berhasil diexport ke:\n{file_path}")
                self.table.clearSelection()
                self.reset_panel()
                
        except ImportError:
            QMessageBox.critical(self, "Error", "Library 'pandas' atau 'openpyxl' belum terinstal.")
        except Exception as e:
            QMessageBox.critical(self, "Error Export", f"Terjadi kesalahan saat menyimpan Excel:\n{str(e)}\n\n{traceback.format_exc()}")

    # ==========================================
    # LOGIKA CETAK PDF
    # ==========================================
    def print_multi_invoice(self):
        if not self.selected_sales: return
        
        try:
            from fpdf import FPDF
            
            sales_data = self.db.query(PengeluaranOffline).filter(PengeluaranOffline.id.in_(self.selected_sales)).all()
            if not sales_data: return
            
            nama_klien = self.lbl_klien.text()
            dibayar = self.clean_rupiah(self.ent_dibayar.text())
            sisa_akhir = self.total_tagihan - dibayar
            
            try:
                BASE_DIR = os.path.dirname(os.path.abspath(__file__))
                APP_DIR = os.path.dirname(os.path.dirname(BASE_DIR))
            except NameError:
                APP_DIR = os.getcwd()
                
            FOLDER = os.path.join(APP_DIR, "exports", "invoices")
            if not os.path.exists(FOLDER): os.makedirs(FOLDER)
            
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            no_inv = f"INV-MULTI-{timestamp}"
            tanggal = datetime.date.today().strftime("%d %B %Y")
            
            pdf = FPDF(); pdf.add_page()
            
            pdf.set_font("Arial", 'B', 26); pdf.set_text_color(33, 150, 243); pdf.cell(100, 10, "ESSA STORE", 0, 0, 'L')
            pdf.set_font("Arial", 'B', 24); pdf.set_text_color(60, 60, 60); pdf.cell(90, 10, "INVOICE", 0, 1, 'R')
            pdf.set_font("Arial", '', 10); pdf.set_text_color(100, 100, 100)
            pdf.cell(100, 5, "WA: 0895426950709 | 08888169421", 0, 0, 'L')
            pdf.cell(90, 5, f"No. Ref : {no_inv}", 0, 1, 'R')
            pdf.cell(100, 5, "Pendosawalan 16/06, Kec. Kalinyamatan, Jepara", 0, 0, 'L')
            pdf.cell(90, 5, f"Tanggal : {tanggal}", 0, 1, 'R'); pdf.ln(5)
            
            pdf.set_draw_color(33, 150, 243); pdf.set_line_width(0.6); pdf.line(10, pdf.get_y(), 200, pdf.get_y()); pdf.ln(8)
            
            pdf.set_font("Arial", 'B', 10); pdf.set_text_color(150, 150, 150); pdf.cell(0, 5, "TAGIHAN KEPADA:", 0, 1)
            pdf.set_font("Arial", 'B', 14); pdf.set_text_color(0, 0, 0); pdf.cell(0, 7, nama_klien, 0, 1); pdf.ln(6)
            
            pdf.set_fill_color(33, 150, 243); pdf.set_text_color(255, 255, 255); pdf.set_font("Arial", 'B', 10)
            pdf.cell(12, 9, "No", 1, 0, 'C', 1); pdf.cell(83, 9, "Deskripsi Barang", 1, 0, 'L', 1)
            pdf.cell(15, 9, "Qty", 1, 0, 'C', 1); pdf.cell(40, 9, "Harga Satuan", 1, 0, 'R', 1); pdf.cell(40, 9, "Total", 1, 1, 'R', 1)
            
            pdf.set_text_color(0, 0, 0); pdf.set_font("Arial", '', 10)
            for idx, item in enumerate(sales_data, 1):
                fill = 1 if idx % 2 == 0 else 0; pdf.set_fill_color(248, 248, 248)
                
                # --- PERBAIKAN: Menuliskan KODE SKU di PDF ---
                kode_produk = item.sku.kode_sku if item.sku else "Barang Offline"
                desc = f"[{item.tanggal}] {kode_produk}"[:42].encode('latin-1', 'replace').decode('latin-1')
                # ---------------------------------------------
                
                pdf.cell(12, 8, str(idx), 1, 0, 'C', fill); pdf.cell(83, 8, f" {desc}", 1, 0, 'L', fill)
                pdf.cell(15, 8, str(item.qty), 1, 0, 'C', fill); pdf.cell(40, 8, f"Rp {item.harga_satuan:,.0f}", 1, 0, 'R', fill)
                pdf.cell(40, 8, f"Rp {item.total:,.0f}", 1, 1, 'R', fill); pdf.ln(0)
            
            pdf.ln(8); pdf.set_font("Arial", '', 10)
            pdf.cell(100, 6, "", 0, 0); pdf.cell(45, 6, "Total Tagihan", 0, 0, 'R'); pdf.cell(45, 6, f"Rp {self.total_tagihan:,.0f}", 0, 1, 'R')
            pdf.cell(100, 6, "", 0, 0); pdf.cell(45, 6, "Dibayar Saat Ini", 0, 0, 'R')
            pdf.set_text_color(40, 167, 69); pdf.cell(45, 6, f"Rp {dibayar:,.0f}", 0, 1, 'R'); pdf.ln(2); pdf.set_text_color(0, 0, 0)
            
            pdf.set_fill_color(253, 236, 240); pdf.set_text_color(233, 30, 99); pdf.set_font("Arial", 'B', 12)
            pdf.cell(90, 10, "", 0, 0); pdf.cell(55, 10, "SISA HUTANG", 1, 0, 'R', 1); pdf.cell(45, 10, f"Rp {max(0, sisa_akhir):,.0f}", 1, 1, 'R', 1)
            
            pdf.set_y(-60); pdf.set_text_color(0, 0, 0); pdf.set_font("Arial", 'B', 10); pdf.cell(0, 6, "Instruksi Pembayaran:", 0, 1)
            pdf.set_font("Arial", '', 10); pdf.cell(0, 6, "Mohon lakukan transfer ke: Bank BRI No. Rek: 224001017473501 a/n ACHMAD FAIS SETIAWAN", 0, 1)
            pdf.ln(8); pdf.set_font("Arial", 'I', 10); pdf.set_text_color(150, 150, 150); pdf.cell(0, 5, "Terima kasih atas kepercayaan Anda.", 0, 1, 'C')

            out_path = os.path.join(FOLDER, f"{no_inv}_{nama_klien.replace(' ','_')}.pdf")
            pdf.output(out_path)
            
            os.startfile(out_path)
            self.table.clearSelection()
            self.reset_panel()
            
            QMessageBox.information(self, "Sukses", f"Invoice PDF berhasil dicetak dan disimpan di folder exports/invoices!")

        except Exception as e: 
            QMessageBox.critical(self, "Error PDF", f"Gagal mencetak: {str(e)}\n\nDetail:\n{traceback.format_exc()}")

    def closeEvent(self, event):
        self.db.close()
        super().closeEvent(event)