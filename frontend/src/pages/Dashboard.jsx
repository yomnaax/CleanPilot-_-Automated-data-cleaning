import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { FileText, Clock, ArrowRight, Trash2 } from 'lucide-react'
import { getDatasets, deleteDataset } from '../api/client'

export default function Dashboard() {
  const [datasets, setDatasets] = useState([])
  const [loading, setLoading] = useState(true)
  const [deletingId, setDeletingId] = useState(null)

  useEffect(() => {
    loadDatasets()
  }, [])

  const loadDatasets = async () => {
    try {
      const response = await getDatasets()
      setDatasets(response.data || [])
    } catch (error) {
      console.error('Failed to load datasets:', error)
      setDatasets([])
    } finally {
      setLoading(false)
    }
  }

  const handleDelete = async (e, dataset) => {
    e.preventDefault()
    e.stopPropagation()

    const ok = window.confirm(`Delete dataset "${dataset.name}"? This will also delete its rules and runs.`)
    if (!ok) return

    try {
      setDeletingId(dataset.id)
      await deleteDataset(dataset.id)
      await loadDatasets()
    } catch (error) {
      console.error('Failed to delete dataset:', error)
      window.alert('Failed to delete dataset. Check backend logs.')
    } finally {
      setDeletingId(null)
    }
  }

  const getPurposeBadge = (purpose) => {
    const colors = {
      rule_extraction: 'bg-purple-100 text-purple-800',
      cleaning: 'bg-green-100 text-green-800',
    }
    return (
      <span className={`px-2 py-1 rounded-full text-xs font-medium ${colors[purpose] || 'bg-gray-100 text-gray-800'}`}>
        {purpose === 'rule_extraction' ? 'Rule Extraction' : 'Cleaning'}
      </span>
    )
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  return (
    <div>
      <div className="mb-8">
        <h2 className="text-3xl font-bold text-gray-900 dark:text-gray-100">Datasets</h2>
        <p className="mt-2 text-gray-600 dark:text-gray-300">Manage and process your datasets</p>
      </div>

      {datasets.length === 0 ? (
        <div className="text-center py-12 bg-white dark:bg-slate-950 black:bg-black rounded-lg shadow border border-transparent dark:border-slate-800 black:border-gray-900">
          <FileText className="mx-auto h-12 w-12 text-gray-400 dark:text-gray-500" />
          <h3 className="mt-4 text-lg font-medium text-gray-900 dark:text-gray-100">No datasets yet</h3>
          <p className="mt-2 text-gray-500 dark:text-gray-400">Get started by uploading your first dataset</p>
          <Link
            to="/upload"
            className="mt-6 inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700"
          >
            Upload Dataset
          </Link>
        </div>
      ) : (
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          {datasets.map((dataset) => (
            <Link
              key={dataset.id}
              to={`/dataset/${dataset.id}`}
              className="bg-white dark:bg-slate-950 black:bg-black border border-transparent dark:border-slate-800 black:border-gray-900 rounded-lg shadow hover:shadow-lg transition-shadow p-6"
            >
              <div className="flex items-start justify-between mb-4">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 truncate">
                  {dataset.name}
                </h3>
                <div className="flex items-center gap-2">
                  {getPurposeBadge(dataset.purpose)}
                  <button
                    type="button"
                    onClick={(e) => handleDelete(e, dataset)}
                    disabled={deletingId === dataset.id}
                    className="inline-flex items-center justify-center rounded-md p-2 text-gray-500 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/30 disabled:opacity-50 disabled:cursor-not-allowed"
                    title="Delete dataset"
                    aria-label="Delete dataset"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              </div>
              <div className="space-y-2 text-sm text-gray-600 dark:text-gray-300">
                <div className="flex items-center">
                  <span className="font-medium">Modality:</span>
                  <span className="ml-2 capitalize">{dataset.modality}</span>
                </div>
                <div className="flex items-center">
                  <Clock className="h-4 w-4 mr-2" />
                  <span>{new Date(dataset.created_at).toLocaleDateString()}</span>
                </div>
              </div>
              <div className="mt-4 flex items-center text-blue-600 dark:text-cyan-300 black:text-cyan-300">
                <span className="text-sm font-medium">View Details</span>
                <ArrowRight className="ml-2 h-4 w-4" />
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}










