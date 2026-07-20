# app_essa/ui/views/client_view.py
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QTableWidgetItem, QHeaderView, QMessageBox, QAbstractItemView,
    QGridLayout, QLineEdit, QTextEdit
)
from PySide6.QtCore import Qt

from ui.components.tables import CyberTable
from ui.components.buttons import CyberButton
from ui.theme import Theme
from data.database import SessionLocal
from data.models import Client


class ClientView(QWidget):
    """Manajemen data klien: nama, alamat, no HP."""

    def __init__(self, notifier=None):
        super().__init__()
        self.db = SessionLocal()
        self.notifier = notifier
        self.selected_client_id = None
        self.setup_ui()
        self.load_data()
        if self.notifier:
            self.notifier.database_changed.connect(self.refresh_data)

    def refresh_data(self):
        self.db.expire_all()
        self.load_data()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # --- Header ---
        header = QHBoxLayout()
        title = QLabel("MANAJEMEN KLIEN")
        title.setStyleSheet(f"font-size: 16pt; font-weight: bold; color: {Theme.NEON_CYAN};")
        header.addWidget(title)
        header.addStretch()
        layout.addLayout(header)

        # --- Tabel Klien ---
        self.table = CyberTable()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["ID", "Nama Klien", "No. HP", "Alamat"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.itemSelectionChanged.connect(self.on_client_selected)
        layout.addWidget(self.table, stretch=2)

        # --- Form Edit ---
        form_frame = QFrame()
        form_frame.setObjectName("GridPanel")
        form_lay = QGridLayout(form_frame)
        form_lay.setSpacing(8)

        form_lay.addWidget(QLabel("Nama Klien:"), 0, 0)
        self.input_nama = QLineEdit()
        self.input_nama.setPlaceholderText("Nama lengkap klien...")
        self.input_nama.setStyleSheet(
            f"background-color: {Theme.BG_VOID}; color: {Theme.TEXT_MAIN};"
            f" padding: 6px; border: 1px solid {Theme.BORDER_DIM}; border-radius: 4px;"
        )
        form_lay.addWidget(self.input_nama, 0, 1, 1, 2)

        form_lay.addWidget(QLabel("No. HP:"), 1, 0)
        self.input_hp = QLineEdit()
        self.input_hp.setPlaceholderText("08xxxxxxxxxx")
        self.input_hp.setStyleSheet(
            f"background-color: {Theme.BG_VOID}; color: {Theme.TEXT_MAIN};"
            f" padding: 6px; border: 1px solid {Theme.BORDER_DIM}; border-radius: 4px;"
        )
        form_lay.addWidget(self.input_hp, 1, 1, 1, 2)

        form_lay.addWidget(QLabel("Alamat:"), 2, 0)
        self.input_alamat = QTextEdit()
        self.input_alamat.setPlaceholderText("Alamat lengkap klien...")
        self.input_alamat.setMaximumHeight(60)
        self.input_alamat.setStyleSheet(
            f"background-color: {Theme.BG_VOID}; color: {Theme.TEXT_MAIN};"
            f" padding: 6px; border: 1px solid {Theme.BORDER_DIM}; border-radius: 4px;"
        )
        form_lay.addWidget(self.input_alamat, 2, 1, 1, 2)

        # Buttons
        btn_layout = QHBoxLayout()
        self.btn_save = CyberButton("SIMPAN KLIEN")
        self.btn_save.clicked.connect(self.save_client)
        btn_layout.addWidget(self.btn_save)

        self.btn_clear = CyberButton("RESET")
        self.btn_clear.clicked.connect(self.clear_form)
        btn_layout.addWidget(self.btn_clear)

        btn_layout.addStretch()

        self.btn_delete = CyberButton("HAPUS KLIEN", is_danger=True)
        self.btn_delete.setEnabled(False)
        self.btn_delete.clicked.connect(self.delete_client)
        btn_layout.addWidget(self.btn_delete)

        form_lay.addLayout(btn_layout, 3, 0, 1, 3)
        layout.addWidget(form_frame)

    # ====================================================================
    # LOAD DATA
    # ====================================================================
    def load_data(self):
        self.table.setRowCount(0)
        clients = (
            self.db.query(Client)
            .filter(Client.is_deleted == 0)
            .order_by(Client.nama)
            .all()
        )
        self.table.setRowCount(len(clients))
        for row, c in enumerate(clients):
            self.table.setItem(row, 0, QTableWidgetItem(str(c.id)))
            self.table.setItem(row, 1, QTableWidgetItem(c.nama))
            self.table.setItem(row, 2, QTableWidgetItem(c.no_hp or "-"))
            self.table.setItem(row, 3, QTableWidgetItem(c.alamat or "-"))

    # ====================================================================
    # SELECTION
    # ====================================================================
    def on_client_selected(self):
        selected = self.table.selectedItems()
        if not selected:
            return
        row = selected[0].row()
        self.selected_client_id = int(self.table.item(row, 0).text())

        record = self.db.query(Client).get(self.selected_client_id)
        if record:
            self.input_nama.setText(record.nama)
            self.input_hp.setText(record.no_hp or "")
            self.input_alamat.setText(record.alamat or "")
            self.btn_save.setText("UPDATE KLIEN")
            self.btn_delete.setEnabled(True)

    # ====================================================================
    # SAVE
    # ====================================================================
    def save_client(self):
        nama = self.input_nama.text().strip()
        if not nama:
            QMessageBox.warning(self, "Error", "Nama klien tidak boleh kosong!")
            return

        no_hp = self.input_hp.text().strip()
        alamat = self.input_alamat.toPlainText().strip()

        try:
            if self.selected_client_id:
                record = self.db.query(Client).get(self.selected_client_id)
                record.nama = nama
                record.no_hp = no_hp if no_hp else None
                record.alamat = alamat if alamat else None
                msg = "Data klien berhasil diperbarui!"
            else:
                record = Client(
                    nama=nama,
                    no_hp=no_hp if no_hp else None,
                    alamat=alamat if alamat else None,
                )
                self.db.add(record)
                msg = "Klien baru berhasil disimpan!"

            self.db.commit()
            self.clear_form()
            self.load_data()
            if self.notifier:
                self.notifier.database_changed.emit()
            QMessageBox.information(self, "Sukses", msg)

        except Exception as e:
            self.db.rollback()
            self.db.expire_all()
            QMessageBox.critical(self, "Error", f"Gagal menyimpan: {e}")

    # ====================================================================
    # DELETE
    # ====================================================================
    def delete_client(self):
        if not self.selected_client_id:
            return

        reply = QMessageBox.question(
            self, "Konfirmasi Hapus",
            "Yakin ingin menghapus klien ini?\n\n"
            "Data transaksi (penjualan & piutang) yang terkait dengan "
            "klien ini TIDAK akan dihapus.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        try:
            record = self.db.query(Client).get(self.selected_client_id)
            record.is_deleted = 1
            self.db.commit()
            self.clear_form()
            self.load_data()
            if self.notifier:
                self.notifier.database_changed.emit()
            QMessageBox.information(self, "Sukses", "Klien berhasil dihapus.")

        except Exception as e:
            self.db.rollback()
            self.db.expire_all()
            QMessageBox.critical(self, "Error", f"Gagal menghapus: {e}")

    # ====================================================================
    # CLEAR FORM
    # ====================================================================
    def clear_form(self):
        self.selected_client_id = None
        self.input_nama.clear()
        self.input_hp.clear()
        self.input_alamat.clear()
        self.btn_save.setText("SIMPAN KLIEN")
        self.btn_delete.setEnabled(False)
        self.table.clearSelection()

    # ====================================================================
    # CLOSE
    # ====================================================================
    def closeEvent(self, event):
        self.db.close()
        super().closeEvent(event)
