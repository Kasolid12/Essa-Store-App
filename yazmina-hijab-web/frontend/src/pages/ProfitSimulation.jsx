import React, { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../api/client'

function formatRp(val) {
  return 'Rp ' + Number(val || 0).toLocaleString('id-ID')
}

// ── Info Panel Component ─────────────────────────────────────────────
function InfoRow({ label, value, accent, bold }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', padding: '4px 0' }}>
      <span className="text-muted">{label}</span>
      <span className={`font-mono ${accent || ''}`} style={bold ? { fontWeight: 'bold', fontSize: 16 } : {}}>
        {value}
      </span>
    </div>
  )
}

// ── Main Component ───────────────────────────────────────────────────
export default function ProfitSimulation() {
  const queryClient = useQueryClient()
  const [selectedBatch, setSelectedBatch] = useState('')

  // ── Queries ──────────────────────────────────────────────────────
  const { data: batchData } = useQuery({
    queryKey: ['profit-batches'],
    queryFn: () => api.listProfitBatches(),
  })

  const { data: analysis, isLoading: analyzing } = useQuery({
    queryKey: ['profit-analysis', selectedBatch],
    queryFn: () => api.analyzeProfitBatch(selectedBatch),
    enabled: !!selectedBatch,
  })

  const batches = batchData?.batches || []

  // Auto-select first batch
  useEffect(() => {
    if (batches.length > 0 && !selectedBatch) {
      setSelectedBatch(batches[0])
    }
  }, [batches, selectedBatch])

  // ── Mutations ────────────────────────────────────────────────────
  const toggleMutation = useMutation({
    mutationFn: (kode) => api.toggleProfitStatus(kode),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['profit-analysis', selectedBatch] })
    },
  })

  const saveMutation = useMutation({
    mutationFn: (kode) => api.saveProfitHistory(kode),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['profit-history'] })
    },
  })

  // ── Render ───────────────────────────────────────────────────────
  const a = analysis || {}
  const profitColor = (a.net_profit || 0) >= 0 ? 'text-green' : 'text-pink'
  const statusKain = a.status_kain === 'SELESAI'

  return (
    <div>
      {/* Header */}
      <div className="page-header">
        <h2 className="text-cyan">⚡ REAL-TIME PROFIT ANALYZER</h2>
      </div>

      {/* Batch Selector */}
      <div className="panel mb-24">
        <div className="table-toolbar">
          <span className="text-muted">Pilih Kode Produksi:</span>
          <select
            className="input"
            style={{ minWidth: 300 }}
            value={selectedBatch}
            onChange={e => setSelectedBatch(e.target.value)}
          >
            {batches.length === 0 ? (
              <option value="">-- Belum ada data produksi --</option>
            ) : (
              batches.map(b => <option key={b} value={b}>{b}</option>)
            )}
          </select>
          <div style={{ flex: 1 }} />
          {selectedBatch && (
            <>
              <button
                className="btn btn-sm"
                onClick={() => saveMutation.mutate(selectedBatch)}
                disabled={saveMutation.isPending}
              >
                {saveMutation.isPending ? 'Menyimpan...' : '💾 SIMPAN HISTORI'}
              </button>
              <button
                className={`btn btn-sm ${statusKain ? 'btn-danger' : ''}`}
                onClick={() => toggleMutation.mutate(selectedBatch)}
                disabled={toggleMutation.isPending}
              >
                {statusKain ? '🔓 BATALKAN FULL CUT' : '🔒 TANDAI FULL CUT'}
              </button>
            </>
          )}
        </div>
      </div>

      {!selectedBatch ? (
        <div className="panel text-muted">Pilih kode produksi untuk mulai analisis.</div>
      ) : analyzing ? (
        <div className="panel text-muted">Menganalisis data...</div>
      ) : (
        <>
          {/* Info Panels */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 16 }}>
            {/* Panel: Modal Bahan */}
            <div className="panel">
              <h3 className="text-pink" style={{ marginBottom: 12, fontSize: 14, letterSpacing: 1 }}>
                🧵 DATA MODAL BAHAN (Hutang Modal)
              </h3>
              <InfoRow label="Total Qty Kain (Kg):" value={`${a.kain_qty || 0} Kg`} />
              <InfoRow label="Harga Beli / Kg:" value={formatRp(a.kain_harga_per_kg)} />
              <div style={{ borderTop: '1px solid var(--border-dim)', margin: '8px 0', paddingTop: 8 }}>
                <InfoRow label="Total Modal Bahan:" value={formatRp(a.kain_total)} accent="text-pink" bold />
              </div>
              <div style={{ borderTop: '1px solid var(--border-dim)', margin: '8px 0', paddingTop: 8 }}>
                <InfoRow label="Status Kain:" value={
                  <span style={{ color: statusKain ? 'var(--neon-green)' : 'var(--neon-yellow)', fontWeight: 'bold' }}>
                    {statusKain ? '✓ FULL CUTTING' : '○ BELUM FULL (Masih Sisa)'}
                  </span>
                } />
              </div>
            </div>

            {/* Panel: Produksi & Distribusi */}
            <div className="panel">
              <h3 className="text-cyan" style={{ marginBottom: 12, fontSize: 14, letterSpacing: 1 }}>
                📦 DATA PRODUKSI & DISTRIBUSI
              </h3>
              <InfoRow label="Total Hasil Cutting (Pcs):" value={`${a.cut_qty || 0} Pcs`} />
              <InfoRow label="Distribusi Penjahit (Home):" value={`${a.dist_home || 0} Pcs`} />
              <InfoRow label="Distribusi Peng-sup:" value={`${a.dist_sup || 0} Pcs`} />
              <div style={{ borderTop: '1px solid var(--border-dim)', margin: '8px 0', paddingTop: 8 }}>
                <InfoRow label="Status Verifikasi:" value={
                  <span style={{
                    color: a.verif_status === 'SIAP' ? 'var(--neon-green)'
                      : a.verif_status === 'TERTAHAN' ? 'var(--neon-yellow)'
                      : 'var(--neon-pink)',
                    fontWeight: 'bold'
                  }}>
                    {a.verif_label || '-'}
                  </span>
                } />
              </div>
              {a.sku_missing_price && a.sku_missing_price.length > 0 && (
                <div style={{ marginTop: 8, padding: '6px 10px', background: 'rgba(252,226,5,0.1)', border: '1px solid var(--neon-yellow)' }}>
                  <span className="text-yellow" style={{ fontSize: 12 }}>
                    ⚠ Harga kosong: {a.sku_missing_price.join(', ')}
                  </span>
                </div>
              )}
            </div>
          </div>

          {/* Profit Calculation */}
          <div className="panel">
            <h3 className="text-cyan" style={{ marginBottom: 16, fontSize: 16, letterSpacing: 1 }}>
              💰 LAPORAN LABA BERSIH (NET PROFIT)
            </h3>

            <div className="profit-breakdown">
              <div className="profit-row">
                <span className="text-muted">A. Estimasi Pendapatan (Omzet)</span>
                <span className="text-green font-mono" style={{ fontSize: 16 }}>{formatRp(a.total_revenue)}</span>
              </div>
              <div className="profit-row">
                <span className="text-muted" style={{ paddingLeft: 16 }}>· Qty distribusi: {a.total_dist || 0} pcs</span>
                <span className="font-mono" style={{ fontSize: 12 }}>{a.dist_home || 0} home + {a.dist_sup || 0} sup</span>
              </div>
              <div className="profit-divider" />

              <div className="profit-row">
                <span className="text-muted">B. Modal Kain (Bahan Baku)</span>
                <span className="text-pink font-mono" style={{ fontSize: 16 }}>- {formatRp(a.kain_total)}</span>
              </div>
              <div className="profit-divider" />

              <div className="profit-row">
                <span className="text-cyan" style={{ fontWeight: 'bold' }}>
                  GROSS MARGIN (A - B)
                </span>
                <span className={`font-mono ${(a.gross_margin || 0) >= 0 ? 'text-green' : 'text-pink'}`} style={{ fontSize: 16 }}>
                  {formatRp(a.gross_margin)}
                </span>
              </div>
              <div className="profit-divider" />

              <div className="profit-row">
                <span className="text-muted">C. Beban Produksi Home (Sesuai SKU)</span>
                <span className="text-pink font-mono">- {formatRp(a.cost_home_total)}</span>
              </div>
              <div className="profit-row">
                <span className="text-muted">D. Beban Produksi Supplier (Sesuai SKU)</span>
                <span className="text-pink font-mono">- {formatRp(a.cost_sup_total)}</span>
              </div>
              <div className="profit-divider" />

              <div className="profit-row" style={{ fontSize: 20, padding: '12px 0' }}>
                <span className="text-cyan" style={{ fontWeight: 'bold', letterSpacing: 1 }}>LABA BERSIH (NET PROFIT)</span>
                <span className={`${profitColor} font-mono`} style={{ fontSize: 24, fontWeight: 'bold' }}>
                  {formatRp(a.net_profit)}
                </span>
              </div>
            </div>
          </div>

          {/* Distribution Details Table */}
          {a.distribusi && a.distribusi.length > 0 && (
            <div className="panel mt-16">
              <h3 className="text-cyan" style={{ marginBottom: 16, fontSize: 14, letterSpacing: 1 }}>
                📋 DETAIL DISTRIBUSI
              </h3>
              <div className="table-container">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Tanggal</th>
                      <th>Penerima</th>
                      <th>Jenis</th>
                      <th>SKU</th>
                      <th className="text-right">Qty</th>
                      <th className="text-right">Harga Jual</th>
                      <th className="text-right">Biaya/Pcs</th>
                      <th className="text-right">Total Biaya</th>
                    </tr>
                  </thead>
                  <tbody>
                    {a.distribusi.map((d, i) => (
                      <tr key={i}>
                        <td className="font-mono">{d.tanggal}</td>
                        <td>{d.person_nama}</td>
                        <td>
                          <span className={`badge ${(d.jenis || '').toLowerCase().includes('penjahit') ? 'badge-green' : 'badge-yellow'}`}>
                            {d.jenis}
                          </span>
                        </td>
                        <td className="font-mono">{d.sku_kode}</td>
                        <td className="text-right font-mono">{d.qty}</td>
                        <td className="text-right font-mono">{formatRp(d.harga_jual)}</td>
                        <td className="text-right font-mono">{formatRp(d.biaya_pcs)}</td>
                        <td className="text-right font-mono text-pink">{formatRp(d.biaya_total)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}
