import React from 'react'
import { NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../App'

const NAV_SECTIONS = [
  {
    title: 'MAIN',
    items: [
      { to: '/dashboard', label: 'DASHBOARD', icon: '📊' },
    ],
  },
  {
    title: 'DATA MASTER',
    items: [
      { to: '/master/sku', label: 'SKU', icon: '🏷️' },
      { to: '/master/persons', label: 'PERSONS', icon: '👤' },
    ],
  },
  {
    title: 'OPERATIONS',
    items: [
      { to: '/harian', label: 'CATATAN HARIAN', icon: '📝' },
      { to: '/hutang', label: 'HUTANG & PELUNASAN', icon: '💳' },
      { to: '/gaji', label: 'PAYROLL & BON', icon: '💰' },
      { to: '/stok', label: 'STOCK MANAGER', icon: '📦' },
      { to: '/invoice', label: 'INVOICE & PIUTANG', icon: '🧾' },
      { to: '/profit', label: 'PROFIT SIMULATION', icon: '📈' },
    ],
  },
]

export default function Sidebar() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const handleLogout = async () => {
    await logout()
    navigate('/login', { replace: true })
  }

  return (
    <nav className="sidebar">
      {/* Brand */}
      <div className="sidebar-brand">
        <h1>YAZMINA HIJAB</h1>
        <p>OPERATIONS OS · WEB v0.1</p>
      </div>

      {/* Navigation */}
      <div className="sidebar-nav">
        {NAV_SECTIONS.map(section => (
          <div key={section.title} className="sidebar-section">
            <div className="sidebar-section-title">{section.title}</div>
            {section.items.map(item => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  `sidebar-link${isActive ? ' active' : ''}`
                }
              >
                <span className="sidebar-icon">{item.icon}</span>
                {item.label}
              </NavLink>
            ))}
          </div>
        ))}
      </div>

      {/* Footer */}
      <div className="sidebar-footer">
        <div className="admin-label">👤 {user?.username || 'admin'}</div>
        <button className="btn btn-danger" onClick={handleLogout} style={{ width: '100%' }}>
          LOGOUT
        </button>
      </div>
    </nav>
  )
}
