"""
Yazmina Hijab Web — Payroll Models.

- SalaryRun: salary processing run
- SalaryLineItem: individual line items in a salary run
- BonBalance: bon (advance) balance per person
- BonMovement: bon transaction history
- AttendanceRecord: daily attendance from fingerprint Excel
- MasterTarifPenjahit: master tariff for penjahit garapan
"""

from datetime import datetime
from typing import Optional, List

from sqlalchemy import String, Float, Integer, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base


class SalaryRun(Base):
    __tablename__ = "salary_runs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tipe: Mapped[str] = mapped_column(String, nullable=False)  # BORONGAN_PENJAHIT, PENGSUP, PASUKAN_KARYAWAN
    person_id: Mapped[Optional[int]] = mapped_column(ForeignKey("persons.id"), index=True)

    periode_mulai: Mapped[Optional[str]] = mapped_column(String)
    periode_akhir: Mapped[Optional[str]] = mapped_column(String)
    tanggal_proses: Mapped[str] = mapped_column(String, nullable=False)

    gaji_kotor: Mapped[float] = mapped_column(Float, default=0.0)
    bon_lama: Mapped[float] = mapped_column(Float, default=0.0)
    tambah_bon: Mapped[float] = mapped_column(Float, default=0.0)
    potong_bon: Mapped[float] = mapped_column(Float, default=0.0)
    gaji_bersih: Mapped[float] = mapped_column(Float, default=0.0)
    sisa_bon_akhir: Mapped[float] = mapped_column(Float, default=0.0)

    catatan: Mapped[Optional[str]] = mapped_column(String)

    is_deleted: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now
    )

    person = relationship("Person")
    line_items: Mapped[List["SalaryLineItem"]] = relationship(
        "SalaryLineItem", back_populates="salary_run"
    )

    def __repr__(self) -> str:
        return f"<SalaryRun(tipe='{self.tipe}', gaji_bersih={self.gaji_bersih})>"


class SalaryLineItem(Base):
    __tablename__ = "salary_line_items"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    salary_run_id: Mapped[int] = mapped_column(ForeignKey("salary_runs.id"), nullable=False)
    sku_id: Mapped[Optional[int]] = mapped_column(ForeignKey("sku_master.id"), nullable=True)

    model_code: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    qty: Mapped[int] = mapped_column(Integer, default=1)
    tarif_per_pcs: Mapped[float] = mapped_column(Float, nullable=False)
    subtotal: Mapped[float] = mapped_column(Float, nullable=False)

    salary_run = relationship("SalaryRun", back_populates="line_items")


class BonBalance(Base):
    __tablename__ = "bon_balances"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    person_id: Mapped[int] = mapped_column(ForeignKey("persons.id"), nullable=False, unique=True)
    saldo: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)

    person = relationship("Person")


class BonMovement(Base):
    __tablename__ = "bon_movements"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    person_id: Mapped[int] = mapped_column(ForeignKey("persons.id"), nullable=False, index=True)
    tanggal: Mapped[str] = mapped_column(String, nullable=False)

    tipe: Mapped[str] = mapped_column(String, nullable=False)  # TAMBAH or POTONG
    nominal: Mapped[float] = mapped_column(Float, nullable=False)
    sumber: Mapped[str] = mapped_column(String, nullable=False)  # MANUAL, PAYROLL_*, PELUNASAN_HUTANG
    catatan: Mapped[Optional[str]] = mapped_column(String)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now
    )

    person = relationship("Person")


class AttendanceRecord(Base):
    """Daily attendance record per karyawan (from fingerprint Excel)."""
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

    status: Mapped[Optional[str]] = mapped_column(String)  # NORMAL, LUPA_TAP, LIBUR, SAKIT
    catatan: Mapped[Optional[str]] = mapped_column(String)
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now
    )

    person = relationship("Person")


class MasterTarifPenjahit(Base):
    __tablename__ = "master_tarif_penjahit"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    kode_garapan: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    harga: Mapped[float] = mapped_column(Float, nullable=False)
    is_active: Mapped[int] = mapped_column(Integer, default=1)
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now
    )
