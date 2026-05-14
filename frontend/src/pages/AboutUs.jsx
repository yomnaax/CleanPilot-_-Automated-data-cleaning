import { Link } from 'react-router-dom'
import {
  Satellite, Sparkles, ShieldCheck, Zap, BarChart3,
  ArrowRight, Database, Wand2, FileCheck2
} from 'lucide-react'

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
  return (
    <div className="min-h-screen bg-cp-bg text-cp-text">
      {/* Background orbs */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-0 left-1/3 w-[600px] h-[600px] bg-cp-purple/6 rounded-full blur-3xl" />
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-cyan-500/5 rounded-full blur-3xl" />
      </div>

      {/* Nav bar */}
      <header className="sticky top-0 z-50 border-b border-cp-border bg-cp-surface/80 backdrop-blur-md">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <Link to="/login" className="flex items-center gap-3 group">
              <div className="w-8 h-8 rounded-lg bg-cp-purple/20 border border-cp-purple/40 flex items-center justify-center group-hover:bg-cp-purple/30 transition-colors">
                <Satellite className="w-4 h-4 text-cp-purple" />
              </div>
              <span className="font-semibold text-lg tracking-tight text-cp-text">
                Clean<span className="text-cp-purple">Pilot</span>
              </span>
            </Link>

            <div className="flex items-center gap-3">
              <Link
                to="/login"
                className="text-sm text-cp-muted hover:text-cp-text transition-colors px-3 py-2 rounded-lg hover:bg-white/5"
              >
                Sign in
              </Link>
              <Link
                to="/register"
                className="cp-btn-primary py-2 px-4 text-sm"
              >
                Get started
                <ArrowRight className="w-4 h-4" />
              </Link>
            </div>
          </div>
        </div>
      </header>

      <main className="relative z-10">

        {/* Hero */}
        <section className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 pt-24 pb-20 text-center">
          <div className="inline-flex items-center gap-2 bg-cp-purple/10 border border-cp-purple/20 rounded-full px-4 py-1.5 text-cp-purple-light text-sm font-medium mb-6">
            <Sparkles className="w-3.5 h-3.5" />
            Intelligent Data Cleaning
          </div>
          <h1 className="text-5xl sm:text-6xl font-bold text-cp-text tracking-tight mb-6 leading-tight">
            About{' '}
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-cp-purple to-cyan-400">
              CleanPilot
            </span>
          </h1>
          <p className="text-cp-muted text-lg sm:text-xl max-w-2xl mx-auto leading-relaxed">
            CleanPilot is an AI-assisted data cleaning platform built to help data scientists,
            analysts, and engineers transform messy raw datasets into clean, analysis-ready data —
            faster and smarter than ever before.
          </p>
        </section>

        {/* Mission */}
        <section className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 pb-24">
          <div className="auth-card-border">
            <div className="p-10 sm:p-14 grid sm:grid-cols-2 gap-10 items-center">
              <div>
                <h2 className="text-2xl font-semibold text-cp-text mb-4">Our Mission</h2>
                <p className="text-cp-muted leading-relaxed mb-4">
                  Data quality is one of the biggest bottlenecks in every data-driven project.
                  Analysts spend up to <span className="text-cp-text font-medium">80% of their time</span> just
                  preparing and cleaning data before any analysis can begin.
                </p>
                <p className="text-cp-muted leading-relaxed">
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
                  <div key={label} className="bg-cp-surface border border-cp-border rounded-xl p-5 text-center">
                    <p className="text-3xl font-bold text-cp-purple-light mb-1">{value}</p>
                    <p className="text-xs text-cp-muted">{label}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>

        {/* Features */}
        <section className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 pb-24">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-semibold text-cp-text mb-3">What CleanPilot Does</h2>
            <p className="text-cp-muted max-w-xl mx-auto">
              Everything you need to go from raw, messy data to clean, trustworthy data.
            </p>
          </div>
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
            {features.map(({ icon: Icon, title, desc }) => (
              <div
                key={title}
                className="bg-cp-card border border-cp-border rounded-xl p-6 hover:border-cp-purple/30 transition-colors group"
              >
                <div className="w-10 h-10 rounded-lg bg-cp-purple/15 border border-cp-purple/25 flex items-center justify-center mb-4 group-hover:bg-cp-purple/25 transition-colors">
                  <Icon className="w-5 h-5 text-cp-purple-light" />
                </div>
                <h3 className="font-semibold text-cp-text mb-2">{title}</h3>
                <p className="text-cp-muted text-sm leading-relaxed">{desc}</p>
              </div>
            ))}
          </div>
        </section>

        {/* Team */}
        <section className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 pb-32">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-semibold text-cp-text mb-3">The Team</h2>
            <p className="text-cp-muted max-w-xl mx-auto">
              CleanPilot is built with care by a small team passionate about data quality.
            </p>
          </div>
          <div className="flex flex-wrap justify-center gap-6">
            {team.map(({ name, initials }) => (
              <div
                key={name}
                className="bg-cp-card border border-cp-border rounded-xl p-6 flex flex-col items-center text-center w-48"
              >
                <div className="w-14 h-14 rounded-full bg-cp-purple/20 border border-cp-purple/40 flex items-center justify-center text-lg font-bold text-cp-purple-light mb-3">
                  {initials}
                </div>
                <p className="font-semibold text-cp-text text-sm">{name}</p>
              </div>
            ))}
          </div>
        </section>

      </main>

      {/* Footer */}
      <footer className="border-t border-cp-border py-6">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-3">
          <p className="text-xs text-cp-faint">© 2025 CleanPilot · Intelligent Data Cleaning</p>
          <div className="flex items-center gap-4 text-xs text-cp-faint">
            <Link to="/login" className="hover:text-cp-muted transition-colors">Sign in</Link>
            <Link to="/register" className="hover:text-cp-muted transition-colors">Sign up</Link>
          </div>
        </div>
      </footer>
    </div>
  )
}
