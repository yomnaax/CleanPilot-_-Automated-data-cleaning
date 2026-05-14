import { useEffect, useState } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { ArrowLeft, Play, Download, CheckCircle } from 'lucide-react'
import { getRules, applyRules, getDataset, getDatasets } from '../api/client'

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

  const handleApply = async (preview = true) => {
    if (!sourceDatasetId && !applyGeneralPreprocessing) {
      alert('Please choose which dataset rules you want to apply, or enable general preprocessing')
      return
    }
    if (selectedRules.length === 0 && !applyGeneralPreprocessing) {
      alert('Please select at least one rule, or enable general preprocessing')
      return
    }

    setProcessing(true)
    setResult(null) // Clear previous results
    try {
      // Pass empty array if no rules selected, but preprocessing is enabled
      const ruleIdsToSend = applyGeneralPreprocessing && selectedRules.length === 0 ? [] : selectedRules
      // Convert empty string to null for reference_dataset_id
      const refDatasetId = sourceDatasetId && sourceDatasetId !== '' ? parseInt(sourceDatasetId) : null
      
      console.log('Sending apply request:', {
        datasetId,
        ruleIdsToSend,
        preview,
        refDatasetId,
        applyGeneralPreprocessing
      })
      
      const response = await applyRules(datasetId, ruleIdsToSend, preview, refDatasetId, applyGeneralPreprocessing)
      
      console.log('Full response:', response)
      console.log('Response data:', response.data)
      console.log('Before sample:', response.data?.before_sample)
      console.log('After sample:', response.data?.after_sample)
      console.log('Summary:', response.data?.summary)
      console.log('Accuracy metrics:', response.data?.summary?.accuracy_metrics)
      
      if (response && response.data) {
      setResult(response.data)
        console.log('Result state set:', response.data)
        
        // Scroll to results after setting them
        setTimeout(() => {
          const resultsElement = document.querySelector('[data-results-section]')
          if (resultsElement) {
            resultsElement.scrollIntoView({ behavior: 'smooth', block: 'start' })
          } else {
            console.warn('Results element not found')
          }
        }, 500)
      } else {
        console.error('Invalid response structure:', response)
        alert('Received invalid response from server. Check console for details.')
      }
    } catch (error) {
      console.error('Apply error:', error)
      console.error('Error details:', {
        message: error.message,
        response: error.response,
        data: error.response?.data
      })
      const errorMsg = error.response?.data?.detail || error.response?.data?.message || error.message || JSON.stringify(error.response?.data || error)
      alert('Failed to apply rules: ' + errorMsg)
    } finally {
      setProcessing(false)
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
              onClick={() => {
                setApplyGeneralPreprocessing(true)
                handleApply(true)
              }}
              disabled={processing}
              className="flex-1 flex items-center justify-center px-4 py-3 bg-blue-600 text-white rounded-md text-sm font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Play className="h-4 w-4 mr-2" />
              {processing ? 'Processing...' : 'Preview'}
            </button>
            <button
              onClick={() => {
                setApplyGeneralPreprocessing(true)
                handleApply(false)
              }}
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

      {/* Results section - Always visible when result exists, regardless of source dataset */}
      {result ? (
            <div data-results-section className="mt-6 bg-white dark:bg-gray-900 rounded-lg shadow p-6 border-2 border-blue-200 dark:border-blue-800">
              <h3 className="text-xl font-bold text-gray-900 dark:text-gray-100 mb-4 flex items-center">
                <span className="mr-2">📊</span>
                Cleaning Results
              </h3>
              {/* Debug info */}
              <div className="mb-4 p-2 bg-gray-100 dark:bg-gray-800 rounded text-xs">
                <strong>Debug:</strong> Result received. Has summary: {result.summary ? 'Yes' : 'No'}, 
                Has before_sample: {result.before_sample ? 'Yes' : 'No'}, 
                Has after_sample: {result.after_sample ? 'Yes' : 'No'}
          </div>
              <div className="space-y-2 text-sm">
                {result.summary?.general_preprocessing && (
                  <div className="mb-4 p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
                    <h4 className="font-semibold text-gray-900 dark:text-gray-100 mb-2">General Preprocessing</h4>
                    <div className="space-y-1 text-sm">
                      <p><span className="font-medium">Nulls Imputed:</span> {result.summary.general_preprocessing.nulls_imputed || 0}</p>
                      <p><span className="font-medium">Whitespace Trimmed:</span> {result.summary.general_preprocessing.whitespace_trimmed || 0}</p>
                      <p><span className="font-medium">Duplicates Removed:</span> {result.summary.general_preprocessing.duplicates_removed || 0}</p>
                      <p><span className="font-medium">Case Standardized:</span> {result.summary.general_preprocessing.case_standardized || 0}</p>
                      <p><span className="font-medium">Outliers Clipped:</span> {result.summary.general_preprocessing.outliers_clipped || 0}</p>
                      <p><span className="font-medium">Rows:</span> {result.summary.general_preprocessing.rows_before || 0} → {result.summary.general_preprocessing.rows_after || 0}</p>
                    </div>
                  </div>
                )}
                <p><span className="font-medium">Rules Applied:</span> {result.summary?.rules_applied || 0}</p>
                <p><span className="font-medium">Total Changes:</span> {result.summary?.total_changes || 0}</p>
                <p><span className="font-medium">Rows Affected:</span> {result.summary?.rows_affected || 0}</p>
                {result.preview_path && (
                  <p className="text-blue-600">
                    Preview available at: {result.preview_path}
                  </p>
                )}
                {result.output_path && (
                  <p className="text-green-600">
                    Output saved to: {result.output_path}
                  </p>
                )}
              </div>

              {result.summary?.accuracy_metrics && (
                <div className="mt-6 p-4 bg-green-50 dark:bg-green-900/20 rounded-lg border border-green-200 dark:border-green-800">
                  <h4 className="text-md font-semibold text-gray-900 dark:text-gray-100 mb-3">Accuracy Metrics</h4>
                  <div className="space-y-3 text-sm">
                    {result.summary.accuracy_metrics.overall_accuracy !== null && result.summary.accuracy_metrics.overall_accuracy !== undefined && (
                      <div className="flex items-center justify-between">
                        <span className="font-medium text-gray-700 dark:text-gray-300">Overall Accuracy:</span>
                        <span className="text-lg font-bold text-green-600 dark:text-green-400">
                          {(result.summary.accuracy_metrics.overall_accuracy * 100).toFixed(2)}%
                        </span>
                      </div>
                    )}
                    
                    {result.summary.accuracy_metrics.rule_compliance && (
                      <div className="flex items-center justify-between">
                        <span className="font-medium text-gray-700 dark:text-gray-300">Rule Compliance:</span>
                        <span className="text-lg font-bold text-blue-600 dark:text-blue-400">
                          {(result.summary.accuracy_metrics.rule_compliance.compliance_rate * 100).toFixed(2)}%
                        </span>
                      </div>
                    )}
                    
                    {result.summary.accuracy_metrics.row_coverage !== undefined && (
                      <div className="flex items-center justify-between">
                        <span className="font-medium text-gray-700 dark:text-gray-300">Row Coverage:</span>
                        <span className="text-gray-600 dark:text-gray-400">
                          {(result.summary.accuracy_metrics.row_coverage * 100).toFixed(2)}%
                          {result.summary.accuracy_metrics.matching_rows !== undefined && (
                            <span className="ml-2 text-xs text-gray-500">
                              ({result.summary.accuracy_metrics.matching_rows} / {result.summary.accuracy_metrics.reference_rows} rows)
                            </span>
                          )}
                        </span>
                      </div>
                    )}
                    
                    {result.summary.accuracy_metrics.column_accuracy && Object.keys(result.summary.accuracy_metrics.column_accuracy).length > 0 && (
                      <div className="mt-4">
                        <p className="font-medium text-gray-700 dark:text-gray-300 mb-2">Column Accuracy:</p>
                        <div className="space-y-1 max-h-40 overflow-y-auto">
                          {Object.entries(result.summary.accuracy_metrics.column_accuracy).map(([col, acc]) => (
                            <div key={col} className="flex items-center justify-between text-xs">
                              <span className="text-gray-600 dark:text-gray-400 truncate max-w-[200px]">{col}:</span>
                              <span className="ml-2 font-medium text-gray-700 dark:text-gray-300">
                                {(acc.accuracy * 100).toFixed(1)}%
                              </span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                    
                    {result.summary.accuracy_metrics.note && (
                      <p className="text-xs text-gray-500 dark:text-gray-400 italic mt-2">
                        {result.summary.accuracy_metrics.note}
                      </p>
                    )}
                    
                    {result.summary.accuracy_metrics.error && (
                      <p className="text-xs text-red-600 dark:text-red-400 mt-2">
                        Error: {result.summary.accuracy_metrics.error}
                      </p>
                    )}
                  </div>
                </div>
              )}

              {/* Always show before/after if they exist */}
              {result.before_sample && result.after_sample ? (
                <div className="mt-6">
                  <h4 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">Before & After Comparison</h4>
                  <div className="grid gap-6 md:grid-cols-2">
                    <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4">
                      <h5 className="text-md font-semibold text-gray-900 dark:text-gray-100 mb-3">Before Cleaning (sample)</h5>
                      {renderSampleTable(result.before_sample)}
                    </div>
                    <div className="bg-green-50 dark:bg-green-900/20 rounded-lg p-4">
                      <h5 className="text-md font-semibold text-gray-900 dark:text-gray-100 mb-3">After Cleaning (sample)</h5>
                    {renderSampleTable(result.after_sample)}
                    </div>
                  </div>
                </div>
              ) : (
                <div className="mt-4 p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
                  <p className="text-sm text-gray-600 dark:text-gray-400">
                    Before/after samples not available. Check console for details.
                  </p>
                </div>
              )}
              
              {!result.summary?.accuracy_metrics && sourceDatasetId && (
                <div className="mt-4 p-3 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg">
                  <p className="text-sm text-yellow-800 dark:text-yellow-200">
                    <span className="font-medium">Note:</span> Accuracy metrics are only calculated when a reference dataset is provided. 
                    To see accuracy, make sure you're applying rules from a reference dataset that was used for rule extraction.
                  </p>
                </div>
              )}
            </div>
          ) : null}
    </div>
  )
}










