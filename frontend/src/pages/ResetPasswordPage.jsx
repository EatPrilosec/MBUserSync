import { useState, useEffect } from 'react'
import { resetPassword } from '../services/api'

export default function ResetPasswordPage() {
  const [token, setToken] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [success, setSuccess] = useState(false)
  
  useEffect(() => {
    // Extract token from URL search params
    const params = new URLSearchParams(window.location.search)
    const t = params.get('token')
    if (t) setToken(t)
  }, [])
  
  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!token) {
      setError("No token found in the URL. Ensure you used the exact link provided.")
      return
    }
    if (newPassword !== confirmPassword) {
      setError("Passwords do not match.")
      return
    }
    if (newPassword.length < 4) {
      setError("Password is too short.")
      return
    }
    
    setLoading(true)
    setError(null)
    
    try {
      await resetPassword(token, newPassword)
      setSuccess(true)
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
          <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>✅</div>
          <h2 style={{ marginBottom: '1rem' }}>Password Updated</h2>
          <p className="text-muted">Your password has been successfully updated across all configured media servers. You can now log in normally.</p>
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
          <h2>Reset Password</h2>
          <p className="text-muted" style={{ fontSize: '0.9rem' }}>Choose a new password for your account</p>
        </div>
        
        {error && <div className="alert alert-error">{error}</div>}
        
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>New Password</label>
            <input 
              type="password" 
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
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
            {loading ? 'Updating...' : 'Update Password'}
          </button>
        </form>
      </div>
    </div>
  )
}
