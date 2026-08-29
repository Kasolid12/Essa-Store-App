import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../App'

export default function Login() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const { login, user } = useAuth()
  const navigate = useNavigate()

  // If already logged in, redirect
  if (user) {
    navigate('/dashboard', { replace: true })
    return null
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      await login(username, password)
      navigate('/dashboard', { replace: true })
    } catch (err) {
      setError(err.message || 'Login gagal')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="login-page">
      <div className="login-card">
        <h1>YAZMINA HIJAB</h1>
        <p className="subtitle">OPERATIONS OS · WEB</p>

        {/* Decorative grid line */}
        <div style={{
          height: '1px',
          background: 'linear-gradient(90deg, transparent, var(--neon-cyan), transparent)',
          marginBottom: '32px',
        }} />

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>Username</label>
            <input
              type="text"
              className="input"
              value={username}
              onChange={e => setUsername(e.target.value)}
              placeholder="Masukkan username"
              autoFocus
              autoComplete="username"
            />
          </div>

          <div className="form-group">
            <label>Password</label>
            <input
              type="password"
              className="input"
              value={password}
              onChange={e => setPassword(e.target.value)}
              placeholder="Masukkan password"
              autoComplete="current-password"
            />
          </div>

          <button
            type="submit"
            className="btn btn-solid"
            disabled={loading || !username || !password}
            style={{ marginTop: '8px' }}
          >
            {loading ? 'MEMPROSES...' : 'MASUK'}
          </button>
        </form>

        <p className="login-error">{error}</p>

        {/* Decorative grid lines */}
        <div style={{
          marginTop: '24px',
          height: '1px',
          background: 'linear-gradient(90deg, transparent, var(--border-dim), transparent)',
        }} />
      </div>
    </div>
  )
}
