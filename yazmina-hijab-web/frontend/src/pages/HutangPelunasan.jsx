/**
 * Yazmina Hijab Web — Hutang & Pelunasan Page.
 *
 * Tabs:
 * 1. Barang Terhutang — goods debt from supplier
 * 2. Modal Hutang — capital/money loan
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

const STATUS_COLORS = {
  OPEN: 'badge-red',
  PARTIAL: 'badge-yellow',
  LUNAS: 'badge-green',
}

// ── Shared: Debt Table Component ─────────────────────────────────────

function DebtTable({ items, loading, onEdit, onDelete, onSelect }) {
  const [selectedIds, setSelectedIds] = useState(new Set())

  const toggleSelect = (id) => {
    setSelectedIds(prev => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const toggleAll = () => {
    if (selectedIds.size === items.length) {
      setSelectedIds(new Set())
    } else {
      setSelectedIds(new Set(items.map(i => i.id)))
    }
  }

  useEffect(() => {
    onSelect?.(items.filter(i => selectedIds.has(i.id)))
  }, [selectedIds])

  return (
    <div className="panel">
      <div className="table-container">
        <table className="data-table">
          <thead>
            <tr>
              <th style={{ width: 40 }}>
                <input type="checkbox" checked={selectedIds.size === items.length && items.length > 0} onChange={toggleAll} />
              </th>
              <th style={{ width: 48 }}>#</th>
              <th style={{ width: 110 }}>Tanggal</th>
              <th>Supplier / Pemberi</th>
              <th>Keterangan</th>
              <th style={{ width: 130, textAlign: 'right' }}>Hutang</th>
              <th style={{ width: 130, textAlign: 'right' }}>Terbayar</th>
              <th style={{ width: 130, textAlign: 'right' }}>Sisa</th>
              <th style={{ width: 90 }}>Status</th>
              <th style={{ width: 120 }}>Aksi</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={10} className="text-muted" style={{ padding: 32, textAlign: 'center' }}>Memuat data...</td></tr>
            ) : items.length === 0 ? (
              <tr><td colSpan={10} className="text-muted" style={{ padding: 32, textAlign: 'center' }}>Tidak ada data hutang</td></tr>
            ) : items.map((row, i) => (
              <tr key={row.id} style={{ background: selectedIds.has(row.id) ? 'rgba(0,240,255,0.06)' : undefined }}>
                <td>
                  <input type="checkbox" checked={selectedIds.has(row.id)} onChange={() => toggleSelect(row.id)} />
                </td>
                <td className="text-muted">{i + 1}</td>
                <td>{row.tanggal}</td>
                <td>{row.person_nama || '-'}</td>
                <td>{row.keterangan}</td>
                <td style={{ textAlign: 'right', fontFamily: 'Consolas, monospace' }}>{formatRp(row.nominal_hutang)}</td>
                <td style={{ textAlign: 'right', fontFamily: 'Consolas, monospace', color: 'var(--neon-green)' }}>{formatRp(row.terbayar)}</td>
                <td style={{ textAlign: 'right', fontFamily: 'Consolas, monospace', color: 'var(--neon-pink)', fontWeight: 'bold' }}>{formatRp(row.sisa)}</td>
                <td><span className={`badge ${STATUS_COLORS[row.status] || 'badge-gray'}`}>{row.status}</span></td>
                <td>
                  <button className="btn btn-ghost btn-sm" onClick={() => onEdit(row)} style={{ marginRight: 4 }}>Edit</button>
                  <button className="btn btn-ghost btn-sm text-red" onClick={() => onDelete(row)}>Hapus</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

// ── Tab: Barang Terhutang ────────────────────────────────────────────

function BarangTerhutangTab() {
  const [items, setItems] = useState([])
  const [skus, setSkus] = useState([])
  const [suppliers, setSuppliers] = useState([])
  const [loading, setLoading] = useState(true)
  const [summary, setSummary] = useState({})
  const [filterStatus, setFilterStatus] = useState('')

  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState(null)
  const [form, setForm] = useState({ tanggal: today(), person_id: '', sku_id: '', qty: 1, nominal_hutang: 0, keterangan: 'Hutang Barang', catatan: '' })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  // Payment modal
  const [payModalOpen, setPayModalOpen] = useState(false)
  const [selectedDebts, setSelectedDebts] = useState([])
  const [payForm, setPayForm] = useState({ tanggal_bayar: today(), nominal_bayar: 0, metode: 'CASH' })
  const [paySaving, setPaySaving] = useState(false)
  const [payError, setPayError] = useState('')

  const fetchData = useCallback(async () => {
    setLoading(true)
    try {
      const [list, sum, skuList, supplierList] = await Promise.all([
        api.listHutang({ tipe_hutang: 'BARANG', status: filterStatus || undefined }),
        api.summaryHutang({ tipe_hutang: 'BARANG' }),
        api.listSku(),
        api.listPersons({ person_type: 'SUPPLIER' }),
      ])
      setItems(list)
      setSummary(sum)
      setSkus(skuList)
      setSuppliers(supplierList)
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }, [filterStatus])

  useEffect(() => { fetchData() }, [fetchData])

  const handleCreate = () => {
    setEditing(null)
    setForm({ tanggal: today(), person_id: '', sku_id: '', qty: 1, nominal_hutang: 0, keterangan: 'Hutang Barang', catatan: '' })
    setError('')
    setModalOpen(true)
  }

  const handleEdit = (row) => {
    setEditing(row)
    setForm({ tanggal: row.tanggal, person_id: row.person_id, sku_id: row.sku_id || '', qty: row.qty || 1, nominal_hutang: row.nominal_hutang, keterangan: row.keterangan, catatan: row.catatan || '' })
    setError('')
    setModalOpen(true)
  }

  const handleDelete = async (row) => {
    if (!confirm(`Hapus hutang "${row.person_nama}" sebesar ${formatRp(row.nominal_hutang)}?`)) return
    try {
      await api.deleteHutang(row.id)
      fetchData()
    } catch (err) {
      alert('Gagal: ' + err.message)
    }
  }

  const handleSave = async () => {
    setError('')
    setSaving(true)
    try {
      const payload = { ...form, tipe_hutang: 'BARANG', person_id: Number(form.person_id), sku_id: form.sku_id ? Number(form.sku_id) : null, qty: Number(form.qty), nominal_hutang: Number(form.nominal_hutang) }
      if (editing) {
        await api.updateHutang(editing.id, payload)
      } else {
        await api.createHutang(payload)
      }
      setModalOpen(false)
      fetchData()
    } catch (err) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  const handlePay = () => {
    if (selectedDebts.length === 0) return
    const totalSisa = selectedDebts.reduce((s, d) => s + d.sisa, 0)
    setPayForm({ tanggal_bayar: today(), nominal_bayar: totalSisa, metode: 'CASH' })
    setPayError('')
    setPayModalOpen(true)
  }

  const handlePaySubmit = async () => {
    setPayError('')
    setPaySaving(true)
    try {
      await api.batchPay({
        debt_ids: selectedDebts.map(d => d.id),
        tanggal_bayar: payForm.tanggal_bayar,
        nominal_total: Number(payForm.nominal_bayar),
        metode: payForm.metode,
      })
      setPayModalOpen(false)
      setSelectedDebts([])
      fetchData()
    } catch (err) {
      setPayError(err.message)
    } finally {
      setPaySaving(false)
    }
  }

  return (
    <div>
      {/* Summary */}
      <div className="kpi-grid" style={{ marginBottom: 16 }}>
        <div className="kpi-card">
          <div className="kpi-label">TOTAL HUTANG</div>
          <div className="kpi-value text-pink">{formatRp(summary.total_hutang)}</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-label">TERBAYAR</div>
          <div className="kpi-value text-green">{formatRp(summary.total_terbayar)}</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-label">SISA HUTANG</div>
          <div className="kpi-value text-yellow">{formatRp(summary.total_sisa)}</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-label">STATUS</div>
          <div className="kpi-value text-cyan">
            {summary.count_open || 0} OPEN · {summary.count_partial || 0} PARTIAL · {summary.count_lunas || 0} LUNAS
          </div>
        </div>
      </div>

      {/* Toolbar */}
      <div className="table-toolbar" style={{ marginBottom: 16 }}>
        <button className="btn btn-solid" onClick={handleCreate}>+ Catat Hutang Barang</button>
        <select className="input" value={filterStatus} onChange={e => setFilterStatus(e.target.value)} style={{ maxWidth: 150 }}>
          <option value="">Semua Status</option>
          <option value="OPEN">OPEN</option>
          <option value="PARTIAL">PARTIAL</option>
          <option value="LUNAS">LUNAS</option>
        </select>
        {selectedDebts.length > 0 && selectedDebts.some(d => d.status !== 'LUNAS') && (
          <button className="btn btn-solid-yellow" onClick={handlePay}>
            BAYAR ({selectedDebts.length} dipilih) — Total Sisa: {formatRp(selectedDebts.reduce((s, d) => s + d.sisa, 0))}
          </button>
        )}
      </div>

      {/* Table */}
      <DebtTable items={items} loading={loading} onEdit={handleEdit} onDelete={handleDelete} onSelect={setSelectedDebts} />

      {/* Create/Edit Modal */}
      <Modal open={modalOpen} title={editing ? 'Edit Hutang Barang' : 'Catat Hutang Barang Baru'} onClose={() => setModalOpen(false)}>
        <div className="form-grid">
          <div className="form-group">
            <label>Tanggal *</label>
            <input className="input" type="date" value={form.tanggal} onChange={e => setForm({ ...form, tanggal: e.target.value })} />
          </div>
          <div className="form-group">
            <label>Supplier *</label>
            <select className="input" value={form.person_id} onChange={e => setForm({ ...form, person_id: e.target.value })}>
              <option value="">-- Pilih Supplier --</option>
              {suppliers.map(s => <option key={s.id} value={s.id}>{s.nama}</option>)}
            </select>
          </div>
          <div className="form-group">
            <label>SKU</label>
            <select className="input" value={form.sku_id} onChange={e => setForm({ ...form, sku_id: e.target.value })}>
              <option value="">-- Pilih SKU --</option>
              {skus.map(s => <option key={s.id} value={s.id}>{s.kode_sku} - {s.nama_produk}</option>)}
            </select>
          </div>
          <div className="form-group">
            <label>Qty</label>
            <input className="input" type="number" min="0" step="0.1" value={form.qty} onChange={e => setForm({ ...form, qty: e.target.value })} />
          </div>
          <div className="form-group">
            <label>Total Hutang (Rp) *</label>
            <input className="input" type="number" value={form.nominal_hutang} onChange={e => setForm({ ...form, nominal_hutang: e.target.value })} />
          </div>
          <div className="form-group">
            <label>Keterangan</label>
            <input className="input" value={form.keterangan} onChange={e => setForm({ ...form, keterangan: e.target.value })} />
          </div>
          <div className="form-group" style={{ gridColumn: '1 / -1' }}>
            <label>Catatan</label>
            <input className="input" value={form.catatan} onChange={e => setForm({ ...form, catatan: e.target.value })} placeholder="Opsional" />
          </div>
        </div>
        {error && <p className="text-red" style={{ marginTop: 8 }}>{error}</p>}
        <div className="modal-footer">
          <button className="btn btn-ghost" onClick={() => setModalOpen(false)}>Batal</button>
          <button className="btn btn-solid" onClick={handleSave} disabled={saving || !form.person_id || !form.nominal_hutang}>
            {saving ? 'Menyimpan...' : editing ? 'Simpan Perubahan' : 'Tambah'}
          </button>
        </div>
      </Modal>

      {/* Payment Modal */}
      <Modal open={payModalOpen} title={`Bayar Hutang (${selectedDebts.length} tagihan)`} onClose={() => setPayModalOpen(false)}>
        <div className="form-grid">
          <div className="form-group">
            <label>Tanggal Bayar *</label>
            <input className="input" type="date" value={payForm.tanggal_bayar} onChange={e => setPayForm({ ...payForm, tanggal_bayar: e.target.value })} />
          </div>
          <div className="form-group">
            <label>Nominal Bayar (Rp) *</label>
            <input className="input" type="number" value={payForm.nominal_bayar} onChange={e => setPayForm({ ...payForm, nominal_bayar: e.target.value })} />
          </div>
          <div className="form-group">
            <label>Metode</label>
            <select className="input" value={payForm.metode} onChange={e => setPayForm({ ...payForm, metode: e.target.value })}>
              <option value="CASH">Cash</option>
              <option value="TRANSFER">Transfer</option>
              <option value="POTONG_BON">Potong Bon</option>
            </select>
          </div>
        </div>
        <p className="text-muted" style={{ marginTop: 8, fontSize: 12 }}>
          Total sisa: {formatRp(selectedDebts.reduce((s, d) => s + d.sisa, 0))} — Nominal akan dibagi otomatis ke tiap tagihan.
        </p>
        {payError && <p className="text-red" style={{ marginTop: 8 }}>{payError}</p>}
        <div className="modal-footer">
          <button className="btn btn-ghost" onClick={() => setPayModalOpen(false)}>Batal</button>
          <button className="btn btn-solid" onClick={handlePaySubmit} disabled={paySaving || !payForm.nominal_bayar}>
            {paySaving ? 'Memproses...' : 'Bayar'}
          </button>
        </div>
      </Modal>
    </div>
  )
}

// ── Tab: Modal Hutang ────────────────────────────────────────────────

function ModalHutangTab() {
  const [items, setItems] = useState([])
  const [suppliers, setSuppliers] = useState([])
  const [loading, setLoading] = useState(true)
  const [summary, setSummary] = useState({})
  const [filterStatus, setFilterStatus] = useState('')

  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState(null)
  const [form, setForm] = useState({ tanggal: today(), person_id: '', keterangan: '', qty: 1, nominal_hutang: 0, kode_produksi: '', catatan: '' })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const [payModalOpen, setPayModalOpen] = useState(false)
  const [selectedDebts, setSelectedDebts] = useState([])
  const [payForm, setPayForm] = useState({ tanggal_bayar: today(), nominal_bayar: 0, metode: 'CASH' })
  const [paySaving, setPaySaving] = useState(false)
  const [payError, setPayError] = useState('')

  const fetchData = useCallback(async () => {
    setLoading(true)
    try {
      const [list, sum, supplierList] = await Promise.all([
        api.listHutang({ tipe_hutang: 'MODAL', status: filterStatus || undefined }),
        api.summaryHutang({ tipe_hutang: 'MODAL' }),
        api.listPersons({ person_type: 'SUPPLIER' }),
      ])
      setItems(list)
      setSummary(sum)
      setSuppliers(supplierList)
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }, [filterStatus])

  useEffect(() => { fetchData() }, [fetchData])

  const handleCreate = () => {
    setEditing(null)
    setForm({ tanggal: today(), person_id: '', keterangan: '', qty: 1, nominal_hutang: 0, kode_produksi: '', catatan: '' })
    setError('')
    setModalOpen(true)
  }

  const handleEdit = (row) => {
    setEditing(row)
    setForm({ tanggal: row.tanggal, person_id: row.person_id, keterangan: row.keterangan, qty: row.qty || 1, nominal_hutang: row.nominal_hutang, kode_produksi: row.kode_produksi || '', catatan: row.catatan || '' })
    setError('')
    setModalOpen(true)
  }

  const handleDelete = async (row) => {
    if (!confirm(`Hapus hutang modal "${row.person_nama}" sebesar ${formatRp(row.nominal_hutang)}?`)) return
    try {
      await api.deleteHutang(row.id)
      fetchData()
    } catch (err) {
      alert('Gagal: ' + err.message)
    }
  }

  const handleSave = async () => {
    setError('')
    setSaving(true)
    try {
      const payload = { ...form, tipe_hutang: 'MODAL', person_id: Number(form.person_id), qty: Number(form.qty), nominal_hutang: Number(form.nominal_hutang) }
      if (editing) {
        await api.updateHutang(editing.id, payload)
      } else {
        await api.createHutang(payload)
      }
      setModalOpen(false)
      fetchData()
    } catch (err) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  const handlePay = () => {
    if (selectedDebts.length === 0) return
    const totalSisa = selectedDebts.reduce((s, d) => s + d.sisa, 0)
    setPayForm({ tanggal_bayar: today(), nominal_bayar: totalSisa, metode: 'CASH' })
    setPayError('')
    setPayModalOpen(true)
  }

  const handlePaySubmit = async () => {
    setPayError('')
    setPaySaving(true)
    try {
      await api.batchPay({
        debt_ids: selectedDebts.map(d => d.id),
        tanggal_bayar: payForm.tanggal_bayar,
        nominal_total: Number(payForm.nominal_bayar),
        metode: payForm.metode,
      })
      setPayModalOpen(false)
      setSelectedDebts([])
      fetchData()
    } catch (err) {
      setPayError(err.message)
    } finally {
      setPaySaving(false)
    }
  }

  return (
    <div>
      {/* Summary */}
      <div className="kpi-grid" style={{ marginBottom: 16 }}>
        <div className="kpi-card">
          <div className="kpi-label">TOTAL MODAL</div>
          <div className="kpi-value text-pink">{formatRp(summary.total_hutang)}</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-label">TERBAYAR / DEPOSIT</div>
          <div className="kpi-value text-green">{formatRp(summary.total_terbayar)}</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-label">SISA</div>
          <div className="kpi-value text-yellow">{formatRp(summary.total_sisa)}</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-label">STATUS</div>
          <div className="kpi-value text-cyan">
            {summary.count_open || 0} OPEN · {summary.count_partial || 0} PARTIAL · {summary.count_lunas || 0} LUNAS
          </div>
        </div>
      </div>

      {/* Toolbar */}
      <div className="table-toolbar" style={{ marginBottom: 16 }}>
        <button className="btn btn-solid" onClick={handleCreate}>+ Catat Pinjaman Modal</button>
        <select className="input" value={filterStatus} onChange={e => setFilterStatus(e.target.value)} style={{ maxWidth: 150 }}>
          <option value="">Semua Status</option>
          <option value="OPEN">OPEN</option>
          <option value="PARTIAL">PARTIAL</option>
          <option value="LUNAS">LUNAS</option>
        </select>
        {selectedDebts.length > 0 && selectedDebts.some(d => d.status !== 'LUNAS') && (
          <button className="btn btn-solid-yellow" onClick={handlePay}>
            SETOR DEPOSIT ({selectedDebts.length} dipilih)
          </button>
        )}
      </div>

      {/* Table */}
      <DebtTable items={items} loading={loading} onEdit={handleEdit} onDelete={handleDelete} onSelect={setSelectedDebts} />

      {/* Create/Edit Modal */}
      <Modal open={modalOpen} title={editing ? 'Edit Hutang Modal' : 'Catat Pinjaman Modal Baru'} onClose={() => setModalOpen(false)}>
        <div className="form-grid">
          <div className="form-group">
            <label>Tanggal *</label>
            <input className="input" type="date" value={form.tanggal} onChange={e => setForm({ ...form, tanggal: e.target.value })} />
          </div>
          <div className="form-group">
            <label>Pemberi Modal *</label>
            <select className="input" value={form.person_id} onChange={e => setForm({ ...form, person_id: e.target.value })}>
              <option value="">-- Pilih Pemberi Modal --</option>
              {suppliers.map(s => <option key={s.id} value={s.id}>{s.nama}</option>)}
            </select>
          </div>
          <div className="form-group">
            <label>Kode Batch</label>
            <input className="input" value={form.kode_produksi} onChange={e => setForm({ ...form, kode_produksi: e.target.value })} placeholder="PRD-MMYY-001" />
          </div>
          <div className="form-group">
            <label>Jenis / Keterangan *</label>
            <input className="input" value={form.keterangan} onChange={e => setForm({ ...form, keterangan: e.target.value })} placeholder="Kain Jersey, Label, Modal Tunai..." />
          </div>
          <div className="form-group">
            <label>Qty</label>
            <input className="input" type="number" min="0" step="0.1" value={form.qty} onChange={e => setForm({ ...form, qty: e.target.value })} />
          </div>
          <div className="form-group">
            <label>Total Hutang (Rp) *</label>
            <input className="input" type="number" value={form.nominal_hutang} onChange={e => setForm({ ...form, nominal_hutang: e.target.value })} />
          </div>
          <div className="form-group" style={{ gridColumn: '1 / -1' }}>
            <label>Catatan</label>
            <input className="input" value={form.catatan} onChange={e => setForm({ ...form, catatan: e.target.value })} placeholder="Opsional" />
          </div>
        </div>
        {error && <p className="text-red" style={{ marginTop: 8 }}>{error}</p>}
        <div className="modal-footer">
          <button className="btn btn-ghost" onClick={() => setModalOpen(false)}>Batal</button>
          <button className="btn btn-solid" onClick={handleSave} disabled={saving || !form.person_id || !form.keterangan || !form.nominal_hutang}>
            {saving ? 'Menyimpan...' : editing ? 'Simpan Perubahan' : 'Tambah'}
          </button>
        </div>
      </Modal>

      {/* Payment Modal */}
      <Modal open={payModalOpen} title={`Setor Deposit (${selectedDebts.length} pinjaman)`} onClose={() => setPayModalOpen(false)}>
        <div className="form-grid">
          <div className="form-group">
            <label>Tanggal Deposit *</label>
            <input className="input" type="date" value={payForm.tanggal_bayar} onChange={e => setPayForm({ ...payForm, tanggal_bayar: e.target.value })} />
          </div>
          <div className="form-group">
            <label>Nominal Deposit (Rp) *</label>
            <input className="input" type="number" value={payForm.nominal_bayar} onChange={e => setPayForm({ ...payForm, nominal_bayar: e.target.value })} />
          </div>
          <div className="form-group">
            <label>Metode</label>
            <select className="input" value={payForm.metode} onChange={e => setPayForm({ ...payForm, metode: e.target.value })}>
              <option value="CASH">Cash</option>
              <option value="TRANSFER">Transfer</option>
            </select>
          </div>
        </div>
        <p className="text-muted" style={{ marginTop: 8, fontSize: 12 }}>
          Total sisa: {formatRp(selectedDebts.reduce((s, d) => s + d.sisa, 0))} — Nominal akan dibagi otomatis.
        </p>
        {payError && <p className="text-red" style={{ marginTop: 8 }}>{payError}</p>}
        <div className="modal-footer">
          <button className="btn btn-ghost" onClick={() => setPayModalOpen(false)}>Batal</button>
          <button className="btn btn-solid" onClick={handlePaySubmit} disabled={paySaving || !payForm.nominal_bayar}>
            {paySaving ? 'Memproses...' : 'Setor'}
          </button>
        </div>
      </Modal>
    </div>
  )
}

// ── Main Page ────────────────────────────────────────────────────────

export default function HutangPelunasan() {
  const [activeTab, setActiveTab] = useState('barang')

  const tabs = [
    { key: 'barang', label: 'BARANG TERHUTANG' },
    { key: 'modal', label: 'MODAL HUTANG' },
  ]

  return (
    <div>
      <div className="page-header">
        <h2>Hutang & Pelunasan</h2>
      </div>

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

      {activeTab === 'barang' && <BarangTerhutangTab />}
      {activeTab === 'modal' && <ModalHutangTab />}
    </div>
  )
}
