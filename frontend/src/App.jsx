import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './context/AuthContext'
import { ThemeProvider } from './context/ThemeContext'
import Layout from './components/Layout'
import Login from './pages/Login'
import Register from './pages/Register'
import Dashboard from './pages/Dashboard'
import Upload from './pages/Upload'
import DatasetDetail from './pages/DatasetDetail'
import Rules from './pages/Rules'
import Cleaning from './pages/Cleaning'
import AboutUs from './pages/AboutUs'

function ProtectedRoute({ children }) {
  const { isAuthenticated, loading } = useAuth()
  if (loading) {
    return (
      <div className="min-h-screen bg-cp-bg flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <div className="w-10 h-10 border-2 border-cp-purple border-t-transparent rounded-full animate-spin" />
          <span className="text-cp-muted text-sm">Loading CleanPilot…</span>
        </div>
      </div>
    )
  }
  return isAuthenticated ? children : <Navigate to="/about" replace />
}

function PublicRoute({ children }) {
  const { isAuthenticated, loading } = useAuth()
  if (loading) return null
  return isAuthenticated ? <Navigate to="/" replace /> : children
}

function AppRoutes() {
  return (
    <Routes>
      {/* Public routes */}
      <Route path="/login" element={<PublicRoute><Login /></PublicRoute>} />
      <Route path="/register" element={<PublicRoute><Register /></PublicRoute>} />
      <Route path="/about" element={<AboutUs />} />

      {/* Protected routes */}
      <Route path="/" element={
        <ProtectedRoute>
          <Layout><Dashboard /></Layout>
        </ProtectedRoute>
      } />
      <Route path="/upload" element={
        <ProtectedRoute>
          <Layout><Upload /></Layout>
        </ProtectedRoute>
      } />
      <Route path="/dataset/:id" element={
        <ProtectedRoute>
          <Layout><DatasetDetail /></Layout>
        </ProtectedRoute>
      } />
      <Route path="/rules/:datasetId" element={
        <ProtectedRoute>
          <Layout><Rules /></Layout>
        </ProtectedRoute>
      } />
      <Route path="/cleaning/:datasetId" element={
        <ProtectedRoute>
          <Layout><Cleaning /></Layout>
        </ProtectedRoute>
      } />

      <Route path="*" element={<Navigate to="/about" replace />} />
    </Routes>
  )
}

export default function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <Router>
          <AppRoutes />
        </Router>
      </AuthProvider>
    </ThemeProvider>
  )
}
