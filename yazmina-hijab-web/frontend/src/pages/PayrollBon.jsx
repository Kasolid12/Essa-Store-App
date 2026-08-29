/**
 * Yazmina Hijab Web — Payroll & Bon Page.
 *
 * 4 Tabs matching desktop app:
 * 1. GAJI PENJAHIT — manual line items + import Excel
 * 2. TOTALAN PENGSUP — reconciliation + import Excel
 * 3. GAJI KARYAWAN (ABSENSI) — import Excel fingerprint, editable grid, batch submit
 * 4. KASBON / UTANG — bon balances + movements
 */

import React, { useState, useEffect, useCallback, useRef } from 'react'
import { api } from '../api/client'
import Modal from '../components/Modal'

// ── Helpers ──────────────────────────────────────────────────────────

function formatRp(val) {
  if (!val || val === 0) return 'Rp 0'
  return 'Rp ' + Number(val).toLocaleString('id-ID')
}

function today() {
  return new Date().toISOString().slice(0, 10)
}

// ══════════════════════════════════════════════════════════════════════
// TAB 1: GAJI PENJAHIT
// ══════════════════════════════════════════════════════════════════════

function GajiPenjahitTab() {
  const [workers, setWorkers] = useState([])
  const [skus, setSkus] = useState([])
  const [cart, setCart] = useState([])
  const [loading, setLoading] = useState(true)
  const [form, setForm] = useState({
    person_id: '', tanggal: today(), tambah_bon: 0, potong_bon: 0,
  })
  const [bonLama, setBonLama] = useState(0)
  const [items, setItems] = useState([])
  const [showHistory, setShowHistory] = useState(false)
  const fileRef = useRef(null)

  useEffect(() => {
    Promise.all([
      api.listPersons({ person_type: 'PENJAHIT' }),
      api.listSku(),
    ]).then(([p, s]) => {
      setWorkers(p)
      setSkus(s)
    }).finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    if (form.person_id) {
      api.getBonLama(form.person_id).then(r => setBonLama(r.bon_lama)).catch(() => setBonLama(0))
    }
  }, [form.person_id])

  useEffect(() => {
    api.listGaji({ tipe: 'BORONGAN_PENJAHIT' }).then(setItems).catch(() => setItems([]))
  }, [])

  const addLine = () => {
    setCart([...cart, { sku_id: '', model_code: '', qty: 1, tarif_per_pcs: 0 }])
  }

  const updateLine = (idx, field, val) => {
    const next = [...cart]
    next[idx] = { ...next[idx], [field]: val }
    setCart(next)
  }

  const removeLine = (idx) => {
    setCart(cart.filter((_, i) => i !== idx))
  }

  const gajiKotor = cart.reduce((s, l) => s + (l.qty * l.tarif_per_pcs), 0)
  const gajiBersih = gajiKotor - (form.potong_bon || 0)
  const sisaBonAkhir = bonLama + (form.tambah_bon || 0) - (form.potong_bon || 0)

  const handleImport = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    try {
      const res = await api.importExcelPenjahit(file)
      const newItems = res.items.map(it => ({
        sku_id: it.sku_id || '',
        model_code: it.nama_garapan,
        qty: it.qty,
        tarif_per_pcs: it.harga,
      }))
      setCart([...cart, ...newItems])
    } catch (err) {
      alert('Error import: ' + err.message)
    }
    e.target.value = ''
  }

  const handleSave = async () => {
    if (!form.person_id || cart.length === 0) return alert('Pilih penjahit & minimal 1 garapan')
    try {
      await api.createGaji({
        tipe: 'BORONGAN_PENJAHIT',
        person_id: Number(form.person_id),
        tanggal_proses: form.tanggal,
        tambah_bon: form.tambah_bon,
        potong_bon: form.potong_bon,
        line_items: cart.map(l => ({
          sku_id: l.sku_id ? Number(l.sku_id) : null,
          model_code: l.model_code,
          qty: l.qty,
          tarif_per_pcs: l.tarif_per_pcs,
        })),
      })
      setCart([])
      setForm(f => ({ ...f, tambah_bon: 0, potong_bon: 0 }))
      api.listGaji({ tipe: 'BORONGAN_PENJAHIT' }).then(setItems)
      alert('Gaji penjahit berhasil disimpan!')
    } catch (err) {
      alert('Error: ' + err.message)
    }
  }

  const handleDelete = async (id) => {
    if (!confirm('Hapus data gaji ini?')) return
    await api.deleteGaji(id)
    setItems(items.filter(i => i.id !== id))
  }

  return (
    <div>
      {/* KPI Cards */}
      <div className="kpi-grid" style={{ gridTemplateColumns: 'repeat(4, 1fr)', marginBottom: 16 }}>
        <div className="kpi-card">
          <div className="kpi-label">Sisa Bon Lama</div>
          <div className="kpi-value text-pink">{formatRp(bonLama)}</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-label">+ Tambah Bon</div>
          <div className="kpi-value text-cyan">{formatRp(form.tambah_bon)}</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-label">- Potong Bon</div>
          <div className="kpi-value text-red">{formatRp(form.potong_bon)}</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-label">Gaji Bersih</div>
          <div className="kpi-value text-green">{formatRp(gajiBersih)}</div>
        </div>
      </div>

      {/* Form */}
      <div className="form-grid" style={{ marginBottom: 16 }}>
        <div className="form-group">
          <label>Penjahit</label>
          <select className="input" value={form.person_id} onChange={e => setForm({ ...form, person_id: e.target.value })}>
            <option value="">-- Pilih --</option>
            {workers.map(w => <option key={w.id} value={w.id}>{w.nama}</option>)}
          </select>
        </div>
        <div className="form-group">
          <label>Tanggal</label>
          <input className="input" type="date" value={form.tanggal} onChange={e => setForm({ ...form, tanggal: e.target.value })} />
        </div>
        <div className="form-group">
          <label>+ Tambah Bon</label>
          <input className="input" type="number" min="0" value={form.tambah_bon} onChange={e => setForm({ ...form, tambah_bon: Number(e.target.value) })} />
        </div>
        <div className="form-group">
          <label>- Potong Bon</label>
          <input className="input" type="number" min="0" max={bonLama} value={form.potong_bon} onChange={e => setForm({ ...form, potong_bon: Number(e.target.value) })} />
        </div>
      </div>

      {/* Import + Add */}
      <div className="table-toolbar" style={{ marginBottom: 12 }}>
        <button className="btn btn-solid" onClick={addLine}>+ Tambah Garapan</button>
        <input type="file" ref={fileRef} accept=".xlsx,.xls,.csv" style={{ display: 'none' }} onChange={handleImport} />
        <button className="btn btn-ghost" onClick={() => fileRef.current?.click()}>Import Excel</button>
      </div>

      {/* Cart Table */}
      {cart.length > 0 && (
        <div className="panel mb-16">
          <div className="table-container">
            <table className="data-table">
              <thead>
                <tr><th style={{ width: 48 }}>No</th><th>Garapan/SKU</th><th style={{ width: 90 }}>Qty</th><th style={{ width: 120 }}>Harga/Pcs</th><th style={{ width: 130 }}>Total</th><th style={{ width: 60 }}></th></tr>
              </thead>
              <tbody>
                {cart.map((line, i) => (
                  <tr key={i}>
                    <td className="text-muted">{i + 1}</td>
                    <td>
                      <input className="input" value={line.model_code} onChange={e => updateLine(i, 'model_code', e.target.value)} style={{ width: '100%' }} />
                    </td>
                    <td>
                      <input className="input" type="number" min="1" value={line.qty} onChange={e => updateLine(i, 'qty', Number(e.target.value))} style={{ width: 80 }} />
                    </td>
                    <td>
                      <input className="input" type="number" min="0" value={line.tarif_per_pcs} onChange={e => updateLine(i, 'tarif_per_pcs', Number(e.target.value))} style={{ width: 120 }} />
                    </td>
                    <td className="text-green font-mono">{formatRp(line.qty * line.tarif_per_pcs)}</td>
                    <td><button className="btn btn-danger btn-sm" onClick={() => removeLine(i)}>X</button></td>
                  </tr>
                ))}
              </tbody>
              <tfoot>
                <tr>
                  <td colSpan={4} style={{ textAlign: 'right', fontWeight: 'bold' }}>TOTAL:</td>
                  <td className="text-green font-mono" style={{ fontWeight: 'bold' }}>{formatRp(gajiKotor)}</td>
                  <td></td>
                </tr>
              </tfoot>
            </table>
          </div>
        </div>
      )}

      <button className="btn btn-solid" onClick={handleSave} disabled={!form.person_id || cart.length === 0}
        style={{ padding: '12px 32px' }}>
        Simpan &amp; Cetak
      </button>

      {/* History */}
      <div className="mt-16">
        <button className="tab" style={{ color: 'var(--neon-cyan)', cursor: 'pointer' }}
          onClick={() => setShowHistory(!showHistory)}>
          {showHistory ? '▼' : '▶'} Riwayat Gaji Penjahit
        </button>
        {showHistory && (
          <div className="panel" style={{ marginTop: 8 }}>
            <div className="table-container">
              <table className="data-table">
                <thead>
                  <tr><th>Tanggal</th><th>Penjahit</th><th>Gaji Kotor</th><th>Potong Bon</th><th>Gaji Bersih</th><th style={{ width: 80 }}></th></tr>
                </thead>
                <tbody>
                  {items.map(it => (
                    <tr key={it.id}>
                      <td>{it.tanggal_proses}</td>
                      <td>{it.person_nama}</td>
                      <td className="font-mono">{formatRp(it.gaji_kotor)}</td>
                      <td className="font-mono">{formatRp(it.potong_bon)}</td>
                      <td className="text-green font-mono" style={{ fontWeight: 'bold' }}>{formatRp(it.gaji_bersih)}</td>
                      <td><button className="btn btn-danger btn-sm" onClick={() => handleDelete(it.id)}>Hapus</button></td>
                    </tr>
                  ))}
                  {items.length === 0 && <tr><td colSpan={6} className="text-muted" style={{ textAlign: 'center', padding: 24 }}>Belum ada data</td></tr>}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}


// ══════════════════════════════════════════════════════════════════════
// TAB 2: TOTALAN PENGSUP
// ══════════════════════════════════════════════════════════════════════

function TotalanPengsupTab() {
  const [workers, setWorkers] = useState([])
  const [skus, setSkus] = useState([])
  const [cart, setCart] = useState([])
  const [loading, setLoading] = useState(true)
  const [form, setForm] = useState({
    person_id: '', tanggal: today(), tambah_bon: 0, potong_bon: 0,
    kain_qty: 0, kain_harga: 0,
  })
  const [bonLama, setBonLama] = useState(0)
  const [items, setItems] = useState([])
  const [showHistory, setShowHistory] = useState(false)
  const fileRef = useRef(null)

  useEffect(() => {
    Promise.all([
      api.listPersons({ person_type: 'SUPPLIER' }),
      api.listSku(),
    ]).then(([p, s]) => { setWorkers(p); setSkus(s) })
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    if (form.person_id) {
      api.getBonLama(form.person_id).then(r => setBonLama(r.bon_lama)).catch(() => setBonLama(0))
    }
  }, [form.person_id])

  useEffect(() => {
    api.listGaji({ tipe: 'PENGSUP' }).then(setItems).catch(() => setItems([]))
  }, [])

  const addLine = () => {
    setCart([...cart, { tipe: 'Setor Barang Jadi (Kain)', sku_kode: '', qty: 0, harga: 0 }])
  }
  const updateLine = (i, f, v) => { const n = [...cart]; n[i] = { ...n[i], [f]: v }; setCart(n) }
  const removeLine = (i) => setCart(cart.filter((_, idx) => idx !== i))

  const totalPemasukan = cart.reduce((s, l) => s + l.qty * l.harga, 0)
  const kainTotal = form.kain_qty * form.kain_harga
  const gajiKotor = totalPemasukan - kainTotal
  const gajiBersih = gajiKotor - (form.potong_bon || 0)

  const handleImport = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    try {
      const res = await api.importExcelPengsup(file)
      setCart(res.items.map(it => ({
        tipe: it.tipe, sku_kode: it.sku_kode, qty: it.qty, harga: it.harga, nama_garapan: it.nama_garapan,
      })))
      setForm(f => ({
        ...f,
        kain_qty: res.kain_qty || 0,
        kain_harga: res.kain_harga || 0,
        tambah_bon: res.tambah_bon || 0,
        potong_bon: res.potong_bon || 0,
      }))
    } catch (err) {
      alert('Error import: ' + err.message)
    }
    e.target.value = ''
  }

  const handleSave = async () => {
    if (!form.person_id || cart.length === 0) return alert('Pilih pengsup & pastikan data ada')
    try {
      const lineItems = []

      // Kain mentah as negative item
      if (kainTotal > 0) {
        lineItems.push({ model_code: '[KAIN_MENTAH]', qty: form.kain_qty, tarif_per_pcs: form.kain_harga })
      }

      for (const l of cart) {
        const prefix = l.tipe?.includes('Potongan') ? '[POTONG] ' : '[BARANG] '
        lineItems.push({
          model_code: prefix + (l.nama_garapan || l.sku_kode),
          qty: l.qty,
          tarif_per_pcs: l.harga,
        })
      }

      await api.createGaji({
        tipe: 'PENGSUP',
        person_id: Number(form.person_id),
        tanggal_proses: form.tanggal,
        tambah_bon: form.tambah_bon,
        potong_bon: form.potong_bon,
        line_items: lineItems,
      })
      setCart([])
      setForm(f => ({ ...f, tambah_bon: 0, potong_bon: 0, kain_qty: 0, kain_harga: 0 }))
      api.listGaji({ tipe: 'PENGSUP' }).then(setItems)
      alert('Data pengsup berhasil disimpan!')
    } catch (err) { alert('Error: ' + err.message) }
  }

  return (
    <div>
      {/* KPI */}
      <div className="kpi-grid" style={{ gridTemplateColumns: 'repeat(4, 1fr)', marginBottom: 16 }}>
        <div className="kpi-card">
          <div className="kpi-label">Total Pemasukan</div>
          <div className="kpi-value text-cyan">{formatRp(totalPemasukan)}</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-label">- Kain Mentah</div>
          <div className="kpi-value text-red">-{formatRp(kainTotal)}</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-label">Gaji Kotor</div>
          <div className="kpi-value text-yellow">{formatRp(gajiKotor)}</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-label">Gaji Bersih</div>
          <div className="kpi-value text-green">{formatRp(gajiBersih)}</div>
        </div>
      </div>

      {/* Form */}
      <div className="form-grid" style={{ marginBottom: 16 }}>
        <div className="form-group">
          <label>Pengsup</label>
          <select className="input" value={form.person_id} onChange={e => setForm({ ...form, person_id: e.target.value })}>
            <option value="">-- Pilih --</option>
            {workers.map(w => <option key={w.id} value={w.id}>{w.nama}</option>)}
          </select>
        </div>
        <div className="form-group">
          <label>Tanggal</label>
          <input className="input" type="date" value={form.tanggal} onChange={e => setForm({ ...form, tanggal: e.target.value })} />
        </div>
        <div className="form-group">
          <label>Kain Qty</label>
          <input className="input" type="number" min="0" value={form.kain_qty} onChange={e => setForm({ ...form, kain_qty: Number(e.target.value) })} />
        </div>
        <div className="form-group">
          <label>Kain Harga/Unit</label>
          <input className="input" type="number" min="0" value={form.kain_harga} onChange={e => setForm({ ...form, kain_harga: Number(e.target.value) })} />
        </div>
        <div className="form-group">
          <label>+ Tambah Bon</label>
          <input className="input" type="number" min="0" value={form.tambah_bon} onChange={e => setForm({ ...form, tambah_bon: Number(e.target.value) })} />
        </div>
        <div className="form-group">
          <label>- Potong Bon</label>
          <input className="input" type="number" min="0" value={form.potong_bon} onChange={e => setForm({ ...form, potong_bon: Number(e.target.value) })} />
        </div>
      </div>

      <div className="table-toolbar" style={{ marginBottom: 12 }}>
        <button className="btn btn-solid" onClick={addLine}>+ Tambah Item</button>
        <input type="file" ref={fileRef} accept=".xlsx,.xls" style={{ display: 'none' }} onChange={handleImport} />
        <button className="btn btn-ghost" onClick={() => fileRef.current?.click()}>Import Excel</button>
      </div>

      {cart.length > 0 && (
        <div className="panel mb-16">
          <div className="table-container">
            <table className="data-table">
              <thead>
                <tr><th style={{ width: 48 }}>No</th><th>Nama/SKU</th><th style={{ width: 90 }}>Qty</th><th style={{ width: 120 }}>Harga</th><th style={{ width: 130 }}>Total</th><th style={{ width: 120 }}>Tipe</th><th style={{ width: 60 }}></th></tr>
              </thead>
              <tbody>
                {cart.map((l, i) => (
                  <tr key={i}>
                    <td className="text-muted">{i + 1}</td>
                    <td><input className="input" value={l.nama_garapan || l.sku_kode} onChange={e => updateLine(i, 'sku_kode', e.target.value)} style={{ width: '100%' }} /></td>
                    <td><input className="input" type="number" min="0" value={l.qty} onChange={e => updateLine(i, 'qty', Number(e.target.value))} style={{ width: 80 }} /></td>
                    <td><input className="input" type="number" min="0" value={l.harga} onChange={e => updateLine(i, 'harga', Number(e.target.value))} style={{ width: 120 }} /></td>
                    <td className="text-green font-mono">{formatRp(l.qty * l.harga)}</td>
                    <td><span className="badge badge-cyan">{l.tipe}</span></td>
                    <td><button className="btn btn-danger btn-sm" onClick={() => removeLine(i)}>X</button></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      <button className="btn btn-solid" onClick={handleSave} disabled={!form.person_id || cart.length === 0}
        style={{ padding: '12px 32px' }}>
        Simpan
      </button>

      <div className="mt-16">
        <button className="tab" style={{ color: 'var(--neon-cyan)', cursor: 'pointer' }}
          onClick={() => setShowHistory(!showHistory)}>
          {showHistory ? '▼' : '▶'} Riwayat Totalan Pengsup
        </button>
        {showHistory && (
          <div className="panel" style={{ marginTop: 8 }}>
            <div className="table-container">
              <table className="data-table">
                <thead><tr><th>Tanggal</th><th>Pengsup</th><th>Gaji Kotor</th><th>Gaji Bersih</th><th style={{ width: 80 }}></th></tr></thead>
                <tbody>
                  {items.map(it => (
                    <tr key={it.id}>
                      <td>{it.tanggal_proses}</td>
                      <td>{it.person_nama}</td>
                      <td className="font-mono">{formatRp(it.gaji_kotor)}</td>
                      <td className="text-green font-mono" style={{ fontWeight: 'bold' }}>{formatRp(it.gaji_bersih)}</td>
                      <td><button className="btn btn-danger btn-sm" onClick={async () => { await api.deleteGaji(it.id); setItems(items.filter(x => x.id !== it.id)) }}>Hapus</button></td>
                    </tr>
                  ))}
                  {items.length === 0 && <tr><td colSpan={5} className="text-muted" style={{ textAlign: 'center', padding: 24 }}>Belum ada data</td></tr>}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}


// ══════════════════════════════════════════════════════════════════════
// TAB 3: GAJI KARYAWAN (ABSENSI)
// ══════════════════════════════════════════════════════════════════════

function GajiKaryawanTab() {
  const [karyawan, setKaryawan] = useState([])
  const [loading, setLoading] = useState(true)
  const [fileActive, setFileActive] = useState('')
  const [tarifNormal, setTarifNormal] = useState(140)
  const [tarifLembur, setTarifLembur] = useState(160)
  const [tanggal, setTanggal] = useState(today())
  const [editingIdx, setEditingIdx] = useState(null)
  const [editorData, setEditorData] = useState(null)
  const fileRef = useRef(null)

  // Grand totals
  const grandKotor = karyawan.reduce((s, k) => s + k.gaji_kotor, 0)
  const grandPotong = karyawan.reduce((s, k) => s + k.potong_bon, 0)
  const grandBersih = karyawan.reduce((s, k) => s + k.gaji_bersih, 0)

  useEffect(() => {
    // Load karyawan list from persons
    api.listPersons({ person_type: 'KARYAWAN' }).then(persons => {
      // Get bon balances
      api.listBonBalances().then(balances => {
        const balMap = {}
        balances.forEach(b => { balMap[b.person_id] = b.saldo })

        setKaryawan(persons.map(p => ({
          person_id: p.id,
          nama: p.nama,
          emp_id: '',
          hadir: 0,
          menit_normal: 0,
          tarif_normal: tarifNormal,
          menit_lembur: 0,
          tarif_lembur: tarifLembur,
          gaji_kotor: 0,
          bon_lama: balMap[p.id] || 0,
          potong_bon: 0,
          gaji_bersih: 0,
          daily_records: [],
        })))
      }).catch(() => {
        setKaryawan(persons.map(p => ({
          person_id: p.id, nama: p.nama, emp_id: '', hadir: 0,
          menit_normal: 0, tarif_normal: tarifNormal, menit_lembur: 0,
          tarif_lembur: tarifLembur, gaji_kotor: 0, bon_lama: 0,
          potong_bon: 0, gaji_bersih: 0, daily_records: [],
        })))
      }).finally(() => setLoading(false))
    }).catch(() => setLoading(false))
  }, [])

  // Handle Excel import
  const handleImport = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    setFileActive(file.name)
    try {
      const res = await api.importAbsensi(file)
      setKaryawan(res.karyawan)
    } catch (err) {
      alert('Error import: ' + err.message)
    }
    e.target.value = ''
  }

  // Update a karyawan row
  const updateK = (idx, field, val) => {
    const next = [...karyawan]
    next[idx] = { ...next[idx], [field]: val }
    // Recalculate
    const k = next[idx]
    k.gaji_kotor = (k.menit_normal * k.tarif_normal) + (k.menit_lembur * k.tarif_lembur)
    k.potong_bon = Math.min(k.bon_lama, k.gaji_kotor)
    k.gaji_bersih = k.gaji_kotor - k.potong_bon
    setKaryawan(next)
  }

  // Open editor for daily records
  const openEditor = (idx) => {
    setEditingIdx(idx)
    setEditorData({ ...karyawan[idx] })
  }

  const handleEditorSave = (updated) => {
    const next = [...karyawan]
    next[editingIdx] = { ...next[editingIdx], ...updated }
    const k = next[editingIdx]
    k.gaji_kotor = (k.menit_normal * k.tarif_normal) + (k.menit_lembur * k.tarif_lembur)
    k.potong_bon = Math.min(k.bon_lama, k.gaji_kotor)
    k.gaji_bersih = k.gaji_kotor - k.potong_bon
    setKaryawan(next)
    setEditingIdx(null)
    setEditorData(null)
  }

  // Batch save
  const handleSaveAll = async () => {
    const valid = karyawan.filter(k => k.menit_normal > 0 || k.menit_lembur > 0)
    if (valid.length === 0) return alert('Tidak ada data karyawan yang valid')
    try {
      await api.savePasukan({
        tanggal_proses: tanggal,
        tarif_normal: tarifNormal,
        tarif_lembur: tarifLembur,
        karyawan: valid,
      })
      alert(`${valid.length} data gaji karyawan berhasil disimpan!`)
    } catch (err) { alert('Error: ' + err.message) }
  }

  if (loading) return <div className="text-muted" style={{ padding: 32, textAlign: 'center' }}>Memuat data karyawan...</div>

  return (
    <div>
      {/* Header Controls */}
      <div className="table-toolbar" style={{ marginBottom: 16 }}>
        <div className="form-group">
          <label>Tanggal Proses</label>
          <input className="input" type="date" value={tanggal} onChange={e => setTanggal(e.target.value)} style={{ maxWidth: 180 }} />
        </div>
        <div className="form-group">
          <label>Tarif Normal (/mnt)</label>
          <input className="input" type="number" min="0" value={tarifNormal} onChange={e => setTarifNormal(Number(e.target.value))} style={{ width: 100 }} />
        </div>
        <div className="form-group">
          <label>Tarif Lembur (/mnt)</label>
          <input className="input" type="number" min="0" value={tarifLembur} onChange={e => setTarifLembur(Number(e.target.value))} style={{ width: 100 }} />
        </div>
        <input type="file" ref={fileRef} accept=".xlsx,.xls" style={{ display: 'none' }} onChange={handleImport} />
        <button className="btn btn-solid-yellow" onClick={() => fileRef.current?.click()}>Import Absensi Excel</button>
        {fileActive && <span className="text-cyan" style={{ fontSize: 12 }}>File: {fileActive}</span>}
      </div>

      {/* KPI */}
      <div className="kpi-grid" style={{ gridTemplateColumns: 'repeat(3, 1fr)', marginBottom: 16 }}>
        <div className="kpi-card">
          <div className="kpi-label">Total Gaji Kotor</div>
          <div className="kpi-value text-yellow">{formatRp(grandKotor)}</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-label">Total Potong Bon</div>
          <div className="kpi-value text-red">{formatRp(grandPotong)}</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-label">Total Gaji Bersih</div>
          <div className="kpi-value text-green">{formatRp(grandBersih)}</div>
        </div>
      </div>

      {/* Main Table */}
      <div className="panel">
        <div className="table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th style={{ width: 40 }}>#</th>
                <th>Nama Karyawan</th>
                <th style={{ width: 60 }}>Hadir</th>
                <th style={{ width: 90 }}>Menit Normal</th>
                <th style={{ width: 90 }}>Tarif Normal</th>
                <th style={{ width: 90 }}>Menit Lembur</th>
                <th style={{ width: 90 }}>Tarif Lembur</th>
                <th style={{ width: 120 }}>Gaji Kotor</th>
                <th style={{ width: 100 }}>Bon Lama</th>
                <th style={{ width: 90 }}>Potong</th>
                <th style={{ width: 120 }}>Gaji Bersih</th>
                <th style={{ width: 50 }}></th>
              </tr>
            </thead>
            <tbody>
              {karyawan.map((k, i) => (
                <tr key={k.person_id} style={k.gaji_bersih === 0 && k.gaji_kotor > 0 ? { opacity: 0.5 } : {}}>
                  <td className="text-muted">{i + 1}</td>
                  <td style={{ fontWeight: 'bold' }}>{k.nama}</td>
                  <td style={{ textAlign: 'center' }}>{k.hadir}</td>
                  <td>
                    <input className="input" type="number" min="0" value={k.menit_normal}
                      onChange={e => updateK(i, 'menit_normal', Number(e.target.value))}
                      style={{ width: 70, textAlign: 'center' }} />
                  </td>
                  <td>
                    <input className="input" type="number" min="0" value={k.tarif_normal}
                      onChange={e => updateK(i, 'tarif_normal', Number(e.target.value))}
                      style={{ width: 70, textAlign: 'center' }} />
                  </td>
                  <td>
                    <input className="input" type="number" min="0" value={k.menit_lembur}
                      onChange={e => updateK(i, 'menit_lembur', Number(e.target.value))}
                      style={{ width: 70, textAlign: 'center' }} />
                  </td>
                  <td>
                    <input className="input" type="number" min="0" value={k.tarif_lembur}
                      onChange={e => updateK(i, 'tarif_lembur', Number(e.target.value))}
                      style={{ width: 70, textAlign: 'center' }} />
                  </td>
                  <td className="text-yellow font-mono">{formatRp(k.gaji_kotor)}</td>
                  <td className="text-pink font-mono">{formatRp(k.bon_lama)}</td>
                  <td>
                    <input className="input" type="number" min="0" value={k.potong_bon}
                      onChange={e => updateK(i, 'potong_bon', Number(e.target.value))}
                      style={{ width: 70, textAlign: 'center', color: 'var(--neon-pink)' }} />
                  </td>
                  <td className="text-green font-mono" style={{ fontWeight: 'bold' }}>{formatRp(k.gaji_bersih)}</td>
                  <td>
                    {k.daily_records.length > 0 && (
                      <button className="btn btn-ghost btn-sm" onClick={() => openEditor(i)} title="Edit absensi harian">Edit</button>
                    )}
                  </td>
                </tr>
              ))}
              {karyawan.length === 0 && (
                <tr><td colSpan={12} className="text-muted" style={{ textAlign: 'center', padding: 32 }}>
                  Import file absensi dari mesin fingerprint untuk memulai
                </td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Save Button */}
      <div className="mt-16">
        <button className="btn btn-solid" onClick={handleSaveAll} disabled={karyawan.length === 0}
          style={{ padding: '12px 32px' }}>
          Simpan &amp; Cetak All
        </button>
      </div>

      {/* Attendance Editor Modal */}
      {editingIdx !== null && editorData && (
        <AttendanceEditor
          data={editorData}
          tarifNormal={tarifNormal}
          tarifLembur={tarifLembur}
          onSave={handleEditorSave}
          onCancel={() => { setEditingIdx(null); setEditorData(null) }}
        />
      )}
    </div>
  )
}


// ── Attendance Editor Modal ──────────────────────────────────────────

function AttendanceEditor({ data, tarifNormal, tarifLembur, onSave, onCancel }) {
  const [records, setRecords] = useState(data.daily_records || [])
  const [trfN, setTrfN] = useState(tarifNormal)
  const [trfL, setTrfL] = useState(tarifLembur)
  const [potong, setPotong] = useState(data.potong_bon || 0)

  const updateRec = (i, field, val) => {
    const next = [...records]
    next[i] = { ...next[i], [field]: val }
    // Recalculate menit
    const r = next[i]
    if (r.tap_masuk && r.tap_keluar && r.tap_keluar.toLowerCase() !== 'lupa') {
      try {
        const [mh, mm] = r.tap_masuk.split(':').map(Number)
        const [kh, km] = r.tap_keluar.split(':').map(Number)
        let diff = (kh * 60 + km) - (mh * 60 + mm)
        if (diff < 0) diff += 1440
        r.menit_normal = Math.min(diff, 480)
        r.menit_lembur = Math.max(0, diff - 480)
      } catch { /* keep manual values */ }
    }
    setRecords(next)
  }

  const totalNormal = records.reduce((s, r) => s + (r.menit_normal || 0), 0)
  const totalLembur = records.reduce((s, r) => s + (r.menit_lembur || 0), 0)
  const gajiKotor = (totalNormal * trfN) + (totalLembur * trfL)
  const gajiBersih = gajiKotor - potong

  const handleSave = () => {
    onSave({
      tarif_normal: trfN,
      tarif_lembur: trfL,
      potong_bon: potong,
      menit_normal: totalNormal,
      menit_lembur: totalLembur,
      hadir: records.filter(r => r.tap_masuk && r.tap_keluar?.toLowerCase() !== 'lupa').length,
      daily_records: records,
    })
  }

  return (
    <div className="modal-overlay">
      <div className="modal-content" style={{ maxWidth: 900 }}>
        <div className="modal-header">
          <h3>EDITOR ABSENSI: {data.nama.toUpperCase()}</h3>
          <button className="btn btn-ghost btn-sm" onClick={onCancel}>X</button>
        </div>
        <div className="modal-body">
          {/* Tarif Controls */}
          <div className="form-row" style={{ marginBottom: 16 }}>
            <div className="form-group">
              <label>Tarif Normal</label>
              <input className="input" type="number" value={trfN} onChange={e => setTrfN(Number(e.target.value))} style={{ width: 100 }} />
            </div>
            <div className="form-group">
              <label>Tarif Lembur</label>
              <input className="input" type="number" value={trfL} onChange={e => setTrfL(Number(e.target.value))} style={{ width: 100 }} />
            </div>
            <div className="form-group">
              <label>Potong Bon</label>
              <input className="input" type="number" min="0" value={potong} onChange={e => setPotong(Number(e.target.value))} style={{ width: 120 }} />
            </div>
          </div>

          {/* Daily Records Table */}
          <div className="table-container mb-16">
            <table className="data-table">
              <thead><tr><th>Tanggal</th><th>Jam Masuk</th><th>Jam Keluar</th><th style={{ textAlign: 'center' }}>Menit Normal</th><th style={{ textAlign: 'center' }}>Menit Lembur</th></tr></thead>
              <tbody>
                {records.map((r, i) => (
                  <tr key={i}>
                    <td className="text-muted">{r.tanggal}</td>
                    <td><input className="input" value={r.tap_masuk || ''} onChange={e => updateRec(i, 'tap_masuk', e.target.value)} style={{ width: 80, textAlign: 'center' }} /></td>
                    <td><input className="input" value={r.tap_keluar || ''} onChange={e => updateRec(i, 'tap_keluar', e.target.value)} style={{ width: 80, textAlign: 'center' }} /></td>
                    <td style={{ textAlign: 'center' }}>{r.menit_normal}</td>
                    <td style={{ textAlign: 'center' }}>{r.menit_lembur}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Summary */}
          <div className="form-row" style={{ marginBottom: 16 }}>
            <span className="text-muted">Total Normal: <b className="text-cyan">{totalNormal}</b> mnt</span>
            <span className="text-muted">Total Lembur: <b className="text-cyan">{totalLembur}</b> mnt</span>
            <span className="text-muted">Gaji Kotor: <b className="text-yellow">{formatRp(gajiKotor)}</b></span>
            <span className="text-muted">Gaji Bersih: <b className="text-green">{formatRp(gajiBersih)}</b></span>
          </div>
        </div>

        <div className="modal-footer">
          <button className="btn btn-ghost" onClick={onCancel}>Batal</button>
          <button className="btn btn-solid" onClick={handleSave}>Simpan Editan</button>
        </div>
      </div>
    </div>
  )
}


// ══════════════════════════════════════════════════════════════════════
// TAB 4: KASBON / UTANG
// ══════════════════════════════════════════════════════════════════════

function KasbonTab() {
  const [balances, setBalances] = useState([])
  const [movements, setMovements] = useState([])
  const [persons, setPersons] = useState([])
  const [loading, setLoading] = useState(true)
  const [filterPerson, setFilterPerson] = useState('')
  const [modalOpen, setModalOpen] = useState(false)
  const [form, setForm] = useState({ person_id: '', tipe: 'TAMBAH', nominal: 0, catatan: '' })

  const loadData = useCallback(() => {
    setLoading(true)
    Promise.all([
      api.listBonBalances(),
      api.listBonMovements(filterPerson ? { person_id: filterPerson } : {}),
      api.listPersons(),
    ]).then(([b, m, p]) => { setBalances(b); setMovements(m); setPersons(p) })
      .finally(() => setLoading(false))
  }, [filterPerson])

  useEffect(() => { loadData() }, [loadData])

  const totalSaldo = balances.reduce((s, b) => s + b.saldo, 0)

  const handleCreate = async () => {
    if (!form.person_id || form.nominal <= 0) return alert('Isi form dengan benar')
    await api.createBonMovement({
      person_id: Number(form.person_id),
      tipe: form.tipe,
      nominal: form.nominal,
      catatan: form.catatan,
    })
    setModalOpen(false)
    setForm({ person_id: '', tipe: 'TAMBAH', nominal: 0, catatan: '' })
    loadData()
  }

  return (
    <div>
      <div className="kpi-grid" style={{ gridTemplateColumns: 'repeat(3, 1fr)', marginBottom: 16 }}>
        <div className="kpi-card">
          <div className="kpi-label">Total Saldo Bon</div>
          <div className="kpi-value text-pink">{formatRp(totalSaldo)}</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-label">Jumlah Person</div>
          <div className="kpi-value text-cyan">{balances.length}</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-label">Total Transaksi</div>
          <div className="kpi-value text-yellow">{movements.length}</div>
        </div>
      </div>

      <div className="table-toolbar" style={{ marginBottom: 16 }}>
        <button className="btn btn-solid" onClick={() => setModalOpen(true)}>+ Catat Bon</button>
        <select className="input" value={filterPerson} onChange={e => setFilterPerson(e.target.value)} style={{ maxWidth: 200 }}>
          <option value="">Semua Person</option>
          {persons.map(p => <option key={p.id} value={p.id}>{p.nama}</option>)}
        </select>
      </div>

      {/* Balances */}
      <div className="panel" style={{ marginBottom: 24 }}>
        <h3 className="text-cyan mb-16" style={{ fontSize: 14, letterSpacing: 1 }}>SALDO BON PER PERSON</h3>
        <div className="table-container">
          <table className="data-table">
            <thead><tr><th>Person</th><th style={{ textAlign: 'right' }}>Saldo</th><th>Terakhir Update</th></tr></thead>
            <tbody>
              {balances.map(b => (
                <tr key={b.id}>
                  <td style={{ fontWeight: 'bold' }}>{b.person_nama || `ID: ${b.person_id}`}</td>
                  <td className="text-pink font-mono" style={{ textAlign: 'right', fontWeight: 'bold' }}>{formatRp(b.saldo)}</td>
                  <td className="text-muted">{b.updated_at ? new Date(b.updated_at).toLocaleDateString('id-ID') : '-'}</td>
                </tr>
              ))}
              {balances.length === 0 && <tr><td colSpan={3} className="text-muted" style={{ textAlign: 'center', padding: 24 }}>Belum ada data bon</td></tr>}
            </tbody>
          </table>
        </div>
      </div>

      {/* Movements */}
      <div className="panel">
        <h3 className="text-cyan mb-16" style={{ fontSize: 14, letterSpacing: 1 }}>RIWAYAT TRANSAKSI</h3>
        <div className="table-container">
          <table className="data-table">
            <thead><tr><th>Tanggal</th><th>Person</th><th>Tipe</th><th style={{ textAlign: 'right' }}>Nominal</th><th>Sumber</th><th>Catatan</th></tr></thead>
            <tbody>
              {movements.map(m => (
                <tr key={m.id}>
                  <td>{m.tanggal}</td>
                  <td>{m.person_nama || `ID: ${m.person_id}`}</td>
                  <td><span className={`badge ${m.tipe === 'TAMBAH' ? 'badge-green' : 'badge-red'}`}>{m.tipe}</span></td>
                  <td className={`font-mono ${m.tipe === 'TAMBAH' ? 'text-green' : 'text-red'}`} style={{ textAlign: 'right', fontWeight: 'bold' }}>{formatRp(m.nominal)}</td>
                  <td className="text-muted">{m.sumber}</td>
                  <td className="text-muted">{m.catatan || '-'}</td>
                </tr>
              ))}
              {movements.length === 0 && <tr><td colSpan={6} className="text-muted" style={{ textAlign: 'center', padding: 24 }}>Belum ada transaksi</td></tr>}
            </tbody>
          </table>
        </div>
      </div>

      {/* Modal */}
      <Modal open={modalOpen} title="Catat Bon" onClose={() => setModalOpen(false)}>
        <div className="form-grid">
          <div className="form-group">
            <label>Person</label>
            <select className="input" value={form.person_id} onChange={e => setForm({ ...form, person_id: e.target.value })}>
              <option value="">-- Pilih --</option>
              {persons.map(p => <option key={p.id} value={p.id}>{p.nama}</option>)}
            </select>
          </div>
          <div className="form-group">
            <label>Tipe</label>
            <select className="input" value={form.tipe} onChange={e => setForm({ ...form, tipe: e.target.value })}>
              <option value="TAMBAH">TAMBAH (Pinjam)</option>
              <option value="POTONG">POTONG (Bayar)</option>
            </select>
          </div>
          <div className="form-group">
            <label>Nominal</label>
            <input className="input" type="number" min="0" value={form.nominal} onChange={e => setForm({ ...form, nominal: Number(e.target.value) })} />
          </div>
          <div className="form-group">
            <label>Catatan</label>
            <input className="input" value={form.catatan} onChange={e => setForm({ ...form, catatan: e.target.value })} />
          </div>
        </div>
        <div className="modal-footer">
          <button className="btn btn-ghost" onClick={() => setModalOpen(false)}>Batal</button>
          <button className="btn btn-solid" onClick={handleCreate}>Simpan</button>
        </div>
      </Modal>
    </div>
  )
}


// ══════════════════════════════════════════════════════════════════════
// MAIN PAGE
// ══════════════════════════════════════════════════════════════════════

const TABS = [
  { key: 'penjahit', label: 'GAJI PENJAHIT' },
  { key: 'pengsup', label: 'TOTALAN PENGSUP' },
  { key: 'karyawan', label: 'GAJI KARYAWAN (ABSENSI)' },
  { key: 'kasbon', label: 'KASBON / UTANG' },
]

export default function PayrollBon() {
  const [activeTab, setActiveTab] = useState('penjahit')

  return (
    <div>
      <div className="page-header">
        <h2>PAYROLL &amp; REKAP GAJI</h2>
      </div>

      {/* Tab Bar */}
      <div className="tabs">
        {TABS.map(tab => (
          <button
            key={tab.key}
            className={`tab${activeTab === tab.key ? ' active' : ''}`}
            onClick={() => setActiveTab(tab.key)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      {activeTab === 'penjahit' && <GajiPenjahitTab />}
      {activeTab === 'pengsup' && <TotalanPengsupTab />}
      {activeTab === 'karyawan' && <GajiKaryawanTab />}
      {activeTab === 'kasbon' && <KasbonTab />}
    </div>
  )
}
