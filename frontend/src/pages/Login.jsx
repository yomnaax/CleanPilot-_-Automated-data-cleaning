import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { useTheme } from '../context/ThemeContext'
import { Satellite, Eye, EyeOff, ArrowRight, AlertCircle } from 'lucide-react'
import AuthNav from '../components/AuthNav'

export default function Login() {
  const navigate = useNavigate()
  const { login } = useAuth()
  const { dark } = useTheme()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPw, setShowPw] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    if (!email || !password) { setError('Please fill in all fields'); return }
    setLoading(true)
    try {
      await login(email, password)
      navigate('/')
    } catch (err) {
      setError(err.response?.data?.detail || 'Invalid email or password')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className={`min-h-screen flex flex-col ${dark ? 'bg-cp-bg' : 'bg-gray-50'}`}>
      <AuthNav />
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-cp-purple/8 rounded-full blur-3xl" />
        <div className="absolute bottom-1/4 right-1/4 w-80 h-80 bg-cyan-500/5 rounded-full blur-3xl" />
      </div>

      <div className="flex-1 flex items-center justify-center px-4">
        <div className="w-full max-w-md relative z-10 animate-slide-up">

          {/* Logo */}
          <div className="flex flex-col items-center mb-8">
            <div className={`w-14 h-14 rounded-2xl flex items-center justify-center mb-4 border ${
              dark ? 'bg-cp-purple/20 border-cp-purple/40' : 'bg-violet-100 border-violet-300'
            }`}>
              <Satellite className={`w-7 h-7 ${dark ? 'text-cp-purple' : 'text-violet-600'}`} />
            </div>
            <h1 className={`text-2xl font-semibold ${dark ? 'text-cp-text' : 'text-gray-900'}`}>Welcome back</h1>
            <p className={`text-sm mt-1 ${dark ? 'text-cp-muted' : 'text-gray-500'}`}>Sign in to your CleanPilot account</p>
          </div>

          {/* Card */}
          <div className={dark ? 'auth-card-border' : 'bg-white border border-gray-200 rounded-2xl shadow-md'}>
            <div className="p-8">
              {error && (
                <div className="flex items-center gap-2.5 bg-red-500/10 border border-red-500/20 rounded-lg px-4 py-3 mb-6 text-red-400 text-sm animate-fade-in">
                  <AlertCircle className="w-4 h-4 flex-shrink-0" />
                  {error}
                </div>
              )}

              <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                  <label className={`block text-sm font-medium mb-1.5 ${dark ? 'text-cp-muted' : 'text-gray-600'}`}>Email</label>
                  <input
                    type="email"
                    value={email}
                    onChange={e => setEmail(e.target.value)}
                    placeholder="you@example.com"
                    className={dark ? 'cp-input' : 'light-input'}
                    autoComplete="email"
                    autoFocus
                  />
                </div>

                <div>
                  <label className={`block text-sm font-medium mb-1.5 ${dark ? 'text-cp-muted' : 'text-gray-600'}`}>Password</label>
                  <div className="relative">
                    <input
                      type={showPw ? 'text' : 'password'}
                      value={password}
                      onChange={e => setPassword(e.target.value)}
                      placeholder="••••••••"
                      className={`${dark ? 'cp-input' : 'light-input'} pr-11`}
                      autoComplete="current-password"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPw(v => !v)}
                      className={`absolute right-3 top-1/2 -translate-y-1/2 transition-colors ${
                        dark ? 'text-cp-faint hover:text-cp-muted' : 'text-gray-400 hover:text-gray-600'
                      }`}
                    >
                      {showPw ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={loading}
                  className="cp-btn-primary w-full mt-2"
                >
                  {loading ? (
                    <span className="flex items-center gap-2">
                      <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                      Signing in…
                    </span>
                  ) : (
                    <span className="flex items-center gap-2">
                      Sign in
                      <ArrowRight className="w-4 h-4" />
                    </span>
                  )}
                </button>
              </form>
            </div>
          </div>

          <p className={`text-center text-sm mt-6 ${dark ? 'text-cp-muted' : 'text-gray-600'}`}>
            Don't have an account?{' '}
            <Link to="/register" className={`font-medium transition-colors ${
              dark ? 'text-cp-purple-light hover:text-cp-purple' : 'text-violet-600 hover:text-violet-700'
            }`}>
              Create one
            </Link>
          </p>
        </div>
      </div>
    </div>
  )
}
