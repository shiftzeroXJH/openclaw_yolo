import { type Experiment } from '../api'
import { clsx } from 'clsx'

interface Props {
  experiments: Experiment[]
  activeId: string | null
  onSelect: (id: string) => void
}

export function ExperimentList({ experiments, activeId, onSelect }: Props) {
  if (experiments.length === 0) {
    return (
      <div className="p-4" style={{ color: 'var(--text-muted)', fontSize: '0.875rem', textAlign: 'center' }}>
        暂无实验记录。<br/>请点击上方 + 新建实验。
      </div>
    )
  }

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'COMPLETED': return 'badge-success'
      case 'FAILED':
      case 'CANCELLED': return 'badge-danger'
      case 'TRAINING':
      case 'ANALYZING':
      case 'RETRAINING': return 'badge-warning'
      case 'WAITING_USER_CONFIRM': return 'badge-warning'
      default: return ''
    }
  }

  const getStatusText = (status: string) => {
    const map: any = {
      COMPLETED: '已完成',
      FAILED: '训练失败',
      CANCELLED: '已取消',
      TRAINING: '训练中',
      ANALYZING: '正在分析',
      RETRAINING: '重新训练',
      WAITING_USER_CONFIRM: '待确认',
      READY: '准备就绪'
    }
    return map[status] || status.replace(/_/g, ' ')
  }

  return (
    <div className="flex-col px-2 py-4 gap-2">
      {experiments.map(exp => (
        <div 
          key={exp.experiment_id}
          className={clsx("card flex-col gap-2", { 'active': exp.experiment_id === activeId })}
          style={{ 
            cursor: 'pointer', 
            transition: 'background-color var(--transition-fast)',
            borderColor: exp.experiment_id === activeId ? 'var(--primary-color)' : 'var(--panel-border)',
            backgroundColor: exp.experiment_id === activeId ? 'rgba(59, 130, 246, 0.05)' : undefined
          }}
          onClick={() => onSelect(exp.experiment_id)}
        >
          <div className="flex items-center justify-between">
            <span style={{ fontWeight: 600, fontSize: '0.875rem' }}>{exp.description}</span>
            <span className={clsx("badge", getStatusBadge(exp.status))}>
              {getStatusText(exp.status)}
            </span>
          </div>
          
          <div className="flex justify-between" style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            <span>运行次数: {exp.trial_count}</span>
            <span>类型: {exp.task_type}</span>
          </div>

          <div style={{ fontSize: '0.75rem', backgroundColor: 'var(--bg-color)', padding: '0.5rem', borderRadius: 'var(--radius-sm)' }}>
            <div className="flex justify-between">
              <span>目标指标 ({exp.goal.metric})</span>
              <span style={{ color: 'var(--text-main)' }}>{exp.goal.target}</span>
            </div>
            {exp.best_metric && (
              <div className="flex justify-between" style={{ marginTop: '0.25rem' }}>
                <span>最优达成</span>
                <span className={exp.best_metric.value >= exp.goal.target ? 'text-success' : 'text-warning'}>
                  {exp.best_metric.value.toFixed(4)}
                </span>
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
  )
}
