"""
Yazmina Hijab Web — Pengeluaran Offline (Penjualan) CRUD API.
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..database import get_db
from ..auth import get_current_admin
from ..models.daily_notes import PengeluaranOffline
from ..models.sku import SkuMaster
from ..models.person import Person
from ..models.invoice import Client

router = APIRouter(prefix="/api/pengeluaran-offline", tags=["pengeluaran-offline"])


# ── Schemas ───────────────────────────────────────────────────────────

class PengeluaranCreate(BaseModel):
    tanggal: str
    sku_id: int
    qty: float
    harga_satuan: float
    total: float
    person_id: Optional[int] = None
    client_id: Optional[int] = None
    catatan: Optional[str] = None


class PengeluaranUpdate(BaseModel):
    tanggal: Optional[str] = None
    sku_id: Optional[int] = None
    qty: Optional[float] = None
    harga_satuan: Optional[float] = None
    total: Optional[float] = None
    person_id: Optional[int] = None
    client_id: Optional[int] = None
    catatan: Optional[str] = None


class PengeluaranOut(BaseModel):
    id: int
    tanggal: str
    sku_id: int
    sku_nama: Optional[str] = None
    person_id: Optional[int] = None
    person_nama: Optional[str] = None
    client_id: Optional[int] = None
    qty: float
    harga_satuan: float
    total: float
    catatan: Optional[str] = None
    is_deleted: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ── Helper ────────────────────────────────────────────────────────────

def _enrich(item: PengeluaranOut, db: Session) -> dict:
    """Add sku_nama, person_nama, client_nama to output."""
    d = item.model_dump()
    sku = db.get(SkuMaster, item.sku_id)
    d["sku_nama"] = sku.nama_produk if sku else None
    if item.person_id:
        person = db.get(Person, item.person_id)
        d["person_nama"] = person.nama if person else None
    if item.client_id:
        client = db.get(Client, item.client_id)
        d["client_nama"] = client.nama if client else None
    return d


# ── Routes ────────────────────────────────────────────────────────────

@router.get("")
def list_pengeluaran(
    search: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    q = db.query(PengeluaranOffline).filter(PengeluaranOffline.is_deleted == 0)

    if date_from:
        q = q.filter(PengeluaranOffline.tanggal >= date_from)
    if date_to:
        q = q.filter(PengeluaranOffline.tanggal <= date_to)

    items = q.order_by(
        PengeluaranOffline.tanggal.desc(), PengeluaranOffline.id.desc()
    ).limit(200).all()

    result = []
    for item in items:
        out = PengeluaranOut.model_validate(item)
        result.append(_enrich(out, db))
    return result


@router.get("/summary")
def summary(
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    q = db.query(
        func.coalesce(func.sum(PengeluaranOffline.total), 0.0),
        func.coalesce(func.sum(PengeluaranOffline.qty), 0.0),
    ).filter(PengeluaranOffline.is_deleted == 0)

    if date_from:
        q = q.filter(PengeluaranOffline.tanggal >= date_from)
    if date_to:
        q = q.filter(PengeluaranOffline.tanggal <= date_to)

    row = q.one()
    return {"total_penjualan": row[0], "total_qty": row[1]}


@router.post("")
def create_pengeluaran(
    body: PengeluaranCreate,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    # Validate SKU exists
    sku = db.get(SkuMaster, body.sku_id)
    if not sku:
        raise HTTPException(400, "SKU tidak ditemukan")

    entry = PengeluaranOffline(**body.model_dump())
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return _enrich(PengeluaranOut.model_validate(entry), db)


@router.put("/{entry_id}")
def update_pengeluaran(
    entry_id: int,
    body: PengeluaranUpdate,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    entry = db.get(PengeluaranOffline, entry_id)
    if not entry or entry.is_deleted:
        raise HTTPException(404, "Data tidak ditemukan")

    data = body.model_dump(exclude_unset=True)

    if "sku_id" in data:
        sku = db.get(SkuMaster, data["sku_id"])
        if not sku:
            raise HTTPException(400, "SKU tidak ditemukan")

    for k, v in data.items():
        setattr(entry, k, v)

    db.commit()
    db.refresh(entry)
    return _enrich(PengeluaranOut.model_validate(entry), db)


@router.delete("/{entry_id}")
def delete_pengeluaran(
    entry_id: int,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    entry = db.get(PengeluaranOffline, entry_id)
    if not entry or entry.is_deleted:
        raise HTTPException(404, "Data tidak ditemukan")
    entry.is_deleted = 1
    db.commit()
    return {"message": "Data penjualan dihapus"}
