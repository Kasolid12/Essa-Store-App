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
from data.models.debt import DebtEntry

class CatatanHarianView(QWidget):
    def __init__(self):
        super().__init__()
        self.db = SessionLocal()
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

        lay.addWidget(form_frame)

        self.table_cutting = CyberTable()
        self.table_cutting.setColumnCount(5)
        self.table_cutting.setHorizontalHeaderLabels(["ID", "Tanggal", "Kode Batch", "SKU", "Qty"])
        self.table_cutting.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
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

        lay.addWidget(form_frame)

        self.table_distribusi = CyberTable()
        self.table_distribusi.setColumnCount(7)
        self.table_distribusi.setHorizontalHeaderLabels(["ID", "Tanggal", "Penerima", "Jenis", "Kode Batch", "SKU", "Qty"])
        self.table_distribusi.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
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
        
        form_lay.addWidget(self.btn_submit_off, 2, 4, 1, 2)
        lay.addWidget(form_frame)

        self.table_offline = CyberTable()
        self.table_offline.setColumnCount(7)
        self.table_offline.setHorizontalHeaderLabels(["ID", "Tanggal", "Pembeli", "SKU", "Qty", "Harga", "Total"])
        self.table_offline.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
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
        self.on_dist_kode_changed() # Trigger untuk mereset daftar list cutting di sebelahnya

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
            # Ambil otomatis Kode Batch dari data hutang kain
            debt = self.db.query(DebtEntry).get(modal_id)
            kode_batch_otomatis = getattr(debt, 'kode_produksi', None)
            
            cut_entry = HasilCutting(
                tanggal=self.date_cut.date().toString("yyyy-MM-dd"),
                sku_id=sku_id,
                qty=self.qty_cut.value(),
                modal_hutang_id=modal_id,
                kode_produksi=kode_batch_otomatis # Simpan otomatis
            )
            self.db.add(cut_entry)
            self.db.commit()
            
            self.load_hasil_cutting()
            self.load_sumber_dropdowns()
            self.qty_cut.setValue(0)
            self.sku_cut.lineEdit().clear()
            QMessageBox.information(self, "Sukses", "Data Cutting berhasil disimpan!")
            
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
            
            dist_entry = DistribusiCutting(
                tanggal=self.date_dist.date().toString("yyyy-MM-dd"),
                person_id=person_id,
                jenis=jenis_pekerjaan,
                sku_id=c_record.sku_id, # SKU otomatis diambil dari Hasil Cutting
                qty=qty_input,
                hasil_cutting_id=cutting_id,
                kode_produksi=c_record.kode_produksi # Kode Produksi otomatis
            )
            self.db.add(dist_entry)
            self.db.commit()
            
            self.load_distribusi()
            self.on_dist_kode_changed() # Refresh dropdown sisa qty otomatis
            self.person_dist.lineEdit().clear()
            QMessageBox.information(self, "Sukses", "Data Distribusi berhasil disimpan!")
            
        except Exception as e:
            self.db.rollback()
            QMessageBox.critical(self, "Error", f"Gagal menyimpan: {e}")

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