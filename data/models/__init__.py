# app_essa/data/models/__init__.py

from .base import Base
from .sku import SkuMaster
from .person import Person
from .master import GarapanRate, AppSetting
from .catatan_harian import HasilCutting, DistribusiCutting, ModalOperasional, PengeluaranOffline
from .debt import DebtEntry, DebtPayment
from .bon import BonBalance, BonMovement
from .salary import SalaryRun, SalaryLineItem, PengsupReconciliation, AttendanceRecord
from .invoice import Invoice, InvoiceLine, ClientReceivable, ClientReceivablePayment
from .stock_audit import StockMovement, AuditLog
from .profit_history import ProfitHistory

# This ensures all models are attached to Base.metadata before Alembic reads it