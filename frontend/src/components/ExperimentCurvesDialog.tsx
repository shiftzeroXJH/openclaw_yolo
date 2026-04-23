import { useEffect, useState, useMemo } from 'react'
import { api } from '../api'
import { X, Activity } from 'lucide-react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'

interface Props {
  experimentId: string
  onClose: () => void
}

const COLORS = ['#3b82f6', '#ef4444', '#10b981', '#f59e0b', '#8b5cf6', '#ec4899', '#14b8a6', '#f97316'];

export function ExperimentCurvesDialog({ experimentId, onClose }: Props) {
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [selectedTrials, setSelectedTrials] = useState<Set<string>>(new Set())

  useEffect(() => {
    const fetchCurves = async () => {
      setLoading(true)
      try {
        const res = await api.getExperimentCurves(experimentId)
        setData(res)
        // Auto-select latest 5 trials by default
        const tids = Object.keys(res.curves || {}).sort().reverse().slice(0, 5)
        setSelectedTrials(new Set(tids))
      } catch (err) {
        console.error("Failed to load curves:", err)
      } finally {
        setLoading(false)
      }
    }
    fetchCurves()
  }, [experimentId])

  const toggleTrial = (tid: string) => {
    const next = new Set(selectedTrials)
    if (next.has(tid)) next.delete(tid)
    else next.add(tid)
    setSelectedTrials(next)
  }

  // Pivot data for Recharts
  const chartData = useMemo(() => {
    if (!data?.curves) return []
    const epochSet = new Set<number>()
    Object.values(data.curves).forEach((arr: any) => arr.forEach((d: any) => epochSet.add(d.epoch)))
    if (epochSet.size === 0) return []

    const maxEpoch = Math.max(...Array.from(epochSet))
    const result = []

    for (let i = 1; i <= maxEpoch; i++) {
      const point: any = { epoch: i }
      Object.keys(data.curves).forEach(tid => {
        const row = data.curves[tid].find((d: any) => d.epoch === i)
        if (row) {
          point[tid] = row
        }
      })
      result.push(point)
    }
    return result
  }, [data])

  const trialIds = Object.keys(data?.curves || {}).sort()

  return (
    <div style={{ position: 'fixed', inset: 0, zIndex: 60, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <div
        style={{ position: 'absolute', inset: 0, backgroundColor: 'rgba(0,0,0,0.5)', backdropFilter: 'blur(4px)' }}
        onClick={onClose}
      />

      <div
        className="card flex-col"
        style={{
          position: 'relative', width: '90vw', height: '85vh', maxWidth: '1400px',
          zIndex: 61, padding: 0, display: 'flex', overflow: 'hidden'
        }}
      >
        <div className="flex justify-between items-center p-4 border-b border-panel-border" style={{ backgroundColor: 'rgba(255,255,255,0.05)' }}>
          <h2 style={{ fontSize: '1.25rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Activity className="text-primary" /> 上帝视野：横向性能对比图
          </h2>
          <button className="btn" style={{ padding: '0.25rem' }} onClick={onClose}><X size={20} /></button>
        </div>

        <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
          {/* Left panel: Filter */}
          <div style={{ width: '240px', borderRight: '1px solid var(--panel-border)', padding: '1rem', overflowY: 'auto', overscrollBehavior: 'contain' }}>
            <h3 style={{ fontSize: '0.875rem', fontWeight: 600, marginBottom: '1rem' }} className="text-muted">选择要对比的任务</h3>
            {loading ? (
              <div className="text-muted text-sm">加载中...</div>
            ) : trialIds.length === 0 ? (
              <div className="text-muted text-sm">暂无数据</div>
            ) : (
              <div className="flex-col gap-2">
                {trialIds.map((tid, idx) => (
                  <label key={tid} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer', fontSize: '0.875rem' }}>
                    <input
                      type="checkbox"
                      checked={selectedTrials.has(tid)}
                      onChange={() => toggleTrial(tid)}
                    />
                    <span style={{ color: selectedTrials.has(tid) ? COLORS[idx % COLORS.length] : 'var(--text-muted)' }}>
                      {tid}
                    </span>
                  </label>
                ))}
              </div>
            )}
          </div>

          {/* Right panel: Charts */}
          <div style={{ flex: 1, padding: '1.5rem', overflowY: 'auto', overscrollBehavior: 'contain', display: 'flex', flexDirection: 'column', gap: '2rem' }}>
            {loading ? (
              <div className="text-center text-muted" style={{ marginTop: '20vh' }}>解析超大数据中...</div>
            ) : chartData.length === 0 ? (
              <div className="text-center text-muted" style={{ marginTop: '20vh' }}>该实验下的任务还未产生可绘制的曲线数据</div>
            ) : (
              <>
                {[
                  { key: 'metrics/mAP50-95(B)', label: 'Box mAP50-95 (综合定位考核)' },
                  { key: 'metrics/mAP50-95(M)', label: 'Mask mAP50-95 (像素级分割考核)' },
                  { key: 'metrics/recall(B)', label: 'Recall (box召回率)' },
                  { key: 'metrics/precision(B)', label: 'Precision (box精准率)' },
                  { key: 'train/box_loss', label: 'Train Box Loss (box训练误差)' },
                  { key: 'train/seg_loss', label: 'Train Seg Loss (掩码训练误差)' },
                  { key: 'train/cls_loss', label: 'Train Class Loss (分类训练误差)' },
                ].map(metric => {
                  const hasMetric = chartData.some((d: any) =>
                    trialIds.some(tid => selectedTrials.has(tid) && d[tid] && typeof d[tid][metric.key] === 'number')
                  )
                  if (!hasMetric) return null;

                  return (
                    <div key={metric.key} style={{ minHeight: '450px', flexShrink: 0, border: '1px solid var(--panel-border)', borderRadius: '8px', padding: '1rem' }} className="flex-col gap-2">
                      <h3 style={{ fontSize: '1rem', fontWeight: 600, textAlign: 'center' }}>{metric.label}</h3>
                      <ResponsiveContainer width="100%" height="100%">
                        <LineChart data={chartData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                          <CartesianGrid strokeDasharray="3 3" stroke="rgba(0,0,0,0.1)" />
                          <XAxis dataKey="epoch" stroke="var(--text-muted)" />
                          <YAxis stroke="var(--text-muted)" domain={['auto', 'auto']} />
                          <Tooltip
                            contentStyle={{ backgroundColor: 'var(--panel-bg)', borderColor: 'var(--panel-border)', borderRadius: '8px' }}
                            itemStyle={{ fontSize: '0.875rem' }}
                          />
                          <Legend />
                          {trialIds.filter(tid => selectedTrials.has(tid)).map((tid, idx) => (
                            <Line
                              key={tid}
                              type="monotone"
                              dataKey={`${tid}.${metric.key}`}
                              name={`${tid}`}
                              stroke={COLORS[idx % COLORS.length]}
                              strokeWidth={2}
                              dot={false}
                              activeDot={{ r: 4 }}
                              connectNulls
                            />
                          ))}
                        </LineChart>
                      </ResponsiveContainer>
                    </div>
                  )
                })}
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
