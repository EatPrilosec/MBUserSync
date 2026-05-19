import { create } from 'zustand'

/**
 * Global app store using Zustand
 */
export const useAppStore = create((set) => ({
  // UI state
  activeTab: 'emby',
  setActiveTab: (tab) => set({ activeTab: tab }),
  
  // Settings state
  settings: null,
  loading: false,
  error: null,
  
  setSettings: (settings) => set({ settings }),
  setLoading: (loading) => set({ loading }),
  setError: (error) => set({ error }),
  
  // Sync status
  syncStatus: null,
  setSyncStatus: (status) => set({ syncStatus: status }),
  
  // Server configs
  serverConfigs: {},
  setServerConfigs: (configs) => set({ serverConfigs: configs }),
}))

export default useAppStore
