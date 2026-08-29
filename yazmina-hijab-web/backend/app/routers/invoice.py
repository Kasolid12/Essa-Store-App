"""Invoice & Piutang API.

Matches desktop invoice_view.py logic:
- Client dropdown: Client table + Person (KLIEN) with existing sales
- Combined transaction table: PengeluaranOffline (sales) + ClientReceivablePayment (payments)
- FIFO status computation: payments applied to oldest sales first
- Summary: total tagihan, total dibayar, sisa, status
- Deposit: save payment + recalculate receivable (self-healing)
"""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from ..database import get_db
from ..auth import get_current_admin
from ..models.invoice import Client, ClientReceivable, ClientReceivablePayment
from ..models.person import Person
from ..models.daily_notes import PengeluaranOffline

router = APIRouter(prefix="/api/invoice", tags=["invoice"])


# ── Schemas ────────────────────────────────────────────────────────

class ClientOption(BaseModel):
    id: str  # "client_3" or "person_5"
    nama: str
    ref_type: str  # "client" or "person"
    ref_id: int

class TransactionRow(BaseModel):
    id: str  # "S12" (sale) or "P5" (payment)
    tanggal: str
    jenis: str  # "Penjualan" or "Pembayaran"
    keterangan: str
    debit: float = 0.0
    credit: float = 0.0
    status: str = ""  # LUNAS / PARTIAL / BELUM LUNAS

class InvoiceSummary(BaseModel):
    total_tagihan: float = 0.0
    total_bayar: float = 0.0
    sisa: float = 0.0
    status: str = "-"

class DepositIn(BaseModel):
    tanggal_bayar: str
    nominal_bayar: float
    metode: str = "CASH"
    catatan: Optional[str] = None


# ── Helpers ────────────────────────────────────────────────────────

def _get_client_options(db: Session) -> list[ClientOption]:
    """Build dropdown: Client table + Person who have sales or receivables."""
    options = []

    # Clients from Client table
    clients = db.query(Client).filter(Client.is_deleted == 0).order_by(Client.nama).all()
    for c in clients:
        options.append(ClientOption(id=f"client_{c.id}", nama=c.nama, ref_type="client", ref_id=c.id))

    # Persons who have PengeluaranOffline or ClientReceivable
    person_ids_sales = {
        r[0] for r in db.query(PengeluaranOffline.person_id)
        .filter(PengeluaranOffline.is_deleted == 0, PengeluaranOffline.person_id.isnot(None))
        .distinct().all() if r[0]
    }
    person_ids_cr = {
        r[0] for r in db.query(ClientReceivable.person_id)
        .filter(ClientReceivable.person_id.isnot(None))
        .distinct().all() if r[0]
    }
    all_ids = person_ids_sales | person_ids_cr
    if all_ids:
        persons = db.query(Person).filter(Person.id.in_(all_ids)).order_by(Person.nama).all()
        for p in persons:
            options.append(ClientOption(id=f"person_{p.id}", nama=f"{p.nama} (Person)", ref_type="person", ref_id=p.id))

    return options


def _parse_client_id(raw_id: str):
    """Parse 'client_3' -> ('client', 3) or 'person_5' -> ('person', 5)."""
    parts = raw_id.split("_", 1)
    return parts[0], int(parts[1])


def _get_sales(db: Session, ref_type: str, ref_id: int):
    """Get PengeluaranOffline for a client/person."""
    if ref_type == "client":
        return db.query(PengeluaranOffline).filter(
            PengeluaranOffline.client_id == ref_id,
            PengeluaranOffline.is_deleted == 0,
        ).order_by(PengeluaranOffline.tanggal, PengeluaranOffline.id).all()
    else:
        return db.query(PengeluaranOffline).filter(
            PengeluaranOffline.person_id == ref_id,
            PengeluaranOffline.is_deleted == 0,
        ).order_by(PengeluaranOffline.tanggal, PengeluaranOffline.id).all()


def _get_receivable(db: Session, ref_type: str, ref_id: int):
    """Get ClientReceivable for a client/person."""
    if ref_type == "client":
        return db.query(ClientReceivable).filter(ClientReceivable.client_id == ref_id).first()
    else:
        return db.query(ClientReceivable).filter(ClientReceivable.person_id == ref_id).first()


def _build_combined_rows(db: Session, ref_type: str, ref_id: int) -> list[TransactionRow]:
    """Build combined sales + payments list with FIFO status."""
    rows = []

    # Sales
    sales = _get_sales(db, ref_type, ref_id)
    for s in sales:
        sku_nama = ""
        if hasattr(s, 'sku') and s.sku:
            sku_nama = s.sku.kode_sku or ""
        person_nama = ""
        if hasattr(s, 'person') and s.person:
            person_nama = s.person.nama
        elif hasattr(s, 'client') and s.client:
            person_nama = s.client.nama
        qty_str = f"{int(s.qty)}" if s.qty == int(s.qty) else f"{s.qty:g}"
        keterangan = f"{sku_nama} x{qty_str}" + (f" | {person_nama}" if person_nama else "")
        rows.append(TransactionRow(
            id=f"S{s.id}",
            tanggal=s.tanggal,
            jenis="Penjualan",
            keterangan=keterangan,
            debit=float(s.total),
            credit=0.0,
            status="BELUM LUNAS",
        ))

    # Payments
    receivable = _get_receivable(db, ref_type, ref_id)
    if receivable:
        payments = db.query(ClientReceivablePayment).filter(
            ClientReceivablePayment.receivable_id == receivable.id
        ).order_by(ClientReceivablePayment.tanggal_bayar, ClientReceivablePayment.id).all()
        for p in payments:
            rows.append(TransactionRow(
                id=f"P{p.id}",
                tanggal=p.tanggal_bayar,
                jenis="Pembayaran",
                keterangan=f"Deposit ({p.metode or '-'})",
                debit=0.0,
                credit=float(p.nominal_bayar),
                status="LUNAS",
            ))

    # Sort: sales first, then payments, by date
    rows.sort(key=lambda r: (r.tanggal, 0 if r.jenis == "Penjualan" else 1, r.id))

    # FIFO status computation
    fifo_queue = []
    for i, r in enumerate(rows):
        if r.jenis == "Penjualan":
            fifo_queue.append({"idx": i, "sisa": r.debit})
            r.status = "BELUM LUNAS"
        else:
            sisa_bayar = r.credit
            while sisa_bayar > 0 and fifo_queue:
                oldest = fifo_queue[0]
                if sisa_bayar >= oldest["sisa"]:
                    sisa_bayar -= oldest["sisa"]
                    rows[oldest["idx"]].status = "LUNAS"
                    fifo_queue.pop(0)
                else:
                    oldest["sisa"] -= sisa_bayar
                    rows[oldest["idx"]].status = "PARTIAL"
                    sisa_bayar = 0
            r.status = "LUNAS"

    return rows


def _recalculate_receivable(db: Session, ref_type: str, ref_id: int):
    """Self-healing: recalculate ClientReceivable from actual data."""
    total_tagihan = 0.0
    sales = _get_sales(db, ref_type, ref_id)
    for s in sales:
        total_tagihan += float(s.total or 0)

    receivable = _get_receivable(db, ref_type, ref_id)

    total_bayar = 0.0
    if receivable:
        total_bayar = db.query(func.coalesce(func.sum(ClientReceivablePayment.nominal_bayar), 0.0)).filter(
            ClientReceivablePayment.receivable_id == receivable.id
        ).scalar() or 0.0

    sisa_baru = max(0.0, total_tagihan - total_bayar)

    if receivable:
        receivable.nominal = total_tagihan
        receivable.sisa = sisa_baru
        receivable.status = "LUNAS" if sisa_baru <= 0 else "OPEN"
    elif total_tagihan > 0:
        kwargs = {"nominal": total_tagihan, "sisa": sisa_baru, "status": "OPEN" if sisa_baru > 0 else "LUNAS"}
        if ref_type == "client":
            kwargs["client_id"] = ref_id
        else:
            kwargs["person_id"] = ref_id
        receivable = ClientReceivable(**kwargs)
        db.add(receivable)

    db.commit()
    return receivable


# ── Endpoints ──────────────────────────────────────────────────────

@router.get("/clients", response_model=list[ClientOption])
def list_invoice_clients(
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    """Client dropdown: Client + Person with sales."""
    return _get_client_options(db)


@router.get("/combined/{client_ref}")
def get_combined_table(
    client_ref: str,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    """Combined transaction table for a client."""
    ref_type, ref_id = _parse_client_id(client_ref)
    _recalculate_receivable(db, ref_type, ref_id)
    rows = _build_combined_rows(db, ref_type, ref_id)
    return {"rows": [r.model_dump() for r in rows]}


@router.get("/summary/{client_ref}", response_model=InvoiceSummary)
def get_summary(
    client_ref: str,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    """Summary: total tagihan, total dibayar, sisa, status."""
    ref_type, ref_id = _parse_client_id(client_ref)
    receivable = _get_receivable(db, ref_type, ref_id)
    sales = _get_sales(db, ref_type, ref_id)
    total_all = sum(float(s.total or 0) for s in sales)

    total_bayar = 0.0
    sisa = total_all
    if receivable:
        total_bayar = max(0.0, receivable.nominal - receivable.sisa)
        sisa = receivable.sisa

    return InvoiceSummary(
        total_tagihan=total_all,
        total_bayar=total_bayar,
        sisa=max(0.0, sisa),
        status="LUNAS" if sisa <= 0 else "BELUM LUNAS",
    )


@router.post("/deposit/{client_ref}")
def create_deposit(
    client_ref: str,
    body: DepositIn,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    """Save a deposit payment."""
    ref_type, ref_id = _parse_client_id(client_ref)

    receivable = _get_receivable(db, ref_type, ref_id)
    if not receivable:
        # Create receivable first
        _recalculate_receivable(db, ref_type, ref_id)
        receivable = _get_receivable(db, ref_type, ref_id)
        if not receivable:
            raise HTTPException(400, "Tidak ada data penjualan untuk klien ini")

    payment = ClientReceivablePayment(
        receivable_id=receivable.id,
        tanggal_bayar=body.tanggal_bayar,
        nominal_bayar=body.nominal_bayar,
        metode=body.metode,
        catatan=body.catatan,
    )
    db.add(payment)
    db.commit()

    # Self-heal
    _recalculate_receivable(db, ref_type, ref_id)

    return {"ok": True, "message": f"Deposit Rp {body.nominal_bayar:,.0f} berhasil disimpan"}


@router.delete("/payment/{payment_id}")
def delete_payment(
    payment_id: int,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    """Delete a payment and recalculate receivable."""
    payment = db.query(ClientReceivablePayment).filter(ClientReceivablePayment.id == payment_id).first()
    if not payment:
        raise HTTPException(404, "Payment not found")

    receivable = payment.receivable
    db.delete(payment)
    db.commit()

    # Self-heal
    if receivable:
        if receivable.client_id:
            _recalculate_receivable(db, "client", receivable.client_id)
        elif receivable.person_id:
            _recalculate_receivable(db, "person", receivable.person_id)

    return {"ok": True}
