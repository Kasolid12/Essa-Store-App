# app_essa/ui/views/profit_view.py
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, 
    QComboBox, QTableWidgetItem, QHeaderView, QGridLayout
)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QColor, QBrush, QFont

from ui.components.tables import CyberTable
from ui.theme import Theme
from data.database import SessionLocal
from data.models import SkuMaster
from data.models.debt import DebtEntry
from data.models.catatan_harian import HasilCutting, DistribusiCutting
from data.models.salary import MasterTarifPenjahit
from sqlalchemy import extract

class ProfitSimulationView(QWidget):
    def __init__(self):
        super().__init__()
        self.db = SessionLocal()
        
        # Biaya Overhead per Pcs (Berdasarkan Excel profit simulation v1.xlsx)
        self.BIAYA_PACKAGING = 100
        self.BIAYA_HANGTAG = 215
        self.BIAYA_WOVEN = 150
        self.BIAYA_TALI_HT = 20
        self.BIAYA_BENANG = 75
        self.TOTAL_AKSESORIS = self.BIAYA_HANGTAG + self.BIAYA_WOVEN + self.BIAYA_TALI_HT + self.BIAYA_BENANG

        self.setup_ui()
        self.load_filters()
        
        self.combo_tahun.currentIndexChanged.connect(self.load_data)
        self.combo_bulan.currentIndexChanged.connect(self.load_data)
        self.combo_status.currentIndexChanged.connect(self.load_data)
        
        self.load_data()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # --- HEADER ---
        title = QLabel("PROFIT SIMULATION DASHBOARD")
        title.setStyleSheet(f"font-size: 24pt; font-weight: bold; color: {Theme.NEON_CYAN};")
        layout.addWidget(title)

        # --- TOP PANEL: FILTER ---
        filter_frame = QFrame()
        filter_frame.setObjectName("GridPanel")
        filter_lay = QHBoxLayout(filter_frame)
        
        self.combo_tahun = QComboBox()
        self.combo_bulan = QComboBox()
        self.combo_status = QComboBox()
        self.combo_status.addItems(["Semua Status", "Hanya Kain Habis (FULL)", "Belum Habis (OPEN/PARTIAL)"])
        self.combo_status.setCurrentIndex(1) # Default cari yang sudah habis
        
        filter_lay.addWidget(QLabel("Tahun:")); filter_lay.addWidget(self.combo_tahun)
        filter_lay.addWidget(QLabel("Bulan:")); filter_lay.addWidget(self.combo_bulan)
        filter_lay.addWidget(QLabel("Status Kain:")); filter_lay.addWidget(self.combo_status)
        filter_lay.addStretch()
        layout.addWidget(filter_frame)

        # --- MAIN PANEL: TABEL KAIN (MODAL HUTANG) ---
        self.table_kain = CyberTable()
        self.table_kain.setColumnCount(5)
        self.table_kain.setHorizontalHeaderLabels(["Tanggal", "Jenis Kain", "Nominal Modal", "Status Cutting", "Status Distribusi"])
        self.table_kain.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table_kain.itemSelectionChanged.connect(self.calculate_profit)
        layout.addWidget(self.table_kain)

        # --- BOTTOM PANEL: SIMULASI PROFIT (PERBANDINGAN) ---
        profit_lay = QHBoxLayout()
        
        # Card 1: Gross Revenue
        self.card_gross = self.create_info_card("GROSS REVENUE (Estimasi)", "Rp 0", Theme.NEON_CYAN)
        profit_lay.addWidget(self.card_gross)
        
        # Card 2: Home Production (Penjahit)
        self.card_home = self.create_info_card("PROFIT: HOME PRODUCTION", "Rp 0", Theme.NEON_YELLOW)
        profit_lay.addWidget(self.card_home)
        
        # Card 3: Outsourced (Pengsup)
        self.card_pengsup = self.create_info_card("PROFIT: OUTSOURCED (PENGSUP)", "Rp 0", Theme.NEON_PINK)
        profit_lay.addWidget(self.card_pengsup)
        
        layout.addLayout(profit_lay)

    def create_info_card(self, title, value, color):
        card = QFrame()
        card.setObjectName("GridPanel")
        lay = QVBoxLayout(card)
        lbl_title = QLabel(title)
        lbl_title.setStyleSheet(f"color: {Theme.TEXT_MUTED}; font-size: 10pt; font-weight: bold;")
        lbl_val = QLabel(value)
        lbl_val.setStyleSheet(f"color: {color}; font-size: 18pt; font-weight: bold;")
        lay.addWidget(lbl_title); lay.addWidget(lbl_val)
        return card

    def load_filters(self):
        tahun_ini = QDate.currentDate().year()
        self.combo_tahun.addItems([str(y) for y in range(tahun_ini - 2, tahun_ini + 2)])
        self.combo_tahun.setCurrentText(str(tahun_ini))
        
        self.combo_bulan.addItem("-- Semua Bulan --", None)
        bulans = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"]
        for i, b in enumerate(bulans, 1):
            self.combo_bulan.addItem(b, f"{i:02d}")
        self.combo_bulan.setCurrentIndex(QDate.currentDate().month())

    def load_data(self):
        self.table_kain.setRowCount(0)
        
        tahun = self.combo_tahun.currentText()
        bulan = self.combo_bulan.currentData()
        status_filter = self.combo_status.currentIndex()
        
        query = self.db.query(DebtEntry).filter(DebtEntry.tipe_hutang == 'MODAL')
        if bulan:
            query = query.filter(DebtEntry.tanggal.like(f"{tahun}-{bulan}-%"))
        else:
            query = query.filter(DebtEntry.tanggal.like(f"{tahun}-%"))
            
        if status_filter == 1:
            query = query.filter(DebtEntry.status_cutting == 'FULL')
        elif status_filter == 2:
            query = query.filter(DebtEntry.status_cutting.in_(['OPEN', 'PARTIAL']))
            
        kain_list = query.order_by(DebtEntry.tanggal.desc()).all()
        
        self.table_kain.setRowCount(len(kain_list))
        for row, kain in enumerate(kain_list):
            self.table_kain.setItem(row, 0, QTableWidgetItem(kain.tanggal))
            
            # Simpan ID kain di kolom 1 agar mudah diambil saat di-klik
            item_kain = QTableWidgetItem(kain.keterangan)
            item_kain.setData(Qt.UserRole, kain.id)
            self.table_kain.setItem(row, 1, item_kain)
            
            self.table_kain.setItem(row, 2, QTableWidgetItem(f"Rp {kain.nominal_hutang:,.0f}"))
            
            # Warnai status cutting
            item_status = QTableWidgetItem(kain.status_cutting)
            if kain.status_cutting == 'FULL': item_status.setForeground(QBrush(QColor(Theme.NEON_CYAN)))
            else: item_status.setForeground(QBrush(QColor(Theme.NEON_YELLOW)))
            self.table_kain.setItem(row, 3, item_status)
            
            # Cek status distribusi secara dinamis
            total_potong = sum(c.qty for c in kain.hasil_cuttings)
            total_distribusi = 0
            for hc in kain.hasil_cuttings:
                total_distribusi += sum(d.qty for d in hc.distribusi)
                
            status_dist = "BELUM SELESAI"
            if total_potong > 0 and total_distribusi >= total_potong:
                status_dist = "FULLY DISTRIBUTED"
                
            item_dist = QTableWidgetItem(status_dist)
            if status_dist == "FULLY DISTRIBUTED": item_dist.setForeground(QBrush(QColor(Theme.NEON_CYAN)))
            else: item_dist.setForeground(QBrush(QColor(Theme.NEON_PINK)))
            self.table_kain.setItem(row, 4, item_dist)

    def calculate_profit(self):
        selected = self.table_kain.selectedItems()
        if not selected: return
        
        # Ambil ID Kain dari kolom ke-2 (index 1)
        kain_id = self.table_kain.item(selected[0].row(), 1).data(Qt.UserRole)
        kain = self.db.query(DebtEntry).get(kain_id)
        
        if not kain or not kain.hasil_cuttings:
            self.reset_cards()
            return
            
        total_revenue = 0
        total_qty_potong = 0
        
        # Hitung Gross Revenue dari Harga Jual Master SKU
        for hc in kain.hasil_cuttings:
            total_qty_potong += hc.qty
            if hc.sku:
                total_revenue += (hc.qty * hc.sku.harga_jual)
                
        gross_margin = total_revenue - kain.nominal_hutang
        
        self.card_gross.findChildren(QLabel)[1].setText(f"Rp {total_revenue:,.0f}")
        
        if total_qty_potong == 0:
            self.reset_cards()
            return
            
        # ==========================================
        # SIMULASI HOME PRODUCTION (PENJAHIT)
        # ==========================================
        # Estimasi biaya jahit (ambil rata-rata atau asumsikan JSO jika tidak spesifik)
        # Untuk presisi, idealnya kita cek tarif_id, tapi sebagai simulasi global:
        tarif_jahit_estimasi = 600 # Rp 600/pcs
        biaya_jahit_total = total_qty_potong * tarif_jahit_estimasi
        biaya_aksesoris_home = total_qty_potong * (self.TOTAL_AKSESORIS + self.BIAYA_PACKAGING)
        
        total_cost_home = biaya_jahit_total + biaya_aksesoris_home
        profit_home = gross_margin - total_cost_home
        
        self.card_home.findChildren(QLabel)[1].setText(f"Rp {profit_home:,.0f}\n({profit_home/total_qty_potong:,.0f} /pcs)")
        
        # ==========================================
        # SIMULASI OUTSOURCED (PENGSUP)
        # ==========================================
        tarif_pengsup_estimasi = 1500 # Contoh Rp 1500/pcs
        biaya_pengsup_total = total_qty_potong * tarif_pengsup_estimasi
        # Sesuai excel, pengsup tidak pakai packaging dari kita
        biaya_aksesoris_pengsup = total_qty_potong * self.TOTAL_AKSESORIS
        
        total_cost_pengsup = biaya_pengsup_total + biaya_aksesoris_pengsup
        profit_pengsup = gross_margin - total_cost_pengsup
        
        self.card_pengsup.findChildren(QLabel)[1].setText(f"Rp {profit_pengsup:,.0f}\n({profit_pengsup/total_qty_potong:,.0f} /pcs)")

    def reset_cards(self):
        self.card_gross.findChildren(QLabel)[1].setText("Rp 0")
        self.card_home.findChildren(QLabel)[1].setText("Rp 0")
        self.card_pengsup.findChildren(QLabel)[1].setText("Rp 0")