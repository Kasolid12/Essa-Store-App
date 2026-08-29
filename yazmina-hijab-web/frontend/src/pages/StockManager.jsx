import React, { useState, useRef, useCallback } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'

function formatRp(val) {
  return 'Rp ' + Number(val || 0).toLocaleString('id-ID')
}

export default function StockManager() {
  const [search, setSearch] = useState('')
  const [staging, setStaging] = useState([]) // [{sku, qty, harga}]
  const [selectedSku, setSelectedSku] = useState(null)
  const [qty, setQty] = useState(1)
  const [harga, setHarga] = useState(0)
  const [exporting, setExporting] = useState(false)
  const [selectedRows, setSelectedRows] = useState(new Set())
  const searchTimeout = useRef(null)

  // ── SKU Search ────────────────────────────────────────────────────
  const { data: skuList } = useQuery({
    queryKey: ['stock-skus', search],
    queryFn: () => api.listStockSkus(search),
    enabled: true,
  })

  const skus = skuList || []

  // ── Add to Staging ────────────────────────────────────────────────
  const addToStaging = () => {
    if (!selectedSku) return
    const existing = staging.find(s => s.sku === selectedSku.kode_sku)
    if (existing) {
      setStaging(staging.map(s =>
        s.sku === selectedSku.kode_sku
          ? { ...s, qty: s.qty + qty, harga: harga || s.harga }
          : s
      ))
    } else {
      setStaging([...staging, {
        sku: selectedSku.kode_sku,
        nama: selectedSku.nama_produk,
        qty,
        harga: harga || selectedSku.harga_jual || 0,
      }])
    }
    setQty(1)
    setHarga(0)
    setSelectedSku(null)
    setSearch('')
  }

  // ── Delete from Staging ───────────────────────────────────────────
  const deleteSelected = () => {
    setStaging(staging.filter((_, i) => !selectedRows.has(i)))
    setSelectedRows(new Set())
  }

  const toggleRow = (idx) => {
    const next = new Set(selectedRows)
    next.has(idx) ? next.delete(idx) : next.add(idx)
    setSelectedRows(next)
  }

  const toggleAll = () => {
    if (selectedRows.size === staging.length) {
      setSelectedRows(new Set())
    } else {
      setSelectedRows(new Set(staging.map((_, i) => i)))
    }
  }

  // ── Export ────────────────────────────────────────────────────────
  const handleExport = async (mode) => {
    if (staging.length === 0) return
    setExporting(true)
    try {
      await api.exportStock(
        staging.map(s => ({ sku: s.sku, qty: s.qty, harga: s.harga })),
        mode
      )
    } catch (err) {
      alert('Gagal export: ' + err.message)
    } finally {
      setExporting(false)
    }
  }

  // ── SKU Dropdown Selection ────────────────────────────────────────
  const handleSkuSelect = (e) => {
    const kode = e.target.value
    const found = skus.find(s => s.kode_sku === kode)
    setSelectedSku(found || null)
    if (found && !harga) setHarga(found.harga_jual || 0)
  }

  return (
    <div>
      {/* Header */}
      <div className="page-header">
        <h2 className="text-cyan">📦 INVENTORY & BIGSELLER SYNC</h2>
      </div>

      {/* Tab: Staging & Export */}
      <div className="panel">
        <h3 className="text-cyan" style={{ marginBottom: 16, fontSize: 14, letterSpacing: 1 }}>
          STAGING & EXPORT (BIGSELLER)
        </h3>

        {/* Input Form */}
        <div className="table-toolbar" style={{ marginBottom: 16 }}>
          <div className="form-group" style={{ margin: 0, minWidth: 300 }}>
            <label>Pilih SKU</label>
            <select
              className="input"
              value={selectedSku?.kode_sku || ''}
              onChange={handleSkuSelect}
            >
              <option value="">-- Pilih SKU --</option>
              {skus.map(s => (
                <option key={s.id} value={s.kode_sku}>
                  {s.kode_sku} — {s.nama_produk}
                </option>
              ))}
            </select>
          </div>

          <div className="form-group" style={{ margin: 0 }}>
            <label>Qty</label>
            <input
              type="number"
              className="input"
              value={qty}
              onChange={e => setQty(Math.max(1, parseInt(e.target.value) || 1))}
              min="1"
              style={{ width: 80 }}
            />
          </div>

          <div className="form-group" style={{ margin: 0 }}>
            <label>Harga (opsional)</label>
            <input
              type="number"
              className="input"
              value={harga}
              onChange={e => setHarga(parseFloat(e.target.value) || 0)}
              min="0"
              style={{ width: 140 }}
            />
          </div>

          <button
            className="btn"
            onClick={addToStaging}
            disabled={!selectedSku}
            style={{ alignSelf: 'flex-end' }}
          >
            + TAMBAHKAN
          </button>
        </div>

        {/* Staging Table */}
        {staging.length === 0 ? (
          <div className="text-muted" style={{ padding: '24px 0', textAlign: 'center' }}>
            Belum ada item di staging. Pilih SKU dan klik TAMBAHKAN.
          </div>
        ) : (
          <>
            <div className="table-container">
              <table className="data-table">
                <thead>
                  <tr>
                    <th style={{ width: 40 }}>
                      <input
                        type="checkbox"
                        checked={selectedRows.size === staging.length && staging.length > 0}
                        onChange={toggleAll}
                      />
                    </th>
                    <th>Kode SKU</th>
                    <th>Nama Produk</th>
                    <th className="text-right">Qty</th>
                    <th className="text-right">Harga Satuan</th>
                    <th className="text-right">Subtotal</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {staging.map((item, i) => (
                    <tr key={i} style={{ cursor: 'pointer' }} onClick={() => toggleRow(i)}>
                      <td>
                        <input
                          type="checkbox"
                          checked={selectedRows.has(i)}
                          onChange={() => toggleRow(i)}
                          onClick={e => e.stopPropagation()}
                        />
                      </td>
                      <td className="font-mono">{item.sku}</td>
                      <td>{item.nama}</td>
                      <td className="text-right font-mono">
                        <input
                          type="number"
                          className="input"
                          value={item.qty}
                          onChange={e => {
                            const val = Math.max(1, parseInt(e.target.value) || 1)
                            setStaging(staging.map((s, j) => j === i ? { ...s, qty: val } : s))
                          }}
                          onClick={e => e.stopPropagation()}
                          style={{ width: 70, textAlign: 'right' }}
                          min="1"
                        />
                      </td>
                      <td className="text-right font-mono">
                        <input
                          type="number"
                          className="input"
                          value={item.harga}
                          onChange={e => {
                            const val = parseFloat(e.target.value) || 0
                            setStaging(staging.map((s, j) => j === i ? { ...s, harga: val } : s))
                          }}
                          onClick={e => e.stopPropagation()}
                          style={{ width: 120, textAlign: 'right' }}
                          min="0"
                        />
                      </td>
                      <td className="text-right font-mono text-green">
                        {formatRp(item.qty * item.harga)}
                      </td>
                      <td>
                        <span className="badge badge-green">Siap Export</span>
                      </td>
                    </tr>
                  ))}
                </tbody>
                <tfoot>
                  <tr>
                    <td colSpan="3" className="text-muted" style={{ fontWeight: 'bold' }}>
                      Total {staging.length} item
                    </td>
                    <td className="text-right font-mono" style={{ fontWeight: 'bold' }}>
                      {staging.reduce((s, i) => s + i.qty, 0).toLocaleString('id-ID')}
                    </td>
                    <td></td>
                    <td className="text-right font-mono text-green" style={{ fontWeight: 'bold' }}>
                      {formatRp(staging.reduce((s, i) => s + i.qty * i.harga, 0))}
                    </td>
                    <td></td>
                  </tr>
                </tfoot>
              </table>
            </div>

            {/* Action Buttons */}
            <div className="table-toolbar" style={{ marginTop: 16 }}>
              <button
                className="btn btn-danger btn-sm"
                onClick={deleteSelected}
                disabled={selectedRows.size === 0}
              >
                🗑 HAPUS BARIS ({selectedRows.size})
              </button>
              <div style={{ flex: 1 }} />
              <button
                className="btn"
                onClick={() => handleExport('stock_in')}
                disabled={exporting || staging.length === 0}
              >
                📥 EXPORT PENAMBAHAN (IN)
              </button>
              <button
                className="btn btn-sm"
                style={{ borderColor: 'var(--neon-yellow)', color: 'var(--neon-yellow)' }}
                onClick={() => handleExport('stock_out')}
                disabled={exporting || staging.length === 0}
              >
                📤 EXPORT PENGURANGAN (OUT)
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
