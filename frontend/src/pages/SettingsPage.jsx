import { useState, useEffect } from 'react'
import { useForm, Controller } from 'react-hook-form'
import * as api from '../services/api'

export default function SettingsPage() {
  const [syncStatus, setSyncStatus] = useState(null)
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState(null)
  const [validationResult, setValidationResult] = useState(null)
  
  const { control, handleSubmit, watch, formState: { errors } } = useForm({
    defaultValues: {
      sync_mode: 'primary_source',
      sync_enabled: true,
      cron_schedule: '0 */20 * * * *',
    }
  })
  
  const syncEnabled = watch('sync_enabled')
  
  useEffect(() => {
    loadSyncStatus()
  }, [])
  
  const loadSyncStatus = async () => {
    try {
      const status = await api.getSyncStatus()
      setSyncStatus(status)
    } catch (error) {
      console.error('Error loading sync status:', error)
    }
  }
  
  const onSubmit = async (data) => {
    setLoading(true)
    try {
      await api.updateSyncConfig(data)
      setMessage({ type: 'success', text: 'Sync settings updated' })
      await loadSyncStatus()
    } catch (error) {
      setMessage({ type: 'error', text: `Error: ${error.message}` })
    } finally {
      setLoading(false)
    }
  }
  
  const handleRunSync = async () => {
    setLoading(true)
    try {
      const result = await api.runSync()
      if (result.success) {
        setMessage({
          type: 'success',
          text: `${result.message} (${result.synced_count} users synced)`
        })
      } else {
        setMessage({
          type: 'error',
          text: result.message
        })
      }
      await loadSyncStatus()
    } catch (error) {
      setMessage({ type: 'error', text: `Error: ${error.message}` })
    } finally {
      setLoading(false)
    }
  }
  
  const handleValidate = async () => {
    try {
      const result = await api.validateSync()
      setValidationResult(result)
    } catch (error) {
      setMessage({ type: 'error', text: `Validation error: ${error.message}` })
    }
  }
  
  return (
    <div className="card">
      <h2>Sync Settings</h2>
      
      {message && (
        <div className={`alert alert-${message.type}`}>
          {message.text}
        </div>
      )}
      
      {syncStatus && (
        <div className="alert alert-info">
          <div>
            <strong>Sync Status:</strong>{' '}
            <span className={`status-badge ${syncStatus.enabled ? 'status-connected' : 'status-disconnected'}`}>
              {syncStatus.enabled ? 'Enabled' : 'Disabled'}
            </span>
          </div>
          {syncStatus.last_sync_time && (
            <div className="mt-1">
              <strong>Last Sync:</strong> {new Date(syncStatus.last_sync_time).toLocaleString()}
            </div>
          )}
          <div className="mt-1">
            <strong>Mode:</strong> {syncStatus.sync_mode === 'primary_source' ? 'Primary Source' : 'Any-to-Any'}
          </div>
        </div>
      )}
      
      <form onSubmit={handleSubmit(onSubmit)}>
        <div className="form-group">
          <label className="checkbox-group">
            <Controller
              name="sync_enabled"
              control={control}
              render={({ field }) => <input type="checkbox" {...field} />}
            />
            <span>Enable automatic syncing</span>
          </label>
        </div>
        
        <div className="form-group">
          <label htmlFor="sync_mode">Sync Mode</label>
          <Controller
            name="sync_mode"
            control={control}
            render={({ field }) => (
              <select {...field} id="sync_mode">
                <option value="primary_source">
                  Primary Source (one-way from primary)
                </option>
                <option value="any_to_any">
                  Any-to-Any (all users on all servers)
                </option>
              </select>
            )}
          />
          <p className="text-muted mt-1">
            {watch('sync_mode') === 'primary_source'
              ? 'Users from the primary server are synced to all secondary servers.'
              : 'All users from all enabled servers are synced to all other enabled servers.'}
          </p>
        </div>
        
        <div className="form-group">
          <label htmlFor="cron_schedule">Cron Schedule</label>
          <Controller
            name="cron_schedule"
            control={control}
            rules={{ required: 'Cron schedule is required' }}
            render={({ field }) => (
              <input
                {...field}
                id="cron_schedule"
                type="text"
                placeholder="0 */20 * * * *"
              />
            )}
          />
          {errors.cron_schedule && <span className="text-muted">{errors.cron_schedule.message}</span>}
          <p className="text-muted mt-1">
            Format: minute hour day month dayOfWeek (e.g., "0 */20 * * * *" = every 20 minutes)
          </p>
        </div>
        
        <div className="button-group">
          <button
            type="submit"
            className="button button-primary"
            disabled={loading || !syncEnabled}
          >
            {loading ? 'Saving...' : 'Save Settings'}
          </button>
          <button
            type="button"
            className="button button-success"
            onClick={handleRunSync}
            disabled={loading}
          >
            {loading ? 'Syncing...' : 'Run Sync Now'}
          </button>
          <button
            type="button"
            className="button button-secondary"
            onClick={handleValidate}
            disabled={loading}
          >
            Validate
          </button>
        </div>
      </form>
      
      {validationResult && (
        <div className={`alert alert-${validationResult.valid ? 'success' : 'warning'} mt-2`}>
          <strong>Validation Result:</strong>
          <div className="mt-1">
            Status: {validationResult.valid ? '✓ Valid' : '✗ Invalid'}
          </div>
          {validationResult.enabled_servers && (
            <div className="mt-1">
              Enabled Servers: {validationResult.enabled_servers.join(', ')}
            </div>
          )}
          {validationResult.primary_server && (
            <div className="mt-1">
              Primary Server: {validationResult.primary_server}
            </div>
          )}
          {validationResult.errors && validationResult.errors.length > 0 && (
            <div className="mt-1">
              <strong>Errors:</strong>
              <ul>
                {validationResult.errors.map((err, i) => <li key={i}>{err}</li>)}
              </ul>
            </div>
          )}
          {validationResult.warnings && validationResult.warnings.length > 0 && (
            <div className="mt-1">
              <strong>Warnings:</strong>
              <ul>
                {validationResult.warnings.map((warn, i) => <li key={i}>{warn}</li>)}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
