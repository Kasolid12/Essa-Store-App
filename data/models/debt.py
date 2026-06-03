from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, Float, Integer, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy import String, Integer, Float, ForeignKey

class DebtEntry(Base):
    __tablename__ = "debt_entries"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tipe_hutang: Mapped[str] = mapped_column(String, nullable=False, index=True) # 'BARANG' or 'MODAL'
    tanggal: Mapped[str] = mapped_column(String, nullable=False)
    kode_produksi: Mapped[Optional[str]] = mapped_column(String, index=True)
    status_cutting: Mapped[Optional[str]] = mapped_column(String, default="OPEN")
    
    person_id: Mapped[int] = mapped_column(ForeignKey("persons.id"), nullable=False, index=True)
    keterangan: Mapped[str] = mapped_column(String, nullable=False)
    
    # Only applicable for 'BARANG'
    sku_id: Mapped[Optional[int]] = mapped_column(ForeignKey("sku_master.id"))
    qty: Mapped[Optional[float]] = mapped_column(Float)
    
    nominal_hutang: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String, default="OPEN", index=True) # 'OPEN', 'PARTIAL', 'LUNAS'
    catatan: Mapped[Optional[str]] = mapped_column(String)
    
    is_deleted: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    person = relationship("Person")
    sku = relationship("SkuMaster")
    payments: Mapped[List["DebtPayment"]] = relationship("DebtPayment", back_populates="debt_entry")
    
    # Tracking status untuk profit dashboard
    status_cutting: Mapped[str] = mapped_column(String, default="OPEN") 
    
    # Relasi ke tabel hasil cutting
    hasil_cuttings = relationship("HasilCutting", back_populates="sumber_modal")

class DebtPayment(Base):
    __tablename__ = "debt_payments"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    debt_entry_id: Mapped[int] = mapped_column(ForeignKey("debt_entries.id"), nullable=False, index=True)
    tanggal_bayar: Mapped[str] = mapped_column(String, nullable=False)
    
    nominal_bayar: Mapped[float] = mapped_column(Float, nullable=False)
    metode: Mapped[Optional[str]] = mapped_column(String) # 'CASH', 'TRANSFER', 'POTONG_BON'
    bon_used: Mapped[float] = mapped_column(Float, default=0.0)
    nota_pdf_path: Mapped[Optional[str]] = mapped_column(String)
    catatan: Mapped[Optional[str]] = mapped_column(String)
    
    is_deleted: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    debt_entry = relationship("DebtEntry", back_populates="payments")