import { useCallback, useEffect, useState } from 'react'

interface Props {
  title: string
  message: string
  dangerousMessage?: string
  onConfirm: (keepFiles: boolean) => Promise<void>
  onClose: () => void
}

export function DeleteDialog({ title, message, dangerousMessage, onConfirm, onClose }: Props) {
  const [keepFiles, setKeepFiles] = useState(true)
  const [loading, setLoading] = useState(false)

  const handleConfirm = async () => {
    setLoading(true)
    try {
      await onConfirm(keepFiles)
    } finally {
      setLoading(false)
    }
  }

  const handleKeyDown = useCallback((event: KeyboardEvent) => {
    if (event.key === 'Escape' && !loading) onClose()
  }, [loading, onClose])

  useEffect(() => {
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [handleKeyDown])

  return (
    <div
      style={{
        position: 'fixed', inset: 0,
        backgroundColor: 'rgba(0,0,0,0.4)',
        backdropFilter: 'blur(4px)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        zIndex: 200,
      }}
      onClick={(e) => { if (e.target === e.currentTarget && !loading) onClose() }}
    >
      <div className="card" style={{ width: '450px', maxWidth: '100%', border: '1px solid var(--danger-color)' }}>
        <h2 style={{ marginBottom: '1rem', fontSize: '1.25rem', color: 'var(--danger-color)' }}>{title}</h2>
        <p style={{ marginBottom: '1rem' }}>{message}</p>

        {dangerousMessage && (
          <div className="p-3 mb-4" style={{ backgroundColor: 'rgba(239,68,68,0.1)', borderRadius: 'var(--radius-sm)' }}>
            <label className="flex items-center gap-2" style={{ cursor: 'pointer', fontSize: '0.875rem' }}>
              <input type="checkbox" checked={!keepFiles} onChange={(e) => setKeepFiles(!e.target.checked)} style={{ width: '1rem', height: '1rem' }} />
              <span className="text-danger" style={{ fontWeight: 600 }}>{dangerousMessage}</span>
            </label>
            {!keepFiles && <div className="text-danger mt-1" style={{ fontSize: '0.75rem' }}>警告：物理文件删除后将无法恢复。</div>}
          </div>
        )}

        <div className="flex justify-end gap-2 pt-4" style={{ borderTop: '1px solid var(--panel-border)' }}>
          <button className="btn" onClick={onClose} disabled={loading}>取消</button>
          <button className="btn btn-danger" onClick={handleConfirm} disabled={loading}>
            {loading ? '正在删除...' : '确认删除'}
          </button>
        </div>
      </div>
    </div>
  )
}
