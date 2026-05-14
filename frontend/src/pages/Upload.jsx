import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Upload as UploadIcon, FileText, AlertCircle } from 'lucide-react'
import { uploadDataset } from '../api/client'

export default function Upload() {
  const navigate = useNavigate()
  const [file, setFile] = useState(null)
  const [name, setName] = useState('')
  const [purpose, setPurpose] = useState('rule_extraction')
  const [modality, setModality] = useState('tabular')
  const [domain, setDomain] = useState('general')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0]
    if (selectedFile) {
      setFile(selectedFile)
      if (!name) {
        setName(selectedFile.name.replace(/\.[^/.]+$/, ''))
      }
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    
    if (!file) {
      setError('Please select a file')
      return
    }

    if (!name.trim()) {
      setError('Please enter a dataset name')
      return
    }

    setLoading(true)

    try {
      const formData = new FormData()
      formData.append('file', file)
      formData.append('name', name)
      formData.append('purpose', purpose)
      formData.append('modality', modality)
      formData.append('domain', domain)

      const response = await uploadDataset(formData)
      navigate(`/dataset/${response.data.id}`)
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to upload dataset')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-2xl mx-auto">
      <div className="mb-8">
        <h2 className="text-3xl font-bold text-gray-900 dark:text-gray-100">Upload Dataset</h2>
        <p className="mt-2 text-gray-600 dark:text-gray-300">Upload a dataset for rule extraction or cleaning</p>
      </div>

      <form onSubmit={handleSubmit} className="bg-white dark:bg-slate-950 black:bg-black border border-transparent dark:border-slate-800 black:border-gray-900 rounded-lg shadow p-6 space-y-6">
        {error && (
          <div className="bg-red-50 border border-red-200 dark:bg-red-900/30 dark:border-red-800 rounded-md p-4 flex items-start">
            <AlertCircle className="h-5 w-5 text-red-600 mt-0.5 mr-3" />
            <p className="text-sm text-red-800 dark:text-red-200">{error}</p>
          </div>
        )}

        {/* File Upload */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Dataset File
          </label>
          <div className="mt-1 flex justify-center px-6 pt-5 pb-6 border-2 border-gray-300 dark:border-slate-700 border-dashed rounded-md hover:border-blue-400 dark:hover:border-cyan-400 transition-colors">
            <div className="space-y-1 text-center">
              <UploadIcon className="mx-auto h-12 w-12 text-gray-400" />
              <div className="flex text-sm text-gray-600 dark:text-gray-300">
                <label className="relative cursor-pointer rounded-md font-medium text-blue-600 hover:text-blue-500">
                  <span>Upload a file</span>
                  <input
                    type="file"
                    className="sr-only"
                    onChange={handleFileChange}
                    accept=".csv,.json,.parquet,.xlsx,.xls"
                  />
                </label>
                <p className="pl-1">or drag and drop</p>
              </div>
              <p className="text-xs text-gray-500 dark:text-gray-400">CSV, JSON, Parquet, Excel</p>
              {file && (
                <p className="text-sm text-gray-900 dark:text-gray-100 mt-2">
                  <FileText className="inline h-4 w-4 mr-1" />
                  {file.name}
                </p>
              )}
            </div>
          </div>
        </div>

        {/* Dataset Name */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Dataset Name
          </label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 dark:border-slate-700 rounded-md shadow-sm bg-white dark:bg-slate-950 text-gray-900 dark:text-slate-100 focus:outline-none focus:ring-cyan-500 focus:border-cyan-500"
            placeholder="Enter dataset name"
            required
          />
        </div>

        {/* Purpose */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Purpose
          </label>
          <div className="space-y-2">
            <label className="flex items-center">
              <input
                type="radio"
                value="rule_extraction"
                checked={purpose === 'rule_extraction'}
                onChange={(e) => setPurpose(e.target.value)}
                className="mr-2"
              />
              <span className="text-gray-800 dark:text-gray-200">Rule Extraction - Extract cleaning rules from this dataset</span>
            </label>
            <label className="flex items-center">
              <input
                type="radio"
                value="cleaning"
                checked={purpose === 'cleaning'}
                onChange={(e) => setPurpose(e.target.value)}
                className="mr-2"
              />
              <span className="text-gray-800 dark:text-gray-200">Cleaning - Apply rules to clean this dataset</span>
            </label>
          </div>
        </div>

        {/* Modality */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Data Modality
          </label>
          <select
            value={modality}
            onChange={(e) => setModality(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 dark:border-slate-700 rounded-md shadow-sm bg-white dark:bg-slate-950 text-gray-900 dark:text-slate-100 focus:outline-none focus:ring-cyan-500 focus:border-cyan-500"
          >
            <option value="tabular">Tabular</option>
            <option value="text">Text</option>
            <option value="image">Image</option>
            <option value="audio">Audio</option>
          </select>
        </div>

        {/* Domain Selection */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Domain <span className="text-gray-500 text-xs">(Optional - improves accuracy)</span>
          </label>
          <select
            value={domain}
            onChange={(e) => setDomain(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 dark:border-slate-700 rounded-md shadow-sm bg-white dark:bg-slate-950 text-gray-900 dark:text-slate-100 focus:outline-none focus:ring-cyan-500 focus:border-cyan-500"
          >
            <option value="general">General (Works for any data)</option>
            <option value="finance">Finance (Transactions, accounts, merchant descriptions, payment narratives)</option>
            <option value="ecommerce">E-commerce (Products, orders, customers)</option>
            <option value="healthcare">Healthcare (Patient data, medical records)</option>
            <option value="hr">HR (Employees, salaries, performance, attrition)</option>
            <option value="retail">Retail (Inventory, sales, stores)</option>
            <option value="education">Education (Students, courses, grades)</option>
            <option value="logistics">Logistics (Shipments, delivery, supply chain)</option>
          </select>
          <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
            {domain === 'general' 
              ? 'General mode extracts all possible rules'
              : domain === 'finance'
              ? 'Finance mode focuses on transaction logs, merchant descriptions, account metadata, and payment narratives - fewer but more accurate rules'
              : `${domain.charAt(0).toUpperCase() + domain.slice(1)} mode focuses on domain-specific patterns - fewer but more accurate rules`}
          </p>
        </div>

        {/* Submit */}
        <div className="flex justify-end space-x-4">
          <button
            type="button"
            onClick={() => navigate('/')}
            className="px-4 py-2 border border-gray-300 dark:border-gray-700 rounded-md text-sm font-medium text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-800"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={loading}
            className="px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? 'Uploading...' : 'Upload Dataset'}
          </button>
        </div>
      </form>
    </div>
  )
}



