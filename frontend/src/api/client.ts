import axios from 'axios'

const api = axios.create({ baseURL: '/', withCredentials: true })

let accessToken: string | null = null
let refreshPromise: Promise<string | null> | null = null

export function setAccessToken(token: string | null) {
  accessToken = token
}

export function getAccessToken() {
  return accessToken
}

async function doRefresh(): Promise<string | null> {
  try {
    const res = await axios.post('/api/auth/refresh', {}, { withCredentials: true })
    const token = (res.data as { access_token: string }).access_token
    setAccessToken(token)
    return token
  } catch {
    setAccessToken(null)
    return null
  }
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
      if (!refreshPromise) refreshPromise = doRefresh()
      const token = await refreshPromise
      refreshPromise = null
      if (token) {
        original.headers.Authorization = `Bearer ${token}`
        return api(original)
      }
      setAccessToken(null)
      window.location.href = '/login'
    }
    return Promise.reject(error)
  },
)

export default api