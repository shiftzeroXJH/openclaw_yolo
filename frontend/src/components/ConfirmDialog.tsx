import { useCallback, useEffect, useState } from 'react'

interface Props {
  title: string
  message: string
  confirmLabel?: string
  confirmClassName?: string
  onConfirm: () => Promise<void>
  onClose: () => void
}

export function ConfirmDialog({
  title,
  message,
  confirmLabel = '确认',
  confirmClassName = 'btn btn-primary',
  onConfirm,
  onClose,
}: Props) {
  const [loading, setLoading] = useState(false)

  const handleConfirm = async () => {
    setLoading(true)
    try {
      await onConfirm()
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
        position: 'fixed',
        inset: 0,
        backgroundColor: 'rgba(0,0,0,0.4)',
        backdropFilter: 'blur(4px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 200,
      }}
      onClick={(e) => { if (e.target === e.currentTarget && !loading) onClose() }}
    >
      <div className="card" style={{ width: '450px', maxWidth: '100%' }}>
        <h2 style={{ marginBottom: '1rem', fontSize: '1.25rem' }}>{title}</h2>
        <p style={{ marginBottom: '1rem' }}>{message}</p>

        <div className="flex justify-end gap-2 pt-4" style={{ borderTop: '1px solid var(--panel-border)' }}>
          <button className="btn" onClick={onClose} disabled={loading}>取消</button>
          <button className={confirmClassName} onClick={handleConfirm} disabled={loading}>
            {loading ? '处理中...' : confirmLabel}
          </button>
        </div>
      </div>
    </div>
  )
}
