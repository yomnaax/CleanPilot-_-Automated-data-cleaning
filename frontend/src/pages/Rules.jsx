import { useEffect, useState } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { ArrowLeft, Check, X, MessageSquare, ThumbsUp, ThumbsDown, Sparkles, ChevronDown, ChevronRight } from 'lucide-react'
import { getRules, updateRule, submitFeedback, validateRuleWithLLM, getLatestRun, getMappings, generateMappings, updateMapping, extractRules } from '../api/client'

export default function Rules() {
  const { datasetId } = useParams()
  const navigate = useNavigate()
  const [rules, setRules] = useState([])
  const [loading, setLoading] = useState(true)
  const [skipReasonsByExtractor, setSkipReasonsByExtractor] = useState({})
  const [mappings, setMappings] = useState(null)
  const [mappingsLoading, setMappingsLoading] = useState(false)
  const [mappingsError, setMappingsError] = useState('')
  const [mappingExpanded, setMappingExpanded] = useState(true)
  const [mappingEditMode, setMappingEditMode] = useState(false)
  const [mappingDraft, setMappingDraft] = useState({})
  const [mappingDirty, setMappingDirty] = useState(false)
  const [rerunLoading, setRerunLoading] = useState(false)
  const [feedback, setFeedback] = useState({})
  const [validatingRules, setValidatingRules] = useState(new Set())
  const [expandedGroups, setExpandedGroups] = useState({
    semantic: true,
    regex: true,
    range: true,
    categorical: true,
    uniqueness: true,
    fd: true,
    anomaly: true,
    missing: true,
    other: true,
  })

  // Manual adjustment modal
  const [adjustOpen, setAdjustOpen] = useState(false)
  const [adjustRule, setAdjustRule] = useState(null)
  const [editPredicate, setEditPredicate] = useState('')
  const [editAction, setEditAction] = useState('')
  const [editMin, setEditMin] = useState('')
  const [editMax, setEditMax] = useState('')

  useEffect(() => {
    loadRules()
  }, [datasetId])

  const getSkipKeyForGroup = (groupKey) => {
    // Backend stores these in Run.summary.skip_reasons
    const map = {
      regex: 'regex',
      range: 'range',
      categorical: 'categorical',
      uniqueness: 'uniqueness',
      fd: 'fd',
      anomaly: 'anomaly',
      missing: 'missing_value', // UI group key differs from backend key
    }
    return map[groupKey] || null
  }

  const renderSkipReasons = (groupKey) => {
    const backendKey = getSkipKeyForGroup(groupKey)
    if (!backendKey) return null

    const rows = skipReasonsByExtractor?.[backendKey] || []
    if (!Array.isArray(rows) || rows.length === 0) return null

    return (
      <div className="bg-white rounded-lg border border-amber-200 p-4">
        <div className="flex items-center justify-between mb-3">
          <div className="text-sm font-semibold text-amber-900">
            Skipped columns / pairs ({rows.length})
          </div>
          <div className="text-xs text-amber-700">
            These were ignored by the extractor due to heuristics (e.g., too null, free text, not numeric, etc.)
          </div>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-amber-200 text-sm">
            <thead className="bg-amber-50">
              <tr>
                <th className="px-3 py-2 text-left font-semibold text-amber-900 whitespace-nowrap">Column / Pair</th>
                <th className="px-3 py-2 text-left font-semibold text-amber-900 whitespace-nowrap">Reason</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-amber-100">
              {rows.slice(0, 25).map((r, idx) => (
                <tr key={idx}>
                  <td className="px-3 py-2 text-gray-900 font-mono whitespace-nowrap">
                    {r?.column || r?.pair || r?.name || (r ? JSON.stringify(r) : '')}
                  </td>
                  <td className="px-3 py-2 text-gray-700 whitespace-nowrap">
                    {r?.reason || ''}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {rows.length > 25 && (
          <div className="mt-2 text-xs text-gray-600">
            Showing first 25 skipped entries. (Total: {rows.length})
          </div>
        )}
      </div>
    )
  }

  const loadMappings = async () => {
    setMappingsError('')
    setMappingsLoading(true)
    try {
      const resp = await getMappings(datasetId)
      const m = resp.data?.mappings || {}
      setMappings(m)
      setMappingDraft(Object.fromEntries(Object.entries(m).map(([k, v]) => [k, v?.canonical_concept || ''])))
    } catch (e) {
      // 404 means not generated yet — treat as normal state
      if (e?.response?.status === 404) {
        setMappings(null)
      } else {
        setMappingsError(e?.response?.data?.detail || e.message || 'Failed to load mappings')
        setMappings(null)
      }
    } finally {
      setMappingsLoading(false)
    }
  }

  const handleGenerateMappings = async () => {
    setMappingsError('')
    setMappingsLoading(true)
    try {
      const resp = await generateMappings(datasetId, true)
      const m = resp.data?.mappings || {}
      setMappings(m)
      setMappingDraft(Object.fromEntries(Object.entries(m).map(([k, v]) => [k, v?.canonical_concept || ''])))
      setMappingDirty(true)
    } catch (e) {
      setMappingsError(e?.response?.data?.detail || e.message || 'Failed to generate mappings')
    } finally {
      setMappingsLoading(false)
    }
  }

  const applyMappingBulkStatus = async (approved) => {
    if (!mappings) return
    setMappingsLoading(true)
    try {
      const entries = Object.entries(mappings)
      const updates = entries.map(([colName, m]) => {
        // If approving all, only approve mapped columns (concept exists)
        if (approved === true && !m?.canonical_concept) return Promise.resolve()
        return updateMapping(datasetId, colName, { approved })
      })
      await Promise.allSettled(updates)
      setMappingDirty(true)
      await loadMappings()
    } catch (e) {
      alert('Failed to update mappings: ' + (e?.response?.data?.detail || e.message))
    } finally {
      setMappingsLoading(false)
    }
  }

  const saveMappingDraft = async () => {
    if (!mappings) return
    setMappingsLoading(true)
    try {
      const updates = Object.entries(mappingDraft).map(([colName, concept]) =>
        updateMapping(datasetId, colName, { canonical_concept: concept?.trim() ? concept.trim() : null })
      )
      await Promise.allSettled(updates)
      setMappingEditMode(false)
      setMappingDirty(true)
      await loadMappings()
    } catch (e) {
      alert('Failed to save mapping adjustments: ' + (e?.response?.data?.detail || e.message))
    } finally {
      setMappingsLoading(false)
    }
  }

  const rerunExtractionForRag = async () => {
    setRerunLoading(true)
    try {
      await extractRules(datasetId, true, true)
      setMappingDirty(false)
      await loadRules()
    } catch (e) {
      alert('Failed to re-run extraction: ' + (e?.response?.data?.detail || e.message))
    } finally {
      setRerunLoading(false)
    }
  }

  const loadRules = async () => {
    try {
      const [rulesResp, runResp] = await Promise.allSettled([
        getRules(datasetId),
        getLatestRun(datasetId, 'rule_extraction'),
      ])

      if (rulesResp.status === 'fulfilled') {
        setRules(rulesResp.value.data || [])
      } else {
        throw rulesResp.reason
      }

      if (runResp.status === 'fulfilled') {
        const sr = runResp.value?.data?.summary?.skip_reasons || {}
        setSkipReasonsByExtractor(sr)
      } else {
        // Non-fatal: rules can still render without skip reasons
        setSkipReasonsByExtractor({})
      }

      // Load mappings (non-fatal)
      await loadMappings()
    } catch (error) {
      console.error('Failed to load rules:', error)
      alert('Failed to load rules: ' + (error.response?.data?.detail || error.message))
    } finally {
      setLoading(false)
    }
  }

  const handleApprove = async (ruleId) => {
    try {
      await updateRule(ruleId, { approved: true })
      loadRules()
    } catch (error) {
      alert('Failed to approve rule: ' + (error.response?.data?.detail || error.message))
    }
  }

  const openAdjust = (rule) => {
    setAdjustRule(rule)
    setEditPredicate(rule.predicate || '')
    setEditAction(rule.action || '')

    // If it's a range rule, prefill min/max
    const m1 = (rule.predicate || '').match(/range\([^,]+,\s*min\s*=\s*([\d.\-]+),\s*max\s*=\s*([\d.\-]+)\)/i)
    const m2 = (rule.predicate || '').match(/(\w+)\s*>=\s*([\d.\-]+)\s+AND\s+\1\s*<=\s*([\d.\-]+)/i)
    if (m1) {
      setEditMin(m1[1])
      setEditMax(m1[2])
    } else if (m2) {
      setEditMin(m2[2])
      setEditMax(m2[3])
    } else {
      setEditMin('')
      setEditMax('')
    }
    setAdjustOpen(true)
  }

  const saveAdjust = async (alsoApprove = false) => {
    if (!adjustRule) return
    let predicate = editPredicate
    let action = editAction

    // If user edited min/max and this looks like a range predicate, rewrite predicate/action
    if (editMin !== '' && editMax !== '') {
      const cols = adjustRule.targets?.columns || []
      const col = cols[0] || null
      if (col) {
        if ((adjustRule.predicate || '').includes('range(')) {
          predicate = `range(${col}, min=${editMin}, max=${editMax})`
        } else if ((adjustRule.predicate || '').includes('AND')) {
          predicate = `${col} >= ${editMin} AND ${col} <= ${editMax}`
        }
        if ((adjustRule.action || '').includes('enforce_range(')) {
          action = `enforce_range(${col}, ${editMin}, ${editMax})`
        }
      }
    }

    try {
      await updateRule(adjustRule.id, {
        predicate,
        action,
        targets: adjustRule.targets,
        ...(alsoApprove ? { approved: true } : {})
      })
      setAdjustOpen(false)
      setAdjustRule(null)
      loadRules()
    } catch (error) {
      alert('Failed to update rule: ' + (error.response?.data?.detail || error.message))
    }
  }

  const handleReject = async (ruleId) => {
    try {
      await updateRule(ruleId, { approved: false })
      loadRules()
    } catch (error) {
      alert('Failed to reject rule: ' + (error.response?.data?.detail || error.message))
    }
  }

  const handleResetRule = async (ruleId) => {
    try {
      await updateRule(ruleId, { approved: null })
      loadRules()
    } catch (error) {
      alert('Failed to reset rule: ' + (error.response?.data?.detail || error.message))
    }
  }

  // (adjust modal helpers are defined above)

  const handleFeedback = async (ruleId, decision) => {
    const comment = feedback[ruleId] || ''
    try {
      await submitFeedback(ruleId, decision, comment)
      setFeedback({ ...feedback, [ruleId]: '' })
      loadRules()
    } catch (error) {
      alert('Failed to submit feedback: ' + (error.response?.data?.detail || error.message))
    }
  }

  const handleValidateRule = async (ruleId) => {
    console.log('Validating rule:', ruleId)
    setValidatingRules(prev => new Set(prev).add(ruleId))
    try {
      console.log('Calling validateRuleWithLLM API...')
      // Add timeout for LLM calls (can take 10-30 seconds)
      const timeoutPromise = new Promise((_, reject) => 
        setTimeout(() => reject(new Error('Request timeout - LLM validation took too long')), 60000)
      )
      
      const response = await Promise.race([
        validateRuleWithLLM(ruleId),
        timeoutPromise
      ])
      
      console.log('LLM validation response:', response.data)
      
      if (response.data) {
        // Update the rule in local state immediately
        setRules(prevRules => 
          prevRules.map(rule => 
            rule.id === ruleId 
              ? {
                  ...rule,
                  llm_opinion: response.data.opinion,
                  llm_confidence: response.data.confidence,
                  llm_reasoning: response.data.reasoning,
                  llm_concerns: response.data.concerns || [],
                  llm_suggestions: response.data.suggestions || []
                }
              : rule
          )
        )
        console.log('Rule updated with LLM opinion')
      } else {
        console.warn('No data in response:', response)
        // Fallback: reload all rules anyway
        await loadRules()
      }
    } catch (error) {
      console.error('Validation error:', error)
      console.error('Error details:', error.response)
      
      // Handle different error types with user-friendly messages
      let errorMessage = 'Unknown error'
      let errorTitle = 'Validation Failed'
      
      if (error.response?.status === 429) {
        errorTitle = 'API Quota Exceeded'
        const detail = error.response?.data?.detail
        if (typeof detail === 'object' && detail.message) {
          errorMessage = detail.message
          if (detail.suggestions && detail.suggestions.length > 0) {
            errorMessage += '\n\nSuggestions:\n' + detail.suggestions.map((s, i) => `${i + 1}. ${s}`).join('\n')
          }
        } else {
          errorMessage = 'You\'ve exceeded your OpenAI API quota. Please check your billing or upgrade your plan.\n\nYou can still review and approve rules without LLM validation.'
        }
      } else if (error.response?.status === 401) {
        errorTitle = 'API Key Error'
        const detail = error.response?.data?.detail
        if (typeof detail === 'object' && detail.message) {
          errorMessage = detail.message
        } else {
          errorMessage = 'Your OpenAI API key is invalid or missing. Please check your .env file.'
        }
      } else {
        errorMessage = error.response?.data?.detail || error.message || 'Unknown error'
      }
      
      alert(`${errorTitle}\n\n${errorMessage}\n\nCheck browser console for details.`)
    } finally {
      setValidatingRules(prev => {
        const next = new Set(prev)
        next.delete(ruleId)
        return next
      })
    }
  }

  const getSourceBadge = (source) => {
    const colors = {
      extracted: 'bg-blue-100 text-blue-800',
      rag: 'bg-purple-100 text-purple-800',
      user: 'bg-green-100 text-green-800',
    }
    return (
      <span className={`px-2 py-1 rounded-full text-xs font-medium ${colors[source] || 'bg-gray-100 text-gray-800'}`}>
        {source}
      </span>
    )
  }

  const getSemanticSourceBadge = (rule) => {
    const src = (rule?.targets?.semantic_source || '').toLowerCase()
    if (src === 'llm') {
      return (
        <span className="px-2 py-1 rounded-full text-xs font-semibold bg-purple-100 text-purple-700 border border-purple-200">
          by LLM
        </span>
      )
    }
    if (src === 'rag') {
      return (
        <span className="px-2 py-1 rounded-full text-xs font-semibold bg-indigo-100 text-indigo-700 border border-indigo-200">
          by RAG
        </span>
      )
    }
    // Backward-compatible fallback for older stored rules
    if (rule?.targets?.llm_generated) {
      return (
        <span className="px-2 py-1 rounded-full text-xs font-semibold bg-purple-100 text-purple-700 border border-purple-200">
          by LLM
        </span>
      )
    }
    if ((rule?.source || '').toLowerCase() === 'rag') {
      return (
        <span className="px-2 py-1 rounded-full text-xs font-semibold bg-indigo-100 text-indigo-700 border border-indigo-200">
          by RAG
        </span>
      )
    }
    return null
  }

  const getRuleGroups = (allRules) => {
    const groups = {
      semantic: [],
      regex: [],
      range: [],
      categorical: [],
      uniqueness: [],
      fd: [],
      anomaly: [],
      missing: [],
      other: [],
    }

    allRules.forEach((rule) => {
      const ruleType = (rule.rule_type || '').toLowerCase()
      const predicate = rule.predicate || ''
      const tier = rule.targets?.tier
      const ragDomain = (rule.targets?.rag_domain || rule.targets?.domain || '').toLowerCase()
      const extractionGroup = rule.targets?.extraction_group
      const isRegexLike = ruleType.includes('regex') || String(predicate).includes('regex_match(')

      // Explicit group override from backend
      if (extractionGroup === 'semantic') {
        groups.semantic.push(rule)
        return
      }

      // Backwards-compatible semantic grouping:
      // - tier_3 finance pack
      // - tier_2 LLM semantic rules (but do NOT steal regex rules; keep them under Regex group)
      if (tier === 'tier_3' && ragDomain === 'finance') {
        groups.semantic.push(rule)
        return
      }
      if ((tier === 'tier_2' || rule.targets?.llm_generated) && !isRegexLike) {
        groups.semantic.push(rule)
        return
      }

      if (ruleType.includes('regex') || ruleType.includes('pattern')) {
        groups.regex.push(rule)
      } else if (ruleType.includes('range')) {
        groups.range.push(rule)
      } else if (ruleType.includes('unique') || predicate.includes('unique(')) {
        groups.uniqueness.push(rule)
      } else if (ruleType.includes('functional dependency') || predicate.includes('fd(')) {
        groups.fd.push(rule)
      } else if (ruleType.includes('anomaly') || predicate.includes('outlier_iqr(') || predicate.includes('rare_values(')) {
        groups.anomaly.push(rule)
      } else if (ruleType.includes('missing') || predicate.includes('is_null(')) {
        groups.missing.push(rule)
      } else if (ruleType.includes('categorical') || predicate.includes(' IN ')) {
        groups.categorical.push(rule)
      } else {
        groups.other.push(rule)
      }
    })

    return groups
  }

  const toggleGroup = (groupKey) => {
    setExpandedGroups((prev) => ({
      ...prev,
      [groupKey]: !prev[groupKey],
    }))
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
        <div className="flex items-center space-x-3">
          <h2 className="text-3xl font-bold text-gray-900 dark:text-gray-100">Extracted Rules</h2>
          <span className="px-2 py-1 rounded-full text-xs font-semibold bg-blue-100 text-blue-700 border border-blue-200">
            Grouped by extractor
          </span>
        </div>
        <p className="mt-2 text-gray-600 dark:text-gray-300">Review and approve rules for data cleaning</p>
      </div>

      {/* Canonical Mapping Panel */}
      <div className="bg-white dark:bg-slate-950 black:bg-black rounded-xl shadow-sm border border-gray-200 dark:border-slate-800 black:border-gray-900 overflow-hidden mb-8">
        <button
          onClick={() => setMappingExpanded((p) => !p)}
          className="w-full px-6 py-4 bg-gradient-to-r from-gray-50 to-gray-100/50 dark:from-slate-950 dark:to-slate-950 border-b border-gray-200 dark:border-slate-800 flex items-center justify-between hover:bg-gray-100 dark:hover:bg-slate-900 transition-colors"
        >
          <div className="flex items-center space-x-3">
            {mappingExpanded ? (
              <ChevronDown className="h-5 w-5 text-gray-600 dark:text-gray-300" />
            ) : (
              <ChevronRight className="h-5 w-5 text-gray-600 dark:text-gray-300" />
            )}
            <span className="text-lg font-bold text-gray-900 dark:text-gray-100">Canonical Mapping</span>
            {mappings && (
              <span className="px-2 py-1 rounded-full text-xs font-semibold bg-blue-100 text-blue-700 border border-blue-200">
                {Object.keys(mappings).length} column{Object.keys(mappings).length !== 1 ? 's' : ''}
              </span>
            )}
          </div>
          <span className="text-xs text-gray-500 uppercase tracking-wide">
            {mappingExpanded ? 'Hide' : 'Show'}
          </span>
        </button>

        {mappingExpanded && (
          <div className="p-6 bg-gray-50/30 dark:bg-slate-950/40 space-y-4">
            <div className="text-sm text-gray-700 dark:text-gray-300">
              RAG uses the current mapping. Use <span className="font-semibold">Reject All</span> to disable all mappings, or adjust concepts then re-run extraction to refresh RAG rules.
            </div>

            {mappingDirty && (
              <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 flex items-center justify-between">
                <div className="text-sm text-amber-900">
                  Mapping changed. Re-run extraction to refresh RAG rules.
                </div>
                <button
                  onClick={rerunExtractionForRag}
                  disabled={rerunLoading}
                  className="px-4 py-2 rounded-lg text-sm font-semibold bg-amber-600 text-white hover:bg-amber-700 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {rerunLoading ? 'Re-running...' : 'Re-run Extraction'}
                </button>
              </div>
            )}

            {mappingsLoading && (
              <div className="text-sm text-gray-600 dark:text-gray-300">Loading mappings...</div>
            )}

            {!mappingsLoading && mappingsError && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-sm text-red-800">
                {mappingsError}
              </div>
            )}

            {!mappingsLoading && !mappings && (
              <div className="bg-white dark:bg-slate-950 black:bg-black rounded-lg border border-gray-200 dark:border-slate-800 black:border-gray-900 p-4 flex items-center justify-between">
                <div className="text-sm text-gray-700 dark:text-gray-300">
                  No canonical mappings yet. Generate them to review/approve.
                </div>
                <button
                  onClick={handleGenerateMappings}
                  className="px-4 py-2 rounded-lg text-sm font-semibold bg-blue-600 text-white hover:bg-blue-700"
                >
                  Generate Mapping
                </button>
              </div>
            )}

            {!mappingsLoading && mappings && (
              <>
                <div className="flex flex-wrap items-center gap-2">
                  <button
                    onClick={() => applyMappingBulkStatus(true)}
                    disabled={mappingsLoading}
                    className="px-4 py-2 rounded-lg text-sm font-semibold bg-green-600 text-white hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    Approve All
                  </button>
                  <button
                    onClick={() => applyMappingBulkStatus(false)}
                    disabled={mappingsLoading}
                    className="px-4 py-2 rounded-lg text-sm font-semibold bg-white dark:bg-gray-900 border border-red-300 dark:border-red-800 text-red-700 dark:text-red-200 hover:bg-red-50 dark:hover:bg-red-900/30 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    Reject All
                  </button>
                  {!mappingEditMode ? (
                    <button
                      onClick={() => setMappingEditMode(true)}
                      disabled={mappingsLoading}
                      className="px-4 py-2 rounded-lg text-sm font-semibold bg-white dark:bg-gray-900 border border-blue-200 dark:border-blue-800 text-blue-700 dark:text-blue-200 hover:bg-blue-50 dark:hover:bg-blue-900/30 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      Adjust All
                    </button>
                  ) : (
                    <>
                      <button
                        onClick={saveMappingDraft}
                        disabled={mappingsLoading}
                        className="px-4 py-2 rounded-lg text-sm font-semibold bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        Save Adjustments
                      </button>
                      <button
                        onClick={() => { setMappingEditMode(false); setMappingDraft(Object.fromEntries(Object.entries(mappings).map(([k, v]) => [k, v?.canonical_concept || '']))) }}
                        className="px-4 py-2 rounded-lg text-sm font-semibold bg-white dark:bg-gray-900 border border-gray-300 dark:border-gray-700 text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-800"
                      >
                        Cancel
                      </button>
                    </>
                  )}
                </div>

                <div className="bg-white dark:bg-slate-950 black:bg-black rounded-lg border border-gray-200 dark:border-slate-800 black:border-gray-900 overflow-x-auto">
                  <table className="min-w-full divide-y divide-gray-200 text-sm">
                    <thead className="bg-gray-50 dark:bg-slate-950/60">
                      <tr>
                        <th className="px-3 py-2 text-left font-semibold text-gray-700 whitespace-nowrap">Dataset Column</th>
                        <th className="px-3 py-2 text-left font-semibold text-gray-700 whitespace-nowrap">Canonical Concept</th>
                        <th className="px-3 py-2 text-left font-semibold text-gray-700 whitespace-nowrap">Confidence</th>
                      </tr>
                    </thead>
                    <tbody className="bg-white dark:bg-slate-950 divide-y divide-gray-200 dark:divide-slate-800">
                      {Object.entries(mappings).map(([colName, m]) => (
                        <tr key={colName}>
                          <td className="px-3 py-2 font-mono text-gray-900 dark:text-gray-100 whitespace-nowrap">{colName}</td>
                          <td className="px-3 py-2 text-gray-900 whitespace-nowrap">
                            {mappingEditMode ? (
                              <input
                                value={mappingDraft[colName] ?? ''}
                                onChange={(e) => setMappingDraft((prev) => ({ ...prev, [colName]: e.target.value }))}
                                className="w-full min-w-[260px] px-3 py-2 border border-gray-300 dark:border-slate-700 rounded-md text-sm font-mono bg-white dark:bg-slate-950 text-gray-900 dark:text-slate-100 focus:outline-none focus:ring-cyan-500 focus:border-cyan-500"
                                placeholder="e.g. transaction_amount"
                              />
                            ) : m?.canonical_concept ? (
                              <span className="font-medium">{m.canonical_concept}</span>
                            ) : (
                              <span className="text-gray-500">Unmapped</span>
                            )}
                          </td>
                          <td className="px-3 py-2 text-gray-700 whitespace-nowrap">
                            {typeof m?.confidence === 'number' ? `${(m.confidence * 100).toFixed(0)}%` : '—'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </>
            )}
          </div>
        )}
      </div>

      {rules.length === 0 ? (
        <div className="bg-white dark:bg-slate-950 black:bg-black border border-transparent dark:border-slate-800 black:border-gray-900 rounded-lg shadow p-12 text-center">
          <p className="text-gray-600 dark:text-gray-300">No rules extracted yet. Extract rules from the dataset first.</p>
        </div>
      ) : (
        <div className="space-y-8">
          {Object.entries(getRuleGroups(rules)).map(([groupKey, groupRules]) => {
            const groupTitles = {
              semantic: 'Semantic Rules',
              regex: 'Regex Pattern Extractor',
              range: 'Range Constraint Extractor',
              categorical: 'Categorical Constraint Extractor',
              uniqueness: 'Uniqueness Constraint',
              fd: 'Functional Dependency (FD)',
              anomaly: 'Anomaly Rules',
              missing: 'Missing Value Rules',
              other: 'Other Rules',
            }

            const skipKey = getSkipKeyForGroup(groupKey)
            const skipCount = skipKey ? (skipReasonsByExtractor?.[skipKey]?.length || 0) : 0

            return (
              <div key={groupKey} className="bg-white dark:bg-slate-950 black:bg-black rounded-xl shadow-sm border border-gray-200 dark:border-slate-800 black:border-gray-900 overflow-hidden">
                <button
                  onClick={() => toggleGroup(groupKey)}
                  className="w-full px-6 py-4 bg-gradient-to-r from-gray-50 to-gray-100/50 dark:from-slate-950 dark:to-slate-950 border-b border-gray-200 dark:border-slate-800 flex items-center justify-between hover:bg-gray-100 dark:hover:bg-slate-900 transition-colors"
                >
                  <div className="flex items-center space-x-3">
                    {expandedGroups[groupKey] ? (
                      <ChevronDown className="h-5 w-5 text-gray-600 dark:text-gray-300" />
                    ) : (
                      <ChevronRight className="h-5 w-5 text-gray-600 dark:text-gray-300" />
                    )}
                    <span className="text-lg font-bold text-gray-900 dark:text-gray-100">
                      {groupTitles[groupKey]}
                    </span>
                    <span className="px-2 py-1 rounded-full text-xs font-semibold bg-blue-100 text-blue-700">
                      {groupRules.length} rule{groupRules.length !== 1 ? 's' : ''}
                    </span>
                    {skipCount > 0 && (
                      <span className="px-2 py-1 rounded-full text-xs font-semibold bg-amber-100 text-amber-800 border border-amber-200">
                        {skipCount} skipped
                      </span>
                    )}
                  </div>
                  <span className="text-xs text-gray-500 uppercase tracking-wide">
                    {expandedGroups[groupKey] ? 'Hide' : 'Show'}
                  </span>
                </button>

                {expandedGroups[groupKey] && (
                  <div className="space-y-6 p-6 bg-gray-50/30 dark:bg-slate-950/40">
                    {renderSkipReasons(groupKey)}
                    {groupRules.length === 0 ? (
                      <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 p-6 text-sm text-gray-600 dark:text-gray-300">
                        {skipCount > 0
                          ? 'No rules extracted for this extractor (see skipped columns/pairs above).'
                          : 'No rules extracted for this extractor yet.'}
                      </div>
                    ) : (
                      groupRules.map((rule) => (
                        <div 
                          key={rule.id} 
                          className={`bg-white rounded-xl shadow-sm border-2 transition-all hover:shadow-md ${
                            rule.approved === false ? 'border-red-200 bg-red-50/30' : 
                            rule.approved === true ? 'border-green-200 bg-green-50/30' : 
                            'border-gray-200 hover:border-blue-300'
                          }`}
                        >
              {/* Header Section */}
              <div className="px-6 py-4 bg-gradient-to-r from-gray-50 to-gray-100/50 border-b border-gray-200 rounded-t-xl">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-3">
                    <div className={`w-2 h-2 rounded-full ${
                      rule.approved === true ? 'bg-green-500' :
                      rule.approved === false ? 'bg-red-500' :
                      'bg-yellow-500 animate-pulse'
                    }`}></div>
                    <span className="text-xl font-bold text-gray-900">R{rule.id}</span>
                    {getSourceBadge(rule.source)}
                    {getSemanticSourceBadge(rule)}
                    {/* Show a small badge if the rule was generated by the LLM extractor */}
                    {rule.targets?.llm_generated && (
                      <span className="ml-1 px-2 py-1 rounded-full text-xs font-semibold bg-purple-100 text-purple-700 border border-purple-200">
                        Extracted by LLM
                      </span>
                    )}
                    {rule.approved === true && (
                      <span className="px-3 py-1 rounded-full text-xs font-semibold bg-green-100 text-green-700 border border-green-200">
                        ✓ Approved
                      </span>
                    )}
                    {rule.approved === false && (
                      <span className="px-3 py-1 rounded-full text-xs font-semibold bg-red-100 text-red-700 border border-red-200">
                        ✗ Rejected
                      </span>
                    )}
                    {(rule.approved === null || rule.approved === undefined) && (
                      <span className="px-3 py-1 rounded-full text-xs font-semibold bg-yellow-100 text-yellow-700 border border-yellow-200">
                        ⏳ Pending Review
                      </span>
                    )}
                  </div>
                  <div className="text-right">
                    <div className="text-xs text-gray-500 uppercase tracking-wide font-medium">Confidence</div>
                    <div className="text-lg font-bold text-gray-900">
                      {rule.confidence ? (rule.confidence * 100).toFixed(0) + '%' : 'N/A'}
                    </div>
                  </div>
                </div>
              </div>

              {/* Main Content */}
              <div className="p-6">
                {/* Rule Type Badge */}
                <div className="mb-5">
                  <span className="inline-flex items-center px-3 py-1.5 rounded-lg text-sm font-semibold bg-indigo-100 text-indigo-800 border border-indigo-200">
                    {rule.rule_type || 'Data Quality Rule'}
                  </span>
                </div>

                {/* User-Friendly Explanation - Prominent */}
                {rule.user_explanation && (
                  <div className="mb-6 p-5 bg-gradient-to-br from-blue-50 via-indigo-50 to-purple-50 rounded-lg border border-blue-200/50 shadow-sm">
                    <div className="flex items-start space-x-3">
                      <div className="flex-shrink-0 mt-0.5">
                        <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center">
                          <svg className="h-5 w-5 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                          </svg>
                        </div>
                      </div>
                      <div className="flex-1">
                        <h4 className="text-sm font-bold text-gray-900 mb-2">What This Rule Does</h4>
                        <p className="text-sm text-gray-700 leading-relaxed">{rule.user_explanation}</p>
                      </div>
                    </div>
                  </div>
                )}

                {/* Fallback Description */}
                {!rule.user_explanation && rule.explanation && (
                  <div className="mb-6 p-4 bg-gray-50 rounded-lg border border-gray-200">
                    <p className="text-sm text-gray-700 leading-relaxed">{rule.explanation}</p>
                  </div>
                )}

                {/* LLM Opinion Bar */}
                <div className="mb-6">
                  {rule.llm_opinion ? (
                    <div className={`p-4 rounded-lg border-2 ${
                      rule.llm_opinion === 'agree' ? 'bg-green-50 border-green-300' :
                      rule.llm_opinion === 'disagree' ? 'bg-red-50 border-red-300' :
                      'bg-yellow-50 border-yellow-300'
                    }`}>
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center space-x-2">
                          <Sparkles className={`h-5 w-5 ${
                            rule.llm_opinion === 'agree' ? 'text-green-600' :
                            rule.llm_opinion === 'disagree' ? 'text-red-600' :
                            'text-yellow-600'
                          }`} />
                          <span className="text-sm font-bold text-gray-900">
                            AI Opinion: {rule.llm_opinion === 'agree' ? '✓ Agrees' : 
                                        rule.llm_opinion === 'disagree' ? '✗ Disagrees' : 
                                        '? Uncertain'}
                          </span>
                          {rule.llm_confidence !== null && rule.llm_confidence !== undefined && (
                            <span className="text-xs text-gray-600">
                              ({Math.round(rule.llm_confidence * 100)}% confidence)
                            </span>
                          )}
                        </div>
                      </div>
                      {rule.llm_reasoning && (
                        <p className="text-sm text-gray-700 mb-2">{rule.llm_reasoning}</p>
                      )}
                      {rule.llm_concerns && rule.llm_concerns.length > 0 && (
                        <div className="mt-2">
                          <span className="text-xs font-semibold text-red-700">Concerns:</span>
                          <ul className="text-xs text-red-600 list-disc list-inside mt-1">
                            {rule.llm_concerns.map((concern, idx) => (
                              <li key={idx}>{concern}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                      {rule.llm_suggestions && rule.llm_suggestions.length > 0 && (
                        <div className="mt-2">
                          <span className="text-xs font-semibold text-blue-700">Suggestions:</span>
                          <ul className="text-xs text-blue-600 list-disc list-inside mt-1">
                            {rule.llm_suggestions.map((suggestion, idx) => (
                              <li key={idx}>{suggestion}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="p-3 bg-gray-50 rounded-lg border border-gray-200">
                      <button
                        onClick={() => handleValidateRule(rule.id)}
                        disabled={validatingRules.has(rule.id)}
                        className="flex items-center space-x-2 text-sm text-gray-700 hover:text-gray-900 transition-colors disabled:opacity-50"
                      >
                        <Sparkles className="h-4 w-4" />
                        <span>{validatingRules.has(rule.id) ? 'Validating...' : 'Get AI Opinion on This Rule'}</span>
                      </button>
                    </div>
                  )}
                </div>

                {/* Technical Details - Collapsible Style */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
                  {/* Left Column */}
                  <div className="space-y-4">
                    {rule.determinant_column && rule.determinant_column !== 'N/A' && (
                      <div className="p-3 bg-gray-50 rounded-lg border border-gray-200">
                        <div className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">Determinant</div>
                        <div className="text-sm font-mono text-gray-900 font-semibold">{rule.determinant_column}</div>
                      </div>
                    )}
                    {rule.dependent_column && rule.dependent_column !== 'N/A' && (
                      <div className="p-3 bg-gray-50 rounded-lg border border-gray-200">
                        <div className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">Dependent</div>
                        <div className="text-sm font-mono text-gray-900 font-semibold">{rule.dependent_column}</div>
                      </div>
                    )}
                    {rule.compliance_display && (
                      <div className="p-3 bg-emerald-50 rounded-lg border border-emerald-200">
                        <div className="text-xs font-semibold text-emerald-700 uppercase tracking-wide mb-1">Compliance</div>
                        <div className="text-sm font-bold text-emerald-900">{rule.compliance_display}</div>
                      </div>
                    )}
                  </div>

                  {/* Right Column */}
                  <div className="space-y-4">
                    {rule.extraction_algorithm && (
                      <div className="p-3 bg-gray-50 rounded-lg border border-gray-200">
                        <div className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">Extracted</div>
                        <div className="text-sm text-gray-700">
                          {rule.created_at ? new Date(rule.created_at).toLocaleDateString('en-US', { 
                            year: 'numeric', 
                            month: 'short', 
                            day: 'numeric' 
                          }) : 'N/A'}
                        </div>
                        <div className="text-xs text-gray-500 mt-1">{rule.extraction_algorithm}</div>
                      </div>
                    )}
                    {rule.suggested_action && (
                      <div className={`p-3 rounded-lg border ${
                        rule.approved === true ? 'bg-green-50 border-green-200' :
                        rule.approved === false ? 'bg-red-50 border-red-200' :
                        'bg-amber-50 border-amber-200'
                      }`}>
                        <div className="text-xs font-semibold uppercase tracking-wide mb-1" style={{
                          color: rule.approved === true ? '#065f46' : 
                                 rule.approved === false ? '#991b1b' : '#92400e'
                        }}>
                          Recommendation
                        </div>
                        <div className="text-sm font-medium" style={{
                          color: rule.approved === true ? '#047857' : 
                                 rule.approved === false ? '#dc2626' : '#d97706'
                        }}>
                          {rule.suggested_action}
                        </div>
                      </div>
                    )}
                  </div>
                </div>

                {/* Code Blocks for Predicate and Action */}
                <div className="space-y-3">
                  <div className="bg-slate-900 rounded-lg p-4 border border-slate-700">
                    <div className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-2">Predicate</div>
                    <code className="text-sm text-slate-100 font-mono block whitespace-pre-wrap break-words">
                      {rule.predicate}
                    </code>
                  </div>
                  {rule.action && (
                    <div className="bg-slate-800 rounded-lg p-4 border border-slate-700">
                      <div className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-2">Action</div>
                      <code className="text-sm text-slate-100 font-mono block whitespace-pre-wrap break-words">
                        {rule.action}
                      </code>
                    </div>
                  )}
                </div>
              </div>

              {/* Action Buttons */}
              <div className="px-6 py-4 bg-gray-50 border-t border-gray-200 rounded-b-xl">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-3">
                    <button
                      onClick={() => handleApprove(rule.id)}
                      disabled={rule.approved === true}
                      className={`flex items-center px-5 py-2.5 rounded-lg text-sm font-semibold transition-all ${
                        rule.approved === true
                          ? 'bg-green-100 text-green-600 cursor-not-allowed border border-green-200'
                          : 'bg-green-600 text-white hover:bg-green-700 hover:shadow-md border border-green-600'
                      }`}
                    >
                      <Check className="h-4 w-4 mr-2" />
                      {rule.approved === true ? 'Approved' : 'Approve Rule'}
                    </button>
                    <button
                      onClick={() => handleReject(rule.id)}
                      disabled={rule.approved === false}
                      className={`flex items-center px-5 py-2.5 rounded-lg text-sm font-semibold transition-all ${
                        rule.approved === false
                          ? 'bg-red-100 text-red-600 cursor-not-allowed border border-red-200'
                          : 'bg-white border-2 border-red-300 text-red-700 hover:bg-red-50 hover:border-red-400'
                      }`}
                    >
                      <X className="h-4 w-4 mr-2" />
                      {rule.approved === false ? 'Rejected' : 'Reject Rule'}
                    </button>

                    <button
                      onClick={() => openAdjust(rule)}
                      className="flex items-center px-5 py-2.5 rounded-lg text-sm font-semibold transition-all bg-white border-2 border-blue-200 text-blue-700 hover:bg-blue-50 hover:border-blue-300"
                    >
                      Adjust
                    </button>
                    {(rule.approved === true || rule.approved === false) && (
                      <button
                        onClick={() => handleResetRule(rule.id)}
                        className="flex items-center px-4 py-2.5 border-2 border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-100 hover:border-gray-400 transition-all"
                      >
                        Reset to Pending
                      </button>
                    )}
                  </div>
                  <div className="flex-1 max-w-md ml-4">
                    <textarea
                      value={feedback[rule.id] || ''}
                      onChange={(e) => setFeedback({ ...feedback, [rule.id]: e.target.value })}
                      placeholder="Add feedback or comments (optional)..."
                      className="w-full px-4 py-2 border-2 border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-none"
                      rows="2"
                    />
                    <div className="mt-2 flex space-x-2">
                      <button
                        onClick={() => handleFeedback(rule.id, 'approved')}
                        className="flex items-center px-3 py-1.5 text-xs font-medium text-green-700 hover:bg-green-50 rounded-lg border border-green-200 transition-all"
                      >
                        <ThumbsUp className="h-3 w-3 mr-1" />
                        Positive Feedback
                      </button>
                      <button
                        onClick={() => handleFeedback(rule.id, 'rejected')}
                        className="flex items-center px-3 py-1.5 text-xs font-medium text-red-700 hover:bg-red-50 rounded-lg border border-red-200 transition-all"
                      >
                        <ThumbsDown className="h-3 w-3 mr-1" />
                        Negative Feedback
                      </button>
                    </div>
                  </div>
                </div>
              </div>
                        </div>
                      ))
                    )}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}

      {/* Adjust Rule Modal */}
      {adjustOpen && adjustRule && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="w-full max-w-2xl bg-white rounded-xl shadow-xl border border-gray-200">
            <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
              <div>
                <div className="text-sm text-gray-500">Adjust rule</div>
                <div className="text-lg font-semibold text-gray-900">{adjustRule.explanation || `Rule #${adjustRule.id}`}</div>
              </div>
              <button
                onClick={() => { setAdjustOpen(false); setAdjustRule(null) }}
                className="px-3 py-1.5 rounded-lg border border-gray-300 text-gray-700 hover:bg-gray-50"
              >
                Close
              </button>
            </div>

            <div className="px-6 py-4 space-y-4">
              {(editMin !== '' || editMax !== '') && (
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-semibold text-gray-600 mb-1">Min</label>
                    <input
                      value={editMin}
                      onChange={(e) => setEditMin(e.target.value)}
                      className="w-full px-3 py-2 border-2 border-gray-300 rounded-lg text-sm"
                      placeholder="e.g. 0"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-gray-600 mb-1">Max</label>
                    <input
                      value={editMax}
                      onChange={(e) => setEditMax(e.target.value)}
                      className="w-full px-3 py-2 border-2 border-gray-300 rounded-lg text-sm"
                      placeholder="e.g. 120"
                    />
                  </div>
                  <div className="col-span-2 text-xs text-gray-500">
                    Tip: editing Min/Max will update the predicate/action when you click Save.
                  </div>
                </div>
              )}

              <div>
                <label className="block text-xs font-semibold text-gray-600 mb-1">Predicate</label>
                <textarea
                  value={editPredicate}
                  onChange={(e) => setEditPredicate(e.target.value)}
                  className="w-full px-3 py-2 border-2 border-gray-300 rounded-lg text-sm font-mono"
                  rows={3}
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-gray-600 mb-1">Action</label>
                <textarea
                  value={editAction}
                  onChange={(e) => setEditAction(e.target.value)}
                  className="w-full px-3 py-2 border-2 border-gray-300 rounded-lg text-sm font-mono"
                  rows={3}
                />
              </div>
            </div>

            <div className="px-6 py-4 border-t border-gray-200 flex items-center justify-end space-x-3 bg-gray-50 rounded-b-xl">
              <button
                onClick={() => saveAdjust(false)}
                className="px-5 py-2.5 rounded-lg text-sm font-semibold bg-white border-2 border-gray-300 text-gray-700 hover:bg-gray-100"
              >
                Save
              </button>
              <button
                onClick={() => saveAdjust(true)}
                className="px-5 py-2.5 rounded-lg text-sm font-semibold bg-blue-600 text-white hover:bg-blue-700"
              >
                Save & Approve
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  )
}



