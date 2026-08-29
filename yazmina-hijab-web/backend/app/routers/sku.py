"""
Yazmina Hijab Web — SKU CRUD API.
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..database import get_db
from ..auth import get_current_admin
from ..models.sku import SkuMaster

router = APIRouter(prefix="/api/sku", tags=["sku"])


# ── Schemas ───────────────────────────────────────────────────────────

class SkuCreate(BaseModel):
    kode_sku: str
    nama_produk: str
    parent_sku_id: Optional[int] = None
    kategori: Optional[str] = None
    model: Optional[str] = None
    warna: Optional[str] = None
    ukuran: Optional[str] = None
    gtin: Optional[str] = None
    harga_jual: float = 0.0
    harga_modal: float = 0.0
    kain_cost: float = 0.0
    potongan_cost: float = 0.0


class SkuUpdate(BaseModel):
    kode_sku: Optional[str] = None
    nama_produk: Optional[str] = None
    parent_sku_id: Optional[int] = None
    kategori: Optional[str] = None
    model: Optional[str] = None
    warna: Optional[str] = None
    ukuran: Optional[str] = None
    gtin: Optional[str] = None
    harga_jual: Optional[float] = None
    harga_modal: Optional[float] = None
    kain_cost: Optional[float] = None
    potongan_cost: Optional[float] = None
    is_active: Optional[int] = None


class SkuOut(BaseModel):
    id: int
    kode_sku: str
    nama_produk: str
    parent_sku_id: Optional[int] = None
    kategori: Optional[str] = None
    model: Optional[str] = None
    warna: Optional[str] = None
    ukuran: Optional[str] = None
    gtin: Optional[str] = None
    harga_jual: float
    harga_modal: float
    kain_cost: float
    potongan_cost: float
    is_active: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ── Routes ────────────────────────────────────────────────────────────

@router.get("")
def list_sku(
    search: Optional[str] = Query(None),
    kategori: Optional[str] = Query(None),
    active_only: bool = Query(True),
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    """List all SKUs with optional search & filter."""
    q = db.query(SkuMaster)

    if active_only:
        q = q.filter(SkuMaster.is_active == 1)

    if search:
        like = f"%{search}%"
        q = q.filter(
            or_(
                SkuMaster.kode_sku.ilike(like),
                SkuMaster.nama_produk.ilike(like),
                SkuMaster.model.ilike(like),
                SkuMaster.warna.ilike(like),
            )
        )

    if kategori:
        q = q.filter(SkuMaster.kategori == kategori)

    items = q.order_by(SkuMaster.kode_sku).all()
    return [SkuOut.model_validate(s).model_dump() for s in items]


@router.post("")
def create_sku(
    body: SkuCreate,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    """Create a new SKU."""
    # Check duplicate kode_sku
    existing = db.query(SkuMaster).filter(SkuMaster.kode_sku == body.kode_sku).first()
    if existing:
        raise HTTPException(400, f"SKU '{body.kode_sku}' sudah ada")

    sku = SkuMaster(**body.model_dump())
    db.add(sku)
    db.commit()
    db.refresh(sku)
    return SkuOut.model_validate(sku).model_dump()


@router.get("/{sku_id}")
def get_sku(
    sku_id: int,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    """Get single SKU by ID."""
    sku = db.get(SkuMaster, sku_id)
    if not sku:
        raise HTTPException(404, "SKU tidak ditemukan")
    return SkuOut.model_validate(sku).model_dump()


@router.put("/{sku_id}")
def update_sku(
    sku_id: int,
    body: SkuUpdate,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    """Update an existing SKU."""
    sku = db.get(SkuMaster, sku_id)
    if not sku:
        raise HTTPException(404, "SKU tidak ditemukan")

    data = body.model_dump(exclude_unset=True)

    # Check duplicate kode_sku if changing
    if "kode_sku" in data and data["kode_sku"] != sku.kode_sku:
        dup = db.query(SkuMaster).filter(SkuMaster.kode_sku == data["kode_sku"]).first()
        if dup:
            raise HTTPException(400, f"SKU '{data['kode_sku']}' sudah ada")

    for k, v in data.items():
        setattr(sku, k, v)

    db.commit()
    db.refresh(sku)
    return SkuOut.model_validate(sku).model_dump()


@router.delete("/{sku_id}")
def delete_sku(
    sku_id: int,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    """Soft-delete a SKU (set is_active=0)."""
    sku = db.get(SkuMaster, sku_id)
    if not sku:
        raise HTTPException(404, "SKU tidak ditemukan")
    sku.is_active = 0
    db.commit()
    return {"message": f"SKU '{sku.kode_sku}' dihapus"}


@router.get("/categories/list")
def list_categories(
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    """Get distinct kategori values for filter dropdown."""
    rows = (
        db.query(SkuMaster.kategori)
        .filter(SkuMaster.kategori.isnot(None), SkuMaster.kategori != "")
        .distinct()
        .order_by(SkuMaster.kategori)
        .all()
    )
    return [r[0] for r in rows]
