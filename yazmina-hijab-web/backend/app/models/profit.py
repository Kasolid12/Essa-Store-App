"""
Yazmina Hijab Web — Profit & Tarif Models.

- ProfitHistory: saved profit calculations per batch
- TarifMaster: sewing/cutting tariffs per SKU
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Float, Integer, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base


class TarifMaster(Base):
    __tablename__ = "tarif_master"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    kode_sku: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    tarif_jahit: Mapped[float] = mapped_column(Float, default=0.0)
    tarif_pengsup_kain: Mapped[float] = mapped_column(Float, default=0.0)
    tarif_pengsup_potongan: Mapped[float] = mapped_column(Float, default=0.0)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now
    )

    def __repr__(self) -> str:
        return f"<TarifMaster(sku='{self.kode_sku}', jahit={self.tarif_jahit})>"


class ProfitHistory(Base):
    __tablename__ = "profit_history"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tanggal_hitung: Mapped[str] = mapped_column(String, nullable=False, index=True)

    debt_entry_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("debt_entries.id"), nullable=True, index=True
    )

    total_pendapatan: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    total_modal_kain: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    total_modal_jahit: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    total_profit: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    periode_mulai: Mapped[str] = mapped_column(String, nullable=False)
    periode_akhir: Mapped[str] = mapped_column(String, nullable=False)

    catatan: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now
    )

    debt_entry = relationship("DebtEntry")

    def __repr__(self) -> str:
        return f"<ProfitHistory(batch='{self.catatan}', profit={self.total_profit})>"
