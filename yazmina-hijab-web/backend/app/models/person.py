"""
Yazmina Hijab Web — Person Model.

Person types: SUPPLIER, SUPPLIER_KAIN, KLIEN, KARYAWAN, PENJAHIT, LAINNYA
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import String, Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


# Person type constants
PERSON_TYPES = [
    "SUPPLIER",
    "SUPPLIER_KAIN",
    "KLIEN",
    "KARYAWAN",
    "PENJAHIT",
    "LAINNYA",
]

PERSON_TYPE_LABELS = {
    "SUPPLIER": "Supplier",
    "SUPPLIER_KAIN": "Supplier Kain",
    "KLIEN": "Klien",
    "KARYAWAN": "Karyawan",
    "PENJAHIT": "Penjahit",
    "LAINNYA": "Lainnya",
}


class Person(Base):
    __tablename__ = "persons"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    nama: Mapped[str] = mapped_column(String, nullable=False)
    person_type: Mapped[str] = mapped_column(String, nullable=False, index=True)

    no_hp: Mapped[Optional[str]] = mapped_column(String)
    alamat: Mapped[Optional[str]] = mapped_column(String)
    catatan: Mapped[Optional[str]] = mapped_column(String)

    # Status
    is_active: Mapped[int] = mapped_column(Integer, default=1)

    # Audit
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now
    )

    def __repr__(self) -> str:
        return f"<Person(nama='{self.nama}', type='{self.person_type}')>"
