from datetime import datetime
from typing import Optional
from sqlalchemy import String, Float, Integer, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base

class HasilCutting(Base):
    __tablename__ = "hasil_cutting"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tanggal: Mapped[str] = mapped_column(String, nullable=False)
    kode_produksi: Mapped[Optional[str]] = mapped_column(String, index=True)
    sku_id: Mapped[int] = mapped_column(ForeignKey("sku_master.id"), nullable=False)
    qty: Mapped[int] = mapped_column(Integer, nullable=False)
    catatan: Mapped[Optional[str]] = mapped_column(String)
    created_by: Mapped[Optional[str]] = mapped_column(String)
    
    # --- NEW: Link ke roll kain spesifik (Modal Hutang) ---
    modal_hutang_id: Mapped[Optional[int]] = mapped_column(ForeignKey("debt_entries.id"), nullable=True)
    
    is_deleted: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    # --- UPDATED: Relationships ---
    sku = relationship("SkuMaster")
    sumber_modal = relationship("DebtEntry", back_populates="hasil_cuttings")
    distribusi = relationship("DistribusiCutting", back_populates="sumber_cutting")

class DistribusiCutting(Base):
    __tablename__ = "distribusi_cutting"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tanggal: Mapped[str] = mapped_column(String, nullable=False)
    kode_produksi: Mapped[Optional[str]] = mapped_column(String, index=True)
    person_id: Mapped[int] = mapped_column(ForeignKey("persons.id"), nullable=False, index=True)
    jenis: Mapped[str] = mapped_column(String, nullable=False) # 'PENJAHIT' or 'PENGSUP'
    sku_id: Mapped[int] = mapped_column(ForeignKey("sku_master.id"), nullable=False)
    qty: Mapped[int] = mapped_column(Integer, nullable=False)
    catatan: Mapped[Optional[str]] = mapped_column(String)
    
    # --- NEW: Link kembali ke Batch Cutting yang spesifik ---
    hasil_cutting_id: Mapped[Optional[int]] = mapped_column(ForeignKey("hasil_cutting.id"), nullable=True)
    
    is_deleted: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    # --- UPDATED: Relationships ---
    person = relationship("Person")
    sku = relationship("SkuMaster")
    sumber_cutting = relationship("HasilCutting", back_populates="distribusi")

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
    qty: Mapped[float] = mapped_column(Float, nullable=False)
    harga_satuan: Mapped[float] = mapped_column(Float, nullable=False) # Snapshot from sku_master.harga_jual
    total: Mapped[float] = mapped_column(Float, nullable=False)
    person_id: Mapped[Optional[int]] = mapped_column(ForeignKey("persons.id")) # Legacy: Pembeli/Klien (Person)
    client_id: Mapped[Optional[int]] = mapped_column(ForeignKey("clients.id")) # Pembeli/Klien (Client)
    catatan: Mapped[Optional[str]] = mapped_column(String)
    
    is_deleted: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    sku = relationship("SkuMaster")
    person = relationship("Person")
    client = relationship("Client")