import { useEffect, useState } from 'react'
import { createPortal } from 'react-dom'
import { api } from '../api'

interface Props {
  trialId: string
}

export function ImageGallery({ trialId }: Props) {
  const [images, setImages] = useState<string[]>([])
  const [loading, setLoading] = useState(true)
  const [fullscreenImage, setFullscreenImage] = useState<string | null>(null)

  useEffect(() => {
    const fetchImages = async () => {
      setLoading(true)
      try {
        const res = await api.getTrialVisualizations(trialId)
        setImages(res.visualizations || [])
      } catch (err) {
        console.error("Failed to load visualizations:", err)
      } finally {
        setLoading(false)
      }
    }
    fetchImages()
  }, [trialId])

  if (loading) {
    return <div className="text-muted p-4 text-center">正在读取原图...</div>
  }

  if (images.length === 0) {
    return (
      <div className="card text-center text-muted" style={{ padding: '3rem 1rem' }}>
        <p>暂无训练过程图片</p>
        <span style={{ fontSize: '0.75rem' }}>可能由于训练过早被中断，未生成 batch 图片。</span>
      </div>
    )
  }

  const curves = images.filter(img => img.endsWith('.png'))
  const batches = images.filter(img => img.startsWith('train_batch') || img.startsWith('val_batch'))

  const renderGroup = (title: string, items: string[]) => {
    if (items.length === 0) return null;
    return (
      <div className="flex-col gap-4 mb-6">
        <h4 style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--text-muted)', borderBottom: '1px solid var(--panel-border)', paddingBottom: '0.5rem' }}>
          {title} ({items.length})
        </h4>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '1rem' }}>
          {items.map(img => (
            <div 
              key={img} 
              className="card p-0 overflow-hidden flex-col" 
              style={{ cursor: 'pointer', transition: 'transform 0.2s', border: '1px solid var(--panel-border)' }}
              onClick={() => setFullscreenImage(img)}
              onMouseEnter={(e) => e.currentTarget.style.transform = 'scale(1.02)'}
              onMouseLeave={(e) => e.currentTarget.style.transform = 'scale(1)'}
            >
              <div className="p-2 border-b border-panel-border" style={{ fontSize: '0.875rem', fontWeight: 600, background: 'rgba(0,0,0,0.02)' }}>
                {img}
              </div>
              <div style={{ backgroundColor: '#050505', display: 'flex', justifyContent: 'center' }}>
                <img 
                  src={`/api/trials/${trialId}/files/${img}`} 
                  alt={img} 
                  style={{ width: '100%', maxHeight: '550px', objectFit: 'contain' }}
                  loading="lazy"
                />
              </div>
            </div>
          ))}
        </div>
      </div>
    )
  }

  return (
    <>
      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) minmax(0, 1fr)', gap: '1.5rem', alignItems: 'start' }}>
        <div style={{ minWidth: 0 }}>
          {renderGroup('分析查错图表 (Curves)', curves)}
        </div>
        <div style={{ minWidth: 0 }}>
          {renderGroup('验证集批次图像 (Batches)', batches)}
        </div>
      </div>

      {fullscreenImage && createPortal(
        <div 
          style={{
            position: 'fixed', inset: 0, zIndex: 99999, 
            backgroundColor: 'rgba(0,0,0,0.85)', backdropFilter: 'blur(4px)',
            display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'zoom-out'
          }} 
          onClick={() => setFullscreenImage(null)}
          title="点击空白处关闭"
        >
          <img 
            src={`/api/trials/${trialId}/files/${fullscreenImage}`} 
            style={{ maxWidth: '98vw', maxHeight: '98vh', objectFit: 'contain', borderRadius: '8px', boxShadow: '0 10px 40px rgba(0,0,0,0.5)' }} 
            onClick={(e) => e.stopPropagation()}
          />
        </div>,
        document.body
      )}
    </>
  )
}
