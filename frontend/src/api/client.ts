import axios from 'axios'
import type { User } from './types'

const api = axios.create({ baseURL: '/', withCredentials: true })

let accessToken: string | null = null
let refreshPromise: Promise<{ token: string; user: User } | null> | null = null
let restoring = true

export function setAccessToken(token: string | null) {
  accessToken = token
}

export function getAccessToken() {
  return accessToken
}

export function setRestoringDone() {
  restoring = false
}

async function doRefresh(): Promise<{ token: string; user: User } | null> {
  try {
    const res = await axios.post('/api/auth/refresh', {}, { withCredentials: true })
    const data = res.data as { access_token: string; user: User }
    setAccessToken(data.access_token)
    return { token: data.access_token, user: data.user }
  } catch {
    setAccessToken(null)
    return null
  }
}

export function refreshSession(): Promise<{ token: string; user: User } | null> {
  if (!refreshPromise) {
    refreshPromise = doRefresh().finally(() => {
      refreshPromise = null
    })
  }
  return refreshPromise
}

api.interceptors.request.use((config) => {
  if (accessToken) {
    config.headers.Authorization = `Bearer ${accessToken}`
  }
  return config
})

api.interceptors.response.use(
  (res) => res,
  async (error) => {
    const original = error.config
    if (
      error.response?.status === 401 &&
      !original._retry &&
      !original.url.includes('/api/auth/')
    ) {
      original._retry = true
      const result = await refreshSession()
      if (result) {
        original.headers.Authorization = `Bearer ${result.token}`
        return api(original)
      }
      setAccessToken(null)
      if (!restoring) {
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  },
)

export default api