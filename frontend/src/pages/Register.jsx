import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { useTheme } from '../context/ThemeContext'
import { Satellite, Eye, EyeOff, ArrowRight, AlertCircle, CheckCircle2 } from 'lucide-react'
import AuthNav from '../components/AuthNav'

const PasswordStrength = ({ password, dark }) => {
  const checks = [
    { label: '8+ characters', ok: password.length >= 8 },
    { label: 'Uppercase letter', ok: /[A-Z]/.test(password) },
    { label: 'Number', ok: /\d/.test(password) },
  ]
  if (!password) return null
  return (
    <div className="flex gap-3 mt-2">
      {checks.map(({ label, ok }) => (
        <span key={label} className={`flex items-center gap-1 text-xs ${ok ? 'text-green-500' : dark ? 'text-cp-faint' : 'text-gray-400'}`}>
          <CheckCircle2 className={`w-3 h-3 ${ok ? 'text-green-500' : dark ? 'text-cp-faint' : 'text-gray-400'}`} />
          {label}
        </span>
      ))}
    </div>
  )
}

export default function Register() {
  const navigate = useNavigate()
  const { register } = useAuth()
  const { dark } = useTheme()
  const [fullName, setFullName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPw, setShowPw] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    if (!fullName || !email || !password) { setError('Please fill in all fields'); return }
    if (password.length < 8) { setError('Password must be at least 8 characters'); return }
    setLoading(true)
    try {
      await register(email, password, fullName)
      navigate('/')
    } catch (err) {
      setError(err.response?.data?.detail || 'Registration failed. Try a different email.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className={`min-h-screen flex flex-col ${dark ? 'bg-cp-bg' : 'bg-gray-50'}`}>
      <AuthNav />
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/3 right-1/4 w-96 h-96 bg-cp-purple/8 rounded-full blur-3xl" />
        <div className="absolute bottom-1/3 left-1/4 w-80 h-80 bg-cyan-500/5 rounded-full blur-3xl" />
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
            <h1 className={`text-2xl font-semibold ${dark ? 'text-cp-text' : 'text-gray-900'}`}>Create your account</h1>
            <p className={`text-sm mt-1 ${dark ? 'text-cp-muted' : 'text-gray-500'}`}>Start cleaning data intelligently</p>
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
                  <label className={`block text-sm font-medium mb-1.5 ${dark ? 'text-cp-muted' : 'text-gray-600'}`}>Full name</label>
                  <input
                    type="text"
                    value={fullName}
                    onChange={e => setFullName(e.target.value)}
                    placeholder="Jane Doe"
                    className={dark ? 'cp-input' : 'light-input'}
                    autoComplete="name"
                    autoFocus
                  />
                </div>

                <div>
                  <label className={`block text-sm font-medium mb-1.5 ${dark ? 'text-cp-muted' : 'text-gray-600'}`}>Email</label>
                  <input
                    type="email"
                    value={email}
                    onChange={e => setEmail(e.target.value)}
                    placeholder="you@example.com"
                    className={dark ? 'cp-input' : 'light-input'}
                    autoComplete="email"
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
                      autoComplete="new-password"
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
                  <PasswordStrength password={password} dark={dark} />
                </div>

                <button
                  type="submit"
                  disabled={loading}
                  className="cp-btn-primary w-full mt-2"
                >
                  {loading ? (
                    <span className="flex items-center gap-2">
                      <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                      Creating account…
                    </span>
                  ) : (
                    <span className="flex items-center gap-2">
                      Create account
                      <ArrowRight className="w-4 h-4" />
                    </span>
                  )}
                </button>
              </form>
            </div>
          </div>

          <p className={`text-center text-sm mt-6 ${dark ? 'text-cp-muted' : 'text-gray-600'}`}>
            Already have an account?{' '}
            <Link to="/login" className={`font-medium transition-colors ${
              dark ? 'text-cp-purple-light hover:text-cp-purple' : 'text-violet-600 hover:text-violet-700'
            }`}>
              Sign in
            </Link>
          </p>
        </div>
      </div>
    </div>
  )
}
