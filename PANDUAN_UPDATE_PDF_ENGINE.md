# Panduan Setup: Update Format Invoice `pdf_engine.py`

**Tujuan:** Mengubah tampilan invoice yang dihasilkan fungsi `generate_invoice_pdf()` di `app_essa/utils/pdf_engine.py` dari gaya lama ("ESSA STORE INVOICE" seperti contoh `INV-20260716_161707_Mbak_Iin.pdf`) menjadi gaya target ("Invoice" dua-kolom seperti contoh `Invoice_INV_0002.pdf`).

---

## 0. Temuan Penting Sebelum Mulai

Saya sudah membaca kode `pdf_engine.py` yang kamu upload. Ada beberapa hal yang **AI agent kamu wajib tahu dulu** sebelum mengedit, karena tidak sesederhana "ganti tampilan":

1. **Fungsi yang harus diubah cuma satu:** `generate_invoice_pdf()`, mulai baris **598** sampai **933**. Fungsi lain (`generate_batch_karyawan_slip`, `generate_batch_receipt_pdf`) **jangan disentuh** — itu untuk slip gaji & nota pembayaran, bukan invoice.

2. **Kode ini sudah setengah jalan diubah, dan ada bug.** Docstring fungsi ini bahkan sudah menulis "mengacu Invoice_INV_0002.pdf", tapi hasil sebenarnya (lihat file `INV-20260716_161707_Mbak_Iin.pdf` yang kamu upload — nomor invoice-nya `INV-20260716_161707` cocok persis dengan pola `f"INV-{timestamp}"` di baris 640, jadi PDF itu memang dibuat oleh fungsi ini) masih menampilkan gaya lama. Yang lebih parah:
   - Di baris 673–680, variabel `company_lines` (harusnya alamat **ESSA HIJAB sendiri**) **isinya malah alamat klien JM FASHION** yang ter-hardcode dari sample. Ini **bug**, harus diperbaiki terlepas dari urusan format.
   - Bagian tabel, ringkasan, "Rincian Piutang", dan footer instruksi pembayaran masih pakai struktur & data gaya lama (piutang berjalan), bukan gaya sederhana di `Invoice_INV_0002.pdf`.

3. **Keterbatasan data yang tersedia saat ini** (penting supaya AI agent tidak mengarang data):
   - Klien cuma direpresentasikan sebagai `nama_klien` (string biasa). **Tidak ada field** alamat perusahaan klien, telepon klien, atau nama PIC ("Up: ..."), padahal itu ada di contoh `Invoice_INV_0002.pdf`.
   - Item produk cuma punya `item.sku.kode_sku` (nama SKU). **Tidak ada field "Deskripsi" terpisah** dari nama produk, padahal tabel target punya kolom `Produk` DAN `Deskripsi` secara terpisah.
   - **Tidak ada asset logo** (gambar bunga "ESSA Store") di manapun dalam kode ini.
   
   → Lihat Bagian 4 untuk pilihan cara menangani ini.

---

## 1. Perbandingan Format (Lama vs Target)

| Bagian | Format Lama (Mbak Iin) | Format Target (INV_0002 / JM Fashion) | Status di kode saat ini |
|---|---|---|---|
| Judul | "ESSA STORE INVOICE" jadi satu baris judul | Logo grafis "ESSA Store" (kiri) + teks "Invoice" besar (kanan) | Belum sesuai — kode masih pakai "ESSA HIJAB" + "INVOICE" sejajar, tanpa logo |
| Info invoice | No. Ref & Tanggal langsung di bawah judul, rata kiri | "Nomor", "Tanggal", "Tgl. Jatuh Tempo" rata kanan di bawah judul "Invoice" | Sudah cukup dekat (baris 690–707) |
| Info penjual & pembeli | Satu baris "TAGIHAN KEPADA: Mbak Iin" saja, tanpa info toko | Dua kolom berlabel **"Informasi Perusahaan"** (alamat ESSA HIJAB) dan **"Tagihan Kepada"** (nama + alamat + telp + PIC klien) berdampingan | **Belum ada** — ini bagian paling besar yang perlu dibangun ulang |
| Tabel item | Kolom: No, Deskripsi Barang, Qty, Harga Satuan, Total | Kolom: Produk, Deskripsi, Kuantitas, Harga, Jumlah | Belum sesuai — kode masih pakai No, Produk, Kuantitas, Harga, Jumlah (tanpa Deskripsi) |
| Warna header tabel | Tidak ada warna (teks polos) | Fill warna navy gelap, teks putih | Kode sudah pakai fill biru (baris 739: `BLUE = (33,150,243)`), tapi nuansanya lebih terang/cerah dibanding navy gelap di target — perlu disesuaikan |
| Ringkasan | Sisa Hutang Sebelumnya → Total Transaksi Baru → Subtotal (Sisa Piutang) → Deposit → Sisa Hutang Baru | Subtotal → Total → Sisa Tagihan (sederhana, 3 baris) | Kode sudah punya versi sederhana (Subtotal/Total/Sisa Tagihan, baris 822–832) **dan** versi piutang berjalan (baris 834–890) — keduanya perlu dipertahankan tapi lihat catatan di Bagian 3.E |
| Terbilang | Tidak ada | Ada, di bawah ringkasan | Kode sudah ada (baris 796–805) ✅ sesuai |
| Instruksi pembayaran | Ada (nomor rekening BRI) | Tidak muncul di sample (mungkin karena contoh lunas/transaksi awal) | Kode sudah ada (baris 913–920) — **pertahankan**, ini info penting untuk bisnis meskipun tidak muncul di 1 contoh |
| Tanda tangan | Tidak ada | "Dengan Hormat," + "ESSA HIJAB" di tengah bawah | Kode sudah ada (baris 922–929) ✅ sesuai |

---

## 2. Rencana Perubahan per Bagian

### A. Header atas (baris ±663–713)
- **Ganti** baris judul "ESSA HIJAB" (besar, biru) sejajar "INVOICE" (kanan) dengan:
  - **Kiri:** logo gambar (lihat Bagian 4, opsi logo). Jika logo belum tersedia, sebagai fallback sementara boleh pakai teks "ESSA Store" bergaya (bukan "ESSA HIJAB" polos), tapi tandai ini sebagai **TODO ganti logo asli**.
  - **Kanan:** teks "Invoice" (besar, bold, warna aksen — boleh pakai `BLUE` yang sudah ada), lalu di bawahnya baris `Nomor` / `Tanggal` / `Tgl. Jatuh Tempo` rata kanan — bagian ini sudah ada di kode (baris 690–707), **cukup dipertahankan**, hanya posisinya menyesuaikan tinggi logo baru.

### B. Blok "Informasi Perusahaan" & "Tagihan Kepada" (baris ±715–725, dibangun ulang)
Ini pengganti section "TAGIHAN KEPADA" yang sekarang cuma 1 baris nama klien. Buat 2 kolom sejajar (mirip pola `pdf.set_xy()` yang sudah dipakai di baris 697 untuk kolom kanan):

- **Kolom kiri — "Informasi Perusahaan":**
  - Label kecil "Informasi Perusahaan" (abu-abu, sesuai gaya `GRAY` yang sudah ada)
  - Nama toko **"ESSA HIJAB"** (bold, `BLUE`)
  - Alamat asli toko: `Pendosawalan 16/06, Kec. Kalinyamatan, Jepara` *(catatan: contoh lama tulis "16/06", contoh target tulis "16/05" — user perlu konfirmasi mana yang benar sebelum AI agent isi hardcode)*
  - Telp: `0895426950709` (dan boleh tambah `08888169421` seperti di invoice lama jika kedua nomor relevan)
  - Email jika ada (di sample target ada `achmadfais0909@gmail.com` — konfirmasi apakah email ini masih dipakai)
  
  Ini **memperbaiki bug** `company_lines` yang sekarang salah isi data klien.

- **Kolom kanan — "Tagihan Kepada":**
  - Label kecil "Tagihan Kepada" (abu-abu)
  - Nama klien: `nama_klien` (bold) — data ini **sudah tersedia** dari parameter fungsi
  - Alamat / Telp / Up (PIC) klien: **field ini belum ada di data yang dikirim ke fungsi.** Buat baris-baris ini **kondisional** — hanya tampil jika datanya ada, supaya untuk klien seperti "Mbak Iin" yang cuma punya nama, layout tidak menampilkan baris kosong yang aneh. (Lihat Bagian 4 opsi A/B.)

### C. Tabel item (baris ±727–793)
- Ubah definisi kolom dari `No | Produk | Kuantitas | Harga | Jumlah` menjadi `Produk | Deskripsi | Kuantitas | Harga | Jumlah` (drop kolom "No", tambah kolom "Deskripsi").
  - Saran lebar kolom (total tetap 190mm sesuai `W` yang sudah didefinisikan): `Produk=50, Deskripsi=50, Kuantitas=25, Harga=30, Jumlah=35`. Ini cuma saran awal — sesuaikan lagi kalau nama produk sering panjang (bisnis ini banyak SKU dengan nama warna panjang seperti "JSO-Cokelat Tua", "JSO-Dusty Pink").
  - **Isi kolom "Deskripsi" perlu diputuskan** (lihat Bagian 4 opsi C) karena `item.sku.kode_sku` saat ini cuma 1 field.
- Ganti warna fill header tabel dari biru cerah (`BLUE = (33,150,243)`) ke **navy gelap** agar mendekati contoh target (mis. `NAVY = (30, 41, 74)` — ini estimasi visual, minta AI agent cek ulang warna asli dari gambar `Invoice_INV_0002.pdf` kalau butuh presisi, bisa pakai color picker pada file gambarnya).
- Logic page-break (baris 764–776, header tabel diulang di halaman baru) **sudah bagus, pertahankan** — jangan dihapus, ini penting karena invoice ESSA Store bisa punya puluhan baris item (lihat contoh Mbak Iin, 27 item).

### D. Ringkasan finansial sederhana (baris ±807–832)
Bagian `Subtotal / Total / Sisa Tagihan` ini **sudah sesuai** dengan target, tidak perlu dirombak — cukup dirapikan spacing/warnanya kalau perlu menyesuaikan estetika baru.

### E. "Rincian Piutang" (baris ±834–890) — **JANGAN DIHAPUS**
Section ini (Sisa Hutang Sebelumnya, Total Transaksi Baru, Deposit, Sisa Hutang Baru) **tidak muncul** di contoh `Invoice_INV_0002.pdf` — tapi itu kemungkinan besar karena transaksi JM FASHION di contoh itu adalah transaksi pertama/lunas, bukan karena fitur ini harus dihapus. Section ini sudah **kondisional** (baris 835: `if abs(sisa_piutang - total_tagihan) > 100 or deposit > 0:`), jadi otomatis akan sembunyi sendiri untuk kasus seperti JM FASHION dan tetap muncul untuk klien reseller berulang seperti Mbak Iin.

→ **Instruksikan AI agent untuk mempertahankan logic ini, cuma ubah stylingnya** (warna, jarak, font) supaya konsisten dengan estetika baru yang lebih rapi.

### F. Terbilang (baris ±795–805) & Footer (baris ±893–929)
Kedua bagian ini **sudah sesuai** dengan gaya target secara struktur. Cukup pastikan warna/font-nya konsisten dengan perubahan di bagian lain.

---

## 3. Keputusan yang Perlu Kamu Ambil Dulu

Sebelum AI agent mulai coding, ada 3 hal yang sebaiknya kamu putuskan supaya hasilnya tidak asal tebak:

1. **Logo:** Apakah kamu punya file logo "ESSA Store" (PNG/JPG) yang bisa dipakai? Kalau ada, siapkan file-nya dan kasih tahu AI agent path-nya supaya bisa di-embed pakai `pdf.image()`. Kalau belum ada, minta AI agent pakai fallback teks dulu dan tandai TODO.

2. **Data klien (alamat/telp/PIC):** Untuk klien seperti "Mbak Iin" yang cuma punya nama, apakah kamu ingin:
   - **Opsi A:** Baris "Tagihan Kepada" tetap sesederhana sekarang (cuma nama) untuk klien tanpa data lengkap — kolom kanan otomatis lebih pendek dari kolom kiri, dan itu wajar.
   - **Opsi B:** Perluas fungsi `generate_invoice_pdf()` dengan parameter opsional baru (misal `alamat_klien=None, telp_klien=None, pic_klien=None`) supaya ke depannya bisa diisi kalau ada klien dengan data lengkap (seperti JM FASHION).
   
   → Saran saya: **Opsi B**, karena lebih fleksibel dan tidak mengubah perilaku untuk klien lama yang datanya minim (parameter opsional, default `None`, dan baris hanya dicetak kalau nilainya tidak `None`).

3. **Kolom "Deskripsi" di tabel:** Karena `item.sku.kode_sku` cuma 1 field, apakah:
   - **Opsi A:** Kolom "Deskripsi" dikosongkan/dihilangkan dulu (tabel tetap 4 kolom: Produk, Kuantitas, Harga, Jumlah) sampai ada field deskripsi di data model.
   - **Opsi B:** Pindahkan info tanggal transaksi (`[2026-07-06]` yang sekarang nempel di nama produk pada invoice lama) ke kolom "Deskripsi" terpisah, dan kolom "Produk" cuma isi nama SKU bersih.
   
   → Kalau data tanggal per item memang tersimpan di `item` (cek field seperti `item.tanggal` di model `PengeluaranOffline`), **Opsi B** paling mendekati kebutuhan asli dan tidak kehilangan informasi yang sudah ada di invoice lama.

---

## 4. Instruksi Siap-Pakai untuk AI Agent Coding Kamu

Kamu bisa copy-paste blok ini ke AI agent kamu sebagai instruksi kerja:

```
Edit fungsi generate_invoice_pdf() di app_essa/utils/pdf_engine.py (baris 598–933).
Jangan ubah fungsi lain di file ini.

1. Perbaiki bug: variabel company_lines (baris ~675-680) saat ini berisi alamat
   klien JM FASHION yang ter-hardcode dari file contoh. Ganti dengan alamat asli
   toko ESSA HIJAB: [ISI ALAMAT, TELP, EMAIL YANG BENAR DI SINI].

2. Ganti header atas: logo ESSA Store di kiri (pakai file [PATH LOGO] via pdf.image(),
   atau fallback teks jika file belum ada) + judul teks "Invoice" di kanan, dengan
   Nomor/Tanggal/Tgl. Jatuh Tempo rata kanan di bawahnya (logic yang sudah ada di
   baris 690-707 boleh dipertahankan, sesuaikan posisi Y saja).

3. Bangun ulang section "Tagihan Kepada" (baris ~715-725) menjadi dua kolom sejajar:
   - Kolom kiri berlabel "Informasi Perusahaan": nama & alamat ESSA HIJAB.
   - Kolom kanan berlabel "Tagihan Kepada": nama_klien (wajib ada), lalu alamat/
     telp/PIC klien HANYA jika parameter baru (alamat_klien, telp_klien, pic_klien
     - default None) diisi. Tambahkan parameter opsional ini ke signature fungsi.

4. Ubah tabel item (baris ~727-793): kolom jadi Produk | Deskripsi | Kuantitas |
   Harga | Jumlah (hapus kolom "No"). [ISI KEPUTUSAN OPSI A/B DARI BAGIAN 3.3 DI SINI
   untuk sumber data kolom Deskripsi]. Pertahankan logic page-break & ulang header
   tabel di halaman baru (baris 764-776) — jangan dihapus.

5. Ganti warna fill header tabel dari BLUE cerah ke warna navy gelap yang lebih
   mendekati referensi visual Invoice_INV_0002.pdf.

6. JANGAN hapus section "Rincian Piutang" (baris ~834-890) dan "Instruksi
   Pembayaran" (baris ~913-920) — keduanya tetap dipakai untuk bisnis piutang
   berjalan (reseller), cuma sesuaikan styling (warna/spacing) supaya konsisten
   dengan tampilan baru. Section ini sudah kondisional (hanya muncul kalau relevan),
   itu perilaku yang benar dan harus dipertahankan.

7. Bagian Terbilang (baris ~795-805) dan Tanda Tangan (baris ~922-929) sudah
   sesuai target — jangan diubah strukturnya, cukup selaraskan gaya visual saja.

8. Setelah selesai, generate 2 test case: (a) klien baru tanpa piutang sebelumnya
   dan tanpa data alamat/telp/PIC (mirip kasus JM FASHION), (b) klien reseller
   dengan piutang berjalan dan banyak item / lebih dari 1 halaman (mirip kasus
   Mbak Iin, 27 item) — pastikan keduanya render dengan benar.
```

---

## 5. Checklist Sebelum Dianggap Selesai

- [ ] Alamat & kontak ESSA HIJAB di header sudah benar (bukan lagi alamat klien)
- [ ] Logo tampil (atau fallback teks jelas ditandai TODO)
- [ ] Section "Informasi Perusahaan" & "Tagihan Kepada" tampil berdampingan
- [ ] Klien tanpa data alamat/telp/PIC tetap tampil rapi (tidak ada baris kosong aneh)
- [ ] Tabel item punya kolom Deskripsi, tanpa kolom No
- [ ] Invoice dengan banyak item (test dengan ≥27 baris) tetap pindah halaman dengan benar, header tabel terulang
- [ ] Section Rincian Piutang tetap muncul untuk klien dengan piutang berjalan, dan tetap tersembunyi untuk transaksi bersih/pertama
- [ ] Instruksi pembayaran & tanda tangan tetap ada di semua invoice
- [ ] Warna & font konsisten di seluruh halaman
