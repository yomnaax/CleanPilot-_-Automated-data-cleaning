import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { Satellite, Eye, EyeOff, ArrowRight, AlertCircle, CheckCircle2 } from 'lucide-react'

const PasswordStrength = ({ password }) => {
  const checks = [
    { label: '8+ characters', ok: password.length >= 8 },
    { label: 'Uppercase letter', ok: /[A-Z]/.test(password) },
    { label: 'Number', ok: /\d/.test(password) },
  ]
  if (!password) return null
  return (
    <div className="flex gap-3 mt-2">
      {checks.map(({ label, ok }) => (
        <span key={label} className={`flex items-center gap-1 text-xs ${ok ? 'text-green-400' : 'text-cp-faint'}`}>
          <CheckCircle2 className={`w-3 h-3 ${ok ? 'text-green-400' : 'text-cp-faint'}`} />
          {label}
        </span>
      ))}
    </div>
  )
}

export default function Register() {
  const navigate = useNavigate()
  const { register } = useAuth()
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
    <div className="min-h-screen bg-cp-bg flex items-center justify-center px-4">
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/3 right-1/4 w-96 h-96 bg-cp-purple/8 rounded-full blur-3xl" />
        <div className="absolute bottom-1/3 left-1/4 w-80 h-80 bg-cyan-500/5 rounded-full blur-3xl" />
      </div>

      <div className="w-full max-w-md relative z-10 animate-slide-up">
        <div className="flex flex-col items-center mb-8">
          <div className="w-14 h-14 rounded-2xl bg-cp-purple/20 border border-cp-purple/40 flex items-center justify-center mb-4">
            <Satellite className="w-7 h-7 text-cp-purple" />
          </div>
          <h1 className="text-2xl font-semibold text-cp-text">Create your account</h1>
          <p className="text-cp-muted text-sm mt-1">Start cleaning data intelligently</p>
        </div>

        <div className="auth-card-border">
          <div className="p-8">
            {error && (
              <div className="flex items-center gap-2.5 bg-red-500/10 border border-red-500/20 rounded-lg px-4 py-3 mb-6 text-red-400 text-sm animate-fade-in">
                <AlertCircle className="w-4 h-4 flex-shrink-0" />
                {error}
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-cp-muted mb-1.5">Full name</label>
                <input
                  type="text"
                  value={fullName}
                  onChange={e => setFullName(e.target.value)}
                  placeholder="Jane Doe"
                  className="cp-input"
                  autoComplete="name"
                  autoFocus
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-cp-muted mb-1.5">Email</label>
                <input
                  type="email"
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  placeholder="you@example.com"
                  className="cp-input"
                  autoComplete="email"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-cp-muted mb-1.5">Password</label>
                <div className="relative">
                  <input
                    type={showPw ? 'text' : 'password'}
                    value={password}
                    onChange={e => setPassword(e.target.value)}
                    placeholder="••••••••"
                    className="cp-input pr-11"
                    autoComplete="new-password"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPw(v => !v)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-cp-faint hover:text-cp-muted transition-colors"
                  >
                    {showPw ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
                <PasswordStrength password={password} />
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

        <p className="text-center text-sm text-cp-muted mt-6">
          Already have an account?{' '}
          <Link to="/login" className="text-cp-purple-light hover:text-cp-purple transition-colors font-medium">
            Sign in
          </Link>
        </p>
        <p className="text-center text-sm text-cp-muted mt-3">
          <Link to="/about" className="text-cp-faint hover:text-cp-muted transition-colors">
            About CleanPilot
          </Link>
        </p>
      </div>
    </div>
  )
}
