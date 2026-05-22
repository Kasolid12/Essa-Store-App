# app_essa/ui/components/buttons.py
from PySide6.QtWidgets import QPushButton
from PySide6.QtCore import Qt

class CyberButton(QPushButton):
    """A sharp, industrial button with neon hover effects."""
    def __init__(self, text, is_danger=False, parent=None):
        super().__init__(text, parent)
        
        # Apply the pointer cursor so it feels like a web app
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # If it's a delete/cancel button, tag it for the QSS to make it pink
        if is_danger:
            self.setObjectName("BtnDanger")