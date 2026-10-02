import { useEffect, useState } from 'react'
import { api, tokenStore } from './api.js'
import Auth from './pages/Auth.jsx'
import Workspace from './pages/Workspace.jsx'

export default function App() {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(Boolean(tokenStore.access))

  function hydrate() {
    setLoading(true)
    api('/auth/me')
      .then(setUser)
      .catch(() => {
        tokenStore.clear()
        setUser(null)
      })
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    if (tokenStore.access) hydrate()
    else setLoading(false)
  }, [])

  function logout() {
    tokenStore.clear()
    setUser(null)
  }

  if (loading) return <div className="loading-screen">Loading Passbook…</div>
  if (!user) return <Auth onAuthenticated={hydrate} />
  return <Workspace user={user} onLogout={logout} />
}
