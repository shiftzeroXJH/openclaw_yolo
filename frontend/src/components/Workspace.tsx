import { useEffect, useState } from 'react'
import { api } from '../api'
import { TrialComparisonTable } from './TrialComparisonTable'
import { ParameterEditor } from './ParameterEditor'
import { TrialSummaryDrawer } from './TrialSummaryDrawer'
import { Trash2, Activity } from 'lucide-react'
import { DeleteDialog } from './DeleteDialog'
import { ExperimentCurvesDialog } from './ExperimentCurvesDialog'

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

  const handleDeleteTrial = async (trialId: string, keepFiles: boolean) => {
    try {
      await api.deleteTrial(trialId, keepFiles, false);
      // Wait for backend to delete DB objects
      await new Promise(r => setTimeout(r, 600)); 
      await loadData();
    } catch (e: any) {
      const msg = e?.detail?.error || '删除失败';
      if (msg.includes('force=true')) {
        if (confirm(`${msg}\n此训练仍在进行中，是否强行删除？`)) {
          await api.deleteTrial(trialId, keepFiles, true);
          await loadData();
        }
      } else {
        alert(msg);
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
              <div className="flex gap-4 text-muted" style={{ fontSize: '0.875rem' }}>
                <span>数据集: {detail.experiment.dataset_root}</span>
                <span>初始模型: {detail.experiment.pretrained_model}</span>
                <span>历史运行总计: {detail.trial_count || 0}</span>
              </div>
            </div>
            <button className="btn btn-danger" onClick={() => setIsDeleting(true)} title="删除实验">
              <Trash2 size={16} /> 删除任务
            </button>
          </div>
        </div>

        <div className="card flex-col flex-1 overflow-hidden" style={{ padding: 0 }}>
          <div className="p-4 border-b border-panel-border" style={{ borderBottom: '1px solid var(--panel-border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h2 style={{ fontSize: '1rem' }}>历次试验对比汇总</h2>
            <div className="flex gap-2">
              <button className="btn" style={{ borderColor: 'var(--primary-color)', color: 'var(--primary-color)', display: 'flex', alignItems: 'center', gap: '0.25rem' }} onClick={() => setShowCurves(true)}>
                <Activity size={16} /> 上帝视野联合曲线
              </button>
              <button className="btn" onClick={loadData}>刷新数据</button>
            </div>
          </div>
          <div style={{ flex: 1, overflow: 'hidden' }}>
            {comparison ? (
              <TrialComparisonTable data={comparison} onRowClick={setSelectedTrialId} onDeleteTrial={handleDeleteTrial} />
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

      {isDeleting && (
        <DeleteDialog
          title="删除主线任务 (Experiment)"
          message={`确定要将实验 "${detail.experiment.description}" 彻底移除吗？此操作将移除该实验下的所有试运行记录（Trials）。`}
          dangerousMessage="同时删除本地磁盘上的根目录数据文件"
          onClose={() => setIsDeleting(false)}
          onConfirm={async (keepFiles) => {
            try {
              await api.deleteExperiment(experimentId, keepFiles, false);
              setIsDeleting(false);
              onDeleted();
            } catch (e: any) {
              const msg = e?.detail?.error || '删除失败';
              if (msg.includes('force=true')) {
                if (confirm(`${msg}\n已有任务正处于活跃中，是否强行删除该实验？\n危险：强行打断可能产生僵尸进程或文件锁。`)) {
                  await api.deleteExperiment(experimentId, keepFiles, true);
                  setIsDeleting(false);
                  onDeleted();
                }
              } else {
                alert(msg);
              }
            }
          }}
        />
      )}

      {showCurves && (
        <ExperimentCurvesDialog
          experimentId={experimentId}
          onClose={() => setShowCurves(false)}
        />
      )}
    </div>
  )
}
