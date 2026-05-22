# app_essa/utils/pdf_engine.py
import os
from datetime import datetime
from reportlab.lib.pagesizes import A5 # A5 is half an A4 page, perfect for slips
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm

from data.database import SessionLocal
from data.models import SalaryRun
from data.models import SalaryRun, PengeluaranOffline # <--- Add PengeluaranOffline here

def generate_salary_slip(salary_run_id):
    """Generates an Industrial-style PDF salary slip."""
    db = SessionLocal()
    try:
        # 1. Fetch the data
        run = db.query(SalaryRun).get(salary_run_id)
        if not run:
            raise ValueError("Salary Run ID not found.")
            
        person = run.person
        
        # 2. Setup the File Path
        # Creates a 'exports/slips' folder in your root directory if it doesn't exist
        export_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "exports", "slips")
        os.makedirs(export_dir, exist_ok=True)
        
        filename = f"SLIP_{person.nama.replace(' ', '_')}_{run.tanggal_proses}.pdf"
        filepath = os.path.join(export_dir, filename)

        # 3. Initialize the PDF Canvas (A5 Landscape)
        c = canvas.Canvas(filepath, pagesize=(210*mm, 148*mm))
        
        # --- DRAWING THE INDUSTRIAL AESTHETIC ---
        
        # Outer Border (Sharp, industrial frame)
        c.setLineWidth(2)
        c.rect(10*mm, 10*mm, 190*mm, 128*mm)
        c.setLineWidth(1)
        c.rect(12*mm, 12*mm, 186*mm, 124*mm) # Inner accent line
        
        # HEADER
        c.setFont("Courier-Bold", 18)
        c.drawString(16*mm, 122*mm, "ESSA STORE // PAYROLL MANIFEST")
        
        c.setFont("Courier", 9)
        c.drawString(16*mm, 116*mm, f"GENERATED: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        c.drawString(16*mm, 112*mm, f"SYSTEM ID: TXN-{run.id:06d}")
        
        # Divider Line
        c.line(16*mm, 108*mm, 194*mm, 108*mm)

        # EMPLOYEE DETAILS
        c.setFont("Courier-Bold", 12)
        c.drawString(16*mm, 98*mm, "RECIPIENT DATA")
        c.setFont("Courier", 11)
        c.drawString(16*mm, 90*mm, f"NAMA      : {person.nama.upper()}")
        c.drawString(16*mm, 84*mm, f"KATEGORI  : {person.person_type}")
        c.drawString(16*mm, 78*mm, f"PERIODE   : {run.periode_mulai} to {run.periode_akhir}")

        # FINANCIAL DETAILS BOX
        c.rect(100*mm, 68*mm, 94*mm, 35*mm) # Right-side box
        c.setFont("Courier-Bold", 12)
        c.drawString(104*mm, 96*mm, "FINANCIAL SUMMARY")
        
        c.setFont("Courier", 11)
        c.drawString(104*mm, 90*mm, "GAJI KOTOR (BASE) :")
        c.drawRightString(190*mm, 90*mm, f"Rp {run.gaji_kotor:,.0f}")
        
        c.drawString(104*mm, 82*mm, "POTONGAN KASBON   :")
        c.drawRightString(190*mm, 82*mm, f"- Rp {run.potong_bon:,.0f}")
        
        # Separator inside box
        c.line(104*mm, 76*mm, 190*mm, 76*mm)
        
        # Net Salary
        c.setFont("Courier-Bold", 14)
        c.drawString(104*mm, 70*mm, "GAJI BERSIH :")
        c.drawRightString(190*mm, 70*mm, f"Rp {run.gaji_bersih:,.0f}")

        # FOOTER / SIGNATURES
        c.setFont("Courier", 10)
        c.drawString(20*mm, 40*mm, "AUTHORIZED BY (ADMIN)")
        c.line(20*mm, 25*mm, 70*mm, 25*mm)
        
        c.drawString(140*mm, 40*mm, "RECEIVED BY")
        c.line(140*mm, 25*mm, 190*mm, 25*mm)
        c.drawString(140*mm, 20*mm, person.nama.upper())

        # Save the PDF
        c.save()
        return filepath
        
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