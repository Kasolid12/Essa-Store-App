"""
Yazmina Hijab Web — Hutang & Pelunasan CRUD API.

2 types:
- BARANG: goods debt from supplier
- MODAL: capital/money loan
"""

from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from ..database import get_db
from ..auth import get_current_admin
from ..models.debt import DebtEntry, DebtPayment
from ..models.person import Person
from ..models.sku import SkuMaster

router = APIRouter(prefix="/api/hutang", tags=["hutang"])

TIPE_OPTIONS = ["BARANG", "MODAL"]
METODE_OPTIONS = ["CASH", "TRANSFER", "POTONG_BON"]


# ── Schemas ───────────────────────────────────────────────────────────

class HutangCreate(BaseModel):
    tipe_hutang: str
    tanggal: str
    person_id: int
    keterangan: str
    sku_id: Optional[int] = None
    qty: Optional[float] = None
    kode_produksi: Optional[str] = None
    nominal_hutang: float
    catatan: Optional[str] = None


class HutangUpdate(BaseModel):
    tanggal: Optional[str] = None
    person_id: Optional[int] = None
    keterangan: Optional[str] = None
    sku_id: Optional[int] = None
    qty: Optional[float] = None
    kode_produksi: Optional[str] = None
    nominal_hutang: Optional[float] = None
    catatan: Optional[str] = None


class PaymentCreate(BaseModel):
    tanggal_bayar: str
    nominal_bayar: float
    metode: Optional[str] = "CASH"
    catatan: Optional[str] = None


class HutangOut(BaseModel):
    id: int
    tipe_hutang: str
    tanggal: str
    person_id: int
    person_nama: Optional[str] = None
    keterangan: str
    sku_id: Optional[int] = None
    sku_nama: Optional[str] = None
    sku_kode: Optional[str] = None
    qty: Optional[float] = None
    kode_produksi: Optional[str] = None
    nominal_hutang: float
    terbayar: float = 0.0
    sisa: float = 0.0
    status: str
    catatan: Optional[str] = None
    is_deleted: int

    model_config = {"from_attributes": True}


# ── Helpers ───────────────────────────────────────────────────────────

def _calc_paid(debt: DebtEntry, db: Session) -> float:
    total = db.query(func.coalesce(func.sum(DebtPayment.nominal_bayar), 0.0)).filter(
        DebtPayment.debt_entry_id == debt.id,
        DebtPayment.is_deleted == 0,
    ).scalar()
    return total or 0.0


def _enrich(debt: DebtEntry, db: Session) -> dict:
    terbayar = _calc_paid(debt, db)
    sisa = max(0.0, debt.nominal_hutang - terbayar)
    return {
        "id": debt.id,
        "tipe_hutang": debt.tipe_hutang,
        "tanggal": debt.tanggal,
        "person_id": debt.person_id,
        "person_nama": debt.person.nama if debt.person else None,
        "keterangan": debt.keterangan,
        "sku_id": debt.sku_id,
        "sku_nama": debt.sku.nama_produk if debt.sku else None,
        "sku_kode": debt.sku.kode_sku if debt.sku else None,
        "qty": debt.qty,
        "kode_produksi": debt.kode_produksi,
        "nominal_hutang": debt.nominal_hutang,
        "terbayar": terbayar,
        "sisa": sisa,
        "status": debt.status,
        "catatan": debt.catatan,
        "is_deleted": debt.is_deleted,
    }


def _update_status(debt: DebtEntry, db: Session):
    terbayar = _calc_paid(debt, db)
    if terbayar >= debt.nominal_hutang:
        debt.status = "LUNAS"
    elif terbayar > 0:
        debt.status = "PARTIAL"
    else:
        debt.status = "OPEN"


# ── Routes ────────────────────────────────────────────────────────────

@router.get("/tipe")
def list_tipe():
    return TIPE_OPTIONS


@router.get("/metode")
def list_metode():
    return METODE_OPTIONS


@router.get("")
def list_hutang(
    tipe_hutang: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    q = db.query(DebtEntry).filter(DebtEntry.is_deleted == 0)

    if tipe_hutang:
        q = q.filter(DebtEntry.tipe_hutang == tipe_hutang)
    if status:
        q = q.filter(DebtEntry.status == status)
    if date_from:
        q = q.filter(DebtEntry.tanggal >= date_from)
    if date_to:
        q = q.filter(DebtEntry.tanggal <= date_to)

    items = q.order_by(
        DebtEntry.status.desc(), DebtEntry.tanggal.desc(), DebtEntry.id.desc()
    ).limit(200).all()

    return [_enrich(d, db) for d in items]


@router.get("/summary")
def summary(
    tipe_hutang: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    q = db.query(DebtEntry).filter(DebtEntry.is_deleted == 0)
    if tipe_hutang:
        q = q.filter(DebtEntry.tipe_hutang == tipe_hutang)

    debts = q.all()
    total_hutang = sum(d.nominal_hutang for d in debts)
    total_terbayar = sum(_calc_paid(d, db) for d in debts)
    total_sisa = max(0, total_hutang - total_terbayar)
    count_open = sum(1 for d in debts if d.status == "OPEN")
    count_partial = sum(1 for d in debts if d.status == "PARTIAL")
    count_lunas = sum(1 for d in debts if d.status == "LUNAS")

    return {
        "total_hutang": total_hutang,
        "total_terbayar": total_terbayar,
        "total_sisa": total_sisa,
        "count_open": count_open,
        "count_partial": count_partial,
        "count_lunas": count_lunas,
    }


@router.post("")
def create_hutang(
    body: HutangCreate,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    if body.tipe_hutang not in TIPE_OPTIONS:
        raise HTTPException(400, f"Tipe '{body.tipe_hutang}' tidak valid")

    person = db.get(Person, body.person_id)
    if not person:
        raise HTTPException(400, "Person tidak ditemukan")

    if body.sku_id:
        sku = db.get(SkuMaster, body.sku_id)
        if not sku:
            raise HTTPException(400, "SKU tidak ditemukan")

    debt = DebtEntry(**body.model_dump())
    debt.status = "OPEN"
    db.add(debt)
    db.commit()
    db.refresh(debt)
    return _enrich(debt, db)


@router.put("/{debt_id}")
def update_hutang(
    debt_id: int,
    body: HutangUpdate,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    debt = db.get(DebtEntry, debt_id)
    if not debt or debt.is_deleted:
        raise HTTPException(404, "Data hutang tidak ditemukan")

    data = body.model_dump(exclude_unset=True)

    if "person_id" in data:
        person = db.get(Person, data["person_id"])
        if not person:
            raise HTTPException(400, "Person tidak ditemukan")

    if "sku_id" in data and data["sku_id"]:
        sku = db.get(SkuMaster, data["sku_id"])
        if not sku:
            raise HTTPException(400, "SKU tidak ditemukan")

    for k, v in data.items():
        setattr(debt, k, v)

    _update_status(debt, db)
    db.commit()
    db.refresh(debt)
    return _enrich(debt, db)


@router.delete("/{debt_id}")
def delete_hutang(
    debt_id: int,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    debt = db.get(DebtEntry, debt_id)
    if not debt or debt.is_deleted:
        raise HTTPException(404, "Data hutang tidak ditemukan")

    # Soft-delete all payments
    for p in db.query(DebtPayment).filter(DebtPayment.debt_entry_id == debt_id).all():
        p.is_deleted = 1

    debt.is_deleted = 1
    db.commit()
    return {"message": "Data hutang dihapus"}


# ── Payment endpoints ─────────────────────────────────────────────────

@router.get("/{debt_id}/payments")
def list_payments(
    debt_id: int,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    debt = db.get(DebtEntry, debt_id)
    if not debt or debt.is_deleted:
        raise HTTPException(404, "Data hutang tidak ditemukan")

    payments = db.query(DebtPayment).filter(
        DebtPayment.debt_entry_id == debt_id,
        DebtPayment.is_deleted == 0,
    ).order_by(DebtPayment.tanggal_bayar.desc()).all()

    return [
        {
            "id": p.id,
            "tanggal_bayar": p.tanggal_bayar,
            "nominal_bayar": p.nominal_bayar,
            "metode": p.metode,
            "catatan": p.catatan,
        }
        for p in payments
    ]


@router.post("/{debt_id}/payments")
def create_payment(
    debt_id: int,
    body: PaymentCreate,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    debt = db.get(DebtEntry, debt_id)
    if not debt or debt.is_deleted:
        raise HTTPException(404, "Data hutang tidak ditemukan")

    if body.nominal_bayar <= 0:
        raise HTTPException(400, "Nominal bayar harus lebih dari 0")

    payment = DebtPayment(
        debt_entry_id=debt_id,
        tanggal_bayar=body.tanggal_bayar,
        nominal_bayar=body.nominal_bayar,
        metode=body.metode,
        catatan=body.catatan,
    )
    db.add(payment)

    # Update status
    _update_status(debt, db)
    db.commit()
    db.refresh(debt)

    terbayar = _calc_paid(debt, db)
    return {
        "message": "Pembayaran tercatat",
        "status": debt.status,
        "terbayar": terbayar,
        "sisa": max(0, debt.nominal_hutang - terbayar),
    }


@router.post("/batch-pay")
def batch_pay(
    debt_ids: List[int],
    tanggal_bayar: str,
    nominal_total: float,
    metode: str = "CASH",
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    """Batch payment: split nominal across multiple debts (same person only)."""
    if not debt_ids:
        raise HTTPException(400, "Pilih minimal 1 hutang")

    if nominal_total <= 0:
        raise HTTPException(400, "Nominal harus lebih dari 0")

    debts = []
    person_ids = set()
    for did in debt_ids:
        debt = db.get(DebtEntry, did)
        if not debt or debt.is_deleted:
            raise HTTPException(404, f"Hutang ID {did} tidak ditemukan")
        debts.append(debt)
        person_ids.add(debt.person_id)

    if len(person_ids) > 1:
        raise HTTPException(400, "Hanya bisa melunasi hutang dari SATU SUPPLIER yang sama")

    sisa_uang = nominal_total
    for debt in debts:
        if sisa_uang <= 0:
            break
        terbayar = _calc_paid(debt, db)
        sisa_tagihan = debt.nominal_hutang - terbayar
        if sisa_tagihan <= 0:
            continue
        bayar = min(sisa_uang, sisa_tagihan)
        payment = DebtPayment(
            debt_entry_id=debt.id,
            tanggal_bayar=tanggal_bayar,
            nominal_bayar=bayar,
            metode=metode,
            catatan=f"Batch payment",
        )
        db.add(payment)
        _update_status(debt, db)
        sisa_uang -= bayar

    db.commit()
    return {"message": f"Batch payment berhasil: Rp {nominal_total:,.0f}"}
