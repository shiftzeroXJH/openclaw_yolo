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
      } finally {
        setLoading(false)
      }
    }
    fetchImages().catch(console.error)
  }, [trialId])

  if (loading) return <div className="text-muted p-4 text-center">正在读取图片...</div>

  if (images.length === 0) {
    return (
      <div className="card text-center text-muted" style={{ padding: '3rem 1rem' }}>
        <p>暂无训练过程图片</p>
        <span style={{ fontSize: '0.75rem' }}>远程训练早期可能尚未生成 batch 图或结果图。</span>
      </div>
    )
  }

  const renderGroup = (title: string, items: string[]) => {
    if (items.length === 0) return null
    return (
      <div className="flex-col gap-4 mb-6">
        <h4 style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--text-muted)', borderBottom: '1px solid var(--panel-border)', paddingBottom: '0.5rem' }}>
          {title} ({items.length})
        </h4>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '1rem' }}>
          {items.map((image) => (
            <div key={image} className="card p-0 overflow-hidden flex-col" style={{ cursor: 'pointer' }} onClick={() => setFullscreenImage(image)}>
              <div className="p-2" style={{ fontSize: '0.875rem', fontWeight: 600, borderBottom: '1px solid var(--panel-border)' }}>{image}</div>
              <div style={{ backgroundColor: '#050505', display: 'flex', justifyContent: 'center' }}>
                <img src={`/api/trials/${trialId}/files/${image}`} alt={image} style={{ width: '100%', maxHeight: 550, objectFit: 'contain' }} loading="lazy" />
              </div>
            </div>
          ))}
        </div>
      </div>
    )
  }

  const batches = images.filter((image) => image.startsWith('train_batch') || image.startsWith('val_batch'))
  const other = images.filter((image) => !batches.includes(image))

  return (
    <>
      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) minmax(0, 1fr)', gap: '1.5rem', alignItems: 'start' }}>
        <div>{renderGroup('曲线与分析图', other)}</div>
        <div>{renderGroup('Batch 图片', batches)}</div>
      </div>
      {fullscreenImage && createPortal(
        <div
          style={{ position: 'fixed', inset: 0, zIndex: 99999, backgroundColor: 'rgba(0,0,0,0.85)', display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'zoom-out' }}
          onClick={() => setFullscreenImage(null)}
        >
          <img
            src={`/api/trials/${trialId}/files/${fullscreenImage}`}
            alt={fullscreenImage}
            style={{ maxWidth: '98vw', maxHeight: '98vh', objectFit: 'contain', borderRadius: 8 }}
            onClick={(event) => event.stopPropagation()}
          />
        </div>,
        document.body
      )}
    </>
  )
}
