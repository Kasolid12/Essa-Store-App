from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, Float, Integer, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base

class SalaryRun(Base):
    __tablename__ = "salary_runs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tipe: Mapped[str] = mapped_column(String, nullable=False) # 'BORONGAN_PENJAHIT', 'PENGSUP', 'PASUKAN_KARYAWAN'
    person_id: Mapped[Optional[int]] = mapped_column(ForeignKey("persons.id"), index=True) # Null for batch runs
    
    periode_mulai: Mapped[Optional[str]] = mapped_column(String)
    periode_akhir: Mapped[Optional[str]] = mapped_column(String)
    tanggal_proses: Mapped[str] = mapped_column(String, nullable=False)
    
    gaji_kotor: Mapped[float] = mapped_column(Float, default=0.0)
    bon_lama: Mapped[float] = mapped_column(Float, default=0.0)
    tambah_bon: Mapped[float] = mapped_column(Float, default=0.0)
    potong_bon: Mapped[float] = mapped_column(Float, default=0.0)
    gaji_bersih: Mapped[float] = mapped_column(Float, default=0.0)
    sisa_bon_akhir: Mapped[float] = mapped_column(Float, default=0.0)
    
    pdf_path: Mapped[Optional[str]] = mapped_column(String)
    excel_path: Mapped[Optional[str]] = mapped_column(String)
    catatan: Mapped[Optional[str]] = mapped_column(String)
    
    is_deleted: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    person = relationship("Person")
    line_items: Mapped[List["SalaryLineItem"]] = relationship("SalaryLineItem", back_populates="salary_run")
    pengsup_items: Mapped[List["PengsupReconciliation"]] = relationship("PengsupReconciliation", back_populates="salary_run")

class SalaryLineItem(Base):
    __tablename__ = "salary_line_items"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    salary_run_id: Mapped[int] = mapped_column(ForeignKey("salary_runs.id"), nullable=False)
    sku_id: Mapped[Optional[int]] = mapped_column(ForeignKey("sku_master.id"), nullable=True)
    
    # Link ke Master Tarif Penjahit
    tarif_id: Mapped[Optional[int]] = mapped_column(ForeignKey("master_tarif_penjahit.id"), nullable=True) 
    
    model_code: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    qty: Mapped[int] = mapped_column(Integer, default=1)
    tarif_per_pcs: Mapped[float] = mapped_column(Float, nullable=False)
    subtotal: Mapped[float] = mapped_column(Float, nullable=False)

    # --- THE FIX: Missing Relationships ---
    # This connects the line item back to its parent SalaryRun
    salary_run = relationship("SalaryRun", back_populates="line_items")

class PengsupReconciliation(Base):
    __tablename__ = "pengsup_reconciliation"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    salary_run_id: Mapped[int] = mapped_column(ForeignKey("salary_runs.id"), nullable=False)
    tipe: Mapped[str] = mapped_column(String, nullable=False) # 'PEMASUKAN_KAIN', 'POTONGAN_PCS'
    
    sku_id: Mapped[Optional[int]] = mapped_column(ForeignKey("sku_master.id"))
    qty: Mapped[float] = mapped_column(Float, nullable=False)
    harga_per_unit: Mapped[float] = mapped_column(Float, nullable=False)
    subtotal: Mapped[float] = mapped_column(Float, nullable=False)

    salary_run = relationship("SalaryRun", back_populates="pengsup_items")
    sku = relationship("SkuMaster")

class AttendanceRecord(Base):
    __tablename__ = "attendance_records"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    salary_run_id: Mapped[int] = mapped_column(ForeignKey("salary_runs.id"), nullable=False, index=True)
    person_id: Mapped[int] = mapped_column(ForeignKey("persons.id"), nullable=False, index=True)
    tanggal: Mapped[str] = mapped_column(String, nullable=False)
    
    tap_masuk: Mapped[Optional[str]] = mapped_column(String)
    tap_keluar: Mapped[Optional[str]] = mapped_column(String)
    total_menit: Mapped[int] = mapped_column(Integer, default=0)
    menit_normal: Mapped[int] = mapped_column(Integer, default=0)
    menit_lembur: Mapped[int] = mapped_column(Integer, default=0)
    
    tarif_normal: Mapped[float] = mapped_column(Float, default=140.0)
    tarif_lembur: Mapped[float] = mapped_column(Float, default=160.0)
    pendapatan: Mapped[float] = mapped_column(Float, default=0.0)
    
    status: Mapped[Optional[str]] = mapped_column(String) # 'NORMAL', 'LUPA_TAP', 'LIBUR', 'SAKIT'
    catatan: Mapped[Optional[str]] = mapped_column(String)

    person = relationship("Person")
    
class MasterTarifPenjahit(Base):
    __tablename__ = "master_tarif_penjahit"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    kode_garapan: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    harga: Mapped[float] = mapped_column(Float, nullable=False)
    is_active: Mapped[int] = mapped_column(Integer, default=1)