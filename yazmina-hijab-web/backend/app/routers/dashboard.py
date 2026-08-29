"""
Yazmina Hijab Web — Dashboard API.

Phase 6: Full analytics — 4 KPIs + omzet summary + monthly trend chart data.
Ported from data/dashboard_queries.py with enhanced analytics.
"""

from datetime import date, datetime
from calendar import month_name
from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..database import get_db
from ..auth import get_current_admin
from ..models.admin_user import AdminUser
from ..models.debt import DebtEntry, DebtPayment
from ..models.invoice import ClientReceivable
from ..models.payroll import SalaryRun
from ..models.daily_notes import PengeluaranOffline, ModalOperasional

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


# ── 4 Core KPIs ──────────────────────────────────────────────────────

def _get_total_hutang_tersisa(db: Session) -> float:
    """SUM nominal_hutang belum lunas - SUM bayar terkait."""
    total_hutang = (
        db.query(func.coalesce(func.sum(DebtEntry.nominal_hutang), 0.0))
        .filter(DebtEntry.is_deleted == 0)
        .filter(DebtEntry.status != "LUNAS")
        .scalar()
    ) or 0.0
    total_bayar = (
        db.query(func.coalesce(func.sum(DebtPayment.nominal_bayar), 0.0))
        .join(DebtEntry, DebtPayment.debt_entry_id == DebtEntry.id)
        .filter(DebtPayment.is_deleted == 0)
        .filter(DebtEntry.is_deleted == 0)
        .filter(DebtEntry.status != "LUNAS")
        .scalar()
    ) or 0.0
    return float(total_hutang) - float(total_bayar)


def _get_total_piutang(db: Session) -> float:
    """SUM sisa dari client_receivables yang belum lunas."""
    return float(
        (
            db.query(func.coalesce(func.sum(ClientReceivable.sisa), 0.0))
            .filter(ClientReceivable.status != "LUNAS")
            .scalar()
        )
        or 0.0
    )


def _get_gaji_karyawan(db: Session, mulai: str, akhir: str) -> float:
    """SUM gaji_bersih salary_runs karyawan dalam rentang tanggal."""
    return float(
        (
            db.query(func.coalesce(func.sum(SalaryRun.gaji_bersih), 0.0))
            .filter(SalaryRun.tipe == "PASUKAN_KARYAWAN")
            .filter(SalaryRun.is_deleted == 0)
            .filter(SalaryRun.tanggal_proses.between(mulai, akhir))
            .scalar()
        )
        or 0.0
    )


def _get_profit_produksi(db: Session, mulai: str, akhir: str) -> float:
    """Approximate: Penjualan offline + Invoice receipts - Modal operasional - Gaji karyawan."""
    # Total penjualan offline dalam rentang
    penjualan_offline = float(
        (
            db.query(func.coalesce(func.sum(PengeluaranOffline.total), 0.0))
            .filter(PengeluaranOffline.is_deleted == 0)
            .filter(PengeluaranOffline.tanggal.between(mulai, akhir))
            .scalar()
        )
        or 0.0
    )

    # Total pembayaran piutang diterima dalam rentang
    from ..models.invoice import ClientReceivablePayment
    piutang_bayar = float(
        (
            db.query(func.coalesce(func.sum(ClientReceivablePayment.nominal_bayar), 0.0))
            .filter(ClientReceivablePayment.tanggal_bayar.between(mulai, akhir))
            .scalar()
        )
        or 0.0
    )

    # Total modal operasional dalam rentang
    modal_op = float(
        (
            db.query(func.coalesce(func.sum(ModalOperasional.nominal), 0.0))
            .filter(ModalOperasional.is_deleted == 0)
            .filter(ModalOperasional.tanggal.between(mulai, akhir))
            .scalar()
        )
        or 0.0
    )

    # Total gaji karyawan dalam rentang
    gaji = _get_gaji_karyawan(db, mulai, akhir)

    # Profit = Omzet - Biaya
    omzet = penjualan_offline + piutang_bayar
    return omzet - modal_op - gaji


# ── Main Dashboard Endpoint ───────────────────────────────────────────

@router.get("")
def get_dashboard(
    mulai: str = "",
    akhir: str = "",
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """Return 4 KPI values + omzet breakdown + profit analysis."""
    # Default: bulan ini
    today = date.today()
    if not mulai:
        mulai = today.replace(day=1).strftime("%Y-%m-%d")
    if not akhir:
        akhir = today.strftime("%Y-%m-%d")

    # 4 Core KPIs
    total_hutang_tersisa = _get_total_hutang_tersisa(db)
    total_piutang = _get_total_piutang(db)
    gaji_karyawan = _get_gaji_karyawan(db, mulai, akhir)
    profit_produksi = _get_profit_produksi(db, mulai, akhir)

    # ── Omzet Breakdown ──────────────────────────────────────────────
    from ..models.invoice import ClientReceivablePayment

    penjualan_offline = float(
        (
            db.query(func.coalesce(func.sum(PengeluaranOffline.total), 0.0))
            .filter(PengeluaranOffline.is_deleted == 0)
            .filter(PengeluaranOffline.tanggal.between(mulai, akhir))
            .scalar()
        )
        or 0.0
    )

    piutang_bayar = float(
        (
            db.query(func.coalesce(func.sum(ClientReceivablePayment.nominal_bayar), 0.0))
            .filter(ClientReceivablePayment.tanggal_bayar.between(mulai, akhir))
            .scalar()
        )
        or 0.0
    )

    modal_operasional = float(
        (
            db.query(func.coalesce(func.sum(ModalOperasional.nominal), 0.0))
            .filter(ModalOperasional.is_deleted == 0)
            .filter(ModalOperasional.tanggal.between(mulai, akhir))
            .scalar()
        )
        or 0.0
    )

    # Modal operasional per jenis
    modal_per_jenis = {}
    rows = (
        db.query(ModalOperasional.jenis, func.coalesce(func.sum(ModalOperasional.nominal), 0.0))
        .filter(ModalOperasional.is_deleted == 0)
        .filter(ModalOperasional.tanggal.between(mulai, akhir))
        .group_by(ModalOperasional.jenis)
        .all()
    )
    for jenis, total in rows:
        modal_per_jenis[jenis] = float(total)

    omzet = penjualan_offline + piutang_bayar

    return {
        # Core KPIs
        "total_hutang_tersisa": total_hutang_tersisa,
        "total_piutang": total_piutang,
        "gaji_karyawan": gaji_karyawan,
        "profit_produksi": profit_produksi,
        # Omzet Breakdown
        "omzet": omzet,
        "penjualan_offline": penjualan_offline,
        "piutang_diterima": piutang_bayar,
        "modal_operasional": modal_operasional,
        "modal_per_jenis": modal_per_jenis,
        "periode_mulai": mulai,
        "periode_akhir": akhir,
    }


# ── Monthly Trend Data (for chart) ───────────────────────────────────

@router.get("/trend")
def get_dashboard_trend(
    months: int = 6,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """Return monthly omzet + profit + gaji for the last N months."""
    from ..models.invoice import ClientReceivablePayment

    today = date.today()
    result = []

    for i in range(months - 1, -1, -1):
        # Calculate month boundaries
        year = today.year
        month = today.month - i
        while month <= 0:
            month += 12
            year -= 1

        first_day = date(year, month, 1)
        if month == 12:
            last_day = date(year + 1, 1, 1)
        else:
            last_day = date(year, month + 1, 1)

        m_start = first_day.strftime("%Y-%m-%d")
        m_end = last_day.strftime("%Y-%m-%d")

        # Penjualan offline
        penjualan = float(
            (
                db.query(func.coalesce(func.sum(PengeluaranOffline.total), 0.0))
                .filter(PengeluaranOffline.is_deleted == 0)
                .filter(PengeluaranOffline.tanggal.between(m_start, m_end))
                .scalar()
            )
            or 0.0
        )

        # Piutang diterima
        piutang = float(
            (
                db.query(func.coalesce(func.sum(ClientReceivablePayment.nominal_bayar), 0.0))
                .filter(ClientReceivablePayment.tanggal_bayar.between(m_start, m_end))
                .scalar()
            )
            or 0.0
        )

        # Modal operasional
        modal = float(
            (
                db.query(func.coalesce(func.sum(ModalOperasional.nominal), 0.0))
                .filter(ModalOperasional.is_deleted == 0)
                .filter(ModalOperasional.tanggal.between(m_start, m_end))
                .scalar()
            )
            or 0.0
        )

        # Gaji karyawan
        gaji = float(
            (
                db.query(func.coalesce(func.sum(SalaryRun.gaji_bersih), 0.0))
                .filter(SalaryRun.tipe == "PASUKAN_KARYAWAN")
                .filter(SalaryRun.is_deleted == 0)
                .filter(SalaryRun.tanggal_proses.between(m_start, m_end))
                .scalar()
            )
            or 0.0
        )

        omzet = penjualan + piutang
        profit = omzet - modal - gaji

        result.append({
            "month": month_name[month],
            "year": year,
            "omzet": omzet,
            "modal": modal,
            "gaji": gaji,
            "profit": profit,
        })

    return result


# ── Quick Stats (for sidebar badge) ───────────────────────────────────

@router.get("/stats")
def get_quick_stats(
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """Quick stats for sidebar: overdue debts, unpaid invoices, etc."""
    # Hutang overdue (OPEN status)
    hutang_open = (
        db.query(func.count(DebtEntry.id))
        .filter(DebtEntry.is_deleted == 0)
        .filter(DebtEntry.status == "OPEN")
        .scalar()
    ) or 0

    # Piutang unpaid
    piutang_open = (
        db.query(func.count(ClientReceivable.id))
        .filter(ClientReceivable.status == "OPEN")
        .scalar()
    ) or 0

    # Pending salary runs
    gaji_pending = (
        db.query(func.count(SalaryRun.id))
        .filter(SalaryRun.is_deleted == 0)
        .filter(SalaryRun.tipe == "PASUKAN_KARYAWAN")
        .scalar()
    ) or 0

    return {
        "hutang_open": hutang_open,
        "piutang_open": piutang_open,
        "gaji_pending": gaji_pending,
    }
