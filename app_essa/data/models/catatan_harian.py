from datetime import datetime
from typing import Optional
from sqlalchemy import String, Float, Integer, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base

class HasilCutting(Base):
    __tablename__ = "hasil_cutting"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tanggal: Mapped[str] = mapped_column(String, nullable=False) # Storing as YYYY-MM-DD string is fine for SQLite
    sku_id: Mapped[int] = mapped_column(ForeignKey("sku_master.id"), nullable=False)
    qty: Mapped[int] = mapped_column(Integer, nullable=False)
    catatan: Mapped[Optional[str]] = mapped_column(String)
    created_by: Mapped[Optional[str]] = mapped_column(String)
    
    is_deleted: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    sku = relationship("SkuMaster")

class DistribusiCutting(Base):
    __tablename__ = "distribusi_cutting"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tanggal: Mapped[str] = mapped_column(String, nullable=False)
    person_id: Mapped[int] = mapped_column(ForeignKey("persons.id"), nullable=False, index=True)
    jenis: Mapped[str] = mapped_column(String, nullable=False) # 'PENJAHIT' or 'PENGSUP'
    sku_id: Mapped[int] = mapped_column(ForeignKey("sku_master.id"), nullable=False)
    qty: Mapped[int] = mapped_column(Integer, nullable=False)
    catatan: Mapped[Optional[str]] = mapped_column(String)
    
    is_deleted: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    person = relationship("Person")
    sku = relationship("SkuMaster")

class ModalOperasional(Base):
    __tablename__ = "modal_operasional"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tanggal: Mapped[str] = mapped_column(String, nullable=False)
    jenis: Mapped[str] = mapped_column(String, nullable=False) # 'BARANG', 'OVERHEAD', 'UTILITAS'
    keterangan: Mapped[str] = mapped_column(String, nullable=False)
    nominal: Mapped[float] = mapped_column(Float, nullable=False)
    catatan: Mapped[Optional[str]] = mapped_column(String)
    
    is_deleted: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

class PengeluaranOffline(Base):
    __tablename__ = "pengeluaran_offline"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tanggal: Mapped[str] = mapped_column(String, nullable=False)
    sku_id: Mapped[int] = mapped_column(ForeignKey("sku_master.id"), nullable=False)
    qty: Mapped[int] = mapped_column(Integer, nullable=False)
    harga_satuan: Mapped[float] = mapped_column(Float, nullable=False) # Snapshot from sku_master.harga_jual
    total: Mapped[float] = mapped_column(Float, nullable=False)
    person_id: Mapped[Optional[int]] = mapped_column(ForeignKey("persons.id")) # Pembeli/Klien
    catatan: Mapped[Optional[str]] = mapped_column(String)
    
    is_deleted: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    sku = relationship("SkuMaster")
    person = relationship("Person")