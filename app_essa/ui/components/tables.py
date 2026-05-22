# app_essa/ui/components/tables.py
from PySide6.QtWidgets import QTableWidget, QHeaderView, QAbstractItemView
from PySide6.QtCore import Qt

class CyberTable(QTableWidget):
    """A standardized, high-contrast data table for the ESSA platform."""
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # UI Behavior Settings
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers) # Read-only by default
        self.setAlternatingRowColors(True)
        self.setShowGrid(True)
        
        # Header Settings
        header = self.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch) # Auto-fill width
        header.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        
        # Hide the vertical row numbers for a cleaner look
        self.verticalHeader().setVisible(False)