# app_essa/ui/views/gaji_view.py
import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, 
    QComboBox, QSpinBox, QDoubleSpinBox, QDateEdit, QMessageBox, 
    QTableWidgetItem, QHeaderView, QTabWidget, QGridLayout
)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QColor, QBrush

from ui.components.tables import CyberTable
from ui.components.buttons import CyberButton
from ui.theme import Theme
from data.database import SessionLocal
from data.models import Person, SkuMaster
from data.models.salary import SalaryRun, SalaryLineItem, MasterTarifPenjahit
from data.models.bon import BonBalance, BonMovement

class GajiView(QWidget):
    def __init__(self):
        super().__init__()
        self.db = SessionLocal()
        
        # Cart for Penjahit
        self.cart_penjahit = [] 
        
        self.setup_ui()
        self.load_dropdowns()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # --- Page Header ---
        header_layout = QHBoxLayout()
        title = QLabel("PAYROLL & REKAP GAJI")
        title.setStyleSheet(f"font-size: 24pt; font-weight: bold; color: {Theme.NEON_CYAN};")
        header_layout.addWidget(title)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        # --- TABS SETUP ---
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(f"""
            QTabBar::tab {{
                background: {Theme.BG_VOID}; color: {Theme.TEXT_MUTED};
                border: 1px solid {Theme.BORDER_DIM}; padding: 12px 25px; font-weight: bold; font-size: 11pt;
            }}
            QTabBar::tab:selected {{
                background: {Theme.BG_PANEL}; color: {Theme.NEON_CYAN};
                border-bottom: 2px solid {Theme.NEON_CYAN};
            }}
            QTabWidget::pane {{ border: 1px solid {Theme.BORDER_DIM}; top: -1px; }}
        """)

        self.setup_tab_penjahit()
        self.setup_tab_pengsup()
        self.setup_tab_pasukan()

        self.tabs.addTab(self.tab_penjahit, "GAJI PENJAHIT")
        self.tabs.addTab(self.tab_pengsup, "TOTALAN PENGSUP")
        self.tabs.addTab(self.tab_pasukan, "GAJI KARYAWAN (ABSENSI)")
        
        layout.addWidget(self.tabs)

    # ==========================================
    # TAB 1: GAJI PENJAHIT (BORONGAN)
    # ==========================================
    def setup_tab_penjahit(self):
        self.tab_penjahit = QWidget()
        lay = QVBoxLayout(self.tab_penjahit)
        
        # --- TOP: Identity & Kasbon ---
        top_frame = QFrame()
        top_frame.setObjectName("GridPanel")
        top_lay = QGridLayout(top_frame)
        
        self.penj_person = QComboBox()
        self.penj_person.currentIndexChanged.connect(self.on_penjahit_selected)
        self.penj_date = QDateEdit(QDate.currentDate())
        self.penj_date.setCalendarPopup(True)
        
        self.penj_bon_lama = QDoubleSpinBox()
        self.penj_bon_lama.setRange(0, 999999999); self.penj_bon_lama.setPrefix("Rp "); self.penj_bon_lama.setReadOnly(True)
        self.penj_bon_lama.setStyleSheet(f"color: {Theme.NEON_PINK}; font-weight: bold;")
        self.penj_bon_lama.buttonSymbols = QDoubleSpinBox.ButtonSymbols.NoButtons
        
        self.penj_tambah_bon = QDoubleSpinBox()
        self.penj_tambah_bon.setRange(0, 999999999); self.penj_tambah_bon.setPrefix("Rp ")
        
        self.penj_potong_bon = QDoubleSpinBox()
        self.penj_potong_bon.setRange(0, 999999999); self.penj_potong_bon.setPrefix("Rp ")
        
        top_lay.addWidget(QLabel("Nama Penjahit:"), 0, 0); top_lay.addWidget(self.penj_person, 0, 1)
        top_lay.addWidget(QLabel("Tanggal:"), 0, 2); top_lay.addWidget(self.penj_date, 0, 3)
        
        top_lay.addWidget(QLabel("Sisa Bon Lama:"), 1, 0); top_lay.addWidget(self.penj_bon_lama, 1, 1)
        top_lay.addWidget(QLabel("+ Tambah Bon Baru:"), 1, 2); top_lay.addWidget(self.penj_tambah_bon, 1, 3)
        top_lay.addWidget(QLabel("- Potong Bon Minggu Ini:"), 1, 4); top_lay.addWidget(self.penj_potong_bon, 1, 5)
        
        lay.addWidget(top_frame)
        
        # --- MID: Input Garapan (Cart) ---
        mid_frame = QFrame()
        mid_frame.setStyleSheet(f"background-color: {Theme.BG_PANEL}; border: 1px solid {Theme.BORDER_DIM};")
        mid_lay = QHBoxLayout(mid_frame)
        
        self.penj_sku = QComboBox()
        self.penj_sku.setEditable(True)
        self.penj_sku.setMinimumWidth(250)
        self.penj_sku.currentIndexChanged.connect(self.on_garapan_changed)
        
        self.penj_qty = QSpinBox()
        self.penj_qty.setRange(1, 99999)
        self.penj_qty.setPrefix("Qty: ")
        
        self.penj_harga = QDoubleSpinBox()
        self.penj_harga.setRange(0, 999999999); self.penj_harga.setPrefix("Rp ")
        # FIX: Kunci input harga agar mengikuti master data
        self.penj_harga.setReadOnly(True)
        self.penj_harga.setStyleSheet(f"background-color: {Theme.BG_VOID}; color: {Theme.NEON_YELLOW};")
        self.penj_harga.buttonSymbols = QDoubleSpinBox.ButtonSymbols.NoButtons
        
        btn_add = CyberButton("TAMBAH GARAPAN")
        btn_add.clicked.connect(self.add_garapan)
        
        mid_lay.addWidget(QLabel("Pilih SKU/Jenis:")); mid_lay.addWidget(self.penj_sku)
        mid_lay.addWidget(self.penj_qty); mid_lay.addWidget(QLabel("Harga/Pcs:")); mid_lay.addWidget(self.penj_harga)
        mid_lay.addWidget(btn_add)
        
        lay.addWidget(mid_frame)
        
        # --- BOTTOM: Table & Action ---
        self.table_penj = CyberTable()
        self.table_penj.setColumnCount(4)
        self.table_penj.setHorizontalHeaderLabels(["Jenis Garapan", "Qty", "Harga Satuan", "Total Harga"])
        self.table_penj.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        lay.addWidget(self.table_penj)
        
        bot_lay = QHBoxLayout()
        btn_del = CyberButton("Hapus Baris", is_danger=True)
        btn_del.clicked.connect(self.del_garapan)
        
        self.lbl_gaji_kotor = QLabel("TOTAL KOTOR: Rp 0")
        self.lbl_gaji_kotor.setStyleSheet(f"font-size: 14pt; font-weight: bold; color: {Theme.NEON_YELLOW};")
        
        btn_save = CyberButton("SIMPAN GAJI & CETAK NOTA")
        btn_save.setStyleSheet(f"background-color: {Theme.NEON_CYAN}; color: #000; font-weight: bold;")
        btn_save.clicked.connect(self.submit_penjahit)
        
        bot_lay.addWidget(btn_del); bot_lay.addStretch()
        bot_lay.addWidget(self.lbl_gaji_kotor); bot_lay.addWidget(btn_save)
        lay.addLayout(bot_lay)

    # ==========================================
    # TAB 2 & 3: PLACEHOLDERS (For Next Steps)
    # ==========================================
    def setup_tab_pengsup(self):
        self.tab_pengsup = QWidget()
        lay = QVBoxLayout(self.tab_pengsup)
        lbl = QLabel("MODUL TOTALAN PENGSUP\n(Akan dibangun di tahap selanjutnya)")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setStyleSheet("color: gray; font-size: 16pt;")
        lay.addWidget(lbl)

    def setup_tab_pasukan(self):
        self.tab_pasukan = QWidget()
        lay = QVBoxLayout(self.tab_pasukan)
        lbl = QLabel("MODUL GAJI KARYAWAN & IMPORT EXCEL\n(Akan dibangun di tahap selanjutnya)")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setStyleSheet("color: gray; font-size: 16pt;")
        lay.addWidget(lbl)

    # ==========================================
    # LOGIC: PENJAHIT
    # ==========================================
    def load_dropdowns(self):
        self.penj_person.clear()
        self.penj_person.addItem("-- Pilih Penjahit --", None)
        persons = self.db.query(Person).filter(Person.person_type == 'PENJAHIT').all()
        for p in persons: self.penj_person.addItem(p.nama, p.id)
            
        # FIX: Tarik data dari Tabel Database, bukan dictionary!
        self.penj_sku.clear()
        self.penj_sku.addItem("-- Pilih Garapan --", None)
        
        tarifs = self.db.query(MasterTarifPenjahit).filter(MasterTarifPenjahit.is_active == 1).order_by(MasterTarifPenjahit.kode_garapan).all()
        for t in tarifs: 
            # Simpan ID dan Harga sekaligus
            self.penj_sku.addItem(t.kode_garapan, (t.id, t.harga))

    def on_garapan_changed(self, index):
        if index > 0:
            data = self.penj_sku.itemData(index)
            if data:
                tarif_id, harga_db = data
                self.penj_harga.setValue(harga_db)

    def on_penjahit_selected(self):
        p_id = self.penj_person.currentData()
        if not p_id:
            self.penj_bon_lama.setValue(0)
            return
            
        balance = self.db.query(BonBalance).filter(BonBalance.person_id == p_id).first()
        self.penj_bon_lama.setValue(balance.saldo if balance else 0)

    def add_garapan(self):
        sku_text = self.penj_sku.currentText()
        
        # Tarik data tuple dari combobox
        data = self.penj_sku.currentData()
        tarif_id = data[0] if data else None 
        
        qty = self.penj_qty.value()
        harga = self.penj_harga.value()
        
        if not sku_text or sku_text == "-- Pilih Garapan --" or harga <= 0:
            QMessageBox.warning(self, "Error", "Pilih garapan dan pastikan harga valid!")
            return
            
        total = qty * harga
        self.cart_penjahit.append({
            "tarif_id": tarif_id, # <--- SIMPAN ID DISINI
            "sku_id": None,
            "nama_garapan": sku_text,
            "qty": qty,
            "harga": harga,
            "total": total
        })
        self.refresh_cart_table()
        self.penj_qty.setValue(0)
        
    def del_garapan(self):
        selected = self.table_penj.selectedItems()
        if not selected: return
        rows = sorted(list(set([item.row() for item in selected])), reverse=True)
        for r in rows:
            self.cart_penjahit.pop(r)
        self.refresh_cart_table()

    def refresh_cart_table(self):
        self.table_penj.setRowCount(0)
        gaji_kotor = 0
        for i, item in enumerate(self.cart_penjahit):
            self.table_penj.insertRow(i)
            self.table_penj.setItem(i, 0, QTableWidgetItem(item['nama_garapan']))
            self.table_penj.setItem(i, 1, QTableWidgetItem(str(item['qty'])))
            self.table_penj.setItem(i, 2, QTableWidgetItem(f"Rp {item['harga']:,.0f}"))
            self.table_penj.setItem(i, 3, QTableWidgetItem(f"Rp {item['total']:,.0f}"))
            gaji_kotor += item['total']
            
        self.lbl_gaji_kotor.setText(f"TOTAL KOTOR: Rp {gaji_kotor:,.0f}")

    def submit_penjahit(self):
        person_id = self.penj_person.currentData()
        if not person_id:
            QMessageBox.warning(self, "Error", "Pilih nama penjahit terlebih dahulu!")
            return
            
        if not self.cart_penjahit:
            QMessageBox.warning(self, "Error", "Belum ada garapan yang ditambahkan!")
            return
            
        bon_lama = self.penj_bon_lama.value()
        tambah_bon = self.penj_tambah_bon.value()
        potong_bon = self.penj_potong_bon.value()
        
        gaji_kotor = sum(item['total'] for item in self.cart_penjahit)
        gaji_bersih = gaji_kotor - potong_bon
        sisa_bon_akhir = bon_lama + tambah_bon - potong_bon
        
        if potong_bon > gaji_kotor:
            QMessageBox.warning(self, "Error", "Potongan bon tidak boleh lebih besar dari Gaji Kotor!")
            return

        try:
            tanggal_str = self.penj_date.date().toString("yyyy-MM-dd")
            
            # 1. Create Salary Run
            run = SalaryRun(
                tipe="BORONGAN_PENJAHIT",
                person_id=person_id,
                tanggal_proses=tanggal_str,
                gaji_kotor=gaji_kotor,
                bon_lama=bon_lama,
                tambah_bon=tambah_bon,
                potong_bon=potong_bon,
                gaji_bersih=gaji_bersih,
                sisa_bon_akhir=sisa_bon_akhir
            )
            self.db.add(run)
            self.db.flush() # Get run.id
            
            # 2. Add Line Items
            for item in self.cart_penjahit:
                line = SalaryLineItem(
                    salary_run_id=run.id,
                    sku_id=item['sku_id'],
                    tarif_id=item['tarif_id'], # <--- MASUKKAN KE DATABASE
                    model_code=item['nama_garapan'] if not item['sku_id'] else None,
                    qty=item['qty'],
                    tarif_per_pcs=item['harga'],
                    subtotal=item['total']
                )
                self.db.add(line)
                
            # 3. Handle Kasbon Updates
            balance = self.db.query(BonBalance).filter(BonBalance.person_id == person_id).first()
            if not balance:
                balance = BonBalance(person_id=person_id, saldo=0)
                self.db.add(balance)
                
            if tambah_bon > 0:
                mov = BonMovement(person_id=person_id, tanggal=tanggal_str, tipe="TAMBAH", 
                                  nominal=tambah_bon, sumber="PAYROLL_PENJAHIT", catatan="Tambah kasbon saat gajian")
                self.db.add(mov)
                balance.saldo += tambah_bon
                
            if potong_bon > 0:
                mov = BonMovement(person_id=person_id, tanggal=tanggal_str, tipe="POTONG_GAJI", 
                                  nominal=potong_bon, sumber="PAYROLL_PENJAHIT", catatan="Potong kasbon saat gajian")
                self.db.add(mov)
                balance.saldo -= potong_bon
                
            self.db.commit()
            
            QMessageBox.information(self, "Sukses", "Data gaji penjahit berhasil disimpan dan kasbon diupdate!")
            
            # Reset UI
            self.cart_penjahit.clear()
            self.refresh_cart_table()
            self.penj_tambah_bon.setValue(0)
            self.penj_potong_bon.setValue(0)
            self.penj_harga.setValue(0)
            self.on_penjahit_selected() # Refresh Bon balance
            
        except Exception as e:
            self.db.rollback()
            QMessageBox.critical(self, "Error", f"Gagal menyimpan data: {e}")

    def closeEvent(self, event):
        self.db.close()
        super().closeEvent(event)