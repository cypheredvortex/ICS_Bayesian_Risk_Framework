/**
 * Auth store for the ICS GRC platform.
 *
 * Provides:
 * - Login / logout with JWT token persistence (localStorage)
 * - Auto-refresh on page load (reads token from localStorage)
 * - Current user info with role name and permissions
 * - Auth header helper for API calls
 */

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import { API_BASE_URL } from './constants'
import { setAuthHeader } from './services/grc'
import { parseErrorDetail } from './utils'

// ── Types ──────────────────────────────────────────────────────

export interface UserInfo {
  id: number
  username: string
  email: string
  first_name: string | null
  last_name: string | null
  job_title: string | null
  organization_id: number | null
  role_id: number | null
  department_name: string | null
  is_active: boolean
  is_locked: boolean
  last_login_at: string | null
  created_at: string | null
  role_name: string | null
  permissions: string[]
}

export interface AuthState {
  /** JWT access token, or null if not authenticated */
  token: string | null
  /** Decoded user info from /api/v1/auth/me */
  user: UserInfo | null
  /** True while loading persisted token on mount */
  loading: boolean
  /** Most recent login error message */
  error: string | null
}

export interface AuthContextValue extends AuthState {
  /** Log in with username+password */
  login: (username: string, password: string) => Promise<void>
  /** Log out (clear token, invalidate server-side) */
  logout: () => Promise<void>
  /** True if the user has a specific permission */
  hasPermission: (permission: string) => boolean
  /** True if the user has admin role */
  isAdmin: boolean
  /** Authorization header value for API calls */
  authHeader: Record<string, string>
}

// ── Helpers ─────────────────────────────────────────────────────

const TOKEN_KEY = 'ics_grc_token'

function getStoredToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY)
  } catch {
    return null
  }
}

function storeToken(token: string | null): void {
  try {
    if (token) {
      localStorage.setItem(TOKEN_KEY, token)
    } else {
      localStorage.removeItem(TOKEN_KEY)
    }
  } catch {
    // localStorage may be unavailable in some environments
  }
}

async function fetchUser(token: string): Promise<UserInfo> {
  const response = await fetch(`${API_BASE_URL}/api/v1/auth/me`, {
    headers: { Authorization: `Bearer ${token}` },
  })
  if (!response.ok) {
    throw new Error(await parseErrorDetail(response, 'Failed to load user profile.'))
  }
  return response.json() as Promise<UserInfo>
}

// ── Context ────────────────────────────────────────────────────

const AuthContext = createContext<AuthContextValue | null>(null)

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within an AuthProvider')
  return ctx
}

// ── Provider ───────────────────────────────────────────────────

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = useState<string | null>(getStoredToken)
  const [user, setUser] = useState<UserInfo | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // On mount, validate the stored token (if any) by fetching /me
  useEffect(() => {
    const stored = getStoredToken()
    if (!stored) {
      setLoading(false)
      return
    }

    fetchUser(stored)
      .then((u) => {
        setUser(u)
        setToken(stored)
        setAuthHeader({ Authorization: `Bearer ${stored}` })
        setError(null)
      })
      .catch(() => {
        // Token expired or invalid — clear it
        storeToken(null)
        setToken(null)
        setUser(null)
        setAuthHeader({})
      })
      .finally(() => {
        setLoading(false)
      })
  }, [])

  const login = useCallback(async (username: string, password: string) => {
    setError(null)
    setLoading(true)

    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
      })

      if (!response.ok) {
        const detail = await parseErrorDetail(response, 'Login failed.')
        throw new Error(detail)
      }

      const data = (await response.json()) as { access_token: string }
      const token = data.access_token
      storeToken(token)
      setToken(token)
      setAuthHeader({ Authorization: `Bearer ${token}` })

      // Fetch full user profile from /me to get role_name and permissions
      const userInfo = await fetchUser(token)
      setUser(userInfo)
      setError(null)
    } catch (caught) {
      const message = caught instanceof Error ? caught.message : 'Login failed.'
      setError(message)
      throw caught
    } finally {
      setLoading(false)
    }
  }, [])

  const logout = useCallback(async () => {
    if (token) {
      try {
        await fetch(`${API_BASE_URL}/api/v1/auth/logout`, {
          method: 'POST',
          headers: { Authorization: `Bearer ${token}` },
        })
      } catch {
        // Best-effort; ignore server-side invalidation errors
      }
    }

    storeToken(null)
    setToken(null)
    setUser(null)
    setAuthHeader({})
    setError(null)
  }, [token])

  const hasPermission = useCallback(
    (permission: string): boolean => {
      if (!user) return false
      return user.permissions.includes('*') || user.permissions.includes(permission)
    },
    [user],
  )

  const isAdmin = useMemo(() => {
    return user?.role_name === 'admin' || hasPermission('*')
  }, [user, hasPermission])

  const authHeader = useMemo((): Record<string, string> => {
    return token ? { Authorization: `Bearer ${token}` } : {}
  }, [token])

  const value = useMemo<AuthContextValue>(
    () => ({
      token,
      user,
      loading,
      error,
      login,
      logout,
      hasPermission,
      isAdmin,
      authHeader,
    }),
    [token, user, loading, error, login, logout, hasPermission, isAdmin, authHeader],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
