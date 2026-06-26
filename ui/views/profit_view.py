# app_essa/ui/views/profit_view.py
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, 
    QFrame, QComboBox, QMessageBox, QGroupBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from ui.components.buttons import CyberButton
from ui.theme import Theme
from datetime import datetime

from data.database import SessionLocal
from data.models.debt import DebtEntry
from data.models.catatan_harian import HasilCutting, DistribusiCutting
from data.models.sku import SkuMaster
from data.models.master import TarifMaster
from data.models.profit_history import ProfitHistory

class ProfitSimulationView(QWidget):
    def __init__(self, notifier=None):
        super().__init__()
        self.db = SessionLocal()
        self.notifier = notifier
        # --- KONSTANTA BIAYA PRODUKSI ---
        self.COST_PACK = 100
        self.COST_HANGTAG = 97
        self.COST_WOVEN = 150
        self.COST_HTROPE = 20
        self.COST_THREAD = 100
        self.COST_AKRILIK = 250
        
        self.setup_ui()
        self.load_kode_produksi()
        if self.notifier:
            self.notifier.database_changed.connect(self.refresh_harian_tables)

    def refresh_harian_tables(self):
        """Menyegarkan seluruh grid tabel catatan harian jika ada perubahan data di menu lain"""
        self.db.expire_all()
        # Masukkan semua fungsi load data harian Anda di bawah ini
        if hasattr(self, 'load_kode_produksi'): self.load_kode_produksi()
    
    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)

        # --- HEADER ---
        title = QLabel("REAL-TIME PROFIT ANALYZER")
        title.setStyleSheet(f"font-size: 24pt; font-weight: bold; color: {Theme.NEON_CYAN};")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title)

        # --- SECTION 1: PEMILIHAN BATCH (KODE PRODUKSI) ---
        filter_frame = QFrame()
        filter_frame.setObjectName("GridPanel") # Mewarisi CSS dark panel dari tema utama
        filter_lay = QHBoxLayout(filter_frame)
        
        self.cb_kode_prod = QComboBox()
        self.cb_kode_prod.setMinimumWidth(300)
        # Diperbaiki: Menggunakan hex color #15151a untuk latar belakang combo box
        self.cb_kode_prod.setStyleSheet(f"background-color: #15151a; color: {Theme.TEXT_MAIN}; padding: 8px; border: 1px solid #2d2d38; border-radius: 4px;")
        
        btn_tarik = CyberButton("TARIK DATA & ANALISIS")
        btn_tarik.clicked.connect(self.proses_analisis)

        filter_lay.addWidget(QLabel("Pilih Kode Produksi:"), 0, Qt.AlignmentFlag.AlignRight)
        filter_lay.addWidget(self.cb_kode_prod, 1)
        filter_lay.addWidget(btn_tarik, 0)
        main_layout.addWidget(filter_frame)

        # --- SECTION 2: DASHBOARD INFO DATA ---
        info_layout = QHBoxLayout()
        info_layout.setSpacing(15)
        
        # Panel 2A: Data Modal Bahan
        self.grp_kain = QGroupBox("DATA MODAL BAHAN (Hutang Modal)")
        self.grp_kain.setStyleSheet(self.get_groupbox_style())
        lay_kain = QGridLayout(self.grp_kain)
        
        self.lbl_kain_qty = QLabel("-"); self.lbl_kain_hrg = QLabel("-")
        self.lbl_kain_tot = QLabel("-")
        self.lbl_kain_tot.setStyleSheet(f"color: {Theme.NEON_PINK}; font-weight: bold; font-size: 14pt;")
        
        lay_kain.addWidget(QLabel("Total Qty Kain (Kg):"), 0, 0); lay_kain.addWidget(self.lbl_kain_qty, 0, 1)
        lay_kain.addWidget(QLabel("Harga Beli / Kg:"), 1, 0); lay_kain.addWidget(self.lbl_kain_hrg, 1, 1)
        lay_kain.addWidget(QLabel("Total Modal Bahan:"), 2, 0); lay_kain.addWidget(self.lbl_kain_tot, 2, 1)
        
        self.lbl_status_kain = QLabel("-")
        self.btn_toggle_kain = CyberButton("TANDAI KAIN HABIS (FULL CUT)")
        self.btn_toggle_kain.clicked.connect(self.toggle_status_kain)
        self.btn_toggle_kain.hide()
        
        lay_kain.addWidget(QLabel("Status Kain:"), 3, 0); lay_kain.addWidget(self.lbl_status_kain, 3, 1)
        lay_kain.addWidget(self.btn_toggle_kain, 4, 0, 1, 2)
        
        # Panel 2B: Data Produksi & Distribusi
        self.grp_dist = QGroupBox("DATA PRODUKSI & DISTRIBUSI")
        self.grp_dist.setStyleSheet(self.get_groupbox_style())
        lay_dist = QGridLayout(self.grp_dist)
        
        self.lbl_cut_qty = QLabel("-"); self.lbl_dist_home = QLabel("-")
        self.lbl_dist_sup = QLabel("-"); self.lbl_dist_status = QLabel("Belum ditarik")
        self.lbl_dist_status.setStyleSheet(f"color: {Theme.TEXT_MUTED}; font-weight: bold;")
        
        lay_dist.addWidget(QLabel("Total Hasil Cutting (Pcs):"), 0, 0); lay_dist.addWidget(self.lbl_cut_qty, 0, 1)
        lay_dist.addWidget(QLabel("Distribusi Penjahit (Home):"), 1, 0); lay_dist.addWidget(self.lbl_dist_home, 1, 1)
        lay_dist.addWidget(QLabel("Distribusi Peng-sup:"), 2, 0); lay_dist.addWidget(self.lbl_dist_sup, 2, 1)
        lay_dist.addWidget(QLabel("Status Verifikasi:"), 3, 0); lay_dist.addWidget(self.lbl_dist_status, 3, 1)
        
        info_layout.addWidget(self.grp_kain)
        info_layout.addWidget(self.grp_dist)
        main_layout.addLayout(info_layout)

        # --- SECTION 3: HASIL KALKULASI PROFIT ---
        self.grp_result = QGroupBox("LAPORAN LABA BERSIH (NET PROFIT)")
        self.grp_result.setStyleSheet(self.get_groupbox_style())
        lay_result = QGridLayout(self.grp_result)
        lay_result.setSpacing(12)

        self.lbl_rev = QLabel("-")
        self.lbl_gross = QLabel("-")
        self.lbl_cost_home = QLabel("-")
        self.lbl_cost_sup = QLabel("-")
        self.lbl_net = QLabel("-")

        val_style = f"font-size: 14pt; font-weight: bold; color: {Theme.TEXT_MAIN};"
        for lbl in [self.lbl_rev, self.lbl_gross, self.lbl_cost_home, self.lbl_cost_sup]:
            lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            lbl.setStyleSheet(val_style)
            
        self.lbl_net.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.lbl_net.setStyleSheet(f"font-size: 24pt; font-weight: bold; color: {Theme.TEXT_MUTED};")

        lay_result.addWidget(QLabel("A. Estimasi Pendapatan (Omzet)"), 0, 0); lay_result.addWidget(self.lbl_rev, 0, 1)
        lay_result.addWidget(QLabel("B. Gross Margin (Pendapatan - Modal Kain)"), 1, 0); lay_result.addWidget(self.lbl_gross, 1, 1)
        
        # Diperbaiki: Menggunakan hex #2d2d38 untuk garis pemisah
        line = QFrame(); line.setFrameShape(QFrame.Shape.HLine); line.setStyleSheet("background-color: #2d2d38;")
        lay_result.addWidget(line, 2, 0, 1, 2)

        lay_result.addWidget(QLabel("C. Beban Produksi Home (Sesuai SKU)"), 3, 0); lay_result.addWidget(self.lbl_cost_home, 3, 1)
        lay_result.addWidget(QLabel("D. Beban Produksi Supplier (Sesuai SKU)"), 4, 0); lay_result.addWidget(self.lbl_cost_sup, 4, 1)
        
        # Diperbaiki: Menggunakan hex #2d2d38 untuk garis pemisah ke-2
        line2 = QFrame(); line2.setFrameShape(QFrame.Shape.HLine); line2.setStyleSheet("background-color: #2d2d38;")
        lay_result.addWidget(line2, 5, 0, 1, 2)

        lbl_net_title = QLabel("LABA BERSIH (NET PROFIT)")
        lbl_net_title.setStyleSheet(f"font-size: 16pt; font-weight: bold; color: {Theme.NEON_CYAN};")
        lay_result.addWidget(lbl_net_title, 6, 0)
        lay_result.addWidget(self.lbl_net, 6, 1)

        main_layout.addWidget(self.grp_result)
        main_layout.addStretch()

    def get_groupbox_style(self):
        """Helper untuk styling QGroupBox dengan hex color aman."""
        # Diperbaiki: Menggunakan #1e1e24 untuk bg panel dan #2d2d38 untuk border panel
        return f"""
        QGroupBox {{
            background-color: #1e1e24;
            border: 1px solid #2d2d38;
            border-radius: 8px;
            margin-top: 15px;
            padding-top: 15px;
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            subcontrol-position: top left;
            padding: 0 8px;
            color: {Theme.NEON_CYAN};
            font-weight: bold;
        }}
        QLabel {{ color: {Theme.TEXT_MAIN}; }}
        """

    def format_rupiah(self, value):
        return f"Rp {value:,.0f}".replace(",", ".")

    def reset_result(self):
        for lbl in [self.lbl_rev, self.lbl_gross, self.lbl_cost_home, self.lbl_cost_sup, self.lbl_net]:
            lbl.setText("-")
        self.lbl_net.setStyleSheet(f"font-size: 24pt; font-weight: bold; color: {Theme.TEXT_MUTED};")

    def load_kode_produksi(self):
        """Menarik list kode produksi langsung dari database (Tabel Hutang Modal)"""
        # Ingat pilihan saat ini supaya tidak hilang ketika combo di-reload
        # (mis. oleh refresh_harian_tables setelah profit disimpan).
        prev_kode = self.cb_kode_prod.currentText()
        self.cb_kode_prod.clear()

        # Tarik semua kode_produksi yang tidak kosong dari DebtEntry
        kodes = self.db.query(DebtEntry.kode_produksi).filter(DebtEntry.kode_produksi.isnot(None)).distinct().all()
        kode_list = sorted([k[0] for k in kodes if k[0]], reverse=True)

        if kode_list:
            self.cb_kode_prod.addItems(kode_list)
            # Kembalikan pilihan sebelumnya bila masih tersedia
            idx = self.cb_kode_prod.findText(prev_kode)
            if idx >= 0:
                self.cb_kode_prod.setCurrentIndex(idx)
        else:
            self.cb_kode_prod.addItem("-- Belum ada data produksi --")

    def identify_sku_components(self, sku_string):
        """Memisahkan kode dasar dan ukuran untuk mendeteksi aturan biaya khusus (seperti Akrilik)"""
        target = str(sku_string).strip().upper()
        parts = target.split('-')
        base = parts[0]
        size = ""
        for p in parts:
            if p in ["S", "M", "L", "XL", "Adila"]:
                size = p
                break
        return base, size, target

    def get_sewing_cost(self, sku_kode):
        """Mencari ongkos jahit (Home) dari TarifMaster"""
        # 1. Cek kecocokan persis (misal: "DG-L")
        tarif = self.db.query(TarifMaster).filter(TarifMaster.kode_sku == sku_kode).first()
        if tarif and (tarif.tarif_jahit or 0) > 0:
            return tarif.tarif_jahit

        # 2. Fallback 1: Coba cari Base-Size (Misal sku aslinya "DG-Almond-L", kita cari "DG-L")
        base, size, target = self.identify_sku_components(sku_kode)
        if size:
            fallback_1 = f"{base}-{size}"
            tarif_f1 = self.db.query(TarifMaster).filter(TarifMaster.kode_sku == fallback_1).first()
            if tarif_f1 and (tarif_f1.tarif_jahit or 0) > 0:
                return tarif_f1.tarif_jahit

        # 3. Fallback 2: Coba cari Base-nya saja (Misal "DG")
        tarif_f2 = self.db.query(TarifMaster).filter(TarifMaster.kode_sku == base).first()
        if tarif_f2 and (tarif_f2.tarif_jahit or 0) > 0:
            return tarif_f2.tarif_jahit

        # Default terakhir jika SKU benar-benar belum didaftarkan di Master
        return 700.0 

    def get_service_cost(self, sku_kode):
        """Mencari ongkos potong (Pengsup) menggunakan kolom 'Potongan'"""
        # 1. Cek kecocokan persis (karena Pengsup biasanya mendata sampai ke warna, misal "DG-Almond-L")
        tarif = self.db.query(TarifMaster).filter(TarifMaster.kode_sku == sku_kode).first()
        if tarif and (tarif.tarif_pengsup_potongan or 0) > 0:
            return tarif.tarif_pengsup_potongan

        # 2. Fallback (Jaga-jaga jika warna baru belum didaftarkan, ambil harga Base-Size)
        base, size, target = self.identify_sku_components(sku_kode)
        if size:
            fallback_1 = f"{base}-{size}"
            tarif_f1 = self.db.query(TarifMaster).filter(TarifMaster.kode_sku == fallback_1).first()
            if tarif_f1 and (tarif_f1.tarif_pengsup_potongan or 0) > 0:
                return tarif_f1.tarif_pengsup_potongan

        tarif_f2 = self.db.query(TarifMaster).filter(TarifMaster.kode_sku == base).first()
        if tarif_f2 and (tarif_f2.tarif_pengsup_potongan or 0) > 0:
            return tarif_f2.tarif_pengsup_potongan

        return 1500.0

    def get_harga_jual(self, sku_kode):
        """Mencari harga jual resmi untuk estimasi omzet"""
        sku = self.db.query(SkuMaster).filter(SkuMaster.kode_sku == sku_kode).first()
        if sku and sku.harga_jual is not None:
            return sku.harga_jual
        return 0.0

    def proses_analisis(self):
        """Core Engine: Menarik data SQL dan menghitung Laba Rugi"""
        target_kode = self.cb_kode_prod.currentText()
        if not target_kode or target_kode.startswith("--"): return

        try:
            # --- 1. TARIK DATA MODAL KAIN (SQL Query) ---
            hutangs = self.db.query(DebtEntry).filter(
                DebtEntry.kode_produksi == target_kode, 
                DebtEntry.tipe_hutang == 'MODAL'
            ).all()
            
            kain_qty = sum(h.qty for h in hutangs if h.qty) 
            kain_total = sum(h.nominal_hutang for h in hutangs)
            kain_harga = kain_total / kain_qty if kain_qty > 0 else 0

            # --- TAMBAHKAN LOGIKA DETEKSI STATUS INI ---
            if hutangs:
                status_kain = getattr(hutangs[0], 'status_cutting', 'OPEN')
                self.btn_toggle_kain.show()
                if status_kain == 'SELESAI':
                    self.lbl_status_kain.setText("FULL CUTTING ✓")
                    self.lbl_status_kain.setStyleSheet(f"color: {Theme.NEON_CYAN}; font-weight: bold;")
                    self.btn_toggle_kain.setText("BATALKAN FULL CUT (BUKA LAGI)")
                else:
                    self.lbl_status_kain.setText("BELUM FULL (Masih Sisa)")
                    self.lbl_status_kain.setStyleSheet(f"color: {Theme.NEON_YELLOW}; font-weight: bold;")
                    self.btn_toggle_kain.setText("TANDAI KAIN HABIS (FULL CUT)")
            else:
                self.btn_toggle_kain.hide()
            # -------------------------------------------
            # --- 2. TARIK DATA HASIL CUTTING (SQL Query) ---
            cuttings = self.db.query(HasilCutting).filter(HasilCutting.kode_produksi == target_kode).all()
            cut_qty = sum(c.qty for c in cuttings)

            # --- 3. TARIK DATA DISTRIBUSI (SQL Query) ---
            distribusis = self.db.query(DistribusiCutting).filter(DistribusiCutting.kode_produksi == target_kode).all()
            
            dist_home = 0; dist_sup = 0
            cost_home_total = 0; cost_sup_total = 0
            total_revenue = 0.0
            sku_missing_price = []

            for dist in distribusis:
                jenis = (dist.jenis or "").lower()
                sku_kode = dist.sku.kode_sku if dist.sku else ""
                qty = dist.qty

                # Identifikasi Rule Khusus
                base, size, target = self.identify_sku_components(sku_kode)
                tambahan_akrilik = self.COST_AKRILIK if base == "DG" else 0
                
                harga_jual = self.get_harga_jual(sku_kode)
                if harga_jual <= 0 and sku_kode not in sku_missing_price:
                    sku_missing_price.append(sku_kode)
                
                total_revenue += (qty * harga_jual)

                # Logika Distribusi
                if "penjahit" in jenis or "home" in jenis:
                    dist_home += qty
                    biaya_jahit = self.get_sewing_cost(sku_kode)
                    biaya_produksi_pcs = biaya_jahit + self.COST_PACK + self.COST_HANGTAG + self.COST_WOVEN + self.COST_HTROPE + self.COST_THREAD + tambahan_akrilik
                    cost_home_total += (qty * biaya_produksi_pcs)
                
                elif "sup" in jenis:
                    dist_sup += qty
                    biaya_service = self.get_service_cost(sku_kode)
                    biaya_produksi_pcs = biaya_service + self.COST_HANGTAG + self.COST_WOVEN + self.COST_HTROPE + tambahan_akrilik
                    cost_sup_total += (qty * biaya_produksi_pcs)

            total_dist = dist_home + dist_sup

            # --- UPDATE UI PANEL INFO ---
            self.lbl_kain_qty.setText(f"{kain_qty:g} Kg")
            self.lbl_kain_hrg.setText(self.format_rupiah(kain_harga))
            self.lbl_kain_tot.setText(self.format_rupiah(kain_total))

            self.lbl_cut_qty.setText(f"{cut_qty} Pcs")
            self.lbl_dist_home.setText(f"{dist_home} Pcs")
            self.lbl_dist_sup.setText(f"{dist_sup} Pcs")

            # --- VERIFIKASI (NON-BLOCKING WARNING) ---
            if cut_qty == 0:
                self.lbl_dist_status.setText("Belum Di-Cutting!")
                self.lbl_dist_status.setStyleSheet("color: #ff5252; font-weight: bold;") # Merah
                self.reset_result()
                QMessageBox.warning(self, "Stop", "Batch ini belum masuk proses Cutting!")
                return # Block karena memang 0 pcs
            
            if total_dist < cut_qty:
                selisih = cut_qty - total_dist
                self.lbl_dist_status.setText(f"Tertahan (Kurang {selisih} pcs)")
                self.lbl_dist_status.setStyleSheet("color: #ffd740; font-weight: bold;") # Kuning
                # LOGIKA BARU: Kita tidak lagi memblokir (return) disini! Simulasi profit tetap muncul.
            else:
                self.lbl_dist_status.setText("Siap Dihitung ✓")
                self.lbl_dist_status.setStyleSheet("color: #69f0ae; font-weight: bold;") # Hijau

            if sku_missing_price:
                missing_str = ", ".join(set(sku_missing_price))
                QMessageBox.information(self, "Info Harga Kosong", f"Beberapa SKU belum memiliki harga jual di database Master SKU:\n\n{missing_str}\n\nPendapatan dihitung Rp 0 untuk produk tersebut.")

            # --- KALKULASI HASIL AKHIR ---
            gross_margin = total_revenue - kain_total
            net_profit = gross_margin - (cost_home_total + cost_sup_total)

            self.lbl_rev.setText(self.format_rupiah(total_revenue))
            self.lbl_gross.setText(self.format_rupiah(gross_margin))
            self.lbl_cost_home.setText(f"- {self.format_rupiah(cost_home_total)}")
            self.lbl_cost_sup.setText(f"- {self.format_rupiah(cost_sup_total)}")
            self.lbl_net.setText(self.format_rupiah(net_profit))

            # Ubah warna Laba Bersih
            if net_profit >= 0:
                self.lbl_net.setStyleSheet(f"font-size: 24pt; font-weight: bold; color: #69f0ae;") # Hijau Neon
            else:
                self.lbl_net.setStyleSheet(f"font-size: 24pt; font-weight: bold; color: #ff5252;") # Merah Neon

            # --- SIMPAN HASIL KALKULASI KE profit_history (upsert per batch) ---
            # Kegagalan menyimpan TIDAK boleh membatalkan tampilan yang sudah benar.
            try:
                self.save_profit_history(
                    hutangs=hutangs,
                    cuttings=cuttings,
                    target_kode=target_kode,
                    total_revenue=total_revenue,
                    kain_total=kain_total,
                    cost_produksi_total=cost_home_total + cost_sup_total,
                    net_profit=net_profit,
                    dist_home=dist_home,
                    dist_sup=dist_sup,
                )
            except Exception as e_save:
                self.db.rollback()
                QMessageBox.warning(
                    self, "Gagal Menyimpan Histori",
                    f"Hasil profit tampil, namun gagal disimpan ke profit_history:\n{e_save}",
                )

        except Exception as e:
            QMessageBox.critical(self, "Fatal Error", f"Terjadi kesalahan SQL:\n{str(e)}")
    
    def save_profit_history(self, hutangs, cuttings, target_kode,
                            total_revenue, kain_total, cost_produksi_total,
                            net_profit, dist_home, dist_sup):
        """Upsert hasil kalkulasi batch ke tabel profit_history.

        Kunci dedup = debt_entry_id (id MODAL hutang terkecil pada batch), supaya
        klik 'TARIK DATA & ANALISIS' berulang atau toggle status TIDAK
        menggandakan baris. Batch tanpa hutang MODAL tetap disimpan sebagai baris
        baru dengan debt_entry_id = None.
        """
        today = datetime.now().strftime("%Y-%m-%d")

        # id MODAL hutang terkecil -> deterministik sebagai kunci batch.
        debt_entry_id = min((h.id for h in hutangs), default=None)

        # Periode = rentang tanggal cutting batch ini (fallback ke hari ini).
        cut_dates = [c.tanggal for c in cuttings if getattr(c, "tanggal", None)]
        periode_mulai = min(cut_dates) if cut_dates else today
        periode_akhir = max(cut_dates) if cut_dates else today

        catatan = f"Batch {target_kode} | Dist Home {dist_home} pcs / Sup {dist_sup} pcs"

        record = None
        if debt_entry_id is not None:
            record = (
                self.db.query(ProfitHistory)
                .filter(ProfitHistory.debt_entry_id == debt_entry_id)
                .first()
            )

        if record is None:
            record = ProfitHistory(debt_entry_id=debt_entry_id)
            self.db.add(record)

        # tanggal_hitung = tanggal kain acuan dari hutang (bukan tanggal proses)
        kain_dates = [h.tanggal for h in hutangs if getattr(h, "tanggal", None)]
        record.tanggal_hitung = min(kain_dates) if kain_dates else today
        record.total_pendapatan = float(total_revenue)
        record.total_modal_kain = float(kain_total)
        record.total_modal_jahit = float(cost_produksi_total)
        record.total_profit = float(net_profit)
        record.periode_mulai = periode_mulai
        record.periode_akhir = periode_akhir
        record.catatan = catatan

        self.db.commit()

        # Beritahu view lain (mis. Dashboard) agar ikut menyegarkan datanya.
        if self.notifier:
            self.notifier.database_changed.emit()

    def toggle_status_kain(self):
        """Fungsi untuk mengubah status kain (OPEN <-> SELESAI)"""
        target_kode = self.cb_kode_prod.currentText()
        if not target_kode or target_kode.startswith("--"): return
        
        try:
            # Cari data hutang modal yang sesuai dengan kode batch
            hutangs = self.db.query(DebtEntry).filter(
                DebtEntry.kode_produksi == target_kode, 
                DebtEntry.tipe_hutang == 'MODAL'
            ).all()
            
            if not hutangs: return
            
            # Cek status saat ini, lalu balikkan nilainya (Toggle)
            current_status = getattr(hutangs[0], 'status_cutting', 'OPEN')
            new_status = 'OPEN' if current_status == 'SELESAI' else 'SELESAI'
            
            # Terapkan ke semua entri hutang di batch tersebut
            for h in hutangs:
                h.status_cutting = new_status
            
            self.db.commit()
            
            # Refresh halaman secara otomatis
            self.proses_analisis()
            
            if new_status == 'SELESAI':
                QMessageBox.information(self, "Terkunci", "Kain ditandai FULL CUTTING!\nKain ini tidak akan muncul lagi di pilihan menu Harian (Cutting).")
            else:
                QMessageBox.information(self, "Terbuka", "Status dikembalikan ke BELUM FULL.\nKain akan muncul kembali di menu Harian (Cutting).")
                
        except Exception as e:
            self.db.rollback()
            self.db.expire_all()
            QMessageBox.critical(self, "Error", f"Gagal mengubah status kain: {e}")