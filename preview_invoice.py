# preview_invoice.py
# Implementasi CONTOH dari panduan PANDUAN_UPDATE_PDF_ENGINE.md
# Menggunakan data mock (bukan koneksi database asli) supaya bisa dijalankan
# berdiri sendiri untuk preview visual.

import os
from datetime import datetime, date, timedelta
from fpdf import FPDF

# ── Helper (disalin dari pdf_engine.py asli) ──────────────────────────
def format_indo(angka):
    try:
        return f"{int(angka):,}".replace(",", ".")
    except Exception:
        return "0"

def terbilang(angka):
    if angka == 0:
        return "Nol"
    bilangan = ["", "Satu", "Dua", "Tiga", "Empat", "Lima", "Enam",
                "Tujuh", "Delapan", "Sembilan", "Sepuluh", "Sebelas"]

    def _sebut(n):
        hasil = ""
        if n < 12:
            hasil = bilangan[n]
        elif n < 20:
            hasil = bilangan[n - 10] + " Belas"
        elif n < 100:
            hasil = _sebut(n // 10) + " Puluh"
            if n % 10 > 0:
                hasil += " " + _sebut(n % 10)
        elif n < 200:
            hasil = "Seratus"
            if n > 100:
                hasil += " " + _sebut(n - 100).lower()
        else:
            hasil = _sebut(n // 100) + " Ratus"
            if n % 100 > 0:
                hasil += " " + _sebut(n % 100).lower()
        return hasil

    hasil = ""
    if angka >= 1000000000000:
        triliun = angka // 1000000000000
        hasil += _sebut(triliun) + " Triliun "
        angka %= 1000000000000
    if angka >= 1000000000:
        milyar = angka // 1000000000
        hasil += _sebut(milyar) + " Milyar "
        angka %= 1000000000
    if angka >= 1000000:
        juta = angka // 1000000
        hasil += _sebut(juta) + " Juta "
        angka %= 1000000
    if angka >= 1000:
        ribu = angka // 1000
        if ribu == 1:
            hasil += "Seribu "
        else:
            hasil += _sebut(ribu) + " Ribu "
        angka %= 1000
    if angka > 0:
        hasil += _sebut(angka).lower()
    return hasil.strip()


# ── Mock data classes (pengganti model SQLAlchemy asli) ───────────────
class MockSKU:
    def __init__(self, kode_sku):
        self.kode_sku = kode_sku

class MockItem:
    def __init__(self, tanggal, kode_sku, qty, harga_satuan):
        self.tanggal = tanggal
        self.sku = MockSKU(kode_sku)
        self.qty = qty
        self.harga_satuan = harga_satuan
        self.total = qty * harga_satuan


# ── Fungsi hasil redesain (mengikuti PANDUAN_UPDATE_PDF_ENGINE.md) ────
def generate_invoice_pdf_v2(sales_data, nama_klien, total_tagihan, sisa_piutang,
                             deposit=0, tgl_deposit="-", metode="TUNAI",
                             alamat_klien=None, telp_klien=None, pic_klien=None,
                             out_path="preview.pdf"):

    sisa_sebelum = max(0.0, sisa_piutang - total_tagihan)
    subtotal = sisa_piutang
    sisa_baru = max(0.0, subtotal - deposit)

    no_inv = "INV-" + datetime.now().strftime("%Y%m%d_%H%M%S")
    tgl_cetak = date.today().strftime("%d/%m/%Y")
    tgl_jatuh_tempo = (date.today() + timedelta(days=30)).strftime("%d/%m/%Y")

    LM = 10
    W = 190
    PAGE_H = 297
    NAVY = (30, 41, 74)        # header tabel (baru, ganti dari BLUE cerah)
    BLUE = (33, 150, 243)      # aksen judul & garis (dipertahankan dari kode asli)
    DARK = (60, 60, 60)
    GRAY = (110, 110, 110)
    LIGHT_GRAY = (245, 245, 245)
    WHITE = (255, 255, 255)
    BLACK = (0, 0, 0)
    GREEN = (40, 167, 69)
    PINK = (233, 30, 99)

    pdf = FPDF()
    pdf.set_auto_page_break(auto=False)  # fix: cegah footer "kepotong" ke halaman baru
    pdf.add_page()

    # ====================================================================
    # HEADER — logo (kiri) + judul "Invoice" & info nomor (kanan)
    # ====================================================================
    y0 = pdf.get_y()

    # --- Logo placeholder sederhana (TODO: ganti dengan file logo asli) ---
    cx, cy = LM + 10, y0 + 8
    pdf.set_fill_color(*PINK)
    for dx, dy in [(-4, -3), (4, -3), (-4, 3), (4, 3), (0, 0)]:
        pdf.ellipse(cx + dx - 3, cy + dy - 3, 6, 6, style='F')
    pdf.set_font("Helvetica", 'B', 16)
    pdf.set_text_color(*DARK)
    pdf.set_xy(LM, y0 + 14)
    pdf.cell(60, 6, "ESSA", 0, 1, 'L')
    pdf.set_font("Helvetica", '', 11)
    pdf.set_text_color(*GRAY)
    pdf.set_x(LM)
    pdf.cell(60, 5, "Store", 0, 1, 'L')

    # --- Kanan: judul "Invoice" + Nomor/Tanggal/Jatuh Tempo ---
    pdf.set_xy(LM + 95, y0)
    pdf.set_font("Helvetica", 'B', 22)
    pdf.set_text_color(*BLUE)
    pdf.cell(95, 10, "Invoice", 0, 1, 'R')

    inv_lines_data = [
        ("Nomor", no_inv),
        ("Tanggal", tgl_cetak),
        ("Tgl. Jatuh Tempo", tgl_jatuh_tempo),
    ]
    ry = y0 + 12
    for label, value in inv_lines_data:
        pdf.set_xy(LM + 95, ry)
        pdf.set_font("Helvetica", 'B', 9)
        pdf.set_text_color(*DARK)
        pdf.cell(35, 5, label, 0, 0, 'L')
        pdf.set_font("Helvetica", '', 9)
        pdf.set_text_color(*GRAY)
        pdf.cell(60, 5, value, 0, 0, 'R')
        ry += 5

    pdf.set_y(max(y0 + 30, ry) + 4)
    pdf.set_draw_color(*BLUE)
    pdf.set_line_width(0.4)
    pdf.line(LM, pdf.get_y(), LM + W, pdf.get_y())
    pdf.ln(6)

    # ====================================================================
    # INFORMASI PERUSAHAAN | TAGIHAN KEPADA (dua kolom)
    # ====================================================================
    col_w = 95
    top_y = pdf.get_y()

    # -- Kolom kiri: Informasi Perusahaan --
    pdf.set_xy(LM, top_y)
    pdf.set_font("Helvetica", '', 9)
    pdf.set_text_color(*GRAY)
    pdf.cell(col_w, 5, "Informasi Perusahaan", 0, 1, 'L')
    pdf.set_draw_color(200, 200, 200)
    pdf.line(LM, pdf.get_y(), LM + col_w - 5, pdf.get_y())
    pdf.ln(2)

    pdf.set_x(LM)
    pdf.set_font("Helvetica", 'B', 11)
    pdf.set_text_color(*BLUE)
    pdf.cell(col_w, 6, "ESSA HIJAB", 0, 1, 'L')

    company_lines = [
        "Pendosawalan 16/06, Kec. Kalinyamatan, Jepara",
        "Telp: 0895426950709",
    ]
    pdf.set_font("Helvetica", '', 8)
    pdf.set_text_color(*GRAY)
    for line in company_lines:
        pdf.set_x(LM)
        pdf.cell(col_w, 4.5, line, 0, 1, 'L')
    left_end_y = pdf.get_y()

    # -- Kolom kanan: Tagihan Kepada --
    pdf.set_xy(LM + col_w, top_y)
    pdf.set_font("Helvetica", '', 9)
    pdf.set_text_color(*GRAY)
    pdf.cell(col_w, 5, "Tagihan Kepada", 0, 1, 'L')
    pdf.set_x(LM + col_w)
    pdf.line(LM + col_w, pdf.get_y(), LM + col_w + col_w - 5, pdf.get_y())
    pdf.ln(2)

    pdf.set_x(LM + col_w)
    pdf.set_font("Helvetica", 'B', 11)
    pdf.set_text_color(*BLUE)
    pdf.cell(col_w, 6, nama_klien.upper(), 0, 1, 'L')

    pdf.set_font("Helvetica", '', 8)
    pdf.set_text_color(*GRAY)
    if alamat_klien:
        pdf.set_x(LM + col_w)
        pdf.multi_cell(col_w, 4.5, alamat_klien)
    if telp_klien:
        pdf.set_x(LM + col_w)
        pdf.cell(col_w, 4.5, f"Telp: {telp_klien}", 0, 1, 'L')
    if pic_klien:
        pdf.set_x(LM + col_w)
        pdf.cell(col_w, 4.5, f"Up: {pic_klien}", 0, 1, 'L')
    right_end_y = pdf.get_y()

    pdf.set_y(max(left_end_y, right_end_y) + 5)

    # ====================================================================
    # TABEL PRODUK — Produk | Deskripsi | Kuantitas | Harga | Jumlah
    # ====================================================================
    col_produk = 48
    col_desk = 42
    col_qty = 25
    col_harga = 35
    col_jumlah = 40  # total = 190

    def draw_table_header():
        pdf.set_font("Helvetica", 'B', 9)
        pdf.set_fill_color(*NAVY)
        pdf.set_text_color(*WHITE)
        pdf.cell(col_produk, 9, "Produk", 1, 0, 'L', 1)
        pdf.cell(col_desk, 9, "Deskripsi", 1, 0, 'L', 1)
        pdf.cell(col_qty, 9, "Kuantitas", 1, 0, 'C', 1)
        pdf.cell(col_harga, 9, "Harga", 1, 0, 'R', 1)
        pdf.cell(col_jumlah, 9, "Jumlah", 1, 1, 'R', 1)
        pdf.set_text_color(*BLACK)
        pdf.set_font("Helvetica", '', 9)

    draw_table_header()

    POST_TABLE_RESERVE = 130
    items = list(sales_data)
    row_height = 7

    for idx, item in enumerate(items, 1):
        if pdf.get_y() + row_height + POST_TABLE_RESERVE > PAGE_H:
            pdf.add_page()
            draw_table_header()

        fill = 1 if idx % 2 == 0 else 0
        pdf.set_fill_color(*LIGHT_GRAY)

        nama_produk = item.sku.kode_sku if item.sku else "Barang Offline"
        nama_produk = nama_produk[:26]
        deskripsi = item.tanggal.strftime("%d %b %Y") if hasattr(item.tanggal, "strftime") else str(item.tanggal)
        qty_str = str(int(item.qty)) if float(item.qty).is_integer() else f"{item.qty:g}"
        harga_str = format_indo(item.harga_satuan)
        jumlah_str = format_indo(item.total)

        pdf.cell(col_produk, row_height, f" {nama_produk}", 1, 0, 'L', fill)
        pdf.cell(col_desk, row_height, f" {deskripsi}", 1, 0, 'L', fill)
        pdf.cell(col_qty, row_height, qty_str, 1, 0, 'C', fill)
        pdf.cell(col_harga, row_height, harga_str, 1, 0, 'R', fill)
        pdf.cell(col_jumlah, row_height, jumlah_str, 1, 1, 'R', fill)

    pdf.ln(3)

    # ====================================================================
    # TERBILANG
    # ====================================================================
    terbilang_text = terbilang(int(round(total_tagihan))) + " Rupiah"
    pdf.set_font("Helvetica", 'I', 9)
    pdf.set_text_color(*GRAY)
    pdf.cell(20, 4, "Terbilang:", 0, 1, 'L')
    pdf.set_font("Helvetica", 'B', 10)
    pdf.set_text_color(*DARK)
    pdf.multi_cell(W, 5, terbilang_text)
    pdf.ln(2)

    # ====================================================================
    # RINGKASAN FINANSIAL
    # ====================================================================
    sum_x = LM + 90
    sum_lbl = 60
    sum_val = 40

    def summary_row(label, value, bold=False, color=None, border=''):
        pdf.set_x(sum_x)
        fw = 'B' if bold else ''
        pdf.set_font("Helvetica", fw, 10)
        pdf.set_text_color(*(color if color else BLACK))
        pdf.cell(sum_lbl, 7, label, border, 0, 'R')
        pdf.cell(sum_val, 7, value, border, 1, 'R')

    summary_row("Subtotal", f"Rp {format_indo(total_tagihan)}")
    summary_row("Total", f"Rp {format_indo(total_tagihan)}", bold=True, border='TB')
    pdf.ln(1)

    sisa_tagihan = max(0.0, total_tagihan - deposit) if deposit > 0 else total_tagihan
    summary_row("Sisa Tagihan", f"Rp {format_indo(sisa_tagihan)}", bold=True,
                color=BLUE if sisa_tagihan > 0 else GREEN)
    pdf.ln(3)

    # ── Rincian Piutang (KONDISIONAL — dipertahankan sesuai panduan) ──
    if abs(sisa_piutang - total_tagihan) > 100 or deposit > 0:
        pdf.set_draw_color(200, 200, 200)
        pdf.set_line_width(0.2)
        pdf.line(LM, pdf.get_y(), LM + W, pdf.get_y())
        pdf.ln(2)

        pdf.set_x(sum_x)
        pdf.set_font("Helvetica", 'B', 9)
        pdf.set_text_color(*DARK)
        pdf.cell(sum_lbl + sum_val, 5, "Rincian Piutang", 0, 1, 'R')
        pdf.ln(1)

        pdf.set_font("Helvetica", '', 9)
        for lbl, val, clr in [
            ("Sisa Hutang Sebelumnya", f"Rp {format_indo(sisa_sebelum)}", GRAY),
            ("Total Transaksi Baru", f"Rp {format_indo(total_tagihan)}", GRAY),
        ]:
            pdf.set_x(sum_x)
            pdf.set_text_color(*clr)
            pdf.cell(sum_lbl, 6, lbl, 0, 0, 'R')
            pdf.cell(sum_val, 6, val, 0, 1, 'R')

        pdf.set_x(sum_x)
        pdf.set_font("Helvetica", 'B', 9)
        pdf.set_text_color(*BLUE)
        pdf.cell(sum_lbl, 6, "Total Sisa Piutang", 0, 0, 'R')
        pdf.cell(sum_val, 6, f"Rp {format_indo(subtotal)}", 0, 1, 'R')

        if deposit > 0:
            pdf.set_x(sum_x)
            pdf.set_font("Helvetica", 'B', 9)
            pdf.set_text_color(*GREEN)
            pdf.cell(sum_lbl, 6, f"Deposit ({tgl_deposit}, {metode})", 0, 0, 'R')
            pdf.cell(sum_val, 6, f"- Rp {format_indo(deposit)}", 0, 1, 'R')

            pdf.set_draw_color(*BLUE)
            pdf.set_line_width(0.3)
            pdf.set_x(sum_x)
            pdf.cell(sum_lbl + sum_val, 0, "", 'T', 1)
            pdf.ln(1)

            color_sisa = PINK if sisa_baru > 0 else GREEN
            pdf.set_x(sum_x)
            pdf.set_font("Helvetica", 'B', 10)
            pdf.set_text_color(*color_sisa)
            label_sisa = "Sisa Hutang Baru"
            val_sisa = f"Rp {format_indo(sisa_baru)}" if sisa_baru > 0 else "Rp 0 (LUNAS)"
            pdf.cell(sum_lbl, 7, label_sisa, 0, 0, 'R')
            pdf.cell(sum_val, 7, val_sisa, 0, 1, 'R')

    pdf.ln(5)

    # ====================================================================
    # FOOTER — Instruksi Pembayaran & Tanda Tangan
    # ====================================================================
    y_post_content = pdf.get_y()
    FOOTER_H = 55

    if y_post_content + FOOTER_H > PAGE_H:
        pdf.add_page()
        pdf.set_y(PAGE_H - FOOTER_H)
    else:
        pdf.set_y(PAGE_H - FOOTER_H)

    pdf.set_draw_color(200, 200, 200)
    pdf.set_line_width(0.3)
    pdf.line(LM, pdf.get_y(), LM + W, pdf.get_y())
    pdf.ln(5)

    pdf.set_font("Helvetica", 'B', 9)
    pdf.set_text_color(*DARK)
    pdf.cell(0, 6, "Instruksi Pembayaran:", 0, 1)
    pdf.set_font("Helvetica", '', 9)
    pdf.set_text_color(*GRAY)
    pdf.cell(0, 5, "Mohon lakukan transfer ke: Bank BRI No. Rek: 224001017473501 a/n ACHMAD FAIS SETIAWAN", 0, 1)
    pdf.ln(8)

    pdf.set_font("Helvetica", '', 10)
    pdf.set_text_color(*DARK)
    pdf.cell(0, 5, "Dengan Hormat,", 0, 1, 'C')
    pdf.ln(14)
    pdf.set_font("Helvetica", 'B', 11)
    pdf.set_text_color(*BLUE)
    pdf.cell(0, 5, "ESSA HIJAB", 0, 1, 'C')

    pdf.output(out_path)
    return out_path


# ── TEST CASE A: klien baru, transaksi bersih, data lengkap (mirip JM FASHION) ──
items_a = [
    MockItem(date(2026, 7, 15), "PASHMINA POLOS JERSEY", 1325, 12000),
]
generate_invoice_pdf_v2(
    sales_data=items_a,
    nama_klien="JM Fashion",
    total_tagihan=15_900_000,
    sisa_piutang=15_900_000,   # tidak ada piutang sebelumnya -> section piutang sembunyi
    deposit=0,
    alamat_klien="Kantor Pusat: Jl. Pleret KM 1, Baturetno, Banguntapan, Bantul, D I Yogyakarta",
    telp_klien="089619044442",
    pic_klien="Ibu Hj. Chalimatus Sa'diyah",
    out_path="/home/claude/preview_A_JM_Fashion.pdf",
)

# ── TEST CASE B: reseller berulang, banyak item, ada piutang berjalan (mirip Mbak Iin) ──
raw_items = [
    ("2026-07-06", "JSO-Coksu", 29), ("2026-07-06", "JSO-Taro", 38),
    ("2026-07-06", "JSO-Army", 30), ("2026-07-06", "JSO-Hazelnut", 90),
    ("2026-07-06", "JSO-Smoke", 40), ("2026-07-06", "JSO-Softpink", 60),
    ("2026-07-06", "JSO-Burgundy", 40), ("2026-07-06", "JSO-Choco", 29),
    ("2026-07-06", "JSO-Maroon", 50), ("2026-07-06", "JSO-Turkish", 26),
    ("2026-07-06", "JSO-Olive", 50), ("2026-07-06", "JSO-Grey", 70),
    ("2026-07-06", "JSO-Beige", 180), ("2026-07-06", "JSO-Hitam", 181),
    ("2026-07-06", "JSO-Sage", 111), ("2026-07-06", "JSO-Moca", 20),
    ("2026-07-06", "JSO-Caramel", 30), ("2026-07-06", "JSO-Cream", 110),
    ("2026-07-06", "JSO-Cokelat Tua", 70), ("2026-07-06", "JSO-Dusty Pink", 30),
    ("2026-07-10", "JSO-Almond", 30), ("2026-07-10", "JSO-Dark Grey", 20),
    ("2026-07-10", "JSO-Navy", 20), ("2026-07-10", "JSO-Denim", 34),
    ("2026-07-10", "JSO-Putih", 30), ("2026-07-10", "JSO-Jotol", 30),
    ("2026-07-10", "JSO-Lime", 40),
]
items_b = [MockItem(datetime.strptime(t, "%Y-%m-%d").date(), k, q, 13000) for t, k, q in raw_items]
total_b = sum(i.total for i in items_b)

generate_invoice_pdf_v2(
    sales_data=items_b,
    nama_klien="Mbak Iin",
    total_tagihan=total_b,
    sisa_piutang=27_729_000 + total_b,   # sisa sebelumnya + transaksi baru
    deposit=20_000_000,
    tgl_deposit="2026-07-16",
    metode="TUNAI",
    out_path="/home/claude/preview_B_Mbak_Iin.pdf",
)

print("Total B (harus 19.344.000):", format_indo(total_b))
print("OK - 2 file PDF berhasil dibuat")
