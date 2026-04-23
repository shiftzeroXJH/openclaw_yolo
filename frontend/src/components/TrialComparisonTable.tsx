import { CheckCircle2, CircleDashed, XCircle, Loader2, Trash2 } from 'lucide-react'
import { useState } from 'react'
import { DeleteDialog } from './DeleteDialog'

interface Props {
  data: any
  onRowClick: (trialId: string) => void
  onDeleteTrial: (trialId: string, keepFiles: boolean) => Promise<void>
}

export function TrialComparisonTable({ data, onRowClick, onDeleteTrial }: Props) {
  const [trialToDelete, setTrialToDelete] = useState<string | null>(null);

  if (!data || !data.rows || data.rows.length === 0) {
    return <div className="p-4 text-muted">暂无实验记录，请先运行一次实验。</div>
  }

  const cols = [
    'iteration', 'trial_id', 'status', 'source', 'map50_95', 'delta_map50_95', 
    'precision', 'recall', 'best_epoch', 'epochs_completed', 'imgsz', 'batch', 'lr0'
  ]

  const formatValue = (_key: string, val: any) => {
    if (val === undefined || val === null) return '-'
    if (typeof val === 'number') {
      if (Number.isInteger(val)) return val
      return val.toFixed(4)
    }
    return val
  }

  const renderStatus = (status: string) => {
    switch(status) {
      case 'COMPLETED': return <CheckCircle2 size={16} className="text-success" />
      case 'FAILED': 
      case 'CANCELLED': return <XCircle size={16} className="text-danger" />
      case 'TRAINING':
      case 'ANALYZING': return <Loader2 size={16} className="text-warning" style={{ animation: 'spin 1s linear infinite' }} />
      case 'WAITING_USER_CONFIRM': return <CircleDashed size={16} className="text-warning" />
      default: return status
    }
  }

  const renderDelta = (val: any) => {
    if (typeof val !== 'number') return '-'
    if (val > 0) return <span className="text-success">+{val.toFixed(4)}</span>
    if (val < 0) return <span className="text-danger">{val.toFixed(4)}</span>
    return <span className="text-muted">0.0</span>
  }

  return (
    <div className="table-wrapper h-full" style={{ border: 'none', borderRadius: 0 }}>
      <table>
        <thead style={{ position: 'sticky', top: 0, zIndex: 10 }}>
          <tr>
            {cols.map(c => <th key={c}>{c.replace(/_/g, ' ')}</th>)}
            <th>备注</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          {data.rows.map((r: any) => (
            <tr 
              key={r.trial_id} 
              onClick={() => onRowClick(r.trial_id)}
              style={{ 
                cursor: 'pointer',
                backgroundColor: r.is_best ? 'rgba(16, 185, 129, 0.05)' : undefined 
              }}
            >
              <td>{r.iteration}</td>
              <td style={{ fontWeight: r.is_best ? 'bold' : 'normal', color: r.is_best ? 'var(--success-color)' : 'inherit' }}>
                {r.trial_id} {r.is_best && '★'}
              </td>
              <td>{renderStatus(r.status)}</td>
              <td><span className="badge">{r.source}</span></td>
              <td style={{ fontWeight: 'bold' }}>{formatValue('map50_95', r.map50_95)}</td>
              <td>{renderDelta(r.delta_map50_95)}</td>
              <td>{formatValue('precision', r.precision)}</td>
              <td>{formatValue('recall', r.recall)}</td>
              <td>{r.best_epoch}</td>
              <td>{r.epochs_completed}</td>
              <td>{r.params?.imgsz || r.imgsz || '-'}</td>
              <td>{r.params?.batch || r.batch || '-'}</td>
              <td>{formatValue('lr0', r.params?.lr0 || r.lr0)}</td>
              <td style={{ maxWidth: 150, overflow: 'hidden', textOverflow: 'ellipsis' }}>{r.note || '-'}</td>
              <td>
                <button 
                  className="btn btn-danger" 
                  style={{ padding: '0.2rem 0.4rem', backgroundColor: 'transparent', color: 'var(--danger-color)', border: 'none', boxShadow: 'none' }}
                  onClick={(e) => { e.stopPropagation(); setTrialToDelete(r.trial_id); }}
                  title="删除该 Trial"
                >
                  <Trash2 size={16} />
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {trialToDelete && (
        <DeleteDialog
          title="删除训练记录"
          message={`确定要将训练记录 ${trialToDelete} 从面板中移除吗？这不会影响同属一个任务下的其他实验结果。`}
          dangerousMessage="同时删除本地磁盘上的此模型训练文件"
          onClose={() => setTrialToDelete(null)}
          onConfirm={async (keepFiles) => {
            await onDeleteTrial(trialToDelete, keepFiles);
            setTrialToDelete(null);
          }}
        />
      )}
    </div>
  )
}
