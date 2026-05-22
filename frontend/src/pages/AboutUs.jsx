import { Link } from 'react-router-dom'
import {
  Sparkles, ShieldCheck, Zap, BarChart3,
  Database, Wand2, FileCheck2
} from 'lucide-react'
import AuthNav from '../components/AuthNav'
import { useTheme } from '../context/ThemeContext'

const features = [
  {
    icon: Database,
    title: 'Smart Dataset Upload',
    desc: 'Upload CSV files and CleanPilot instantly profiles your data — detecting types, distributions, and quality issues.',
  },
  {
    icon: Wand2,
    title: 'AI-Powered Cleaning',
    desc: 'Our AI engine suggests and applies cleaning rules tailored to your dataset: missing values, duplicates, outliers, and more.',
  },
  {
    icon: ShieldCheck,
    title: 'Custom Rules Engine',
    desc: 'Define your own cleaning logic with a flexible rules builder. Save and reuse rules across datasets.',
  },
  {
    icon: BarChart3,
    title: 'Before & After Reports',
    desc: 'Get detailed reports comparing raw vs. cleaned data so you always know exactly what changed and why.',
  },
  {
    icon: Zap,
    title: 'Fast & Accurate',
    desc: 'Processing is optimized to handle large datasets quickly without sacrificing accuracy or control.',
  },
  {
    icon: FileCheck2,
    title: 'Export Ready',
    desc: 'Download your cleaned dataset in CSV format, ready to plug into any pipeline, notebook, or BI tool.',
  },
]

const team = [
  { name: 'Yomna Khairy', initials: 'YK' },
  { name: 'Sama Eldesouky', initials: 'SE' },
  { name: 'Ziad Wael', initials: 'ZW' },
  { name: 'Abdelrahman Abourayya', initials: 'AA' },
  { name: 'Karim Abdullah', initials: 'KA' },
]

export default function AboutUs() {
  const { dark } = useTheme()

  return (
    <div className={`min-h-screen ${dark ? 'bg-cp-bg text-cp-text' : 'bg-gray-50 text-gray-900'}`}>
      {/* Background orbs */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-0 left-1/3 w-[600px] h-[600px] bg-cp-purple/6 rounded-full blur-3xl" />
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-cyan-500/5 rounded-full blur-3xl" />
      </div>

      <AuthNav />

      <main className="relative z-10">

        {/* Hero */}
        <section className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 pt-24 pb-20 text-center">
          <div className="inline-flex items-center gap-2 bg-cp-purple/10 border border-cp-purple/20 rounded-full px-4 py-1.5 text-cp-purple-light text-sm font-medium mb-6">
            <Sparkles className="w-3.5 h-3.5" />
            Intelligent Data Cleaning
          </div>
          <h1 className={`text-5xl sm:text-6xl font-bold tracking-tight mb-6 leading-tight ${dark ? 'text-cp-text' : 'text-gray-900'}`}>
            About{' '}
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-cp-purple to-cyan-400">
              CleanPilot
            </span>
          </h1>
          <p className={`text-lg sm:text-xl max-w-2xl mx-auto leading-relaxed ${dark ? 'text-cp-muted' : 'text-gray-600'}`}>
            CleanPilot is an AI-assisted data cleaning platform built to help data scientists,
            analysts, and engineers transform messy raw datasets into clean, analysis-ready data —
            faster and smarter than ever before.
          </p>
        </section>

        {/* Mission */}
        <section className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 pb-24">
          <div className={dark ? 'auth-card-border' : 'bg-white border border-gray-200 rounded-2xl shadow-md'}>
            <div className="p-10 sm:p-14 grid sm:grid-cols-2 gap-10 items-center">
              <div>
                <h2 className={`text-2xl font-semibold mb-4 ${dark ? 'text-cp-text' : 'text-gray-900'}`}>Our Mission</h2>
                <p className={`leading-relaxed mb-4 ${dark ? 'text-cp-muted' : 'text-gray-600'}`}>
                  Data quality is one of the biggest bottlenecks in every data-driven project.
                  Analysts spend up to <span className={`font-medium ${dark ? 'text-cp-text' : 'text-gray-900'}`}>80% of their time</span> just
                  preparing and cleaning data before any analysis can begin.
                </p>
                <p className={`leading-relaxed ${dark ? 'text-cp-muted' : 'text-gray-600'}`}>
                  CleanPilot was built to eliminate that bottleneck. By combining rule-based
                  automation with AI-driven suggestions, we give you a co-pilot that understands
                  your data and helps you clean it with confidence.
                </p>
              </div>
              <div className="grid grid-cols-2 gap-4">
                {[
                  { label: 'Datasets Cleaned', value: '10K+' },
                  { label: 'Rows Processed', value: '50M+' },
                  { label: 'Cleaning Rules', value: '200+' },
                  { label: 'Time Saved', value: '80%' },
                ].map(({ label, value }) => (
                  <div key={label} className={`rounded-xl p-5 text-center border ${
                    dark ? 'bg-cp-surface border-cp-border' : 'bg-gray-50 border-gray-200'
                  }`}>
                    <p className={`text-3xl font-bold mb-1 ${dark ? 'text-cp-purple-light' : 'text-violet-600'}`}>{value}</p>
                    <p className={`text-xs ${dark ? 'text-cp-muted' : 'text-gray-500'}`}>{label}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>

        {/* Features */}
        <section className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 pb-24">
          <div className="text-center mb-12">
            <h2 className={`text-3xl font-semibold mb-3 ${dark ? 'text-cp-text' : 'text-gray-900'}`}>What CleanPilot Does</h2>
            <p className={`max-w-xl mx-auto ${dark ? 'text-cp-muted' : 'text-gray-600'}`}>
              Everything you need to go from raw, messy data to clean, trustworthy data.
            </p>
          </div>
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
            {features.map(({ icon: Icon, title, desc }) => (
              <div
                key={title}
                className={`rounded-xl p-6 transition-colors group border ${
                  dark
                    ? 'bg-cp-card border-cp-border hover:border-cp-purple/30'
                    : 'bg-white border-gray-200 hover:border-violet-300'
                }`}
              >
                <div className={`w-10 h-10 rounded-lg flex items-center justify-center mb-4 border transition-colors ${
                  dark
                    ? 'bg-cp-purple/15 border-cp-purple/25 group-hover:bg-cp-purple/25'
                    : 'bg-violet-50 border-violet-200 group-hover:bg-violet-100'
                }`}>
                  <Icon className={`w-5 h-5 ${dark ? 'text-cp-purple-light' : 'text-violet-600'}`} />
                </div>
                <h3 className={`font-semibold mb-2 ${dark ? 'text-cp-text' : 'text-gray-900'}`}>{title}</h3>
                <p className={`text-sm leading-relaxed ${dark ? 'text-cp-muted' : 'text-gray-500'}`}>{desc}</p>
              </div>
            ))}
          </div>
        </section>

        {/* Team */}
        <section className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 pb-32">
          <div className="text-center mb-12">
            <h2 className={`text-3xl font-semibold mb-3 ${dark ? 'text-cp-text' : 'text-gray-900'}`}>The Team</h2>
            <p className={`max-w-xl mx-auto ${dark ? 'text-cp-muted' : 'text-gray-600'}`}>
              CleanPilot is built with care by a small team passionate about data quality.
            </p>
          </div>
          <div className="flex flex-wrap justify-center gap-6">
            {team.map(({ name, initials }) => (
              <div
                key={name}
                className={`rounded-xl p-6 flex flex-col items-center text-center w-48 border ${
                  dark ? 'bg-cp-card border-cp-border' : 'bg-white border-gray-200'
                }`}
              >
                <div className={`w-14 h-14 rounded-full flex items-center justify-center text-lg font-bold mb-3 border ${
                  dark
                    ? 'bg-cp-purple/20 border-cp-purple/40 text-cp-purple-light'
                    : 'bg-violet-100 border-violet-300 text-violet-700'
                }`}>
                  {initials}
                </div>
                <p className={`font-semibold text-sm ${dark ? 'text-cp-text' : 'text-gray-900'}`}>{name}</p>
              </div>
            ))}
          </div>
        </section>

      </main>

      {/* Footer */}
      <footer className={`border-t py-6 ${dark ? 'border-cp-border' : 'border-gray-200'}`}>
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-3">
          <p className={`text-xs ${dark ? 'text-cp-faint' : 'text-gray-400'}`}>© 2025 CleanPilot · Intelligent Data Cleaning</p>
          <div className={`flex items-center gap-4 text-xs ${dark ? 'text-cp-faint' : 'text-gray-400'}`}>
            <Link to="/login" className={`transition-colors ${dark ? 'hover:text-cp-muted' : 'hover:text-gray-600'}`}>Sign in</Link>
            <Link to="/register" className={`transition-colors ${dark ? 'hover:text-cp-muted' : 'hover:text-gray-600'}`}>Sign up</Link>
          </div>
        </div>
      </footer>
    </div>
  )
}
