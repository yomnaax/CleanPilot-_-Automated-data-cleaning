import axios from 'axios'

const API_BASE = 'http://127.0.0.1:8000'

// Base client factory — injects token automatically
const createClient = (token = null) => {
  const instance = axios.create({
    baseURL: API_BASE,
    headers: { 'Content-Type': 'application/json' },
  })

  instance.interceptors.request.use((config) => {
    const t = token || localStorage.getItem('cp_token')
    if (t) config.headers.Authorization = `Bearer ${t}`
    return config
  })

  instance.interceptors.response.use(
    (res) => res,
    (err) => {
      if (err.response?.status === 401) {
        localStorage.removeItem('cp_token')
        window.location.href = '/login'
      }
      return Promise.reject(err)
    }
  )

  return instance
}

const client = createClient()

// ─── Auth ────────────────────────────────────────────────────────────────────
export const authAPI = {
  login: (email, password) =>
    axios.post(`${API_BASE}/auth/login`, { email, password }),

  register: (email, password, full_name) =>
    axios.post(`${API_BASE}/auth/register`, { email, password, full_name }),

  me: (token) =>
    axios.get(`${API_BASE}/auth/me`, {
      headers: { Authorization: `Bearer ${token}` },
    }),
}

// ─── Health ───────────────────────────────────────────────────────────────────
export const healthCheck = () => client.get('/health/live')

// ─── Datasets ─────────────────────────────────────────────────────────────────
export const uploadDataset = (formData) =>
  client.post('/ingest', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })

export const getDatasets = () => client.get('/ingest')
export const getDataset = (id) => client.get(`/ingest/${id}`)
export const deleteDataset = (id) => client.delete(`/ingest/${id}`)

// ─── Profiling ────────────────────────────────────────────────────────────────
export const profileDataset = (id) => client.post(`/profile/${id}`, {})

// ─── Rule Extraction ──────────────────────────────────────────────────────────
export const extractRules = (datasetId, includeRag = true, includeLlm = true) =>
  client.post('/extract', {
    dataset_id: datasetId,
    include_rag: includeRag,
    include_llm: includeLlm,
  })

// ─── Rules ────────────────────────────────────────────────────────────────────
export const getRules = (datasetId) =>
  client.get(`/rules?dataset_id=${datasetId}`)
export const updateRule = (ruleId, updates) =>
  client.patch(`/rules/${ruleId}`, updates)
export const approveRule = (ruleId) =>
  client.patch(`/rules/${ruleId}`, { approved: true })

// ─── Apply Rules ──────────────────────────────────────────────────────────────
export const applyRules = (
  datasetId,
  ruleIds,
  preview = true,
  referenceDatasetId = null,
  applyGeneralPreprocessing = false
) =>
  client.post(`/apply/${datasetId}`, {
    rule_ids: ruleIds,
    preview,
    reference_dataset_id: referenceDatasetId,
    apply_general_preprocessing: applyGeneralPreprocessing,
  })

export const downloadCleanedDataset = (datasetId, runId) =>
  client.get(`/apply/${datasetId}/download`, {
    params: { run_id: runId },
    responseType: 'blob',
  })

// ─── Validation ───────────────────────────────────────────────────────────────
export const validateDataset = (datasetId, ruleIds) =>
  client.post(`/validate/${datasetId}`, { rule_ids: ruleIds })

// ─── Feedback ────────────────────────────────────────────────────────────────
export const submitFeedback = (ruleId, decision, comment) =>
  client.post('/feedback', { rule_id: ruleId, decision, comment })

// ─── Runs ─────────────────────────────────────────────────────────────────────
export const getLatestRun = (datasetId, runType = 'rule_extraction') =>
  client.get('/runs/latest', {
    params: { dataset_id: datasetId, run_type: runType },
  })

// ─── Mapping ──────────────────────────────────────────────────────────────────
export const generateMappings = (datasetId, useLlm = true) =>
  client.post(`/mapping/${datasetId}`, null, { params: { use_llm: useLlm } })
export const getMappings = (datasetId) => client.get(`/mapping/${datasetId}`)
export const updateMapping = (datasetId, columnName, updates) =>
  client.patch(
    `/mapping/${datasetId}/${encodeURIComponent(columnName)}`,
    updates
  )

// ─── Rule Validation (LLM) ────────────────────────────────────────────────────
export const validateRuleWithLLM = (ruleId) =>
  client.post(`/rule-validation/${ruleId}`)
export const validateRulesBatch = (ruleIds) =>
  client.post('/rule-validation/batch', ruleIds)

// ─── Actions ──────────────────────────────────────────────────────────────────
export const getSuggestedActions = (datasetId) =>
  client.get(`/actions/${datasetId}`)

export default client
