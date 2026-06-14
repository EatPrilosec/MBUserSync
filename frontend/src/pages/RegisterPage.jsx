import { useState } from 'react'
import { registerUser } from '../services/api'

export default function RegisterPage() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [success, setSuccess] = useState(false)
  
  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!username || username.trim().length < 3) {
      setError("Username must be at least 3 characters long.")
      return
    }
    if (password !== confirmPassword) {
      setError("Passwords do not match.")
      return
    }
    if (password.length < 8) {
      setError("Password must be at least 8 characters long to be compatible with all servers.")
      return
    }
    
    setLoading(true)
    setError(null)
    
    try {
      const res = await registerUser(username.trim(), password)
      if (res.success && res.message !== "Username already exists") {
        setSuccess(true)
      } else if (res.message === "Username already exists") {
        setError("Username already exists. Please choose a different one.")
      } else {
        setError(res.message || "Failed to create account.")
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  if (success) {
    return (
      <div className="app-container" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '100vh' }}>
        <div className="card" style={{ maxWidth: '400px', width: '100%', textAlign: 'center' }}>
          <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>🎉</div>
          <h2 style={{ marginBottom: '1rem' }}>Account Created</h2>
          <p className="text-muted">Your account <strong>{username}</strong> has been successfully created. You can now log in to the media servers.</p>
        </div>
      </div>
    )
  }

  return (
    <div className="app-container" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '100vh' }}>
      <div className="card" style={{ maxWidth: '400px', width: '100%' }}>
        <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
          <h1 style={{ 
            fontSize: '1.5rem', 
            fontWeight: '600', 
            background: 'linear-gradient(90deg, #60a5fa, #a78bfa)', 
            WebkitBackgroundClip: 'text', 
            WebkitTextFillColor: 'transparent',
            marginBottom: '0.5rem'
          }}>MB User Sync</h1>
          <h2>Create Account</h2>
          <p className="text-muted" style={{ fontSize: '0.9rem' }}>Choose a username and password for your media server access</p>
        </div>
        
        {error && <div className="alert alert-error mb-2">{error}</div>}
        
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>Username</label>
            <input 
              type="text" 
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="e.g. johndoe"
              required
            />
          </div>
          
          <div className="form-group">
            <label>Password</label>
            <input 
              type="password" 
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>
          
          <div className="form-group">
            <label>Confirm Password</label>
            <input 
              type="password" 
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              required
            />
          </div>
          
          <button 
            type="submit" 
            className="button button-primary" 
            style={{ width: '100%' }}
            disabled={loading}
          >
            {loading ? 'Creating...' : 'Create Account'}
          </button>
        </form>
      </div>
    </div>
  )
}
