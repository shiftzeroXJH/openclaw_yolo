import { useEffect, useState } from 'react'
import { api } from '../api'

interface Props {
  experimentId: string
  onRunSuccess: () => void
}

export function ParameterEditor({ experimentId, onRunSuccess }: Props) {
  const [schemaData, setSchemaData] = useState<any>(null)
  const [params, setParams] = useState<any>({})
  const [model, setModel] = useState('')
  const [note, setNote] = useState('')
  const [loading, setLoading] = useState(false)
  const [validating, setValidating] = useState(false)
  const [validationErrors, setValidationErrors] = useState<any>({})

  const loadParams = async () => {
    const data = await api.getParams(experimentId)
    setSchemaData(data)
    setParams(data.latest_params || data.initial_params || {})
    setModel(data.default_model || '')
  }

  useEffect(() => {
    loadParams().catch(console.error)
  }, [experimentId])

  const handleValidate = async () => {
    setValidating(true)
    setValidationErrors({})
    try {
      const res = await api.validateParams(experimentId, params)
      if (!res.valid) {
        setValidationErrors(res.errors || {})
        return false
      }
      return true
    } catch (err: any) {
      setValidationErrors({ general: err?.detail?.error || '参数校验失败' })
      return false
    } finally {
      setValidating(false)
    }
  }

  const handleRun = async () => {
    const isValid = await handleValidate()
    if (!isValid) return
    setLoading(true)
    try {
      await api.runTrial(experimentId, { params, pretrained: model, note, reason: 'Manual tuning' })
      setNote('')
      onRunSuccess()
    } catch (err: any) {
      alert(err?.detail?.error || '运行失败')
    } finally {
      setLoading(false)
    }
  }

  if (!schemaData) return <div className="card h-full">正在加载参数...</div>
  const schema = schemaData.editable_schema || {}

  return (
    <div className="card h-full flex-col" style={{ overflow: 'hidden' }}>
      <h2 style={{ fontSize: '1rem', marginBottom: '1rem' }}>本地训练</h2>
      <div className="flex-col gap-4 overflow-y-auto pr-2" style={{ flex: 1 }}>
        {validationErrors.general && <div className="text-danger p-2">{validationErrors.general}</div>}
        <div className="flex-col gap-1">
          <label style={{ fontSize: '0.75rem', fontWeight: 600 }}>模型</label>
          <input className="input" value={model} onChange={(e) => setModel(e.target.value)} />
        </div>
        {Object.keys(schema).map((key) => {
          const field = schema[key]
          const isError = validationErrors[key]
          return (
            <div key={key} className="flex-col gap-1">
              <label style={{ fontSize: '0.75rem', fontWeight: 600, display: 'flex', justifyContent: 'space-between' }}>
                <span>{key}</span>
                <span className="text-muted" style={{ fontWeight: 'normal' }}>
                  {field.type === 'int' || field.type === 'float' ? `[${field.min ?? ''}-${field.max ?? ''}]` : ''}
                </span>
              </label>
              {field.type === 'choice' ? (
                <select
                  className="input"
                  style={{ borderColor: isError ? 'var(--danger-color)' : undefined }}
                  value={params[key] ?? ''}
                  onChange={(e) => {
                    const val = e.target.value
                    const parsed = field.values && typeof field.values[0] === 'number' ? Number(val) : val
                    setParams({ ...params, [key]: parsed })
                  }}
                >
                  <option value="" disabled>选择 {key}</option>
                  {field.values?.map((v: any) => <option key={v} value={v}>{v}</option>)}
                </select>
              ) : (
                <input
                  type="number"
                  step={field.type === 'int' ? field.step || 1 : 'any'}
                  className="input"
                  style={{ borderColor: isError ? 'var(--danger-color)' : undefined }}
                  value={params[key] ?? ''}
                  onChange={(e) => setParams({ ...params, [key]: field.type === 'int' ? parseInt(e.target.value) : parseFloat(e.target.value) })}
                />
              )}
              {isError && <span className="text-danger" style={{ fontSize: '0.7rem' }}>{String(isError)}</span>}
            </div>
          )
        })}
      </div>
      <div className="pt-4 mt-2" style={{ borderTop: '1px solid var(--panel-border)' }}>
        <div className="flex-col gap-2 mb-4">
          <label style={{ fontSize: '0.75rem' }}>备注</label>
          <input className="input" value={note} onChange={(e) => setNote(e.target.value)} />
        </div>
        <div className="flex gap-2">
          <button className="btn flex-1" onClick={handleValidate} disabled={validating || loading}>校验</button>
          <button className="btn btn-primary flex-1" onClick={handleRun} disabled={loading || validating}>开始运行</button>
        </div>
      </div>
    </div>
  )
}
