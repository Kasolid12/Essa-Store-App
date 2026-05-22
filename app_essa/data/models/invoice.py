from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, Float, Integer, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base

class Invoice(Base):
    __tablename__ = "invoices"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    nomor_invoice: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    tanggal: Mapped[str] = mapped_column(String, nullable=False)
    
    person_id: Mapped[int] = mapped_column(ForeignKey("persons.id"), nullable=False, index=True) # Klien
    
    subtotal: Mapped[float] = mapped_column(Float, default=0.0)
    diskon: Mapped[float] = mapped_column(Float, default=0.0)
    ongkir: Mapped[float] = mapped_column(Float, default=0.0)
    total: Mapped[float] = mapped_column(Float, default=0.0)
    dp: Mapped[float] = mapped_column(Float, default=0.0)
    sisa: Mapped[float] = mapped_column(Float, default=0.0)
    
    status: Mapped[str] = mapped_column(String, default="OPEN") # 'OPEN', 'PARTIAL', 'LUNAS', 'VOID'
    pdf_path: Mapped[Optional[str]] = mapped_column(String)
    catatan: Mapped[Optional[str]] = mapped_column(String)
    
    is_deleted: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    person = relationship("Person")
    lines: Mapped[List["InvoiceLine"]] = relationship("InvoiceLine", back_populates="invoice")
    receivable = relationship("ClientReceivable", back_populates="invoice", uselist=False)

class InvoiceLine(Base):
    __tablename__ = "invoice_lines"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("invoices.id"), nullable=False)
    sku_id: Mapped[int] = mapped_column(ForeignKey("sku_master.id"), nullable=False)
    
    qty: Mapped[int] = mapped_column(Integer, nullable=False)
    harga_satuan: Mapped[float] = mapped_column(Float, nullable=False)
    diskon_line: Mapped[float] = mapped_column(Float, default=0.0)
    subtotal: Mapped[float] = mapped_column(Float, nullable=False)

    invoice = relationship("Invoice", back_populates="lines")
    sku = relationship("SkuMaster")

class ClientReceivable(Base):
    __tablename__ = "client_receivables"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    invoice_id: Mapped[Optional[int]] = mapped_column(ForeignKey("invoices.id"))
    person_id: Mapped[int] = mapped_column(ForeignKey("persons.id"), nullable=False, index=True)
    
    nominal: Mapped[float] = mapped_column(Float, nullable=False)
    sisa: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String, default="OPEN")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    invoice = relationship("Invoice", back_populates="receivable")
    person = relationship("Person")
    payments: Mapped[List["ClientReceivablePayment"]] = relationship("ClientReceivablePayment", back_populates="receivable")

class ClientReceivablePayment(Base):
    __tablename__ = "client_receivable_payments"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    receivable_id: Mapped[int] = mapped_column(ForeignKey("client_receivables.id"), nullable=False)
    tanggal_bayar: Mapped[str] = mapped_column(String, nullable=False)
    
    nominal_bayar: Mapped[float] = mapped_column(Float, nullable=False)
    metode: Mapped[Optional[str]] = mapped_column(String)
    catatan: Mapped[Optional[str]] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    receivable = relationship("ClientReceivable", back_populates="payments")