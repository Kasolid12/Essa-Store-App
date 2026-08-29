import React, { useState, useEffect } from 'react'
import { BrowserRouter, Routes, Route, Navigate, useNavigate, useLocation } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { api } from './api/client'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import SkuPage from './pages/SkuPage'
import PersonPage from './pages/PersonPage'
import CatatanHarian from './pages/CatatanHarian'
import HutangPelunasan from './pages/HutangPelunasan'
import PayrollBon from './pages/PayrollBon'
import Invoice from './pages/Invoice'
import ProfitSimulation from './pages/ProfitSimulation'
import StockManager from './pages/StockManager'
import Sidebar from './components/Sidebar'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
})

// ── Auth Context ──────────────────────────────────────────────────────
const AuthContext = React.createContext(null)

export function useAuth() {
  return React.useContext(AuthContext)
}

function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.getMe()
      .then(data => setUser(data))
      .catch(() => setUser(null))
      .finally(() => setLoading(false))
  }, [])

  const login = async (username, password) => {
    const data = await api.login(username, password)
    setUser({ username: data.username })
    return data
  }

  const logout = async () => {
    await api.logout()
    setUser(null)
  }

  if (loading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100vh' }}>
        <span className="text-cyan">Loading...</span>
      </div>
    )
  }

  return (
    <AuthContext.Provider value={{ user, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

// ── Protected Layout (sidebar + content) ──────────────────────────────
function ProtectedLayout({ children }) {
  const { user } = useAuth()
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const location = useLocation()

  // Close sidebar on route change (mobile)
  useEffect(() => {
    setSidebarOpen(false)
  }, [location.pathname])

  if (!user) return <Navigate to="/login" replace />
  return (
    <div>
      {/* Mobile hamburger */}
      <button
        className="hamburger"
        onClick={() => setSidebarOpen(!sidebarOpen)}
        aria-label="Toggle menu"
      >
        {sidebarOpen ? '✕' : '☰'}
      </button>
      <Sidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} />
      <div className="content-area">
        {children}
      </div>
    </div>
  )
}

// ── Coming Soon placeholder ──────────────────────────────────────────
function ComingSoon({ title }) {
  return (
    <>
      <div className="page-header">
        <h2>{title}</h2>
      </div>
      <div className="panel">
        <p className="text-muted">Halaman ini akan diimplementasikan di fase berikutnya.</p>
      </div>
    </>
  )
}

// ── App ───────────────────────────────────────────────────────────────
export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AuthProvider>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/" element={<Navigate to="/dashboard" replace />} />

            {/* Dashboard */}
            <Route
              path="/dashboard"
              element={
                <ProtectedLayout>
                  <Dashboard />
                </ProtectedLayout>
              }
            />

            {/* Data Master — Fase 1 */}
            <Route
              path="/master/sku"
              element={
                <ProtectedLayout>
                  <SkuPage />
                </ProtectedLayout>
              }
            />
            <Route
              path="/master/persons"
              element={
                <ProtectedLayout>
                  <PersonPage />
                </ProtectedLayout>
              }
            />

            {/* Operations — Coming Soon */}
            <Route
              path="/harian"
              element={
                <ProtectedLayout>
                  <CatatanHarian />
                </ProtectedLayout>
              }
            />
            <Route
              path="/hutang"
              element={
                <ProtectedLayout>
                  <HutangPelunasan />
                </ProtectedLayout>
              }
            />
            <Route
              path="/gaji"
              element={
                <ProtectedLayout>
                  <PayrollBon />
                </ProtectedLayout>
              }
            />
            <Route path="/stok" element={<ProtectedLayout><StockManager /></ProtectedLayout>} />
            <Route path="/invoice" element={<ProtectedLayout><Invoice /></ProtectedLayout>} />
            <Route path="/profit" element={<ProtectedLayout><ProfitSimulation /></ProtectedLayout>} />

            {/* Catch-all */}
            <Route
              path="*"
              element={
                <ProtectedLayout>
                  <ComingSoon title="Halaman Tidak Ditemukan" />
                </ProtectedLayout>
              }
            />
          </Routes>
        </AuthProvider>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
