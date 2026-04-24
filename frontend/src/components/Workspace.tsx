import { useEffect, useState } from 'react'
import { Activity, Check, Edit2, RadioTower, Square, Trash2, X } from 'lucide-react'
import { api } from '../api'
import { ConfirmDialog } from './ConfirmDialog'
import { DeleteDialog } from './DeleteDialog'
import { ExperimentCurvesDialog } from './ExperimentCurvesDialog'
import { ParameterEditor } from './ParameterEditor'
import { RemoteTrialDialog } from './RemoteTrialDialog'
import { TrialComparisonTable } from './TrialComparisonTable'
import { TrialSummaryDrawer } from './TrialSummaryDrawer'

interface Props {
  experimentId: string
  onExperimentUpdated?: () => void
  onDeleted: () => void
}

const CANCELLABLE_STATUSES = new Set([
  'TRAINING',
  'RETRAINING',
  'ANALYZING',
  'WAITING_USER_CONFIRM',
])

export function Workspace({ experimentId, onExperimentUpdated, onDeleted }: Props) {
  const [detail, setDetail] = useState<any>(null)
  const [comparison, setComparison] = useState<any>(null)
  const [selectedTrialId, setSelectedTrialId] = useState<string | null>(null)
  const [trialToDelete, setTrialToDelete] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [isDeleting, setIsDeleting] = useState(false)
  const [isCancelling, setIsCancelling] = useState(false)
  const [showCurves, setShowCurves] = useState(false)
  const [showRemoteDialog, setShowRemoteDialog] = useState(false)
  const [isRenaming, setIsRenaming] = useState(false)
  const [renameValue, setRenameValue] = useState('')
  const [renaming, setRenaming] = useState(false)

  const loadData = async () => {
    setLoading(true)
    try {
      const [det, comp] = await Promise.all([
        api.getExperiment(experimentId),
        api.getComparison(experimentId),
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
      if (msg.includes('force=true') && confirm(`${msg}\n是否强制删除该训练记录？`)) {
        await api.deleteTrial(trialId, keepFiles, true)
        await loadData()
      } else {
        alert(msg)
      }
    }
  }

  const handleCancelExperiment = async () => {
    try {
      await api.cancelExperiment(experimentId, '用户手动停止')
      setIsCancelling(false)
      await loadData()
      onExperimentUpdated?.()
    } catch (err: any) {
      alert(err?.detail?.error || '停止失败')
    }
  }

  const startRename = () => {
    setRenameValue(detail.experiment.description)
    setIsRenaming(true)
  }

  const handleRename = async () => {
    const nextName = renameValue.trim()
    if (!nextName) {
      alert('任务名称不能为空')
      return
    }
    setRenaming(true)
    try {
      await api.updateExperiment(experimentId, { description: nextName })
      setIsRenaming(false)
      await loadData()
      onExperimentUpdated?.()
    } catch (err: any) {
      alert(err?.detail?.error || '重命名失败')
    } finally {
      setRenaming(false)
    }
  }

  if (loading || !detail) return <div className="p-4">正在加载实验详情...</div>

  const experiment = detail.experiment
  const canCancel = CANCELLABLE_STATUSES.has(experiment.status)

  return (
    <div className="workspace-grid">
      <div className="workspace-center">
        <div className="card">
          <div className="flex justify-between items-center bg-transparent">
            <div>
              {isRenaming ? (
                <div className="flex items-center gap-2" style={{ marginBottom: '0.25rem' }}>
                  <input
                    className="input"
                    style={{ width: 320, maxWidth: '100%', fontSize: '1rem', fontWeight: 600 }}
                    value={renameValue}
                    onChange={(event) => setRenameValue(event.target.value)}
                    onKeyDown={(event) => {
                      if (event.key === 'Enter') handleRename()
                      if (event.key === 'Escape') setIsRenaming(false)
                    }}
                    autoFocus
                  />
                  <button className="btn btn-primary" style={{ padding: '0.35rem 0.55rem' }} onClick={handleRename} disabled={renaming} title="保存">
                    <Check size={16} />
                  </button>
                  <button className="btn" style={{ padding: '0.35rem 0.55rem' }} onClick={() => setIsRenaming(false)} disabled={renaming} title="取消">
                    <X size={16} />
                  </button>
                </div>
              ) : (
                <div className="flex items-center gap-2" style={{ marginBottom: '0.25rem' }}>
                  <h1 style={{ fontSize: '1.25rem' }}>{experiment.description}</h1>
                  <button className="btn" style={{ padding: '0.25rem 0.45rem' }} onClick={startRename} title="重命名">
                    <Edit2 size={14} /> 重命名
                  </button>
                </div>
              )}
              <div className="flex gap-4 text-muted" style={{ fontSize: '0.875rem', flexWrap: 'wrap' }}>
                <span>数据集：{experiment.dataset_root}</span>
                <span>默认模型：{detail.default_model || experiment.pretrained_model}</span>
                <span>状态：{experiment.status}</span>
                <span>试验次数：{detail.trial_count || 0}</span>
              </div>
            </div>
            <div className="flex gap-2">
              {canCancel && (
                <button className="btn" onClick={() => setIsCancelling(true)} title="停止任务">
                  <Square size={16} /> 停止任务
                </button>
              )}
              <button className="btn btn-danger" onClick={() => setIsDeleting(true)} title="删除任务">
                <Trash2 size={16} /> 删除任务
              </button>
            </div>
          </div>
        </div>

        <div className="card comparison-card">
          <div className="p-4" style={{ borderBottom: '1px solid var(--panel-border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h2 style={{ fontSize: '1rem' }}>历次试验对比汇总</h2>
            <div className="flex gap-2">
              <button className="btn" onClick={() => setShowRemoteDialog(true)}>
                <RadioTower size={16} /> 导入远程训练
              </button>
              <button className="btn" onClick={() => setShowCurves(true)}>
                <Activity size={16} /> 曲线对比
              </button>
              <button className="btn" onClick={loadData}>刷新</button>
            </div>
          </div>
          <div style={{ flex: 1, overflow: 'hidden' }}>
            {comparison ? (
              <TrialComparisonTable
                data={comparison}
                onRowClick={setSelectedTrialId}
                onRequestDeleteTrial={setTrialToDelete}
              />
            ) : (
              <div className="p-4">暂无对比数据。</div>
            )}
          </div>
        </div>
      </div>

      <div className="training-column">
        <ParameterEditor experimentId={experimentId} onRunSuccess={loadData} />
      </div>

      {selectedTrialId && (
        <TrialSummaryDrawer
          trialId={selectedTrialId}
          onClose={() => setSelectedTrialId(null)}
          onUpdated={loadData}
        />
      )}

      {showRemoteDialog && (
        <RemoteTrialDialog experimentId={experimentId} onClose={() => setShowRemoteDialog(false)} onImported={loadData} />
      )}

      {trialToDelete && (
        <DeleteDialog
          title="删除训练记录"
          message={`确定删除训练记录 ${trialToDelete} 吗？`}
          dangerousMessage="同时删除本地托管文件"
          onClose={() => setTrialToDelete(null)}
          onConfirm={async (keepFiles) => {
            await handleDeleteTrial(trialToDelete, keepFiles)
            setTrialToDelete(null)
          }}
        />
      )}

      {isCancelling && (
        <ConfirmDialog
          title="停止任务"
          message="这会立即终止当前本地训练进程，并将实验状态标记为已取消。若当前没有本地训练进程在运行，则只会更新状态。"
          confirmLabel="确认停止"
          confirmClassName="btn btn-danger"
          onClose={() => setIsCancelling(false)}
          onConfirm={handleCancelExperiment}
        />
      )}

      {isDeleting && (
        <DeleteDialog
          title="删除任务"
          message={`确定删除实验“${experiment.description}”吗？此操作会移除该实验下的所有 Trial 记录。`}
          dangerousMessage="同时删除本地托管的训练文件"
          onClose={() => setIsDeleting(false)}
          onConfirm={async (keepFiles) => {
            try {
              await api.deleteExperiment(experimentId, keepFiles, false)
              setIsDeleting(false)
              onDeleted()
            } catch (err: any) {
              const msg = err?.detail?.error || '删除失败'
              if (msg.includes('force=true') && confirm(`${msg}\n是否强制删除该实验？`)) {
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
