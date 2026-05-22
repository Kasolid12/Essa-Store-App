from datetime import datetime, date
from typing import Optional
from sqlalchemy import String, Float, Integer, ForeignKey, DateTime, Date
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base

class GarapanRate(Base):
    __tablename__ = "garapan_rates"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    sku_id: Mapped[Optional[int]] = mapped_column(ForeignKey("sku_master.id"))
    model_code: Mapped[Optional[str]] = mapped_column(String, index=True) # e.g. "JSO", "DG"
    
    tarif_per_pcs: Mapped[float] = mapped_column(Float, nullable=False)
    berlaku_sejak: Mapped[date] = mapped_column(Date, default=date.today)
    is_active: Mapped[int] = mapped_column(Integer, default=1)
    catatan: Mapped[Optional[str]] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    sku = relationship("SkuMaster")

class AppSetting(Base):
    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String, primary_key=True)
    value: Mapped[Optional[str]] = mapped_column(String)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)