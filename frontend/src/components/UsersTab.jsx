import { useState, useEffect } from 'react'
import * as api from '../services/api'
import UserActionsModal from './UserActionsModal'

export default function UsersTab() {
  const [users, setUsers] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [successMessage, setSuccessMessage] = useState(null)
  const [selectedUser, setSelectedUser] = useState(null)
  
  const fetchUsers = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await api.getAllUsers()
      setUsers(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchUsers()
  }, [])

  // Keep selectedUser in sync with the updated users list
  useEffect(() => {
    if (selectedUser && users.length > 0) {
      const updatedUser = users.find(u => u.username === selectedUser.username)
      if (!updatedUser) {
        setSelectedUser(null)
      } else if (JSON.stringify(updatedUser) !== JSON.stringify(selectedUser)) {
        setSelectedUser(updatedUser)
      }
    }
  }, [users, selectedUser])

  const copyToClipboard = async (text, successMsg) => {
    try {
      if (navigator.clipboard && navigator.clipboard.writeText) {
        await navigator.clipboard.writeText(text);
      } else {
        const textArea = document.createElement("textarea");
        textArea.value = text;
        textArea.style.position = "fixed";
        textArea.style.left = "-999999px";
        document.body.appendChild(textArea);
        textArea.focus();
        textArea.select();
        try {
          document.execCommand('copy');
        } catch (err) {
          console.error('Fallback copy failed', err);
          setError("Failed to copy. Please manually copy the link.");
          document.body.removeChild(textArea);
          return;
        }
        document.body.removeChild(textArea);
      }
      setSuccessMessage(successMsg);
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err) {
      console.error("Clipboard failed:", err);
      setError("Failed to copy. Please manually copy the link.");
    }
  }

  const handleGenerateResetLink = async (username) => {
    setLoading(true)
    setError(null)
    setSuccessMessage(null)
    try {
      const data = await api.generateResetToken(username)
      const resetLink = `${window.location.origin}/reset?token=${data.token}`
      await copyToClipboard(resetLink, `Reset link for ${username} copied!`)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="card">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
        <div>
          <h2 style={{ marginBottom: '0.2rem' }}>All Users</h2>
          <p className="text-muted">
            Manage users across all your configured media servers.
          </p>
        </div>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <button 
            className="button button-secondary"
            onClick={() => window.open('/register', '_blank')}
          >
            New User Page
          </button>
          <button 
            className="button button-primary"
            onClick={async () => {
              const link = `${window.location.origin}/register`;
              await copyToClipboard(link, 'Registration link copied!');
            }}
          >
            Copy Registration Link
          </button>
        </div>
      </div>
      
      {successMessage && <div className="alert alert-success mb-2">{successMessage}</div>}
      {error && <div className="alert alert-error mb-2">{error}</div>}
      
      {loading ? (
        <div className="text-center p-4">
          <div className="spinner"></div>
          <p className="mt-1 text-muted">Loading users...</p>
        </div>
      ) : users.length === 0 ? (
        <div className="alert alert-info">No users found. Are your servers configured and online?</div>
      ) : (
        <div style={{ overflowX: 'auto' }}>
          <table className="users-table">
            <thead>
              <tr>
                <th>Username</th>
                <th>Server Presence</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {users.map(user => (
                <tr key={user.username}>
                  <td style={{ fontWeight: '500' }}>{user.username}</td>
                  <td>
                    <div className="server-badges">
                      {['emby', 'jellyfin', 'ombi', 'seerr'].map(server => {
                        const exists = !!user.servers[server]
                        const isExcluded = user.excluded_from.includes(server)
                        
                        if (!exists && !isExcluded) return null
                        
                        let badgeClass = `badge badge-${server}`
                        if (isExcluded) badgeClass += ' badge-excluded'
                        
                        return (
                          <span key={server} className={badgeClass} title={isExcluded ? 'Excluded' : 'Active'}>
                            {server}
                          </span>
                        )
                      })}
                    </div>
                  </td>
                  <td>
                    <div className="button-group-small" style={{ display: 'flex', gap: '0.5rem' }}>
                      <button 
                        className="button button-secondary button-small"
                        onClick={() => handleGenerateResetLink(user.username)}
                        disabled={loading}
                      >
                        Copy Reset Link
                      </button>
                      <button 
                        className="button button-primary button-small"
                        onClick={() => setSelectedUser(user)}
                      >
                        Manage
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      
      {selectedUser && (
        <UserActionsModal 
          user={selectedUser} 
          onClose={() => setSelectedUser(null)} 
          onUpdated={fetchUsers}
        />
      )}
    </div>
  )
}
