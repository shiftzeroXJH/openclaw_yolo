import { useState, useEffect } from 'react'
import { api } from '../api'

interface Props {
  experimentId: string
  onRunSuccess: () => void
}

export function ParameterEditor({ experimentId, onRunSuccess }: Props) {
  const [schemaData, setSchemaData] = useState<any>(null)
  const [params, setParams] = useState<any>({})
  const [note, setNote] = useState('')
  const [loading, setLoading] = useState(false)
  const [validating, setValidating] = useState(false)
  const [validationErrors, setValidationErrors] = useState<any>({})

  const loadParams = async () => {
    try {
      const data = await api.getParams(experimentId)
      setSchemaData(data)
      setParams(data.latest_params || data.initial_params || {})
    } catch (err) {
      console.error(err)
    }
  }

  useEffect(() => { loadParams() }, [experimentId])

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
    } catch (e: any) {
      setValidationErrors({ general: e?.detail?.error || '参数校验失败' })
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
      await api.runTrial(experimentId, { params, note, reason: 'Manual tuning' })
      setNote('')
      // Give backend a bit of time to queue
      setTimeout(onRunSuccess, 500)
    } catch (e: any) {
      alert(e?.detail?.error || '运行失败')
    } finally {
      setLoading(false)
    }
  }

  if (!schemaData) return <div className="card h-full">正在加载参数...</div>

  const schema = schemaData.editable_schema || {}

  return (
    <div className="card h-full flex-col" style={{ overflow: 'hidden' }}>
      <div className="flex justify-between items-center mb-4">
        <h2 style={{ fontSize: '1rem' }}>参数编辑</h2>
      </div>

      <div className="flex-col gap-4 overflow-y-auto pr-2" style={{ flex: 1 }}>
        {validationErrors.general && (
          <div className="p-2 text-danger" style={{ backgroundColor: 'rgba(239, 68, 68, 0.1)', borderRadius: 4 }}>
            {validationErrors.general}
          </div>
        )}

        {Object.keys(schema).map(key => {
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
                  value={params[key] || ''} 
                  onChange={e => setParams({...params, [key]: e.target.value})}
                >
                  <option value="" disabled>Select {key}...</option>
                  {field.values?.map((v: any) => <option key={v} value={v}>{v}</option>)}
                </select>
              ) : (
                <input 
                  type="number" 
                  step={field.type === 'int' ? field.step || 1 : 'any'}
                  required={field.required}
                  className="input" 
                  style={{ borderColor: isError ? 'var(--danger-color)' : undefined, padding: '0.4rem 0.5rem' }}
                  value={params[key] ?? ''} 
                  onChange={e => setParams({...params, [key]: field.type === 'int' ? parseInt(e.target.value) : parseFloat(e.target.value)})}
                />
              )}
              {isError && <span className="text-danger" style={{ fontSize: '0.7rem' }}>{isError}</span>}
            </div>
          )
        })}
      </div>

      <div className="pt-4 mt-2" style={{ borderTop: '1px solid var(--panel-border)' }}>
        <div className="flex-col gap-2 mb-4">
          <label style={{ fontSize: '0.75rem' }}>实验备注 (可选)</label>
          <input className="input" placeholder="例如：尝试使用稍小batch" value={note} onChange={e => setNote(e.target.value)} />
        </div>
        <div className="flex gap-2">
          <button className="btn flex-1" onClick={handleValidate} disabled={validating || loading}>参数校验</button>
          <button className="btn btn-primary flex-1" onClick={handleRun} disabled={loading || validating}>开始运行</button>
        </div>
      </div>
    </div>
  )
}
