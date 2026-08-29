"""
Yazmina Hijab Web — Hasil Cutting CRUD API.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from ..auth import get_current_admin
from ..models.daily_notes import HasilCutting
from ..models.sku import SkuMaster

router = APIRouter(prefix="/api/hasil-cutting", tags=["hasil-cutting"])


# ── Schemas ───────────────────────────────────────────────────────────

class HasilCuttingCreate(BaseModel):
    tanggal: str
    sku_id: int
    qty: int
    kode_produksi: Optional[str] = None
    catatan: Optional[str] = None


class HasilCuttingUpdate(BaseModel):
    tanggal: Optional[str] = None
    sku_id: Optional[int] = None
    qty: Optional[int] = None
    kode_produksi: Optional[str] = None
    catatan: Optional[str] = None


class HasilCuttingOut(BaseModel):
    id: int
    tanggal: str
    sku_id: int
    sku_nama: Optional[str] = None
    sku_kode: Optional[str] = None
    qty: int
    kode_produksi: Optional[str] = None
    catatan: Optional[str] = None
    is_deleted: int

    model_config = {"from_attributes": True}


# ── Helper ────────────────────────────────────────────────────────────

def _enrich(item: HasilCuttingOut, db: Session) -> dict:
    d = item.model_dump()
    sku = db.get(SkuMaster, item.sku_id)
    if sku:
        d["sku_nama"] = sku.nama_produk
        d["sku_kode"] = sku.kode_sku
    return d


# ── Routes ────────────────────────────────────────────────────────────

@router.get("")
def list_hasil_cutting(
    search: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    q = db.query(HasilCutting).filter(HasilCutting.is_deleted == 0)

    if date_from:
        q = q.filter(HasilCutting.tanggal >= date_from)
    if date_to:
        q = q.filter(HasilCutting.tanggal <= date_to)

    items = q.order_by(
        HasilCutting.tanggal.desc(), HasilCutting.id.desc()
    ).limit(200).all()

    return [_enrich(HasilCuttingOut.model_validate(i), db) for i in items]


@router.post("")
def create_hasil_cutting(
    body: HasilCuttingCreate,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    sku = db.get(SkuMaster, body.sku_id)
    if not sku:
        raise HTTPException(400, "SKU tidak ditemukan")

    entry = HasilCutting(**body.model_dump())
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return _enrich(HasilCuttingOut.model_validate(entry), db)


@router.put("/{entry_id}")
def update_hasil_cutting(
    entry_id: int,
    body: HasilCuttingUpdate,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    entry = db.get(HasilCutting, entry_id)
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
    return _enrich(HasilCuttingOut.model_validate(entry), db)


@router.delete("/{entry_id}")
def delete_hasil_cutting(
    entry_id: int,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    entry = db.get(HasilCutting, entry_id)
    if not entry or entry.is_deleted:
        raise HTTPException(404, "Data tidak ditemukan")
    entry.is_deleted = 1
    db.commit()
    return {"message": "Data hasil cutting dihapus"}
