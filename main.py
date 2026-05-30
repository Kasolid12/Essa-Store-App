# app_essa/main.py

import sys
import os
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QStackedWidget, QFrame
)
from PySide6.QtCore import Qt

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
from ui.views.bi_agent_view import BIAgentView
from utils.backup_engine import backup_database

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
            ("agent", "BI AGENT"),
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
        # The Content Area holds multiple pages we can switch between seamlessly
        self.content_area = QFrame()
        content_layout = QVBoxLayout(self.content_area)
        content_layout.setContentsMargins(30, 30, 30, 30)

        # QStackedWidget acts like a deck of cards; only one page is visible at a time
        self.stacked_widget = QStackedWidget()
        self.pages = {}
        
        # 1. Dashboard Placeholder
        page_dash = QWidget()
        lay_dash = QVBoxLayout(page_dash)
        title_dash = QLabel("SYSTEM DASHBOARD")
        title_dash.setStyleSheet(f"font-size: 28pt; font-weight: bold; color: {Theme.TEXT_MAIN};")
        lay_dash.addWidget(title_dash)
        lay_dash.addStretch()
        self.pages["dashboard"] = page_dash
        self.stacked_widget.addWidget(page_dash)

        # 2. Catatan Harian (REAL VIEW)
        page_harian = CatatanHarianView()
        self.pages["harian"] = page_harian
        self.stacked_widget.addWidget(page_harian)
        
        # 3. Data Manager (REAL VIEW)
        page_master = MasterDataView()
        self.pages["master"] = page_master
        self.stacked_widget.addWidget(page_master)
        
        # 4. Hutang Manager (REAL VIEW)
        page_hutang = HutangView()
        self.pages["hutang"] = page_hutang
        self.stacked_widget.addWidget(page_hutang)
        
        # 5. Gaji & Bon Manager (REAL VIEW)
        page_gaji = GajiView()
        self.pages["gaji"] = page_gaji
        self.stacked_widget.addWidget(page_gaji)
        
        # 6. Stock Manager (REAL VIEW)
        page_stok = StockView()
        self.pages["stok"] = page_stok
        self.stacked_widget.addWidget(page_stok)
        
        # 7. Invoice & Piutang (REAL VIEW)
        page_invoice = InvoiceView()
        self.pages["invoice"] = page_invoice
        self.stacked_widget.addWidget(page_invoice)
        
        # 8. Profit Simulation
        page_profit = ProfitSimulationView()
        self.pages["profit"] = page_profit
        self.stacked_widget.addWidget(page_profit)
        
        page_bi_agent = BIAgentView()
        self.pages["agent"] = page_bi_agent
        self.stacked_widget.addWidget(page_bi_agent)

        content_layout.addWidget(self.stacked_widget)
        self.main_layout.addWidget(self.content_area)

    def switch_page(self, page_key):
        """Switches the active page in the main viewing area."""
        if page_key in self.pages:
            self.stacked_widget.setCurrentWidget(self.pages[page_key])
    
    def closeEvent(self, event):
        """Fires automatically when the user clicks the X to close the window."""
        # Run the backup engine silently in the background
        backup_database()
        
        # Accept the close event so the app actually shuts down
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ESSAMainWindow()
    window.show()
    sys.exit(app.exec())