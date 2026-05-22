from datetime import datetime
from typing import Optional
from sqlalchemy import String, Integer, DateTime, text, Computed
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base # Assuming Base is defined in base.py

class Person(Base):
    __tablename__ = "persons"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    nama: Mapped[str] = mapped_column(String, nullable=False)
    
    # 'KARYAWAN', 'PENJAHIT', 'PENGSUP', 'KLIEN', 'SUPPLIER', 'LAINNYA'
    person_type: Mapped[str] = mapped_column(String, nullable=False, index=True) 
    
    # Using SQLite's GENERATED ALWAYS for the uppercase column to help with legacy JSON mapping
    nama_uppercase: Mapped[Optional[str]] = mapped_column(
        String, 
        Computed("UPPER(nama)"), 
        index=True
    )
    
    no_hp: Mapped[Optional[str]] = mapped_column(String)
    alamat: Mapped[Optional[str]] = mapped_column(String)
    catatan: Mapped[Optional[str]] = mapped_column(String)
    
    is_active: Mapped[int] = mapped_column(Integer, default=1)
    is_deleted: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)

    def __repr__(self) -> str:
        return f"<Person(nama='{self.nama}', type='{self.person_type}')>"