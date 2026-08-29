/**
 * Yazmina Hijab Web — Catatan Harian Page.
 *
 * Tabs (matching desktop app):
 * 1. Hasil Cutting — cutting results (production output)
 * 2. Distribusi Jahit — distribution to penjahit/pengsup
 * 3. Pengeluaran Offline — offline sales
 * 4. Modal Operasional — daily expenses (BARANG, OVERHEAD, UTILITAS)
 */

import React, { useState, useEffect, useCallback } from 'react'
import { api } from '../api/client'
import Modal from '../components/Modal'

// ── Helpers ──────────────────────────────────────────────────────────

function formatRp(val) {
  if (!val) return 'Rp 0'
  return 'Rp ' + Number(val).toLocaleString('id-ID')
}

function today() {
  return new Date().toISOString().slice(0, 10)
}

const JENIS_OPTIONS = [
  { value: 'BARANG', label: 'Barang', color: 'badge-cyan' },
  { value: 'OVERHEAD', label: 'Overhead', color: 'badge-yellow' },
  { value: 'UTILITAS', label: 'Utilitas', color: 'badge-green' },
  { value: 'LAINNYA', label: 'Lainnya', color: 'badge-gray' },
]

const JENIS_COLORS = Object.fromEntries(JENIS_OPTIONS.map(j => [j.value, j.color]))

// ── Tab 1: Hasil Cutting ────────────────────────────────────────────

function HasilCuttingTab() {
  const [items, setItems] = useState([])
  const [skus, setSkus] = useState([])
  const [loading, setLoading] = useState(true)
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')

  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState(null)
  const [form, setForm] = useState({ tanggal: today(), sku_id: '', qty: 1, kode_produksi: '', catatan: '' })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const fetchData = useCallback(async () => {
    setLoading(true)
    try {
      const [list, skuList] = await Promise.all([
        api.listHasilCutting({ date_from: dateFrom || undefined, date_to: dateTo || undefined }),
        api.listSku(),
      ])
      setItems(list)
      setSkus(skuList)
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }, [dateFrom, dateTo])

  useEffect(() => { fetchData() }, [fetchData])

  const handleCreate = () => {
    setEditing(null)
    setForm({ tanggal: today(), sku_id: '', qty: 1, kode_produksi: '', catatan: '' })
    setError('')
    setModalOpen(true)
  }

  const handleEdit = (row) => {
    setEditing(row)
    setForm({ tanggal: row.tanggal, sku_id: row.sku_id, qty: row.qty, kode_produksi: row.kode_produksi || '', catatan: row.catatan || '' })
    setError('')
    setModalOpen(true)
  }

  const handleDelete = async (row) => {
    if (!confirm('Hapus data hasil cutting ini?')) return
    try {
      await api.deleteHasilCutting(row.id)
      fetchData()
    } catch (err) {
      alert('Gagal: ' + err.message)
    }
  }

  const handleSave = async () => {
    setError('')
    setSaving(true)
    try {
      const payload = { ...form, sku_id: Number(form.sku_id), qty: Number(form.qty) }
      if (editing) {
        await api.updateHasilCutting(editing.id, payload)
      } else {
        await api.createHasilCutting(payload)
      }
      setModalOpen(false)
      fetchData()
    } catch (err) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div>
      {/* Toolbar */}
      <div className="table-toolbar" style={{ marginBottom: 16 }}>
        <button className="btn btn-solid" onClick={handleCreate}>+ Tambah Cutting</button>
        <input className="input" type="date" value={dateFrom} onChange={e => setDateFrom(e.target.value)} style={{ maxWidth: 160 }} />
        <span className="text-muted">s/d</span>
        <input className="input" type="date" value={dateTo} onChange={e => setDateTo(e.target.value)} style={{ maxWidth: 160 }} />
      </div>

      {/* Table */}
      <div className="panel">
        <div className="table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th style={{ width: 48 }}>#</th>
                <th style={{ width: 120 }}>Tanggal</th>
                <th style={{ width: 120 }}>Kode Batch</th>
                <th>SKU</th>
                <th style={{ width: 100, textAlign: 'right' }}>Qty</th>
                <th style={{ width: 120 }}>Aksi</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan={6} className="text-muted" style={{ padding: 32, textAlign: 'center' }}>Memuat data...</td></tr>
              ) : items.length === 0 ? (
                <tr><td colSpan={6} className="text-muted" style={{ padding: 32, textAlign: 'center' }}>Tidak ada data</td></tr>
              ) : items.map((row, i) => (
                <tr key={row.id}>
                  <td className="text-muted">{i + 1}</td>
                  <td>{row.tanggal}</td>
                  <td style={{ color: 'var(--neon-cyan)' }}>{row.kode_produksi || '-'}</td>
                  <td>{row.sku_kode || row.sku_id}</td>
                  <td style={{ textAlign: 'right', fontWeight: 'bold' }}>{row.qty}</td>
                  <td>
                    <button className="btn btn-ghost btn-sm" onClick={() => handleEdit(row)} style={{ marginRight: 4 }}>Edit</button>
                    <button className="btn btn-ghost btn-sm text-red" onClick={() => handleDelete(row)}>Hapus</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Modal */}
      <Modal open={modalOpen} title={editing ? 'Edit Hasil Cutting' : 'Tambah Hasil Cutting'} onClose={() => setModalOpen(false)}>
        <div className="form-grid">
          <div className="form-group">
            <label>Tanggal *</label>
            <input className="input" type="date" value={form.tanggal} onChange={e => setForm({ ...form, tanggal: e.target.value })} />
          </div>
          <div className="form-group">
            <label>Kode Produksi / Batch</label>
            <input className="input" value={form.kode_produksi} onChange={e => setForm({ ...form, kode_produksi: e.target.value })} placeholder="Kode batch (opsional)" />
          </div>
          <div className="form-group">
            <label>SKU *</label>
            <select className="input" value={form.sku_id} onChange={e => setForm({ ...form, sku_id: e.target.value })}>
              <option value="">-- Pilih SKU --</option>
              {skus.map(s => <option key={s.id} value={s.id}>{s.kode_sku} - {s.nama_produk}</option>)}
            </select>
          </div>
          <div className="form-group">
            <label>Qty Hasil Potong *</label>
            <input className="input" type="number" min="1" value={form.qty} onChange={e => setForm({ ...form, qty: Number(e.target.value) })} />
          </div>
          <div className="form-group" style={{ gridColumn: '1 / -1' }}>
            <label>Catatan</label>
            <input className="input" value={form.catatan} onChange={e => setForm({ ...form, catatan: e.target.value })} placeholder="Opsional" />
          </div>
        </div>
        {error && <p className="text-red" style={{ marginTop: 8 }}>{error}</p>}
        <div className="modal-footer">
          <button className="btn btn-ghost" onClick={() => setModalOpen(false)}>Batal</button>
          <button className="btn btn-solid" onClick={handleSave} disabled={saving || !form.sku_id || form.qty <= 0}>
            {saving ? 'Menyimpan...' : editing ? 'Simpan Perubahan' : 'Tambah'}
          </button>
        </div>
      </Modal>
    </div>
  )
}

// ── Tab 2: Distribusi Jahit ─────────────────────────────────────────

function DistribusiCuttingTab() {
  const [items, setItems] = useState([])
  const [skus, setSkus] = useState([])
  const [persons, setPersons] = useState([])
  const [loading, setLoading] = useState(true)
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')

  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState(null)
  const [form, setForm] = useState({ tanggal: today(), person_id: '', sku_id: '', qty: 1, catatan: '' })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const fetchData = useCallback(async () => {
    setLoading(true)
    try {
      const [list, skuList, personList] = await Promise.all([
        api.listDistribusiCutting({ date_from: dateFrom || undefined, date_to: dateTo || undefined }),
        api.listSku(),
        api.listPersons({ person_type: 'PENJAHIT' }),
      ])
      setItems(list)
      setSkus(skuList)
      setPersons(personList)
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }, [dateFrom, dateTo])

  useEffect(() => { fetchData() }, [fetchData])

  const handleCreate = () => {
    setEditing(null)
    setForm({ tanggal: today(), person_id: '', sku_id: '', qty: 1, catatan: '' })
    setError('')
    setModalOpen(true)
  }

  const handleEdit = (row) => {
    setEditing(row)
    setForm({ tanggal: row.tanggal, person_id: row.person_id, sku_id: row.sku_id, qty: row.qty, catatan: row.catatan || '' })
    setError('')
    setModalOpen(true)
  }

  const handleDelete = async (row) => {
    if (!confirm('Hapus data distribusi ini?')) return
    try {
      await api.deleteDistribusiCutting(row.id)
      fetchData()
    } catch (err) {
      alert('Gagal: ' + err.message)
    }
  }

  const handleSave = async () => {
    setError('')
    setSaving(true)
    try {
      const payload = { ...form, person_id: Number(form.person_id), sku_id: Number(form.sku_id), qty: Number(form.qty) }
      if (editing) {
        await api.updateDistribusiCutting(editing.id, payload)
      } else {
        await api.createDistribusiCutting(payload)
      }
      setModalOpen(false)
      fetchData()
    } catch (err) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div>
      {/* Toolbar */}
      <div className="table-toolbar" style={{ marginBottom: 16 }}>
        <button className="btn btn-solid" onClick={handleCreate}>+ Tambah Distribusi</button>
        <input className="input" type="date" value={dateFrom} onChange={e => setDateFrom(e.target.value)} style={{ maxWidth: 160 }} />
        <span className="text-muted">s/d</span>
        <input className="input" type="date" value={dateTo} onChange={e => setDateTo(e.target.value)} style={{ maxWidth: 160 }} />
      </div>

      {/* Table */}
      <div className="panel">
        <div className="table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th style={{ width: 48 }}>#</th>
                <th style={{ width: 120 }}>Tanggal</th>
                <th>Penerima</th>
                <th style={{ width: 100 }}>Jenis</th>
                <th>SKU</th>
                <th style={{ width: 80, textAlign: 'right' }}>Qty</th>
                <th style={{ width: 120 }}>Aksi</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan={7} className="text-muted" style={{ padding: 32, textAlign: 'center' }}>Memuat data...</td></tr>
              ) : items.length === 0 ? (
                <tr><td colSpan={7} className="text-muted" style={{ padding: 32, textAlign: 'center' }}>Tidak ada data</td></tr>
              ) : items.map((row, i) => (
                <tr key={row.id}>
                  <td className="text-muted">{i + 1}</td>
                  <td>{row.tanggal}</td>
                  <td>{row.person_nama || '-'}</td>
                  <td><span className={`badge ${row.person_jenis === 'PENJAHIT' ? 'badge-cyan' : 'badge-purple'}`}>{row.person_jenis || '-'}</span></td>
                  <td>{row.sku_kode || row.sku_id}</td>
                  <td style={{ textAlign: 'right', fontWeight: 'bold' }}>{row.qty}</td>
                  <td>
                    <button className="btn btn-ghost btn-sm" onClick={() => handleEdit(row)} style={{ marginRight: 4 }}>Edit</button>
                    <button className="btn btn-ghost btn-sm text-red" onClick={() => handleDelete(row)}>Hapus</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Modal */}
      <Modal open={modalOpen} title={editing ? 'Edit Distribusi' : 'Tambah Distribusi'} onClose={() => setModalOpen(false)}>
        <div className="form-grid">
          <div className="form-group">
            <label>Tanggal *</label>
            <input className="input" type="date" value={form.tanggal} onChange={e => setForm({ ...form, tanggal: e.target.value })} />
          </div>
          <div className="form-group">
            <label>Penerima (Penjahit) *</label>
            <select className="input" value={form.person_id} onChange={e => setForm({ ...form, person_id: e.target.value })}>
              <option value="">-- Pilih Penerima --</option>
              {persons.map(p => <option key={p.id} value={p.id}>{p.nama} ({p.person_type})</option>)}
            </select>
          </div>
          <div className="form-group">
            <label>SKU *</label>
            <select className="input" value={form.sku_id} onChange={e => setForm({ ...form, sku_id: e.target.value })}>
              <option value="">-- Pilih SKU --</option>
              {skus.map(s => <option key={s.id} value={s.id}>{s.kode_sku} - {s.nama_produk}</option>)}
            </select>
          </div>
          <div className="form-group">
            <label>Qty Diambil *</label>
            <input className="input" type="number" min="1" value={form.qty} onChange={e => setForm({ ...form, qty: Number(e.target.value) })} />
          </div>
          <div className="form-group" style={{ gridColumn: '1 / -1' }}>
            <label>Catatan</label>
            <input className="input" value={form.catatan} onChange={e => setForm({ ...form, catatan: e.target.value })} placeholder="Opsional" />
          </div>
        </div>
        {error && <p className="text-red" style={{ marginTop: 8 }}>{error}</p>}
        <div className="modal-footer">
          <button className="btn btn-ghost" onClick={() => setModalOpen(false)}>Batal</button>
          <button className="btn btn-solid" onClick={handleSave} disabled={saving || !form.person_id || !form.sku_id || form.qty <= 0}>
            {saving ? 'Menyimpan...' : editing ? 'Simpan Perubahan' : 'Tambah'}
          </button>
        </div>
      </Modal>
    </div>
  )
}

// ── Tab 3: Pengeluaran Offline ───────────────────────────────────────

function PenjualanOfflineTab() {
  const [items, setItems] = useState([])
  const [skus, setSkus] = useState([])
  const [persons, setPersons] = useState([])
  const [loading, setLoading] = useState(true)
  const [summary, setSummary] = useState({})
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')

  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState(null)
  const [form, setForm] = useState({ tanggal: today(), sku_id: '', qty: 1, harga_satuan: 0, total: 0, person_id: '', catatan: '' })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const fetchData = useCallback(async () => {
    setLoading(true)
    try {
      const [list, sum, skuList, personList] = await Promise.all([
        api.listPengeluaranOffline({ date_from: dateFrom || undefined, date_to: dateTo || undefined }),
        api.summaryPengeluaranOffline({ date_from: dateFrom || undefined, date_to: dateTo || undefined }),
        api.listSku(),
        api.listPersons(),
      ])
      setItems(list)
      setSummary(sum)
      setSkus(skuList)
      setPersons(personList)
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }, [dateFrom, dateTo])

  useEffect(() => { fetchData() }, [fetchData])

  useEffect(() => {
    setForm(f => ({ ...f, total: (f.qty || 0) * (f.harga_satuan || 0) }))
  }, [form.qty, form.harga_satuan])

  const handleCreate = () => {
    setEditing(null)
    setForm({ tanggal: today(), sku_id: '', qty: 1, harga_satuan: 0, total: 0, person_id: '', catatan: '' })
    setError('')
    setModalOpen(true)
  }

  const handleEdit = (row) => {
    setEditing(row)
    setForm({ tanggal: row.tanggal, sku_id: row.sku_id, qty: row.qty, harga_satuan: row.harga_satuan, total: row.total, person_id: row.person_id || '', catatan: row.catatan || '' })
    setError('')
    setModalOpen(true)
  }

  const handleDelete = async (row) => {
    if (!confirm('Hapus data penjualan ini?')) return
    try {
      await api.deletePengeluaranOffline(row.id)
      fetchData()
    } catch (err) {
      alert('Gagal: ' + err.message)
    }
  }

  const handleSave = async () => {
    setError('')
    setSaving(true)
    try {
      const payload = { ...form, sku_id: Number(form.sku_id), person_id: form.person_id ? Number(form.person_id) : null }
      if (editing) {
        await api.updatePengeluaranOffline(editing.id, payload)
      } else {
        await api.createPengeluaranOffline(payload)
      }
      setModalOpen(false)
      fetchData()
    } catch (err) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div>
      {/* Summary */}
      <div className="kpi-grid" style={{ marginBottom: 16 }}>
        <div className="kpi-card">
          <div className="kpi-label">TOTAL PENJUALAN</div>
          <div className="kpi-value text-pink">{formatRp(summary.total_penjualan)}</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-label">TOTAL QTY</div>
          <div className="kpi-value text-cyan">{Number(summary.total_qty || 0).toLocaleString('id-ID')}</div>
        </div>
      </div>

      {/* Toolbar */}
      <div className="table-toolbar" style={{ marginBottom: 16 }}>
        <button className="btn btn-solid" onClick={handleCreate}>+ Tambah Penjualan</button>
        <input className="input" type="date" value={dateFrom} onChange={e => setDateFrom(e.target.value)} style={{ maxWidth: 160 }} />
        <span className="text-muted">s/d</span>
        <input className="input" type="date" value={dateTo} onChange={e => setDateTo(e.target.value)} style={{ maxWidth: 160 }} />
      </div>

      {/* Table */}
      <div className="panel">
        <div className="table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th style={{ width: 48 }}>#</th>
                <th style={{ width: 120 }}>Tanggal</th>
                <th>Pembeli</th>
                <th>SKU</th>
                <th style={{ width: 80, textAlign: 'right' }}>Qty</th>
                <th style={{ width: 130, textAlign: 'right' }}>Harga</th>
                <th style={{ width: 130, textAlign: 'right' }}>Total</th>
                <th style={{ width: 120 }}>Aksi</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan={8} className="text-muted" style={{ padding: 32, textAlign: 'center' }}>Memuat data...</td></tr>
              ) : items.length === 0 ? (
                <tr><td colSpan={8} className="text-muted" style={{ padding: 32, textAlign: 'center' }}>Tidak ada data</td></tr>
              ) : items.map((row, i) => (
                <tr key={row.id}>
                  <td className="text-muted">{i + 1}</td>
                  <td>{row.tanggal}</td>
                  <td>{row.person_nama || '-'}</td>
                  <td>{row.sku_nama || row.sku_id}</td>
                  <td style={{ textAlign: 'right' }}>{row.qty}</td>
                  <td style={{ textAlign: 'right', fontFamily: 'Consolas, monospace' }}>{formatRp(row.harga_satuan)}</td>
                  <td style={{ textAlign: 'right', fontFamily: 'Consolas, monospace', color: 'var(--neon-pink)' }}>{formatRp(row.total)}</td>
                  <td>
                    <button className="btn btn-ghost btn-sm" onClick={() => handleEdit(row)} style={{ marginRight: 4 }}>Edit</button>
                    <button className="btn btn-ghost btn-sm text-red" onClick={() => handleDelete(row)}>Hapus</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Modal */}
      <Modal open={modalOpen} title={editing ? 'Edit Penjualan' : 'Tambah Penjualan'} onClose={() => setModalOpen(false)}>
        <div className="form-grid">
          <div className="form-group">
            <label>Tanggal *</label>
            <input className="input" type="date" value={form.tanggal} onChange={e => setForm({ ...form, tanggal: e.target.value })} />
          </div>
          <div className="form-group">
            <label>Pembeli</label>
            <select className="input" value={form.person_id} onChange={e => setForm({ ...form, person_id: e.target.value })}>
              <option value="">-- Pilih Pembeli --</option>
              {persons.map(p => <option key={p.id} value={p.id}>{p.nama} ({p.person_type})</option>)}
            </select>
          </div>
          <div className="form-group">
            <label>SKU *</label>
            <select className="input" value={form.sku_id} onChange={e => setForm({ ...form, sku_id: e.target.value })}>
              <option value="">-- Pilih SKU --</option>
              {skus.map(s => <option key={s.id} value={s.id}>{s.kode_sku} - {s.nama_produk}</option>)}
            </select>
          </div>
          <div className="form-group">
            <label>Qty *</label>
            <input className="input" type="number" min="0.01" step="0.1" value={form.qty} onChange={e => setForm({ ...form, qty: Number(e.target.value) })} />
          </div>
          <div className="form-group">
            <label>Harga Satuan (Rp) *</label>
            <input className="input" type="number" value={form.harga_satuan} onChange={e => setForm({ ...form, harga_satuan: Number(e.target.value) })} />
          </div>
          <div className="form-group">
            <label>Total (Rp)</label>
            <input className="input" type="number" value={form.total} readOnly style={{ color: 'var(--neon-pink)', fontWeight: 'bold' }} />
          </div>
          <div className="form-group" style={{ gridColumn: '1 / -1' }}>
            <label>Catatan</label>
            <input className="input" value={form.catatan} onChange={e => setForm({ ...form, catatan: e.target.value })} placeholder="Opsional" />
          </div>
        </div>
        {error && <p className="text-red" style={{ marginTop: 8 }}>{error}</p>}
        <div className="modal-footer">
          <button className="btn btn-ghost" onClick={() => setModalOpen(false)}>Batal</button>
          <button className="btn btn-solid" onClick={handleSave} disabled={saving || !form.sku_id || form.qty <= 0}>
            {saving ? 'Menyimpan...' : editing ? 'Simpan Perubahan' : 'Tambah'}
          </button>
        </div>
      </Modal>
    </div>
  )
}

// ── Tab 4: Modal Operasional ─────────────────────────────────────────

function ModalOperasionalTab() {
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)
  const [summary, setSummary] = useState({})
  const [filterJenis, setFilterJenis] = useState('')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')

  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState(null)
  const [form, setForm] = useState({ tanggal: today(), jenis: 'BARANG', keterangan: '', nominal: 0, catatan: '' })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const fetchData = useCallback(async () => {
    setLoading(true)
    try {
      const [list, sum] = await Promise.all([
        api.listModalOperasional({ jenis: filterJenis || undefined, date_from: dateFrom || undefined, date_to: dateTo || undefined }),
        api.summaryModalOperasional({ date_from: dateFrom || undefined, date_to: dateTo || undefined }),
      ])
      setItems(list)
      setSummary(sum)
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }, [filterJenis, dateFrom, dateTo])

  useEffect(() => { fetchData() }, [fetchData])

  const handleCreate = () => {
    setEditing(null)
    setForm({ tanggal: today(), jenis: 'BARANG', keterangan: '', nominal: 0, catatan: '' })
    setError('')
    setModalOpen(true)
  }

  const handleEdit = (row) => {
    setEditing(row)
    setForm({ tanggal: row.tanggal, jenis: row.jenis, keterangan: row.keterangan, nominal: row.nominal, catatan: row.catatan || '' })
    setError('')
    setModalOpen(true)
  }

  const handleDelete = async (row) => {
    if (!confirm(`Hapus pengeluaran "${row.keterangan}"?`)) return
    try {
      await api.deleteModalOperasional(row.id)
      fetchData()
    } catch (err) {
      alert('Gagal: ' + err.message)
    }
  }

  const handleSave = async () => {
    setError('')
    setSaving(true)
    try {
      if (editing) {
        await api.updateModalOperasional(editing.id, form)
      } else {
        await api.createModalOperasional(form)
      }
      setModalOpen(false)
      fetchData()
    } catch (err) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div>
      {/* Summary Cards */}
      <div className="kpi-grid" style={{ marginBottom: 16 }}>
        {JENIS_OPTIONS.map(j => (
          <div className="kpi-card" key={j.value}>
            <div className="kpi-label">{j.label}</div>
            <div className="kpi-value text-cyan">{formatRp(summary[j.value])}</div>
          </div>
        ))}
        <div className="kpi-card" style={{ gridColumn: '1 / -1' }}>
          <div className="kpi-label">TOTAL PENGELUARAN</div>
          <div className="kpi-value text-pink">{formatRp(summary.total)}</div>
        </div>
      </div>

      {/* Toolbar */}
      <div className="table-toolbar" style={{ marginBottom: 16 }}>
        <button className="btn btn-solid" onClick={handleCreate}>+ Tambah Pengeluaran</button>
        <select className="input" value={filterJenis} onChange={e => setFilterJenis(e.target.value)} style={{ maxWidth: 160 }}>
          <option value="">Semua Jenis</option>
          {JENIS_OPTIONS.map(j => <option key={j.value} value={j.value}>{j.label}</option>)}
        </select>
        <input className="input" type="date" value={dateFrom} onChange={e => setDateFrom(e.target.value)} style={{ maxWidth: 160 }} />
        <span className="text-muted">s/d</span>
        <input className="input" type="date" value={dateTo} onChange={e => setDateTo(e.target.value)} style={{ maxWidth: 160 }} />
      </div>

      {/* Table */}
      <div className="panel">
        <div className="table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th style={{ width: 48 }}>#</th>
                <th style={{ width: 120 }}>Tanggal</th>
                <th style={{ width: 110 }}>Jenis</th>
                <th>Keterangan</th>
                <th style={{ width: 140, textAlign: 'right' }}>Nominal</th>
                <th style={{ width: 120 }}>Aksi</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan={6} className="text-muted" style={{ padding: 32, textAlign: 'center' }}>Memuat data...</td></tr>
              ) : items.length === 0 ? (
                <tr><td colSpan={6} className="text-muted" style={{ padding: 32, textAlign: 'center' }}>Tidak ada data</td></tr>
              ) : items.map((row, i) => (
                <tr key={row.id}>
                  <td className="text-muted">{i + 1}</td>
                  <td>{row.tanggal}</td>
                  <td><span className={`badge ${JENIS_COLORS[row.jenis] || 'badge-gray'}`}>{row.jenis}</span></td>
                  <td>{row.keterangan}</td>
                  <td style={{ textAlign: 'right', fontFamily: 'Consolas, monospace' }}>{formatRp(row.nominal)}</td>
                  <td>
                    <button className="btn btn-ghost btn-sm" onClick={() => handleEdit(row)} style={{ marginRight: 4 }}>Edit</button>
                    <button className="btn btn-ghost btn-sm text-red" onClick={() => handleDelete(row)}>Hapus</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Modal */}
      <Modal open={modalOpen} title={editing ? 'Edit Pengeluaran' : 'Tambah Pengeluaran'} onClose={() => setModalOpen(false)}>
        <div className="form-grid">
          <div className="form-group">
            <label>Tanggal *</label>
            <input className="input" type="date" value={form.tanggal} onChange={e => setForm({ ...form, tanggal: e.target.value })} />
          </div>
          <div className="form-group">
            <label>Jenis *</label>
            <select className="input" value={form.jenis} onChange={e => setForm({ ...form, jenis: e.target.value })}>
              {JENIS_OPTIONS.map(j => <option key={j.value} value={j.value}>{j.label}</option>)}
            </select>
          </div>
          <div className="form-group" style={{ gridColumn: '1 / -1' }}>
            <label>Keterangan *</label>
            <input className="input" value={form.keterangan} onChange={e => setForm({ ...form, keterangan: e.target.value })} placeholder="Misal: Uang Makan, Listrik, Tali Goni..." />
          </div>
          <div className="form-group">
            <label>Nominal (Rp) *</label>
            <input className="input" type="number" value={form.nominal} onChange={e => setForm({ ...form, nominal: Number(e.target.value) })} />
          </div>
          <div className="form-group">
            <label>Catatan</label>
            <input className="input" value={form.catatan} onChange={e => setForm({ ...form, catatan: e.target.value })} placeholder="Opsional" />
          </div>
        </div>
        {error && <p className="text-red" style={{ marginTop: 8 }}>{error}</p>}
        <div className="modal-footer">
          <button className="btn btn-ghost" onClick={() => setModalOpen(false)}>Batal</button>
          <button className="btn btn-solid" onClick={handleSave} disabled={saving || !form.keterangan || form.nominal <= 0}>
            {saving ? 'Menyimpan...' : editing ? 'Simpan Perubahan' : 'Tambah'}
          </button>
        </div>
      </Modal>
    </div>
  )
}

// ── Main Page ────────────────────────────────────────────────────────

export default function CatatanHarian() {
  const [activeTab, setActiveTab] = useState('cutting')

  const tabs = [
    { key: 'cutting', label: 'HASIL CUTTING' },
    { key: 'distribusi', label: 'DISTRIBUSI JAHIT' },
    { key: 'offline', label: 'PENGELUARAN OFFLINE' },
    { key: 'operasional', label: 'MODAL OPERASIONAL' },
  ]

  return (
    <div>
      <div className="page-header">
        <h2>Catatan Harian</h2>
      </div>

      {/* Tabs */}
      <div className="tabs">
        {tabs.map(tab => (
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
      {activeTab === 'cutting' && <HasilCuttingTab />}
      {activeTab === 'distribusi' && <DistribusiCuttingTab />}
      {activeTab === 'offline' && <PenjualanOfflineTab />}
      {activeTab === 'operasional' && <ModalOperasionalTab />}
    </div>
  )
}
