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
                        alamat_klien=None, telp_klien=None, pic_klien=None):
    """
    Generate PDF Invoice dengan format baru (mengacu Invoice_INV_0002.pdf):
    - Header: logo ESSA Store (kiri) + Invoice / Nomor / Tanggal / Jatuh Tempo (kanan)
    - Dua kolom info: Informasi Perusahaan (kiri) | Tagihan Kepada (kanan)
    - Tabel item: Produk | Kuantitas | Harga | Jumlah (tanpa kolom No & Deskripsi)
    - Terbilang, ringkasan finansial, rincian piutang (kondisional), instruksi bayar & tanda tangan

    Args:
        sales_data: list of PengeluaranOffline objects (yang dipilih).
        nama_klien: str — nama klien.
        total_tagihan: float — total dari semua sales_data.
        sisa_piutang: float — sisa piutang klien saat ini (dari ClientReceivable.sisa).
        deposit: float — jumlah deposit (0 jika tidak ada).
        tgl_deposit: str — tanggal deposit.
        metode: str — metode pembayaran (TUNAI/TRANSFER).
        simpan_deposit: bool — untuk pesan di result.
        alamat_klien: str (opsional) — alamat klien untuk kolom Tagihan Kepada.
        telp_klien: str (opsional) — nomor telepon klien.
        pic_klien: str (opsional) — nama PIC / Up klien.

    Returns:
        str — path file PDF yang dihasilkan.
    """
    from fpdf import FPDF
    import os, datetime

    # ─── Perhitungan finansial ───
    sisa_sebelum = max(0.0, sisa_piutang - total_tagihan)
    subtotal = sisa_piutang
    sisa_baru = max(0.0, subtotal - deposit)

    # ─── Path setup ───
    try:
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        APP_DIR = os.path.dirname(BASE_DIR)
    except NameError:
        APP_DIR = os.getcwd()

    FOLDER = os.path.join(APP_DIR, "exports", "invoices")
    if not os.path.exists(FOLDER):
        os.makedirs(FOLDER)

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    no_inv = f"INV-{timestamp}"
    tgl_cetak = datetime.date.today().strftime("%d/%m/%Y")
    tgl_jatuh_tempo = (datetime.date.today() + datetime.timedelta(days=30)).strftime("%d/%m/%Y")

    # ─── Constants ───
    LM = 10
    W = 190
    PAGE_H = 297  # A4 height in mm
    NAVY = (30, 41, 74)        # header tabel (navy gelap)
    BLUE = (33, 150, 243)      # aksen judul & garis
    DARK = (60, 60, 60)
    GRAY = (110, 110, 110)
    LIGHT_GRAY = (245, 245, 245)
    WHITE = (255, 255, 255)
    BLACK = (0, 0, 0)
    GREEN = (40, 167, 69)
    PINK = (233, 30, 99)

    pdf = FPDF()
    pdf.set_auto_page_break(auto=False)  # cegah footer "kepotong"
    pdf.add_page()

    # ====================================================================
    # HEADER — Logo (kiri) + "Invoice" & info nomor (kanan)
    # ====================================================================
    y0 = pdf.get_y()

    # --- Kiri: Logo ---
    logo_path = os.path.join(APP_DIR, "assets", "images", "Logo_Yazmina.png")
    if os.path.exists(logo_path):
        # Gunakan pdf.get_y() setelah image untuk dapat posisi bottom yang akurat
        pdf.image(logo_path, x=LM, y=y0 + 2, w=30)
        logo_bottom = pdf.get_y() if pdf.get_y() > y0 + 2 else y0 + 2 + 20
    else:
        # Fallback teks jika logo tidak ditemukan
        pdf.set_fill_color(*PINK)
        cx, cy = LM + 10, y0 + 8
        for dx, dy in [(-4, -3), (4, -3), (-4, 3), (4, 3), (0, 0)]:
            pdf.ellipse(cx + dx - 3, cy + dy - 3, 6, 6, style='F')
        pdf.set_font("Helvetica", 'B', 12)
        pdf.set_text_color(*DARK)
        pdf.set_xy(LM, y0 + 14)
        pdf.cell(60, 5, "ESSA", 0, 1, 'L')
        pdf.set_font("Helvetica", '', 9)
        pdf.set_text_color(*GRAY)
        pdf.set_x(LM)
        pdf.cell(60, 5, "Store", 0, 1, 'L')
        logo_bottom = pdf.get_y()

    # --- Kanan: judul "Invoice" + info nomor/tgl/jatuh tempo ---
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

    pdf.set_y(max(logo_bottom, ry) + 4)
    pdf.set_draw_color(*BLUE)
    pdf.set_line_width(0.4)
    pdf.line(LM, pdf.get_y(), LM + W, pdf.get_y())
    pdf.ln(6)

    # ====================================================================
    # INFORMASI PERUSAHAAN | TAGIHAN KEPADA (dua kolom sejajar)
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
    # Nama toko: ESSA HIJAB (bukan ESSA STORE — sesuai contoh invoice)
    pdf.set_font("Helvetica", 'B', 11)
    pdf.set_text_color(*BLUE)
    pdf.cell(col_w, 6, "YAZMINA HIJAB", 0, 1, 'L')

    # Alamat asli ESSA HIJAB (BUKAN alamat klien!)
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

    # Baris opsional: alamat, telp, PIC (hanya tampil jika diisi)
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
    # TABEL PRODUK — Produk | Kuantitas | Harga | Jumlah (tanpa No & Deskripsi)
    # ====================================================================
    col_produk = 75
    col_qty = 28
    col_harga = 42
    col_jumlah = 45  # total = 190

    def draw_table_header():
        pdf.set_font("Helvetica", 'B', 9)
        pdf.set_fill_color(*NAVY)       # Navy gelap (ganti dari BLUE cerah)
        pdf.set_text_color(*WHITE)
        pdf.cell(col_produk, 9, "Produk", 1, 0, 'L', 1)
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

        nama_produk = (item.sku.kode_sku if item.sku else "Barang Offline")
        nama_produk = nama_produk[:38].encode('latin-1', 'replace').decode('latin-1')
        qty_str = str(int(item.qty)) if float(item.qty).is_integer() else f"{item.qty:g}"
        harga_str = format_indo(item.harga_satuan)
        jumlah_str = format_indo(item.total)

        pdf.cell(col_produk, row_height, f" {nama_produk}", 1, 0, 'L', fill)
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
    # RINGKASAN FINANSIAL (rata kanan)
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
            ("Total Transaksi Baru",   f"Rp {format_indo(total_tagihan)}", GRAY),
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
    pdf.cell(0, 5, "YAZMINA HIJAB", 0, 1, 'C')

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