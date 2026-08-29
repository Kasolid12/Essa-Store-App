"""
Yazmina Hijab Web — Bon (Advance) CRUD API.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from ..auth import get_current_admin
from ..models.payroll import BonBalance, BonMovement
from ..models.person import Person

router = APIRouter(prefix="/api/bon", tags=["bon"])


# ── Schemas ───────────────────────────────────────────────────────────

class BonMovementCreate(BaseModel):
    person_id: int
    tanggal: str
    tipe: str  # TAMBAH or POTONG
    nominal: float
    sumber: str = "MANUAL"
    catatan: Optional[str] = None


# ── Helpers ───────────────────────────────────────────────────────────

def _get_or_create_balance(person_id: int, db: Session) -> BonBalance:
    balance = db.query(BonBalance).filter(BonBalance.person_id == person_id).first()
    if not balance:
        balance = BonBalance(person_id=person_id, saldo=0.0)
        db.add(balance)
        db.flush()
    return balance


# ── Routes ────────────────────────────────────────────────────────────

@router.get("/balances")
def list_balances(
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    balances = db.query(BonBalance).all()
    result = []
    for b in balances:
        person = db.get(Person, b.person_id)
        result.append({
            "id": b.id,
            "person_id": b.person_id,
            "person_nama": person.nama if person else None,
            "saldo": b.saldo,
        })
    return result


@router.get("/movements")
def list_movements(
    person_id: Optional[int] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    q = db.query(BonMovement)

    if person_id:
        q = q.filter(BonMovement.person_id == person_id)
    if date_from:
        q = q.filter(BonMovement.tanggal >= date_from)
    if date_to:
        q = q.filter(BonMovement.tanggal <= date_to)

    items = q.order_by(BonMovement.tanggal.desc(), BonMovement.id.desc()).limit(200).all()

    result = []
    for item in items:
        person = db.get(Person, item.person_id)
        result.append({
            "id": item.id,
            "person_id": item.person_id,
            "person_nama": person.nama if person else None,
            "tanggal": item.tanggal,
            "tipe": item.tipe,
            "nominal": item.nominal,
            "sumber": item.sumber,
            "catatan": item.catatan,
        })
    return result


@router.post("/move")
def create_movement(
    body: BonMovementCreate,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    """Record a bon movement (TAMBAH or POTONG)."""
    person = db.get(Person, body.person_id)
    if not person:
        raise HTTPException(400, "Person tidak ditemukan")

    if body.tipe not in ("TAMBAH", "POTONG"):
        raise HTTPException(400, f"Tipe '{body.tipe}' tidak valid (harus TAMBAH atau POTONG)")

    if body.nominal <= 0:
        raise HTTPException(400, "Nominal harus lebih dari 0")

    movement = BonMovement(
        person_id=body.person_id,
        tanggal=body.tanggal,
        tipe=body.tipe,
        nominal=body.nominal,
        sumber=body.sumber,
        catatan=body.catatan,
    )
    db.add(movement)

    balance = _get_or_create_balance(body.person_id, db)
    if body.tipe == "TAMBAH":
        balance.saldo += body.nominal
    else:
        balance.saldo -= body.nominal

    db.commit()
    return {
        "message": f"Bon {'ditambah' if body.tipe == 'TAMBAH' else 'dipotong'}: Rp {body.nominal:,.0f}",
        "saldo_baru": balance.saldo,
    }
