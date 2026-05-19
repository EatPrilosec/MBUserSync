/**
 * API service for communicating with backend
 */

const API_BASE = '/api'

class APIError extends Error {
  constructor(status, message) {
    super(message)
    this.status = status
  }
}

async function fetchAPI(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`
  
  const config = {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    ...options,
  }
  
  try {
    const response = await fetch(url, config)
    
    if (!response.ok) {
      const error = await response.text()
      throw new APIError(response.status, error || `HTTP ${response.status}`)
    }
    
    return await response.json()
  } catch (error) {
    if (error instanceof APIError) {
      throw error
    }
    throw new APIError(0, error.message || 'Network error')
  }
}

// Settings
export const getSettings = () => fetchAPI('/settings')
export const updateSettings = (settings) => fetchAPI('/settings', {
  method: 'PUT',
  body: JSON.stringify(settings),
})

// Servers
export const listServers = () => fetchAPI('/servers')
export const getServer = (serverName) => fetchAPI(`/servers/${serverName}`)
export const updateServer = (serverName, config) => fetchAPI(`/servers/${serverName}`, {
  method: 'PUT',
  body: JSON.stringify(config),
})
export const testServer = (serverName) => fetchAPI(`/servers/${serverName}/test`, {
  method: 'POST',
})
export const getServerUsers = (serverName) => fetchAPI(`/servers/${serverName}/users`, {
  method: 'POST',
})

// Sync
export const getSyncStatus = () => fetchAPI('/sync/status')
export const runSync = () => fetchAPI('/sync/run', { method: 'POST' })
export const updateSyncConfig = (config) => fetchAPI('/sync/config', {
  method: 'PUT',
  body: JSON.stringify(config),
})
export const validateSync = () => fetchAPI('/sync/validate', { method: 'POST' })

export default {
  getSettings,
  updateSettings,
  listServers,
  getServer,
  updateServer,
  testServer,
  getServerUsers,
  getSyncStatus,
  runSync,
  updateSyncConfig,
  validateSync,
}
