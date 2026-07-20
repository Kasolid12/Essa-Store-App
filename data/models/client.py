from datetime import datetime
from typing import Optional
from sqlalchemy import String, Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base

class Client(Base):
    __tablename__ = "clients"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    nama: Mapped[str] = mapped_column(String, nullable=False)
    alamat: Mapped[Optional[str]] = mapped_column(String)
    no_hp: Mapped[Optional[str]] = mapped_column(String)
    catatan: Mapped[Optional[str]] = mapped_column(String)

    is_active: Mapped[int] = mapped_column(Integer, default=1)
    is_deleted: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)

    def __repr__(self) -> str:
        return f"<Client(nama='{self.nama}', id={self.id})>"
