# app_essa/ui/views/harian_view.py
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTabWidget, 
    QTableWidgetItem, QHeaderView, QComboBox, QSpinBox, 
    QDateEdit, QMessageBox, QFrame, QCompleter, QDoubleSpinBox, 
    QGridLayout, QLineEdit, QAbstractItemView
)
from PySide6.QtCore import Qt, QDate

from ui.components.tables import CyberTable
from ui.components.buttons import CyberButton
from ui.theme import Theme
from data.database import SessionLocal
from data.models import HasilCutting, DistribusiCutting, PengeluaranOffline, ModalOperasional, SkuMaster, Person
from data.models.debt import DebtEntry

class CatatanHarianView(QWidget):
    def __init__(self):
        super().__init__()
        self.db = SessionLocal()
        self.selected_cut_id = None
        self.selected_dist_id = None
        self.selected_off_id = None
        self.selected_op_id = None
        
        self.setup_ui()
        
        self.load_skus()
        self.load_persons()
        
        self.load_hasil_cutting()
        self.load_distribusi()
        self.load_offline()
        self.load_operasional()
        self.load_sumber_dropdowns()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        header_layout = QHBoxLayout()
        title = QLabel("CATATAN HARIAN")
        title.setStyleSheet(f"font-size: 24pt; font-weight: bold; color: {Theme.NEON_CYAN};")
        header_layout.addWidget(title)
        header_layout.addStretch()
        layout.addLayout(header_layout)

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

        self.setup_tab_cutting()
        self.setup_tab_distribusi()
        self.setup_tab_offline()
        self.setup_tab_operasional()

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
    # 1. TAB HASIL CUTTING (DIPERBARUI)
    # ==========================================
    def setup_tab_cutting(self):
        self.tab_cutting = QWidget()
        lay = QVBoxLayout(self.tab_cutting)
        
        form_frame = QFrame()
        form_frame.setObjectName("GridPanel")
        form_lay = QGridLayout(form_frame)
        
        self.date_cut = QDateEdit(QDate.currentDate())
        self.date_cut.setCalendarPopup(True)
        
        self.cut_sumber_kain = QComboBox()
        self.cut_sumber_kain.setStyleSheet(f"background-color: {Theme.BG_VOID}; color: {Theme.NEON_CYAN}; font-weight: bold; padding: 5px;")
        
        self.sku_cut = QComboBox()
        self.sku_cut.setEditable(True)
        self.sku_cut.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.sku_cut.lineEdit().setPlaceholderText("Ketik SKU...")
        self.setup_completer(self.sku_cut)
        
        self.qty_cut = QSpinBox()
        self.qty_cut.setRange(1, 99999)
        
        self.btn_submit_cut = CyberButton("SIMPAN CUTTING")
        self.btn_submit_cut.clicked.connect(self.submit_cutting)
        
        self.btn_reset_cut = CyberButton("BATAL EDIT")
        self.btn_reset_cut.clicked.connect(self.reset_cutting_form)
        self.btn_reset_cut.hide() # Sembunyikan saat mode normal
        
        # Penataan ulang grid agar lebih rapi
        form_lay.addWidget(QLabel("Tanggal:"), 0, 0)
        form_lay.addWidget(self.date_cut, 0, 1)
        form_lay.addWidget(QLabel("Sumber Kain (Pilih Batch):"), 0, 2)
        form_lay.addWidget(self.cut_sumber_kain, 0, 3, 1, 3) # Memanjang

        form_lay.addWidget(QLabel("SKU Produk:"), 1, 0)
        form_lay.addWidget(self.sku_cut, 1, 1, 1, 2)
        form_lay.addWidget(QLabel("Qty Hasil Potong:"), 1, 3)
        form_lay.addWidget(self.qty_cut, 1, 4)
        form_lay.addWidget(self.btn_submit_cut, 1, 5)
        form_lay.addWidget(self.btn_reset_cut, 1, 6)

        lay.addWidget(form_frame)

        self.table_cutting = CyberTable()
        self.table_cutting.setColumnCount(5)
        self.table_cutting.setHorizontalHeaderLabels(["ID", "Tanggal", "Kode Batch", "SKU", "Qty"])
        self.table_cutting.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table_cutting.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_cutting.itemSelectionChanged.connect(self.on_cutting_selected)
        lay.addWidget(self.table_cutting)
        lay.addWidget(self.table_cutting)

    # ==========================================
    # 2. TAB DISTRIBUSI JAHIT (DIPERBARUI)
    # ==========================================
    def setup_tab_distribusi(self):
        self.tab_distribusi = QWidget()
        lay = QVBoxLayout(self.tab_distribusi)
        
        form_frame = QFrame()
        form_frame.setObjectName("GridPanel")
        form_lay = QGridLayout(form_frame)
        
        self.date_dist = QDateEdit(QDate.currentDate())
        self.date_dist.setCalendarPopup(True)
        
        self.person_dist = QComboBox()
        self.person_dist.setEditable(True)
        self.person_dist.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.person_dist.lineEdit().setPlaceholderText("Pilih Penjahit/Pengsup...")
        self.setup_completer(self.person_dist)

        # Dropdown untuk memilih Kode Batch
        self.dist_kode_produksi = QComboBox()
        self.dist_kode_produksi.setStyleSheet(f"background-color: {Theme.BG_VOID}; color: {Theme.NEON_CYAN}; font-weight: bold; padding: 5px;")
        self.dist_kode_produksi.currentIndexChanged.connect(self.on_dist_kode_changed)

        # Dropdown List Hasil Cutting
        self.dist_sumber_cutting = QComboBox()
        self.dist_sumber_cutting.setMinimumWidth(300)
        self.dist_sumber_cutting.setStyleSheet(f"background-color: {Theme.BG_VOID}; color: {Theme.TEXT_MAIN}; padding: 5px;")
        self.dist_sumber_cutting.currentIndexChanged.connect(self.on_dist_sumber_changed)
        
        self.qty_dist = QSpinBox()
        self.qty_dist.setRange(1, 99999)
        self.qty_dist.setStyleSheet(f"background-color: {Theme.BG_VOID}; color: {Theme.NEON_YELLOW}; font-weight: bold;")
        
        self.btn_submit_dist = CyberButton("SIMPAN DISTRIBUSI")
        self.btn_submit_dist.clicked.connect(self.submit_distribusi)
        
        self.btn_reset_dist = CyberButton("BATAL EDIT")
        self.btn_reset_dist.clicked.connect(self.reset_cutting_form)
        self.btn_reset_dist.hide()

        # Penataan layout grid baru
        form_lay.addWidget(QLabel("Tanggal:"), 0, 0)
        form_lay.addWidget(self.date_dist, 0, 1)
        form_lay.addWidget(QLabel("Penerima:"), 0, 2)
        form_lay.addWidget(self.person_dist, 0, 3, 1, 2)
        
        form_lay.addWidget(QLabel("Filter Kode Batch:"), 1, 0)
        form_lay.addWidget(self.dist_kode_produksi, 1, 1)
        form_lay.addWidget(QLabel("List Batch Cutting:"), 1, 2)
        form_lay.addWidget(self.dist_sumber_cutting, 1, 3, 1, 2) # Memanjang

        form_lay.addWidget(QLabel("Qty Diambil:"), 2, 2)
        form_lay.addWidget(self.qty_dist, 2, 3)
        form_lay.addWidget(self.btn_submit_dist, 2, 4)
        form_lay.addWidget(self.btn_reset_dist, 2, 5)

        lay.addWidget(form_frame)

        self.table_distribusi = CyberTable()
        self.table_distribusi.setColumnCount(7)
        self.table_distribusi.setHorizontalHeaderLabels(["ID", "Tanggal", "Penerima", "Jenis", "Kode Batch", "SKU", "Qty"])
        self.table_distribusi.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table_distribusi.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_distribusi.itemSelectionChanged.connect(self.on_distribusi_selected)
        lay.addWidget(self.table_distribusi)

    # ==========================================
    # 3. TAB PENGELUARAN OFFLINE (Tetap)
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
        
        self.btn_reset_off = CyberButton("BATAL EDIT")
        self.btn_reset_off.clicked.connect(self.reset_offline_form)
        self.btn_reset_off.hide()

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
        form_lay.addWidget(self.btn_reset_off, 1, 6)
        
        form_lay.addWidget(self.btn_submit_off, 2, 4, 1, 2)
        lay.addWidget(form_frame)

        self.table_offline = CyberTable()
        self.table_offline.setColumnCount(7)
        self.table_offline.setHorizontalHeaderLabels(["ID", "Tanggal", "Pembeli", "SKU", "Qty", "Harga", "Total"])
        self.table_offline.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table_offline.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_offline.itemSelectionChanged.connect(self.on_offline_selected)
        lay.addWidget(self.table_offline)

    def calculate_offline_total(self):
        self.total_off.setValue(self.qty_off.value() * self.harga_off.value())

    # ==========================================
    # 4. TAB MODAL OPERASIONAL (Tetap)
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
        
        self.btn_reset_op = CyberButton("BATAL EDIT")
        self.btn_reset_op.clicked.connect(self.reset_operasional_form)
        self.btn_reset_op.hide()

        form_lay.addWidget(QLabel("Tanggal:"))
        form_lay.addWidget(self.date_op)
        form_lay.addWidget(QLabel("  Jenis:"))
        form_lay.addWidget(self.jenis_op)
        form_lay.addWidget(QLabel("  Keterangan:"))
        form_lay.addWidget(self.ket_op, stretch=1)
        form_lay.addWidget(QLabel("  Nominal Total:"))
        form_lay.addWidget(self.nominal_op)
        form_lay.addWidget(self.btn_submit_op)
        form_lay.addWidget(self.btn_reset_op)
        
        lay.addWidget(form_frame)

        self.table_operasional = CyberTable()
        self.table_operasional.setColumnCount(5)
        self.table_operasional.setHorizontalHeaderLabels(["ID", "Tanggal", "Kategori", "Keterangan", "Nominal / Total"])
        self.table_operasional.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table_operasional.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_operasional.itemSelectionChanged.connect(self.on_operasional_selected)
        lay.addWidget(self.table_operasional)

    # --- DATA LOADERS ---
    def load_skus(self):
        self.sku_cut.clear()
        self.sku_off.clear()
        
        # Tambahkan placeholder agar tidak kosong
        self.sku_cut.addItem("-- Ketik/Pilih SKU --", None)
        self.sku_off.addItem("-- Ketik/Pilih SKU --", None)
        
        # Hapus filter is_active agar semua data terbaca paksa
        skus = self.db.query(SkuMaster).order_by(SkuMaster.kode_sku).all()
        for sku in skus:
            # Bungkus dengan str() agar kebal terhadap SKU berupa angka
            kode_teks = str(sku.kode_sku) if sku.kode_sku else "NO-KODE"
            self.sku_cut.addItem(kode_teks, sku.id)
            self.sku_off.addItem(kode_teks, sku.id)

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
            
            kode_prod = getattr(rec, 'kode_produksi', None)
            item_kode = QTableWidgetItem(kode_prod if kode_prod else "-")
            item_kode.setForeground(Qt.GlobalColor.cyan)
            self.table_cutting.setItem(row, 2, item_kode)
            
            self.table_cutting.setItem(row, 3, QTableWidgetItem(rec.sku.kode_sku if rec.sku else "Unknown"))
            
            qty_item = QTableWidgetItem(str(rec.qty))
            qty_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table_cutting.setItem(row, 4, qty_item)

    def load_distribusi(self):
        records = self.db.query(DistribusiCutting).order_by(DistribusiCutting.tanggal.desc(), DistribusiCutting.id.desc()).limit(100).all()
        self.table_distribusi.setRowCount(len(records))
        for row, rec in enumerate(records):
            self.table_distribusi.setItem(row, 0, QTableWidgetItem(str(rec.id)))
            self.table_distribusi.setItem(row, 1, QTableWidgetItem(rec.tanggal))
            self.table_distribusi.setItem(row, 2, QTableWidgetItem(rec.person.nama if rec.person else "Unknown"))
            self.table_distribusi.setItem(row, 3, QTableWidgetItem(rec.jenis))
            
            kode_prod = getattr(rec, 'kode_produksi', None)
            item_kode = QTableWidgetItem(kode_prod if kode_prod else "-")
            item_kode.setForeground(Qt.GlobalColor.cyan)
            self.table_distribusi.setItem(row, 4, item_kode)
            
            self.table_distribusi.setItem(row, 5, QTableWidgetItem(rec.sku.kode_sku if rec.sku else "Unknown"))
            qty_item = QTableWidgetItem(str(rec.qty))
            qty_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table_distribusi.setItem(row, 6, qty_item)

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

    # --- DYNAMIC DROPDOWNS HANDLING ---
    def load_sumber_dropdowns(self):
        """Memuat list kain untuk Hasil Cutting & list kode batch untuk Distribusi."""
        # 1. Combo Sumber Kain (Menu Cutting)
        self.cut_sumber_kain.clear()
        self.cut_sumber_kain.addItem("-- Pilih Sumber Kain --", None)
        kain_aktif = self.db.query(DebtEntry).filter(
            DebtEntry.tipe_hutang == 'MODAL', DebtEntry.status_cutting == 'OPEN'
        ).all()
        for k in kain_aktif:
            kode = getattr(k, 'kode_produksi', 'NO-KODE') or 'NO-KODE'
            self.cut_sumber_kain.addItem(f"[{kode}] {k.keterangan} (Rp {k.nominal_hutang:,.0f})", k.id)

        # 2. Combo Kode Batch (Menu Distribusi)
        self.dist_kode_produksi.blockSignals(True)
        self.dist_kode_produksi.clear()
        self.dist_kode_produksi.addItem("-- Pilih Kode Batch --", None)
        
        # Cari semua kode produksi unik dari Hasil Cutting
        kodes = self.db.query(HasilCutting.kode_produksi).filter(HasilCutting.kode_produksi.isnot(None)).distinct().all()
        for k in kodes:
            if k[0]: self.dist_kode_produksi.addItem(k[0], k[0])
            
        self.dist_kode_produksi.blockSignals(False)
        self.on_dist_kode_changed()
    
    # ==========================================
    # FUNGSI HANDLER EDIT & RESET CUTTING
    # ==========================================
    def on_cutting_selected(self):
        selected = self.table_cutting.selectedItems()
        if not selected: return
        row = selected[0].row()
        
        # Ambil ID dari kolom pertama (hidden/visible index 0)
        self.selected_cut_id = int(self.table_cutting.item(row, 0).text())
        
        # Ambil data dari DB untuk mengisi form
        record = self.db.query(HasilCutting).get(self.selected_cut_id)
        if record:
            self.date_cut.setDate(QDate.fromString(record.tanggal, "yyyy-MM-dd"))
            
            idx_sumber = self.cut_sumber_kain.findData(record.modal_hutang_id)
            if idx_sumber >= 0: self.cut_sumber_kain.setCurrentIndex(idx_sumber)
            
            idx_sku = self.sku_cut.findData(record.sku_id)
            if idx_sku >= 0: self.sku_cut.setCurrentIndex(idx_sku)
            
            self.qty_cut.setValue(record.qty)
            
            # Ubah state UI
            self.btn_submit_cut.setText("UPDATE CUTTING")
            self.btn_reset_cut.show()

    def reset_cutting_form(self):
        self.selected_cut_id = None
        self.qty_cut.setValue(0)
        self.cut_sumber_kain.setCurrentIndex(0)
        self.sku_cut.setCurrentIndex(0)
        self.btn_submit_cut.setText("SIMPAN CUTTING")
        self.btn_reset_cut.hide()
        self.table_cutting.clearSelection()
    
    # ==========================================
    # FUNGSI HANDLER EDIT & RESET DISTRIBUSI
    # ==========================================
    def on_distribusi_selected(self):
        selected = self.table_distribusi.selectedItems()
        if not selected: return
        row = selected[0].row()
        
        # Ambil ID Distribusi
        self.selected_dist_id = int(self.table_distribusi.item(row, 0).text())
        
        record = self.db.query(DistribusiCutting).get(self.selected_dist_id)
        if record:
            # 1. Set Tanggal & Penerima
            self.date_dist.setDate(QDate.fromString(record.tanggal, "yyyy-MM-dd"))
            idx_person = self.person_dist.findData(record.person_id)
            if idx_person >= 0: self.person_dist.setCurrentIndex(idx_person)
            
            # 2. Block Signal agar tidak memicu reset Qty otomatis saat dropdown berubah
            self.dist_kode_produksi.blockSignals(True)
            self.dist_sumber_cutting.blockSignals(True)
            
            # 3. Set Kode Produksi
            idx_kode = self.dist_kode_produksi.findData(record.kode_produksi)
            if idx_kode >= 0: self.dist_kode_produksi.setCurrentIndex(idx_kode)
            
            # 4. KUSTOMISASI DROPDOWN SUMBER CUTTING
            # Kita buat manual list dropdown-nya agar item yang sedang diedit Qty-nya 
            # dikembalikan dulu ke pool sisa, sehingga bisa terbaca di form.
            self.dist_sumber_cutting.clear()
            self.dist_sumber_cutting.addItem("-- Pilih List Cutting --", None)
            
            cuttings = self.db.query(HasilCutting).filter(HasilCutting.kode_produksi == record.kode_produksi).all()
            for c in cuttings:
                distribusis = self.db.query(DistribusiCutting).filter(DistribusiCutting.hasil_cutting_id == c.id).all()
                # Abaikan distribusi yang sedang di-edit ini saat menghitung barang terpakai
                terpakai = sum(d.qty for d in distribusis if d.id != self.selected_dist_id)
                sisa_tersedia_untuk_edit = c.qty - terpakai
                
                if sisa_tersedia_untuk_edit > 0:
                    sku_nama = c.sku.nama_produk if c.sku else "Unknown SKU"
                    self.dist_sumber_cutting.addItem(f"{sku_nama} (Max {sisa_tersedia_untuk_edit} Pcs)", c.id)
            
            # 5. Set Dropdown Sumber Cutting
            idx_sumber = self.dist_sumber_cutting.findData(record.hasil_cutting_id)
            if idx_sumber >= 0: self.dist_sumber_cutting.setCurrentIndex(idx_sumber)
            
            # Buka kembali signal
            self.dist_kode_produksi.blockSignals(False)
            self.dist_sumber_cutting.blockSignals(False)
            
            # 6. Set Qty 
            self.qty_dist.setValue(record.qty)
            
            # 7. Update UI Buttons
            self.btn_submit_dist.setText("UPDATE DISTRIBUSI")
            self.btn_reset_dist.show()

    def reset_distribusi_form(self):
        self.selected_dist_id = None
        self.qty_dist.setValue(0)
        self.person_dist.setCurrentIndex(0)
        self.dist_kode_produksi.setCurrentIndex(0) # Ini otomatis akan mereset list sumber cutting
        self.btn_submit_dist.setText("SIMPAN DISTRIBUSI")
        self.btn_reset_dist.hide()
        self.table_distribusi.clearSelection()

    # ==========================================
    # FUNGSI HANDLER EDIT & RESET OFFLINE
    # ==========================================
    def on_offline_selected(self):
        selected = self.table_offline.selectedItems()
        if not selected: return
        row = selected[0].row()
        self.selected_off_id = int(self.table_offline.item(row, 0).text())
        
        record = self.db.query(PengeluaranOffline).get(self.selected_off_id)
        if record:
            self.date_off.setDate(QDate.fromString(record.tanggal, "yyyy-MM-dd"))
            
            idx_person = self.person_off.findData(record.person_id)
            if idx_person >= 0: self.person_off.setCurrentIndex(idx_person)
            
            idx_sku = self.sku_off.findData(record.sku_id)
            if idx_sku >= 0: self.sku_off.setCurrentIndex(idx_sku)
            
            self.qty_off.setValue(record.qty)
            self.harga_off.setValue(record.harga_satuan)
            self.total_off.setValue(record.total)
            
            self.btn_submit_off.setText("UPDATE PENJUALAN")
            self.btn_reset_off.show()

    def reset_offline_form(self):
        self.selected_off_id = None
        self.qty_off.setValue(0)
        self.harga_off.setValue(0)
        self.person_off.setCurrentIndex(0)
        self.sku_off.setCurrentIndex(0)
        self.btn_submit_off.setText("SIMPAN PENJUALAN")
        self.btn_reset_off.hide()
        self.table_offline.clearSelection()

    # ==========================================
    # FUNGSI HANDLER EDIT & RESET OPERASIONAL
    # ==========================================
    def on_operasional_selected(self):
        selected = self.table_operasional.selectedItems()
        if not selected: return
        row = selected[0].row()
        self.selected_op_id = int(self.table_operasional.item(row, 0).text())
        
        record = self.db.query(ModalOperasional).get(self.selected_op_id)
        if record:
            self.date_op.setDate(QDate.fromString(record.tanggal, "yyyy-MM-dd"))
            
            idx_jenis = self.jenis_op.findText(record.jenis)
            if idx_jenis >= 0: self.jenis_op.setCurrentIndex(idx_jenis)
            
            self.ket_op.setText(record.keterangan)
            self.nominal_op.setValue(record.nominal)
            
            self.btn_submit_op.setText("UPDATE PENGELUARAN")
            self.btn_reset_op.show()

    def reset_operasional_form(self):
        self.selected_op_id = None
        self.ket_op.clear()
        self.nominal_op.setValue(0)
        self.jenis_op.setCurrentIndex(0)
        self.btn_submit_op.setText("SIMPAN PENGELUARAN")
        self.btn_reset_op.hide()
        self.table_operasional.clearSelection()

    def on_dist_kode_changed(self):
        """Otomatis memfilter Batch Cutting saat Kode Batch dipilih."""
        kode_terpilih = self.dist_kode_produksi.currentData()
        
        self.dist_sumber_cutting.blockSignals(True)
        self.dist_sumber_cutting.clear()
        self.dist_sumber_cutting.addItem("-- Pilih List Cutting --", None)
        self.qty_dist.setValue(0)
        
        if kode_terpilih:
            cuttings = self.db.query(HasilCutting).filter(HasilCutting.kode_produksi == kode_terpilih).all()
            for c in cuttings:
                # Hitung sisa potongan yang belum didistribusikan
                distribusis = self.db.query(DistribusiCutting).filter(DistribusiCutting.hasil_cutting_id == c.id).all()
                terpakai = sum(d.qty for d in distribusis)
                sisa = c.qty - terpakai
                
                if sisa > 0:
                    sku_nama = c.sku.nama_produk if c.sku else "Unknown SKU"
                    # Format tampilan: SKU (Sisa 100 dari 150 Pcs)
                    self.dist_sumber_cutting.addItem(f"{sku_nama} (Sisa {sisa} Pcs)", c.id)
                    
        self.dist_sumber_cutting.blockSignals(False)

    def on_dist_sumber_changed(self):
        """Otomatis mengisi form Qty berdasarkan sisa List Cutting yang dipilih."""
        cutting_id = self.dist_sumber_cutting.currentData()
        if cutting_id:
            c = self.db.query(HasilCutting).get(cutting_id)
            if c:
                distribusis = self.db.query(DistribusiCutting).filter(DistribusiCutting.hasil_cutting_id == c.id).all()
                terpakai = sum(d.qty for d in distribusis)
                sisa = c.qty - terpakai
                self.qty_dist.setValue(sisa) # Auto-fill, tapi masih bisa diedit manual oleh user
        else:
            self.qty_dist.setValue(0)

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
        modal_id = self.cut_sumber_kain.currentData()
        
        if not sku_id or not modal_id: 
            return QMessageBox.warning(self, "Error", "Pilih Sumber Kain dan SKU!")
            
        try:
            debt = self.db.query(DebtEntry).get(modal_id)
            kode_batch_otomatis = getattr(debt, 'kode_produksi', None)
            
            if self.selected_cut_id:
                # --- MODE UPDATE ---
                cut_entry = self.db.query(HasilCutting).get(self.selected_cut_id)
                cut_entry.tanggal = self.date_cut.date().toString("yyyy-MM-dd")
                cut_entry.sku_id = sku_id
                cut_entry.qty = self.qty_cut.value()
                cut_entry.modal_hutang_id = modal_id
                cut_entry.kode_produksi = kode_batch_otomatis
                msg = "Data Cutting berhasil diperbarui!"
            else:
                # --- MODE INSERT ---
                cut_entry = HasilCutting(
                    tanggal=self.date_cut.date().toString("yyyy-MM-dd"),
                    sku_id=sku_id,
                    qty=self.qty_cut.value(),
                    modal_hutang_id=modal_id,
                    kode_produksi=kode_batch_otomatis
                )
                self.db.add(cut_entry)
                msg = "Data Cutting berhasil disimpan!"
                
            self.db.commit()
            
            self.load_hasil_cutting()
            self.load_sumber_dropdowns()
            self.reset_cutting_form() # Panggil reset form
            QMessageBox.information(self, "Sukses", msg)
            
        except Exception as e:
            self.db.rollback()
            QMessageBox.critical(self, "Error", f"Gagal menyimpan: {e}")

    def submit_distribusi(self):
        person_id = self.get_valid_combo_data(self.person_dist, "Penerima tidak ditemukan! Pilih dari daftar.")
        cutting_id = self.dist_sumber_cutting.currentData()
        
        if not person_id or not cutting_id: 
            return QMessageBox.warning(self, "Error", "Pilih Penerima dan List Batch Cutting!")
            
        qty_input = self.qty_dist.value()
        if qty_input <= 0:
            return QMessageBox.warning(self, "Error", "Jumlah Distribusi tidak boleh nol!")
            
        try:
            c_record = self.db.query(HasilCutting).get(cutting_id)
            person_record = self.db.query(Person).get(person_id)
            jenis_pekerjaan = person_record.person_type if person_record else 'PENJAHIT'
            
            if getattr(self, 'selected_dist_id', None):
                # --- MODE UPDATE ---
                dist_entry = self.db.query(DistribusiCutting).get(self.selected_dist_id)
                dist_entry.tanggal = self.date_dist.date().toString("yyyy-MM-dd")
                dist_entry.person_id = person_id
                dist_entry.jenis = jenis_pekerjaan
                dist_entry.sku_id = c_record.sku_id
                dist_entry.qty = qty_input
                dist_entry.hasil_cutting_id = cutting_id
                dist_entry.kode_produksi = c_record.kode_produksi
                msg = "Data Distribusi berhasil diperbarui!"
            else:
                # --- MODE INSERT ---
                dist_entry = DistribusiCutting(
                    tanggal=self.date_dist.date().toString("yyyy-MM-dd"),
                    person_id=person_id,
                    jenis=jenis_pekerjaan,
                    sku_id=c_record.sku_id, 
                    qty=qty_input,
                    hasil_cutting_id=cutting_id,
                    kode_produksi=c_record.kode_produksi 
                )
                self.db.add(dist_entry)
                msg = "Data Distribusi berhasil disimpan!"

            self.db.commit()
            
            self.load_distribusi()
            self.on_dist_kode_changed() # Refresh dropdown sisa qty otomatis
            self.reset_distribusi_form() # Reset Form setelah sukses
            self.person_dist.lineEdit().clear()
            QMessageBox.information(self, "Sukses", msg)
            
        except Exception as e:
            self.db.rollback()
            QMessageBox.critical(self, "Error", f"Gagal menyimpan: {e}")

    def submit_offline(self):
        person_id = self.get_valid_combo_data(self.person_off, "Pembeli tidak ditemukan! Pilih Klien dari daftar.")
        sku_id = self.get_valid_combo_data(self.sku_off, "SKU tidak ditemukan!")
        if not person_id or not sku_id: return
        
        try:
            if self.selected_off_id:
                record = self.db.query(PengeluaranOffline).get(self.selected_off_id)
                record.tanggal = self.date_off.date().toString("yyyy-MM-dd")
                record.person_id = person_id
                record.sku_id = sku_id
                record.qty = self.qty_off.value()
                record.harga_satuan = self.harga_off.value()
                record.total = self.total_off.value()
                msg = "Data Penjualan berhasil diperbarui!"
            else:
                record = PengeluaranOffline(
                    tanggal=self.date_off.date().toString("yyyy-MM-dd"), 
                    person_id=person_id, 
                    sku_id=sku_id,
                    qty=self.qty_off.value(), 
                    harga_satuan=self.harga_off.value(), 
                    total=self.total_off.value(), 
                    catatan="Manual Input"
                )
                self.db.add(record)
                msg = "Data Penjualan berhasil disimpan!"
                
            self.db.commit()
            self.load_offline()
            self.reset_offline_form()
            QMessageBox.information(self, "Sukses", msg)
            
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
            if getattr(self, 'selected_op_id', None):
                # --- MODE UPDATE ---
                record = self.db.query(ModalOperasional).get(self.selected_op_id)
                record.tanggal = self.date_op.date().toString("yyyy-MM-dd")
                record.jenis = self.jenis_op.currentText()
                record.keterangan = keterangan
                record.nominal = nominal
                msg = "Data Pengeluaran Operasional berhasil diperbarui!"
            else:
                # --- MODE INSERT ---
                record = ModalOperasional(
                    tanggal=self.date_op.date().toString("yyyy-MM-dd"),
                    jenis=self.jenis_op.currentText(),
                    keterangan=keterangan,
                    nominal=nominal,
                    catatan="Manual Input"
                )
                self.db.add(record)
                msg = "Data Pengeluaran Operasional berhasil disimpan!"
                
            self.db.commit()
            
            self.load_operasional()
            self.reset_operasional_form() # Panggil fungsi reset form setelah sukses
            QMessageBox.information(self, "Sukses", msg)
            
        except Exception as e:
            self.db.rollback()
            QMessageBox.critical(self, "Error", f"Gagal menyimpan: {e}")
            
    def closeEvent(self, event):
        self.db.close()
        super().closeEvent(event)