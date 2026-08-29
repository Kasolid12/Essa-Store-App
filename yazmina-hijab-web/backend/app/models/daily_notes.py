"""
Yazmina Hijab Web — Daily Notes Models.

- HasilCutting: cutting results (production)
- DistribusiCutting: distribution to penjahit/pengsup
- ModalOperasional: operational expenses (BARANG, OVERHEAD, UTILITAS)
- PengeluaranOffline: offline sales
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import String, Float, Integer, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base


class HasilCutting(Base):
    __tablename__ = "hasil_cutting"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tanggal: Mapped[str] = mapped_column(String, nullable=False, index=True)
    kode_produksi: Mapped[Optional[str]] = mapped_column(String, index=True)
    sku_id: Mapped[int] = mapped_column(ForeignKey("sku_master.id"), nullable=False)
    qty: Mapped[int] = mapped_column(Integer, nullable=False)
    catatan: Mapped[Optional[str]] = mapped_column(String)

    is_deleted: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now
    )

    sku = relationship("SkuMaster")

    def __repr__(self) -> str:
        return f"<HasilCutting(tanggal='{self.tanggal}', sku_id={self.sku_id}, qty={self.qty})>"


class DistribusiCutting(Base):
    __tablename__ = "distribusi_cutting"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tanggal: Mapped[str] = mapped_column(String, nullable=False, index=True)
    kode_produksi: Mapped[Optional[str]] = mapped_column(String, index=True)
    person_id: Mapped[int] = mapped_column(ForeignKey("persons.id"), nullable=False, index=True)
    jenis: Mapped[str] = mapped_column(String, nullable=False)  # PENJAHIT or PENGSUP
    sku_id: Mapped[int] = mapped_column(ForeignKey("sku_master.id"), nullable=False)
    qty: Mapped[int] = mapped_column(Integer, nullable=False)
    catatan: Mapped[Optional[str]] = mapped_column(String)
    hasil_cutting_id: Mapped[Optional[int]] = mapped_column(ForeignKey("hasil_cutting.id"), nullable=True)

    is_deleted: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now
    )

    person = relationship("Person")
    sku = relationship("SkuMaster")

    def __repr__(self) -> str:
        return f"<DistribusiCutting(tanggal='{self.tanggal}', person_id={self.person_id}, qty={self.qty})>"


class ModalOperasional(Base):
    __tablename__ = "modal_operasional"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tanggal: Mapped[str] = mapped_column(String, nullable=False, index=True)
    jenis: Mapped[str] = mapped_column(String, nullable=False)  # BARANG, OVERHEAD, UTILITAS, LAINNYA
    keterangan: Mapped[str] = mapped_column(String, nullable=False)
    nominal: Mapped[float] = mapped_column(Float, nullable=False)
    catatan: Mapped[Optional[str]] = mapped_column(String)

    is_deleted: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now
    )

    def __repr__(self) -> str:
        return f"<ModalOperasional(tanggal='{self.tanggal}', jenis='{self.jenis}', nominal={self.nominal})>"


class PengeluaranOffline(Base):
    __tablename__ = "pengeluaran_offline"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tanggal: Mapped[str] = mapped_column(String, nullable=False, index=True)
    sku_id: Mapped[int] = mapped_column(ForeignKey("sku_master.id"), nullable=False)
    qty: Mapped[float] = mapped_column(Float, nullable=False)
    harga_satuan: Mapped[float] = mapped_column(Float, nullable=False)
    total: Mapped[float] = mapped_column(Float, nullable=False)
    person_id: Mapped[Optional[int]] = mapped_column(ForeignKey("persons.id"))
    client_id: Mapped[Optional[int]] = mapped_column(ForeignKey("clients.id"))
    catatan: Mapped[Optional[str]] = mapped_column(String)

    is_deleted: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now
    )

    person = relationship("Person")
    sku = relationship("SkuMaster")
    client = relationship("Client")

    def __repr__(self) -> str:
        return f"<PengeluaranOffline(tanggal='{self.tanggal}', total={self.total})>"
