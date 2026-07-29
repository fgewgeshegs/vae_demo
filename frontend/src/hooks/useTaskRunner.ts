import { useEffect, useRef, useState } from 'react'
import { message } from 'antd'
import { getTaskErrorMessage, taskApi } from '../services/api'
import type { LearningTask } from '../types'

interface RunTaskOptions {
  input?: Record<string, unknown>
  courseId?: number
  successMessage?: string
  failureMessage?: string
  onSuccess?: (task: LearningTask) => Promise<void> | void
  onFailure?: (task: LearningTask) => void
}

export function useTaskRunner() {
  const [activeTask, setActiveTask] = useState<LearningTask | null>(null)
  const [running, setRunning] = useState(false)
  const timerRef = useRef<number | null>(null)

  const stopPolling = () => {
    if (timerRef.current) {
      window.clearInterval(timerRef.current)
      timerRef.current = null
    }
  }

  useEffect(() => () => stopPolling(), [])

  const successText = (task: LearningTask, fallback?: string) => {
    const resultData = task.result?.data as Record<string, unknown> | undefined
    return String(fallback || resultData?.message || task.result?.message || '任务完成')
  }

  const runTask = async (
    taskType: LearningTask['task_type'],
    options: RunTaskOptions = {},
  ) => {
    stopPolling()
    setRunning(true)
    try {
      const created = (await taskApi.create(taskType, options.input, options.courseId)).data
      setActiveTask(created)

      timerRef.current = window.setInterval(async () => {
        try {
          const task = (await taskApi.get(created.id)).data
          setActiveTask(task)
          if (task.status === 'succeeded' || task.status === 'failed') {
            stopPolling()
            setRunning(false)
            if (task.status === 'succeeded') {
              message.success(successText(task, options.successMessage))
              await options.onSuccess?.(task)
            } else {
              message.error(task.error || options.failureMessage || '任务失败')
              options.onFailure?.(task)
            }
          }
        } catch (err) {
          stopPolling()
          setRunning(false)
          message.error(getTaskErrorMessage(err, options.failureMessage || '任务状态刷新失败'))
        }
      }, 1000)
    } catch (err) {
      setRunning(false)
      setActiveTask(null)
      message.error(getTaskErrorMessage(err, options.failureMessage || '任务创建失败'))
    }
  }

  const clearTask = () => {
    stopPolling()
    setActiveTask(null)
    setRunning(false)
  }

  return { activeTask, running, runTask, clearTask }
}
