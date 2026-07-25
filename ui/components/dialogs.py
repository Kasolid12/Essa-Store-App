# app_essa/ui/components/dialogs.py
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPlainTextEdit,
    QPushButton, QApplication
)
from PySide6.QtCore import Qt
from ui.theme import Theme


class CopyableErrorDialog(QDialog):
    """
    Error dialog dengan teks yang bisa dipilih, dicopy (Ctrl+C),
    dan tombol "Copy to Clipboard" untuk memudahkan pelaporan bug.
    """
    def __init__(self, parent, title: str, message: str):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumSize(650, 400)
        self.setModal(True)

        self.setStyleSheet(f"""
            QDialog {{
                background-color: {Theme.BG_VOID};
                color: {Theme.TEXT_MAIN};
            }}
            QPlainTextEdit {{
                background-color: #0D0E15;
                color: {Theme.NEON_PINK};
                border: 1px solid {Theme.BORDER_DIM};
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 10pt;
                padding: 10px;
                selection-background-color: {Theme.NEON_CYAN};
                selection-color: {Theme.BG_VOID};
            }}
            QPushButton {{
                background-color: transparent;
                border: 1px solid {Theme.NEON_CYAN};
                color: {Theme.NEON_CYAN};
                padding: 8px 16px;
                font-weight: bold;
                font-size: 10pt;
            }}
            QPushButton:hover {{
                background-color: {Theme.NEON_CYAN};
                color: {Theme.BG_VOID};
            }}
            QPushButton#BtnCopy {{
                border: 1px solid {Theme.NEON_YELLOW};
                color: {Theme.NEON_YELLOW};
            }}
            QPushButton#BtnCopy:hover {{
                background-color: {Theme.NEON_YELLOW};
                color: {Theme.BG_VOID};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        # Label instruksi
        lbl_info = QPushButton("📋  DETAIL ERROR (teks bisa dipilih & dicopy)")
        lbl_info.setStyleSheet(
            f"color: {Theme.TEXT_MUTED}; font-size: 10pt; "
            f"border: none; text-align: left; padding: 0;"
        )
        lbl_info.setEnabled(False)
        layout.addWidget(lbl_info)

        # Text area — selectable & copyable
        self.text_edit = QPlainTextEdit()
        self.text_edit.setPlainText(message)
        self.text_edit.setReadOnly(True)
        self.text_edit.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.text_edit.selectAll()  # Auto-select so user can Ctrl+C immediately
        layout.addWidget(self.text_edit, stretch=1)

        # Button row
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        btn_copy = QPushButton("📋 COPY TO CLIPBOARD")
        btn_copy.setObjectName("BtnCopy")
        btn_copy.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_copy.clicked.connect(self._copy_to_clipboard)
        btn_row.addWidget(btn_copy)

        btn_row.addStretch()

        btn_close = QPushButton("TUTUP")
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.clicked.connect(self.accept)
        btn_row.addWidget(btn_close)

        layout.addLayout(btn_row)

    def _copy_to_clipboard(self):
        """Copy all text to system clipboard."""
        clipboard = QApplication.clipboard()
        clipboard.setText(self.text_edit.toPlainText())
        # Feedback: flash the button briefly
        self._flash_button()

    def _flash_button(self):
        """Brief visual feedback that text was copied."""
        btn = self.findChild(QPushButton, "BtnCopy")
        if btn:
            original = btn.styleSheet()
            btn.setStyleSheet(
                f"background-color: {Theme.NEON_YELLOW}; color: {Theme.BG_VOID};"
                f" border: 1px solid {Theme.NEON_YELLOW}; padding: 8px 16px;"
                f" font-weight: bold;"
            )
            btn.setText("✅ COPIED!")
            from PySide6.QtCore import QTimer
            QTimer.singleShot(1500, lambda: (
                btn.setStyleSheet(original),
                btn.setText("📋 COPY TO CLIPBOARD")
            ))
