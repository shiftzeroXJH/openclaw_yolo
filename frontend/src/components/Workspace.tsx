import { useEffect, useState } from 'react'
import { Activity, RadioTower, Trash2 } from 'lucide-react'
import { api } from '../api'
import { DeleteDialog } from './DeleteDialog'
import { ExperimentCurvesDialog } from './ExperimentCurvesDialog'
import { ParameterEditor } from './ParameterEditor'
import { RemoteTrialDialog } from './RemoteTrialDialog'
import { TrialComparisonTable } from './TrialComparisonTable'
import { TrialSummaryDrawer } from './TrialSummaryDrawer'

interface Props {
  experimentId: string
  onDeleted: () => void
}

export function Workspace({ experimentId, onDeleted }: Props) {
  const [detail, setDetail] = useState<any>(null)
  const [comparison, setComparison] = useState<any>(null)
  const [selectedTrialId, setSelectedTrialId] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [isDeleting, setIsDeleting] = useState(false)
  const [showCurves, setShowCurves] = useState(false)
  const [showRemoteDialog, setShowRemoteDialog] = useState(false)

  const loadData = async () => {
    setLoading(true)
    try {
      const [det, comp] = await Promise.all([
        api.getExperiment(experimentId),
        api.getComparison(experimentId)
      ])
      setDetail(det)
      setComparison(comp)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [experimentId])

  const handleDeleteTrial = async (trialId: string, keepFiles: boolean) => {
    try {
      await api.deleteTrial(trialId, keepFiles, false)
      await loadData()
    } catch (err: any) {
      const msg = err?.detail?.error || '删除失败'
      if (msg.includes('force=true') && confirm(`${msg}\n是否强制删除？`)) {
        await api.deleteTrial(trialId, keepFiles, true)
        await loadData()
      } else {
        alert(msg)
      }
    }
  }

  if (loading || !detail) return <div className="p-4">正在加载实验详情...</div>

  return (
    <div className="flex p-4 gap-4 h-full">
      <div className="flex-col w-full h-full gap-4 overflow-hidden" style={{ flex: 1 }}>
        <div className="card">
          <div className="flex justify-between items-center bg-transparent">
            <div>
              <h1 style={{ fontSize: '1.25rem', marginBottom: '0.25rem' }}>{detail.experiment.description}</h1>
              <div className="flex gap-4 text-muted" style={{ fontSize: '0.875rem', flexWrap: 'wrap' }}>
                <span>数据集: {detail.experiment.dataset_root}</span>
                <span>默认模型: {detail.default_model || detail.experiment.pretrained_model}</span>
                <span>Trial: {detail.trial_count || 0}</span>
              </div>
            </div>
            <button className="btn btn-danger" onClick={() => setIsDeleting(true)} title="删除实验">
              <Trash2 size={16} /> 删除任务
            </button>
          </div>
        </div>

        <div className="card flex-col flex-1 overflow-hidden" style={{ padding: 0 }}>
          <div className="p-4" style={{ borderBottom: '1px solid var(--panel-border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h2 style={{ fontSize: '1rem' }}>历次试验对比汇总</h2>
            <div className="flex gap-2">
              <button className="btn" onClick={() => setShowRemoteDialog(true)}>
                <RadioTower size={16} /> 登记远程训练
              </button>
              <button className="btn" onClick={() => setShowCurves(true)}>
                <Activity size={16} /> 曲线对比
              </button>
              <button className="btn" onClick={loadData}>刷新</button>
            </div>
          </div>
          <div style={{ flex: 1, overflow: 'hidden' }}>
            {comparison ? (
              <TrialComparisonTable data={comparison} onRowClick={setSelectedTrialId} onDeleteTrial={handleDeleteTrial} />
            ) : (
              <div className="p-4">暂无对比数据</div>
            )}
          </div>
        </div>
      </div>

      <div className="flex-col h-full gap-4" style={{ width: 380 }}>
        <ParameterEditor experimentId={experimentId} onRunSuccess={loadData} />
      </div>

      {selectedTrialId && <TrialSummaryDrawer trialId={selectedTrialId} onClose={() => setSelectedTrialId(null)} onUpdated={loadData} />}

      {showRemoteDialog && (
        <RemoteTrialDialog experimentId={experimentId} onClose={() => setShowRemoteDialog(false)} onImported={loadData} />
      )}

      {isDeleting && (
        <DeleteDialog
          title="删除任务"
          message={`确定删除实验 "${detail.experiment.description}" 吗？此操作会移除该实验下的所有 Trial 记录。`}
          dangerousMessage="同时删除本地托管的训练文件"
          onClose={() => setIsDeleting(false)}
          onConfirm={async (keepFiles) => {
            try {
              await api.deleteExperiment(experimentId, keepFiles, false)
              setIsDeleting(false)
              onDeleted()
            } catch (err: any) {
              const msg = err?.detail?.error || '删除失败'
              if (msg.includes('force=true') && confirm(`${msg}\n是否强制删除？`)) {
                await api.deleteExperiment(experimentId, keepFiles, true)
                setIsDeleting(false)
                onDeleted()
              } else {
                alert(msg)
              }
            }
          }}
        />
      )}

      {showCurves && <ExperimentCurvesDialog experimentId={experimentId} onClose={() => setShowCurves(false)} />}
    </div>
  )
}
