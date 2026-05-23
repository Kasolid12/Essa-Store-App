from datetime import datetime
from typing import Optional
from sqlalchemy import String, Integer, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base

class StockMovement(Base):
    __tablename__ = "stock_movements"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tanggal: Mapped[str] = mapped_column(String, nullable=False)
    sku_id: Mapped[int] = mapped_column(ForeignKey("sku_master.id"), nullable=False, index=True)
    
    # 'IN_CUTTING', 'IN_RETUR', 'OUT_OFFLINE', 'OUT_INVOICE', 'OUT_HILANG', 'ADJUST_PLUS', 'ADJUST_MINUS'
    tipe: Mapped[str] = mapped_column(String, nullable=False)
    qty: Mapped[int] = mapped_column(Integer, nullable=False) # positive for IN, negative for OUT
    
    sumber_ref: Mapped[Optional[str]] = mapped_column(String) # e.g., 'hasil_cutting:123'
    catatan: Mapped[Optional[str]] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    sku = relationship("SkuMaster")

class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    table_name: Mapped[str] = mapped_column(String, nullable=False, index=True)
    record_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    
    action: Mapped[str] = mapped_column(String, nullable=False) # 'INSERT', 'UPDATE', 'DELETE', 'SOFT_DELETE'
    user_session: Mapped[Optional[str]] = mapped_column(String)
    
    before_json: Mapped[Optional[str]] = mapped_column(String) # Store as JSON string
    after_json: Mapped[Optional[str]] = mapped_column(String)  # Store as JSON string
    
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)