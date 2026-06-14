import { useState, useEffect } from 'react'
import Layout from './pages/Layout'
import ResetPasswordPage from './pages/ResetPasswordPage'
import RegisterPage from './pages/RegisterPage'

export default function App() {
  const [currentPath, setCurrentPath] = useState(window.location.pathname)
  
  useEffect(() => {
    const onLocationChange = () => {
      setCurrentPath(window.location.pathname)
    }
    window.addEventListener('popstate', onLocationChange)
    return () => window.removeEventListener('popstate', onLocationChange)
  }, [])
  
  if (currentPath === '/reset') {
    return <ResetPasswordPage />
  }

  if (currentPath === '/register') {
    return <RegisterPage />
  }

  return <Layout />
}
