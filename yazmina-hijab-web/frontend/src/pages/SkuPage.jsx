/**
 * Yazmina Hijab Web — SKU Management Page.
 *
 * Features: list, search, filter by kategori, create, edit, soft-delete.
 */

import React, { useState, useEffect, useCallback } from 'react'
import { api } from '../api/client'
import DataTable from '../components/DataTable'
import Modal from '../components/Modal'

const EMPTY_SKU = {
  kode_sku: '',
  nama_produk: '',
  kategori: '',
  model: '',
  warna: '',
  ukuran: '',
  gtin: '',
  harga_jual: 0,
  harga_modal: 0,
  kain_cost: 0,
  potongan_cost: 0,
}

function formatRp(val) {
  if (!val) return 'Rp 0'
  return 'Rp ' + Number(val).toLocaleString('id-ID')
}

export default function SkuPage() {
  const [items, setItems] = useState([])
  const [categories, setCategories] = useState([])
  const [loading, setLoading] = useState(true)
  const [filterKategori, setFilterKategori] = useState('')
  const [search, setSearch] = useState('')

  // Modal state
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState(null) // null = create, object = edit
  const [form, setForm] = useState(EMPTY_SKU)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const fetchData = useCallback(async () => {
    setLoading(true)
    try {
      const [skuList, catList] = await Promise.all([
        api.listSku({ kategori: filterKategori || undefined }),
        api.listSkuCategories(),
      ])
      setItems(skuList)
      setCategories(catList)
    } catch (err) {
      console.error('Gagal memuat SKU:', err)
    } finally {
      setLoading(false)
    }
  }, [filterKategori])

  useEffect(() => { fetchData() }, [fetchData])

  // Open create modal
  const handleCreate = () => {
    setEditing(null)
    setForm({ ...EMPTY_SKU })
    setError('')
    setModalOpen(true)
  }

  // Open edit modal
  const handleEdit = (row) => {
    setEditing(row)
    setForm({
      kode_sku: row.kode_sku,
      nama_produk: row.nama_produk,
      kategori: row.kategori || '',
      model: row.model || '',
      warna: row.warna || '',
      ukuran: row.ukuran || '',
      gtin: row.gtin || '',
      harga_jual: row.harga_jual || 0,
      harga_modal: row.harga_modal || 0,
      kain_cost: row.kain_cost || 0,
      potongan_cost: row.potongan_cost || 0,
    })
    setError('')
    setModalOpen(true)
  }

  // Handle delete
  const handleDelete = async (row) => {
    if (!confirm(`Hapus SKU "${row.kode_sku} - ${row.nama_produk}"?`)) return
    try {
      await api.deleteSku(row.id)
      fetchData()
    } catch (err) {
      alert('Gagal hapus: ' + err.message)
    }
  }

  // Handle save (create or update)
  const handleSave = async () => {
    setError('')
    setSaving(true)
    try {
      if (editing) {
        await api.updateSku(editing.id, form)
      } else {
        await api.createSku(form)
      }
      setModalOpen(false)
      fetchData()
    } catch (err) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  // Filter data by search (client-side)
  const filteredItems = search
    ? items.filter(row =>
        row.kode_sku.toLowerCase().includes(search.toLowerCase()) ||
        row.nama_produk.toLowerCase().includes(search.toLowerCase()) ||
        (row.model || '').toLowerCase().includes(search.toLowerCase())
      )
    : items

  // Table columns
  const columns = [
    { key: 'kode_sku', label: 'Kode SKU', width: 120 },
    { key: 'nama_produk', label: 'Nama Produk' },
    { key: 'kategori', label: 'Kategori', width: 120 },
    { key: 'model', label: 'Model', width: 80 },
    { key: 'warna', label: 'Warna', width: 100 },
    { key: 'ukuran', label: 'Ukuran', width: 80 },
    {
      key: 'harga_jual',
      label: 'Harga Jual',
      width: 130,
      render: (v) => formatRp(v),
    },
    {
      key: 'is_active',
      label: 'Status',
      width: 80,
      render: (v) => (
        <span className={v ? 'badge badge-green' : 'badge badge-red'}>
          {v ? 'Aktif' : 'Nonaktif'}
        </span>
      ),
    },
  ]

  return (
    <div>
      <div className="page-header">
        <h2>Master SKU</h2>
        <button className="btn btn-solid" onClick={handleCreate}>
          + Tambah SKU
        </button>
      </div>

      {/* Toolbar */}
      <div className="table-toolbar" style={{ marginBottom: 16 }}>
        <input
          className="input"
          type="text"
          placeholder="Cari kode/nama/model..."
          value={search}
          onChange={e => setSearch(e.target.value)}
          style={{ maxWidth: 300 }}
        />
        <select
          className="input"
          value={filterKategori}
          onChange={e => setFilterKategori(e.target.value)}
          style={{ maxWidth: 200 }}
        >
          <option value="">Semua Kategori</option>
          {categories.map(c => (
            <option key={c} value={c}>{c}</option>
          ))}
        </select>
        <span className="text-muted" style={{ fontSize: 13 }}>
          {filteredItems.length} data
        </span>
      </div>

      {/* Table */}
      <div className="panel">
        <div className="table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th style={{ width: 48 }}>#</th>
                {columns.map(col => (
                  <th key={col.key} style={{ width: col.width }}>{col.label}</th>
                ))}
                <th style={{ width: 120 }}>Aksi</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={columns.length + 2} className="text-muted" style={{ padding: 32, textAlign: 'center' }}>
                    Memuat data...
                  </td>
                </tr>
              ) : filteredItems.length === 0 ? (
                <tr>
                  <td colSpan={columns.length + 2} className="text-muted" style={{ padding: 32, textAlign: 'center' }}>
                    Tidak ada data SKU
                  </td>
                </tr>
              ) : filteredItems.map((row, i) => (
                <tr key={row.id}>
                  <td className="text-muted">{i + 1}</td>
                  {columns.map(col => (
                    <td key={col.key}>
                      {col.render ? col.render(row[col.key], row) : (row[col.key] ?? '-')}
                    </td>
                  ))}
                  <td>
                    <button
                      className="btn btn-ghost btn-sm"
                      onClick={() => handleEdit(row)}
                      style={{ marginRight: 4 }}
                    >
                      Edit
                    </button>
                    <button
                      className="btn btn-ghost btn-sm text-red"
                      onClick={() => handleDelete(row)}
                    >
                      Hapus
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Modal Form */}
      <Modal
        open={modalOpen}
        title={editing ? `Edit SKU — ${editing.kode_sku}` : 'Tambah SKU Baru'}
        onClose={() => setModalOpen(false)}
        width={600}
      >
        <div className="form-grid">
          <div className="form-group">
            <label>Kode SKU *</label>
            <input
              className="input"
              value={form.kode_sku}
              onChange={e => setForm({ ...form, kode_sku: e.target.value })}
              placeholder="Contoh: JSO-BL-M"
            />
          </div>
          <div className="form-group">
            <label>Nama Produk *</label>
            <input
              className="input"
              value={form.nama_produk}
              onChange={e => setForm({ ...form, nama_produk: e.target.value })}
              placeholder="Contoh: Jilbab Sovie"
            />
          </div>
          <div className="form-group">
            <label>Kategori</label>
            <input
              className="input"
              value={form.kategori}
              onChange={e => setForm({ ...form, kategori: e.target.value })}
              placeholder="Contoh: Jilbab"
            />
          </div>
          <div className="form-group">
            <label>Model</label>
            <input
              className="input"
              value={form.model}
              onChange={e => setForm({ ...form, model: e.target.value })}
              placeholder="Contoh: JSO"
            />
          </div>
          <div className="form-group">
            <label>Warna</label>
            <input
              className="input"
              value={form.warna}
              onChange={e => setForm({ ...form, warna: e.target.value })}
              placeholder="Contoh: Black"
            />
          </div>
          <div className="form-group">
            <label>Ukuran</label>
            <input
              className="input"
              value={form.ukuran}
              onChange={e => setForm({ ...form, ukuran: e.target.value })}
              placeholder="Contoh: M"
            />
          </div>
          <div className="form-group">
            <label>Harga Jual</label>
            <input
              className="input"
              type="number"
              value={form.harga_jual}
              onChange={e => setForm({ ...form, harga_jual: Number(e.target.value) })}
            />
          </div>
          <div className="form-group">
            <label>Harga Modal</label>
            <input
              className="input"
              type="number"
              value={form.harga_modal}
              onChange={e => setForm({ ...form, harga_modal: Number(e.target.value) })}
            />
          </div>
          <div className="form-group">
            <label>Biaya Kain</label>
            <input
              className="input"
              type="number"
              value={form.kain_cost}
              onChange={e => setForm({ ...form, kain_cost: Number(e.target.value) })}
            />
          </div>
          <div className="form-group">
            <label>Biaya Potongan</label>
            <input
              className="input"
              type="number"
              value={form.potongan_cost}
              onChange={e => setForm({ ...form, potongan_cost: Number(e.target.value) })}
            />
          </div>
        </div>

        {error && <p className="text-red" style={{ marginTop: 8 }}>{error}</p>}

        <div className="modal-footer">
          <button className="btn btn-ghost" onClick={() => setModalOpen(false)}>Batal</button>
          <button
            className="btn btn-solid"
            onClick={handleSave}
            disabled={saving || !form.kode_sku || !form.nama_produk}
          >
            {saving ? 'Menyimpan...' : editing ? 'Simpan Perubahan' : 'Tambah'}
          </button>
        </div>
      </Modal>
    </div>
  )
}
