import { Link, useLocation } from 'react-router-dom'
import { Satellite, Sun, Moon } from 'lucide-react'
import { useTheme } from '../context/ThemeContext'

const tabs = [
  { to: '/about', label: 'About Us' },
  { to: '/login', label: 'Sign In' },
  { to: '/register', label: 'Sign Up' },
]

export default function AuthNav() {
  const { pathname } = useLocation()
  const { dark, toggleDark } = useTheme()

  return (
    <header className={`sticky top-0 z-50 border-b backdrop-blur-md ${
      dark ? 'bg-cp-surface/80 border-cp-border' : 'bg-white/90 border-gray-200 shadow-sm'
    }`}>
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">

          <Link to="/about" className="flex items-center gap-3 group">
            <div className={`w-8 h-8 rounded-lg flex items-center justify-center transition-colors ${
              dark
                ? 'bg-cp-purple/20 border border-cp-purple/40 group-hover:bg-cp-purple/30'
                : 'bg-violet-100 border border-violet-300 group-hover:bg-violet-200'
            }`}>
              <Satellite className={`w-4 h-4 ${dark ? 'text-cp-purple' : 'text-violet-600'}`} />
            </div>
            <span className={`font-semibold text-lg tracking-tight ${dark ? 'text-cp-text' : 'text-gray-900'}`}>
              Clean<span className={dark ? 'text-cp-purple' : 'text-violet-600'}>Pilot</span>
            </span>
          </Link>

          <div className="flex items-center gap-2">
            <nav className="flex items-center gap-1">
              {tabs.map(({ to, label }) => (
                <Link
                  key={to}
                  to={to}
                  className={`px-4 py-2 rounded-lg text-sm font-medium transition-all duration-150 ${
                    pathname === to
                      ? dark
                        ? 'bg-cp-purple/15 text-cp-purple-light border border-cp-purple/20'
                        : 'bg-violet-50 text-violet-700 border border-violet-200'
                      : dark
                        ? 'text-cp-muted hover:text-cp-text hover:bg-white/5'
                        : 'text-gray-500 hover:text-gray-900 hover:bg-gray-100'
                  }`}
                >
                  {label}
                </Link>
              ))}
            </nav>

            <button
              onClick={toggleDark}
              className={`w-9 h-9 rounded-lg flex items-center justify-center border transition-colors ${
                dark
                  ? 'border-cp-border text-amber-400 hover:bg-white/5'
                  : 'border-gray-200 text-gray-500 hover:bg-gray-100'
              }`}
              title={dark ? 'Switch to light mode' : 'Switch to dark mode'}
            >
              {dark ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
            </button>
          </div>
        </div>
      </div>
    </header>
  )
}
