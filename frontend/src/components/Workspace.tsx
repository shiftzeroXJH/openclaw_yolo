import { useEffect, useState } from 'react'
import { api } from '../api'
import { TrialComparisonTable } from './TrialComparisonTable'
import { ParameterEditor } from './ParameterEditor'
import { TrialSummaryDrawer } from './TrialSummaryDrawer'

interface Props {
  experimentId: string
}

export function Workspace({ experimentId }: Props) {
  const [detail, setDetail] = useState<any>(null)
  const [comparison, setComparison] = useState<any>(null)
  const [selectedTrialId, setSelectedTrialId] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  const loadData = async () => {
    setLoading(true)
    try {
      const [det, comp] = await Promise.all([
        api.getExperiment(experimentId),
        api.getComparison(experimentId)
      ])
      setDetail(det)
      setComparison(comp)
    } catch (err) {
      console.error('Failed to load workspace data:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [experimentId])

  if (loading || !detail) return <div className="p-4">正在加载实验详情...</div>

  return (
    <div className="flex p-4 gap-4 h-full">
      <div className="flex-col w-full h-full gap-4 overflow-hidden" style={{ flex: 1 }}>
        <div className="card">
          <div className="flex justify-between items-center bg-transparent">
            <div>
              <h1 style={{ fontSize: '1.25rem', marginBottom: '0.25rem' }}>{detail.experiment.description}</h1>
              <div className="flex gap-4 text-muted" style={{ fontSize: '0.875rem' }}>
                <span>数据集: {detail.experiment.dataset_root}</span>
                <span>初始模型: {detail.experiment.pretrained_model}</span>
                <span>历史运行总计: {detail.trial_count || 0}</span>
              </div>
            </div>
          </div>
        </div>

        <div className="card flex-col flex-1 overflow-hidden" style={{ padding: 0 }}>
          <div className="p-4 border-b border-panel-border" style={{ borderBottom: '1px solid var(--panel-border)', display: 'flex', justifyContent: 'space-between' }}>
            <h2 style={{ fontSize: '1rem' }}>历次试验对比图表</h2>
            <button className="btn" onClick={loadData}>刷新</button>
          </div>
          <div style={{ flex: 1, overflow: 'hidden' }}>
            {comparison ? (
              <TrialComparisonTable data={comparison} onRowClick={setSelectedTrialId} />
            ) : <div className="p-4">暂无对比数据</div>}
          </div>
        </div>
      </div>

      <div className="flex-col h-full gap-4" style={{ width: '380px' }}>
        <ParameterEditor experimentId={experimentId} onRunSuccess={loadData} />
      </div>

      {selectedTrialId && (
        <TrialSummaryDrawer 
          trialId={selectedTrialId} 
          onClose={() => setSelectedTrialId(null)} 
        />
      )}
    </div>
  )
}
