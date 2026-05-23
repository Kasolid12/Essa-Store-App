# app_essa/ui/views/profit_view.py
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, 
    QComboBox, QTableWidgetItem, QHeaderView, QMessageBox
)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QColor, QBrush

from ui.components.tables import CyberTable
from ui.components.buttons import CyberButton
from ui.theme import Theme
from data.database import SessionLocal
from data.models.debt import DebtEntry

class ProfitSimulationView(QWidget):
    def __init__(self):
        super().__init__()
        self.db = SessionLocal()
        
        # Biaya Overhead per Pcs (Berdasarkan file profit simulation v1.xlsx)
        self.BIAYA_PACKAGING = 100
        self.BIAYA_HANGTAG = 215
        self.BIAYA_WOVEN = 150
        self.BIAYA_TALI_HT = 20
        self.BIAYA_BENANG = 75
        self.TOTAL_AKSESORIS = self.BIAYA_HANGTAG + self.BIAYA_WOVEN + self.BIAYA_TALI_HT + self.BIAYA_BENANG

        self.setup_ui()
        self.load_filters()
        
        # Hubungkan filter setelah UI selesai dibuat untuk mencegah error
        self.combo_tahun.currentIndexChanged.connect(self.load_data)
        self.combo_bulan.currentIndexChanged.connect(self.load_data)
        self.combo_status.currentIndexChanged.connect(self.load_data)
        
        self.load_data()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # --- HEADER ---
        title = QLabel("PROFIT SIMULATION & BATCH CONTROL")
        title.setStyleSheet(f"font-size: 24pt; font-weight: bold; color: {Theme.NEON_CYAN};")
        layout.addWidget(title)

        # --- TOP PANEL: FILTER ---
        filter_frame = QFrame()
        filter_frame.setObjectName("GridPanel")
        filter_lay = QHBoxLayout(filter_frame)
        
        self.combo_tahun = QComboBox()
        self.combo_bulan = QComboBox()
        self.combo_status = QComboBox()
        self.combo_status.addItems(["Semua Status", "Hanya Status (CLOSE)", "Hanya Status (OPEN)"])
        self.combo_status.setCurrentIndex(1) # Default mencari yang sudah CLOSE
        
        filter_lay.addWidget(QLabel("Tahun:")); filter_lay.addWidget(self.combo_tahun)
        filter_lay.addWidget(QLabel("Bulan:")); filter_lay.addWidget(self.combo_bulan)
        filter_lay.addWidget(QLabel("Status Kain:")); filter_lay.addWidget(self.combo_status)
        filter_lay.addStretch()
        layout.addWidget(filter_frame)

        # --- MAIN PANEL: TABEL KAIN (MODAL HUTANG) ---
        self.table_kain = CyberTable()
        self.table_kain.setColumnCount(6) # Ditambah 1 kolom untuk tombol Aksi
        self.table_kain.setHorizontalHeaderLabels([
            "Tanggal", "Jenis Kain", "Nominal Modal", "Status Cutting", "Status Distribusi", "Aksi Control"
        ])
        self.table_kain.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table_kain.itemSelectionChanged.connect(self.calculate_profit)
        layout.addWidget(self.table_kain)

        # --- BOTTOM PANEL: SIMULASI PROFIT (PERBANDINGAN) ---
        profit_lay = QHBoxLayout()
        
        # Card 1: Gross Revenue
        self.card_gross = self.create_info_card("GROSS REVENUE (Estimasi)", "-", Theme.NEON_CYAN)
        profit_lay.addWidget(self.card_gross)
        
        # Card 2: Home Production (Penjahit)
        self.card_home = self.create_info_card("PROFIT: HOME PRODUCTION", "-", Theme.NEON_YELLOW)
        profit_lay.addWidget(self.card_home)
        
        # Card 3: Outsourced (Pengsup)
        self.card_pengsup = self.create_info_card("PROFIT: OUTSOURCED (PENGSUP)", "-", Theme.NEON_PINK)
        profit_lay.addWidget(self.card_pengsup)
        
        layout.addLayout(profit_lay)

    def create_info_card(self, title, value, color):
        card = QFrame()
        card.setObjectName("GridPanel")
        lay = QVBoxLayout(card)
        lbl_title = QLabel(title)
        lbl_title.setStyleSheet(f"color: {Theme.TEXT_MUTED}; font-size: 10pt; font-weight: bold;")
        lbl_val = QLabel(value)
        lbl_val.setStyleSheet(f"color: {color}; font-size: 16pt; font-weight: bold;")
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
        self.reset_cards() # Reset panel bawah saat filter berubah
        
        tahun = self.combo_tahun.currentText()
        bulan = self.combo_bulan.currentData()
        status_filter = self.combo_status.currentIndex()
        
        query = self.db.query(DebtEntry).filter(DebtEntry.tipe_hutang == 'MODAL')
        if bulan:
            query = query.filter(DebtEntry.tanggal.like(f"{tahun}-{bulan}-%"))
        else:
            query = query.filter(DebtEntry.tanggal.like(f"{tahun}-%"))
            
        if status_filter == 1:
            query = query.filter(DebtEntry.status_cutting == 'CLOSE')
        elif status_filter == 2:
            query = query.filter(DebtEntry.status_cutting.in_(['OPEN', 'PARTIAL']))
            
        kain_list = query.order_by(DebtEntry.tanggal.desc()).all()
        
        self.table_kain.setRowCount(len(kain_list))
        for row, kain in enumerate(kain_list):
            self.table_kain.setItem(row, 0, QTableWidgetItem(kain.tanggal))
            
            # Simpan ID kain untuk logic onClick
            item_kain = QTableWidgetItem(kain.keterangan)
            item_kain.setData(Qt.UserRole, kain.id)
            self.table_kain.setItem(row, 1, item_kain)
            
            self.table_kain.setItem(row, 2, QTableWidgetItem(f"Rp {kain.nominal_hutang:,.0f}"))
            
            # Warnai status cutting
            item_status = QTableWidgetItem(kain.status_cutting)
            if kain.status_cutting == 'CLOSE': 
                item_status.setForeground(QBrush(QColor(Theme.NEON_CYAN)))
            else: 
                item_status.setForeground(QBrush(QColor(Theme.NEON_YELLOW)))
            self.table_kain.setItem(row, 3, item_status)
            
            # Cek status distribusi
            total_potong = sum(c.qty for c in kain.hasil_cuttings)
            total_distribusi = 0
            for hc in kain.hasil_cuttings:
                total_distribusi += sum(d.qty for d in hc.distribusi)
                
            # Logic Status Distribusi
            status_dist = "BELUM SELESAI"
            if total_potong > 0 and total_distribusi >= total_potong:
                status_dist = "FULLY DISTRIBUTED"
            elif total_potong == 0:
                status_dist = "BELUM ADA POTONGAN"
                
            item_dist = QTableWidgetItem(status_dist)
            if status_dist == "FULLY DISTRIBUTED": 
                item_dist.setForeground(QBrush(QColor(Theme.NEON_CYAN)))
            else: 
                item_dist.setForeground(QBrush(QColor(Theme.NEON_PINK)))
            self.table_kain.setItem(row, 4, item_dist)
            
            # --- TOMBOL INTERAKTIF (TOGGLE STATUS) ---
            if kain.status_cutting == 'CLOSE':
                btn_toggle = CyberButton("BUKA (OPEN)", is_danger=True)
                btn_toggle.setStyleSheet(f"background-color: transparent; color: {Theme.NEON_PINK}; border: 1px solid {Theme.NEON_PINK};")
            else:
                btn_toggle = CyberButton("TUTUP (CLOSE)")
                btn_toggle.setStyleSheet(f"background-color: {Theme.NEON_CYAN}; color: #000; font-weight: bold;")
                
            # Gunakan closure untuk mengikat kain.id ke tombol
            btn_toggle.clicked.connect(lambda checked=False, k_id=kain.id: self.toggle_kain_status(k_id))
            self.table_kain.setCellWidget(row, 5, btn_toggle)

    def toggle_kain_status(self, kain_id):
        """Fungsi untuk mengubah status kain secara langsung dari tabel."""
        kain = self.db.query(DebtEntry).get(kain_id)
        if not kain: return
        
        # Balikkan Status
        if kain.status_cutting == 'CLOSE':
            kain.status_cutting = 'OPEN'
        else:
            kain.status_cutting = 'CLOSE'
            
        self.db.commit()
        self.load_data() # Refresh tabel

    def calculate_profit(self):
        selected = self.table_kain.selectedItems()
        if not selected: return
        
        kain_id = self.table_kain.item(selected[0].row(), 1).data(Qt.UserRole)
        kain = self.db.query(DebtEntry).get(kain_id)
        
        if not kain: return
            
        # Hitung Total Qty
        total_potong = sum(c.qty for c in kain.hasil_cuttings)
        total_distribusi = 0
        for hc in kain.hasil_cuttings:
            total_distribusi += sum(d.qty for d in hc.distribusi)

        # ==========================================
        # VALIDATION GATES (THE CONTROL ROOM RULES)
        # ==========================================
        if kain.status_cutting != 'CLOSE':
            self.show_validation_error("STATUS KAIN MASIH 'OPEN'\nKlik Tutup (CLOSE) untuk melihat profit.")
            return
            
        if total_potong == 0:
            self.show_validation_error("BELUM ADA HASIL CUTTING\nCatat potongan di menu Harian terlebih dahulu.")
            return
            
        if total_distribusi < total_potong:
            self.show_validation_error("DISTRIBUSI BELUM SELESAI\nPastikan semua potongan sudah diserahkan ke Penjahit/Pengsup.")
            return

        # ==========================================
        # PROFIT SIMULATION ENGINE (PASSED GATES)
        # ==========================================
        total_revenue = 0
        for hc in kain.hasil_cuttings:
            if hc.sku:
                total_revenue += (hc.qty * hc.sku.harga_jual)
                
        gross_margin = total_revenue - kain.nominal_hutang
        self.card_gross.findChildren(QLabel)[1].setText(f"Rp {total_revenue:,.0f}")
        
        # 1. HOME PRODUCTION SIMULATION
        tarif_jahit_estimasi = 600 # Rata-rata atau ganti dengan query database MasterTarif
        biaya_jahit_total = total_potong * tarif_jahit_estimasi
        biaya_aksesoris_home = total_potong * (self.TOTAL_AKSESORIS + self.BIAYA_PACKAGING)
        
        total_cost_home = biaya_jahit_total + biaya_aksesoris_home
        profit_home = gross_margin - total_cost_home
        
        self.card_home.findChildren(QLabel)[1].setText(f"Rp {profit_home:,.0f}\n({profit_home/total_potong:,.0f} /pcs)")
        
        # 2. OUTSOURCED (PENGSUP) SIMULATION
        tarif_pengsup_estimasi = 1500 
        biaya_pengsup_total = total_potong * tarif_pengsup_estimasi
        biaya_aksesoris_pengsup = total_potong * self.TOTAL_AKSESORIS # Pengsup tidak menggunakan packaging
        
        total_cost_pengsup = biaya_pengsup_total + biaya_aksesoris_pengsup
        profit_pengsup = gross_margin - total_cost_pengsup
        
        self.card_pengsup.findChildren(QLabel)[1].setText(f"Rp {profit_pengsup:,.0f}\n({profit_pengsup/total_potong:,.0f} /pcs)")

    def show_validation_error(self, message):
        """Menampilkan pesan error merah di card jika belum memenuhi syarat profit."""
        error_style = f"color: {Theme.NEON_PINK}; font-size: 11pt; font-weight: bold;"
        
        val_gross = self.card_gross.findChildren(QLabel)[1]
        val_home = self.card_home.findChildren(QLabel)[1]
        val_pengsup = self.card_pengsup.findChildren(QLabel)[1]
        
        for val in [val_gross, val_home, val_pengsup]:
            val.setText(message)
            val.setStyleSheet(error_style)

    def reset_cards(self):
        default_style = f"color: {Theme.TEXT_MAIN}; font-size: 16pt; font-weight: bold;"
        for card, color in [(self.card_gross, Theme.NEON_CYAN), (self.card_home, Theme.NEON_YELLOW), (self.card_pengsup, Theme.NEON_PINK)]:
            val = card.findChildren(QLabel)[1]
            val.setText("-")
            val.setStyleSheet(f"color: {color}; font-size: 16pt; font-weight: bold;")