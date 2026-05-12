import { useEffect, useMemo, useState } from 'react'
import { Routes, Route, useNavigate } from 'react-router-dom'
import './App.css'

const API_BASE = (import.meta.env.VITE_API_BASE || '/api').replace(/\/$/, '')

const selectOptions = {
  Service_Fluid: ['Oxygen', 'Steam', 'Water', 'Oil', 'Gas'],
  Valve_Type: ['Needle', 'Control', 'Gate', 'Globe', 'Ball', 'Check'],
  Body_Material_Grade: ['Bronze', 'SS316', 'CS', 'SS304', 'Alloy'],
  Actuator_Type: ['Gearbox', 'Pneumatic', 'Electric', 'Hydraulic'],
  End_Connection: ['Flanged', 'Threaded', 'Butt Weld', 'Socket Weld'],
  Seat_Type: ['Metal', 'Soft', 'PTFE'],
  Pressure_Class_ASME: [150, 300, 600, 900, 1500, 2500]
}

const initialForm = {
  Service_Fluid: 'Oxygen',
  Valve_Type: 'Needle',
  Body_Material_Grade: 'Bronze',
  Actuator_Type: 'Gearbox',
  End_Connection: 'Flanged',
  Seat_Type: 'Metal',
  Pressure_Class_ASME: 2500,
  NPS_inch: 600,
  Operating_Pressure_bar: 98,
  Operating_Temperature_C: 2000,
  DeltaP_bar: 100,
  Cv: 150
}

function App() {
  return (
    <Routes>
      <Route path="/" element={<Dashboard />} />
      <Route path="/create" element={<CreateValve />} />
    </Routes>
  )
}

function Dashboard() {
  const navigate = useNavigate()
  const [list, setList] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [selectedId, setSelectedId] = useState('')
  const [detail, setDetail] = useState(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const [detailError, setDetailError] = useState('')

  const fetchList = async () => {
    try {
      setLoading(true)
      setError('')
      const res = await fetch(`${API_BASE}/predictions`)
      if (!res.ok) throw new Error('Unable to fetch predictions')
      const data = await res.json()
      setList(Array.isArray(data) ? data : [])
    } catch (err) {
      setError(err.message || 'Failed to load list')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchList()
  }, [])

  const openDetail = async (valveId) => {
    setSelectedId(valveId)
    setDetail(null)
    setDetailError('')
    setDetailLoading(true)
    try {
      const res = await fetch(`${API_BASE}/predictions/${valveId}`)
      if (!res.ok) throw new Error('Unable to fetch valve detail')
      const data = await res.json()
      setDetail(data)
    } catch (err) {
      setDetailError(err.message || 'Failed to load valve detail')
    } finally {
      setDetailLoading(false)
    }
  }

  const closeDetail = () => {
    setSelectedId('')
    setDetail(null)
    setDetailError('')
    setDetailLoading(false)
  }

  return (
    <div className="app">
      <header className="topbar">
        <div>
          <p className="eyebrow">Valve Pricing Studio</p>
          <h1>Dashboard</h1>
          <p className="subtle">Track predictions, inspect details, and create new valve prices.</p>
        </div>
        <button className="primary" onClick={() => navigate('/create')}>
          Create Valve Price
        </button>
      </header>

      <section className="panel">
        <div className="panel-head">
          <h2>All Valve Prices</h2>
          <button className="ghost" onClick={fetchList} disabled={loading}>
            Refresh
          </button>
        </div>

        {loading && <div className="state">Loading predictions...</div>}
        {error && !loading && <div className="state error">{error}</div>}
        {!loading && !error && list.length === 0 && (
          <div className="state">No valve prices yet. Create your first prediction.</div>
        )}

        {!loading && !error && list.length > 0 && (
          <div className="grid">
            {list.map((item) => (
              <button
                key={item.valve_id}
                className="card"
                onClick={() => openDetail(item.valve_id)}
              >
                <div>
                  <p className="label">Valve ID</p>
                  <p className="mono">{item.valve_id}</p>
                </div>
                <div>
                  <p className="label">Predicted Price (INR)</p>
                  <p className="price">{formatPrice(item.price)}</p>
                </div>
              </button>
            ))}
          </div>
        )}
      </section>

      {selectedId && (
        <Modal onClose={closeDetail}>
          <div className="modal-head">
            <div>
              <p className="eyebrow">Valve Detail</p>
              <h3>{selectedId}</h3>
            </div>
            <button className="ghost" onClick={closeDetail}>Close</button>
          </div>

          {detailLoading && <div className="state">Loading valve details...</div>}
          {detailError && !detailLoading && <div className="state error">{detailError}</div>}

          {detail && !detailLoading && !detailError && (
            <div className="detail-grid">
              {Object.entries(detail).map(([key, value]) => (
                <div key={key} className="detail-item">
                  <p className="label">{toLabel(key)}</p>
                  <p className="value">{String(value)}</p>
                </div>
              ))}
            </div>
          )}
        </Modal>
      )}
    </div>
  )
}

function CreateValve() {
  const navigate = useNavigate()
  const [form, setForm] = useState(initialForm)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState(null)
  const [pdfUploading, setPdfUploading] = useState(false)
  const [pdfError, setPdfError] = useState('')

  const fields = useMemo(
    () => [
      { key: 'Service_Fluid', type: 'select' },
      { key: 'Valve_Type', type: 'select' },
      { key: 'Body_Material_Grade', type: 'select' },
      { key: 'Actuator_Type', type: 'select' },
      { key: 'End_Connection', type: 'select' },
      { key: 'Seat_Type', type: 'select' },
      { key: 'Pressure_Class_ASME', type: 'select' },
      { key: 'NPS_inch', type: 'number' },
      { key: 'Operating_Pressure_bar', type: 'number' },
      { key: 'Operating_Temperature_C', type: 'number' },
      { key: 'DeltaP_bar', type: 'number' },
      { key: 'Cv', type: 'number' }
    ],
    []
  )

  const updateField = (key, value) => {
    setForm((prev) => ({ ...prev, [key]: value }))
  }

  const submit = async (event) => {
    event.preventDefault()
    setSaving(true)
    setError('')
    setResult(null)

    try {
      const res = await fetch(`${API_BASE}/predict`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...form,
          Pressure_Class_ASME: Number(form.Pressure_Class_ASME),
          NPS_inch: Number(form.NPS_inch),
          Operating_Pressure_bar: Number(form.Operating_Pressure_bar),
          Operating_Temperature_C: Number(form.Operating_Temperature_C),
          DeltaP_bar: Number(form.DeltaP_bar),
          Cv: Number(form.Cv)
        })
      })

      if (!res.ok) throw new Error('Prediction failed. Check the API and inputs.')
      const data = await res.json()

      setResult({
        raw: data,
        price: data.price ?? data.predicted_price_inr ?? data.predicted_price ?? null,
        valveId: data.valve_id ?? data.id ?? null
      })
    } catch (err) {
      setError(err.message || 'Unable to create valve price')
    } finally {
      setSaving(false)
    }
  }

  const handlePdfUpload = async (file) => {
    if (!file) return
    setPdfUploading(true)
    setPdfError('')
    setError('')
    setResult(null)

    try {
      const formData = new FormData()
      formData.append('file', file)

      const res = await fetch(`${API_BASE}/predict-from-pdf`, {
        method: 'POST',
        body: formData
      })

      const data = await res.json()
      if (!res.ok) {
        let message = 'Failed to process PDF'
        if (data?.detail) {
          if (typeof data.detail === 'string') {
            message = data.detail
          } else if (typeof data.detail === 'object') {
            if (Array.isArray(data.detail.missing_fields) && data.detail.missing_fields.length > 0) {
              message = `Missing fields: ${data.detail.missing_fields.join(', ')}`
            } else if (data.detail.message) {
              message = data.detail.message
            }
          }
        }
        throw new Error(message)
      }

      if (data?.extracted_fields) {
        setForm((prev) => ({ ...prev, ...data.extracted_fields }))
      }

      setResult({
        raw: data,
        price: data.price ?? data.predicted_price_inr ?? data.predicted_price ?? null,
        valveId: data.valve_id ?? data.id ?? null
      })
    } catch (err) {
      setPdfError(err.message || 'Unable to read PDF')
    } finally {
      setPdfUploading(false)
    }
  }

  return (
    <div className="app">
      <header className="topbar">
        <div>
          <p className="eyebrow">New Prediction</p>
          <h1>Create Valve Price</h1>
          <p className="subtle">Upload an RFQ PDF or fill in valve attributes manually.</p>
        </div>
        <button className="ghost" onClick={() => navigate('/')}>Back to Dashboard</button>
      </header>

      <section className="panel">
        <div className="upload-card">
          <div>
            <h3>Upload RFQ PDF</h3>
            <p className="subtle">We will extract valve specs with PaddleOCR and predict the final price.</p>
          </div>
          <label className="upload-button">
            <input
              type="file"
              accept="application/pdf"
              onChange={(event) => handlePdfUpload(event.target.files?.[0])}
            />
            {pdfUploading ? 'Uploading...' : 'Choose PDF'}
          </label>
        </div>

        {pdfError && <div className="state error">{pdfError}</div>}

        <form className="form" onSubmit={submit}>
          {fields.map((field) => (
            <label key={field.key} className="field">
              <span>{toLabel(field.key)}</span>
              {field.type === 'select' ? (
                <select
                  value={form[field.key]}
                  onChange={(event) => updateField(field.key, event.target.value)}
                >
                  {(selectOptions[field.key] || []).map((option) => (
                    <option key={option} value={option}>
                      {option}
                    </option>
                  ))}
                </select>
              ) : (
                <input
                  type="number"
                  value={form[field.key]}
                  onChange={(event) => updateField(field.key, event.target.value)}
                  step="any"
                  required
                />
              )}
            </label>
          ))}

          <div className="actions">
            <button className="primary" type="submit" disabled={saving}>
              {saving ? 'Creating...' : 'Create Valve Price'}
            </button>
            <button
              className="ghost"
              type="button"
              onClick={() => setForm(initialForm)}
              disabled={saving}
            >
              Reset
            </button>
          </div>
        </form>

        {error && <div className="state error">{error}</div>}

        {result && (
          <div className="result">
            <div>
              <p className="label">Predicted Price</p>
              <p className="price">{result.price ? formatPrice(result.price) : '-'}</p>
            </div>
            <div>
              <p className="label">Valve ID</p>
              <p className="mono">{result.valveId || 'Returned in response'}</p>
            </div>
            <details>
              <summary>Raw API response</summary>
              <pre>{JSON.stringify(result.raw, null, 2)}</pre>
            </details>
          </div>
        )}
      </section>
    </div>
  )
}

function Modal({ children, onClose }) {
  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(event) => event.stopPropagation()}>
        {children}
      </div>
    </div>
  )
}

function formatPrice(value) {
  if (value === undefined || value === null || Number.isNaN(Number(value))) return '-'
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 2
  }).format(Number(value))
}

function toLabel(key) {
  return key
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (char) => char.toUpperCase())
}

export default App



