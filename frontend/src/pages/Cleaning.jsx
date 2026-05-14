import { useEffect, useState } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { ArrowLeft, Play, Download, CheckCircle, Loader2 } from 'lucide-react'
import { getRules, applyRules, getDataset, getDatasets, downloadCleanedDataset } from '../api/client'

function MetricBar({ label, value, color, textColor }) {
  const pct = Math.min(100, Math.max(0, value * 100))
  return (
    <div>
      <div className="flex items-center justify-between mb-1">
        <span className="text-gray-400">{label}</span>
        <span className={`font-bold ${textColor}`}>{pct.toFixed(2)}%</span>
      </div>
      <div className="w-full bg-gray-700 rounded-full h-2">
        <div className={`${color} h-2 rounded-full transition-all`} style={{ width: `${pct.toFixed(1)}%` }} />
      </div>
    </div>
  )
}

export default function Cleaning() {
  const { datasetId } = useParams()
  const navigate = useNavigate()
  const [rules, setRules] = useState([])
  const [selectedRules, setSelectedRules] = useState([])
  const [loading, setLoading] = useState(true)
  const [processing, setProcessing] = useState(false)
  const [result, setResult] = useState(null)
  const [dataset, setDataset] = useState(null)
  const [datasets, setDatasets] = useState([])
  const [sourceDatasetId, setSourceDatasetId] = useState('')
  const [applyGeneralPreprocessing, setApplyGeneralPreprocessing] = useState(false)
  const [showRuleBasedOptions, setShowRuleBasedOptions] = useState(false)
  const [downloading, setDownloading] = useState(false)

  useEffect(() => {
    loadRuleSourceDatasets()
    loadDataset()
  }, [datasetId])

  const loadRuleSourceDatasets = async () => {
    try {
      const resp = await getDatasets()
      const all = resp.data || []
      setDatasets(all)
      // Force explicit choice (do NOT auto-select) so user decides which dataset's rules to apply.
      setSourceDatasetId('')
    } catch (error) {
      console.error('Failed to load datasets:', error)
    } finally {
      // do not setLoading here; loadRules depends on sourceDatasetId
      setLoading(false)
    }
  }

  const loadRulesForSource = async (srcId) => {
    if (!srcId) {
      setRules([])
      setSelectedRules([])
      return
    }
    try {
      const response = await getRules(srcId)
      const approvedRules = (response.data || []).filter(r => r.approved)
      setRules(approvedRules)
      setSelectedRules(approvedRules.map(r => r.id))
    } catch (error) {
      console.error('Failed to load rules:', error)
      setRules([])
      setSelectedRules([])
    }
  }

  const loadDataset = async () => {
    try {
      const response = await getDataset(datasetId)
      setDataset(response.data)
    } catch (error) {
      console.error('Failed to load dataset:', error)
    }
  }

  const handleApply = async (preview = true, useGeneralPreprocessing = null) => {
    // Allow passing general preprocessing state directly to avoid React async state timing issues
    const generalPreprocessing = useGeneralPreprocessing !== null ? useGeneralPreprocessing : applyGeneralPreprocessing

    if (!sourceDatasetId && !generalPreprocessing) {
      alert('Please choose which dataset rules you want to apply, or enable general preprocessing')
      return
    }
    if (selectedRules.length === 0 && !generalPreprocessing) {
      alert('Please select at least one rule, or enable general preprocessing')
      return
    }

    setProcessing(true)
    setResult(null)
    try {
      const ruleIdsToSend = generalPreprocessing && selectedRules.length === 0 ? [] : selectedRules
      const refDatasetId = sourceDatasetId && sourceDatasetId !== '' ? parseInt(sourceDatasetId) : null
      const response = await applyRules(datasetId, ruleIdsToSend, preview, refDatasetId, generalPreprocessing)
      if (response && response.data) {
        setResult(response.data)
        setTimeout(() => {
          document.querySelector('[data-results-section]')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
        }, 300)
      } else {
        alert('Received invalid response from server.')
      }
    } catch (error) {
      const errorMsg = error.response?.data?.detail || error.response?.data?.message || error.message
      alert('Failed to apply rules: ' + errorMsg)
    } finally {
      setProcessing(false)
    }
  }

  const handleDownload = async () => {
    if (!result?.run_id) return
    setDownloading(true)
    try {
      const response = await downloadCleanedDataset(datasetId, result.run_id)
      const blob = new Blob([response.data], { type: 'text/csv' })
      const suggestedName = `${dataset?.name?.replace(/\.csv$/i, '') || 'cleaned'}_cleaned.csv`

      if (window.showSaveFilePicker) {
        // Native Save As dialog
        const handle = await window.showSaveFilePicker({
          suggestedName,
          types: [{ description: 'CSV file', accept: { 'text/csv': ['.csv'] } }],
        })
        const writable = await handle.createWritable()
        await writable.write(blob)
        await writable.close()
      } else {
        // Fallback: trigger browser download
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = suggestedName
        document.body.appendChild(a)
        a.click()
        a.remove()
        URL.revokeObjectURL(url)
      }
    } catch (err) {
      if (err.name !== 'AbortError') {
        alert('Download failed: ' + (err.response?.data?.detail || err.message))
      }
    } finally {
      setDownloading(false)
    }
  }

  const toggleRule = (ruleId) => {
    setSelectedRules(prev =>
      prev.includes(ruleId)
        ? prev.filter(id => id !== ruleId)
        : [...prev, ruleId]
    )
  }

  useEffect(() => {
    // Load rules once a source dataset is chosen
    loadRulesForSource(sourceDatasetId)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sourceDatasetId])

  const renderSampleTable = (sample) => {
    if (!sample || !sample.columns || !sample.rows) return null
    const cols = sample.columns
    const rows = sample.rows
    return (
      <div className="overflow-x-auto border border-gray-200 rounded-lg">
        <table className="min-w-full divide-y divide-gray-200 text-sm">
          <thead className="bg-gray-50">
            <tr>
              {cols.map((c) => (
                <th key={c} className="px-3 py-2 text-left font-semibold text-gray-700 whitespace-nowrap">
                  {c}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {rows.map((r, idx) => (
              <tr key={idx}>
                {cols.map((c) => (
                  <td key={c} className="px-3 py-2 text-gray-700 whitespace-nowrap">
                    {r?.[c] === null || r?.[c] === undefined ? '' : String(r[c])}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
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
      <div className="mb-6">
        <button
          onClick={() => navigate(`/dataset/${datasetId}`)}
          className="flex items-center text-gray-600 hover:text-gray-900 dark:text-gray-300 dark:hover:text-gray-100 mb-4"
        >
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back to Dataset
        </button>
        <h2 className="text-3xl font-bold text-gray-900 dark:text-gray-100">Apply Cleaning Rules</h2>
        <p className="mt-2 text-gray-600 dark:text-gray-300">Select rules to apply to {dataset?.name}</p>
      </div>

      {/* Cleaning Options - Two separate buttons */}
      <div className="grid gap-6 md:grid-cols-2 mb-6">
        {/* General Preprocessing */}
        <div className="bg-white dark:bg-gray-900 black:bg-gray-950 border border-transparent dark:border-gray-800 black:border-gray-900 rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-3">
            General Preprocessing
          </h3>
          <p className="text-sm text-gray-600 dark:text-gray-300 mb-4">
            Automatically fix common data quality issues: null imputation (median/mode), whitespace trimming, duplicate removal, case standardization, and outlier clipping.
          </p>
          <div className="flex space-x-3">
            <button
              onClick={() => { setApplyGeneralPreprocessing(true); handleApply(true, true) }}
              disabled={processing}
              className="flex-1 flex items-center justify-center px-4 py-3 bg-blue-600 text-white rounded-md text-sm font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Play className="h-4 w-4 mr-2" />
              {processing ? 'Processing...' : 'Preview'}
            </button>
            <button
              onClick={() => { setApplyGeneralPreprocessing(true); handleApply(false, true) }}
              disabled={processing}
              className="flex-1 flex items-center justify-center px-4 py-3 bg-green-600 text-white rounded-md text-sm font-medium hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <CheckCircle className="h-4 w-4 mr-2" />
              {processing ? 'Processing...' : 'Apply General Preprocessing'}
            </button>
          </div>
        </div>

        {/* Rule Based Preprocessing */}
        <div className="bg-white dark:bg-gray-900 black:bg-gray-950 border border-transparent dark:border-gray-800 black:border-gray-900 rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-3">
            Rule Based Preprocessing
          </h3>
          <p className="text-sm text-gray-600 dark:text-gray-300 mb-4">
            Apply extracted rules from a reference dataset to clean data based on learned patterns and constraints.
          </p>
          <div className="flex space-x-3">
            {!showRuleBasedOptions ? (
              <button
                onClick={() => setShowRuleBasedOptions(true)}
                disabled={processing}
                className="w-full flex items-center justify-center px-4 py-3 bg-purple-600 text-white rounded-md text-sm font-medium hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Setup Rule Based Preprocessing
              </button>
            ) : (
              <>
                <button
                  onClick={() => handleApply(true)}
                  disabled={processing || !sourceDatasetId || selectedRules.length === 0}
                  className="flex-1 flex items-center justify-center px-4 py-3 bg-blue-600 text-white rounded-md text-sm font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <Play className="h-4 w-4 mr-2" />
                  {processing ? 'Processing...' : 'Preview'}
                </button>
                <button
                  onClick={() => handleApply(false)}
                  disabled={processing || !sourceDatasetId || selectedRules.length === 0}
                  className="flex-1 flex items-center justify-center px-4 py-3 bg-green-600 text-white rounded-md text-sm font-medium hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <CheckCircle className="h-4 w-4 mr-2" />
                  {processing ? 'Processing...' : 'Apply Rule Based Preprocessing'}
                </button>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Show rule-based options only when user clicks "Setup Rule Based Preprocessing" */}
      {showRuleBasedOptions && !sourceDatasetId ? (
        <div className="bg-white dark:bg-gray-900 black:bg-gray-950 border border-transparent dark:border-gray-800 black:border-gray-900 rounded-lg shadow p-6 mb-6">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2">Choose rules source dataset</h3>
          <p className="text-sm text-gray-600 dark:text-gray-300 mb-4">
            You must select which dataset&apos;s approved rules you want to apply to <span className="font-medium">{dataset?.name}</span>.
          </p>
          <select
            value={sourceDatasetId}
            onChange={(e) => setSourceDatasetId(e.target.value)}
            className="w-full md:w-auto border border-red-300 dark:border-red-800 rounded-md px-3 py-2 text-sm bg-white dark:bg-gray-950 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-red-200 dark:focus:ring-red-900/40"
          >
            <option value="">Select a dataset...</option>
            {datasets
              .filter(d => d.purpose === 'rule_extraction')
              .map((d) => (
                <option key={d.id} value={String(d.id)}>
                  {d.name} (#{d.id})
                </option>
              ))}
          </select>
          
          {/* Option to also apply general preprocessing */}
          <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-800">
            <label className="flex items-start p-3 border border-blue-200 dark:border-blue-800 rounded-md hover:bg-blue-50 dark:hover:bg-blue-900/20 cursor-pointer bg-blue-50/50 dark:bg-blue-900/10">
              <input
                type="checkbox"
                checked={applyGeneralPreprocessing}
                onChange={(e) => setApplyGeneralPreprocessing(e.target.checked)}
                className="mt-1 mr-3"
              />
              <div className="flex-1">
                <p className="font-medium text-gray-900 dark:text-gray-100">Also Apply General Preprocessing</p>
                <p className="text-sm text-gray-600 dark:text-gray-300 mt-1">
                  Apply general preprocessing (null imputation, whitespace trimming, duplicates, case standardization, outliers) before applying the selected rules.
                </p>
              </div>
            </label>
          </div>
          
          <div className="mt-3 text-xs text-gray-500 dark:text-gray-400">
            Tip: create/choose a dataset with purpose <span className="font-semibold">Rule Extraction</span>, approve rules on its Rules page, then come back here.
          </div>
          <button
            onClick={() => {
              setShowRuleBasedOptions(false)
              setSourceDatasetId('')
              setSelectedRules([])
              setRules([])
              setApplyGeneralPreprocessing(false)
            }}
            className="mt-3 text-sm text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100"
          >
            Cancel
          </button>
        </div>
      ) : showRuleBasedOptions && sourceDatasetId && rules.length === 0 ? (
        <div className="bg-white dark:bg-gray-900 black:bg-gray-950 border border-transparent dark:border-gray-800 black:border-gray-900 rounded-lg shadow p-12 text-center">
          <p className="text-gray-600 dark:text-gray-300 mb-4">No approved rules available.</p>
          <Link to={`/rules/${sourceDatasetId}`} className="text-blue-600 hover:text-blue-500">
            Go to Rules for the selected source dataset to approve some rules first
          </Link>
        </div>
      ) : showRuleBasedOptions && sourceDatasetId && rules.length > 0 ? (
        <>
          <div className="bg-white dark:bg-gray-900 black:bg-gray-950 border border-transparent dark:border-gray-800 black:border-gray-900 rounded-lg shadow p-6 mb-6">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2">Choose rules source dataset</h3>
            <p className="text-sm text-gray-600 dark:text-gray-300 mb-4">
              Select which dataset's approved rules you want to apply to <span className="font-medium">{dataset?.name}</span>.
            </p>
            <select
              value={sourceDatasetId}
              onChange={(e) => setSourceDatasetId(e.target.value)}
              className="w-full md:w-auto border border-gray-300 dark:border-gray-700 rounded-md px-3 py-2 text-sm bg-white dark:bg-gray-950 text-gray-900 dark:text-gray-100"
            >
              <option value="">Select a dataset...</option>
              {datasets
                .filter(d => d.purpose === 'rule_extraction')
                .map((d) => (
                  <option key={d.id} value={String(d.id)}>
                    {d.name} (#{d.id})
                  </option>
                ))}
            </select>
            {sourceDatasetId && (
              <div className="mt-3 text-xs text-gray-500 dark:text-gray-400">
                Using rules from dataset #{sourceDatasetId}.
              </div>
            )}
          </div>

          <div className="bg-white dark:bg-gray-900 black:bg-gray-950 border border-transparent dark:border-gray-800 black:border-gray-900 rounded-lg shadow p-6 mb-6">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
              Select Rules ({selectedRules.length} of {rules.length} selected)
            </h3>
            <div className="space-y-2 max-h-96 overflow-y-auto mb-4">
              {rules.map((rule) => (
                <label
                  key={rule.id}
                  className="flex items-start p-3 border border-gray-200 dark:border-gray-800 rounded-md hover:bg-gray-50 dark:hover:bg-gray-800 cursor-pointer"
                >
                  <input
                    type="checkbox"
                    checked={selectedRules.includes(rule.id)}
                    onChange={() => toggleRule(rule.id)}
                    className="mt-1 mr-3"
                  />
                  <div className="flex-1">
                    <p className="font-medium text-gray-900 dark:text-gray-100">{rule.explanation}</p>
                    <p className="text-sm text-gray-600 dark:text-gray-300 mt-1">{rule.predicate}</p>
                    <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">Confidence: {(rule.confidence * 100).toFixed(1)}%</p>
                  </div>
                </label>
              ))}
            </div>
          </div>
        </>
      ) : null}

      {/* Results section */}
      {result && (
        <div data-results-section className="mt-6 bg-white dark:bg-gray-900 rounded-lg shadow p-6 border-2 border-blue-200 dark:border-blue-800">

          {/* Header */}
          <h3 className="text-xl font-bold text-gray-900 dark:text-gray-100 flex items-center gap-2 mb-6">
            <span>📊</span>
            Cleaning Results
          </h3>

          {/* Stats row */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-6">
            <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4 text-center">
              <p className="text-2xl font-bold text-blue-600 dark:text-blue-400">
                {result.summary?.rules_applied || 0}
              </p>
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">Rules Applied</p>
            </div>
            <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4 text-center">
              <p className="text-2xl font-bold text-purple-600 dark:text-purple-400">
                {result.summary?.total_changes || 0}
              </p>
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">Total Changes</p>
            </div>
            <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4 text-center">
              <p className="text-2xl font-bold text-orange-600 dark:text-orange-400">
                {result.summary?.rows_affected || 0}
              </p>
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">Rows Affected</p>
            </div>
            <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4 text-center">
              {result.summary?.accuracy_metrics?.overall_accuracy != null ? (
                <>
                  <p className="text-2xl font-bold text-green-600 dark:text-green-400">
                    {(result.summary.accuracy_metrics.overall_accuracy * 100).toFixed(1)}%
                  </p>
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">Overall Accuracy</p>
                </>
              ) : (
                <>
                  <p className="text-2xl font-bold text-gray-400">—</p>
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">Overall Accuracy</p>
                </>
              )}
            </div>
          </div>

          {/* General Preprocessing Stats */}
          {result.summary?.general_preprocessing && (
            <div className="mb-6 p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
              <h4 className="font-semibold text-gray-900 dark:text-gray-100 mb-3">General Preprocessing</h4>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 text-sm">
                <div>
                  <span className="text-gray-500 dark:text-gray-400">Nulls Imputed</span>
                  <p className="font-semibold text-gray-900 dark:text-gray-100">{result.summary.general_preprocessing.nulls_imputed || 0}</p>
                </div>
                <div>
                  <span className="text-gray-500 dark:text-gray-400">Whitespace Trimmed</span>
                  <p className="font-semibold text-gray-900 dark:text-gray-100">{result.summary.general_preprocessing.whitespace_trimmed || 0}</p>
                </div>
                <div>
                  <span className="text-gray-500 dark:text-gray-400">Duplicates Removed</span>
                  <p className="font-semibold text-gray-900 dark:text-gray-100">{result.summary.general_preprocessing.duplicates_removed || 0}</p>
                </div>
                <div>
                  <span className="text-gray-500 dark:text-gray-400">Case Standardized</span>
                  <p className="font-semibold text-gray-900 dark:text-gray-100">{result.summary.general_preprocessing.case_standardized || 0}</p>
                </div>
                <div>
                  <span className="text-gray-500 dark:text-gray-400">Outliers Clipped</span>
                  <p className="font-semibold text-gray-900 dark:text-gray-100">{result.summary.general_preprocessing.outliers_clipped || 0}</p>
                </div>
                <div>
                  <span className="text-gray-500 dark:text-gray-400">Rows</span>
                  <p className="font-semibold text-gray-900 dark:text-gray-100">
                    {result.summary.general_preprocessing.rows_before || 0} → {result.summary.general_preprocessing.rows_after || 0}
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Accuracy Metrics */}
          {result.summary?.accuracy_metrics && (
            <div className="mb-6 p-4 bg-green-900/10 rounded-lg border border-green-800/40">
              <h4 className="font-semibold text-gray-100 mb-4 text-sm uppercase tracking-wide">
                Accuracy &amp; Quality Metrics
              </h4>
              {(() => {
                const am = result.summary.accuracy_metrics
                return (
                  <div className="space-y-3 text-sm">
                    {am.overall_accuracy != null && (
                      <MetricBar label="Overall Data Quality Score" value={am.overall_accuracy} color="bg-green-500" textColor="text-green-400" />
                    )}
                    {am.completeness_after != null && (
                      <MetricBar label="Completeness After Cleaning" value={am.completeness_after} color="bg-blue-500" textColor="text-blue-400" />
                    )}
                    {am.null_reduction_rate != null && (
                      <MetricBar label="Null Reduction Rate" value={am.null_reduction_rate} color="bg-purple-500" textColor="text-purple-400" />
                    )}
                    {am.row_retention_rate != null && (
                      <MetricBar label="Row Retention Rate" value={am.row_retention_rate} color="bg-cyan-500" textColor="text-cyan-400" />
                    )}
                    {am.duplicate_reduction_rate != null && (
                      <MetricBar label="Duplicate Reduction" value={am.duplicate_reduction_rate} color="bg-amber-500" textColor="text-amber-400" />
                    )}
                    {am.change_rate != null && (
                      <div className="flex items-center justify-between pt-1">
                        <span className="text-gray-400">Cells Modified</span>
                        <span className="text-gray-300 font-medium">
                          {am.cells_changed != null ? `${am.cells_changed.toLocaleString()} cells` : ''}{' '}
                          <span className="text-gray-500 text-xs">({(am.change_rate * 100).toFixed(2)}%)</span>
                        </span>
                      </div>
                    )}
                    {am.completeness_before != null && am.completeness_after != null && (
                      <div className="flex items-center justify-between pt-1 border-t border-gray-700 mt-2">
                        <span className="text-gray-400">Completeness</span>
                        <span className="text-gray-300">
                          <span className="text-red-400">{(am.completeness_before * 100).toFixed(1)}%</span>
                          <span className="text-gray-500 mx-2">→</span>
                          <span className="text-green-400">{(am.completeness_after * 100).toFixed(1)}%</span>
                        </span>
                      </div>
                    )}
                  </div>
                )
              })()}
            </div>
          )}

          {/* Before & After Comparison */}
          {result.before_sample && result.after_sample ? (
            <div className="mt-4">
              <h4 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">Before & After Comparison</h4>
              <div className="grid gap-6 md:grid-cols-2">
                <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4">
                  <h5 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">Before Cleaning (sample)</h5>
                  {renderSampleTable(result.before_sample)}
                </div>
                <div className="bg-green-50 dark:bg-green-900/20 rounded-lg p-4">
                  <h5 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">After Cleaning (sample)</h5>
                  {renderSampleTable(result.after_sample)}
                </div>
              </div>
            </div>
          ) : (
            <div className="mt-4 p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
              <p className="text-sm text-gray-600 dark:text-gray-400">
                Before/after samples not available.
              </p>
            </div>
          )}

          {/* Bottom save button */}
          {result.output_path && (
            <div className="mt-6 pt-6 border-t border-gray-200 dark:border-gray-700 flex justify-end">
              <button
                onClick={handleDownload}
                disabled={downloading}
                className="flex items-center gap-2 px-6 py-3 bg-green-600 hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed text-white font-medium rounded-lg transition-colors"
              >
                {downloading ? <Loader2 className="h-5 w-5 animate-spin" /> : <Download className="h-5 w-5" />}
                {downloading ? 'Downloading…' : 'Download Cleaned Dataset (.csv)'}
              </button>
            </div>
          )}

        </div>
      )}
    </div>
  )
}
