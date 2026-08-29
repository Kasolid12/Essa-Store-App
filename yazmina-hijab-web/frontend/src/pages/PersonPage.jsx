/**
 * Yazmina Hijab Web — Person Management Page.
 *
 * Person types: SUPPLIER, SUPPLIER_KAIN, KLIEN, KARYAWAN, PENJAHIT, LAINNYA
 * Features: list, search, filter by type, create, edit, soft-delete.
 */

import React, { useState, useEffect, useCallback } from 'react'
import { api } from '../api/client'
import Modal from '../components/Modal'

const EMPTY_PERSON = {
  nama: '',
  person_type: 'SUPPLIER',
  no_hp: '',
  alamat: '',
  catatan: '',
}

const TYPE_BADGE_COLORS = {
  SUPPLIER: 'badge-cyan',
  SUPPLIER_KAIN: 'badge-purple',
  KLIEN: 'badge-green',
  KARYAWAN: 'badge-yellow',
  PENJAHIT: 'badge-orange',
  LAINNYA: 'badge-gray',
}

export default function PersonPage() {
  const [items, setItems] = useState([])
  const [types, setTypes] = useState([])
  const [loading, setLoading] = useState(true)
  const [filterType, setFilterType] = useState('')
  const [search, setSearch] = useState('')

  // Modal state
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState(null)
  const [form, setForm] = useState(EMPTY_PERSON)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const fetchData = useCallback(async () => {
    setLoading(true)
    try {
      const [personList, typeList] = await Promise.all([
        api.listPersons({ person_type: filterType || undefined }),
        api.listPersonTypes(),
      ])
      setItems(personList)
      setTypes(typeList)
    } catch (err) {
      console.error('Gagal memuat data:', err)
    } finally {
      setLoading(false)
    }
  }, [filterType])

  useEffect(() => { fetchData() }, [fetchData])

  const handleCreate = () => {
    setEditing(null)
    setForm({ ...EMPTY_PERSON })
    setError('')
    setModalOpen(true)
  }

  const handleEdit = (row) => {
    setEditing(row)
    setForm({
      nama: row.nama,
      person_type: row.person_type,
      no_hp: row.no_hp || '',
      alamat: row.alamat || '',
      catatan: row.catatan || '',
    })
    setError('')
    setModalOpen(true)
  }

  const handleDelete = async (row) => {
    if (!confirm(`Hapus "${row.nama}"?`)) return
    try {
      await api.deletePerson(row.id)
      fetchData()
    } catch (err) {
      alert('Gagal hapus: ' + err.message)
    }
  }

  const handleSave = async () => {
    setError('')
    setSaving(true)
    try {
      if (editing) {
        await api.updatePerson(editing.id, form)
      } else {
        await api.createPerson(form)
      }
      setModalOpen(false)
      fetchData()
    } catch (err) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  // Client-side search filter
  const filteredItems = search
    ? items.filter(row =>
        row.nama.toLowerCase().includes(search.toLowerCase()) ||
        (row.no_hp || '').includes(search) ||
        (row.alamat || '').toLowerCase().includes(search.toLowerCase())
      )
    : items

  // Type label lookup
  const typeLabel = (t) => types.find(x => x.value === t)?.label || t

  return (
    <div>
      <div className="page-header">
        <h2>Data Person</h2>
        <button className="btn btn-solid" onClick={handleCreate}>
          + Tambah Person
        </button>
      </div>

      {/* Toolbar */}
      <div className="table-toolbar" style={{ marginBottom: 16 }}>
        <input
          className="input"
          type="text"
          placeholder="Cari nama/no HP/alamat..."
          value={search}
          onChange={e => setSearch(e.target.value)}
          style={{ maxWidth: 300 }}
        />
        <select
          className="input"
          value={filterType}
          onChange={e => setFilterType(e.target.value)}
          style={{ maxWidth: 200 }}
        >
          <option value="">Semua Tipe</option>
          {types.map(t => (
            <option key={t.value} value={t.value}>{t.label}</option>
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
                <th style={{ width: 200 }}>Nama</th>
                <th style={{ width: 130 }}>Tipe</th>
                <th style={{ width: 140 }}>No. HP</th>
                <th>Alamat</th>
                <th style={{ width: 120 }}>Status</th>
                <th style={{ width: 120 }}>Aksi</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={7} className="text-muted" style={{ padding: 32, textAlign: 'center' }}>
                    Memuat data...
                  </td>
                </tr>
              ) : filteredItems.length === 0 ? (
                <tr>
                  <td colSpan={7} className="text-muted" style={{ padding: 32, textAlign: 'center' }}>
                    Tidak ada data person
                  </td>
                </tr>
              ) : filteredItems.map((row, i) => (
                <tr key={row.id}>
                  <td className="text-muted">{i + 1}</td>
                  <td><strong>{row.nama}</strong></td>
                  <td>
                    <span className={`badge ${TYPE_BADGE_COLORS[row.person_type] || 'badge-gray'}`}>
                      {typeLabel(row.person_type)}
                    </span>
                  </td>
                  <td>{row.no_hp || '-'}</td>
                  <td className="text-muted" style={{ maxWidth: 250, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {row.alamat || '-'}
                  </td>
                  <td>
                    <span className={row.is_active ? 'badge badge-green' : 'badge badge-red'}>
                      {row.is_active ? 'Aktif' : 'Nonaktif'}
                    </span>
                  </td>
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
        title={editing ? `Edit Person — ${editing.nama}` : 'Tambah Person Baru'}
        onClose={() => setModalOpen(false)}
        width={560}
      >
        <div className="form-grid">
          <div className="form-group">
            <label>Nama *</label>
            <input
              className="input"
              value={form.nama}
              onChange={e => setForm({ ...form, nama: e.target.value })}
              placeholder="Nama lengkap"
            />
          </div>
          <div className="form-group">
            <label>Tipe *</label>
            <select
              className="input"
              value={form.person_type}
              onChange={e => setForm({ ...form, person_type: e.target.value })}
            >
              {types.map(t => (
                <option key={t.value} value={t.value}>{t.label}</option>
              ))}
            </select>
          </div>
          <div className="form-group">
            <label>No. HP</label>
            <input
              className="input"
              value={form.no_hp}
              onChange={e => setForm({ ...form, no_hp: e.target.value })}
              placeholder="08xxxxxxxxxx"
            />
          </div>
          <div className="form-group" style={{ gridColumn: '1 / -1' }}>
            <label>Alamat</label>
            <input
              className="input"
              value={form.alamat}
              onChange={e => setForm({ ...form, alamat: e.target.value })}
              placeholder="Alamat lengkap"
            />
          </div>
          <div className="form-group" style={{ gridColumn: '1 / -1' }}>
            <label>Catatan</label>
            <input
              className="input"
              value={form.catatan}
              onChange={e => setForm({ ...form, catatan: e.target.value })}
              placeholder="Catatan tambahan"
            />
          </div>
        </div>

        {error && <p className="text-red" style={{ marginTop: 8 }}>{error}</p>}

        <div className="modal-footer">
          <button className="btn btn-ghost" onClick={() => setModalOpen(false)}>Batal</button>
          <button
            className="btn btn-solid"
            onClick={handleSave}
            disabled={saving || !form.nama}
          >
            {saving ? 'Menyimpan...' : editing ? 'Simpan Perubahan' : 'Tambah'}
          </button>
        </div>
      </Modal>
    </div>
  )
}
