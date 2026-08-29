"""Client CRUD API."""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from ..auth import get_current_admin
from ..models.invoice import Client

router = APIRouter(prefix="/api/clients", tags=["clients"])


# ── Schemas ────────────────────────────────────────────────────────

class ClientIn(BaseModel):
    nama: str
    alamat: Optional[str] = None
    no_hp: Optional[str] = None
    catatan: Optional[str] = None

class ClientOut(BaseModel):
    id: int
    nama: str
    alamat: Optional[str] = None
    no_hp: Optional[str] = None
    catatan: Optional[str] = None
    is_active: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ── Endpoints ──────────────────────────────────────────────────────

@router.get("", response_model=list[ClientOut])
def list_clients(
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    q = db.query(Client).filter(Client.is_deleted == 0)
    if search:
        q = q.filter(Client.nama.ilike(f"%{search}%"))
    return q.order_by(Client.nama).all()


@router.post("", response_model=ClientOut, status_code=201)
def create_client(
    body: ClientIn,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    c = Client(**body.model_dump())
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


@router.put("/{client_id}", response_model=ClientOut)
def update_client(
    client_id: int,
    body: ClientIn,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    c = db.query(Client).filter(Client.id == client_id, Client.is_deleted == 0).first()
    if not c:
        raise HTTPException(404, "Client not found")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(c, k, v)
    db.commit()
    db.refresh(c)
    return c


@router.delete("/{client_id}")
def delete_client(
    client_id: int,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    c = db.query(Client).filter(Client.id == client_id, Client.is_deleted == 0).first()
    if not c:
        raise HTTPException(404, "Client not found")
    c.is_deleted = 1
    db.commit()
    return {"ok": True}
