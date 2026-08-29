"""
Yazmina Hijab Web — Profit Simulation API.

Ported from ui/views/profit_view.py desktop app.
Core engine: pulls data by kode_produksi, calculates net profit, saves history.
"""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from ..database import get_db
from ..auth import get_current_admin
from ..models.admin_user import AdminUser
from ..models.debt import DebtEntry
from ..models.daily_notes import HasilCutting, DistribusiCutting
from ..models.sku import SkuMaster
from ..models.profit import ProfitHistory, TarifMaster

router = APIRouter(prefix="/api/profit", tags=["profit"])

# ── Production Cost Constants (from desktop app) ──────────────────────
COST_PACK = 100
COST_HANGTAG = 97
COST_WOVEN = 150
COST_HTROPE = 20
COST_THREAD = 100
COST_AKRILIK = 250


# ── Helper Functions ──────────────────────────────────────────────────

def identify_sku_components(sku_kode: str):
    """Split SKU into base code and size for special rule detection."""
    target = str(sku_kode).strip().upper()
    parts = target.split("-")
    base = parts[0]
    size = ""
    for p in parts:
        if p in ["S", "M", "L", "XL", "ADILA"]:
            size = p
            break
    return base, size, target


def get_sewing_cost(db: Session, sku_kode: str) -> float:
    """Find sewing cost (tarif_jahit) from TarifMaster with fallback."""
    # 1. Exact match
    tarif = db.query(TarifMaster).filter(TarifMaster.kode_sku == sku_kode).first()
    if tarif and (tarif.tarif_jahit or 0) > 0:
        return tarif.tarif_jahit

    base, size, _ = identify_sku_components(sku_kode)

    # 2. Fallback: Base-Size (e.g. "DG-L")
    if size:
        f1 = db.query(TarifMaster).filter(TarifMaster.kode_sku == f"{base}-{size}").first()
        if f1 and (f1.tarif_jahit or 0) > 0:
            return f1.tarif_jahit

    # 3. Fallback: Base only (e.g. "DG")
    f2 = db.query(TarifMaster).filter(TarifMaster.kode_sku == base).first()
    if f2 and (f2.tarif_jahit or 0) > 0:
        return f2.tarif_jahit

    return 700.0  # Default


def get_service_cost(db: Session, sku_kode: str) -> float:
    """Find cutting/supplier cost (tarif_pengsup_potongan) from TarifMaster."""
    tarif = db.query(TarifMaster).filter(TarifMaster.kode_sku == sku_kode).first()
    if tarif and (tarif.tarif_pengsup_potongan or 0) > 0:
        return tarif.tarif_pengsup_potongan

    base, size, _ = identify_sku_components(sku_kode)
    if size:
        f1 = db.query(TarifMaster).filter(TarifMaster.kode_sku == f"{base}-{size}").first()
        if f1 and (f1.tarif_pengsup_potongan or 0) > 0:
            return f1.tarif_pengsup_potongan

    f2 = db.query(TarifMaster).filter(TarifMaster.kode_sku == base).first()
    if f2 and (f2.tarif_pengsup_potongan or 0) > 0:
        return f2.tarif_pengsup_potongan

    return 1500.0  # Default


def get_harga_jual(db: Session, sku_kode: str) -> float:
    """Find selling price from SkuMaster."""
    sku = db.query(SkuMaster).filter(SkuMaster.kode_sku == sku_kode).first()
    if sku and sku.harga_jual is not None:
        return sku.harga_jual
    return 0.0


# ── Endpoints ─────────────────────────────────────────────────────────

@router.get("/batches")
def list_batches(
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """List all unique kode_produksi from hutang MODAL."""
    rows = (
        db.query(DebtEntry.kode_produksi)
        .filter(DebtEntry.kode_produksi.isnot(None))
        .filter(DebtEntry.tipe_hutang == "MODAL")
        .distinct()
        .all()
    )
    batches = sorted([r[0] for r in rows if r[0]], reverse=True)
    return {"batches": batches}


@router.get("/analyze/{kode_produksi}")
def analyze_batch(
    kode_produksi: str,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """
    Core engine: analyze a batch by kode_produksi.
    Returns modal kain data, cutting data, distribution data, and profit calculation.
    """
    # 1. Modal Kain (DebtEntry MODAL)
    hutangs = (
        db.query(DebtEntry)
        .filter(DebtEntry.kode_produksi == kode_produksi)
        .filter(DebtEntry.tipe_hutang == "MODAL")
        .all()
    )

    kain_qty = sum(h.qty for h in hutangs if h.qty)
    kain_total = sum(h.nominal_hutang for h in hutangs)
    kain_harga = kain_total / kain_qty if kain_qty > 0 else 0

    # Status cutting
    status_kain = "OPEN"
    if hutangs:
        status_kain = getattr(hutangs[0], "status_cutting", "OPEN") or "OPEN"

    # 2. Hasil Cutting
    cuttings = (
        db.query(HasilCutting)
        .filter(HasilCutting.kode_produksi == kode_produksi)
        .all()
    )
    cut_qty = sum(c.qty for c in cuttings)

    # 3. Distribusi
    distribusis = (
        db.query(DistribusiCutting)
        .options(joinedload(DistribusiCutting.sku))
        .filter(DistribusiCutting.kode_produksi == kode_produksi)
        .all()
    )

    dist_home = 0
    dist_sup = 0
    cost_home_total = 0.0
    cost_sup_total = 0.0
    total_revenue = 0.0
    sku_missing_price = []

    dist_details = []

    for dist in distribusis:
        jenis = (dist.jenis or "").lower()
        sku_kode = dist.sku.kode_sku if dist.sku else ""
        qty = dist.qty

        base, _, _ = identify_sku_components(sku_kode)
        tambahan_akrilik = COST_AKRILIK if base == "DG" else 0

        harga_jual = get_harga_jual(db, sku_kode)
        if harga_jual <= 0 and sku_kode and sku_kode not in sku_missing_price:
            sku_missing_price.append(sku_kode)

        total_revenue += qty * harga_jual

        dist_detail = {
            "id": dist.id,
            "tanggal": dist.tanggal,
            "person_id": dist.person_id,
            "person_nama": dist.person.nama if dist.person else "",
            "jenis": dist.jenis,
            "sku_kode": sku_kode,
            "sku_nama": dist.sku.nama_produk if dist.sku else "",
            "qty": qty,
            "harga_jual": harga_jual,
        }

        if "penjahit" in jenis or "home" in jenis:
            dist_home += qty
            biaya_jahit = get_sewing_cost(db, sku_kode)
            biaya_pcs = biaya_jahit + COST_PACK + COST_HANGTAG + COST_WOVEN + COST_HTROPE + COST_THREAD + tambahan_akrilik
            cost_home_total += qty * biaya_pcs
            dist_detail["biaya_pcs"] = biaya_pcs
            dist_detail["biaya_total"] = qty * biaya_pcs
        elif "sup" in jenis:
            dist_sup += qty
            biaya_service = get_service_cost(db, sku_kode)
            biaya_pcs = biaya_service + COST_HANGTAG + COST_WOVEN + COST_HTROPE + tambahan_akrilik
            cost_sup_total += qty * biaya_pcs
            dist_detail["biaya_pcs"] = biaya_pcs
            dist_detail["biaya_total"] = qty * biaya_pcs

        dist_details.append(dist_detail)

    total_dist = dist_home + dist_sup
    gross_margin = total_revenue - kain_total
    net_profit = gross_margin - (cost_home_total + cost_sup_total)

    # Verification status
    if cut_qty == 0:
        verif_status = "BELUM_DI_CUTTING"
        verif_label = "Belum Di-Cutting!"
    elif total_dist < cut_qty:
        verif_status = "TERTAHAN"
        verif_label = f"Tertahan (Kurang {cut_qty - total_dist} pcs)"
    else:
        verif_status = "SIAP"
        verif_label = "Siap Dihitung"

    return {
        "kode_produksi": kode_produksi,
        # Modal kain
        "kain_qty": kain_qty,
        "kain_harga_per_kg": kain_harga,
        "kain_total": kain_total,
        "status_kain": status_kain,
        # Cutting
        "cut_qty": cut_qty,
        "dist_home": dist_home,
        "dist_sup": dist_sup,
        "total_dist": total_dist,
        # Revenue
        "total_revenue": total_revenue,
        "sku_missing_price": sku_missing_price,
        # Costs
        "cost_home_total": cost_home_total,
        "cost_sup_total": cost_sup_total,
        "cost_produksi_total": cost_home_total + cost_sup_total,
        # Profit
        "gross_margin": gross_margin,
        "net_profit": net_profit,
        # Verification
        "verif_status": verif_status,
        "verif_label": verif_label,
        # Distribution details
        "distribusi": dist_details,
    }


@router.post("/toggle-status/{kode_produksi}")
def toggle_status_kain(
    kode_produksi: str,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """Toggle status_cutting between OPEN <-> SELESAI for a batch."""
    hutangs = (
        db.query(DebtEntry)
        .filter(DebtEntry.kode_produksi == kode_produksi)
        .filter(DebtEntry.tipe_hutang == "MODAL")
        .all()
    )

    if not hutangs:
        raise HTTPException(status_code=404, detail="Batch tidak ditemukan")

    current = getattr(hutangs[0], "status_cutting", "OPEN") or "OPEN"
    new_status = "OPEN" if current == "SELESAI" else "SELESAI"

    for h in hutangs:
        h.status_cutting = new_status

    db.commit()

    return {
        "kode_produksi": kode_produksi,
        "old_status": current,
        "new_status": new_status,
        "message": f"Status kain diubah ke {'FULL CUTTING' if new_status == 'SELESAI' else 'BELUM FULL'}",
    }


@router.post("/save-history")
def save_profit_history(
    kode_produksi: str,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """Save/overwrite profit calculation to profit_history (upsert per batch)."""
    # Recalculate first
    hutangs = (
        db.query(DebtEntry)
        .filter(DebtEntry.kode_produksi == kode_produksi)
        .filter(DebtEntry.tipe_hutang == "MODAL")
        .all()
    )

    if not hutangs:
        raise HTTPException(status_code=404, detail="Batch tidak ditemukan")

    cuttings = (
        db.query(HasilCutting)
        .filter(HasilCutting.kode_produksi == kode_produksi)
        .all()
    )

    distribusis = (
        db.query(DistribusiCutting)
        .options(joinedload(DistribusiCutting.sku))
        .filter(DistribusiCutting.kode_produksi == kode_produksi)
        .all()
    )

    kain_total = sum(h.nominal_hutang for h in hutangs)

    total_revenue = 0.0
    cost_home_total = 0.0
    cost_sup_total = 0.0

    for dist in distribusis:
        jenis = (dist.jenis or "").lower()
        sku_kode = dist.sku.kode_sku if dist.sku else ""
        qty = dist.qty
        base, _, _ = identify_sku_components(sku_kode)
        tambahan_akrilik = COST_AKRILIK if base == "DG" else 0
        harga_jual = get_harga_jual(db, sku_kode)
        total_revenue += qty * harga_jual

        if "penjahit" in jenis or "home" in jenis:
            cost_home_total += qty * (get_sewing_cost(db, sku_kode) + COST_PACK + COST_HANGTAG + COST_WOVEN + COST_HTROPE + COST_THREAD + tambahan_akrilik)
        elif "sup" in jenis:
            cost_sup_total += qty * (get_service_cost(db, sku_kode) + COST_HANGTAG + COST_WOVEN + COST_HTROPE + tambahan_akrilik)

    cost_total = cost_home_total + cost_sup_total
    net_profit = total_revenue - kain_total - cost_total

    today = datetime.now().strftime("%Y-%m-%d")
    debt_entry_id = min((h.id for h in hutangs), default=None)
    cut_dates = [c.tanggal for c in cuttings if getattr(c, "tanggal", None)]
    periode_mulai = min(cut_dates) if cut_dates else today
    periode_akhir = max(cut_dates) if cut_dates else today
    dist_home = sum(d.qty for d in distribusis if "penjahit" in (d.jenis or "").lower() or "home" in (d.jenis or "").lower())
    dist_sup = sum(d.qty for d in distribusis if "sup" in (d.jenis or "").lower())
    catatan = f"Batch {kode_produksi} | Dist Home {dist_home} pcs / Sup {dist_sup} pcs"

    # Upsert
    record = None
    if debt_entry_id is not None:
        record = db.query(ProfitHistory).filter(ProfitHistory.debt_entry_id == debt_entry_id).first()

    if record is None:
        record = ProfitHistory(debt_entry_id=debt_entry_id)
        db.add(record)

    kain_dates = [h.tanggal for h in hutangs if getattr(h, "tanggal", None)]
    record.tanggal_hitung = min(kain_dates) if kain_dates else today
    record.total_pendapatan = float(total_revenue)
    record.total_modal_kain = float(kain_total)
    record.total_modal_jahit = float(cost_total)
    record.total_profit = float(net_profit)
    record.periode_mulai = periode_mulai
    record.periode_akhir = periode_akhir
    record.catatan = catatan

    db.commit()

    return {
        "message": "Profit history tersimpan",
        "batch": kode_produksi,
        "total_pendapatan": total_revenue,
        "total_modal_kain": kain_total,
        "total_modal_jahit": cost_total,
        "total_profit": net_profit,
    }


@router.get("/history")
def list_profit_history(
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """List all saved profit history records."""
    records = (
        db.query(ProfitHistory)
        .order_by(ProfitHistory.tanggal_hitung.desc())
        .limit(50)
        .all()
    )
    return [
        {
            "id": r.id,
            "tanggal_hitung": r.tanggal_hitung,
            "debt_entry_id": r.debt_entry_id,
            "total_pendapatan": r.total_pendapatan,
            "total_modal_kain": r.total_modal_kain,
            "total_modal_jahit": r.total_modal_jahit,
            "total_profit": r.total_profit,
            "periode_mulai": r.periode_mulai,
            "periode_akhir": r.periode_akhir,
            "catatan": r.catatan,
        }
        for r in records
    ]


@router.get("/tarif")
def list_tarif(
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """List all tariffs."""
    records = db.query(TarifMaster).order_by(TarifMaster.kode_sku).all()
    return [
        {
            "id": r.id,
            "kode_sku": r.kode_sku,
            "tarif_jahit": r.tarif_jahit,
            "tarif_pengsup_kain": r.tarif_pengsup_kain,
            "tarif_pengsup_potongan": r.tarif_pengsup_potongan,
        }
        for r in records
    ]


class TarifCreate(BaseModel):
    kode_sku: str
    tarif_jahit: float = 0.0
    tarif_pengsup_kain: float = 0.0
    tarif_pengsup_potongan: float = 0.0


@router.post("/tarif")
def create_tarif(
    body: TarifCreate,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """Create or update tariff for a SKU."""
    existing = db.query(TarifMaster).filter(TarifMaster.kode_sku == body.kode_sku).first()
    if existing:
        existing.tarif_jahit = body.tarif_jahit
        existing.tarif_pengsup_kain = body.tarif_pengsup_kain
        existing.tarif_pengsup_potongan = body.tarif_pengsup_potongan
        db.commit()
        return {"message": "Tarif diperbarui", "id": existing.id}
    else:
        t = TarifMaster(
            kode_sku=body.kode_sku,
            tarif_jahit=body.tarif_jahit,
            tarif_pengsup_kain=body.tarif_pengsup_kain,
            tarif_pengsup_potongan=body.tarif_pengsup_potongan,
        )
        db.add(t)
        db.commit()
        return {"message": "Tarif dibuat", "id": t.id}
