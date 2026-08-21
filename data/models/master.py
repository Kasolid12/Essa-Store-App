from datetime import datetime, date
from typing import Optional
from sqlalchemy import String, Float, Integer, ForeignKey, DateTime, Date, Column
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
    # NOTE (Fase 6): updated_at dibuat NULLABLE (Optional) — cloud masih berisi NULL di
    # tabel yang baru punya kolom ini; pull setup perangkat baru bergantung pada nullability ini.
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)
    # NOTE (Fase 6.3): kepemilikan baris antar perangkat (diisi otomatis via event di base.py; NULL = baris lama)
    created_by_device: Mapped[Optional[str]] = mapped_column(String)
    updated_by_device: Mapped[Optional[str]] = mapped_column(String)

    sku = relationship("SkuMaster")
    
class TarifMaster(Base):
    __tablename__ = "tarif_master"
    
    id = Column(Integer, primary_key=True, index=True)
    kode_sku = Column(String, index=True, unique=True, nullable=False)
    tarif_jahit = Column(Float, default=0.0)
    tarif_pengsup_kain = Column(Float, default=0.0)
    tarif_pengsup_potongan = Column(Float, default=0.0)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    created_by_device = Column(String)
    updated_by_device = Column(String)

class AppSetting(Base):
    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String, primary_key=True)
    value: Mapped[Optional[str]] = mapped_column(String)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)
    created_by_device: Mapped[Optional[str]] = mapped_column(String)
    updated_by_device: Mapped[Optional[str]] = mapped_column(String)