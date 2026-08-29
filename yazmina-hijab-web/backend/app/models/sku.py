"""
Yazmina Hijab Web — SKU Master Model.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import String, Float, Integer, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class SkuMaster(Base):
    __tablename__ = "sku_master"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    kode_sku: Mapped[str] = mapped_column(String, unique=True, index=True)
    nama_produk: Mapped[str] = mapped_column(String)

    # Parent SKU for variants (self-referential)
    parent_sku_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("sku_master.id"), index=True, nullable=True
    )

    # Attributes
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

    # Status
    is_active: Mapped[int] = mapped_column(Integer, default=1)

    # Audit
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now
    )

    def __repr__(self) -> str:
        return f"<SkuMaster(kode='{self.kode_sku}', nama='{self.nama_produk}')>"
