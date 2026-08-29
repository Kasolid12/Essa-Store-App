/**
 * Yazmina Hijab Web — Reusable DataTable Component.
 *
 * Features: search, sort, pagination, empty state, loading state.
 */

import React, { useState, useMemo } from 'react'

const PAGE_SIZE = 15

export default function DataTable({
  columns,      // [{ key, label, render?, sortable?, width? }]
  data,         // array of objects
  loading,      // boolean
  searchable,   // boolean (default true)
  searchPlaceholder,
  onRowClick,   // (row) => void
  emptyMessage = 'Tidak ada data',
}) {
  const [search, setSearch] = useState('')
  const [sortKey, setSortKey] = useState(null)
  const [sortDir, setSortDir] = useState('asc')
  const [page, setPage] = useState(0)

  // Filter
  const filtered = useMemo(() => {
    if (!search) return data
    const q = search.toLowerCase()
    return data.filter(row =>
      columns.some(col => {
        const val = row[col.key]
        return val !== null && val !== undefined && String(val).toLowerCase().includes(q)
      })
    )
  }, [data, search, columns])

  // Sort
  const sorted = useMemo(() => {
    if (!sortKey) return filtered
    return [...filtered].sort((a, b) => {
      const av = a[sortKey] ?? ''
      const bv = b[sortKey] ?? ''
      const cmp = String(av).localeCompare(String(bv), 'id')
      return sortDir === 'asc' ? cmp : -cmp
    })
  }, [filtered, sortKey, sortDir])

  // Paginate
  const totalPages = Math.ceil(sorted.length / PAGE_SIZE)
  const paged = sorted.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE)

  // Reset page when search changes
  React.useEffect(() => { setPage(0) }, [search])

  const handleSort = (key) => {
    if (sortKey === key) {
      setSortDir(d => d === 'asc' ? 'desc' : 'asc')
    } else {
      setSortKey(key)
      setSortDir('asc')
    }
  }

  return (
    <div className="data-table-wrapper">
      {/* Search bar */}
      {searchable !== false && (
        <div className="table-toolbar">
          <input
            className="input"
            type="text"
            placeholder={searchPlaceholder || 'Cari...'}
            value={search}
            onChange={e => setSearch(e.target.value)}
            style={{ maxWidth: 320 }}
          />
          <span className="text-muted" style={{ fontSize: 13 }}>
            {filtered.length} data
          </span>
        </div>
      )}

      {/* Table */}
      <div className="table-container">
        <table className="data-table">
          <thead>
            <tr>
              <th style={{ width: 48 }}>#</th>
              {columns.map(col => (
                <th
                  key={col.key}
                  style={{ width: col.width, cursor: col.sortable !== false ? 'pointer' : 'default' }}
                  onClick={() => col.sortable !== false && handleSort(col.key)}
                >
                  {col.label}
                  {sortKey === col.key && (
                    <span style={{ marginLeft: 4 }}>{sortDir === 'asc' ? '▲' : '▼'}</span>
                  )}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={columns.length + 1} className="text-muted" style={{ padding: 32, textAlign: 'center' }}>
                  Memuat data...
                </td>
              </tr>
            ) : paged.length === 0 ? (
              <tr>
                <td colSpan={columns.length + 1} className="text-muted" style={{ padding: 32, textAlign: 'center' }}>
                  {emptyMessage}
                </td>
              </tr>
            ) : paged.map((row, i) => (
              <tr
                key={row.id || i}
                onClick={() => onRowClick?.(row)}
                style={{ cursor: onRowClick ? 'pointer' : 'default' }}
              >
                <td className="text-muted">{page * PAGE_SIZE + i + 1}</td>
                {columns.map(col => (
                  <td key={col.key}>
                    {col.render ? col.render(row[col.key], row) : (row[col.key] ?? '-')}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="table-pagination">
          <button
            className="btn btn-ghost btn-sm"
            disabled={page === 0}
            onClick={() => setPage(p => p - 1)}
          >
            ‹ Prev
          </button>
          <span className="text-muted">
            {page + 1} / {totalPages}
          </span>
          <button
            className="btn btn-ghost btn-sm"
            disabled={page >= totalPages - 1}
            onClick={() => setPage(p => p + 1)}
          >
            Next ›
          </button>
        </div>
      )}
    </div>
  )
}
