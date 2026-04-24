import { useState } from 'react'
import { api } from '../api'

interface Props {
  onClose: () => void
  onCreated: (id: string) => void
}

export function CreateExperimentDialog({ onClose, onCreated }: Props) {
  const [form, setForm] = useState({
    description: '',
    task_type: 'detection',
    dataset_root: '',
    pretrained: 'yolo26n.pt',
    save_root: 'runs',
    goal_metric: 'map50_95',
    goal_target: '0.65',
  })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      const payload = {
        description: form.description,
        task_type: form.task_type,
        dataset_root: form.dataset_root,
        pretrained: form.pretrained,
        save_root: form.save_root,
        goal: { metric: form.goal_metric, target: parseFloat(form.goal_target) },
      }
      const res = await api.createExperiment(payload)
      if (res.experiment_id) {
        onCreated(res.experiment_id)
      }
    } catch (err: any) {
      setError(err?.detail?.error || '创建实验失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{
      position: 'fixed', inset: 0,
      backgroundColor: 'rgba(0,0,0,0.5)',
      backdropFilter: 'blur(2px)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      zIndex: 100,
    }}>
      <div className="card" style={{ width: '500px', maxWidth: '100%' }}>
        <h2 style={{ marginBottom: '1rem', fontSize: '1.25rem' }}>创建实验</h2>
        {error && <div className="p-4" style={{ backgroundColor: 'var(--danger-color)', color: '#fff', borderRadius: 'var(--radius-sm)', marginBottom: '1rem' }}>{error}</div>}
        <form className="flex-col gap-4" onSubmit={handleSubmit}>
          <div className="flex-col gap-2">
            <label style={{ fontSize: '0.875rem' }}>实验描述</label>
            <input required className="input" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} placeholder="例如：金具 224 baseline" />
          </div>

          <div className="flex gap-4">
            <div className="flex-col gap-2 w-full">
              <label style={{ fontSize: '0.875rem' }}>数据集目录 (Dataset Root)</label>
              <input required className="input" value={form.dataset_root} onChange={(e) => setForm({ ...form, dataset_root: e.target.value })} placeholder="C:/datasets/my_dataset" />
            </div>
            <div className="flex-col gap-2 w-full">
              <label style={{ fontSize: '0.875rem' }}>保存目录 (Save Root)</label>
              <input required className="input" value={form.save_root} onChange={(e) => setForm({ ...form, save_root: e.target.value })} placeholder="runs" />
            </div>
          </div>

          <div className="flex gap-4">
            <div className="flex-col gap-2 w-full">
              <label style={{ fontSize: '0.875rem' }}>初始模型 (Model)</label>
              <input required className="input" value={form.pretrained} onChange={(e) => setForm({ ...form, pretrained: e.target.value })} />
            </div>
            <div className="flex-col gap-2 w-full">
              <label style={{ fontSize: '0.875rem' }}>目标指标 ({form.goal_metric})</label>
              <input type="number" step="0.01" required className="input" value={form.goal_target} onChange={(e) => setForm({ ...form, goal_target: e.target.value })} />
            </div>
          </div>

          <div className="flex justify-end gap-2 mt-4 pt-4" style={{ borderTop: '1px solid var(--panel-border)' }}>
            <button type="button" className="btn" onClick={onClose}>取消</button>
            <button type="submit" className="btn btn-primary" disabled={loading}>
              {loading ? '正在创建...' : '创建实验'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
