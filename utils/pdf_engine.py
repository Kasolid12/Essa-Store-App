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

def format_indo(angka):
    """Format angka gaya Indonesia: titik sebagai pemisah ribuan (tanpa Rp)"""
    try:
        return f"{int(angka):,}".replace(",", ".")
    except:
        return "0"

def terbilang(angka):
    """Konversi angka ke tulisan bahasa Indonesia"""
    if angka == 0:
        return "Nol"

    bilangan = ["", "Satu", "Dua", "Tiga", "Empat", "Lima", "Enam",
                "Tujuh", "Delapan", "Sembilan", "Sepuluh", "Sebelas"]

    def _sebut(n):
        """Konversi n < 1000 ke kata-kata"""
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
    # Triliun
    if angka >= 1000000000000:
        triliun = angka // 1000000000000
        hasil += _sebut(triliun) + " Triliun "
        angka %= 1000000000000
    # Milyar
    if angka >= 1000000000:
        milyar = angka // 1000000000
        hasil += _sebut(milyar) + " Milyar "
        angka %= 1000000000
    # Juta
    if angka >= 1000000:
        juta = angka // 1000000
        hasil += _sebut(juta) + " Juta "
        angka %= 1000000
    # Ribu
    if angka >= 1000:
        ribu = angka // 1000
        if ribu == 1:
            hasil += "Seribu "
        else:
            hasil += _sebut(ribu) + " Ribu "
        angka %= 1000
    # Sisanya
    if angka > 0:
        hasil += _sebut(angka).lower()

    return hasil.strip()

def generate_batch_karyawan_slip(run_ids, tanggal_proses):
    """
    Generate PDF gabungan untuk semua karyawan dalam satu file.
    Format nama file: SLIP_Gaji Karyawan_DDMMYY.pdf
    """
    from reportlab.lib.pagesizes import A5
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import mm
    from data.database import SessionLocal
    from data.models.salary import SalaryRun, AttendanceRecord, SalaryLineItem
    import os

    db = SessionLocal()
    try:
        # Ambil semua run data
        runs = db.query(SalaryRun).filter(SalaryRun.id.in_(run_ids)).all()
        if not runs:
            raise ValueError("Tidak ada data SalaryRun untuk dicetak.")

        # Urutkan berdasarkan nama karyawan
        runs.sort(key=lambda r: r.person.nama.lower() if r.person else "")

        # Siapkan folder ekspor
        export_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "exports", "slips")
        os.makedirs(export_dir, exist_ok=True)

        # Format nama file: SLIP_Gaji Karyawan_DDMMYY.pdf
        # tanggal_proses format: "yyyy-MM-dd" -> konversi ke DDMMYY
        try:
            tgl_obj = datetime.strptime(tanggal_proses, "%Y-%m-%d")
            tgl_str = tgl_obj.strftime("%d%m%y")
        except:
            tgl_str = datetime.now().strftime("%d%m%y")

        filename = f"SLIP_Gaji Karyawan_{tgl_str}.pdf"
        filepath = os.path.join(export_dir, filename)

        c = canvas.Canvas(filepath, pagesize=A5)
        width, height = A5

        def draw_header(run):
            """Gambar header untuk setiap karyawan"""
            person = run.person
            nama_person = person.nama.upper() if person else "UNKNOWN"
            id_person = person.id if person else "-"

            c.setFont("Helvetica-Bold", 12)
            c.drawString(10*mm, height - 15*mm, "ESSA STORE - SLIP GAJI KARYAWAN")
            c.setFont("Helvetica", 10)
            c.drawString(10*mm, height - 25*mm, f"ID Karyawan : {id_person}")
            c.drawString(10*mm, height - 30*mm, f"Nama        : {nama_person}")
            c.drawString(10*mm, height - 35*mm, f"Tanggal     : {run.tanggal_proses}")

        def draw_footer():
            """Gambar footer"""
            c.setFont("Helvetica-Oblique", 8)
            c.drawCentredString(width/2.0, 15*mm, "*Nota ini dicetak secara otomatis oleh Sistem Essa Store")

        for idx, run in enumerate(runs):
            person = run.person
            nama_person = person.nama.upper() if person else "UNKNOWN"

            # Header
            draw_header(run)
            y = height - 45*mm

            # ========================================================
            # BAGIAN 1: RINCIAN JAM KERJA (Khusus Karyawan)
            # ========================================================
            attendances = db.query(AttendanceRecord).filter(AttendanceRecord.salary_run_id == run.id).all()

            c.setFont("Helvetica-Bold", 8)
            c.drawString(10*mm, y, "Tanggal")
            c.drawString(35*mm, y, "Masuk")
            c.drawString(55*mm, y, "Keluar")
            c.drawRightString(95*mm, y, "Tot. Menit")
            c.drawRightString(138*mm, y, "Lembur")

            c.line(10*mm, y-2*mm, 138*mm, y-2*mm)
            y -= 6*mm

            c.setFont("Helvetica", 8)
            if attendances:
                for att in attendances:
                    c.drawString(10*mm, y, str(att.tanggal))
                    c.drawString(35*mm, y, str(att.tap_masuk))
                    c.drawString(55*mm, y, str(att.tap_keluar))
                    c.drawRightString(95*mm, y, f"{att.menit_normal:g}")
                    c.drawRightString(138*mm, y, f"{att.menit_lembur:g}")
                    y -= 5*mm
                    if y < 45*mm:
                        c.showPage()
                        draw_header(run)
                        y = height - 45*mm
                        c.setFont("Helvetica", 8)
            else:
                c.drawString(10*mm, y, "Data rincian harian (tap) tidak tersedia dari Excel.")
                y -= 5*mm

            # ========================================================
            # BAGIAN 2: RINCIAN PEMBAYARAN (dari SalaryLineItem)
            # ========================================================
            line_items = db.query(SalaryLineItem).filter(SalaryLineItem.salary_run_id == run.id).all()

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
            c.setFont("Helvetica-Bold", 9)
            c.drawString(10*mm, y, "RINCIAN PEMBAYARAN:")
            y -= 6*mm

            c.setFont("Helvetica", 9)
            c.drawString(10*mm, y, f"Gaji Normal ({qty_normal:g} mnt @Rp {tarif_normal:g})")
            c.drawString(75*mm, y, ":")
            c.drawRightString(138*mm, y, format_rupiah(subtotal_normal))
            y -= 5*mm

            c.drawString(10*mm, y, f"Gaji Lembur ({qty_lembur:g} mnt @Rp {tarif_lembur:g})")
            c.drawString(75*mm, y, ":")
            c.drawRightString(138*mm, y, format_rupiah(subtotal_lembur))
            y -= 10*mm

            # ========================================================
            # BAGIAN 3: RINGKASAN FINANSIAL & KASBON
            # ========================================================
            c.line(10*mm, y, 138*mm, y)
            y -= 6*mm

            c.setFont("Helvetica-Bold", 10)
            c.drawString(10*mm, y, "TOTAL GAJI KOTOR")
            c.drawString(75*mm, y, ":")
            c.drawRightString(138*mm, y, format_rupiah(run.gaji_kotor))
            y -= 6*mm

            c.setFont("Helvetica", 9)
            if run.bon_lama > 0 or run.potong_bon > 0:
                c.drawString(10*mm, y, "Sisa Bon Lama")
                c.drawString(75*mm, y, ":")
                c.drawRightString(138*mm, y, format_rupiah(run.bon_lama))
                y -= 5*mm

                c.drawString(10*mm, y, "POTONGAN MINGGU INI")
                c.drawString(75*mm, y, ":")
                c.drawRightString(138*mm, y, f"- {format_rupiah(run.potong_bon)}")
                y -= 5*mm

            c.line(75*mm, y+2*mm, 138*mm, y+2*mm)
            y -= 6*mm

            c.setFont("Helvetica-Bold", 10)
            c.drawString(10*mm, y, "TOTAL GAJI BERSIH (DITERIMA)")
            c.drawString(75*mm, y, ":")
            c.drawRightString(138*mm, y, format_rupiah(run.gaji_bersih))
            y -= 8*mm

            if run.sisa_bon_akhir > 0:
                c.setFont("Helvetica-Bold", 9)
                c.drawString(10*mm, y, "SISA BON AKHIR (BELUM LUNAS)")
                c.drawString(75*mm, y, ":")
                c.drawRightString(138*mm, y, format_rupiah(run.sisa_bon_akhir))
                y -= 10*mm

            # Footer
            draw_footer()

            # Page break untuk karyawan berikutnya (kecuali yang terakhir)
            if idx < len(runs) - 1:
                c.showPage()

        c.save()
        return filepath

    except Exception as e:
        print(f"PDF Engine Error (Batch Karyawan): {e}")
        raise e
    finally:
        db.close()


def generate_salary_slip(salary_run_id):
    """
    Generator PDF Cerdas (per-karyawan):
    Otomatis menyesuaikan tata letak untuk Penjahit, Pengsup, atau Karyawan.
    """
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
            c.setFont("Helvetica-Bold", 12)
            if run.tipe == "BORONGAN_PENJAHIT":
                title = "NOTA GAJI PENJAHIT - ESSA STORE"
            elif run.tipe == "PENGSUP":
                title = "NOTA TOTALAN PENGSUP - ESSA STORE"
            else:
                title = "ESSA STORE - SLIP GAJI"

            c.drawString(10*mm, height - 15*mm, title)
            c.setFont("Helvetica", 10)

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
            c.setFont("Helvetica-Bold", 9)
            c.drawString(10*mm, y, "JENIS GARAPAN")
            c.drawString(75*mm, y, "Qty")
            c.drawString(95*mm, y, "HARGA")
            c.drawRightString(138*mm, y, "TOTAL")

            c.line(10*mm, y-2*mm, 138*mm, y-2*mm) # Garis pembatas
            y -= 7*mm

            c.setFont("Helvetica", 9)
            for item in run.line_items:
                nama_garapan = item.model_code or "Barang"
                if len(nama_garapan) > 23:
                    nama_garapan = nama_garapan[:20] + "..."

                qty_str = f"{int(item.qty)}" if float(item.qty).is_integer() else f"{item.qty:g}"

                c.drawString(10*mm, y, nama_garapan)
                c.drawString(75*mm, y, qty_str)
                c.drawString(95*mm, y, format_rupiah(item.tarif_per_pcs).replace("Rp ", ""))
                c.drawRightString(138*mm, y, format_rupiah(item.subtotal))

                y -= 5*mm
                if y < 45*mm: # Buat halaman baru jika kertas habis
                    c.showPage()
                    draw_header()
                    y = height - 45*mm
                    c.setFont("Helvetica", 9)

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
            c.setFont("Helvetica-Bold", 9)
            c.drawString(10*mm, y, "1. DAFTAR KAIN/BARANG JADI")
            y -= 6*mm

            c.drawString(10*mm, y, "NAMA BARANG")
            c.drawString(75*mm, y, "Qty")
            c.drawString(95*mm, y, "HARGA")
            c.drawRightString(138*mm, y, "JUMLAH")
            c.line(10*mm, y-2*mm, 138*mm, y-2*mm)
            y -= 6*mm

            c.setFont("Helvetica", 9)
            total_barang = 0
            for item in list_barang:
                nama = str(item.model_code).replace("[BARANG] ", "")
                if len(nama) > 23: nama = nama[:20] + "..."
                qty_str = f"{int(item.qty)}" if float(item.qty).is_integer() else f"{item.qty:g}"

                c.drawString(10*mm, y, nama)
                c.drawString(75*mm, y, qty_str)
                c.drawString(95*mm, y, format_rupiah(item.tarif_per_pcs).replace("Rp ", ""))
                c.drawRightString(138*mm, y, format_rupiah(item.subtotal))
                total_barang += item.subtotal

                y -= 5*mm
                if y < 45*mm: c.showPage(); draw_header(); y = height - 45*mm; c.setFont("Helvetica", 9)

            c.setFont("Helvetica-Bold", 9)
            c.drawString(10*mm, y, "TOTAL BARANG")
            c.drawRightString(138*mm, y, format_rupiah(total_barang))
            y -= 6*mm

            # --- SEKSI PENGURANGAN KAIN ---
            total_setelah_kain = total_barang
            if mentah_item:
                c.setFont("Helvetica", 9)
                qty_str = f"{int(mentah_item.qty)}" if float(mentah_item.qty).is_integer() else f"{mentah_item.qty:g}"
                c.drawString(10*mm, y, "KAIN")
                c.drawString(75*mm, y, qty_str)
                c.drawString(95*mm, y, format_rupiah(mentah_item.tarif_per_pcs).replace("Rp ", ""))
                c.drawRightString(138*mm, y, format_rupiah(abs(mentah_item.subtotal)))

                total_setelah_kain -= abs(mentah_item.subtotal)
                y -= 5*mm
                c.setFont("Helvetica-Bold", 9)
                c.drawString(10*mm, y, "TOTAL BARANG - KAIN")
                c.drawRightString(138*mm, y, format_rupiah(total_setelah_kain))
                y -= 6*mm

            # --- SEKSI 2: DAFTAR POTONGAN ---
            total_potongan = 0
            if list_potong:
                y -= 2*mm
                c.setFont("Helvetica-Bold", 9)
                c.drawString(10*mm, y, "2. DAFTAR POTONGAN")
                y -= 6*mm

                c.drawString(10*mm, y, "NAMA BARANG")
                c.drawString(75*mm, y, "Qty")
                c.drawString(95*mm, y, "HARGA")
                c.drawRightString(138*mm, y, "JUMLAH")
                c.line(10*mm, y-2*mm, 138*mm, y-2*mm)
                y -= 6*mm

                c.setFont("Helvetica", 9)
                for item in list_potong:
                    nama = str(item.model_code).replace("[POTONG] ", "")
                    if len(nama) > 23: nama = nama[:20] + "..."
                    qty_str = f"{int(item.qty)}" if float(item.qty).is_integer() else f"{item.qty:g}"

                    c.drawString(10*mm, y, nama)
                    c.drawString(75*mm, y, qty_str)
                    c.drawString(95*mm, y, format_rupiah(item.tarif_per_pcs).replace("Rp ", ""))
                    c.drawRightString(138*mm, y, format_rupiah(item.subtotal))
                    total_potongan += item.subtotal

                    y -= 5*mm
                    if y < 45*mm: c.showPage(); draw_header(); y = height - 45*mm; c.setFont("Helvetica", 9)

                c.setFont("Helvetica-Bold", 9)
                c.drawString(10*mm, y, "TOTAL POTONGAN")
                c.drawRightString(138*mm, y, format_rupiah(total_potongan))
                y -= 6*mm

            # --- GRAND TOTAL KESELURUHAN DIBAYAR ---
            grand_total = total_setelah_kain + total_potongan
            y -= 4*mm
            c.setFont("Helvetica-Bold", 10)
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

            c.setFont("Helvetica-Bold", 8)
            c.drawString(10*mm, y, "Tanggal")
            c.drawString(35*mm, y, "Masuk")
            c.drawString(55*mm, y, "Keluar")
            c.drawRightString(95*mm, y, "Tot. Menit")
            c.drawRightString(138*mm, y, "Lembur")

            c.line(10*mm, y-2*mm, 138*mm, y-2*mm)
            y -= 6*mm

            c.setFont("Helvetica", 8)
            if attendances:
                for att in attendances:
                    c.drawString(10*mm, y, str(att.tanggal))
                    c.drawString(35*mm, y, str(att.tap_masuk))
                    c.drawString(55*mm, y, str(att.tap_keluar))
                    c.drawRightString(95*mm, y, f"{att.menit_normal:g}")
                    c.drawRightString(138*mm, y, f"{att.menit_lembur:g}")
                    y -= 5*mm
                    if y < 45*mm: c.showPage(); draw_header(); y = height - 45*mm; c.setFont("Helvetica", 8)
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
            c.setFont("Helvetica-Bold", 9)
            c.drawString(10*mm, y, "RINCIAN PEMBAYARAN:")
            y -= 6*mm

            # Tulis baris slip menggunakan tarif kustom hasil editan kasir di tabel
            c.setFont("Helvetica", 9)
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

        c.setFont("Helvetica-Bold", 10)
        c.drawString(10*mm, y, "TOTAL GAJI KOTOR")
        c.drawString(75*mm, y, ":")
        c.drawRightString(138*mm, y, format_rupiah(run.gaji_kotor))
        y -= 6*mm

        # Bagian Kasbon (Hanya tampil jika ada riwayat bon)
        c.setFont("Helvetica", 9)
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

        c.setFont("Helvetica-Bold", 10)
        c.drawString(10*mm, y, "TOTAL GAJI BERSIH (DITERIMA)")
        c.drawString(75*mm, y, ":")
        c.drawRightString(138*mm, y, format_rupiah(run.gaji_bersih))
        y -= 8*mm

        if run.sisa_bon_akhir > 0:
            c.setFont("Helvetica-Bold", 9)
            c.drawString(10*mm, y, "SISA BON AKHIR (BELUM LUNAS)")
            c.drawString(75*mm, y, ":")
            c.drawRightString(138*mm, y, format_rupiah(run.sisa_bon_akhir))
            y -= 10*mm

        # ========================================================
        # BAGIAN 3: FOOTER
        # ========================================================
        c.setFont("Helvetica-Oblique", 8)
        # Cetak tepat di tengah bawah kertas
        c.drawCentredString(width/2.0, 15*mm, "*Nota ini dicetak secara otomatis oleh Sistem Essa Store")

        c.save()
        return filepath

    except Exception as e:
        print(f"PDF Engine Error: {e}")
        raise e
    finally:
        db.close()

def generate_invoice_pdf(sales_data, nama_klien, total_tagihan, sisa_piutang,
                        deposit=0, tgl_deposit="-", metode="TUNAI",
                        simpan_deposit=False,
                        alamat_klien=None, telp_klien=None, pic_klien=None,
                        tgl_jatuh_tempo=None, diskon=0):
    """
    Generate PDF Invoice — format formal mengacu template INVOICE (Yazmina Hijab).
    Semua elemen mengalir natural setelah konten sebelumnya (tanpa fixed footer).
    """
    from fpdf import FPDF
    import os, datetime
    from collections import OrderedDict

    # ─── Helpers ──────────────────────────────────────────────────────
    def _san(text):
        if not text: return text
        for a, b in [('\u2018',"'"),('\u2019',"'"),('\u201c','"'),('\u201d','"'),
                     ('\u2013','-'),('\u2014','--'),('\u2026','...')]:
            text = text.replace(a, b)
        return text.encode('latin-1','replace').decode('latin-1')

    def _grp(items):
        """
        Kelompokkan item berdasarkan SKU Induk:
        1. parent_sku (via relasi SQLAlchemy, dengan try/except agar robust)
        2. Parse kode_sku: ambil semua sebelum '-' terakhir
           Contoh: 'p-polos-hitam' -> SKU Induk 'p-polos'
        3. Fallback sku.model
        4. Fallback sku.kategori
        5. 'Lainnya'
        """
        groups = OrderedDict()
        for it in items:
            sku = it.sku
            p = None
            if sku:
                try:
                    p = sku.parent_sku
                except Exception:
                    p = None
            if p:
                # Parent SKU tersedia via relasi database
                k = p.kode_sku or str(p.id)
                lb = p.nama_produk
                up = p.harga_jual
            elif sku and sku.kode_sku and '-' in sku.kode_sku:
                # Parse SKU Induk dari kode_sku: ambil semua sebelum '-' terakhir
                k = sku.kode_sku.rsplit('-', 1)[0]
                lb = k  # label = kode induk
                up = sku.harga_jual
            elif sku and sku.model:
                k = lb = sku.model
                up = sku.harga_jual
            elif sku and sku.kategori:
                k = lb = sku.kategori
                up = sku.harga_jual
            else:
                k = '__x__'
                lb = 'Lainnya'
                up = it.harga_satuan
            if k not in groups:
                groups[k] = {'label': lb, 'unit_price': up, 'items': [], 'subtotal': 0.0, 'total_qty': 0}
            groups[k]['items'].append(it)
            groups[k]['subtotal'] += it.total
            groups[k]['total_qty'] += it.qty
        return list(groups.values())

    diskon = max(0.0, float(diskon))
    total_setelah_diskon = max(0.0, total_tagihan - diskon)
    sisa_sebelum = max(0.0, sisa_piutang - total_setelah_diskon)
    subtotal_piutang = sisa_piutang
    sisa_baru = max(0.0, subtotal_piutang - deposit)

    try:
        APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    except NameError:
        APP_DIR = os.getcwd()

    FOLDER = os.path.join(APP_DIR, "exports", "invoices")
    os.makedirs(FOLDER, exist_ok=True)

    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    no_inv = f"INV-{ts}"
    tgl_cetak = datetime.date.today().strftime("%d/%m/%Y")
    if not tgl_jatuh_tempo:
        tgl_jatuh_tempo = (datetime.date.today() + datetime.timedelta(days=30)).strftime("%d/%m/%Y")

    total_pcs = sum(int(it.qty) if float(it.qty).is_integer() else it.qty for it in sales_data)
    if total_pcs == int(total_pcs): total_pcs = int(total_pcs)

    # Colors matching template: #1B2A4A navy, #5A5A5A grey, #DADADA line-soft, #F2F3F5 fill
    LM, W, PH = 10, 190, 297
    NAVY = (27,42,74)
    DARK, GREY, LINE_SOFT = (60,60,60), (90,90,90), (218,218,218)
    FILL_BG = (242,243,245)
    WHITE = (255,255,255)
    INK = (26,26,26)
    GREEN, PINK = (30,122,61), (179,38,30)

    pdf = FPDF()
    pdf.set_auto_page_break(auto=False)
    pdf.add_page()

    # ================================================================
    # LETTERHEAD — Logo/Name (kiri) + Tagline (kanan)
    # ================================================================
    y0 = pdf.get_y()
    logo_p = os.path.join(APP_DIR, "assets", "images", "Logo_Yazmina.png")
    logo_ok = os.path.exists(logo_p)
    if logo_ok:
        pdf.image(logo_p, x=LM, y=y0+1, w=28)
        logo_bot = y0 + 24
    else:
        logo_bot = y0 + 1

    x_name = LM + (30 if logo_ok else 0)
    pdf.set_xy(x_name, y0+2)
    pdf.set_font("Helvetica",'B', 14.5)
    pdf.set_text_color(*NAVY)
    pdf.cell(70, 6, "YAZMINA HIJAB", 0, 1, 'L')

    pdf.set_x(x_name)
    pdf.set_font("Helvetica",'', 8)
    pdf.set_text_color(*GREY)
    pdf.cell(75, 4, "Pendosawalan 16/06, Kec. Kalinyamatan, Jepara, Jawa Tengah", 0, 1, 'L')
    pdf.set_x(x_name)
    pdf.cell(75, 4, "Telp: 0895-4269-50709", 0, 1, 'L')
    left_bot = pdf.get_y()

    # Right: tagline + city
    pdf.set_xy(LM+130, y0+2)
    pdf.set_font("Helvetica",'', 8)
    pdf.set_text_color(*GREY)
    pdf.cell(60, 4, "Konveksi & Grosir Hijab", 0, 1, 'R')
    pdf.set_x(LM+130)
    pdf.cell(60, 4, "Jepara, Indonesia", 0, 1, 'R')
    right_bot = pdf.get_y()

    pdf.set_y(max(left_bot, right_bot, logo_bot) + 2)

    # Double rule (border-top 2px + border-bottom 0.75px)
    ry = pdf.get_y()
    pdf.set_draw_color(*NAVY)
    pdf.set_line_width(0.5)
    pdf.line(LM, ry, LM+W, ry)
    pdf.set_line_width(0.2)
    pdf.line(LM, ry+2.5, LM+W, ry+2.5)
    pdf.set_y(ry + 4)

    # ================================================================
    # TITLE — INVOICE (margin 16px 0 14px 0)
    # ================================================================
    pdf.ln(2)
    pdf.set_font("Helvetica",'B', 16)
    pdf.set_text_color(*INK)
    pdf.cell(0, 7, "INVOICE", 0, 1, 'C')

    pdf.set_font("Helvetica",'', 8.6)
    pdf.set_text_color(*GREY)
    pdf.cell(0, 5, f"No. {no_inv}  |  Tanggal {tgl_cetak}  |  Jatuh Tempo {tgl_jatuh_tempo}", 0, 1, 'C')
    pdf.ln(2)

    # ================================================================
    # INFO ROW — Kepada Yth (kiri) | Status + Total (kanan)
    # margin-bottom 16px, padding-bottom 12px, border-bottom 0.75px
    # ================================================================
    yi = pdf.get_y()
    # Left: bill-to
    pdf.set_xy(LM, yi)
    pdf.set_font("Helvetica",'', 8.4)
    pdf.set_text_color(*GREY)
    pdf.cell(95, 4, "Kepada Yth.", 0, 1, 'L')
    pdf.set_x(LM)
    pdf.set_font("Helvetica",'B', 10.5)
    pdf.set_text_color(*INK)
    pdf.cell(95, 6, _san(nama_klien.upper()), 0, 1, 'L')
    pdf.set_font("Helvetica",'', 8.6)
    pdf.set_text_color(*GREY)
    if alamat_klien:
        pdf.set_x(LM); pdf.multi_cell(95, 4.5, _san(alamat_klien))
    if telp_klien:
        pdf.set_x(LM); pdf.cell(95, 4.5, _san(f"Telp: {telp_klien}"), 0, 1, 'L')
    if pic_klien:
        pdf.set_x(LM); pdf.cell(95, 4.5, _san(f"Up: {pic_klien}"), 0, 1, 'L')
    liy = pdf.get_y()

    # Right: status + total item
    sisa_tgh = max(0.0, total_setelah_diskon - deposit) if deposit > 0 else total_setelah_diskon
    if sisa_tgh <= 0:
        status, sc = "Lunas", GREEN
    elif deposit > 0:
        status, sc = "Lunas Sebagian", (184,114,10)
    else:
        status, sc = "Belum Lunas", PINK

    pdf.set_xy(LM+125, yi+2)
    pdf.set_font("Helvetica",'', 8.6)
    pdf.set_text_color(*GREY)
    pdf.cell(35, 5, "Status", 0, 0, 'L')
    pdf.set_text_color(*sc)
    pdf.set_font("Helvetica",'B', 8.6)
    pdf.cell(30, 5, status, 0, 1, 'R')

    pdf.set_xy(LM+125, pdf.get_y())
    pdf.set_font("Helvetica",'', 8.6)
    pdf.set_text_color(*GREY)
    pdf.cell(35, 5, "Total Item", 0, 0, 'L')
    pdf.set_font("Helvetica",'B', 8.6)
    pdf.set_text_color(*INK)
    pdf.cell(30, 5, f"{format_indo(total_pcs)} pcs", 0, 1, 'R')
    riy = pdf.get_y()

    pdf.set_y(max(liy, riy) + 3)
    # border-bottom soft
    ln_y = pdf.get_y()
    pdf.set_draw_color(*LINE_SOFT)
    pdf.set_line_width(0.2)
    pdf.line(LM, ln_y, LM+W, ln_y)
    pdf.ln(4)

    # ================================================================
    # ITEMS TABLE — dengan kategori grouping
    # ================================================================
    cats = _grp(sales_data)

    # Column widths (matching template %): No(6%) | Produk(40%) | Qty(13%) | Harga(20%) | Jumlah(21%)
    cn, cp, cq, ch, cj = 11, 76, 25, 38, 40  # total 190

    def _th():
        pdf.set_font("Helvetica",'B', 8)
        pdf.set_fill_color(*NAVY)
        pdf.set_text_color(*WHITE)
        pdf.cell(cn, 7, "No.", 1, 0, 'C', 1)
        pdf.cell(cp, 7, "Produk / Varian", 1, 0, 'L', 1)
        pdf.cell(cq, 7, "Kuantitas", 1, 0, 'C', 1)
        pdf.cell(ch, 7, "Harga Satuan", 1, 0, 'R', 1)
        pdf.cell(cj, 7, "Jumlah", 1, 1, 'R', 1)
        pdf.set_text_color(*INK)

    _th()

    RH = 5.0
    # POST KECIL saat render tabel — biar tabel bisa mengisi halaman semaksimal mungkin.
    # Konten setelah tabel (terbilang, totals, dll.) akan diperiksa sendiri setelah tabel selesai.
    nr = abs(sisa_piutang - total_setelah_diskon) > 100 or deposit > 0 or diskon > 0
    POST = 10

    ino = 0
    for gi, grp in enumerate(cats):
        its = grp['items']
        # Category header (bg FILL_BG, navy text, uppercase)
        cl = f"{chr(65+gi)}. {_san(grp['label'])}"
        if pdf.get_y() + RH + POST > PH:
            pdf.add_page(); _th()
        pdf.set_fill_color(*FILL_BG)
        pdf.set_font("Helvetica",'B', 8.4)
        pdf.set_text_color(*NAVY)
        pdf.cell(cn, RH, "", 1, 0, '', 1)
        pdf.cell(cp+cq+ch+cj, RH, f"  {cl}", 1, 1, 'L', 1)
        pdf.set_text_color(*INK)

        for idx, it in enumerate(its, 1):
            ino += 1
            if pdf.get_y() + RH + POST > PH:
                pdf.add_page(); _th()
            fill = 1 if ino%2==0 else 0
            pdf.set_fill_color(*FILL_BG)
            nm = _san(it.sku.kode_sku[:40] if it.sku else "Barang Offline")
            qs = str(int(it.qty)) if float(it.qty).is_integer() else f"{it.qty:g}"
            hs = format_indo(it.harga_satuan)
            js = format_indo(it.total)
            pdf.set_font("Helvetica",'', 9)
            pdf.cell(cn, RH, f"{idx}", 1, 0, 'C', fill)
            pdf.cell(cp, RH, f"  {nm}", 1, 0, 'L', fill)
            pdf.cell(cq, RH, qs, 1, 0, 'C', fill)
            pdf.cell(ch, RH, hs, 1, 0, 'R', fill)
            pdf.cell(cj, RH, js, 1, 1, 'R', fill)

        # Subtotal row (bg #FAFAFA)
        if pdf.get_y() + RH + POST > PH:
            pdf.add_page(); _th()
        pdf.set_fill_color(250,250,250)
        pdf.set_font("Helvetica",'B', 8.4)
        pdf.set_text_color(*NAVY)
        qt = int(grp['total_qty']) if float(grp['total_qty']).is_integer() else grp['total_qty']
        pdf.cell(cn+cp, RH, "", 1, 0, '', 1)
        pdf.cell(cq, RH, f"{qt} pcs", 1, 0, 'C', 1)
        pdf.cell(ch, RH, f"Subtotal {chr(65+gi)}", 1, 0, 'R', 1)
        pdf.cell(cj, RH, format_indo(grp['subtotal']), 1, 1, 'R', 1)
        pdf.set_text_color(*INK)

    pdf.ln(3)

    # ── Cek konten sisa: apakah semua konten setelah tabel muat di halaman ini? ──
    # Minimum dgn rincian: tb(~18)+totals(~31)+rincian(~28)+payment(~24)+signature(~28)+footer(~6)=~135mm
    # Minimum tanpa rincian: tb(~14)+totals(~20)+payment(~24)+signature(~28)+footer(~6)=~92mm
    # Section safety nets (terbilang,payment,signature) menangani overflow jika estimasi kurang
    est_post = 92 if not nr else 130
    if pdf.get_y() + est_post + 5 > PH:
        pdf.add_page()

    # ================================================================
    # TERBILANG (border box, bg #FAFAFA, 8.8pt) — margin-top 14px
    # ================================================================
    tb_text = terbilang(int(round(total_tagihan))) + " Rupiah"
    if pdf.get_y() + 16 + (len(tb_text)//90+1)*4.5 + 5 > PH:
        pdf.add_page()

    ty0 = pdf.get_y()
    tb_h = 10 + (len(tb_text)//90)*4.5
    pdf.set_draw_color(*LINE_SOFT)
    pdf.set_fill_color(250,250,250)
    pdf.rect(LM, ty0, W, tb_h, style='DF')
    pdf.set_xy(LM+4, ty0+2)
    pdf.set_font("Helvetica",'B', 8.8)
    pdf.set_text_color(*NAVY)
    pdf.cell(16, 4.5, "Terbilang:", 0, 1, 'L')
    pdf.set_x(LM+4)
    pdf.set_font("Helvetica",'', 8.8)
    pdf.set_text_color(*INK)
    pdf.multi_cell(W-8, 4.5, tb_text)
    pdf.set_y(ty0 + tb_h + 4)

    # ================================================================
    # TOTALS TABLE (right-aligned, 280px ~ 74mm, border navy, no top border)
    # ================================================================
    tw = 74
    tx = LM + W - tw
    lw = tw * 0.55
    vw = tw * 0.45

    def _sr(label, value, b='T', bold=False, color=None, fill=False, r_size=9.2):
        pdf.set_x(tx)
        fw = 'B' if bold else ''
        pdf.set_font("Helvetica", fw, r_size)
        pdf.set_text_color(*(color if color else DARK))
        f = 1 if fill else 0
        pdf.cell(lw, 5.5, f"  {label}", b, 0, 'L', f)
        pdf.cell(vw, 5.5, value, b, 1, 'R', f)

    pdf.set_draw_color(*NAVY)
    pdf.set_line_width(0.4)
    _sr("Subtotal", f"Rp {format_indo(total_tagihan)}", 'T')
    if diskon > 0:
        _sr("Diskon", f"- Rp {format_indo(diskon)}", '', color=DARK)
    # Grand total row
    _sr("Total", f"Rp {format_indo(total_setelah_diskon)}", 'TB', bold=True, r_size=11)
    pdf.ln(1)
    if deposit > 0:
        _sr("Sudah Dibayar", f"- Rp {format_indo(deposit)}", '', color=DARK)
    # Sisa Tagihan (navy bg, white text, 12pt)
    pdf.set_fill_color(*NAVY)
    pdf.set_text_color(*WHITE)
    pdf.set_font("Helvetica",'B', 12)
    pdf.set_x(tx)
    pdf.cell(lw, 7.5, "  Sisa Tagihan", 1, 0, 'L', 1)
    pdf.cell(vw, 7.5, f"Rp {format_indo(sisa_tgh)}", 1, 1, 'R', 1)
    pdf.set_text_color(*INK)
    pdf.ln(1)

    # ================================================================
    # RINCIAN PIUTANG (kondisional)
    # ================================================================
    if nr:
        pdf.set_draw_color(*LINE_SOFT)
        pdf.set_line_width(0.2)
        pdf.line(LM, pdf.get_y(), LM+W, pdf.get_y())
        pdf.ln(3)
        pdf.set_x(tx)
        pdf.set_font("Helvetica",'B', 8.6)
        pdf.set_text_color(*NAVY)
        pdf.cell(tw, 5, "Rincian Piutang", 0, 1, 'R')
        pdf.ln(1)
        pdf.set_font("Helvetica",'', 8.6)
        for lbl, val, clr in [
            ("Sisa Hutang Sebelumnya", f"Rp {format_indo(sisa_sebelum)}", GREY),
            ("Total Transaksi Baru",   f"Rp {format_indo(total_setelah_diskon)}", GREY),
        ]:
            pdf.set_x(tx); pdf.set_text_color(*clr)
            pdf.cell(lw, 5, lbl, 0, 0, 'L'); pdf.cell(vw, 5, val, 0, 1, 'R')
        pdf.set_x(tx); pdf.set_font("Helvetica",'B', 8.6)
        pdf.set_text_color(*NAVY)
        pdf.cell(lw, 5, "Total Sisa Piutang", 0, 0, 'L')
        pdf.cell(vw, 5, f"Rp {format_indo(subtotal_piutang)}", 0, 1, 'R')
        if deposit > 0:
            pdf.set_x(tx); pdf.set_text_color(*GREEN)
            pdf.set_font("Helvetica",'B', 8.6)
            pdf.cell(lw, 5, f"Deposit ({tgl_deposit}, {metode})", 0, 0, 'L')
            pdf.cell(vw, 5, f"- Rp {format_indo(deposit)}", 0, 1, 'R')
            pdf.set_draw_color(*NAVY); pdf.set_line_width(0.3)
            pdf.set_x(tx); pdf.cell(tw, 0, "", 'T', 1); pdf.ln(1)
            cs = PINK if sisa_baru > 0 else GREEN
            pdf.set_x(tx); pdf.set_text_color(*cs)
            pdf.set_font("Helvetica",'B', 9)
            label_s = "Sisa Hutang Baru"
            val_s = f"Rp {format_indo(sisa_baru)}" if sisa_baru > 0 else "Rp 0 (LUNAS)"
            pdf.cell(lw, 5.5, label_s, 0, 0, 'L')
            pdf.cell(vw, 5.5, val_s, 0, 1, 'R')

    pdf.ln(3)

    # ================================================================
    # PAYMENT INSTRUCTIONS (margin-top 12px)
    # ================================================================
    if pdf.get_y() + 18 > PH:
        pdf.add_page()
    pdf.set_font("Helvetica",'B', 8.4)
    pdf.set_text_color(*NAVY)
    pdf.cell(0, 5, "INSTRUKSI PEMBAYARAN", 0, 1, 'L')
    pdf.ln(1)
    pdf.set_font("Helvetica",'', 8.6)
    pdf.set_text_color(*GREY)
    for lbl, val in [("Bank","BRI"),("No. Rekening","224001017473501"),("Atas Nama","Achmad Fais Setiawan")]:
        pdf.cell(22, 4.5, lbl, 0, 0, 'L')
        pdf.cell(0, 4.5, f": {val}", 0, 1, 'L')

    pdf.ln(4)

    # ================================================================
    # SIGNATURE ROW (margin-top ~30px → 8mm)
    # ================================================================
    if pdf.get_y() + 20 > PH:
        pdf.add_page()

    # Left: notes
    pdf.set_font("Helvetica",'', 8)
    pdf.set_text_color(*GREY)
    pdf.multi_cell(95, 4,
        "Invoice ini sah tanpa tanda tangan basah. Konfirmasi pembayaran mohon "
        "dikirimkan melalui WhatsApp setelah transfer dilakukan.")

    # Right: signature
    sig_y = pdf.get_y()
    pdf.set_xy(LM+115, sig_y - 8)
    pdf.set_font("Helvetica",'', 8.8)
    pdf.set_text_color(*DARK)
    pdf.cell(75, 5, "Dengan Hormat,", 0, 1, 'C')
    # Signature space (margin-bottom 44px ~ 12mm)
    pdf.set_x(LM+115)
    pdf.ln(12)
    # Name with top border
    pdf.set_draw_color(*INK)
    pdf.set_line_width(0.2)
    ny = pdf.get_y()
    pdf.line(LM+130, ny, LM+175, ny)
    pdf.ln(1)
    pdf.set_x(LM+115)
    pdf.set_font("Helvetica",'B', 10)
    pdf.set_text_color(*NAVY)
    pdf.cell(75, 5, "YAZMINA HIJAB", 0, 1, 'C')
    pdf.set_x(LM+115)
    pdf.set_font("Helvetica",'', 8)
    pdf.set_text_color(*GREY)
    pdf.cell(75, 4, "Pemilik Usaha", 0, 1, 'C')
    sig_end = pdf.get_y()
    pdf.set_y(max(pdf.get_y(), sig_y + 15))

    # ================================================================
    # FOOTER STRIP (margin-top 26px, border-top 0.5px, padding-top 6px)
    # ================================================================
    if pdf.get_y() + 10 > PH:
        pdf.add_page()
    pdf.set_draw_color(*LINE_SOFT)
    pdf.set_line_width(0.15)
    pdf.line(LM, pdf.get_y(), LM+W, pdf.get_y())
    pdf.ln(2)
    pdf.set_font("Helvetica",'', 7.4)
    pdf.set_text_color(*GREY)
    pdf.cell(0, 4,
        "YAZMINA HIJAB  \u00b7  Konveksi & Grosir Hijab  \u00b7  "
        "Pendosawalan 16/06, Kec. Kalinyamatan, Jepara  \u00b7  0895-4269-50709", 0, 1, 'C')

    out_path = os.path.join(FOLDER, f"{no_inv}_{nama_klien.replace(' ','_')}.pdf")
    pdf.output(out_path)
    return out_path
        
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
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(width / 2.0, height - 15*mm, "NOTA PEMBAYARAN / DEPOSIT")
    
    c.setFont("Helvetica", 12)
    c.drawCentredString(width / 2.0, height - 20*mm, "=" * 75)
    
    # --- SUPPLIER INFO ---
    c.setFont("Helvetica-Bold", 12)
    c.drawString(15*mm, height - 30*mm, "NAMA SUPPLIER :")
    c.drawString(55*mm, height - 30*mm, nama_supplier.upper())
    
    c.setFont("Helvetica", 11)
    c.drawString(15*mm, height - 36*mm, "TGL BAYAR     :")
    c.drawString(55*mm, height - 36*mm, datetime.now().strftime("%d-%m-%Y"))
    
    c.drawString(15*mm, height - 42*mm, "KETERANGAN    :")
    c.drawString(55*mm, height - 42*mm, f"Pelunasan Batch {len(items)} Transaksi")

    # --- ITEM LIST HEADER ---
    y = height - 55*mm
    c.setFont("Helvetica-Bold", 11)
    c.drawString(15*mm, y, "--- REFERENSI TRANSAKSI TERPILIH ---")
    y -= 8*mm
    
    # NEW: Table Headers matching the old app
    c.setFont("Helvetica-Bold", 10)
    c.drawString(15*mm, y, "TGL")
    c.drawString(32*mm, y, "DESKRIPSI")
    c.drawString(78*mm, y, "QTY")
    c.drawString(92*mm, y, "HARGA/KG")
    c.drawRightString(133*mm, y, "DIBAYAR")
    y -= 3*mm
    c.line(15*mm, y, 133*mm, y)
    y -= 5*mm

    # --- ITEM ROWS ---
    c.setFont("Helvetica", 9)
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
            c.setFont("Helvetica", 8)

    # --- FINANCIAL SUMMARY ---
    y -= 5*mm
    c.setFont("Helvetica-Bold", 12)
    c.drawString(15*mm, y, "--- RINCIAN PEMBAYARAN BUKU BESAR ---")
    y -= 8*mm
    
    c.setFont("Helvetica", 12)
    c.drawString(15*mm, y, "1. Sisa Hutang (Awal) :")
    c.drawRightString(133*mm, y, f"Rp {sisa_awal:,.0f}")
    y -= 6*mm
    
    c.setFont("Helvetica-Bold", 14)
    c.drawString(15*mm, y, "2. TOTAL KAS DIBAYAR  :")
    c.drawRightString(133*mm, y, f"Rp {nominal_uang:,.0f}")
    y -= 4*mm
    c.line(15*mm, y, 133*mm, y)
    y -= 6*mm
    
    c.setFont("Helvetica", 12)
    c.drawString(15*mm, y, "3. Sisa Hutang Akhir  :")
    c.drawRightString(133*mm, y, f"Rp {sisa_akhir:,.0f}")
    
    c.save()
    return filepath