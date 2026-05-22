# app_essa/ui/views/harian_view.py
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTabWidget, 
    QTableWidgetItem, QHeaderView, QComboBox, QSpinBox, 
    QDateEdit, QMessageBox, QFrame, QCompleter, QDoubleSpinBox, 
    QGridLayout, QLineEdit
)
from PySide6.QtCore import Qt, QDate

from ui.components.tables import CyberTable
from ui.components.buttons import CyberButton
from ui.theme import Theme
from data.database import SessionLocal
from data.models import HasilCutting, DistribusiCutting, PengeluaranOffline, ModalOperasional, SkuMaster, Person

class CatatanHarianView(QWidget):
    def __init__(self):
        super().__init__()
        self.db = SessionLocal()
        self.setup_ui()
        
        # Load initial dropdown data
        self.load_skus()
        self.load_persons()
        
        # Load tables
        self.load_hasil_cutting()
        self.load_distribusi()
        self.load_offline()
        self.load_operasional()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # --- Page Header ---
        header_layout = QHBoxLayout()
        title = QLabel("CATATAN HARIAN")
        title.setStyleSheet(f"font-size: 24pt; font-weight: bold; color: {Theme.NEON_CYAN};")
        header_layout.addWidget(title)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        # --- Tabs Container ---
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

        # Build Tabs
        self.setup_tab_cutting()
        self.setup_tab_distribusi()
        self.setup_tab_offline()
        self.setup_tab_operasional() # NEW TAB

        self.tabs.addTab(self.tab_cutting, "HASIL CUTTING")
        self.tabs.addTab(self.tab_distribusi, "DISTRIBUSI JAHIT")
        self.tabs.addTab(self.tab_offline, "PENGELUARAN OFFLINE")
        self.tabs.addTab(self.tab_operasional, "MODAL OPERASIONAL")
        layout.addWidget(self.tabs)

    def setup_completer(self, combobox):
        completer = combobox.completer()
        if completer:
            completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
            completer.setFilterMode(Qt.MatchFlag.MatchContains)
            completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)

    # ==========================================
    # 1. TAB HASIL CUTTING
    # ==========================================
    def setup_tab_cutting(self):
        self.tab_cutting = QWidget()
        lay = QVBoxLayout(self.tab_cutting)
        
        form_frame = QFrame()
        form_frame.setObjectName("GridPanel")
        form_lay = QHBoxLayout(form_frame)
        
        self.date_cut = QDateEdit(QDate.currentDate())
        self.date_cut.setCalendarPopup(True)
        
        self.sku_cut = QComboBox()
        self.sku_cut.setEditable(True)
        self.sku_cut.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.sku_cut.lineEdit().setPlaceholderText("Ketik SKU...")
        self.sku_cut.setMinimumWidth(300)
        self.setup_completer(self.sku_cut)
        
        self.qty_cut = QSpinBox()
        self.qty_cut.setRange(1, 99999)
        
        self.btn_submit_cut = CyberButton("SIMPAN CUTTING")
        self.btn_submit_cut.clicked.connect(self.submit_cutting)

        form_lay.addWidget(QLabel("Tanggal:"))
        form_lay.addWidget(self.date_cut)
        form_lay.addWidget(QLabel("  SKU:"))
        form_lay.addWidget(self.sku_cut, stretch=1)
        form_lay.addWidget(QLabel("  Qty:"))
        form_lay.addWidget(self.qty_cut)
        form_lay.addWidget(self.btn_submit_cut)
        lay.addWidget(form_frame)

        self.table_cutting = CyberTable()
        self.table_cutting.setColumnCount(4)
        self.table_cutting.setHorizontalHeaderLabels(["ID", "Tanggal", "SKU", "Qty"])
        self.table_cutting.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        lay.addWidget(self.table_cutting)

    # ==========================================
    # 2. TAB DISTRIBUSI JAHIT
    # ==========================================
    def setup_tab_distribusi(self):
        self.tab_distribusi = QWidget()
        lay = QVBoxLayout(self.tab_distribusi)
        
        form_frame = QFrame()
        form_frame.setObjectName("GridPanel")
        form_lay = QHBoxLayout(form_frame)
        
        self.date_dist = QDateEdit(QDate.currentDate())
        self.date_dist.setCalendarPopup(True)
        
        self.person_dist = QComboBox()
        self.person_dist.setEditable(True)
        self.person_dist.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.person_dist.lineEdit().setPlaceholderText("Pilih Penjahit/Pengsup...")
        self.setup_completer(self.person_dist)

        self.sku_dist = QComboBox()
        self.sku_dist.setEditable(True)
        self.sku_dist.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.sku_dist.lineEdit().setPlaceholderText("Ketik SKU...")
        self.setup_completer(self.sku_dist)
        
        self.qty_dist = QSpinBox()
        self.qty_dist.setRange(1, 99999)
        
        self.btn_submit_dist = CyberButton("SIMPAN DISTRIBUSI")
        self.btn_submit_dist.clicked.connect(self.submit_distribusi)

        form_lay.addWidget(QLabel("Tanggal:"))
        form_lay.addWidget(self.date_dist)
        form_lay.addWidget(QLabel("  Penerima:"))
        form_lay.addWidget(self.person_dist, stretch=1)
        form_lay.addWidget(QLabel("  SKU:"))
        form_lay.addWidget(self.sku_dist, stretch=1)
        form_lay.addWidget(QLabel("  Qty:"))
        form_lay.addWidget(self.qty_dist)
        form_lay.addWidget(self.btn_submit_dist)
        lay.addWidget(form_frame)

        self.table_distribusi = CyberTable()
        self.table_distribusi.setColumnCount(6)
        self.table_distribusi.setHorizontalHeaderLabels(["ID", "Tanggal", "Penerima", "Jenis", "SKU", "Qty"])
        self.table_distribusi.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        lay.addWidget(self.table_distribusi)

    # ==========================================
    # 3. TAB PENGELUARAN OFFLINE
    # ==========================================
    def setup_tab_offline(self):
        self.tab_offline = QWidget()
        lay = QVBoxLayout(self.tab_offline)
        
        form_frame = QFrame()
        form_frame.setObjectName("GridPanel")
        form_lay = QGridLayout(form_frame)
        
        self.date_off = QDateEdit(QDate.currentDate())
        self.date_off.setCalendarPopup(True)
        
        self.person_off = QComboBox()
        self.person_off.setEditable(True)
        self.person_off.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.person_off.lineEdit().setPlaceholderText("Pilih Pembeli/Klien...")
        self.setup_completer(self.person_off)

        self.sku_off = QComboBox()
        self.sku_off.setEditable(True)
        self.sku_off.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.sku_off.lineEdit().setPlaceholderText("Ketik SKU...")
        self.setup_completer(self.sku_off)
        
        self.qty_off = QSpinBox()
        self.qty_off.setRange(1, 99999)
        self.qty_off.valueChanged.connect(self.calculate_offline_total)
        
        self.harga_off = QDoubleSpinBox()
        self.harga_off.setRange(0, 99999999)
        self.harga_off.setPrefix("Rp ")
        self.harga_off.valueChanged.connect(self.calculate_offline_total)
        
        self.total_off = QDoubleSpinBox()
        self.total_off.setRange(0, 999999999)
        self.total_off.setPrefix("Rp ")
        self.total_off.setReadOnly(True)
        self.total_off.setStyleSheet(f"background-color: {Theme.BG_VOID}; color: {Theme.NEON_PINK}; font-weight: bold;")
        self.total_off.buttonSymbols = QDoubleSpinBox.ButtonSymbols.NoButtons
        
        self.btn_submit_off = CyberButton("SIMPAN PENJUALAN")
        self.btn_submit_off.clicked.connect(self.submit_offline)

        form_lay.addWidget(QLabel("Tanggal:"), 0, 0)
        form_lay.addWidget(self.date_off, 0, 1)
        form_lay.addWidget(QLabel("Pembeli:"), 0, 2)
        form_lay.addWidget(self.person_off, 0, 3)
        form_lay.addWidget(QLabel("SKU:"), 0, 4)
        form_lay.addWidget(self.sku_off, 0, 5)
        
        form_lay.addWidget(QLabel("Qty:"), 1, 0)
        form_lay.addWidget(self.qty_off, 1, 1)
        form_lay.addWidget(QLabel("Harga Satuan:"), 1, 2)
        form_lay.addWidget(self.harga_off, 1, 3)
        form_lay.addWidget(QLabel("Total:"), 1, 4)
        form_lay.addWidget(self.total_off, 1, 5)
        
        form_lay.addWidget(self.btn_submit_off, 1, 6)
        lay.addWidget(form_frame)

        self.table_offline = CyberTable()
        self.table_offline.setColumnCount(7)
        self.table_offline.setHorizontalHeaderLabels(["ID", "Tanggal", "Pembeli", "SKU", "Qty", "Harga", "Total"])
        self.table_offline.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        lay.addWidget(self.table_offline)

    def calculate_offline_total(self):
        self.total_off.setValue(self.qty_off.value() * self.harga_off.value())

    # ==========================================
    # 4. TAB MODAL OPERASIONAL
    # ==========================================
    def setup_tab_operasional(self):
        self.tab_operasional = QWidget()
        lay = QVBoxLayout(self.tab_operasional)
        
        form_frame = QFrame()
        form_frame.setObjectName("GridPanel")
        form_lay = QHBoxLayout(form_frame)
        
        self.date_op = QDateEdit(QDate.currentDate())
        self.date_op.setCalendarPopup(True)
        
        self.jenis_op = QComboBox()
        self.jenis_op.addItems(["OVERHEAD", "BARANG", "UTILITAS", "LAINNYA"])
        
        self.ket_op = QLineEdit()
        self.ket_op.setPlaceholderText("Misal: Uang Makan, Listrik, Tali Goni...")
        
        self.nominal_op = QDoubleSpinBox()
        self.nominal_op.setRange(0, 999999999)
        self.nominal_op.setPrefix("Rp ")
        
        self.btn_submit_op = CyberButton("SIMPAN PENGELUARAN")
        self.btn_submit_op.clicked.connect(self.submit_operasional)

        form_lay.addWidget(QLabel("Tanggal:"))
        form_lay.addWidget(self.date_op)
        form_lay.addWidget(QLabel("  Jenis:"))
        form_lay.addWidget(self.jenis_op)
        form_lay.addWidget(QLabel("  Keterangan:"))
        form_lay.addWidget(self.ket_op, stretch=1)
        form_lay.addWidget(QLabel("  Nominal Total:"))
        form_lay.addWidget(self.nominal_op)
        form_lay.addWidget(self.btn_submit_op)
        
        lay.addWidget(form_frame)

        self.table_operasional = CyberTable()
        self.table_operasional.setColumnCount(5)
        self.table_operasional.setHorizontalHeaderLabels(["ID", "Tanggal", "Kategori", "Keterangan", "Nominal / Total"])
        self.table_operasional.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        lay.addWidget(self.table_operasional)

    # --- DATA LOADERS ---
    def load_skus(self):
        self.sku_cut.clear()
        self.sku_dist.clear()
        self.sku_off.clear()
        skus = self.db.query(SkuMaster).filter(SkuMaster.is_active == 1).order_by(SkuMaster.kode_sku).all()
        for sku in skus:
            text = f"{sku.kode_sku} - {sku.nama_produk[:30]}"
            self.sku_cut.addItem(text, sku.id)
            self.sku_dist.addItem(text, sku.id)
            self.sku_off.addItem(text, sku.id)

    def load_persons(self):
        self.person_dist.clear()
        self.person_off.clear()
        persons = self.db.query(Person).order_by(Person.nama).all()
        for p in persons:
            text = f"{p.nama} ({p.person_type})"
            if p.person_type in ['PENJAHIT', 'PENGSUP']:
                self.person_dist.addItem(text, p.id)
            if p.person_type in ['KLIEN', 'LAINNYA']:
                self.person_off.addItem(text, p.id)

    def load_hasil_cutting(self):
        records = self.db.query(HasilCutting).order_by(HasilCutting.tanggal.desc(), HasilCutting.id.desc()).limit(100).all()
        self.table_cutting.setRowCount(len(records))
        for row, rec in enumerate(records):
            self.table_cutting.setItem(row, 0, QTableWidgetItem(str(rec.id)))
            self.table_cutting.setItem(row, 1, QTableWidgetItem(rec.tanggal))
            self.table_cutting.setItem(row, 2, QTableWidgetItem(rec.sku.kode_sku if rec.sku else "Unknown"))
            qty_item = QTableWidgetItem(str(rec.qty))
            qty_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table_cutting.setItem(row, 3, qty_item)

    def load_distribusi(self):
        records = self.db.query(DistribusiCutting).order_by(DistribusiCutting.tanggal.desc(), DistribusiCutting.id.desc()).limit(100).all()
        self.table_distribusi.setRowCount(len(records))
        for row, rec in enumerate(records):
            self.table_distribusi.setItem(row, 0, QTableWidgetItem(str(rec.id)))
            self.table_distribusi.setItem(row, 1, QTableWidgetItem(rec.tanggal))
            self.table_distribusi.setItem(row, 2, QTableWidgetItem(rec.person.nama if rec.person else "Unknown"))
            self.table_distribusi.setItem(row, 3, QTableWidgetItem(rec.jenis))
            self.table_distribusi.setItem(row, 4, QTableWidgetItem(rec.sku.kode_sku if rec.sku else "Unknown"))
            qty_item = QTableWidgetItem(str(rec.qty))
            qty_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table_distribusi.setItem(row, 5, qty_item)

    def load_offline(self):
        records = self.db.query(PengeluaranOffline).order_by(PengeluaranOffline.tanggal.desc(), PengeluaranOffline.id.desc()).limit(100).all()
        self.table_offline.setRowCount(len(records))
        for row, rec in enumerate(records):
            self.table_offline.setItem(row, 0, QTableWidgetItem(str(rec.id)))
            self.table_offline.setItem(row, 1, QTableWidgetItem(rec.tanggal))
            self.table_offline.setItem(row, 2, QTableWidgetItem(rec.person.nama if rec.person else "Unknown"))
            self.table_offline.setItem(row, 3, QTableWidgetItem(rec.sku.kode_sku if rec.sku else "Unknown"))
            qty_item = QTableWidgetItem(str(rec.qty))
            qty_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table_offline.setItem(row, 4, qty_item)
            harga_item = QTableWidgetItem(f"{rec.harga_satuan:,.0f}")
            harga_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table_offline.setItem(row, 5, harga_item)
            total_item = QTableWidgetItem(f"{rec.total:,.0f}")
            total_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table_offline.setItem(row, 6, total_item)

    def load_operasional(self):
        records = self.db.query(ModalOperasional).order_by(ModalOperasional.tanggal.desc(), ModalOperasional.id.desc()).limit(100).all()
        self.table_operasional.setRowCount(len(records))
        for row, rec in enumerate(records):
            self.table_operasional.setItem(row, 0, QTableWidgetItem(str(rec.id)))
            self.table_operasional.setItem(row, 1, QTableWidgetItem(rec.tanggal))
            self.table_operasional.setItem(row, 2, QTableWidgetItem(rec.jenis))
            self.table_operasional.setItem(row, 3, QTableWidgetItem(rec.keterangan))
            
            nom_item = QTableWidgetItem(f"{rec.nominal:,.0f}")
            nom_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table_operasional.setItem(row, 4, nom_item)

    # --- SUBMIT ACTIONS ---
    def get_valid_combo_data(self, combobox, error_msg):
        text = combobox.currentText().strip()
        if not text:
            QMessageBox.warning(self, "Error", "Form tidak boleh kosong!")
            return None
        index = combobox.findText(text)
        if index == -1:
            QMessageBox.warning(self, "Data Tidak Valid", error_msg)
            return None
        return combobox.itemData(index)

    def submit_cutting(self):
        sku_id = self.get_valid_combo_data(self.sku_cut, "SKU tidak ditemukan! Pilih dari daftar.")
        if not sku_id: return
        try:
            record = HasilCutting(tanggal=self.date_cut.date().toString("yyyy-MM-dd"), sku_id=sku_id, qty=self.qty_cut.value(), catatan="Manual Input")
            self.db.add(record)
            self.db.commit()
            self.load_hasil_cutting()
            self.qty_cut.setValue(0); self.sku_cut.lineEdit().clear() 
        except Exception as e:
            self.db.rollback()
            QMessageBox.critical(self, "Error", f"Gagal: {e}")

    def submit_distribusi(self):
        person_id = self.get_valid_combo_data(self.person_dist, "Penerima tidak ditemukan! Pilih dari daftar.")
        sku_id = self.get_valid_combo_data(self.sku_dist, "SKU tidak ditemukan!")
        if not person_id or not sku_id: return
        person_record = self.db.query(Person).get(person_id)
        jenis_pekerjaan = person_record.person_type if person_record else 'PENJAHIT'
        try:
            record = DistribusiCutting(tanggal=self.date_dist.date().toString("yyyy-MM-dd"), person_id=person_id, jenis=jenis_pekerjaan, sku_id=sku_id, qty=self.qty_dist.value(), catatan="Manual Input")
            self.db.add(record)
            self.db.commit()
            self.load_distribusi()
            self.qty_dist.setValue(0); self.sku_dist.lineEdit().clear(); self.person_dist.lineEdit().clear()
        except Exception as e:
            self.db.rollback()
            QMessageBox.critical(self, "Error", f"Gagal: {e}")

    def submit_offline(self):
        person_id = self.get_valid_combo_data(self.person_off, "Pembeli tidak ditemukan! Pilih Klien dari daftar.")
        sku_id = self.get_valid_combo_data(self.sku_off, "SKU tidak ditemukan!")
        if not person_id or not sku_id: return
        try:
            record = PengeluaranOffline(
                tanggal=self.date_off.date().toString("yyyy-MM-dd"), person_id=person_id, sku_id=sku_id,
                qty=self.qty_off.value(), harga_satuan=self.harga_off.value(), total=self.total_off.value(), catatan="Manual Input"
            )
            self.db.add(record)
            self.db.commit()
            self.load_offline()
            self.qty_off.setValue(0); self.harga_off.setValue(0); self.sku_off.lineEdit().clear(); self.person_off.lineEdit().clear()
        except Exception as e:
            self.db.rollback()
            QMessageBox.critical(self, "Error", f"Gagal: {e}")

    def submit_operasional(self):
        keterangan = self.ket_op.text().strip()
        nominal = self.nominal_op.value()
        
        if not keterangan or nominal <= 0:
            QMessageBox.warning(self, "Error", "Keterangan dan Nominal tidak boleh kosong/nol!")
            return
            
        try:
            record = ModalOperasional(
                tanggal=self.date_op.date().toString("yyyy-MM-dd"),
                jenis=self.jenis_op.currentText(),
                keterangan=keterangan,
                nominal=nominal,
                catatan="Manual Input"
            )
            self.db.add(record)
            self.db.commit()
            
            self.load_operasional()
            self.ket_op.clear()
            self.nominal_op.setValue(0)
        except Exception as e:
            self.db.rollback()
            QMessageBox.critical(self, "Error", f"Gagal: {e}")

    def closeEvent(self, event):
        self.db.close()
        super().closeEvent(event)