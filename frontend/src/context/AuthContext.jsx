import { createContext, useContext, useState, useEffect, useCallback } from 'react'
import { authAPI } from '../api/client'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [token, setToken] = useState(() => localStorage.getItem('cp_token'))
  const [loading, setLoading] = useState(true)

  const logout = useCallback(() => {
    localStorage.removeItem('cp_token')
    setToken(null)
    setUser(null)
  }, [])

  useEffect(() => {
    const init = async () => {
      const stored = localStorage.getItem('cp_token')
      if (!stored) { setLoading(false); return }
      try {
        const res = await authAPI.me(stored)
        setUser(res.data)
        setToken(stored)
      } catch {
        localStorage.removeItem('cp_token')
        setToken(null)
      } finally {
        setLoading(false)
      }
    }
    init()
  }, [])

  const login = async (email, password) => {
    const res = await authAPI.login(email, password)
    const { access_token, user: userData } = res.data
    localStorage.setItem('cp_token', access_token)
    setToken(access_token)
    setUser(userData)
    return userData
  }

  const register = async (email, password, fullName) => {
    const res = await authAPI.register(email, password, fullName)
    const { access_token, user: userData } = res.data
    localStorage.setItem('cp_token', access_token)
    setToken(access_token)
    setUser(userData)
    return userData
  }

  return (
    <AuthContext.Provider value={{ user, token, loading, login, logout, register, isAuthenticated: !!token }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
