/**
 * Yazmina Hijab Web — Invoice & Piutang Page.
 *
 * Features (matching desktop invoice_view.py):
 * 1. Client dropdown (Client + Person with sales)
 * 2. Combined transaction table (sales + payments) with running balance & FIFO status
 * 3. Summary KPI cards: Total Tagihan, Total Dibayar, Sisa Piutang, Status
 * 4. Deposit form (amount, date, method)
 * 5. Delete payment
 */

import React, { useState, useEffect, useCallback } from 'react'
import { api } from '../api/client'

// ── Helpers ──────────────────────────────────────────────────────

function formatRp(val) {
  if (!val || val === 0) return 'Rp 0'
  return 'Rp ' + Number(val).toLocaleString('id-ID')
}

function today() {
  return new Date().toISOString().slice(0, 10)
}

// ══════════════════════════════════════════════════════════════════════
// MAIN PAGE
// ══════════════════════════════════════════════════════════════════════

export default function Invoice() {
  const [clients, setClients] = useState([])
  const [selectedClient, setSelectedClient] = useState('')
  const [rows, setRows] = useState([])
  const [summary, setSummary] = useState({ total_tagihan: 0, total_bayar: 0, sisa: 0, status: '-' })
  const [loading, setLoading] = useState(true)
  const [selectedRows, setSelectedRows] = useState(new Set())

  // Deposit form
  const [deposit, setDeposit] = useState(0)
  const [depositDate, setDepositDate] = useState(today())
  const [depositMethod, setDepositMethod] = useState('CASH')
  const [depositSaving, setDepositSaving] = useState(false)

  // Load client list
  useEffect(() => {
    api.listInvoiceClients().then(setClients).catch(() => setClients([])).finally(() => setLoading(false))
  }, [])

  // Load data when client changes
  const loadClientData = useCallback(async (clientRef) => {
    if (!clientRef) {
      setRows([])
      setSummary({ total_tagihan: 0, total_bayar: 0, sisa: 0, status: '-' })
      setSelectedRows(new Set())
      return
    }
    try {
      const [combined, sum] = await Promise.all([
        api.getInvoiceCombined(clientRef),
        api.getInvoiceSummary(clientRef),
      ])
      setRows(combined.rows || [])
      setSummary(sum)
      setSelectedRows(new Set())
    } catch (err) {
      console.error('Gagal memuat data invoice:', err)
    }
  }, [])

  useEffect(() => {
    loadClientData(selectedClient)
  }, [selectedClient, loadClientData])

  // Toggle row selection
  const toggleRow = (id) => {
    setSelectedRows(prev => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const toggleAll = () => {
    if (selectedRows.size === rows.length) {
      setSelectedRows(new Set())
    } else {
      setSelectedRows(new Set(rows.map(r => r.id)))
    }
  }

  // Selected sales total
  const selectedSalesTotal = rows
    .filter(r => selectedRows.has(r.id) && r.jenis === 'Penjualan')
    .reduce((s, r) => s + r.debit, 0)

  const hasSelectedPayment = rows.some(r => selectedRows.has(r.id) && r.jenis === 'Pembayaran')

  // Compute running balance
  let runningBalance = 0
  const rowsWithBalance = rows.map(r => {
    runningBalance += r.debit - r.credit
    return { ...r, balance: runningBalance }
  })

  // Handle deposit save
  const handleDeposit = async () => {
    if (!selectedClient || deposit <= 0) return
    setDepositSaving(true)
    try {
      await api.createInvoiceDeposit(selectedClient, {
        tanggal_bayar: depositDate,
        nominal_bayar: deposit,
        metode: depositMethod,
      })
      setDeposit(0)
      loadClientData(selectedClient)
    } catch (err) {
      alert('Error: ' + err.message)
    } finally {
      setDepositSaving(false)
    }
  }

  // Handle delete payment
  const handleDeletePayment = async () => {
    if (!selectedRows.size) return
    const paymentIds = rows
      .filter(r => selectedRows.has(r.id) && r.jenis === 'Pembayaran')
      .map(r => parseInt(r.id.replace('P', '')))

    if (paymentIds.length === 0) return
    if (!confirm(`Hapus ${paymentIds.length} riwayat pembayaran?`)) return

    try {
      for (const pid of paymentIds) {
        await api.deleteInvoicePayment(pid)
      }
      loadClientData(selectedClient)
    } catch (err) {
      alert('Error: ' + err.message)
    }
  }

  // Status badge class
  const statusBadge = (status) => {
    if (status === 'LUNAS') return 'badge badge-green'
    if (status === 'PARTIAL') return 'badge badge-yellow'
    return 'badge badge-red'
  }

  return (
    <div>
      <div className="page-header">
        <h2>Invoice &amp; Piutang</h2>
        <button className="btn btn-ghost" onClick={() => loadClientData(selectedClient)}>
          Refresh Data
        </button>
      </div>

      {/* Client Dropdown */}
      <div className="form-row" style={{ marginBottom: 16 }}>
        <div className="form-group">
          <label>Pilih Klien</label>
          <select className="input" value={selectedClient} onChange={e => setSelectedClient(e.target.value)} style={{ maxWidth: 400 }}>
            <option value="">-- Pilih Klien --</option>
            {clients.map(c => (
              <option key={c.id} value={c.id}>{c.nama}</option>
            ))}
          </select>
        </div>
      </div>

      {selectedClient && (
        <>
          {/* Info */}
          <p className="text-muted mb-16" style={{ fontSize: 12 }}>
            PILIH BARIS PENJUALAN (centang) untuk cetak invoice — deposit diisi di bawah
          </p>

          {/* Summary KPI */}
          <div className="kpi-grid" style={{ gridTemplateColumns: 'repeat(4, 1fr)', marginBottom: 16 }}>
            <div className="kpi-card">
              <div className="kpi-label">TOTAL TAGIHAN</div>
              <div className="kpi-value text-pink">{formatRp(summary.total_tagihan)}</div>
            </div>
            <div className="kpi-card">
              <div className="kpi-label">TOTAL DIBAYAR</div>
              <div className="kpi-value text-green">{formatRp(summary.total_bayar)}</div>
            </div>
            <div className="kpi-card">
              <div className="kpi-label">SISA PIUTANG</div>
              <div className="kpi-value" style={{ color: summary.sisa > 0 ? 'var(--neon-pink)' : 'var(--neon-green)' }}>
                {formatRp(summary.sisa)}
              </div>
            </div>
            <div className="kpi-card">
              <div className="kpi-label">STATUS</div>
              <div className="kpi-value">
                <span className={statusBadge(summary.status)}>{summary.status}</span>
              </div>
            </div>
          </div>

          {/* Transaction Table */}
          <div className="panel mb-16">
            <div className="table-container">
              <table className="data-table">
                <thead>
                  <tr>
                    <th style={{ width: 40 }}>
                      <input type="checkbox" checked={selectedRows.size === rows.length && rows.length > 0} onChange={toggleAll} />
                    </th>
                    <th style={{ width: 48 }}>#</th>
                    <th style={{ width: 110 }}>Tanggal</th>
                    <th>Keterangan</th>
                    <th style={{ width: 130, textAlign: 'right' }}>Debit (Rp)</th>
                    <th style={{ width: 130, textAlign: 'right' }}>Kredit (Rp)</th>
                    <th style={{ width: 130, textAlign: 'right' }}>Sisa (Rp)</th>
                    <th style={{ width: 110, textAlign: 'center' }}>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {rowsWithBalance.length === 0 ? (
                    <tr>
                      <td colSpan={8} className="text-muted" style={{ textAlign: 'center', padding: 32 }}>
                        Tidak ada data transaksi untuk klien ini
                      </td>
                    </tr>
                  ) : rowsWithBalance.map((r, i) => (
                    <tr key={r.id}
                      style={{
                        background: selectedRows.has(r.id) ? 'rgba(0,240,255,0.06)' : undefined,
                        cursor: 'pointer',
                      }}
                      onClick={() => toggleRow(r.id)}
                    >
                      <td>
                        <input type="checkbox" checked={selectedRows.has(r.id)} onChange={() => toggleRow(r.id)} onClick={e => e.stopPropagation()} />
                      </td>
                      <td className="text-muted">{i + 1}</td>
                      <td>{r.tanggal}</td>
                      <td>{r.keterangan}</td>
                      <td className="font-mono text-right" style={{ color: r.jenis === 'Penjualan' ? 'var(--neon-pink)' : undefined }}>
                        {r.debit > 0 ? formatRp(r.debit) : '-'}
                      </td>
                      <td className="font-mono text-right text-green">
                        {r.credit > 0 ? formatRp(r.credit) : '-'}
                      </td>
                      <td className="font-mono text-right" style={{ color: r.balance <= 0 ? 'var(--neon-green)' : 'var(--neon-pink)', fontWeight: 'bold' }}>
                        {formatRp(r.balance)}
                      </td>
                      <td style={{ textAlign: 'center' }}>
                        <span className={statusBadge(r.status)}>{r.status}</span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Bottom Panel: Deposit + Actions */}
          <div className="panel">
            {/* Selected info */}
            {selectedSalesTotal > 0 && (
              <div className="mb-16" style={{ fontSize: 13 }}>
                <span className="text-muted">Total tagihan terpilih: </span>
                <span className="text-pink font-mono" style={{ fontWeight: 'bold' }}>{formatRp(selectedSalesTotal)}</span>
                <span className="text-muted"> ({rows.filter(r => selectedRows.has(r.id) && r.jenis === 'Penjualan').length} transaksi)</span>
              </div>
            )}

            {/* Deposit Form */}
            <div className="form-row" style={{ marginBottom: 16 }}>
              <div className="form-group">
                <label>Deposit (Rp)</label>
                <input className="input" type="number" min="0" value={deposit} onChange={e => setDeposit(Number(e.target.value))} style={{ width: 160 }} />
              </div>
              <div className="form-group">
                <label>Tanggal Deposit</label>
                <input className="input" type="date" value={depositDate} onChange={e => setDepositDate(e.target.value)} style={{ width: 180 }} />
              </div>
              <div className="form-group">
                <label>Metode</label>
                <select className="input" value={depositMethod} onChange={e => setDepositMethod(e.target.value)} style={{ width: 130 }}>
                  <option value="CASH">Tunai</option>
                  <option value="TRANSFER">Transfer</option>
                </select>
              </div>
            </div>

            {/* Actions */}
            <div className="form-row">
              <button className="btn btn-solid" onClick={handleDeposit} disabled={!selectedClient || deposit <= 0 || depositSaving}>
                {depositSaving ? 'Menyimpan...' : 'Simpan Deposit'}
              </button>
              {hasSelectedPayment && (
                <button className="btn btn-danger" onClick={handleDeletePayment}>
                  Hapus Pembayaran ({rows.filter(r => selectedRows.has(r.id) && r.jenis === 'Pembayaran').length})
                </button>
              )}
            </div>
          </div>
        </>
      )}

      {!selectedClient && !loading && (
        <div className="panel" style={{ textAlign: 'center', padding: 48 }}>
          <p className="text-muted" style={{ fontSize: 14 }}>
            Pilih klien dari dropdown di atas untuk melihat data invoice &amp; piutang
          </p>
        </div>
      )}
    </div>
  )
}
