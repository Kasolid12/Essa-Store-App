"""
Yazmina Hijab Web — Modal Operasional CRUD API.

Types: BARANG, OVERHEAD, UTILITAS, LAINNYA
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..database import get_db
from ..auth import get_current_admin
from ..models.daily_notes import ModalOperasional

router = APIRouter(prefix="/api/modal-operasional", tags=["modal-operasional"])

JENIS_OPTIONS = ["BARANG", "OVERHEAD", "UTILITAS", "LAINNYA"]


# ── Schemas ───────────────────────────────────────────────────────────

class ModalOpCreate(BaseModel):
    tanggal: str
    jenis: str
    keterangan: str
    nominal: float
    catatan: Optional[str] = None


class ModalOpUpdate(BaseModel):
    tanggal: Optional[str] = None
    jenis: Optional[str] = None
    keterangan: Optional[str] = None
    nominal: Optional[float] = None
    catatan: Optional[str] = None


class ModalOpOut(BaseModel):
    id: int
    tanggal: str
    jenis: str
    keterangan: str
    nominal: float
    catatan: Optional[str] = None
    is_deleted: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ── Routes ────────────────────────────────────────────────────────────

@router.get("/jenis")
def list_jenis():
    return JENIS_OPTIONS


@router.get("")
def list_modal_operasional(
    search: Optional[str] = Query(None),
    jenis: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    q = db.query(ModalOperasional).filter(ModalOperasional.is_deleted == 0)

    if search:
        like = f"%{search}%"
        q = q.filter(
            ModalOperasional.keterangan.ilike(like)
            | ModalOperasional.jenis.ilike(like)
        )

    if jenis:
        q = q.filter(ModalOperasional.jenis == jenis)

    if date_from:
        q = q.filter(ModalOperasional.tanggal >= date_from)

    if date_to:
        q = q.filter(ModalOperasional.tanggal <= date_to)

    items = q.order_by(ModalOperasional.tanggal.desc(), ModalOperasional.id.desc()).limit(200).all()
    return [ModalOpOut.model_validate(m).model_dump() for m in items]


@router.get("/summary")
def summary(
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    """Summary: total pengeluaran per jenis."""
    q = db.query(
        ModalOperasional.jenis,
        func.coalesce(func.sum(ModalOperasional.nominal), 0.0),
    ).filter(ModalOperasional.is_deleted == 0)

    if date_from:
        q = q.filter(ModalOperasional.tanggal >= date_from)
    if date_to:
        q = q.filter(ModalOperasional.tanggal <= date_to)

    rows = q.group_by(ModalOperasional.jenis).all()
    result = {r[0]: r[1] for r in rows}
    result["total"] = sum(result.values())
    return result


@router.post("")
def create_modal_operasional(
    body: ModalOpCreate,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    if body.jenis not in JENIS_OPTIONS:
        raise HTTPException(400, f"Jenis '{body.jenis}' tidak valid")

    entry = ModalOperasional(**body.model_dump())
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return ModalOpOut.model_validate(entry).model_dump()


@router.put("/{entry_id}")
def update_modal_operasional(
    entry_id: int,
    body: ModalOpUpdate,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    entry = db.get(ModalOperasional, entry_id)
    if not entry or entry.is_deleted:
        raise HTTPException(404, "Data tidak ditemukan")

    data = body.model_dump(exclude_unset=True)
    if "jenis" in data and data["jenis"] not in JENIS_OPTIONS:
        raise HTTPException(400, f"Jenis '{data['jenis']}' tidak valid")

    for k, v in data.items():
        setattr(entry, k, v)

    db.commit()
    db.refresh(entry)
    return ModalOpOut.model_validate(entry).model_dump()


@router.delete("/{entry_id}")
def delete_modal_operasional(
    entry_id: int,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    entry = db.get(ModalOperasional, entry_id)
    if not entry or entry.is_deleted:
        raise HTTPException(404, "Data tidak ditemukan")
    entry.is_deleted = 1
    db.commit()
    return {"message": "Data pengeluaran dihapus"}
