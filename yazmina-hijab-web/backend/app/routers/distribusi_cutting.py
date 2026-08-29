"""
Yazmina Hijab Web — Distribusi Cutting CRUD API.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from ..auth import get_current_admin
from ..models.daily_notes import HasilCutting, DistribusiCutting
from ..models.sku import SkuMaster
from ..models.person import Person

router = APIRouter(prefix="/api/distribusi-cutting", tags=["distribusi-cutting"])


# ── Schemas ───────────────────────────────────────────────────────────

class DistribusiCreate(BaseModel):
    tanggal: str
    person_id: int
    sku_id: int
    qty: int
    hasil_cutting_id: Optional[int] = None
    catatan: Optional[str] = None


class DistribusiUpdate(BaseModel):
    tanggal: Optional[str] = None
    person_id: Optional[int] = None
    sku_id: Optional[int] = None
    qty: Optional[int] = None
    hasil_cutting_id: Optional[int] = None
    catatan: Optional[str] = None


class DistribusiOut(BaseModel):
    id: int
    tanggal: str
    person_id: int
    person_nama: Optional[str] = None
    person_jenis: Optional[str] = None
    sku_id: int
    sku_nama: Optional[str] = None
    sku_kode: Optional[str] = None
    qty: int
    hasil_cutting_id: Optional[int] = None
    catatan: Optional[str] = None
    is_deleted: int

    model_config = {"from_attributes": True}


# ── Helper ────────────────────────────────────────────────────────────

def _enrich(item: DistribusiOut, db: Session) -> dict:
    d = item.model_dump()
    sku = db.get(SkuMaster, item.sku_id)
    if sku:
        d["sku_nama"] = sku.nama_produk
        d["sku_kode"] = sku.kode_sku
    person = db.get(Person, item.person_id)
    if person:
        d["person_nama"] = person.nama
        d["person_jenis"] = person.person_type
    return d


# ── Routes ────────────────────────────────────────────────────────────

@router.get("")
def list_distribusi(
    search: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    q = db.query(DistribusiCutting).filter(DistribusiCutting.is_deleted == 0)

    if date_from:
        q = q.filter(DistribusiCutting.tanggal >= date_from)
    if date_to:
        q = q.filter(DistribusiCutting.tanggal <= date_to)

    items = q.order_by(
        DistribusiCutting.tanggal.desc(), DistribusiCutting.id.desc()
    ).limit(200).all()

    return [_enrich(DistribusiOut.model_validate(i), db) for i in items]


@router.post("")
def create_distribusi(
    body: DistribusiCreate,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    person = db.get(Person, body.person_id)
    if not person:
        raise HTTPException(400, "Person tidak ditemukan")

    sku = db.get(SkuMaster, body.sku_id)
    if not sku:
        raise HTTPException(400, "SKU tidak ditemukan")

    entry = DistribusiCutting(
        tanggal=body.tanggal,
        person_id=body.person_id,
        jenis=person.person_type,
        sku_id=body.sku_id,
        qty=body.qty,
        hasil_cutting_id=body.hasil_cutting_id,
        catatan=body.catatan,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return _enrich(DistribusiOut.model_validate(entry), db)


@router.put("/{entry_id}")
def update_distribusi(
    entry_id: int,
    body: DistribusiUpdate,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    entry = db.get(DistribusiCutting, entry_id)
    if not entry or entry.is_deleted:
        raise HTTPException(404, "Data tidak ditemukan")

    data = body.model_dump(exclude_unset=True)

    if "person_id" in data:
        person = db.get(Person, data["person_id"])
        if not person:
            raise HTTPException(400, "Person tidak ditemukan")
        entry.jenis = person.person_type

    if "sku_id" in data:
        sku = db.get(SkuMaster, data["sku_id"])
        if not sku:
            raise HTTPException(400, "SKU tidak ditemukan")

    for k, v in data.items():
        setattr(entry, k, v)

    db.commit()
    db.refresh(entry)
    return _enrich(DistribusiOut.model_validate(entry), db)


@router.delete("/{entry_id}")
def delete_distribusi(
    entry_id: int,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    entry = db.get(DistribusiCutting, entry_id)
    if not entry or entry.is_deleted:
        raise HTTPException(404, "Data tidak ditemukan")
    entry.is_deleted = 1
    db.commit()
    return {"message": "Data distribusi dihapus"}
