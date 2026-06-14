import { useState } from 'react'
import { createPortal } from 'react-dom'
import * as api from '../services/api'

export default function UserActionsModal({ user, onClose, onUpdated }) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [successMsg, setSuccessMsg] = useState(null)
  const [newPassword, setNewPassword] = useState('')
  const [showPasswordForm, setShowPasswordForm] = useState(false)
  
  const servers = ['emby', 'jellyfin', 'ombi', 'seerr']
  
  const handleDelete = async (serverName) => {
    if (!window.confirm(`Are you sure you want to delete ${user.username} from ${serverName}? This cannot be undone.`)) return
    
    setLoading(true)
    setError(null)
    try {
      await api.deleteUser(serverName, user.username)
      await onUpdated()
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }
  
  const handleExclude = async (serverName, exclude) => {
    setLoading(true)
    setError(null)
    try {
      await api.toggleExcludeUser(serverName, user.username, exclude)
      await onUpdated()
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }
  
  const handleDeleteFromAll = async () => {
    if (!window.confirm(`Are you sure you want to delete ${user.username} from ALL servers? This cannot be undone.`)) return
    
    setLoading(true)
    setError(null)
    try {
      const activeServers = Object.keys(user.servers)
      await Promise.all(activeServers.map(server => api.deleteUser(server, user.username)))
      await onUpdated()
      onClose()
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleChangePassword = async () => {
    if (!newPassword) return
    if (!window.confirm(`Force change password for ${user.username} across all servers?`)) return
    
    setLoading(true)
    setError(null)
    setSuccessMsg(null)
    try {
      await api.changePassword(user.username, newPassword)
      setSuccessMsg(`Password successfully updated for ${user.username}`)
      setNewPassword('')
      setShowPasswordForm(false)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return createPortal(
    <div className="modal-backdrop">
      <div className="modal-content">
        <div className="modal-header">
          <h2>Manage User: {user.username}</h2>
          <button className="button-close" onClick={onClose}>&times;</button>
        </div>
        
        <div className="modal-body">
          {error && <div className="alert alert-error mb-2">{error}</div>}
          {successMsg && <div className="alert alert-success mb-2">{successMsg}</div>}
          
          <div className="mb-2" style={{ display: 'flex', gap: '0.5rem', justifyContent: 'flex-end' }}>
            <button 
              className="button button-secondary button-small"
              onClick={() => setShowPasswordForm(!showPasswordForm)}
            >
              Change Password
            </button>
          </div>

          {showPasswordForm && (
            <div className="card mb-2" style={{ padding: '1rem', backgroundColor: 'rgba(255,255,255,0.02)' }}>
              <h3 style={{ marginBottom: '0.5rem', fontSize: '1rem' }}>Force Change Password</h3>
              <div style={{ display: 'flex', gap: '0.5rem' }}>
                <input 
                  type="text" 
                  placeholder="New Password" 
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  className="form-group"
                  style={{ flex: 1, margin: 0, padding: '0.5rem', borderRadius: '4px', border: '1px solid #334155', background: '#0f1115', color: '#fff' }}
                />
                <button 
                  className="button button-primary button-small"
                  onClick={handleChangePassword}
                  disabled={loading || !newPassword}
                >
                  Apply
                </button>
              </div>
              <p className="text-muted" style={{ fontSize: '0.8rem', marginTop: '0.5rem' }}>
                This will immediately overwrite the user's password on all servers they currently exist on.
              </p>
            </div>
          )}
          
          <table className="users-table">
            <thead>
              <tr>
                <th>Server</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {servers.map(server => {
                const exists = !!user.servers[server]
                const isExcluded = user.excluded_from.includes(server)
                
                return (
                  <tr key={server}>
                    <td style={{ textTransform: 'capitalize' }}>{server}</td>
                    <td>
                      {exists ? (
                        <span className="status-badge status-connected">Exists</span>
                      ) : (
                        <span className="status-badge status-disconnected">Missing</span>
                      )}
                      {isExcluded && (
                        <span className="status-badge status-disconnected ml-1">Excluded</span>
                      )}
                    </td>
                    <td>
                      <div className="button-group-small">
                        {exists && (
                          <button 
                            className="button button-error button-small" 
                            disabled={loading}
                            onClick={() => handleDelete(server)}
                          >
                            Delete
                          </button>
                        )}
                        {!isExcluded ? (
                          <button 
                            className="button button-warning button-small" 
                            disabled={loading}
                            onClick={() => handleExclude(server, true)}
                          >
                            Exclude
                          </button>
                        ) : (
                          <button 
                            className="button button-success button-small" 
                            disabled={loading}
                            onClick={() => handleExclude(server, false)}
                          >
                            Include
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
          
          <div className="mt-2" style={{ borderTop: '1px solid var(--border-color)', paddingTop: '1rem', marginTop: '1rem' }}>
            <button 
              className="button button-error" 
              style={{ width: '100%' }}
              disabled={loading || Object.keys(user.servers).length === 0}
              onClick={handleDeleteFromAll}
            >
              Danger: Delete User from ALL Servers
            </button>
          </div>
        </div>
      </div>
    </div>,
    document.body
  )
}
