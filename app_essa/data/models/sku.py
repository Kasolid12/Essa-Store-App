from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, Float, Integer, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

class SkuMaster(Base):
    __tablename__ = "sku_master"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    kode_sku: Mapped[str] = mapped_column(String, unique=True, index=True)
    nama_produk: Mapped[str] = mapped_column(String)
    
    # Self-referential relationship for Parent/Child SKUs
    parent_sku_id: Mapped[Optional[int]] = mapped_column(ForeignKey("sku_master.id"), index=True)
    parent_sku: Mapped[Optional["SkuMaster"]] = relationship("SkuMaster", remote_side=[id], back_populates="variants")
    variants: Mapped[List["SkuMaster"]] = relationship("SkuMaster", back_populates="parent_sku")

    kategori: Mapped[Optional[str]] = mapped_column(String)
    model: Mapped[Optional[str]] = mapped_column(String, index=True)
    warna: Mapped[Optional[str]] = mapped_column(String)
    ukuran: Mapped[Optional[str]] = mapped_column(String)
    gtin: Mapped[Optional[str]] = mapped_column(String)

    # Pricing & Costing
    harga_jual: Mapped[float] = mapped_column(Float, default=0.0)
    harga_modal: Mapped[float] = mapped_column(Float, default=0.0)
    kain_cost: Mapped[float] = mapped_column(Float, default=0.0)
    potongan_cost: Mapped[float] = mapped_column(Float, default=0.0)

    # Status & Audit
    is_active: Mapped[int] = mapped_column(Integer, default=1)
    is_deleted: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)

    def __repr__(self) -> str:
        return f"<SkuMaster(kode='{self.kode_sku}', nama='{self.nama_produk}')>"