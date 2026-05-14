import { useEffect, useState } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { ArrowLeft, Play, FileText, CheckCircle, AlertCircle } from 'lucide-react'
import { getDataset, profileDataset, extractRules, getSuggestedActions } from '../api/client'
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from 'recharts'

export default function DatasetDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [dataset, setDataset] = useState(null)
  const [profile, setProfile] = useState(null)
  const [loading, setLoading] = useState(true)
  const [processing, setProcessing] = useState(false)
  const [suggestions, setSuggestions] = useState([])
  const [edaView, setEdaView] = useState('missing') // missing | types | outliers | columns

  useEffect(() => {
    loadDataset()
    loadSuggestions()
  }, [id])

  const loadDataset = async () => {
    try {
      const response = await getDataset(id)
      setDataset(response.data)
    } catch (error) {
      console.error('Failed to load dataset:', error)
    } finally {
      setLoading(false)
    }
  }

  const loadSuggestions = async () => {
    try {
      const response = await getSuggestedActions(id)
      setSuggestions(response.data || [])
    } catch (error) {
      console.error('Failed to load suggestions:', error)
    }
  }

  const handleProfile = async () => {
    setProcessing(true)
    try {
      const response = await profileDataset(id)
      setProfile(response.data)
      // Pick a sensible default view based on available content
      const hasMissing = Object.keys(response.data?.summary?.missing_counts || {}).some((k) => (response.data.summary.missing_counts[k]?.count || 0) > 0)
      const hasOutliers = Array.isArray(response.data?.summary?.outliers) && response.data.summary.outliers.length > 0
      setEdaView(hasMissing ? 'missing' : hasOutliers ? 'outliers' : 'types')
      loadSuggestions()
    } catch (error) {
      alert('Failed to profile dataset: ' + (error.response?.data?.detail || error.message))
    } finally {
      setProcessing(false)
    }
  }

  const fmtPct = (v) => {
    if (v === null || v === undefined || Number.isNaN(v)) return '0%'
    return `${Number(v).toFixed(1)}%`
  }

  const shortLabel = (s, max = 12) => {
    const str = String(s ?? '')
    if (str.length <= max) return str
    return str.slice(0, Math.max(0, max - 1)) + '…'
  }

  const getMissingTop = () => {
    const mc = profile?.summary?.missing_counts || {}
    const rows = Object.entries(mc).map(([col, info]) => ({
      column: col,
      count: info?.count ?? 0,
      percentage: info?.percentage ?? 0,
    }))
    rows.sort((a, b) => (b.percentage || 0) - (a.percentage || 0))
    return rows.filter(r => (r.count || 0) > 0).slice(0, 10)
  }

  const getTypeBreakdown = () => {
    const td = profile?.summary?.type_distribution || {}
    const counts = {}
    Object.values(td).forEach((t) => {
      const k = String(t || 'unknown')
      counts[k] = (counts[k] || 0) + 1
    })
    return Object.entries(counts).sort((a, b) => b[1] - a[1])
  }

  const getOutlierTop = () => {
    const outs = Array.isArray(profile?.summary?.outliers) ? profile.summary.outliers : []
    const rows = outs.map((o) => ({
      column: o?.column,
      count: o?.count ?? 0,
    }))
    rows.sort((a, b) => (b.count || 0) - (a.count || 0))
    return rows.filter(r => (r.count || 0) > 0).slice(0, 10)
  }

  const handleExtractRules = async () => {
    setProcessing(true)
    try {
      const response = await extractRules(id, true)
      alert(`Successfully extracted ${response.data?.rules?.length || 0} rules!`)
      navigate(`/rules/${id}`)
    } catch (error) {
      alert('Failed to extract rules: ' + (error.response?.data?.detail || error.message))
    } finally {
      setProcessing(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  if (!dataset) {
    return (
      <div className="text-center py-12">
        <AlertCircle className="mx-auto h-12 w-12 text-gray-400" />
        <h3 className="mt-4 text-lg font-medium text-gray-900 dark:text-gray-100">Dataset not found</h3>
        <Link to="/" className="mt-4 text-blue-600 hover:text-blue-500">
          Back to Dashboard
        </Link>
      </div>
    )
  }

  return (
    <div>
      <div className="mb-6">
        <button
          onClick={() => navigate('/')}
          className="flex items-center text-gray-600 hover:text-gray-900 dark:text-gray-300 dark:hover:text-gray-100 mb-4"
        >
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back to Dashboard
        </button>
        <h2 className="text-3xl font-bold text-gray-900 dark:text-gray-100">{dataset.name}</h2>
        <div className="mt-2 flex items-center space-x-4 text-sm text-gray-600 dark:text-gray-300">
          <span className="capitalize">{dataset.modality}</span>
          <span>•</span>
          <span className="capitalize">{dataset.purpose.replace('_', ' ')}</span>
        </div>
      </div>

      {/* Suggested Actions */}
      {suggestions.length > 0 && (
        <div className="bg-blue-50 border border-blue-200 dark:bg-blue-900/25 dark:border-blue-800 rounded-lg p-4 mb-6">
          <h3 className="text-sm font-medium text-blue-900 mb-2">Suggested Next Steps:</h3>
          <ul className="list-disc list-inside text-sm text-blue-800 space-y-1">
            {suggestions.map((action, idx) => (
              <li key={idx}>{action.replace('_', ' ')}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Actions */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3 mb-8">
        {dataset.purpose === 'rule_extraction' && (
          <>
            <button
              onClick={handleProfile}
              disabled={processing}
              className="bg-white dark:bg-gray-900 border border-transparent dark:border-gray-800 rounded-lg shadow p-6 text-left hover:shadow-lg transition-shadow disabled:opacity-50"
            >
              <div className="flex items-center mb-2">
                <FileText className="h-6 w-6 text-blue-600 mr-2" />
                <h3 className="font-semibold text-gray-900 dark:text-gray-100">Profile Dataset</h3>
              </div>
              <p className="text-sm text-gray-600 dark:text-gray-300">Analyze dataset statistics and schema</p>
            </button>

            <button
              onClick={handleExtractRules}
              disabled={processing}
              className="bg-white dark:bg-gray-900 border border-transparent dark:border-gray-800 rounded-lg shadow p-6 text-left hover:shadow-lg transition-shadow disabled:opacity-50"
            >
              <div className="flex items-center mb-2">
                <Play className="h-6 w-6 text-purple-600 mr-2" />
                <h3 className="font-semibold text-gray-900 dark:text-gray-100">Extract Rules</h3>
              </div>
              <p className="text-sm text-gray-600 dark:text-gray-300">Extract cleaning rules from dataset</p>
            </button>
          </>
        )}

        {dataset.purpose === 'cleaning' && (
          <Link
            to={`/cleaning/${id}`}
          className="bg-white dark:bg-gray-900 border border-transparent dark:border-gray-800 rounded-lg shadow p-6 text-left hover:shadow-lg transition-shadow"
          >
            <div className="flex items-center mb-2">
              <CheckCircle className="h-6 w-6 text-green-600 mr-2" />
            <h3 className="font-semibold text-gray-900 dark:text-gray-100">Apply Rules</h3>
            </div>
          <p className="text-sm text-gray-600 dark:text-gray-300">Apply cleaning rules to dataset</p>
          </Link>
        )}
      </div>

      {/* Profile Results */}
      {profile && (
        <div className="bg-white dark:bg-gray-900 black:bg-gray-950 border border-transparent dark:border-gray-800 black:border-gray-900 rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">Profile Results</h3>
          {profile.sample_rows !== null && profile.sample_rows !== undefined && (
            <div className="mb-4 text-sm text-amber-800 bg-amber-50 border border-amber-200 rounded-lg p-3">
              Profile computed on a sample of <span className="font-semibold">{profile.profiled_rows?.toLocaleString?.() || profile.profiled_rows}</span> rows (requested sample_rows={profile.sample_rows}).
            </div>
          )}
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-5 mb-6">
            <div>
              <p className="text-sm text-gray-600">Total Rows</p>
              <p className="text-2xl font-bold text-gray-900">
                {profile.summary?.total_rows?.toLocaleString() || 'N/A'}
              </p>
            </div>
            <div>
              <p className="text-sm text-gray-600">Total Columns</p>
              <p className="text-2xl font-bold text-gray-900">
                {profile.summary?.total_columns || 'N/A'}
              </p>
            </div>
            <div>
              <p className="text-sm text-gray-600">Duplicate Rows</p>
              <p className="text-2xl font-bold text-gray-900">
                {profile.summary?.duplicate_rows?.toLocaleString() || '0'}
              </p>
            </div>
            <div>
              <p className="text-sm text-gray-600">Outliers Detected</p>
              <p className="text-2xl font-bold text-gray-900">
                {profile.summary?.outliers?.length || '0'}
              </p>
            </div>
            <div>
              <p className="text-sm text-gray-600">Potential Primary Keys</p>
              <p className="text-2xl font-bold text-gray-900">
                {Array.isArray(profile.summary?.potential_keys) ? profile.summary.potential_keys.length : '0'}
              </p>
            </div>
          </div>

          {/* EDA View Selector */}
          <div className="mb-4 flex flex-wrap gap-2">
            {[
              { key: 'missing', label: 'Missingness' },
              { key: 'types', label: 'Types' },
              { key: 'outliers', label: 'Outliers' },
              { key: 'columns', label: 'Columns' },
            ].map((t) => (
              <button
                key={t.key}
                onClick={() => setEdaView(t.key)}
                className={`px-4 py-2 rounded-lg text-sm font-semibold border transition-colors ${
                  edaView === t.key
                    ? 'bg-blue-600 text-white border-blue-600'
                    : 'bg-white dark:bg-gray-950 text-gray-700 dark:text-gray-200 border-gray-300 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800'
                }`}
              >
                {t.label}
              </button>
            ))}
          </div>

          {/* EDA Views */}
          {edaView === 'missing' && (
            <div className="bg-gray-50 dark:bg-gray-950/40 border border-gray-200 dark:border-gray-800 rounded-lg p-4">
              <h4 className="text-md font-semibold text-gray-900 dark:text-gray-100 mb-3">Missingness (Top 10)</h4>
              {getMissingTop().length === 0 ? (
                <div className="text-sm text-gray-600 dark:text-gray-300">No missing values detected in the profiled rows.</div>
              ) : (
                <>
                  <div className="h-72 mb-4 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-lg p-2">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={getMissingTop()} margin={{ top: 10, right: 10, left: 0, bottom: 10 }}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="column" tickFormatter={(v) => shortLabel(v, 12)} interval={0} height={50} />
                        <YAxis tickFormatter={(v) => `${v}%`} />
                        <Tooltip
                          formatter={(value, name) => {
                            if (name === 'percentage') return [`${value}%`, 'Missing %']
                            if (name === 'count') return [Number(value).toLocaleString(), 'Missing Count']
                            return [value, name]
                          }}
                          labelFormatter={(label) => `Column: ${label}`}
                        />
                        <Bar dataKey="percentage" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>

                  <div className="overflow-x-auto">
                    <table className="min-w-full divide-y divide-gray-200 text-sm">
                      <thead className="bg-white dark:bg-gray-900">
                        <tr>
                          <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Column</th>
                          <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Missing</th>
                          <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">%</th>
                        </tr>
                      </thead>
                      <tbody className="bg-gray-50 dark:bg-gray-950/40 divide-y divide-gray-200 dark:divide-gray-800">
                        {getMissingTop().map((r) => (
                          <tr key={r.column}>
                            <td className="px-3 py-2 text-gray-900 dark:text-gray-100 font-mono whitespace-nowrap">{r.column}</td>
                            <td className="px-3 py-2 text-gray-700 dark:text-gray-300 whitespace-nowrap">{Number(r.count).toLocaleString()}</td>
                            <td className="px-3 py-2 text-gray-700 dark:text-gray-300 whitespace-nowrap">{fmtPct(r.percentage)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </>
              )}
            </div>
          )}

          {edaView === 'types' && (
            <div className="bg-gray-50 dark:bg-gray-950/40 border border-gray-200 dark:border-gray-800 rounded-lg p-4">
              <h4 className="text-md font-semibold text-gray-900 dark:text-gray-100 mb-3">Column Types</h4>
              {getTypeBreakdown().length === 0 ? (
                <div className="text-sm text-gray-600 dark:text-gray-300">No type information available.</div>
              ) : (
                <>
                  <div className="h-72 mb-4 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-lg p-2">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart
                        data={getTypeBreakdown().map(([dtype, count]) => ({ dtype, count }))}
                        margin={{ top: 10, right: 10, left: 0, bottom: 10 }}
                      >
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="dtype" tickFormatter={(v) => shortLabel(v, 12)} interval={0} height={50} />
                        <YAxis allowDecimals={false} />
                        <Tooltip
                          formatter={(value) => [Number(value).toLocaleString(), 'Columns']}
                          labelFormatter={(label) => `dtype: ${label}`}
                        />
                        <Bar dataKey="count" fill="#10b981" radius={[4, 4, 0, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>

                  <div className="space-y-2 text-sm">
                    {getTypeBreakdown().map(([dtype, count]) => (
                      <div key={dtype} className="flex items-center justify-between bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-md px-3 py-2">
                        <span className="font-mono text-gray-800 dark:text-gray-200">{dtype}</span>
                        <span className="font-semibold text-gray-900 dark:text-gray-100">{count}</span>
                      </div>
                    ))}
                  </div>
                </>
              )}
            </div>
          )}

          {edaView === 'outliers' && (
            <div className="bg-gray-50 dark:bg-gray-950/40 border border-gray-200 dark:border-gray-800 rounded-lg p-4">
              <h4 className="text-md font-semibold text-gray-900 dark:text-gray-100 mb-3">Outliers (IQR)</h4>
              {Array.isArray(profile.summary?.outliers) && profile.summary.outliers.length > 0 ? (
                <>
                  {getOutlierTop().length > 0 && (
                    <div className="h-72 mb-4 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-lg p-2">
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={getOutlierTop()} margin={{ top: 10, right: 10, left: 0, bottom: 10 }}>
                          <CartesianGrid strokeDasharray="3 3" />
                          <XAxis dataKey="column" tickFormatter={(v) => shortLabel(v, 12)} interval={0} height={50} />
                          <YAxis allowDecimals={false} />
                          <Tooltip
                            formatter={(value) => [Number(value).toLocaleString(), 'Outliers']}
                            labelFormatter={(label) => `Column: ${label}`}
                          />
                          <Bar dataKey="count" fill="#f59e0b" radius={[4, 4, 0, 0]} />
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  )}

                  <div className="overflow-x-auto">
                    <table className="min-w-full divide-y divide-gray-200 text-sm">
                      <thead className="bg-gray-50">
                        <tr>
                          <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Column</th>
                          <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Count</th>
                          <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Lower</th>
                          <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Upper</th>
                        </tr>
                      </thead>
                      <tbody className="bg-white divide-y divide-gray-200">
                        {profile.summary.outliers.slice(0, 15).map((o, idx) => (
                          <tr key={`${o.column}-${idx}`}>
                            <td className="px-4 py-2 text-sm font-medium text-gray-900">{o.column}</td>
                            <td className="px-4 py-2 text-sm text-gray-600">{o.count}</td>
                            <td className="px-4 py-2 text-sm text-gray-600">{o.bounds?.lower}</td>
                            <td className="px-4 py-2 text-sm text-gray-600">{o.bounds?.upper}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  {profile.summary.outliers.length > 15 && (
                    <div className="mt-2 text-xs text-gray-500">Showing first 15 outlier columns.</div>
                  )}
                </>
              ) : (
                <div className="text-sm text-gray-600 dark:text-gray-300">No outliers detected by the IQR method.</div>
              )}
            </div>
          )}
          
          {/* Column Details */}
          {edaView === 'columns' && profile.columns && Object.keys(profile.columns).length > 0 && (
            <div className="mt-6">
              <h4 className="text-md font-semibold text-gray-900 mb-3">Column Statistics</h4>
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Column</th>
                      <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Type</th>
                      <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Missing %</th>
                      <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Unique Values</th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {Object.entries(profile.columns).map(([colName, colInfo]) => (
                      <tr key={colName}>
                        <td className="px-4 py-2 text-sm font-medium text-gray-900">{colName}</td>
                        <td className="px-4 py-2 text-sm text-gray-600">{colInfo.dtype}</td>
                        <td className="px-4 py-2 text-sm text-gray-600">{colInfo.missing_percentage?.toFixed(1) || 0}%</td>
                        <td className="px-4 py-2 text-sm text-gray-600">{colInfo.unique_count}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

