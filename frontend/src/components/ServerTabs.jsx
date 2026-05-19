import ServerConfigForm from './ServerConfigForm'

export function EmbyTab() {
  return (
    <div className="card">
      <h2>Emby Configuration</h2>
      <ServerConfigForm serverName="emby" />
    </div>
  )
}

export function JellyfinTab() {
  return (
    <div className="card">
      <h2>Jellyfin Configuration</h2>
      <ServerConfigForm serverName="jellyfin" />
    </div>
  )
}

export function OmbiTab() {
  return (
    <div className="card">
      <h2>Ombi Configuration</h2>
      <ServerConfigForm serverName="ombi" />
    </div>
  )
}

export function SeerrTab() {
  return (
    <div className="card">
      <h2>Seerr Configuration</h2>
      <p className="text-muted mb-2">Unified configuration for Seerr (Overseerr/Jellyseerr)</p>
      <ServerConfigForm serverName="seerr" />
    </div>
  )
}

export default { EmbyTab, JellyfinTab, OmbiTab, SeerrTab }
