"""Models for Client, ClientReceivable, ClientReceivablePayment."""
from datetime import datetime
from typing import Optional, List

from sqlalchemy import String, Float, Integer, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base


class Client(Base):
    __tablename__ = "clients"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    nama: Mapped[str] = mapped_column(String, nullable=False)
    alamat: Mapped[Optional[str]] = mapped_column(String)
    no_hp: Mapped[Optional[str]] = mapped_column(String)
    catatan: Mapped[Optional[str]] = mapped_column(String)

    is_active: Mapped[int] = mapped_column(Integer, default=1)
    is_deleted: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now
    )


class ClientReceivable(Base):
    __tablename__ = "client_receivables"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    person_id: Mapped[Optional[int]] = mapped_column(ForeignKey("persons.id"), index=True)
    client_id: Mapped[Optional[int]] = mapped_column(ForeignKey("clients.id"), index=True)

    nominal: Mapped[float] = mapped_column(Float, nullable=False)
    sisa: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String, default="OPEN")  # OPEN / LUNAS
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now
    )

    person = relationship("Person")
    client = relationship("Client")
    payments: Mapped[List["ClientReceivablePayment"]] = relationship(
        "ClientReceivablePayment", back_populates="receivable"
    )


class ClientReceivablePayment(Base):
    __tablename__ = "client_receivable_payments"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    receivable_id: Mapped[int] = mapped_column(
        ForeignKey("client_receivables.id"), nullable=False
    )
    tanggal_bayar: Mapped[str] = mapped_column(String, nullable=False)
    nominal_bayar: Mapped[float] = mapped_column(Float, nullable=False)
    metode: Mapped[Optional[str]] = mapped_column(String)
    catatan: Mapped[Optional[str]] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now
    )

    receivable = relationship("ClientReceivable", back_populates="payments")
