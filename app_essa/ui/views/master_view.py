# app_essa/ui/views/master_view.py
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QTabWidget,
    QLineEdit, QDoubleSpinBox, QComboBox, QMessageBox, QTableWidgetItem, QHeaderView
)
from PySide6.QtCore import Qt

from ui.components.tables import CyberTable
from ui.components.buttons import CyberButton
from ui.theme import Theme
from data.database import SessionLocal
from data.models import SkuMaster, Person

class MasterDataView(QWidget):
    def __init__(self):
        super().__init__()
        self.db = SessionLocal()
        self.selected_sku_id = None
        self.selected_person_id = None
        self.setup_ui()
        self.load_sku_data()
        self.load_person_data()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # --- Page Header ---
        header_layout = QHBoxLayout()
        title = QLabel("DATA MANAGER: GOD MODE")
        title.setStyleSheet(f"font-size: 24pt; font-weight: bold; color: {Theme.NEON_CYAN};")
        header_layout.addWidget(title)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        # --- TABS ---
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
        
        self.setup_sku_tab()
        self.setup_person_tab()
        
        layout.addWidget(self.tabs)

    # ==========================================
    # 1. SKU TAB SETUP
    # ==========================================
    def setup_sku_tab(self):
        self.tab_sku = QWidget()
        lay_sku = QVBoxLayout(self.tab_sku)
        
        self.table_sku = CyberTable()
        self.table_sku.setColumnCount(4)
        self.table_sku.setHorizontalHeaderLabels(["ID", "Kode SKU", "Nama Produk", "Harga Modal"])
        self.table_sku.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table_sku.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table_sku.itemSelectionChanged.connect(self.on_sku_selected)
        lay_sku.addWidget(self.table_sku, stretch=2)

        form_frame = QFrame()
        form_frame.setObjectName("GridPanel")
        form_layout = QVBoxLayout(form_frame)
        form_layout.addWidget(QLabel("SKU EDITOR FORM", styleSheet=f"color: {Theme.TEXT_MUTED}; font-weight: bold;"))
        
        input_layout = QHBoxLayout()
        self.input_kode = QLineEdit()
        self.input_nama = QLineEdit()
        self.input_modal = QDoubleSpinBox()
        self.input_modal.setRange(0, 9999999)
        
        input_layout.addWidget(QLabel("Kode:"))
        input_layout.addWidget(self.input_kode, stretch=1)
        input_layout.addWidget(QLabel("Nama:"))
        input_layout.addWidget(self.input_nama, stretch=2)
        input_layout.addWidget(QLabel("Modal:"))
        input_layout.addWidget(self.input_modal, stretch=1)
        form_layout.addLayout(input_layout)
        
        btn_layout = QHBoxLayout()
        self.btn_save_sku = CyberButton("SIMPAN SKU")
        self.btn_save_sku.clicked.connect(self.save_sku)
        self.btn_clear_sku = CyberButton("RESET")
        self.btn_clear_sku.clicked.connect(self.clear_sku_form)
        self.btn_delete_sku = CyberButton("HAPUS SKU", is_danger=True)
        self.btn_delete_sku.clicked.connect(self.delete_sku)
        self.btn_delete_sku.setEnabled(False)
        
        btn_layout.addWidget(self.btn_save_sku)
        btn_layout.addWidget(self.btn_clear_sku)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_delete_sku)
        
        form_layout.addLayout(btn_layout)
        lay_sku.addWidget(form_frame)
        self.tabs.addTab(self.tab_sku, "MASTER SKU")

    # ==========================================
    # 2. PERSON TAB SETUP
    # ==========================================
    def setup_person_tab(self):
        self.tab_person = QWidget()
        lay_person = QVBoxLayout(self.tab_person)
        
        self.table_person = CyberTable()
        self.table_person.setColumnCount(4)
        self.table_person.setHorizontalHeaderLabels(["ID", "Nama Person", "Tipe Kategori", "Status"])
        self.table_person.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table_person.itemSelectionChanged.connect(self.on_person_selected)
        lay_person.addWidget(self.table_person, stretch=2)

        form_frame = QFrame()
        form_frame.setObjectName("GridPanel")
        form_layout = QVBoxLayout(form_frame)
        form_layout.addWidget(QLabel("PERSON DIRECTORY EDITOR", styleSheet=f"color: {Theme.TEXT_MUTED}; font-weight: bold;"))
        
        input_layout = QHBoxLayout()
        self.input_person_nama = QLineEdit()
        self.input_person_tipe = QComboBox()
        self.input_person_tipe.addItems(['KARYAWAN', 'PENJAHIT', 'PENGSUP', 'KLIEN', 'SUPPLIER', 'LAINNYA'])
        
        input_layout.addWidget(QLabel("Nama Lengkap:"))
        input_layout.addWidget(self.input_person_nama, stretch=2)
        input_layout.addWidget(QLabel("Kategori / Tipe:"))
        input_layout.addWidget(self.input_person_tipe, stretch=1)
        form_layout.addLayout(input_layout)
        
        btn_layout = QHBoxLayout()
        self.btn_save_person = CyberButton("SIMPAN PERSON")
        self.btn_save_person.clicked.connect(self.save_person)
        
        self.btn_clear_person = CyberButton("RESET")
        self.btn_clear_person.clicked.connect(self.clear_person_form)

        # --- NEW: Delete Person Button ---
        self.btn_delete_person = CyberButton("HAPUS PERSON", is_danger=True)
        self.btn_delete_person.clicked.connect(self.delete_person)
        self.btn_delete_person.setEnabled(False) # Disabled until you click a row
        
        btn_layout.addWidget(self.btn_save_person)
        btn_layout.addWidget(self.btn_clear_person)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_delete_person)
        
        form_layout.addLayout(btn_layout)
        lay_person.addWidget(form_frame)
        self.tabs.addTab(self.tab_person, "DIRECTORY PERSONS")

    # --- SKU LOGIC ---
    def load_sku_data(self):
        self.table_sku.setRowCount(0)
        skus = self.db.query(SkuMaster).order_by(SkuMaster.id.desc()).all()
        self.table_sku.setRowCount(len(skus))
        for row, sku in enumerate(skus):
            self.table_sku.setItem(row, 0, QTableWidgetItem(str(sku.id)))
            self.table_sku.setItem(row, 1, QTableWidgetItem(sku.kode_sku))
            self.table_sku.setItem(row, 2, QTableWidgetItem(sku.nama_produk))
            modal_item = QTableWidgetItem(f"{sku.harga_modal:,.0f}")
            modal_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table_sku.setItem(row, 3, modal_item)

    def on_sku_selected(self):
        selected = self.table_sku.selectedItems()
        if not selected: return
        row = selected[0].row()
        self.selected_sku_id = int(self.table_sku.item(row, 0).text())
        self.input_kode.setText(self.table_sku.item(row, 1).text())
        self.input_nama.setText(self.table_sku.item(row, 2).text())
        self.input_modal.setValue(float(self.table_sku.item(row, 3).text().replace(',', '')))
        self.btn_save_sku.setText("UPDATE DATA")
        self.btn_delete_sku.setEnabled(True)

    def save_sku(self):
        kode = self.input_kode.text().strip()
        nama = self.input_nama.text().strip()
        if not kode or not nama: return
        try:
            if self.selected_sku_id:
                sku = self.db.query(SkuMaster).get(self.selected_sku_id)
                sku.kode_sku, sku.nama_produk, sku.harga_modal = kode, nama, self.input_modal.value()
            else:
                self.db.add(SkuMaster(kode_sku=kode, nama_produk=nama, harga_modal=self.input_modal.value()))
            self.db.commit()
            self.clear_sku_form()
            self.load_sku_data()
        except Exception as e:
            self.db.rollback()

    def delete_sku(self):
        if not self.selected_sku_id: return
        try:
            sku = self.db.query(SkuMaster).get(self.selected_sku_id)
            self.db.delete(sku)
            self.db.commit()
            self.clear_sku_form()
            self.load_sku_data()
        except Exception:
            self.db.rollback()
            QMessageBox.critical(self, "Penghapusan Ditolak", "SKU ini sedang digunakan di tabel lain (Catatan Harian/Invoice) dan tidak bisa dihapus.")

    def clear_sku_form(self):
        self.selected_sku_id = None
        self.input_kode.clear()
        self.input_nama.clear()
        self.input_modal.setValue(0)
        self.btn_save_sku.setText("SIMPAN BARU")
        self.btn_delete_sku.setEnabled(False)
        self.table_sku.clearSelection()

    # --- PERSON LOGIC ---
    def load_person_data(self):
        self.table_person.setRowCount(0)
        persons = self.db.query(Person).order_by(Person.person_type, Person.nama).all()
        self.table_person.setRowCount(len(persons))
        for row, p in enumerate(persons):
            self.table_person.setItem(row, 0, QTableWidgetItem(str(p.id)))
            self.table_person.setItem(row, 1, QTableWidgetItem(p.nama))
            self.table_person.setItem(row, 2, QTableWidgetItem(p.person_type))
            status = "AKTIF" if p.is_active == 1 else "TIDAK AKTIF"
            self.table_person.setItem(row, 3, QTableWidgetItem(status))

    def on_person_selected(self):
        selected = self.table_person.selectedItems()
        if not selected: return
        row = selected[0].row()
        self.selected_person_id = int(self.table_person.item(row, 0).text())
        self.input_person_nama.setText(self.table_person.item(row, 1).text())
        
        tipe_text = self.table_person.item(row, 2).text()
        index = self.input_person_tipe.findText(tipe_text)
        if index >= 0: self.input_person_tipe.setCurrentIndex(index)
        
        self.btn_save_person.setText("UPDATE PERSON")
        self.btn_delete_person.setEnabled(True) # Enable Delete button

    def save_person(self):
        nama = self.input_person_nama.text().strip()
        tipe = self.input_person_tipe.currentText()
        if not nama: return
        try:
            if self.selected_person_id:
                # UPDATE Existing
                p = self.db.query(Person).get(self.selected_person_id)
                p.nama, p.person_type = nama, tipe
            else:
                # CREATE New
                self.db.add(Person(nama=nama, person_type=tipe))
            self.db.commit()
            self.clear_person_form()
            self.load_person_data()
        except Exception as e:
            self.db.rollback()
            QMessageBox.critical(self, "Error", f"Gagal menyimpan data: {e}")

    def delete_person(self):
        """Safely attempt to delete a Person."""
        if not self.selected_person_id: return
        
        reply = QMessageBox.question(
            self, "Konfirmasi Hapus", 
            "Yakin ingin menghapus orang ini?\n\nJika orang ini memiliki riwayat Bon, Gaji, atau Hutang, sistem akan membatalkan penghapusan demi keamanan data akuntansi.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                p = self.db.query(Person).get(self.selected_person_id)
                self.db.delete(p)
                self.db.commit()
                self.clear_person_form()
                self.load_person_data()
                QMessageBox.information(self, "Sukses", "Data berhasil dihapus.")
            except Exception:
                self.db.rollback()
                QMessageBox.critical(self, "Penghapusan Ditolak", "Gagal Menghapus!\n\nOrang ini sudah memiliki riwayat transaksi (Bon, Hutang, atau Gaji). Menghapus data ini akan merusak pembukuan Anda.")

    def clear_person_form(self):
        self.selected_person_id = None
        self.input_person_nama.clear()
        self.input_person_tipe.setCurrentIndex(0)
        self.btn_save_person.setText("SIMPAN BARU")
        self.btn_delete_person.setEnabled(False) # Disable Delete button
        self.table_person.clearSelection()

    def closeEvent(self, event):
        self.db.close()
        super().closeEvent(event)