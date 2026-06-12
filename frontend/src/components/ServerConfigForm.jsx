import { useForm, Controller } from 'react-hook-form'
import { useState, useEffect } from 'react'
import * as api from '../services/api'

/**
 * Reusable ServerConfigForm component
 */
export default function ServerConfigForm({ serverName, onSaved }) {
  const { control, handleSubmit, watch, getValues, reset, formState: { errors } } = useForm({
    defaultValues: {
      enabled: false,
      host: 'localhost',
      port: 8096,
      api_key: '',
      is_primary: false,
      exclude_list: '',
      template_user: '',
    }
  })
  
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState(null)
  const [testResult, setTestResult] = useState(null)
  const [syncMode, setSyncMode] = useState('primary_source')
  const isPrimary = watch('is_primary')
  
  // Load existing server config on mount
  useEffect(() => {
    const loadConfig = async () => {
      try {
        const config = await api.getServer(serverName)
        const settings = await api.getSettings()
        setSyncMode(settings.sync_config?.sync_mode || 'primary_source')
        reset({
          enabled: config.enabled ?? false,
          host: config.host ?? 'localhost',
          port: config.port ?? 8096,
          api_key: config.api_key ?? '',
          is_primary: config.is_primary ?? false,
          exclude_list: config.exclude_list ?? '',
          template_user: config.template_user ?? '',
        })
      } catch (error) {
        // Server config not found or error — use defaults
        console.debug(`Could not load config for ${serverName}:`, error.message)
      }
    }
    loadConfig()
  }, [serverName, reset])
  
  const onSubmit = async (data) => {
    setLoading(true)
    try {
      await api.updateServer(serverName, data)
      setMessage({ type: 'success', text: 'Server configuration saved' })
      if (onSaved) onSaved(data)
    } catch (error) {
      setMessage({ type: 'error', text: `Error: ${error.message}` })
    } finally {
      setLoading(false)
    }
  }
  
  const handleTestConnection = async () => {
    setLoading(true)
    try {
      const currentData = getValues()
      const result = await api.testServer(serverName, currentData)
      if (result.connected) {
        setTestResult({ type: 'success', text: result.message })
      } else {
        setTestResult({ type: 'error', text: result.error || result.message })
      }
    } catch (error) {
      setTestResult({ type: 'error', text: `Error: ${error.message}` })
    } finally {
      setLoading(false)
    }
  }
  
  return (
    <form onSubmit={handleSubmit(onSubmit)} className="server-tab-container">
      {message && (
        <div className={`alert alert-${message.type}`}>
          {message.text}
        </div>
      )}
      
      {testResult && (
        <div className={`alert alert-${testResult.type}`}>
          {testResult.text}
        </div>
      )}
      
      <div className="form-group">
        <label className="checkbox-group">
          <Controller
            name="enabled"
            control={control}
            render={({ field: { value, onChange, ...rest } }) => (
              <input type="checkbox" checked={!!value} onChange={(e) => onChange(e.target.checked)} {...rest} />
            )}
          />
          <span>Enable this server</span>
        </label>
      </div>
      
      <div className="form-group">
        <label htmlFor={`host-${serverName}`}>Host</label>
        <Controller
          name="host"
          control={control}
          rules={{ required: 'Host is required' }}
          render={({ field }) => (
            <input {...field} id={`host-${serverName}`} type="text" placeholder="localhost" />
          )}
        />
        {errors.host && <span className="text-muted">{errors.host.message}</span>}
      </div>
      
      <div className="form-group">
        <label htmlFor={`port-${serverName}`}>Port</label>
        <Controller
          name="port"
          control={control}
          rules={{ required: 'Port is required' }}
          render={({ field: { onChange, ...rest } }) => (
            <input {...rest} onChange={(e) => onChange(Number(e.target.value))} id={`port-${serverName}`} type="number" />
          )}
        />
        {errors.port && <span className="text-muted">{errors.port.message}</span>}
      </div>
      
      <div className="form-group">
        <label htmlFor={`api_key-${serverName}`}>API Key</label>
        <Controller
          name="api_key"
          control={control}
          rules={{ required: 'API Key is required' }}
          render={({ field }) => (
            <input {...field} id={`api_key-${serverName}`} type="password" placeholder="Enter API key" />
          )}
        />
        {errors.api_key && <span className="text-muted">{errors.api_key.message}</span>}
      </div>
      
      <div className="form-group">
        <label className="checkbox-group">
          <Controller
            name="is_primary"
            control={control}
            render={({ field: { value, onChange, ...rest } }) => (
              <input type="checkbox" checked={!!value} onChange={(e) => onChange(e.target.checked)} disabled={syncMode === 'any_to_any'} {...rest} />
            )}
          />
          <span className={syncMode === 'any_to_any' ? 'text-muted' : ''}>Set as primary source</span>
        </label>
        {syncMode === 'any_to_any' && <p className="text-muted mt-1">Primary server is ignored in any-to-any sync mode</p>}
        {syncMode !== 'any_to_any' && isPrimary && <p className="text-muted mt-1">Only one server can be primary</p>}
      </div>
      
      <div className="form-group">
        <label htmlFor={`exclude_list-${serverName}`}>Exclude Users (comma-separated)</label>
        <Controller
          name="exclude_list"
          control={control}
          render={({ field }) => (
            <textarea
              {...field}
              id={`exclude_list-${serverName}`}
              placeholder="user1, user2, user3"
            />
          )}
        />
      </div>
      
      <div className="form-group">
        <label htmlFor={`template_user-${serverName}`}>Template User</label>
        <Controller
          name="template_user"
          control={control}
          render={({ field }) => (
            <input
              {...field}
              id={`template_user-${serverName}`}
              type="text"
              placeholder="Username to clone settings from"
            />
          )}
        />
      </div>
      
      <div className="button-group">
        <button type="submit" className="button button-primary" disabled={loading}>
          {loading ? 'Saving...' : 'Save Configuration'}
        </button>
        <button
          type="button"
          className="button button-secondary"
          onClick={handleTestConnection}
          disabled={loading}
        >
          {loading ? 'Testing...' : 'Test Connection'}
        </button>
      </div>
    </form>
  )
}
