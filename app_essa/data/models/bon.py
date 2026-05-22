from datetime import datetime
from typing import Optional
from sqlalchemy import String, Float, Integer, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base

class BonBalance(Base):
    __tablename__ = "bon_balances"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    person_id: Mapped[int] = mapped_column(ForeignKey("persons.id"), nullable=False, unique=True)
    saldo: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)

    person = relationship("Person")

class BonMovement(Base):
    __tablename__ = "bon_movements"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    person_id: Mapped[int] = mapped_column(ForeignKey("persons.id"), nullable=False, index=True)
    tanggal: Mapped[str] = mapped_column(String, nullable=False)
    
    tipe: Mapped[str] = mapped_column(String, nullable=False) # 'TAMBAH' or 'POTONG'
    nominal: Mapped[float] = mapped_column(Float, nullable=False)
    sumber: Mapped[str] = mapped_column(String, nullable=False) # 'GAJI_BORONGAN', 'MANUAL', 'PELUNASAN_HUTANG'
    sumber_ref_id: Mapped[Optional[int]] = mapped_column(Integer)
    catatan: Mapped[Optional[str]] = mapped_column(String)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    person = relationship("Person")