"""
Yazmina Hijab Web — Person CRUD API.

Person types: SUPPLIER, SUPPLIER_KAIN, KLIEN, KARYAWAN, PENJAHIT, LAINNYA
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..database import get_db
from ..auth import get_current_admin
from ..models.person import Person, PERSON_TYPES, PERSON_TYPE_LABELS

router = APIRouter(prefix="/api/persons", tags=["persons"])


# ── Schemas ───────────────────────────────────────────────────────────

class PersonCreate(BaseModel):
    nama: str
    person_type: str
    no_hp: Optional[str] = None
    alamat: Optional[str] = None
    catatan: Optional[str] = None


class PersonUpdate(BaseModel):
    nama: Optional[str] = None
    person_type: Optional[str] = None
    no_hp: Optional[str] = None
    alamat: Optional[str] = None
    catatan: Optional[str] = None
    is_active: Optional[int] = None


class PersonOut(BaseModel):
    id: int
    nama: str
    person_type: str
    no_hp: Optional[str] = None
    alamat: Optional[str] = None
    catatan: Optional[str] = None
    is_active: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ── Routes ────────────────────────────────────────────────────────────

@router.get("/types")
def list_person_types():
    """Get available person types with labels."""
    return [{"value": t, "label": PERSON_TYPE_LABELS[t]} for t in PERSON_TYPES]


@router.get("")
def list_persons(
    search: Optional[str] = Query(None),
    person_type: Optional[str] = Query(None),
    active_only: bool = Query(True),
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    """List all persons with optional search & filter."""
    q = db.query(Person)

    if active_only:
        q = q.filter(Person.is_active == 1)

    if search:
        like = f"%{search}%"
        q = q.filter(
            or_(
                Person.nama.ilike(like),
                Person.no_hp.ilike(like),
                Person.alamat.ilike(like),
            )
        )

    if person_type:
        q = q.filter(Person.person_type == person_type)

    items = q.order_by(Person.nama).all()
    return [PersonOut.model_validate(p).model_dump() for p in items]


@router.post("")
def create_person(
    body: PersonCreate,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    """Create a new person."""
    if body.person_type not in PERSON_TYPES:
        raise HTTPException(400, f"Tipe '{body.person_type}' tidak valid")

    person = Person(**body.model_dump())
    db.add(person)
    db.commit()
    db.refresh(person)
    return PersonOut.model_validate(person).model_dump()


@router.get("/{person_id}")
def get_person(
    person_id: int,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    """Get single person by ID."""
    person = db.get(Person, person_id)
    if not person:
        raise HTTPException(404, "Person tidak ditemukan")
    return PersonOut.model_validate(person).model_dump()


@router.put("/{person_id}")
def update_person(
    person_id: int,
    body: PersonUpdate,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    """Update an existing person."""
    person = db.get(Person, person_id)
    if not person:
        raise HTTPException(404, "Person tidak ditemukan")

    data = body.model_dump(exclude_unset=True)

    if "person_type" in data and data["person_type"] not in PERSON_TYPES:
        raise HTTPException(400, f"Tipe '{data['person_type']}' tidak valid")

    for k, v in data.items():
        setattr(person, k, v)

    db.commit()
    db.refresh(person)
    return PersonOut.model_validate(person).model_dump()


@router.delete("/{person_id}")
def delete_person(
    person_id: int,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    """Soft-delete a person (set is_active=0)."""
    person = db.get(Person, person_id)
    if not person:
        raise HTTPException(404, "Person tidak ditemukan")
    person.is_active = 0
    db.commit()
    return {"message": f"'{person.nama}' dihapus"}
