import React from 'react'
import { Alert, Button, Space, Steps, Typography } from 'antd'
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  ClockCircleOutlined,
  LoadingOutlined,
} from '@ant-design/icons'
import type { LearningTask, LearningTaskStep } from '../types'

const { Text } = Typography

const statusMap: Record<string, 'wait' | 'process' | 'finish' | 'error'> = {
  pending: 'wait',
  running: 'process',
  done: 'finish',
  skipped: 'wait',
  failed: 'error',
}

const iconMap: Record<string, React.ReactNode> = {
  pending: <ClockCircleOutlined />,
  running: <LoadingOutlined />,
  done: <CheckCircleOutlined />,
  skipped: <ClockCircleOutlined />,
  failed: <CloseCircleOutlined />,
}

const defaultLabels: Record<string, string> = {
  task_created: '任务已创建',
  workflow_started: '正在启动学习任务',
  load_student_state: '正在读取画像',
  profile_update: '正在更新画像',
  latest_evaluation: '正在分析评估',
  path_agent: '正在生成路径',
  profile_agent: '正在分析画像',
  eval_agent: '正在生成评估',
  resource_agent: '正在生成资源',
  resource_recommendations: '正在生成推荐资源',
  save_result: '正在保存结果',
  task_completed: '任务完成',
}

interface TaskProgressProps {
  task: LearningTask | null
  onClose?: () => void
}

const visibleSteps = (steps: LearningTaskStep[]) =>
  steps.filter((step) => step.name !== 'task_created')

const taskTitle = (task: LearningTask) => {
  if (task.status === 'succeeded') return '任务已完成'
  if (task.status === 'failed') return '任务失败'
  const current = [...visibleSteps(task.steps)].reverse().find((step) => step.status === 'running')
  return current?.label || defaultLabels[current?.name || ''] || '任务正在执行'
}

const TaskProgress: React.FC<TaskProgressProps> = ({ task, onClose }) => {
  if (!task) return null

  const failedStep = task.steps.find((step) => step.status === 'failed')
  const errorText = task.error || failedStep?.error
  const steps = visibleSteps(task.steps)

  return (
    <Alert
      type={task.status === 'failed' ? 'error' : task.status === 'succeeded' ? 'success' : 'info'}
      showIcon
      style={{ marginTop: 16, marginBottom: 16 }}
      message={
        <Space style={{ width: '100%', justifyContent: 'space-between' }}>
          <Text strong>{taskTitle(task)}</Text>
          {onClose && task.status !== 'running' && (
            <Button size="small" onClick={onClose}>关闭</Button>
          )}
        </Space>
      }
      description={
        <div>
          <Steps
            size="small"
            direction="vertical"
            items={steps.map((step) => ({
              title: step.label || defaultLabels[step.name] || step.name,
              description: step.error || undefined,
              status: statusMap[step.status] || 'wait',
              icon: iconMap[step.status],
            }))}
          />
          {errorText && (
            <Text type="danger">失败原因：{errorText}</Text>
          )}
        </div>
      }
    />
  )
}

export default TaskProgress
