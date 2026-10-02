import { useEffect, useState } from 'react'

// Tiny hash router. Hash URLs work with the static build FastAPI serves,
// so no server-side route config or extra dependency is needed.
const read = () => window.location.hash.replace(/^#/, '') || '/'

export function useRoute() {
  const [route, setRoute] = useState(read)
  useEffect(() => {
    const onChange = () => setRoute(read())
    window.addEventListener('hashchange', onChange)
    return () => window.removeEventListener('hashchange', onChange)
  }, [])
  return route
}

export function go(path) {
  window.location.hash = path
}
