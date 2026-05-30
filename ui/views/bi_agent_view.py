# app_essa/ui/views/bi_agent_view.py
import os
import pandas as pd
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, 
    QTextEdit, QScrollArea, QSizePolicy, QFileDialog
)
from PySide6.QtCore import Qt, QTimer
from ui.theme import Theme
from ui.components.buttons import CyberButton
from data.database import SessionLocal
from data.models import SkuMaster

class ChatBubble(QFrame):
    def __init__(self, text, is_user=False):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 12, 15, 12)
        
        self.label = QLabel(text)
        self.label.setWordWrap(True)
        self.label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.label.setStyleSheet(f"font-size: 11pt; color: {Theme.TEXT_MAIN}; line-height: 1.5;")
        layout.addWidget(self.label)
        
        if is_user:
            self.setStyleSheet(f"""
                QFrame {{
                    background-color: #1a1a24;
                    border: 1px solid {Theme.NEON_CYAN};
                    border-radius: 12px;
                    border-top-right-radius: 0px;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QFrame {{
                    background-color: #252530;
                    border: 1px solid {Theme.NEON_YELLOW};
                    border-radius: 12px;
                    border-top-left-radius: 0px;
                }}
            """)

class BIAgentView(QWidget):
    def __init__(self):
        super().__init__()
        self.db = SessionLocal()
        
        # Variabel untuk menyimpan data Excel/CSV di memori Agen
        self.current_dataframe = None 
        
        self.setup_ui()
        
        welcome_msg = (
            "Halo! Saya adalah <b>ESSA BI Agent</b> 🤖\n\n"
            "Saya terhubung dengan Database Essa Store. Fitur yang tersedia:\n"
            "1. <b>Kalkulator Shopee:</b> Ketik <i>shopee [harga]</i>\n"
            "2. <b>Cek HPP Produk:</b> Ketik <i>hpp [kode]</i>\n"
            "3. <b>Analisis File:</b> Klik tombol <b>📂 UPLOAD DATA</b> di bawah untuk membaca Excel/CSV penjualanimu!\n\n"
            "Apa yang ingin kamu analisis hari ini?"
        )
        self.add_message(welcome_msg, is_user=False)

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(15)

        # --- HEADER ---
        header_layout = QHBoxLayout()
        title = QLabel("ESSA BUSINESS INTELLIGENCE (BI) AGENT")
        title.setStyleSheet(f"font-size: 24pt; font-weight: bold; color: {Theme.NEON_CYAN};")
        header_layout.addWidget(title)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        # --- CHAT AREA ---
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet(f"""
            QScrollArea {{ border: 1px solid {Theme.BORDER_DIM}; border-radius: 8px; background-color: {Theme.BG_VOID}; }}
            QWidget {{ background-color: transparent; }}
        """)
        
        self.chat_container = QWidget()
        self.chat_layout = QVBoxLayout(self.chat_container)
        self.chat_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.chat_layout.setSpacing(15)
        self.chat_layout.setContentsMargins(20, 20, 20, 20)
        
        self.scroll_area.setWidget(self.chat_container)
        layout.addWidget(self.scroll_area, stretch=1)

        # --- INPUT AREA ---
        input_frame = QFrame()
        input_frame.setStyleSheet(f"background-color: {Theme.BG_PANEL}; border: 1px solid {Theme.BORDER_DIM}; border-radius: 8px;")
        input_layout = QHBoxLayout(input_frame)
        
        # TOMBOL UPLOAD BARU
        self.btn_upload = CyberButton("📂 UPLOAD DATA")
        self.btn_upload.setStyleSheet(f"background-color: {Theme.NEON_YELLOW}; color: #000; font-weight: bold;")
        self.btn_upload.setMinimumHeight(70)
        self.btn_upload.clicked.connect(self.upload_file)
        
        self.txt_input = QTextEdit()
        self.txt_input.setPlaceholderText("Ketik pertanyaan, kalkulasi, atau instruksi analisis di sini...")
        self.txt_input.setFixedHeight(70)
        self.txt_input.setStyleSheet(f"""
            QTextEdit {{
                background-color: {Theme.BG_VOID}; color: {Theme.TEXT_MAIN};
                border: 1px solid #2d2d38; border-radius: 6px; padding: 10px; font-size: 11pt;
            }}
        """)
        
        self.btn_send = CyberButton("KIRIM ➣")
        self.btn_send.setMinimumHeight(70)
        self.btn_send.clicked.connect(self.process_input)
        
        input_layout.addWidget(self.btn_upload)
        input_layout.addWidget(self.txt_input, stretch=1)
        input_layout.addWidget(self.btn_send)
        layout.addWidget(input_frame)

    def add_message(self, text, is_user=False):
        bubble = ChatBubble(text, is_user)
        row_layout = QHBoxLayout()
        
        if is_user:
            row_layout.addStretch()
            row_layout.addWidget(bubble)
        else:
            row_layout.addWidget(bubble)
            row_layout.addStretch()
            
        self.chat_layout.addLayout(row_layout)
        QTimer.singleShot(100, lambda: self.scroll_area.verticalScrollBar().setValue(
            self.scroll_area.verticalScrollBar().maximum()
        ))

    def upload_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Upload Data Analisis", "", "Data Files (*.csv *.xlsx *.xls)")
        if not file_path: return
        
        nama_file = os.path.basename(file_path)
        self.add_message(f"<i>[Mengunggah file: {nama_file}]</i>", is_user=True)
        
        # Proses Membaca Data
        try:
            if file_path.endswith('.csv'):
                df = pd.read_csv(file_path)
            else:
                df = pd.read_excel(file_path)
                
            self.current_dataframe = df
            rows, cols = df.shape
            kolom_tersedia = ", ".join(df.columns.tolist())
            
            # Pesan Balasan Agen
            summary = (
                f"✅ <b>File '{nama_file}' berhasil diproses!</b>\n\n"
                f"📊 <b>Ringkasan Data:</b>\n"
                f"• Total Baris Data: {rows:,}\n"
                f"• Total Kolom: {cols}\n"
                f"• Daftar Kolom: <i>{kolom_tersedia}</i>\n\n"
                f"Data saat ini sudah tersimpan di memori saya. "
                f"Apa yang ingin kamu ketahui dari data ini? (Misal: 'Berapa total penjualan?')"
            )
            self.add_message(summary, is_user=False)
            
        except Exception as e:
            self.add_message(f"❌ <b>Gagal membaca file:</b>\n{str(e)}\n\nPastikan format file tidak rusak atau korup.", is_user=False)

    def process_input(self):
        user_text = self.txt_input.toPlainText().strip()
        if not user_text: return
        
        self.txt_input.clear()
        self.add_message(user_text, is_user=True)
        QTimer.singleShot(500, lambda: self.generate_response(user_text.lower()))

    def generate_response(self, text):
        response = ""
        
        # 1. Logika Analisis DataFrame (Membaca file yang sudah diupload)
        if "total" in text or "jumlah" in text or "analisis" in text:
            if self.current_dataframe is not None:
                df = self.current_dataframe
                # Contoh Logika Sederhana: Menampilkan preview 3 baris teratas
                preview = df.head(3).to_html(index=False)
                response = (
                    f"Saya mendeteksi kamu sedang membahas file yang diunggah. "
                    f"Berikut adalah cuplikan (3 baris teratas) dari datamu:\n\n"
                    f"{preview}\n\n"
                    f"<i>(Catatan: Untuk analisis kompleks seperti Pivot Table atau grafik, integrasi API AI/LLM diperlukan.)</i>"
                )
            else:
                response = "⚠️ Kamu belum mengunggah file apa pun. Silakan klik tombol <b>📂 UPLOAD DATA</b> terlebih dahulu."

        # 2. Logika Shopee
        elif text.startswith("shopee"):
            try:
                angka_str = text.replace("shopee", "").replace("rp", "").replace(".", "").strip()
                harga_jual = float(angka_str)
                fee_persen = harga_jual * 0.2025
                fee_fixed = 1900
                total_fee = fee_persen + fee_fixed
                net_diterima = harga_jual - total_fee
                
                response = (
                    f"📊 <b>ANALISIS PENJUALAN SHOPEE</b>\n\n"
                    f"• Harga Jual: <b>Rp {harga_jual:,.0f}</b>\n"
                    f"• Potongan Admin (20.25%): Rp {fee_persen:,.0f}\n"
                    f"• Biaya Layanan/Packing: Rp {fee_fixed:,.0f}\n"
                    f"• Total Potongan: <span style='color:#ff5252;'>- Rp {total_fee:,.0f}</span>\n"
                    f"──────────────────────\n"
                    f"💰 <b>NET DITERIMA: Rp {net_diterima:,.0f}</b>"
                )
            except ValueError:
                response = "⚠️ Format salah. Gunakan format: <b>shopee [harga]</b>\nContoh: shopee 150000"

        # 3. Logika HPP
        elif text.startswith("hpp"):
            sku_target = text.replace("hpp", "").strip().upper()
            if not sku_target:
                response = "⚠️ Harap masukkan kode SKU. Contoh: <b>hpp DG-L</b>"
            else:
                sku_data = self.db.query(SkuMaster).filter(SkuMaster.kode_sku.like(f"%{sku_target}%")).all()
                if sku_data:
                    response = f"🔍 <b>HASIL PENCARIAN HPP '{sku_target}':</b>\n\n"
                    for s in sku_data:
                        hpp_estimasi = (s.kain_cost or 0) + (s.potongan_cost or 0)
                        response += f"• <b>{s.kode_sku}</b> - {s.nama_produk[:20]}...\n  Modal (Kain+Potong): <b>Rp {hpp_estimasi:,.0f}</b> | Harga Jual: Rp {s.harga_jual:,.0f}\n\n"
                else:
                    response = f"❌ SKU '{sku_target}' tidak ditemukan di Database."

        else:
            response = (
                "Maaf, saat ini saya baru diprogram untuk <b>Shopee</b>, <b>HPP</b>, dan membaca ringkasan <b>File Upload</b>. \n\n"
                "<i>(Agar saya bisa memahami pertanyaan secara bebas, API Key perlu disambungkan di masa mendatang!)</i>"
            )

        self.add_message(response, is_user=False)

    def closeEvent(self, event):
        self.db.close()
        super().closeEvent(event)