import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { LayoutDashboard, Upload, LogOut, ChevronDown, Satellite, Sun, Moon } from 'lucide-react'
import { useState, useEffect } from 'react'

const navItems = [
  { path: '/', label: 'Dashboard', icon: LayoutDashboard },
  { path: '/upload', label: 'Upload Dataset', icon: Upload },
]

export default function Layout({ children }) {
  const location = useLocation()
  const navigate = useNavigate()
  const { user, logout } = useAuth()
  const [userMenuOpen, setUserMenuOpen] = useState(false)
  const [dark, setDark] = useState(() => {
    const saved = localStorage.getItem('theme')
    return saved ? saved === 'dark' : true
  })

  useEffect(() => {
    document.documentElement.classList.toggle('dark', dark)
    localStorage.setItem('theme', dark ? 'dark' : 'light')
  }, [dark])

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  const initials = user?.full_name
    ? user.full_name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2)
    : user?.email?.[0]?.toUpperCase() || 'U'

  return (
    <div className={`min-h-screen flex flex-col ${dark ? 'bg-cp-bg text-cp-text' : 'bg-gray-50 text-gray-900'}`}>
      {/* Top nav */}
      <header className={`sticky top-0 z-50 border-b ${dark ? 'bg-cp-surface border-cp-border' : 'bg-white border-gray-200 shadow-sm'}`}>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">

            {/* Logo */}
            <Link to="/" className="flex items-center gap-3 group">
              <div className={`w-8 h-8 rounded-lg flex items-center justify-center transition-colors ${dark ? 'bg-cp-purple/20 border border-cp-purple/40 group-hover:bg-cp-purple/30' : 'bg-violet-100 border border-violet-300 group-hover:bg-violet-200'}`}>
                <Satellite className={`w-4 h-4 ${dark ? 'text-cp-purple' : 'text-violet-600'}`} />
              </div>
              <span className={`font-semibold text-lg tracking-tight ${dark ? 'text-cp-text' : 'text-gray-900'}`}>
                Clean<span className={dark ? 'text-cp-purple' : 'text-violet-600'}>Pilot</span>
              </span>
            </Link>

            {/* Nav */}
            <nav className="flex items-center gap-1">
              {navItems.map(({ path, label, icon: Icon }) => {
                const active = location.pathname === path
                return (
                  <Link
                    key={path}
                    to={path}
                    className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-all duration-150 ${
                      active
                        ? dark
                          ? 'bg-cp-purple/15 text-cp-purple-light border border-cp-purple/20'
                          : 'bg-violet-100 text-violet-700 border border-violet-200'
                        : dark
                          ? 'text-cp-muted hover:text-cp-text hover:bg-white/5'
                          : 'text-gray-500 hover:text-gray-900 hover:bg-gray-100'
                    }`}
                  >
                    <Icon className="w-4 h-4" />
                    <span className="hidden sm:inline">{label}</span>
                  </Link>
                )
              })}
            </nav>

            {/* Right side */}
            <div className="flex items-center gap-2">

              {/* Theme toggle */}
              <button
                onClick={() => setDark(v => !v)}
                className={`w-9 h-9 rounded-lg flex items-center justify-center border transition-colors ${
                  dark
                    ? 'border-cp-border text-amber-400 hover:bg-white/5'
                    : 'border-gray-200 text-gray-500 hover:bg-gray-100'
                }`}
                title={dark ? 'Switch to light mode' : 'Switch to dark mode'}
              >
                {dark ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
              </button>

              {/* User menu */}
              <div className="relative">
                <button
                  onClick={() => setUserMenuOpen(v => !v)}
                  className={`flex items-center gap-2.5 px-3 py-2 rounded-lg transition-colors ${dark ? 'hover:bg-white/5' : 'hover:bg-gray-100'}`}
                >
                  <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-semibold ${dark ? 'bg-cp-purple/20 border border-cp-purple/40 text-cp-purple-light' : 'bg-violet-100 border border-violet-300 text-violet-700'}`}>
                    {initials}
                  </div>
                  <span className={`hidden sm:inline text-sm max-w-[120px] truncate ${dark ? 'text-cp-muted' : 'text-gray-600'}`}>
                    {user?.full_name || user?.email}
                  </span>
                  <ChevronDown className={`w-3.5 h-3.5 transition-transform ${userMenuOpen ? 'rotate-180' : ''} ${dark ? 'text-cp-faint' : 'text-gray-400'}`} />
                </button>

                {userMenuOpen && (
                  <div className={`absolute right-0 mt-2 w-56 rounded-xl shadow-xl overflow-hidden z-50 animate-fade-in border ${dark ? 'bg-cp-card border-cp-border' : 'bg-white border-gray-200'}`}>
                    <div className={`px-4 py-3 border-b ${dark ? 'border-cp-border' : 'border-gray-100'}`}>
                      <p className={`text-sm font-medium truncate ${dark ? 'text-cp-text' : 'text-gray-900'}`}>{user?.full_name || 'User'}</p>
                      <p className={`text-xs truncate mt-0.5 ${dark ? 'text-cp-muted' : 'text-gray-500'}`}>{user?.email}</p>
                    </div>
                    <button
                      onClick={handleLogout}
                      className={`w-full flex items-center gap-3 px-4 py-3 text-sm transition-colors ${dark ? 'text-cp-muted hover:text-red-400 hover:bg-red-500/5' : 'text-gray-500 hover:text-red-600 hover:bg-red-50'}`}
                    >
                      <LogOut className="w-4 h-4" />
                      Sign out
                    </button>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Main */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {children}
      </main>

      {/* Footer */}
      <footer className={`border-t py-4 ${dark ? 'border-cp-border' : 'border-gray-200'}`}>
        <p className={`text-center text-xs ${dark ? 'text-cp-faint' : 'text-gray-400'}`}>
          CleanPilot · Intelligent Data Cleaning
        </p>
      </footer>
    </div>
  )
}