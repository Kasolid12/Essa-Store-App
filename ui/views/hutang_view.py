# app_essa/ui/views/hutang_view.py
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTabWidget, 
    QTableWidgetItem, QHeaderView, QComboBox, QSpinBox, 
    QDateEdit, QMessageBox, QFrame, QDoubleSpinBox, QCompleter, QGridLayout,
    QAbstractItemView, QLineEdit
)
import os
from utils.pdf_engine import generate_batch_receipt_pdf
from PySide6.QtCore import Qt, QDate, QTimer

from ui.components.tables import CyberTable
from ui.components.buttons import CyberButton
from ui.theme import Theme
from data.database import SessionLocal
from data.models import DebtEntry, DebtPayment, Person, SkuMaster

class HutangView(QWidget):
    def __init__(self, notifier=None):
        super().__init__()
        self.db = SessionLocal()
        self.notifier = notifier
        self.selected_barang_debt_ids = [] 
        self.selected_modal_debt_ids = []
        self.selected_barang_edit_id = None 
        
        self.setup_ui()
        self.load_dropdowns()
        self.load_barang_terhutang()
        self.load_modal_hutang()
        self.generate_kode_produksi()
        
        if self.notifier:
            self.notifier.database_changed.connect(self.refresh_hutang_view)

    def refresh_hutang_view(self):
        self.db.expire_all()
        if hasattr(self, 'load_dropdowns'): self.load_dropdowns()
        if hasattr(self, 'load_barang_terhutang'): self.load_barang_terhutang()
        if hasattr(self, 'load_modal_hutang'): self.load_modal_hutang()
        if hasattr(self, 'apply_search_filter'):
            self.apply_search_filter()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        header_layout = QHBoxLayout()
        title = QLabel("HUTANG & PELUNASAN MANAGER")
        title.setStyleSheet(f"font-size: 24pt; font-weight: bold; color: {Theme.NEON_CYAN};")
        header_layout.addWidget(title)
        header_layout.addStretch()

        # Search bar global — filter sesuai tab yang sedang aktif
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Cari data...")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {Theme.BG_VOID};
                color: {Theme.TEXT_MAIN};
                border: 1px solid {Theme.BORDER_DIM};
                border-radius: 6px;
                padding: 8px 15px;
                font-size: 12pt;
                min-width: 250px;
            }}
            QLineEdit:focus {{
                border: 1px solid {Theme.NEON_CYAN};
            }}
        """)
        header_layout.addWidget(self.search_input)
        layout.addLayout(header_layout)

        # Debounce timer untuk search (300ms)
        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self.apply_search_filter)
        self.search_input.textChanged.connect(self.on_search_text_changed)

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

        self.setup_tab_barang()
        self.setup_tab_modal()

        self.tabs.addTab(self.tab_barang, "BARANG TERHUTANG")
        self.tabs.addTab(self.tab_modal, "MODAL HUTANG")
        self.tabs.currentChanged.connect(self.on_tab_changed)
        layout.addWidget(self.tabs)

    # ==========================================
    # SEARCH GLOBAL (debounce 300ms)
    # ==========================================
    def on_search_text_changed(self):
        """Mulai timer debounce saat teks search berubah."""
        self.search_timer.start(300)

    def apply_search_filter(self):
        """Filter tabel sesuai tab yang aktif berdasarkan teks search."""
        search_text = self.search_input.text().strip().lower()
        idx = self.tabs.currentIndex()

        if idx == 0:
            table = self.table_barang
        elif idx == 1:
            table = self.table_modal
        else:
            return

        self._filter_table(table, search_text)

    def _filter_table(self, table, search_text):
        """Tampilkan baris yang cocok dengan search_text (case-insensitive)."""
        if not search_text:
            for row in range(table.rowCount()):
                table.setRowHidden(row, False)
            return

        for row in range(table.rowCount()):
            found = False
            for col in range(table.columnCount()):
                item = table.item(row, col)
                if item and item.text():
                    if search_text in item.text().lower():
                        found = True
                        break
            table.setRowHidden(row, not found)

    def on_tab_changed(self, index):
        """Re-filter saat pindah tab agar search tetap berlaku."""
        self.apply_search_filter()

    def setup_completer(self, combobox):
        completer = combobox.completer()
        if completer:
            completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
            completer.setFilterMode(Qt.MatchFlag.MatchContains)
            completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)

    # ==========================================
    # 1. TAB BARANG TERHUTANG (Tetap Sama)
    # ==========================================
    def setup_tab_barang(self):
        self.tab_barang = QWidget()
        lay = QVBoxLayout(self.tab_barang)
        
        lbl_hint = QLabel("TAHAN CTRL atau SHIFT untuk memilih banyak hutang sekaligus!")
        lbl_hint.setStyleSheet(f"color: {Theme.NEON_PINK}; font-style: italic;")
        lay.addWidget(lbl_hint)

        self.table_barang = CyberTable()
        self.table_barang.setColumnCount(8)
        self.table_barang.setHorizontalHeaderLabels(["ID", "Tgl Ambil", "Supplier", "SKU", "Qty", "Total Hutang", "Terbayar", "Status"])
        self.table_barang.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_barang.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table_barang.itemSelectionChanged.connect(self.on_barang_selected)
        lay.addWidget(self.table_barang, stretch=2)

        bottom_lay = QHBoxLayout()
        
        frame_baru = QFrame()
        frame_baru.setObjectName("GridPanel")
        lay_baru = QGridLayout(frame_baru)
        
        self.lbl_title_brg = QLabel("CATAT HUTANG BARU")
        self.lbl_title_brg.setStyleSheet(f"color:{Theme.NEON_CYAN}; font-weight:bold;")
        lay_baru.addWidget(self.lbl_title_brg, 0, 0, 1, 2)
        
        self.brg_date = QDateEdit(QDate.currentDate()); self.brg_date.setCalendarPopup(True)
        self.brg_person = QComboBox(); self.brg_person.setEditable(True); self.brg_person.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.setup_completer(self.brg_person)
        
        self.brg_sku = QComboBox(); self.brg_sku.setEditable(True); self.brg_sku.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.setup_completer(self.brg_sku)
        
        self.brg_qty = QDoubleSpinBox()
        self.brg_qty.setDecimals(2)
        self.brg_qty.setRange(0, 9999999.99)
        
        self.brg_harga = QDoubleSpinBox()
        self.brg_harga.setRange(0, 999999999)
        self.brg_harga.setPrefix("Rp ")
        
        self.brg_qty.valueChanged.connect(self.calc_brg_total)
        self.brg_harga.valueChanged.connect(self.calc_brg_total)
        
        self.brg_total = QDoubleSpinBox()
        self.brg_total.setRange(0, 999999999)
        self.brg_total.setPrefix("Rp ")
        self.brg_total.setReadOnly(True)
        self.brg_total.setStyleSheet(f"background-color: {Theme.BG_VOID}; color: {Theme.NEON_PINK}; font-weight: bold;")
        self.brg_total.buttonSymbols = QDoubleSpinBox.ButtonSymbols.NoButtons
        
        brg_btn_lay = QHBoxLayout()
        self.btn_simpan_brg = CyberButton("SIMPAN BARU")
        self.btn_simpan_brg.clicked.connect(self.submit_barang_hutang)
        self.btn_reset_brg = CyberButton("RESET")
        self.btn_reset_brg.clicked.connect(self.reset_barang_form)
        self.btn_delete_brg = CyberButton("HAPUS", is_danger=True)
        self.btn_delete_brg.clicked.connect(self.delete_barang_hutang)
        self.btn_delete_brg.setEnabled(False)

        brg_btn_lay.addWidget(self.btn_simpan_brg)
        brg_btn_lay.addWidget(self.btn_reset_brg)
        brg_btn_lay.addWidget(self.btn_delete_brg)

        lay_baru.addWidget(QLabel("Tanggal:"), 1, 0); lay_baru.addWidget(self.brg_date, 1, 1)
        lay_baru.addWidget(QLabel("Supplier:"), 2, 0); lay_baru.addWidget(self.brg_person, 2, 1)
        lay_baru.addWidget(QLabel("SKU:"), 3, 0); lay_baru.addWidget(self.brg_sku, 3, 1)
        lay_baru.addWidget(QLabel("Qty / Jumlah:"), 4, 0); lay_baru.addWidget(self.brg_qty, 4, 1)
        lay_baru.addWidget(QLabel("Harga Satuan:"), 5, 0); lay_baru.addWidget(self.brg_harga, 5, 1)
        lay_baru.addWidget(QLabel("Total Hutang:"), 6, 0); lay_baru.addWidget(self.brg_total, 6, 1)
        lay_baru.addLayout(brg_btn_lay, 7, 0, 1, 2)
        
        bottom_lay.addWidget(frame_baru, stretch=1)
        
        frame_lunas = QFrame()
        frame_lunas.setObjectName("GridPanel")
        lay_lunas = QVBoxLayout(frame_lunas)
        
        self.lbl_selected_brg = QLabel("PILIH HUTANG UNTUK MELUNASI (Bisa Lebih Dari 1)")
        self.lbl_selected_brg.setStyleSheet(f"color: {Theme.NEON_YELLOW}; font-weight: bold;")
        lay_lunas.addWidget(self.lbl_selected_brg)
        
        form_lunas = QGridLayout()
        self.brg_lunas_date = QDateEdit(QDate.currentDate()); self.brg_lunas_date.setCalendarPopup(True)
        self.brg_lunas_nom = QDoubleSpinBox(); self.brg_lunas_nom.setRange(0, 999999999); self.brg_lunas_nom.setPrefix("Rp ")
        
        self.btn_brg_lunas = CyberButton("BAYAR / CICIL SEMUA")
        self.btn_brg_lunas.setEnabled(False)
        self.btn_brg_lunas.clicked.connect(self.submit_barang_pelunasan)
        
        self.btn_batal_lunas_brg = CyberButton("BATAL LUNAS (SET OPEN)", is_danger=True)
        self.btn_batal_lunas_brg.setEnabled(False)
        self.btn_batal_lunas_brg.clicked.connect(self.submit_batal_lunas_barang)
        lay_lunas.addWidget(self.btn_batal_lunas_brg)
        
        form_lunas.addWidget(QLabel("Tgl Bayar:"), 0, 0); form_lunas.addWidget(self.brg_lunas_date, 0, 1)
        form_lunas.addWidget(QLabel("Nominal (Otomatis Dibagi):"), 1, 0); form_lunas.addWidget(self.brg_lunas_nom, 1, 1)
        
        lay_lunas.addLayout(form_lunas)
        lay_lunas.addWidget(self.btn_brg_lunas)
        lay_lunas.addStretch()
        
        bottom_lay.addWidget(frame_lunas, stretch=1)
        lay.addLayout(bottom_lay)

    # ==========================================
    # 2. TAB MODAL HUTANG (UPDATED: Tambah Kode Batch)
    # ==========================================
    def setup_tab_modal(self):
        self.tab_modal = QWidget()
        lay = QVBoxLayout(self.tab_modal)
        
        lbl_hint = QLabel("TAHAN CTRL atau SHIFT untuk memilih banyak hutang sekaligus!")
        lbl_hint.setStyleSheet(f"color: {Theme.NEON_PINK}; font-style: italic;")
        lay.addWidget(lbl_hint)
        
        self.table_modal = CyberTable()
        self.table_modal.setColumnCount(8) # Diperbarui: Tambah 1 kolom untuk Kode Batch
        self.table_modal.setHorizontalHeaderLabels(["ID", "Tgl Hutang", "Pemberi Modal", "Kode Batch", "Keterangan", "Total Hutang", "Deposit/Lunas", "Status"])
        self.table_modal.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_modal.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table_modal.itemSelectionChanged.connect(self.on_modal_selected)
        lay.addWidget(self.table_modal, stretch=2)

        bottom_lay = QHBoxLayout()
        
        frame_baru = QFrame()
        frame_baru.setObjectName("GridPanel")
        lay_baru = QGridLayout(frame_baru)
        
        self.lbl_title_mod = QLabel("CATAT PINJAMAN MODAL")
        self.lbl_title_mod.setStyleSheet(f"color:{Theme.NEON_CYAN}; font-weight:bold;")
        lay_baru.addWidget(self.lbl_title_mod, 0, 0, 1, 2)
        
        self.mod_date = QDateEdit(QDate.currentDate()); self.mod_date.setCalendarPopup(True)
        self.mod_date.dateChanged.connect(self.generate_kode_produksi)
        self.mod_person = QComboBox(); self.mod_person.setEditable(True); self.mod_person.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.setup_completer(self.mod_person)
        
        # --- NEW: Kolom Input Kode Produksi/Batch ---
        self.mod_kode_produksi = QLineEdit()
        self.mod_kode_produksi.setPlaceholderText("Misal: PRD-001")
        self.mod_kode_produksi.setStyleSheet(f"background-color: {Theme.BG_VOID}; color: {Theme.NEON_CYAN}; font-weight: bold;")
        
        self.mod_jenis = QComboBox()
        self.mod_jenis.addItems(["Kain Jersey", "Label Akrilik", "Hangtag", "Modal Tunai", "Lainnya"])
        self.mod_jenis.setEditable(True)
        
        self.mod_qty = QDoubleSpinBox()
        self.mod_qty.setDecimals(2)
        self.mod_qty.setRange(0, 9999999.99)
        
        self.mod_harga = QDoubleSpinBox()
        self.mod_harga.setRange(0, 999999999)
        self.mod_harga.setPrefix("Rp ")
        
        self.mod_qty.valueChanged.connect(self.calc_mod_total)
        self.mod_harga.valueChanged.connect(self.calc_mod_total)
        
        self.mod_total = QDoubleSpinBox()
        self.mod_total.setRange(0, 999999999)
        self.mod_total.setPrefix("Rp ")
        self.mod_total.setReadOnly(True)
        self.mod_total.setStyleSheet(f"background-color: {Theme.BG_VOID}; color: {Theme.NEON_PINK}; font-weight: bold;")
        self.mod_total.buttonSymbols = QDoubleSpinBox.ButtonSymbols.NoButtons
        
        mod_btn_lay = QHBoxLayout()
        self.btn_simpan_mod = CyberButton("SIMPAN BARU")
        self.btn_simpan_mod.clicked.connect(self.submit_modal_hutang)
        self.btn_reset_mod = CyberButton("RESET")
        self.btn_reset_mod.clicked.connect(self.reset_modal_form)
        self.btn_delete_mod = CyberButton("HAPUS", is_danger=True)
        self.btn_delete_mod.clicked.connect(self.delete_modal_hutang)
        self.btn_delete_mod.setEnabled(False)

        mod_btn_lay.addWidget(self.btn_simpan_mod)
        mod_btn_lay.addWidget(self.btn_reset_mod)
        mod_btn_lay.addWidget(self.btn_delete_mod)

        # Update Grid Layout Form
        lay_baru.addWidget(QLabel("Tanggal:"), 1, 0); lay_baru.addWidget(self.mod_date, 1, 1)
        lay_baru.addWidget(QLabel("Pemberi Modal:"), 2, 0); lay_baru.addWidget(self.mod_person, 2, 1)
        lay_baru.addWidget(QLabel("Kode Batch:"), 3, 0); lay_baru.addWidget(self.mod_kode_produksi, 3, 1)
        lay_baru.addWidget(QLabel("Jenis/Ket:"), 4, 0); lay_baru.addWidget(self.mod_jenis, 4, 1)
        lay_baru.addWidget(QLabel("Qty / Jumlah:"), 5, 0); lay_baru.addWidget(self.mod_qty, 5, 1)
        lay_baru.addWidget(QLabel("Harga Satuan:"), 6, 0); lay_baru.addWidget(self.mod_harga, 6, 1)
        lay_baru.addWidget(QLabel("Total Hutang:"), 7, 0); lay_baru.addWidget(self.mod_total, 7, 1)
        lay_baru.addLayout(mod_btn_lay, 8, 0, 1, 2)
        
        bottom_lay.addWidget(frame_baru, stretch=1)
        
        frame_lunas = QFrame()
        frame_lunas.setObjectName("GridPanel")
        lay_lunas = QVBoxLayout(frame_lunas)
        
        self.lbl_selected_mod = QLabel("PILIH PINJAMAN UNTUK DEPOSIT (Bisa Lebih Dari 1)")
        self.lbl_selected_mod.setStyleSheet(f"color: {Theme.NEON_YELLOW}; font-weight: bold;")
        lay_lunas.addWidget(self.lbl_selected_mod)
        
        form_lunas = QGridLayout()
        self.mod_lunas_date = QDateEdit(QDate.currentDate()); self.mod_lunas_date.setCalendarPopup(True)
        self.mod_lunas_nom = QDoubleSpinBox(); self.mod_lunas_nom.setRange(0, 999999999); self.mod_lunas_nom.setPrefix("Rp ")
        
        self.btn_mod_lunas = CyberButton("SETOR DEPOSIT SEMUA")
        self.btn_mod_lunas.setEnabled(False)
        self.btn_mod_lunas.clicked.connect(self.submit_modal_pelunasan)
        
        self.btn_batal_lunas_mod = CyberButton("BATAL LUNAS (SET OPEN)", is_danger=True)
        self.btn_batal_lunas_mod.setEnabled(False)
        self.btn_batal_lunas_mod.clicked.connect(self.submit_batal_lunas_modal)
        lay_lunas.addWidget(self.btn_batal_lunas_mod)
        
        form_lunas.addWidget(QLabel("Tgl Deposit:"), 0, 0); form_lunas.addWidget(self.mod_lunas_date, 0, 1)
        form_lunas.addWidget(QLabel("Nominal (Otomatis Dibagi):"), 1, 0); form_lunas.addWidget(self.mod_lunas_nom, 1, 1)
        
        lay_lunas.addLayout(form_lunas)
        lay_lunas.addWidget(self.btn_mod_lunas)
        lay_lunas.addStretch()
        
        bottom_lay.addWidget(frame_lunas, stretch=1)
        lay.addLayout(bottom_lay)

    def load_dropdowns(self):
        # 1. REKAM STATE / PILIHAN SAAT INI SEBELUM DI-CLEAR
        current_brg_person_id = self.brg_person.currentData()
        current_mod_person_id = self.mod_person.currentData()
        current_brg_sku_id = self.brg_sku.currentData()

        # 2. CLEAR DAN RELOAD DATA DARI DATABASE
        self.brg_person.clear()
        self.mod_person.clear()
        persons = self.db.query(Person).filter(Person.person_type.in_(['SUPPLIER', 'LAINNYA'])).order_by(Person.nama).all()
        for p in persons:
            self.brg_person.addItem(p.nama, p.id)
            self.mod_person.addItem(p.nama, p.id)
            
        self.brg_sku.clear()
        self.brg_sku.addItem("-- Pilih SKU --", None)
        
        # Hapus filter is_active dan bungkus dengan str()
        skus = self.db.query(SkuMaster).order_by(SkuMaster.kode_sku).all()
        for s in skus:
            kode_teks = str(s.kode_sku) if s.kode_sku else "NO-KODE"
            self.brg_sku.addItem(kode_teks, s.id)

        # 3. KEMBALIKAN PILIHAN KE NAMA YANG DIREKAM (JIKA ADA)
        if current_brg_person_id is not None:
            idx = self.brg_person.findData(current_brg_person_id)
            if idx >= 0: self.brg_person.setCurrentIndex(idx)

        if current_mod_person_id is not None:
            idx = self.mod_person.findData(current_mod_person_id)
            if idx >= 0: self.mod_person.setCurrentIndex(idx)
            
        if current_brg_sku_id is not None:
            idx = self.brg_sku.findData(current_brg_sku_id)
            if idx >= 0: self.brg_sku.setCurrentIndex(idx)

    def calculate_paid(self, debt_entry):
        return sum(p.nominal_bayar for p in debt_entry.payments)
    
    def calc_brg_total(self):
        self.brg_total.setValue(self.brg_qty.value() * self.brg_harga.value())

    def calc_mod_total(self):
        self.mod_total.setValue(self.mod_qty.value() * self.mod_harga.value())

    def load_barang_terhutang(self):
        self.table_barang.setRowCount(0)
        debts = self.db.query(DebtEntry).filter(DebtEntry.tipe_hutang == 'BARANG').order_by(DebtEntry.status.desc(), DebtEntry.tanggal.desc()).all()
        self.table_barang.setRowCount(len(debts))
        
        for r, d in enumerate(debts):
            self.table_barang.setItem(r, 0, QTableWidgetItem(str(d.id)))
            self.table_barang.setItem(r, 1, QTableWidgetItem(d.tanggal))
            self.table_barang.setItem(r, 2, QTableWidgetItem(d.person.nama if d.person else "Unknown"))
            self.table_barang.setItem(r, 3, QTableWidgetItem(d.sku.kode_sku if d.sku else "-"))
            self.table_barang.setItem(r, 4, QTableWidgetItem(str(d.qty or 0)))
            self.table_barang.setItem(r, 5, QTableWidgetItem(f"Rp {d.nominal_hutang:,.0f}"))
            
            terbayar = self.calculate_paid(d)
            self.table_barang.setItem(r, 6, QTableWidgetItem(f"Rp {terbayar:,.0f}"))
            
            status_item = QTableWidgetItem(d.status)
            if d.status == 'OPEN': status_item.setForeground(Qt.GlobalColor.red)
            elif d.status == 'LUNAS': status_item.setForeground(Qt.GlobalColor.green)
            self.table_barang.setItem(r, 7, status_item)

        self.apply_search_filter()

    def load_modal_hutang(self):
        self.table_modal.setRowCount(0)
        debts = self.db.query(DebtEntry).filter(DebtEntry.tipe_hutang == 'MODAL').order_by(DebtEntry.status.desc(), DebtEntry.tanggal.desc()).all()
        self.table_modal.setRowCount(len(debts))
        
        for r, d in enumerate(debts):
            self.table_modal.setItem(r, 0, QTableWidgetItem(str(d.id)))
            self.table_modal.setItem(r, 1, QTableWidgetItem(d.tanggal))
            self.table_modal.setItem(r, 2, QTableWidgetItem(d.person.nama if d.person else "Unknown"))
            
            # --- Tampilkan Kode Produksi di Tabel ---
            kode_prod = getattr(d, 'kode_produksi', None)
            item_kode = QTableWidgetItem(kode_prod if kode_prod else "-")
            item_kode.setForeground(Qt.GlobalColor.cyan)
            self.table_modal.setItem(r, 3, item_kode)
            
            self.table_modal.setItem(r, 4, QTableWidgetItem(d.keterangan))
            self.table_modal.setItem(r, 5, QTableWidgetItem(f"Rp {d.nominal_hutang:,.0f}"))
            
            terbayar = self.calculate_paid(d)
            self.table_modal.setItem(r, 6, QTableWidgetItem(f"Rp {terbayar:,.0f}"))
            
            status_item = QTableWidgetItem(d.status)
            if d.status == 'OPEN': status_item.setForeground(Qt.GlobalColor.red)
            elif d.status == 'LUNAS': status_item.setForeground(Qt.GlobalColor.green)
            self.table_modal.setItem(r, 7, status_item)

        self.apply_search_filter()

    def on_barang_selected(self):
        self.selected_barang_debt_ids.clear()
        selected_items = self.table_barang.selectedItems()
        
        if not selected_items:
            self.btn_brg_lunas.setEnabled(False)
            if hasattr(self, 'btn_batal_lunas_brg'):
                self.btn_batal_lunas_brg.setEnabled(False)
            self.brg_lunas_nom.setValue(0)
            return

        selected_rows = list(set(item.row() for item in selected_items))
        total_kalkulasi = 0
        ada_open = False
        ada_lunas = False

        for row in selected_rows:
            debt_id = int(self.table_barang.item(row, 0).text())
            status = self.table_barang.item(row, 7).text().strip().upper()
            debt = self.db.query(DebtEntry).get(debt_id)
            
            if debt:
                terbayar = self.calculate_paid(debt)
                sisa = debt.nominal_hutang - terbayar
                
                # Jika OPEN/PARTIAL, catat sisa hutangnya untuk dibayar
                if status == 'OPEN' or status == 'PARTIAL':
                    ada_open = True
                    if sisa > 0:
                        self.selected_barang_debt_ids.append((debt_id, sisa))
                        total_kalkulasi += sisa
                        
                # Jika LUNAS, catat total hutangnya (untuk kalkulator view) & bypass nilai sisa jadi 0
                elif status == 'LUNAS':
                    ada_lunas = True
                    self.selected_barang_debt_ids.append((debt_id, 0)) 
                    total_kalkulasi += debt.nominal_hutang

        # 1. FITUR BARU: Nominal pelunasan tetap muncul!
        self.brg_lunas_nom.setValue(total_kalkulasi) 
        
        # 2. Smart Disable Button
        self.btn_brg_lunas.setEnabled(ada_open)
        if hasattr(self, 'btn_batal_lunas_brg'):
            self.btn_batal_lunas_brg.setEnabled(ada_lunas)

        # Proses untuk Form Edit (Ambil data dari baris PERTAMA yang diklik)
        first_row = selected_rows[0]
        self.selected_barang_edit_id = int(self.table_barang.item(first_row, 0).text())

        debt = self.db.query(DebtEntry).get(self.selected_barang_edit_id)
        if debt:
            self.brg_date.setDate(QDate.fromString(debt.tanggal, "yyyy-MM-dd"))
            idx_person = self.brg_person.findData(debt.person_id)
            if idx_person >= 0: self.brg_person.setCurrentIndex(idx_person)

            idx_sku = self.brg_sku.findData(debt.sku_id)
            if idx_sku >= 0: self.brg_sku.setCurrentIndex(idx_sku)

            self.brg_qty.blockSignals(True)
            self.brg_harga.blockSignals(True)
            self.brg_total.blockSignals(True)

            self.brg_qty.setValue(float(debt.qty or 0.0))
            self.brg_total.setValue(debt.nominal_hutang)

            if debt.qty and debt.qty > 0:
                self.brg_harga.setValue(debt.nominal_hutang / debt.qty)
            else:
                self.brg_harga.setValue(0)

            self.brg_qty.blockSignals(False)
            self.brg_harga.blockSignals(False)
            self.brg_total.blockSignals(False)

            self.btn_simpan_brg.setText("UPDATE HUTANG BARANG")
            self.btn_reset_brg.show()
            self.btn_delete_brg.setEnabled(True)

    def on_modal_selected(self):
        self.selected_modal_debt_ids.clear()
        selected_items = self.table_modal.selectedItems()
        
        if not selected_items:
            self.btn_mod_lunas.setEnabled(False)
            if hasattr(self, 'btn_batal_lunas_mod'):
                self.btn_batal_lunas_mod.setEnabled(False)
            self.mod_lunas_nom.setValue(0)
            return

        selected_rows = list(set(item.row() for item in selected_items))
        total_kalkulasi = 0
        ada_open = False
        ada_lunas = False

        for row in selected_rows:
            debt_id = int(self.table_modal.item(row, 0).text())
            status = self.table_modal.item(row, 7).text().strip().upper()
            debt = self.db.query(DebtEntry).get(debt_id)
            
            if debt:
                terbayar = self.calculate_paid(debt)
                sisa = debt.nominal_hutang - terbayar
                
                if status == 'OPEN' or status == 'PARTIAL':
                    ada_open = True
                    if sisa > 0:
                        self.selected_modal_debt_ids.append((debt_id, sisa))
                        total_kalkulasi += sisa
                        
                elif status == 'LUNAS':
                    ada_lunas = True
                    self.selected_modal_debt_ids.append((debt_id, 0))
                    total_kalkulasi += debt.nominal_hutang

        self.mod_lunas_nom.setValue(total_kalkulasi)
        self.btn_mod_lunas.setEnabled(ada_open)
        if hasattr(self, 'btn_batal_lunas_mod'):
            self.btn_batal_lunas_mod.setEnabled(ada_lunas)

        # Proses untuk Form Edit (Ambil data dari baris PERTAMA yang diklik)
        first_row = selected_rows[0]
        self.selected_modal_edit_id = int(self.table_modal.item(first_row, 0).text())

        debt = self.db.query(DebtEntry).get(self.selected_modal_edit_id)
        if debt:
            self.mod_date.setDate(QDate.fromString(debt.tanggal, "yyyy-MM-dd"))
            idx_person = self.mod_person.findData(debt.person_id)
            if idx_person >= 0: self.mod_person.setCurrentIndex(idx_person)

            self.mod_jenis.setCurrentText(debt.keterangan)

            if debt.kode_produksi:
                self.mod_kode_produksi.setText(debt.kode_produksi)

            self.mod_qty.blockSignals(True)
            self.mod_harga.blockSignals(True)
            self.mod_total.blockSignals(True)

            self.mod_qty.setValue(float(debt.qty or 0.0))
            self.mod_total.setValue(debt.nominal_hutang)

            if debt.qty and debt.qty > 0:
                self.mod_harga.setValue(debt.nominal_hutang / debt.qty)
            else:
                self.mod_harga.setValue(0)

            self.mod_qty.blockSignals(False)
            self.mod_harga.blockSignals(False)
            self.mod_total.blockSignals(False)

            self.btn_simpan_mod.setText("UPDATE HUTANG MODAL")
            self.btn_reset_mod.show()
            self.btn_delete_mod.setEnabled(True)

    def reset_barang_form(self):
        self.selected_barang_edit_id = None
        self.selected_barang_debt_ids = []
        self.table_barang.clearSelection()
        self.lbl_title_brg.setText("CATAT HUTANG BARU")
        self.btn_simpan_brg.setText("SIMPAN BARU")
        self.btn_delete_brg.setEnabled(False)
        self.btn_brg_lunas.setEnabled(False)
        self.lbl_selected_brg.setText("PILIH HUTANG UNTUK MELUNASI (Bisa Lebih Dari 1)")
        self.brg_qty.setValue(0)
        self.brg_total.setValue(0)
        self.brg_lunas_nom.setValue(0)
        if hasattr(self, 'btn_batal_lunas_brg'): self.btn_batal_lunas_brg.setEnabled(False)

    def reset_modal_form(self):
        self.selected_modal_edit_id = None
        self.selected_modal_debt_ids = []
        self.table_modal.clearSelection()
        self.lbl_title_mod.setText("CATAT PINJAMAN MODAL")
        # self.mod_person.setCurrentIndex(-1)
        self.mod_jenis.setCurrentIndex(-1)
        self.mod_jenis.setCurrentText("")
        self.mod_qty.setValue(0)
        self.mod_harga.setValue(0)

        self.btn_simpan_mod.setText("SIMPAN BARU")
        self.btn_delete_mod.setEnabled(False)
        self.btn_mod_lunas.setEnabled(False)
        self.lbl_selected_mod.setText("PILIH PINJAMAN UNTUK DEPOSIT (Bisa Lebih Dari 1)")
        self.mod_total.setValue(0)
        self.mod_lunas_nom.setValue(0)
        if hasattr(self, 'btn_batal_lunas_mod'): self.btn_batal_lunas_mod.setEnabled(False)
        
        # Otomatis buatkan kode produksi urutan selanjutnya
        self.generate_kode_produksi()

    def submit_barang_hutang(self):
        person_id = self.brg_person.currentData()
        sku_id = self.brg_sku.currentData()
        
        if not person_id: return QMessageBox.warning(self, "Error", "Pilih Supplier!")

        qty_input = self.brg_qty.value()
        total_hutang = self.brg_total.value()

        if qty_input <= 0 or total_hutang <= 0:
            return QMessageBox.warning(self, "Error", "Qty dan Total tidak boleh nol!")

        try:
            if getattr(self, 'selected_barang_edit_id', None):
                # --- MODE UPDATE ---
                debt = self.db.query(DebtEntry).get(self.selected_barang_edit_id)
                debt.tanggal = self.brg_date.date().toString("yyyy-MM-dd")
                debt.person_id = person_id
                debt.sku_id = sku_id
                debt.qty = float(qty_input) # SIMPAN QTY DESIMAL
                debt.nominal_hutang = total_hutang
                msg = "Data Hutang Barang berhasil diupdate!"
            else:
                # --- MODE INSERT ---
                debt = DebtEntry(
                    tanggal=self.brg_date.date().toString("yyyy-MM-dd"),
                    person_id=person_id,
                    sku_id=sku_id,
                    tipe_hutang='BARANG',
                    qty=float(qty_input), # SIMPAN QTY DESIMAL
                    nominal_hutang=total_hutang,
                    status='OPEN',
                    keterangan='Hutang Barang'
                )
                self.db.add(debt)
                msg = "Data Hutang Barang berhasil disimpan!"

            self.db.commit()
            if hasattr(self, 'notifier') and self.notifier:
                print("[*] Broadcasting database changes to all menus...")
                self.notifier.database_changed.emit()
            self.load_barang_terhutang()
            self.reset_barang_form()
            QMessageBox.information(self, "Sukses", msg)
        except Exception as e:
            self.db.rollback()
            self.db.expire_all()
            QMessageBox.critical(self, "Error", f"Gagal menyimpan: {e}")
            
    def submit_modal_hutang(self):
        person_id = self.mod_person.currentData()
        ket = self.mod_jenis.currentText().strip()
        kode_prod = self.mod_kode_produksi.text().strip()

        if not person_id or not ket:
            return QMessageBox.warning(self, "Error", "Pilih Supplier & Isi Jenis/Ket!")

        qty_input = self.mod_qty.value()
        total_hutang = self.mod_total.value()

        if qty_input <= 0 or total_hutang <= 0:
            return QMessageBox.warning(self, "Error", "Qty dan Total tidak boleh nol!")

        try:
            if getattr(self, 'selected_modal_edit_id', None):
                # --- MODE UPDATE ---
                debt = self.db.query(DebtEntry).get(self.selected_modal_edit_id)
                debt.tanggal = self.mod_date.date().toString("yyyy-MM-dd")
                debt.person_id = person_id
                debt.keterangan = ket
                debt.kode_produksi = kode_prod
                debt.qty = float(qty_input) # SIMPAN QTY DESIMAL
                debt.nominal_hutang = total_hutang
                msg = "Data Hutang Modal berhasil diupdate!"
            else:
                # --- MODE INSERT ---
                debt = DebtEntry(
                    tanggal=self.mod_date.date().toString("yyyy-MM-dd"),
                    person_id=person_id,
                    tipe_hutang='MODAL',
                    keterangan=ket,
                    qty=float(qty_input), # SIMPAN QTY DESIMAL
                    nominal_hutang=total_hutang,
                    status='OPEN',
                    kode_produksi=kode_prod
                )
                self.db.add(debt)
                msg = "Data Hutang Modal berhasil disimpan!"

            self.db.commit()
            if hasattr(self, 'notifier') and self.notifier:
                print("[*] Broadcasting database changes to all menus...")
                self.notifier.database_changed.emit()
            self.load_modal_hutang()
            self.reset_modal_form()
            QMessageBox.information(self, "Sukses", msg)
        except Exception as e:
            self.db.rollback()
            self.db.expire_all()
            QMessageBox.critical(self, "Error", f"Gagal menyimpan: {e}")
    
    def calc_brg_total(self):
        """Menghitung total otomatis untuk Tab Barang"""
        qty = self.brg_qty.value()
        harga = self.brg_harga.value()
        self.brg_total.setValue(qty * harga)

    def calc_mod_total(self):
        """Menghitung total otomatis untuk Tab Modal"""
        qty = self.mod_qty.value()
        harga = self.mod_harga.value()
        self.mod_total.setValue(qty * harga)
            
    def generate_kode_produksi(self):
        """Otomatis membuat Kode Produksi berformat PRD-mmyy-XXX"""
        # Jangan ubah kode jika sedang dalam mode Edit data lama
        if getattr(self, 'selected_modal_edit_id', None):
            return

        # Ambil mmyy dari tanggal yang dipilih di form
        mmyy = self.mod_date.date().toString("MMyy")
        prefix = f"PRD-{mmyy}-"

        try:
            # Cari kode produksi terakhir di database yang berawalan PRD-mmyy
            last_entry = self.db.query(DebtEntry).filter(
                DebtEntry.kode_produksi.like(f"{prefix}%")
            ).order_by(DebtEntry.kode_produksi.desc()).first()

            if last_entry and last_entry.kode_produksi:
                # Ambil 3 angka terakhir, lalu tambah 1
                last_num = int(last_entry.kode_produksi.split('-')[-1])
                new_num = last_num + 1
            else:
                new_num = 1 # Mulai dari 001 jika bulan ini belum ada data

            # Format dengan 3 digit (contoh: 001, 002)
            new_kode = f"{prefix}{new_num:03d}"
            self.mod_kode_produksi.setText(new_kode)
            
        except Exception as e:
            print(f"Error generate kode: {e}")

    def delete_barang_hutang(self):
        if not getattr(self, 'selected_barang_edit_id', None): return
        reply = QMessageBox.question(self, "Konfirmasi Hapus", "Yakin hapus data ini beserta riwayat pembayarannya?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            try:
                debt = self.db.query(DebtEntry).get(self.selected_barang_edit_id)
                for p in self.db.query(DebtPayment).filter(DebtPayment.debt_entry_id == debt.id).all(): self.db.delete(p)
                self.db.delete(debt)
                self.db.commit()
                self.reset_barang_form()
                self.load_barang_terhutang()
            except Exception: self.db.rollback()

    def delete_modal_hutang(self):
        if not getattr(self, 'selected_modal_edit_id', None): return
        reply = QMessageBox.question(self, "Konfirmasi Hapus", "Yakin hapus data ini beserta riwayat pembayarannya?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            try:
                debt = self.db.query(DebtEntry).get(self.selected_modal_edit_id)
                for p in self.db.query(DebtPayment).filter(DebtPayment.debt_entry_id == debt.id).all(): self.db.delete(p)
                self.db.delete(debt)
                self.db.commit()
                self.reset_modal_form()
                self.load_modal_hutang()
            except Exception: self.db.rollback()

    def submit_barang_pelunasan(self):
        if not self.selected_barang_debt_ids: return
        nominal_uang = self.brg_lunas_nom.value()
        if nominal_uang <= 0: return
        tgl_bayar = self.brg_lunas_date.date().toString("yyyy-MM-dd")
        
        try:
            person_ids = set()
            for d_id, _ in self.selected_barang_debt_ids:
                debt = self.db.query(DebtEntry).get(d_id)
                person_ids.add(debt.person_id)
                
            if len(person_ids) > 1:
                QMessageBox.warning(self, "Error Kasir", "Hanya bisa melunasi tagihan dari SATU SUPPLIER yang sama dalam satu waktu!")
                return
                
            person = self.db.query(Person).get(list(person_ids)[0])
            all_debts = self.db.query(DebtEntry).filter(DebtEntry.person_id == person.id, DebtEntry.tipe_hutang == 'BARANG').all()
            sisa_awal = sum([d.nominal_hutang - self.calculate_paid(d) for d in all_debts])
            
            sisa_uang = nominal_uang
            items_for_pdf = []
            
            for debt_id, sisa_tagihan in self.selected_barang_debt_ids:
                if sisa_uang <= 0: break 
                
                bayar_baris_ini = min(sisa_uang, sisa_tagihan)
                
                if bayar_baris_ini > 0:
                    debt = self.db.query(DebtEntry).get(debt_id)
                    payment = DebtPayment(debt_entry_id=debt.id, tanggal_bayar=tgl_bayar, nominal_bayar=bayar_baris_ini, metode='CASH_BATCH')
                    self.db.add(payment)
                    
                    terbayar = self.calculate_paid(debt) + bayar_baris_ini
                    if terbayar >= debt.nominal_hutang: debt.status = 'LUNAS'
                    else: debt.status = 'PARTIAL'
                    
                    sisa_uang -= bayar_baris_ini
                    
                    qty_val = debt.qty if debt.qty and debt.qty > 0 else 1
                    harga_val = debt.nominal_hutang / qty_val
                    
                    items_for_pdf.append({
                        "tgl": debt.tanggal,
                        "desc": debt.sku.nama_produk if debt.sku else "Unknown SKU",
                        "qty": qty_val,
                        "harga": harga_val,
                        "bayar": bayar_baris_ini
                    })
                    
            self.db.commit()
            if hasattr(self, 'notifier') and self.notifier:
                print("[*] Broadcasting database changes to all menus...")
                self.notifier.database_changed.emit()
            sisa_akhir = sisa_awal - nominal_uang
            if sisa_akhir < 0: sisa_akhir = 0
            
            pdf_path = generate_batch_receipt_pdf(person.nama, "BARANG", nominal_uang, items_for_pdf, sisa_awal, sisa_akhir)
            
            self.load_barang_terhutang()
            self.reset_barang_form()
            QMessageBox.information(self, "Sukses", f"Pembayaran Batch berhasil! Membuka Nota...")
            os.startfile(pdf_path)
            
        except Exception as e:
            self.db.rollback()
            self.db.expire_all()
            QMessageBox.critical(self, "Error", f"Gagal memproses batch payment: {e}")

    def submit_modal_pelunasan(self):
        if not self.selected_modal_debt_ids: return
        nominal_uang = self.mod_lunas_nom.value()
        if nominal_uang <= 0: return
        tgl_bayar = self.mod_lunas_date.date().toString("yyyy-MM-dd")
        
        try:
            person_ids = set()
            for d_id, _ in self.selected_modal_debt_ids:
                debt = self.db.query(DebtEntry).get(d_id)
                person_ids.add(debt.person_id)
                
            if len(person_ids) > 1:
                QMessageBox.warning(self, "Error Kasir", "Hanya bisa melunasi tagihan dari SATU SUPPLIER yang sama dalam satu waktu!")
                return
                
            person = self.db.query(Person).get(list(person_ids)[0])
            all_debts = self.db.query(DebtEntry).filter(DebtEntry.person_id == person.id, DebtEntry.tipe_hutang == 'MODAL').all()
            sisa_awal = sum([d.nominal_hutang - self.calculate_paid(d) for d in all_debts])
            
            sisa_uang = nominal_uang
            items_for_pdf = []
            
            for debt_id, sisa_tagihan in self.selected_modal_debt_ids:
                if sisa_uang <= 0: break
                
                bayar_baris_ini = min(sisa_uang, sisa_tagihan)
                
                if bayar_baris_ini > 0:
                    debt = self.db.query(DebtEntry).get(debt_id)
                    payment = DebtPayment(debt_entry_id=debt.id, tanggal_bayar=tgl_bayar, nominal_bayar=bayar_baris_ini, metode='CASH_BATCH')
                    self.db.add(payment)
                    
                    terbayar = self.calculate_paid(debt) + bayar_baris_ini
                    if terbayar >= debt.nominal_hutang: debt.status = 'LUNAS'
                    else: debt.status = 'PARTIAL'
                    
                    sisa_uang -= bayar_baris_ini
                    
                    qty_val = debt.qty if debt.qty and debt.qty > 0 else 1
                    harga_val = debt.nominal_hutang / qty_val
                    
                    items_for_pdf.append({
                        "tgl": debt.tanggal,
                        "desc": debt.keterangan,
                        "qty": qty_val,
                        "harga": harga_val,
                        "bayar": bayar_baris_ini
                    })
                    
            self.db.commit()
            if hasattr(self, 'notifier') and self.notifier:
                print("[*] Broadcasting database changes to all menus...")
                self.notifier.database_changed.emit()
            sisa_akhir = sisa_awal - nominal_uang
            if sisa_akhir < 0: sisa_akhir = 0
            
            pdf_path = generate_batch_receipt_pdf(person.nama, "MODAL", nominal_uang, items_for_pdf, sisa_awal, sisa_akhir)
            
            self.load_modal_hutang()
            self.reset_modal_form()
            QMessageBox.information(self, "Sukses", f"Deposit Batch berhasil! Membuka Nota...")
            os.startfile(pdf_path)
            
        except Exception as e:
            self.db.rollback()
            self.db.expire_all()
            QMessageBox.critical(self, "Error", f"Gagal memproses batch deposit: {e}")

    def submit_batal_lunas_barang(self):
        if not self.selected_barang_debt_ids: return
        reply = QMessageBox.question(self, "Konfirmasi Batal", "Yakin ingin membatalkan pelunasan (SET OPEN) untuk data terpilih?\n\nSemua riwayat pembayaran (nota lunas) dari baris ini akan dihapus.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                for d_id, _ in self.selected_barang_debt_ids:
                    debt = self.db.query(DebtEntry).get(d_id)
                    if debt and debt.status == 'LUNAS':
                        # WAJIB menghapus riwayat pembayarannya agar nilai 'terbayar' kembali jadi 0
                        for p in self.db.query(DebtPayment).filter(DebtPayment.debt_entry_id == debt.id).all():
                            self.db.delete(p)
                        debt.status = 'OPEN'
                        
                self.db.commit()
                if hasattr(self, 'notifier') and self.notifier:
                    self.notifier.database_changed.emit()
                    
                self.load_barang_terhutang()
                self.reset_barang_form()
                QMessageBox.information(self, "Sukses", "Status hutang barang berhasil dikembalikan menjadi OPEN dan riwayat pembayaran dihapus.")
            except Exception as e:
                self.db.rollback()
                self.db.expire_all()
                QMessageBox.critical(self, "Error", f"Gagal merubah status: {e}")

    def submit_batal_lunas_modal(self):
        if not self.selected_modal_debt_ids: return
        reply = QMessageBox.question(self, "Konfirmasi Batal", "Yakin ingin membatalkan deposit/lunas (SET OPEN) untuk data terpilih?\n\nSemua riwayat deposit pada baris ini akan dihapus.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                for d_id, _ in self.selected_modal_debt_ids:
                    debt = self.db.query(DebtEntry).get(d_id)
                    if debt and debt.status == 'LUNAS':
                        for p in self.db.query(DebtPayment).filter(DebtPayment.debt_entry_id == debt.id).all():
                            self.db.delete(p)
                        debt.status = 'OPEN'
                        
                self.db.commit()
                if hasattr(self, 'notifier') and self.notifier:
                    self.notifier.database_changed.emit()
                    
                self.load_modal_hutang()
                self.reset_modal_form()
                QMessageBox.information(self, "Sukses", "Status hutang modal berhasil dikembalikan menjadi OPEN.")
            except Exception as e:
                self.db.rollback()
                self.db.expire_all()
                QMessageBox.critical(self, "Error", f"Gagal merubah status: {e}")
    
    def closeEvent(self, event):
        self.db.close()
        super().closeEvent(event)