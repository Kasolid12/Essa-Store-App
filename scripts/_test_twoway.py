"""Harness uji E2E sinkronisasi dua arah (Fase 6.2) — 2 perangkat + cloud tiruan.

Menjalankan tiap langkah di PROSES terpisah dengan env berbeda:
  - Perangkat A : APP_DATABASE_URL=sqlite:///twoway_a.db
  - Perangkat B : APP_DATABASE_URL=sqlite:///twoway_b.db
  - Cloud tiruan : CLOUD_DATABASE_URL=sqlite:///twoway_cloud.db

Jangan dijalankan bersamaan dengan aplikasi (menggunakan file DB sementara).
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DEV_A = {"APP_DATABASE_URL": "sqlite:///twoway_a.db", "CLOUD_DATABASE_URL": "sqlite:///twoway_cloud.db"}
DEV_B = {"APP_DATABASE_URL": "sqlite:///twoway_b.db", "CLOUD_DATABASE_URL": "sqlite:///twoway_cloud.db"}
NONE = {}


def run(env_extra, step, label):
    env = dict(os.environ)
    env.update(env_extra)
    cmd = [sys.executable, "-c", f"from scripts._twodev import {step}; {step}()"]
    r = subprocess.run(cmd, cwd=ROOT, env=env, capture_output=True, text=True)
    print(f"\n===== {label} =====")
    print(r.stdout, end="")
    if r.returncode != 0:
        print(r.stderr, end="")
        sys.exit(f"GAGAL pada {label} (rc={r.returncode})")


def main():
    for f in ("twoway_a.db", "twoway_b.db", "twoway_cloud.db",
              "twoway_a.db-wal", "twoway_b.db-wal", "twoway_cloud.db-wal",
              "twoway_a.db-shm", "twoway_b.db-shm", "twoway_cloud.db-shm"):
        p = os.path.join(ROOT, f)
        if os.path.exists(p):
            os.remove(p)

    run(DEV_A, "step_seed_a", "1. A: seed + sync (cloud terisi data A)")
    run(DEV_B, "step_seed_b", "2. B: seed standalone (id 1 tumpang tindih, updated_at non-NULL)")
    run(DEV_B, "step_sync", "3. B: sync dua arah -> tabrakan id diberi id cloud baru, A ditarik")
    run(DEV_A, "step_sync", "4. A: sync dua arah -> menarik data B (termasuk id hasil remap)")
    run(DEV_A, "step_lww_a", "5. A: edit person 1 'Andi A' @now+1m, push")
    run(DEV_B, "step_lww_b", "6. B: edit Andi lokal 'Andi B' @now+2m, push (lebih baru)")
    run(DEV_A, "step_lww_check", "7. A: sync -> harus MENARIK 'Andi B' (last-write-wins)")
    run(DEV_A, "step_del_a", "8. A: hapus INV-B1 + line, cloud ikut terhapus")
    run(DEV_B, "step_sync", "9. B: sync -> INV-B1 lokal ikut terhapus (delete dua arah)")
    run(DEV_A, "step_edit_b_row_a", "10. A: edit baris REMAP milik B (Orang B) @10:00, push")
    run(DEV_B, "step_pull_remapped", "11. B: sync -> MENARIK edit ke id lokalnya sendiri (uji lu remap, tanpa duplikat)")
    run(DEV_A, "step_del_remapped", "12. A: hapus Orang B lokal, cloud ikut terhapus")
    run(DEV_B, "step_resurrect", "13. B: edit Orang B @12:00 -> cloud dihidupkan kembali di id SAMA (uji resurrect)")
    run(DEV_A, "step_verify_resurrect", "14. A: sync -> menarik 'Orang B Edit B' dari cloud id 3")
    run(DEV_A, "step_owner_a", "15. A: buat person 100 'Identik' + 101 'Copy Lama' (owner DEVA), push")
    run(DEV_B, "step_owner_b", "16. B: buat KONTEN IDENTIK (100 owner DEVB) -> tabrakan; 101 owner NULL (salinan lama) -> identity")
    run(DEV_A, "step_owner_check", "17. A: sync -> menarik 'Identik' B tanpa duplikat")
    run(NONE, "step_final", "18. Verifikasi akhir: isi, FK cloud, pemetaan id, kepemilikan")

    print("\n>>> UJI E2E DUA PERANGKAT SELESAI <<<")


if __name__ == "__main__":
    main()
