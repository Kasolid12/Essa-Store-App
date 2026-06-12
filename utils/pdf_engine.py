# app_essa/utils/pdf_engine.py
import os
from datetime import datetime
from reportlab.lib.pagesizes import A5 # A5 is half an A4 page, perfect for slips
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm

from data.database import SessionLocal
from data.models import SalaryRun
from data.models import SalaryRun, PengeluaranOffline # <--- Add PengeluaranOffline here

def format_rupiah(angka):
    """Fungsi helper untuk format mata uang Indonesia (Titik untuk ribuan)"""
    try:
        return f"Rp {int(float(angka)):,.0f}".replace(",", ".")
    except:
        return "Rp 0"

def generate_salary_slip(salary_run_id):
    """
    Generator PDF Cerdas: 
    Otomatis menyesuaikan tata letak untuk Penjahit, Pengsup, atau Karyawan.
    """
    from reportlab.lib.pagesizes import A5
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import mm
    from data.database import SessionLocal
    from data.models.salary import SalaryRun
    import os

    db = SessionLocal()
    try:
        # 1. Tarik data utama
        run = db.query(SalaryRun).get(salary_run_id)
        if not run:
            raise ValueError("Data Salary Run ID tidak ditemukan di database.")

        person = run.person
        nama_person = person.nama.upper() if person else "UNKNOWN"
        id_person = person.id if person else "-"

        # 2. Siapkan Folder Ekspor
        export_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "exports", "slips")
        os.makedirs(export_dir, exist_ok=True)

        # Nama file rapi sesuai tipe
        filename = f"SLIP_{run.tipe}_{nama_person.replace(' ', '_')}_{run.tanggal_proses}.pdf"
        filepath = os.path.join(export_dir, filename)

        # 3. Inisialisasi Kertas (A5 Portrait)
        c = canvas.Canvas(filepath, pagesize=A5)
        width, height = A5

        # --- FUNGSI BANTUAN UNTUK MENGGAMBAR HEADER HALAMAN ---
        def draw_header():
            c.setFont("Courier-Bold", 12)
            if run.tipe == "BORONGAN_PENJAHIT":
                title = "NOTA GAJI PENJAHIT - ESSA STORE"
            elif run.tipe == "PENGSUP":
                title = "NOTA TOTALAN PENGSUP - ESSA STORE"
            else:
                title = "ESSA STORE - SLIP GAJI"

            c.drawString(10*mm, height - 15*mm, title)
            c.setFont("Courier", 10)
            
            # Format header menyesuaikan jenis slip
            if run.tipe == "PASUKAN_KARYAWAN":
                c.drawString(10*mm, height - 25*mm, f"ID Karyawan : {id_person}")
                c.drawString(10*mm, height - 30*mm, f"Nama        : {nama_person}")
                c.drawString(10*mm, height - 35*mm, f"Tanggal     : {run.tanggal_proses}")
            else:
                c.drawString(10*mm, height - 25*mm, f"NAMA    : {nama_person}")
                c.drawString(10*mm, height - 30*mm, f"TANGGAL : {run.tanggal_proses}")

        # Jalankan Header di Halaman Pertama
        draw_header()
        y = height - 45*mm

        # ========================================================
        # BAGIAN 1A: TABEL RINCIAN (Khusus PENJAHIT)
        # ========================================================
        if run.tipe == "BORONGAN_PENJAHIT":
            c.setFont("Courier-Bold", 9)
            c.drawString(10*mm, y, "JENIS GARAPAN")
            c.drawString(75*mm, y, "Qty")
            c.drawString(95*mm, y, "HARGA")
            c.drawRightString(138*mm, y, "TOTAL")
            
            c.line(10*mm, y-2*mm, 138*mm, y-2*mm) # Garis pembatas
            y -= 7*mm

            c.setFont("Courier", 9)
            for item in run.line_items:
                nama_garapan = item.model_code or "Barang"
                if len(nama_garapan) > 23:
                    nama_garapan = nama_garapan[:20] + "..."

                qty_str = f"{int(item.qty)}" if item.qty.is_integer() else f"{item.qty:g}"

                c.drawString(10*mm, y, nama_garapan)
                c.drawString(75*mm, y, qty_str)
                c.drawString(95*mm, y, format_rupiah(item.tarif_per_pcs).replace("Rp ", ""))
                c.drawRightString(138*mm, y, format_rupiah(item.subtotal))

                y -= 5*mm
                if y < 45*mm: # Buat halaman baru jika kertas habis
                    c.showPage()
                    draw_header()
                    y = height - 45*mm
                    c.setFont("Courier", 9)

        # ========================================================
        # BAGIAN 1B: TABEL RINCIAN (Khusus PENGSUP)
        # ========================================================
        elif run.tipe == "PENGSUP":
            list_barang = []
            list_potong = []
            mentah_item = None
            
            # Deteksi item dari database berdasarkan TAG Rahasia
            for item in run.line_items:
                code = str(item.model_code)
                if code == "[KAIN_MENTAH]": mentah_item = item
                elif code.startswith("[POTONG]"): list_potong.append(item)
                else: list_barang.append(item)

            # --- SEKSI 1: BARANG JADI ---
            c.setFont("Courier-Bold", 9)
            c.drawString(10*mm, y, "1. DAFTAR KAIN/BARANG JADI")
            y -= 6*mm

            c.drawString(10*mm, y, "NAMA BARANG")
            c.drawString(75*mm, y, "Qty")
            c.drawString(95*mm, y, "HARGA")
            c.drawRightString(138*mm, y, "JUMLAH")
            c.line(10*mm, y-2*mm, 138*mm, y-2*mm)
            y -= 6*mm

            c.setFont("Courier", 9)
            total_barang = 0
            for item in list_barang:
                nama = str(item.model_code).replace("[BARANG] ", "")
                if len(nama) > 23: nama = nama[:20] + "..."
                qty_str = f"{int(item.qty)}" if item.qty.is_integer() else f"{item.qty:g}"

                c.drawString(10*mm, y, nama)
                c.drawString(75*mm, y, qty_str)
                c.drawString(95*mm, y, format_rupiah(item.tarif_per_pcs).replace("Rp ", ""))
                c.drawRightString(138*mm, y, format_rupiah(item.subtotal))
                total_barang += item.subtotal

                y -= 5*mm
                if y < 45*mm: c.showPage(); draw_header(); y = height - 45*mm; c.setFont("Courier", 9)

            c.setFont("Courier-Bold", 9)
            c.drawString(10*mm, y, "TOTAL BARANG")
            c.drawRightString(138*mm, y, format_rupiah(total_barang))
            y -= 6*mm

            # --- SEKSI PENGURANGAN KAIN ---
            total_setelah_kain = total_barang
            if mentah_item:
                c.setFont("Courier", 9)
                qty_str = f"{int(mentah_item.qty)}" if mentah_item.qty.is_integer() else f"{mentah_item.qty:g}"
                c.drawString(10*mm, y, "KAIN")
                c.drawString(75*mm, y, qty_str)
                c.drawString(95*mm, y, format_rupiah(mentah_item.tarif_per_pcs).replace("Rp ", ""))
                c.drawRightString(138*mm, y, format_rupiah(abs(mentah_item.subtotal))) 
                
                total_setelah_kain -= abs(mentah_item.subtotal)
                y -= 5*mm
                c.setFont("Courier-Bold", 9)
                c.drawString(10*mm, y, "TOTAL BARANG - KAIN")
                c.drawRightString(138*mm, y, format_rupiah(total_setelah_kain))
                y -= 6*mm

            # --- SEKSI 2: DAFTAR POTONGAN ---
            total_potongan = 0
            if list_potong:
                y -= 2*mm
                c.setFont("Courier-Bold", 9)
                c.drawString(10*mm, y, "2. DAFTAR POTONGAN")
                y -= 6*mm
                
                c.drawString(10*mm, y, "NAMA BARANG")
                c.drawString(75*mm, y, "Qty")
                c.drawString(95*mm, y, "HARGA")
                c.drawRightString(138*mm, y, "JUMLAH")
                c.line(10*mm, y-2*mm, 138*mm, y-2*mm)
                y -= 6*mm

                c.setFont("Courier", 9)
                for item in list_potong:
                    nama = str(item.model_code).replace("[POTONG] ", "")
                    if len(nama) > 23: nama = nama[:20] + "..."
                    qty_str = f"{int(item.qty)}" if item.qty.is_integer() else f"{item.qty:g}"

                    c.drawString(10*mm, y, nama)
                    c.drawString(75*mm, y, qty_str)
                    c.drawString(95*mm, y, format_rupiah(item.tarif_per_pcs).replace("Rp ", ""))
                    c.drawRightString(138*mm, y, format_rupiah(item.subtotal))
                    total_potongan += item.subtotal

                    y -= 5*mm
                    if y < 45*mm: c.showPage(); draw_header(); y = height - 45*mm; c.setFont("Courier", 9)

                c.setFont("Courier-Bold", 9)
                c.drawString(10*mm, y, "TOTAL POTONGAN")
                c.drawRightString(138*mm, y, format_rupiah(total_potongan))
                y -= 6*mm

            # --- GRAND TOTAL KESELURUHAN DIBAYAR ---
            grand_total = total_setelah_kain + total_potongan
            y -= 4*mm
            c.setFont("Courier-Bold", 10)
            c.drawString(10*mm, y, "TOTAL KESELURUHAN DIBAYAR")
            c.drawRightString(138*mm, y, format_rupiah(grand_total))
            y -= 8*mm

        # ========================================================
        # BAGIAN 1C: RINCIAN JAM KERJA (Khusus Karyawan)
        # ========================================================
        elif run.tipe == "PASUKAN_KARYAWAN":
            from data.models.salary import AttendanceRecord, SalaryLineItem

            # 1. Tarik riwayat kedatangan harian
            attendances = db.query(AttendanceRecord).filter(AttendanceRecord.salary_run_id == run.id).all()

            c.setFont("Courier-Bold", 8)
            c.drawString(10*mm, y, "Tanggal")
            c.drawString(35*mm, y, "Masuk")
            c.drawString(55*mm, y, "Keluar")
            c.drawRightString(95*mm, y, "Tot. Menit")
            c.drawRightString(138*mm, y, "Lembur")
            
            c.line(10*mm, y-2*mm, 138*mm, y-2*mm)
            y -= 6*mm

            c.setFont("Courier", 8)
            if attendances:
                for att in attendances:
                    c.drawString(10*mm, y, str(att.tanggal))
                    c.drawString(35*mm, y, str(att.tap_masuk))
                    c.drawString(55*mm, y, str(att.tap_keluar))
                    c.drawRightString(95*mm, y, f"{att.menit_normal:g}")
                    c.drawRightString(138*mm, y, f"{att.menit_lembur:g}")
                    y -= 5*mm
                    if y < 45*mm: c.showPage(); draw_header(); y = height - 45*mm; c.setFont("Courier", 8)
            else:
                c.drawString(10*mm, y, "Data rincian harian (tap) tidak tersedia dari Excel.")
                y -= 5*mm

            # 2. Tarik nilai tarif dinamis yang terekam di line items detail komponen
            line_items = db.query(SalaryLineItem).filter(SalaryLineItem.salary_run_id == run.id).all()
            
            # Buat nilai fallback default jika seandainya data line items kosong
            qty_normal, tarif_normal, subtotal_normal = 0, 150.0, 0
            qty_lembur, tarif_lembur, subtotal_lembur = 0, 160.0, 0
            
            for item in line_items:
                if item.model_code == "[GAJI_NORMAL]":
                    qty_normal = item.qty
                    tarif_normal = item.tarif_per_pcs
                    subtotal_normal = item.subtotal
                elif item.model_code == "[GAJI_LEMBUR]":
                    qty_lembur = item.qty
                    tarif_lembur = item.tarif_per_pcs
                    subtotal_lembur = item.subtotal

            y -= 2*mm
            c.setFont("Courier-Bold", 9)
            c.drawString(10*mm, y, "RINCIAN PEMBAYARAN:")
            y -= 6*mm
            
            # Tulis baris slip menggunakan tarif kustom hasil editan kasir di tabel
            c.setFont("Courier", 9)
            c.drawString(10*mm, y, f"Gaji Normal ({qty_normal:g} mnt @Rp {tarif_normal:g})")
            c.drawString(75*mm, y, ":")
            c.drawRightString(138*mm, y, format_rupiah(subtotal_normal))
            y -= 5*mm
            
            c.drawString(10*mm, y, f"Gaji Lembur ({qty_lembur:g} mnt @Rp {tarif_lembur:g})")
            c.drawString(75*mm, y, ":")
            c.drawRightString(138*mm, y, format_rupiah(subtotal_lembur))
            y -= 10*mm

        # ========================================================
        # BAGIAN 2: RINGKASAN FINANSIAL & KASBON (Buku Besar)
        # ========================================================
        c.line(10*mm, y, 138*mm, y) # Garis pembatas akhir rincian
        y -= 6*mm

        c.setFont("Courier-Bold", 10)
        c.drawString(10*mm, y, "TOTAL GAJI KOTOR")
        c.drawString(75*mm, y, ":")
        c.drawRightString(138*mm, y, format_rupiah(run.gaji_kotor))
        y -= 6*mm

        # Bagian Kasbon (Hanya tampil jika ada riwayat bon)
        c.setFont("Courier", 9)
        if run.bon_lama > 0 or run.potong_bon > 0:
            c.drawString(10*mm, y, "Sisa Bon Lama")
            c.drawString(75*mm, y, ":")
            c.drawRightString(138*mm, y, format_rupiah(run.bon_lama))
            y -= 5*mm

            c.drawString(10*mm, y, "POTONGAN MINGGU INI")
            c.drawString(75*mm, y, ":")
            c.drawRightString(138*mm, y, f"- {format_rupiah(run.potong_bon)}")
            y -= 5*mm

        c.line(75*mm, y+2*mm, 138*mm, y+2*mm) # Garis Total Bersih
        y -= 6*mm

        c.setFont("Courier-Bold", 10)
        c.drawString(10*mm, y, "TOTAL GAJI BERSIH (DITERIMA)")
        c.drawString(75*mm, y, ":")
        c.drawRightString(138*mm, y, format_rupiah(run.gaji_bersih))
        y -= 8*mm

        if run.sisa_bon_akhir > 0:
            c.setFont("Courier-Bold", 9)
            c.drawString(10*mm, y, "SISA BON AKHIR (BELUM LUNAS)")
            c.drawString(75*mm, y, ":")
            c.drawRightString(138*mm, y, format_rupiah(run.sisa_bon_akhir))
            y -= 10*mm

        # ========================================================
        # BAGIAN 3: FOOTER
        # ========================================================
        c.setFont("Courier-Oblique", 8)
        # Cetak tepat di tengah bawah kertas
        c.drawCentredString(width/2.0, 15*mm, "*Nota ini dicetak secara otomatis oleh Sistem Essa Store")

        c.save()
        return filepath
        
    except Exception as e:
        print(f"PDF Engine Error: {e}")
        raise e
    finally:
        db.close()

def generate_invoice_pdf(offline_sale_id):
    """Generates an Industrial-style PDF Sales Invoice."""
    db = SessionLocal()
    try:
        sale = db.query(PengeluaranOffline).get(offline_sale_id)
        if not sale:
            raise ValueError("Data Penjualan Offline tidak ditemukan.")
            
        person = sale.person
        sku = sale.sku
        
        # Setup the File Path
        export_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "exports", "invoices")
        os.makedirs(export_dir, exist_ok=True)
        
        filename = f"INV_{sale.id:06d}_{person.nama.replace(' ', '_')}.pdf"
        filepath = os.path.join(export_dir, filename)

        # Initialize the PDF Canvas (A5 Landscape)
        c = canvas.Canvas(filepath, pagesize=(210*mm, 148*mm))
        
        # --- DRAWING THE INDUSTRIAL AESTHETIC ---
        
        # Outer Border
        c.setLineWidth(2)
        c.rect(10*mm, 10*mm, 190*mm, 128*mm)
        c.setLineWidth(1)
        c.rect(12*mm, 12*mm, 186*mm, 124*mm) 
        
        # HEADER
        c.setFont("Courier-Bold", 20)
        c.drawString(16*mm, 120*mm, "ESSA STORE // OFFICIAL INVOICE")
        
        c.setFont("Courier", 10)
        c.drawString(16*mm, 112*mm, f"DATE ISSUED : {sale.tanggal}")
        c.drawString(16*mm, 107*mm, f"INVOICE NO  : INV-{sale.id:06d}")
        
        # Divider Line
        c.line(16*mm, 102*mm, 194*mm, 102*mm)

        # BILLING DETAILS
        c.setFont("Courier-Bold", 12)
        c.drawString(16*mm, 92*mm, "BILLED TO:")
        c.setFont("Courier", 11)
        c.drawString(16*mm, 84*mm, person.nama.upper())
        c.drawString(16*mm, 78*mm, f"CATEGORY: {person.person_type}")

        # ITEMIZED BOX
        c.rect(16*mm, 45*mm, 178*mm, 25*mm) 
        c.setFont("Courier-Bold", 10)
        c.drawString(20*mm, 63*mm, "ITEM DESCRIPTION")
        c.drawString(120*mm, 63*mm, "QTY")
        c.drawString(140*mm, 63*mm, "UNIT PRICE")
        c.drawRightString(190*mm, 63*mm, "TOTAL")
        
        # Inner Divider
        c.line(16*mm, 59*mm, 194*mm, 59*mm)
        
        # Item Row
        c.setFont("Courier", 10)
        product_name = f"[{sku.kode_sku}] {sku.nama_produk}"
        # Truncate if too long so it doesn't overlap prices
        if len(product_name) > 45: product_name = product_name[:42] + "..."
        
        c.drawString(20*mm, 51*mm, product_name)
        c.drawString(120*mm, 51*mm, f"{sale.qty:,}")
        c.drawString(140*mm, 51*mm, f"Rp {sale.harga_satuan:,.0f}")
        c.drawRightString(190*mm, 51*mm, f"Rp {sale.total:,.0f}")

        # GRAND TOTAL
        c.setFont("Courier-Bold", 14)
        c.drawString(110*mm, 30*mm, "GRAND TOTAL :")
        c.drawRightString(190*mm, 30*mm, f"Rp {sale.total:,.0f}")

        # FOOTER / SIGNATURES
        c.setFont("Courier", 10)
        c.drawString(20*mm, 30*mm, "AUTHORIZED SIGNATURE")
        c.line(20*mm, 20*mm, 70*mm, 20*mm)

        c.save()
        return filepath
        
    finally:
        db.close()
        
def generate_batch_receipt_pdf(nama_supplier, tipe_hutang, nominal_uang, items, sisa_awal, sisa_akhir):
    """Generates a dynamic PDF receipt for batch payments."""
    import os
    from datetime import datetime
    from reportlab.lib.pagesizes import A5, portrait
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import mm

    export_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "exports", "receipts")
    os.makedirs(export_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_nama = "".join(c for c in nama_supplier if c.isalnum() or c in (' ', '_')).replace(' ', '_')
    filename = f"PAY_{tipe_hutang}_{safe_nama}_{timestamp}.pdf"
    filepath = os.path.join(export_dir, filename)

    c = canvas.Canvas(filepath, pagesize=portrait(A5))
    width, height = portrait(A5)
    
    # --- HEADER ---
    c.setFont("Courier-Bold", 14)
    c.drawCentredString(width / 2.0, height - 15*mm, "NOTA PEMBAYARAN / DEPOSIT")
    
    c.setFont("Courier", 10)
    c.drawCentredString(width / 2.0, height - 20*mm, "=" * 50)
    
    # --- SUPPLIER INFO ---
    c.setFont("Courier-Bold", 11)
    c.drawString(15*mm, height - 30*mm, "NAMA SUPPLIER :")
    c.drawString(55*mm, height - 30*mm, nama_supplier.upper())
    
    c.setFont("Courier", 10)
    c.drawString(15*mm, height - 36*mm, "TGL BAYAR     :")
    c.drawString(55*mm, height - 36*mm, datetime.now().strftime("%d-%m-%Y"))
    
    c.drawString(15*mm, height - 42*mm, "KETERANGAN    :")
    c.drawString(55*mm, height - 42*mm, f"Pelunasan Batch {len(items)} Transaksi")

    # --- ITEM LIST HEADER ---
    y = height - 55*mm
    c.setFont("Courier-Bold", 10)
    c.drawString(15*mm, y, "--- REFERENSI TRANSAKSI TERPILIH ---")
    y -= 8*mm
    
    # NEW: Table Headers matching the old app
    c.setFont("Courier-Bold", 8)
    c.drawString(15*mm, y, "TGL")
    c.drawString(32*mm, y, "DESKRIPSI")
    c.drawString(78*mm, y, "QTY")
    c.drawString(92*mm, y, "HARGA/SATUAN")
    c.drawRightString(133*mm, y, "DIBAYAR")
    y -= 3*mm
    c.line(15*mm, y, 133*mm, y)
    y -= 5*mm

    # --- ITEM ROWS ---
    c.setFont("Courier", 8)
    for item in items:
        c.drawString(15*mm, y, str(item['tgl'])[5:10]) # Just show MM-DD to save space
        
        desc = str(item['desc'])
        if len(desc) > 22: desc = desc[:19] + "..."
        c.drawString(32*mm, y, desc)
        
        # Format Qty to remove .0 if it's a whole number
        qty_str = f"{int(item['qty'])}" if float(item['qty']).is_integer() else f"{item['qty']}"
        
        c.drawString(78*mm, y, qty_str)
        c.drawString(92*mm, y, f"Rp {item['harga']:,.0f}")
        c.drawRightString(133*mm, y, f"Rp {item['bayar']:,.0f}")
        
        y -= 5*mm
        if y < 60*mm:
            c.showPage()
            y = height - 20*mm
            c.setFont("Courier", 8)

    # --- FINANCIAL SUMMARY ---
    y -= 5*mm
    c.setFont("Courier-Bold", 10)
    c.drawString(15*mm, y, "--- RINCIAN PEMBAYARAN BUKU BESAR ---")
    y -= 8*mm
    
    c.setFont("Courier", 10)
    c.drawString(15*mm, y, "1. Sisa Hutang (Awal) :")
    c.drawRightString(133*mm, y, f"Rp {sisa_awal:,.0f}")
    y -= 6*mm
    
    c.setFont("Courier-Bold", 12)
    c.drawString(15*mm, y, "2. TOTAL KAS DIBAYAR  :")
    c.drawRightString(133*mm, y, f"Rp {nominal_uang:,.0f}")
    y -= 4*mm
    c.line(15*mm, y, 133*mm, y)
    y -= 6*mm
    
    c.setFont("Courier", 10)
    c.drawString(15*mm, y, "3. Sisa Hutang Akhir  :")
    c.drawRightString(133*mm, y, f"Rp {sisa_akhir:,.0f}")
    
    c.save()
    return filepath