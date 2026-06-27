"""
Query functions untuk Dashboard (Sesi 2).

Functions-only — tidak ada UI. Setiap fungsi menerima `session` dari caller
(lihat SessionLocal di data/database.py) dan mengembalikan agregat float.

CATATAN PENTING — nilai filter sudah dikoreksi terhadap data aktual essa.db,
berbeda dari SQL referensi di CLAUDE.md. Lihat komentar per fungsi.
"""

from sqlalchemy import func

from data.models.debt import DebtEntry, DebtPayment
from data.models.invoice import ClientReceivable
from data.models.salary import SalaryRun
from data.models.profit_history import ProfitHistory


def get_total_hutang_tersisa(session) -> float:
    """SUM nominal_hutang debt_entries belum lunas dikurangi SUM nominal_bayar terkait.

    Filter is_deleted=0 di kedua tabel.

    KOREKSI: DebtEntry.status menyimpan nilai UPPERCASE ('OPEN'/'PARTIAL'/'LUNAS').
    SQL referensi memakai `status != 'lunas'` (lowercase) yang akan cocok ke SEMUA
    baris. Di sini dipakai 'LUNAS'.
    """
    total_hutang = (
        session.query(func.coalesce(func.sum(DebtEntry.nominal_hutang), 0.0))
        .filter(DebtEntry.is_deleted == 0)
        .filter(DebtEntry.status != "LUNAS")
        .scalar()
    ) or 0.0

    total_bayar = (
        session.query(func.coalesce(func.sum(DebtPayment.nominal_bayar), 0.0))
        .join(DebtEntry, DebtPayment.debt_entry_id == DebtEntry.id)
        .filter(DebtPayment.is_deleted == 0)
        .filter(DebtEntry.is_deleted == 0)
        .filter(DebtEntry.status != "LUNAS")
        .scalar()
    ) or 0.0

    return float(total_hutang) - float(total_bayar)


def get_total_piutang(session) -> float:
    """SUM sisa dari client_receivables yang belum lunas.

    KOREKSI: tabel client_receivables TIDAK punya kolom is_deleted, jadi tidak
    ada filter soft-delete. status juga UPPERCASE (default 'OPEN'), jadi dipakai
    `status != 'LUNAS'` bukan lowercase 'lunas' dari SQL referensi.
    """
    return float(
        (
            session.query(func.coalesce(func.sum(ClientReceivable.sisa), 0.0))
            .filter(ClientReceivable.status != "LUNAS")
            .scalar()
        )
        or 0.0
    )


def get_akumulasi_gaji_karyawan(session, tgl_mulai: str, tgl_akhir: str) -> float:
    """SUM gaji_bersih salary_runs karyawan dalam rentang tanggal_proses.

    Filter is_deleted=0 dan tanggal_proses BETWEEN tgl_mulai AND tgl_akhir.

    KOREKSI: tidak ada baris dengan tipe='karyawan' di data aktual. Payroll
    karyawan tersimpan dengan tipe='PASUKAN_KARYAWAN'. Filter spec `tipe='karyawan'`
    mengembalikan 0.0. Di sini dipakai 'PASUKAN_KARYAWAN'.
    """
    return float(
        (
            session.query(func.coalesce(func.sum(SalaryRun.gaji_bersih), 0.0))
            .filter(SalaryRun.tipe == "PASUKAN_KARYAWAN")
            .filter(SalaryRun.is_deleted == 0)
            .filter(SalaryRun.tanggal_proses.between(tgl_mulai, tgl_akhir))
            .scalar()
        )
        or 0.0
    )


def get_profit_produksi(session, tgl_mulai: str, tgl_akhir: str) -> float:
    """SUM total_profit dari profit_history dalam rentang tanggal_hitung.

    Hanya batch yang sudah FULL CUT (debt_entries.status_cutting = 'SELESAI')
    yang dihitung di Dashboard. Batch tanpa debt_entry_id (tidak terikat kain)
    tetap dihitung (mis. biaya produksi umum).

    Referensi query:
        SELECT SUM(ph.total_profit)
        FROM profit_history ph
        LEFT JOIN debt_entries de ON ph.debt_entry_id = de.id
        WHERE ph.tanggal_hitung BETWEEN :mulai AND :akhir
          AND (de.status_cutting = 'SELESAI' OR ph.debt_entry_id IS NULL)

    Tombol FULL CUT ada di menu Profit Simulation (toggle_status_kain).
    """
    return float(
        (
            session.query(func.coalesce(func.sum(ProfitHistory.total_profit), 0.0))
            .outerjoin(DebtEntry, ProfitHistory.debt_entry_id == DebtEntry.id)
            .filter(ProfitHistory.tanggal_hitung.between(tgl_mulai, tgl_akhir))
            .filter(
                (DebtEntry.status_cutting == "SELESAI")
                | (ProfitHistory.debt_entry_id.is_(None))
            )
            .scalar()
        )
        or 0.0
    )
