# app_essa/main.py

import sys
import os
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QStackedWidget, QFrame
)
from PySide6.QtCore import Qt, QObject, Signal, QThread, QTimer

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

class _CloudSyncWorker(QThread):
    """Jalankan sinkronisasi DUA ARAH di thread latar — dipakai tombol
    'SYNC NOW' di sidebar (Fase 7). Tidak pernah menggagalkan UI."""
    done = Signal(dict)

    def run(self):
        try:
            from utils.cloud_sync import sync_local_to_cloud
            self.done.emit(sync_local_to_cloud())
        except Exception as e:
            self.done.emit({"status": "error", "message": str(e)})

class YazminaMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Yazmina Hijab - Unified Operations Platform")
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
        lbl_brand = QLabel("Yazmina Hijab")
        lbl_brand.setStyleSheet(f"font-size: 22pt; font-weight: bold; color: {Theme.NEON_CYAN};")
        lbl_brand.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_brand.setWordWrap(True)  # aman utk teks brand yang lebih panjang
        
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

        # --- Cloud Sync (Fase 7): indikator status + tombol sinkronisasi manual ---
        self._build_cloud_footer(sidebar_layout)

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

    # ── Cloud Sync Footer (Fase 7) ──────────────────────────────────
    def _build_cloud_footer(self, sidebar_layout):
        """Panel kecil di sidebar: indikator status cloud + tombol 'SYNC NOW'."""
        self._syncing = False

        self.lbl_cloud_status = QLabel("☁ CLOUD NONAKTIF")
        self.lbl_cloud_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_cloud_status.setWordWrap(True)
        self.lbl_cloud_status.setStyleSheet(
            f"color: {Theme.TEXT_MUTED}; font-size: 8pt; letter-spacing: 1px;"
        )
        sidebar_layout.addWidget(self.lbl_cloud_status)

        self.btn_sync_now = CyberButton("⟳ SYNC NOW")
        self.btn_sync_now.clicked.connect(self.start_manual_sync)
        sidebar_layout.addWidget(self.btn_sync_now)

        self.refresh_cloud_status()

    def _set_cloud_status(self, text, color):
        """Ubah teks + warna label status cloud."""
        self.lbl_cloud_status.setText(text)
        self.lbl_cloud_status.setStyleSheet(
            f"color: {color}; font-size: 8pt; letter-spacing: 1px;"
        )

    def refresh_cloud_status(self):
        """Baca metadata sync lokal (cloud_last_sync) & tampilkan status cloud."""
        try:
            from data.database import SessionLocal, get_cloud_engine
            from data.models.master import AppSetting
            cloud_on = get_cloud_engine() is not None
            if not self._syncing:
                self.btn_sync_now.setEnabled(cloud_on)
            if not cloud_on:
                self._set_cloud_status("☁ CLOUD NONAKTIF", Theme.TEXT_MUTED)
                return
            db = SessionLocal()
            try:
                rows = db.query(AppSetting).filter(
                    AppSetting.key.in_(("cloud_last_sync", "cloud_last_error"))
                ).all()
                vals = {r.key: (r.value or "").strip() for r in rows}
                last = vals.get("cloud_last_sync") or None
                last_err = vals.get("cloud_last_error")
            finally:
                db.close()
            if last_err:
                # Sync terakhir GAGAL (mis. jaringan/DNS) — jangan tampilkan
                # "TERSINKRON" yang menyesatkan. Tombol tetap aktif utk retry.
                self._set_cloud_status("☁ OFFLINE · SYNC GAGAL", Theme.NEON_YELLOW)
                return
            if last:
                self._set_cloud_status(f"☁ TERSINKRON · {last[:16]}", Theme.NEON_CYAN)
            else:
                self._set_cloud_status("☁ CLOUD SIAP · BELUM SYNC", Theme.NEON_YELLOW)
        except Exception as e:
            print(f"[CloudSync] refresh status gagal: {e}")
            self._set_cloud_status("☁ CLOUD NONAKTIF", Theme.TEXT_MUTED)

    def start_manual_sync(self):
        """Jalankan sinkronisasi dua arah di thread latar (tombol SYNC NOW)."""
        if self._syncing:
            return  # sudah ada sync yang berjalan (auto-pull / manual)
        self._syncing = True
        self.btn_sync_now.setEnabled(False)
        self._set_cloud_status("☁ MENYINKRONKAN...", Theme.NEON_YELLOW)
        self._sync_worker = _CloudSyncWorker(self)
        self._sync_worker.done.connect(self._on_manual_sync_done)
        self._sync_worker.finished.connect(self._sync_worker.deleteLater)
        self._sync_worker.start()

    def _on_manual_sync_done(self, result):
        """Update label setelah sync manual selesai + refresh dashboard."""
        self._syncing = False
        status = result.get("status")
        if status == "ok":
            self._set_cloud_status("☁ SYNC OK", Theme.NEON_CYAN)
            QTimer.singleShot(3000, self.refresh_cloud_status)
        elif status == "skipped":
            self.refresh_cloud_status()
        else:
            self._set_cloud_status("☁ GAGAL · CEK INTERNET", Theme.NEON_PINK)
            QTimer.singleShot(4000, self.refresh_cloud_status)
        global_notifier.database_changed.emit()

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

        # Sinkronisasi dua arah lokal <-> cloud (Fase 5-6).
        # Tidak pernah menghentikan penutupan aplikasi walaupun cloud gagal/offline.
        # Bila sync manual/auto-pull sedang berjalan di thread latar, lewati saja
        # (transaksi sync tidak boleh berjalan dua-duanya secara bersamaan).
        if not getattr(self, "_syncing", False):
            try:
                from utils.cloud_sync import sync_local_to_cloud
                # retries=0: saat menutup aplikasi jangan tunda keluar walau
                # jaringan/DNS bermasalah (sync dicoba lagi di pembukaan berikutnya).
                sync_local_to_cloud(retries=0)
            except Exception:
                pass

        # Accept the close event so the app actually shuts down
        event.accept()

if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)

    # --- Identitas perangkat (Fase 6.3) ---
    # Pastikan device_id lokal ada & beri tahu model agar setiap baris baru
    # dicatat pembuatnya (created_by_device) dan setiap edit dicatat
    # (updated_by_device) — fondasi kepemilikan baris antar perangkat.
    try:
        from utils.cloud_sync import ensure_device_id
        ensure_device_id()
    except Exception:
        pass

    # --- Startup sync: MasterTarifPenjahit ← TarifMaster ---
    # Memastikan semua data tarif_jahit tersedia di dropdown Penjahit Payroll
    from data.database import SessionLocal
    from data.models.salary import MasterTarifPenjahit
    from data.models.master import TarifMaster
    _sync_db = SessionLocal()
    try:
        _unsynced = (
            _sync_db.query(TarifMaster)
            .filter(
                TarifMaster.tarif_jahit > 0,
                ~TarifMaster.kode_sku.in_(
                    _sync_db.query(MasterTarifPenjahit.kode_garapan).filter(
                        MasterTarifPenjahit.is_active == 1
                    )
                ),
            )
            .all()
        )
        for _u in _unsynced:
            _sync_db.add(
                MasterTarifPenjahit(
                    kode_garapan=_u.kode_sku,
                    harga=_u.tarif_jahit,
                    is_active=1,
                )
            )
        if _unsynced:
            _sync_db.commit()
    finally:
        _sync_db.close()
    # ------------------------------------------------

    app = QApplication(sys.argv)
    window = YazminaMainWindow()
    window.show()

    # --- Startup: sinkronisasi dua arah otomatis (Fase 5.5 + 6.2) ---
    # Dijalankan di THREAD LATAR agar window langsung tampil (tidak membeku
    # saat Neon cold start): perangkat baru mengunduh seluruh data cloud,
    # perangkat lama menarik perubahan perangkat lain & mengirim perubahan
    # lokal. Setelah selesai, sinyal database_changed memicu refresh dashboard.
    # Gagal/offline => dilewati tanpa mengganggu aplikasi.
    try:
        class _CloudPullWorker(QThread):
            done = Signal()
            def run(self):
                try:
                    from utils.cloud_sync import maybe_auto_pull
                    maybe_auto_pull()
                except Exception:
                    pass
                self.done.emit()

        def _after_startup_pull():
            # Auto-pull selesai -> izinkan tombol SYNC NOW lagi + perbarui status
            window._syncing = False
            window.refresh_cloud_status()

        window._syncing = True          # cegah double-sync saat auto-pull berjalan
        window.btn_sync_now.setEnabled(False)
        _worker = _CloudPullWorker(window)
        _worker.done.connect(global_notifier.database_changed.emit)
        _worker.done.connect(_after_startup_pull)
        _worker.finished.connect(_worker.deleteLater)
        _worker.start()
    except Exception:
        pass

    sys.exit(app.exec())