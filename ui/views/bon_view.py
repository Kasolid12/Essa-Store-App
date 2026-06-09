# app_essa/ui/views/bon_view.py
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, 
    QComboBox, QDoubleSpinBox, QLineEdit, QTabWidget, 
    QHeaderView, QTableWidgetItem, QMessageBox, QGridLayout, QGroupBox
)
from PySide6.QtCore import Qt, QDate

from ui.components.tables import CyberTable
from ui.components.buttons import CyberButton
from ui.theme import Theme
from data.database import SessionLocal
from data.models import Person
from data.models.bon import BonBalance, BonMovement

class BonView(QWidget):
    def __init__(self):
        super().__init__()
        self.db = SessionLocal()
        self.setup_ui()
        self.load_persons()
        self.refresh_dashboard()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # --- HEADER ---
        header_layout = QHBoxLayout()
        title = QLabel("MANAJEMEN KASBON (BON)")
        title.setStyleSheet(f"font-size: 24pt; font-weight: bold; color: {Theme.NEON_CYAN};")
        header_layout.addWidget(title)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        # --- TABS ---
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

        self.setup_tab_dashboard()
        self.setup_tab_manual()

        self.tabs.addTab(self.tab_dashboard, "DASHBOARD KASBON")
        self.tabs.addTab(self.tab_manual, "UPDATE BON MANUAL")
        
        # Memicu refresh otomatis saat pindah tab
        self.tabs.currentChanged.connect(self.on_tab_changed)
        
        layout.addWidget(self.tabs)

    # ==========================================
    # TAB 1: DASHBOARD KASBON (Tampilan Keseluruhan)
    # ==========================================
    def setup_tab_dashboard(self):
        self.tab_dashboard = QWidget()
        lay = QVBoxLayout(self.tab_dashboard)
        
        btn_refresh = CyberButton("🔄 REFRESH DATA")
        btn_refresh.setMinimumWidth(200)
        btn_refresh.clicked.connect(self.refresh_dashboard)
        
        top_lay = QHBoxLayout()
        top_lay.addWidget(QLabel("Daftar Sisa Kasbon Aktif (Semua Divisi):"))
        top_lay.addStretch()
        top_lay.addWidget(btn_refresh)
        lay.addLayout(top_lay)
        
        self.table_dash = CyberTable()
        self.table_dash.setColumnCount(4)
        self.table_dash.setHorizontalHeaderLabels(["ID", "Nama Personel", "Divisi", "Sisa Kasbon Saat Ini"])
        self.table_dash.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        lay.addWidget(self.table_dash)

    # ==========================================
    # TAB 2: UPDATE BON MANUAL (TAB BARU)
    # ==========================================
    def setup_tab_manual(self):
        self.tab_manual = QWidget()
        lay = QVBoxLayout(self.tab_manual)
        
        # -- BAGIAN ATAS: Form Input --
        form_group = QGroupBox("FORM UPDATE MANUAL")
        form_group.setStyleSheet(f"""
            QGroupBox {{ color: {Theme.NEON_YELLOW}; font-weight: bold; border: 1px solid #2d2d38; border-radius: 8px; padding: 15px; margin-top: 10px; }}
            QGroupBox::title {{ subcontrol-origin: margin; padding: 0 5px; }}
        """)
        form_lay = QGridLayout(form_group)
        form_lay.setSpacing(15)
        
        self.cb_person = QComboBox()
        self.cb_person.currentIndexChanged.connect(self.on_person_selected)
        
        self.lbl_saldo = QLabel("Rp 0")
        self.lbl_saldo.setStyleSheet(f"font-size: 16pt; font-weight: bold; color: {Theme.NEON_PINK};")
        
        self.cb_aksi = QComboBox()
        self.cb_aksi.addItems(["+ TAMBAH BON BARU", "- POTONG BON (BAYAR TUNAI)"])
        self.cb_aksi.setStyleSheet(f"background-color: {Theme.BG_VOID}; color: {Theme.TEXT_MAIN}; font-weight: bold;")
        
        self.spin_nominal = QDoubleSpinBox()
        self.spin_nominal.setRange(0, 999999999)
        self.spin_nominal.setPrefix("Rp ")
        
        self.txt_ket = QLineEdit()
        self.txt_ket.setPlaceholderText("Catatan (Misal: Pinjam uang bensin, Bayar tunai sisa bon...)")
        
        btn_submit = CyberButton("SIMPAN UPDATE")
        btn_submit.setStyleSheet(f"background-color: {Theme.NEON_CYAN}; color: #000; font-weight: bold; padding: 10px;")
        btn_submit.clicked.connect(self.submit_manual_update)
        
        form_lay.addWidget(QLabel("Pilih Nama:"), 0, 0); form_lay.addWidget(self.cb_person, 0, 1)
        form_lay.addWidget(QLabel("Sisa Saldo Saat Ini:"), 0, 2); form_lay.addWidget(self.lbl_saldo, 0, 3)
        
        line = QFrame(); line.setFrameShape(QFrame.Shape.HLine); line.setStyleSheet("background-color: #2d2d38;")
        form_lay.addWidget(line, 1, 0, 1, 4)
        
        form_lay.addWidget(QLabel("Jenis Tindakan:"), 2, 0); form_lay.addWidget(self.cb_aksi, 2, 1)
        form_lay.addWidget(QLabel("Nominal:"), 2, 2); form_lay.addWidget(self.spin_nominal, 2, 3)
        form_lay.addWidget(QLabel("Keterangan/Catatan:"), 3, 0); form_lay.addWidget(self.txt_ket, 3, 1, 1, 3)
        
        form_lay.addWidget(btn_submit, 4, 3)
        lay.addWidget(form_group)
        
        # -- BAGIAN BAWAH: Tabel Riwayat Khusus Personel yang Dipilih --
        lay.addWidget(QLabel("Riwayat Pergerakan Kasbon (Orang Terpilih):"), alignment=Qt.AlignmentFlag.AlignBottom)
        
        self.table_history = CyberTable()
        self.table_history.setColumnCount(5)
        self.table_history.setHorizontalHeaderLabels(["Tanggal", "Jenis", "Sumber", "Keterangan", "Nominal"])
        self.table_history.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        lay.addWidget(self.table_history)

    # ==========================================
    # LOGIC & HANDLERS
    # ==========================================
    def load_persons(self):
        self.cb_person.clear()
        self.cb_person.addItem("-- Pilih Nama --", None)
        persons = self.db.query(Person).filter(Person.person_type.in_(['PENJAHIT', 'PENGSUP', 'KARYAWAN'])).order_by(Person.nama).all()
        for p in persons:
            self.cb_person.addItem(f"{p.nama} ({p.person_type})", p.id)

    def on_tab_changed(self, index):
        if index == 0:
            self.refresh_dashboard()

    def refresh_dashboard(self):
        self.table_dash.setRowCount(0)
        # Ambil data saldo yang lebih dari 0
        balances = self.db.query(BonBalance).filter(BonBalance.saldo > 0).all()
        
        self.table_dash.setRowCount(len(balances))
        for row, b in enumerate(balances):
            self.table_dash.setItem(row, 0, QTableWidgetItem(str(b.person_id)))
            self.table_dash.setItem(row, 1, QTableWidgetItem(b.person.nama if b.person else "Unknown"))
            self.table_dash.setItem(row, 2, QTableWidgetItem(b.person.person_type if b.person else "-"))
            
            saldo_item = QTableWidgetItem(f"Rp {b.saldo:,.0f}")
            saldo_item.setForeground(Qt.GlobalColor.magenta)
            saldo_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table_dash.setItem(row, 3, saldo_item)

    def on_person_selected(self):
        person_id = self.cb_person.currentData()
        if not person_id:
            self.lbl_saldo.setText("Rp 0")
            self.table_history.setRowCount(0)
            return
            
        # 1. Update Label Saldo
        balance = self.db.query(BonBalance).filter(BonBalance.person_id == person_id).first()
        saldo_saat_ini = balance.saldo if balance else 0
        self.lbl_saldo.setText(f"Rp {saldo_saat_ini:,.0f}")
        
        # 2. Update Tabel Riwayat
        movements = self.db.query(BonMovement).filter(BonMovement.person_id == person_id).order_by(BonMovement.id.desc()).limit(30).all()
        self.table_history.setRowCount(len(movements))
        for row, m in enumerate(movements):
            self.table_history.setItem(row, 0, QTableWidgetItem(str(m.tanggal)))
            
            jenis_item = QTableWidgetItem(m.tipe)
            if "TAMBAH" in m.tipe: jenis_item.setForeground(Qt.GlobalColor.yellow)
            else: jenis_item.setForeground(Qt.GlobalColor.green)
            self.table_history.setItem(row, 1, jenis_item)
            
            self.table_history.setItem(row, 2, QTableWidgetItem(str(m.sumber)))
            self.table_history.setItem(row, 3, QTableWidgetItem(str(m.keterangan) if m.keterangan else "-"))
            
            nom_item = QTableWidgetItem(f"Rp {m.nominal:,.0f}")
            nom_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table_history.setItem(row, 4, nom_item)

    def submit_manual_update(self):
        person_id = self.cb_person.currentData()
        nominal = self.spin_nominal.value()
        is_tambah = (self.cb_aksi.currentIndex() == 0)
        ket = self.txt_ket.text().strip()
        
        if not person_id:
            return QMessageBox.warning(self, "Error", "Pilih nama terlebih dahulu!")
        if nominal <= 0:
            return QMessageBox.warning(self, "Error", "Nominal tidak boleh kosong/nol!")
            
        try:
            # 1. Pastikan record saldo untuk orang ini ada
            balance = self.db.query(BonBalance).filter(BonBalance.person_id == person_id).first()
            if not balance:
                balance = BonBalance(person_id=person_id, saldo=0)
                self.db.add(balance)
                
            # Validasi Potongan
            if not is_tambah and nominal > balance.saldo:
                return QMessageBox.warning(self, "Error", "Nominal potongan tidak boleh lebih besar dari sisa saldo!")

            # 2. Update Saldo Utama
            if is_tambah:
                balance.saldo += nominal
                tipe_mov = "TAMBAH_MANUAL"
            else:
                balance.saldo -= nominal
                tipe_mov = "POTONG_MANUAL"
                
            # 3. Catat Pergerakan Riwayat (Log)
            tgl_sekarang = QDate.currentDate().toString("yyyy-MM-dd")
            catatan = ket if ket else "Update Manual oleh Kasir"
            
            movement = BonMovement(
                person_id=person_id, 
                tanggal=tgl_sekarang, 
                tipe=tipe_mov, 
                nominal=nominal, 
                sumber="UPDATE_MANUAL",
                keterangan=catatan
            )
            self.db.add(movement)
            self.db.commit()
            
            QMessageBox.information(self, "Sukses", "Data kasbon berhasil diupdate manual!")
            
            # Reset Form & Refresh
            self.spin_nominal.setValue(0)
            self.txt_ket.clear()
            self.on_person_selected() # Refresh saldo dan tabel bawah
            
        except Exception as e:
            self.db.rollback()
            self.db.expire_all()
            QMessageBox.critical(self, "Error", f"Terjadi kesalahan database: {e}")

    def closeEvent(self, event):
        self.db.close()
        super().closeEvent(event)