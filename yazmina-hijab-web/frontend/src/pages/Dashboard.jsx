import React, { useState, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'

function formatRp(val) {
  return 'Rp ' + Number(val || 0).toLocaleString('id-ID')
}

function formatShortRp(val) {
  const abs = Math.abs(val || 0)
  if (abs >= 1_000_000_000) return 'Rp ' + (val / 1_000_000_000).toFixed(1) + ' M'
  if (abs >= 1_000_000) return 'Rp ' + (val / 1_000_000).toFixed(1) + ' JT'
  if (abs >= 1_000) return 'Rp ' + (val / 1_000).toFixed(1) + ' RB'
  return 'Rp ' + (val || 0).toLocaleString('id-ID')
}

// ── Simple Bar Chart (pure CSS) ─────────────────────────────────────
function BarChart({ data, dataKey, color, label }) {
  const maxVal = Math.max(...data.map(d => Math.abs(d[dataKey] || 0)), 1)
  return (
    <div className="chart-bars">
      {data.map((d, i) => {
        const val = d[dataKey] || 0
        const pct = Math.abs(val) / maxVal * 100
        const isNeg = val < 0
        return (
          <div className="chart-bar-col" key={i}>
            <div className="chart-bar-wrapper">
              <div
                className={`chart-bar ${isNeg ? 'chart-bar-neg' : ''}`}
                style={{
                  height: `${Math.max(pct, 2)}%`,
                  background: isNeg ? 'var(--neon-pink)' : color,
                }}
              />
            </div>
            <div className="chart-bar-val" style={{ color: isNeg ? 'var(--neon-pink)' : color }}>
              {formatShortRp(val)}
            </div>
            <div className="chart-bar-label">{d.month}</div>
          </div>
        )
      })}
    </div>
  )
}

// ── Stacked Bar Chart ────────────────────────────────────────────────
function StackedBarChart({ data }) {
  const maxVal = Math.max(
    ...data.map(d => (d.omzet || 0)),
    1
  )
  return (
    <div className="chart-bars">
      {data.map((d, i) => {
        const total = d.omzet || 0
        const modalPct = total > 0 ? (d.modal || 0) / total * 100 : 0
        const gajiPct = total > 0 ? (d.gaji || 0) / total * 100 : 0
        const profitPct = total > 0 ? Math.max(0, (d.profit || 0) / total * 100) : 0
        const barPct = total > 0 ? (total / maxVal) * 100 : 0

        return (
          <div className="chart-bar-col" key={i}>
            <div className="chart-bar-wrapper">
              <div className="chart-stacked-bar" style={{ height: `${Math.max(barPct, 3)}%` }}>
                <div className="chart-stack-segment" style={{ height: `${profitPct}%`, background: 'var(--neon-green)' }} title={`Profit: ${formatRp(d.profit)}`} />
                <div className="chart-stack-segment" style={{ height: `${gajiPct}%`, background: 'var(--neon-cyan)' }} title={`Gaji: ${formatRp(d.gaji)}`} />
                <div className="chart-stack-segment" style={{ height: `${modalPct}%`, background: 'var(--neon-yellow)' }} title={`Modal: ${formatRp(d.modal)}`} />
              </div>
            </div>
            <div className="chart-bar-val" style={{ color: d.profit >= 0 ? 'var(--neon-green)' : 'var(--neon-pink)' }}>
              {formatShortRp(d.profit)}
            </div>
            <div className="chart-bar-label">{d.month}</div>
          </div>
        )
      })}
    </div>
  )
}

// ── KPI Card Component ───────────────────────────────────────────────
function KpiCard({ label, value, accent, subtext, icon }) {
  const borderColor = {
    pink: 'var(--neon-pink)',
    yellow: 'var(--neon-yellow)',
    cyan: 'var(--neon-cyan)',
    green: 'var(--neon-green)',
  }[accent] || 'var(--neon-cyan)'

  const textColor = {
    pink: 'text-pink',
    yellow: 'text-yellow',
    cyan: 'text-cyan',
    green: 'text-green',
  }[accent] || 'text-cyan'

  return (
    <div className="kpi-card" style={{ borderLeft: `4px solid ${borderColor}` }}>
      <div className="kpi-label">{icon} {label}</div>
      <div className={`kpi-value ${textColor}`}>{value}</div>
      {subtext && <div className="text-muted" style={{ fontSize: '11px', marginTop: '4px' }}>{subtext}</div>}
    </div>
  )
}

// ── Main Dashboard ───────────────────────────────────────────────────
export default function Dashboard() {
  const today = new Date()
  const firstDay = new Date(today.getFullYear(), today.getMonth(), 1).toISOString().slice(0, 10)
  const lastDay = today.toISOString().slice(0, 10)

  const [mulai, setMulai] = useState('')
  const [akhir, setAkhir] = useState('')
  const [activePreset, setActivePreset] = useState('bulan')

  // Apply preset filter
  const applyPreset = (preset) => {
    setActivePreset(preset)
    if (preset === 'hari') {
      setMulai(lastDay)
      setAkhir(lastDay)
    } else if (preset === 'minggu') {
      const d = new Date(today)
      d.setDate(d.getDate() - d.getDay() + 1)
      setMulai(d.toISOString().slice(0, 10))
      setAkhir(lastDay)
    } else if (preset === 'bulan') {
      setMulai('')
      setAkhir('')
    } else if (preset === 'semua') {
      setMulai('')
      setAkhir('')
    }
  }

  const effectiveMulai = activePreset === 'semua' ? '' : (mulai || firstDay)
  const effectiveAkhir = activePreset === 'semua' ? '' : akhir

  // ── Queries ──────────────────────────────────────────────────────
  const { data: dashboard, isLoading } = useQuery({
    queryKey: ['dashboard', effectiveMulai, effectiveAkhir],
    queryFn: () => api.getDashboard(effectiveMulai, effectiveAkhir),
  })

  const { data: trend } = useQuery({
    queryKey: ['dashboard-trend'],
    queryFn: () => api.getDashboardTrend(6),
  })

  const kpi = dashboard || {}

  // ── Profit Color ─────────────────────────────────────────────────
  const profitColor = (kpi.profit_produksi || 0) >= 0 ? 'green' : 'pink'

  return (
    <div>
      {/* Header */}
      <div className="page-header">
        <h2 className="text-cyan">⚡ Dashboard Yazmina Hijab</h2>
        <button className="btn" onClick={() => window.location.reload()}>
          ↻ REFRESH
        </button>
      </div>

      {/* Filter Presets */}
      <div className="panel mb-24">
        <div className="table-toolbar">
          <button
            className={`btn btn-sm ${activePreset === 'hari' ? '' : 'btn-ghost'}`}
            onClick={() => applyPreset('hari')}
          >
            HARI INI
          </button>
          <button
            className={`btn btn-sm ${activePreset === 'minggu' ? '' : 'btn-ghost'}`}
            onClick={() => applyPreset('minggu')}
          >
            MINGGU INI
          </button>
          <button
            className={`btn btn-sm ${activePreset === 'bulan' ? '' : 'btn-ghost'}`}
            onClick={() => applyPreset('bulan')}
          >
            BULAN INI
          </button>
          <button
            className={`btn btn-sm ${activePreset === 'semua' ? '' : 'btn-ghost'}`}
            onClick={() => applyPreset('semua')}
          >
            SEMUA
          </button>
          <div style={{ flex: 1 }} />
          <div className="form-group" style={{ margin: 0 }}>
            <label>Dari</label>
            <input
              type="date"
              className="input"
              value={mulai}
              onChange={e => { setMulai(e.target.value); setActivePreset('custom') }}
            />
          </div>
          <div className="form-group" style={{ margin: 0 }}>
            <label>Sampai</label>
            <input
              type="date"
              className="input"
              value={akhir}
              onChange={e => { setAkhir(e.target.value); setActivePreset('custom') }}
            />
          </div>
        </div>
      </div>

      {isLoading ? (
        <div className="panel text-muted">Memuat data...</div>
      ) : (
        <>
          {/* 4 Core KPIs */}
          <div className="kpi-grid" style={{ gridTemplateColumns: 'repeat(4, 1fr)' }}>
            <KpiCard
              icon="💸"
              label="TOTAL HUTANG TERSISA"
              value={formatRp(kpi.total_hutang_tersisa)}
              accent="pink"
            />
            <KpiCard
              icon="📋"
              label="TOTAL PIUTANG"
              value={formatRp(kpi.total_piutang)}
              accent="yellow"
            />
            <KpiCard
              icon="👥"
              label="GAJI KARYAWAN"
              value={formatRp(kpi.gaji_karyawan)}
              accent="cyan"
              subtext="Bulan ini"
            />
            <KpiCard
              icon="💰"
              label="PROFIT PRODUKSI"
              value={formatRp(kpi.profit_produksi)}
              accent={profitColor}
              subtext="Estimasi bersih"
            />
          </div>

          {/* Omzet Breakdown */}
          <div className="panel mt-16">
            <h3 className="text-cyan" style={{ marginBottom: 16, fontSize: 16, letterSpacing: 1 }}>
              📊 OMZET & PENGELUARAN
            </h3>
            <div className="kpi-grid" style={{ gridTemplateColumns: 'repeat(5, 1fr)' }}>
              <KpiCard
                icon="📈"
                label="TOTAL OMZET"
                value={formatRp(kpi.omzet)}
                accent="green"
                subtext="Offline + Piutang"
              />
              <KpiCard
                icon="🛒"
                label="PENJUALAN OFFLINE"
                value={formatRp(kpi.penjualan_offline)}
                accent="cyan"
              />
              <KpiCard
                icon="💵"
                label="PIUTANG DITERIMA"
                value={formatRp(kpi.piutang_diterima)}
                accent="yellow"
              />
              <KpiCard
                icon="🔧"
                label="MODAL OPERASIONAL"
                value={formatRp(kpi.modal_operasional)}
                accent="pink"
                subtext={kpi.modal_per_jenis ? Object.entries(kpi.modal_per_jenis).map(([k, v]) => `${k}: ${formatRp(v)}`).join(' · ') : ''}
              />
              <KpiCard
                icon="👥"
                label="TOTAL GAJI"
                value={formatRp(kpi.gaji_karyawan)}
                accent="cyan"
              />
            </div>
          </div>

          {/* Profit Analysis */}
          <div className="panel mt-16">
            <h3 className="text-cyan" style={{ marginBottom: 16, fontSize: 16, letterSpacing: 1 }}>
              💰 ANALISIS LABA RUGI
            </h3>
            <div className="profit-breakdown">
              <div className="profit-row">
                <span className="text-muted">A. Total Omzet (Penjualan Offline + Piutang)</span>
                <span className="text-green font-mono">{formatRp(kpi.omzet)}</span>
              </div>
              <div className="profit-divider" />
              <div className="profit-row">
                <span className="text-muted">B. Total Biaya (Modal Operasional + Gaji Karyawan)</span>
                <span className="text-pink font-mono">{formatRp((kpi.modal_operasional || 0) + (kpi.gaji_karyawan || 0))}</span>
              </div>
              <div className="profit-row" style={{ paddingLeft: 24 }}>
                <span className="text-muted">· Modal Operasional</span>
                <span className="font-mono" style={{ fontSize: 13 }}>{formatRp(kpi.modal_operasional)}</span>
              </div>
              <div className="profit-row" style={{ paddingLeft: 24 }}>
                <span className="text-muted">· Gaji Karyawan</span>
                <span className="font-mono" style={{ fontSize: 13 }}>{formatRp(kpi.gaji_karyawan)}</span>
              </div>
              <div className="profit-divider" />
              <div className="profit-row" style={{ fontSize: 18, fontWeight: 'bold' }}>
                <span className="text-cyan">LABA BERSIH (A - B)</span>
                <span className={kpi.profit_produksi >= 0 ? 'text-green' : 'text-pink'} style={{ fontSize: 22 }}>
                  {formatRp(kpi.profit_produksi)}
                </span>
              </div>
            </div>
          </div>

          {/* Monthly Trend Chart */}
          {trend && trend.length > 0 && (
            <div className="panel mt-16">
              <h3 className="text-cyan" style={{ marginBottom: 16, fontSize: 16, letterSpacing: 1 }}>
                📈 TREN BULANAN (6 BULAN TERAKHIR)
              </h3>

              {/* Legend */}
              <div className="chart-legend">
                <span className="chart-legend-item">
                  <span className="chart-legend-dot" style={{ background: 'var(--neon-cyan)' }} />
                  Omzet
                </span>
                <span className="chart-legend-item">
                  <span className="chart-legend-dot" style={{ background: 'var(--neon-yellow)' }} />
                  Modal
                </span>
                <span className="chart-legend-item">
                  <span className="chart-legend-dot" style={{ background: 'var(--neon-cyan)' }} />
                  Gaji
                </span>
                <span className="chart-legend-item">
                  <span className="chart-legend-dot" style={{ background: 'var(--neon-green)' }} />
                  Profit
                </span>
              </div>

              {/* Stacked bar chart */}
              <StackedBarChart data={trend} />

              {/* Trend table */}
              <table className="data-table" style={{ marginTop: 16 }}>
                <thead>
                  <tr>
                    <th>Bulan</th>
                    <th className="text-right">Omzet</th>
                    <th className="text-right">Modal</th>
                    <th className="text-right">Gaji</th>
                    <th className="text-right">Profit</th>
                  </tr>
                </thead>
                <tbody>
                  {trend.map((t, i) => (
                    <tr key={i}>
                      <td className="font-mono">{t.month} {t.year}</td>
                      <td className="text-right font-mono text-green">{formatRp(t.omzet)}</td>
                      <td className="text-right font-mono text-yellow">{formatRp(t.modal)}</td>
                      <td className="text-right font-mono text-cyan">{formatRp(t.gaji)}</td>
                      <td className={`text-right font-mono ${t.profit >= 0 ? 'text-green' : 'text-pink'}`}>
                        {formatRp(t.profit)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Notes */}
          <p className="text-muted" style={{ fontSize: '12px', marginTop: '16px' }}>
            * Hutang & Piutang menampilkan saldo terkini (tidak terpengaruh filter tanggal).
            Filter berlaku untuk Gaji Karyawan, Modal Operasional, dan Estimasi Profit.
          </p>
        </>
      )}
    </div>
  )
}
