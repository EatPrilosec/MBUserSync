import { useState } from 'react'
import { useAppStore } from '../stores/appStore'
import { EmbyTab, JellyfinTab, OmbiTab, SeerrTab } from '../components/ServerTabs'
import SettingsPage from '../pages/SettingsPage'

export default function Layout() {
  const { activeTab, setActiveTab } = useAppStore()
  
  const tabs = [
    { id: 'emby', label: 'Emby', component: EmbyTab },
    { id: 'jellyfin', label: 'Jellyfin', component: JellyfinTab },
    { id: 'ombi', label: 'Ombi', component: OmbiTab },
    { id: 'seerr', label: 'Seerr', component: SeerrTab },
    { id: 'settings', label: 'Settings', component: SettingsPage },
  ]
  
  const activeTabData = tabs.find(t => t.id === activeTab)
  const Component = activeTabData?.component || tabs[0].component
  
  return (
    <div className="app-container">
      <div className="navbar">
        <h1>🎬 MB User Sync</h1>
        <p>Synchronize users across media servers</p>
      </div>
      
      <div className="tab-navigation">
        {tabs.map(tab => (
          <button
            key={tab.id}
            className={`tab-nav-item ${activeTab === tab.id ? 'active' : ''}`}
            onClick={() => setActiveTab(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </div>
      
      <div className="content">
        <Component />
      </div>
    </div>
  )
}
