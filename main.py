# app_essa/main.py

import sys
import os
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QStackedWidget, QFrame
)
from PySide6.QtCore import Qt, QObject, Signal

# Import your custom UI components
from ui.theme import Theme
from ui.components.buttons import CyberButton
from ui.views.harian_view import CatatanHarianView
from ui.views.master_view import MasterDataView
from ui.views.hutang_view import HutangView
from ui.views.gaji_view import GajiView
from ui.views.stock_view import StockView
from ui.views.invoice_view import InvoiceView
from ui.views.profit_view import ProfitSimulationView
from ui.views.dashboard_view import DashboardView
from utils.backup_engine import backup_database
from data.database import engine
from data.models.base import Base
import data.models

class DataSignals(QObject):
    # Sinyal universal yang dipicu setiap kali database berubah
    database_changed = Signal()

# Definisikan objek notifier global yang bisa diakses oleh seluruh view
global_notifier = DataSignals()

class ESSAMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ESSA STORE - Unified Operations Platform")
        self.setMinimumSize(1200, 800) # Give it a wide, dashboard feel

        # 1. APPLY THE GLOBAL THEME
        self.setStyleSheet(Theme.GLOBAL_STYLESHEET)

        # Setup Main Layout Structure
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        # Horizontal layout to split Sidebar (Left) and Content (Right)
        self.main_layout = QHBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # Build the two halves of the screen
        self.build_sidebar()
        self.build_content_area()
    
    def build_sidebar(self):
        # Sidebar Container
        self.sidebar = QFrame()
        self.sidebar.setObjectName("GridPanel") # This triggers the dark panel CSS
        self.sidebar.setFixedWidth(260)
        
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(20, 30, 20, 30)
        sidebar_layout.setSpacing(15)

        # --- Branding Area ---
        lbl_brand = QLabel("ESSA STORE")
        lbl_brand.setStyleSheet(f"font-size: 22pt; font-weight: bold; color: {Theme.NEON_CYAN};")
        lbl_brand.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        lbl_sub = QLabel("OPERATIONS OS v0.8")
        lbl_sub.setStyleSheet(f"font-size: 9pt; color: {Theme.TEXT_MUTED}; letter-spacing: 2px;")
        lbl_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)

        sidebar_layout.addWidget(lbl_brand)
        sidebar_layout.addWidget(lbl_sub)
        sidebar_layout.addSpacing(40) # Gap before buttons

        # --- Navigation Buttons ---
        self.nav_buttons = {}
        # Define our main menus
        menus = [
            ("dashboard", "DASHBOARD"),
            ("harian", "CATATAN HARIAN"),
            ("hutang", "HUTANG & PELUNASAN"),
            ("gaji", "PAYROLL & BON"),
            ("stok", "STOCK MANAGER"),
            ("invoice", "INVOICE & PIUTANG"),
            ("profit", "PROFIT SIMULATION"),
            ("master", "DATA MANAGER")
        ]

        for key, label in menus:
            btn = CyberButton(label)
            # Link button click to the page switching function
            btn.clicked.connect(lambda checked=False, k=key: self.switch_page(k))
            self.nav_buttons[key] = btn
            sidebar_layout.addWidget(btn)

        sidebar_layout.addStretch() # Pushes everything up

        # --- Footer Area ---
        btn_exit = CyberButton("EXIT SYSTEM", is_danger=True)
        btn_exit.clicked.connect(self.close)
        sidebar_layout.addWidget(btn_exit)

        # Add sidebar to main layout
        self.main_layout.addWidget(self.sidebar)

    def build_content_area(self):
        self.content_area = QFrame()
        content_layout = QVBoxLayout(self.content_area)
        content_layout.setContentsMargins(30, 30, 30, 30)

        self.stacked_widget = QStackedWidget()
        self.pages = {} # Hanya simpan dictionary kosong di awal

        # Render Dashboard saja di awal
        page_dash = DashboardView(notifier=global_notifier)
        self.pages["dashboard"] = page_dash
        self.stacked_widget.addWidget(page_dash)

        content_layout.addWidget(self.stacked_widget)
        self.main_layout.addWidget(self.content_area)

    def switch_page(self, page_key):
        """Switches the active page. Lazy-loads the page if it hasn't been created yet."""
        if page_key not in self.pages:
            # Render modul HANYA jika tombolnya diklik
            if page_key == "harian": self.pages[page_key] = CatatanHarianView(notifier=global_notifier)
            elif page_key == "master": self.pages[page_key] = MasterDataView(notifier=global_notifier)
            elif page_key == "hutang": self.pages[page_key] = HutangView(notifier=global_notifier)
            elif page_key == "gaji": self.pages[page_key] = GajiView(notifier=global_notifier)
            elif page_key == "stok": self.pages[page_key] = StockView(notifier=global_notifier)
            elif page_key == "invoice": self.pages[page_key] = InvoiceView(notifier=global_notifier)
            elif page_key == "profit": self.pages[page_key] = ProfitSimulationView(notifier=global_notifier)
            
            # Tambahkan ke tumpukan widget
            self.stacked_widget.addWidget(self.pages[page_key])

        self.stacked_widget.setCurrentWidget(self.pages[page_key])
    
    def closeEvent(self, event):
        """Fires automatically when the user clicks the X to close the window."""
        # Run the backup engine silently in the background
        backup_database()
        
        # Accept the close event so the app actually shuts down
        event.accept()

if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    app = QApplication(sys.argv)
    window = ESSAMainWindow()
    window.show()
    sys.exit(app.exec())