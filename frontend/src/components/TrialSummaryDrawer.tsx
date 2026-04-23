import { useEffect, useState } from 'react'
import { api } from '../api'
import { X } from 'lucide-react'

interface Props {
  trialId: string
  onClose: () => void
}

export function TrialSummaryDrawer({ trialId, onClose }: Props) {
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const load = async () => {
      setLoading(true)
      try {
        const res = await api.getTrialSummary(trialId)
        setData(res)
      } catch (err) {
        console.error(err)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [trialId])

  return (
    <>
      <div 
        style={{ position: 'fixed', inset: 0, backgroundColor: 'rgba(0,0,0,0.3)', zIndex: 40 }} 
        onClick={onClose} 
      />
      <div 
        className="card flex-col"
        style={{
          position: 'fixed', right: 0, top: 0, bottom: 0, width: '600px', maxWidth: '100vw',
          zIndex: 50, borderRadius: 0, borderRight: 'none', borderTop: 'none', borderBottom: 'none',
          boxShadow: '-4px 0 24px rgba(0,0,0,0.5)',
          overflow: 'hidden', padding: 0
        }}
      >
        <div className="flex justify-between items-center p-4 border-b border-panel-border" style={{ borderBottom: '1px solid var(--panel-border)' }}>
          <div>
            <h2 style={{ fontSize: '1.25rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              实验运行 <span className="text-primary">{trialId}</span>
            </h2>
          </div>
          <button className="btn" style={{ padding: '0.25rem' }} onClick={onClose}><X size={20} /></button>
        </div>

        <div className="flex-col overflow-y-auto p-4 gap-6">
          {loading ? (
            <div className="text-muted">正在加载报告...</div>
          ) : !data ? (
            <div className="text-danger">未能加载报告，或该实验尚无结果。</div>
          ) : (
            <>
              {/* Warnings */}
              {data.warnings?.length > 0 && (
                <div className="card" style={{ backgroundColor: 'rgba(245, 158, 11, 0.05)', borderColor: 'rgba(245, 158, 11, 0.2)' }}>
                  <h3 className="text-warning mb-2" style={{ fontSize: '1rem' }}>运行警告</h3>
                  <ul style={{ paddingLeft: '1.25rem', fontSize: '0.875rem' }} className="text-muted">
                    {data.warnings.map((w: string, i: number) => <li key={i}>{w}</li>)}
                  </ul>
                </div>
              )}

              {/* Final Metrics */}
              <div className="flex-col gap-2">
                <h3 style={{ fontSize: '1rem', fontWeight: 600 }}>最终测试指标</h3>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '0.5rem' }}>
                  {Object.entries(data.final_metrics || {}).map(([k, v]: [string, any]) => (
                    <div key={k} className="card p-2 text-center" style={{ padding: '0.75rem' }}>
                      <div className="text-muted" style={{ fontSize: '0.75rem', textTransform: 'uppercase' }}>{k}</div>
                      <div style={{ fontSize: '1.25rem', fontWeight: 600 }}>{typeof v === 'number' ? v.toFixed(4) : v}</div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Resource */}
              <div className="flex-col gap-2">
                <h3 style={{ fontSize: '1rem', fontWeight: 600 }}>资源占用</h3>
                <div className="table-wrapper">
                  <table>
                    <tbody>
                      <tr><td className="text-muted" style={{ width: 140 }}>训练用时</td><td>{data.resource?.train_time_sec ? `${data.resource.train_time_sec.toFixed(1)}s` : '-'}</td></tr>
                      <tr><td className="text-muted">显存峰值</td><td>{data.resource?.gpu_mem_peak ? `${data.resource.gpu_mem_peak} MB` : '-'}</td></tr>
                      <tr><td className="text-muted">运行目录</td><td style={{ fontSize: '0.75rem', wordBreak: 'break-all' }}>{data.trial?.run_dir || '-'}</td></tr>
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Params */}
              <div className="flex-col gap-2">
                <h3 style={{ fontSize: '1rem', fontWeight: 600 }}>详细使用参数</h3>
                <div className="table-wrapper">
                  <table>
                    <tbody>
                      {Object.entries(data.params || {}).map(([k, v]: [string, any]) => (
                        <tr key={k}>
                          <td className="text-muted" style={{ width: '50%' }}>{k}</td>
                          <td>{typeof v === 'number' ? v : String(v)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </>
  )
}
