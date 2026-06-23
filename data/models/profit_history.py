from datetime import datetime
from typing import Optional
from sqlalchemy import String, Float, Integer, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base


class ProfitHistory(Base):
    __tablename__ = "profit_history"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tanggal_hitung: Mapped[str] = mapped_column(String, nullable=False, index=True)

    # Referensi opsional ke modal kain (debt_entries) yang dihitung profitnya
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

    debt_entry = relationship("DebtEntry")
