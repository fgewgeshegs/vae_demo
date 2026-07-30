import { useMemo, useState } from 'react'
import { Alert, Button, Card, Empty, Progress, Space, Steps, Tag, Typography } from 'antd'
import { CheckCircleOutlined, EditOutlined, ReadOutlined, ReloadOutlined } from '@ant-design/icons'
import type { LearningFeedback, LearningResource, LearningRun } from '../types'
import { learningRunApi } from '../services/api'

const { Paragraph, Text, Title } = Typography

const order = ['learn', 'practice', 'assess', 'feedback', 'review'] as const
const labels: Record<(typeof order)[number] | 'remedial', string> = {
  learn: '学习', practice: '练习', assess: '检测', feedback: '反馈', review: '复习', remedial: '补救',
}

type Props = {
  run: LearningRun
  feedback: LearningFeedback | null
  knowledgePointId?: number
  resources: LearningResource[]
  loading: boolean
  onRefresh: () => Promise<void>
  onFeedback: (feedback: LearningFeedback) => void
  onLoading: (loading: boolean) => void
}

export default function FiveStageLearningLoop({ run, feedback, knowledgePointId, resources, loading, onRefresh, onFeedback, onLoading }: Props) {
  const [assessmentCorrect, setAssessmentCorrect] = useState<boolean | null>(null)
  const current = run.current_stage === 'remedial' ? 1 : Math.max(0, order.indexOf(run.current_stage as (typeof order)[number]))
  const stage = run.current_stage
  const exercises = useMemo(() => resources.filter((item) => item.resource_type === 'exercise'), [resources])
  const learningMaterials = useMemo(() => resources.filter((item) => item.resource_type !== 'exercise').slice(0, 3), [resources])
  const canRecord = Boolean(knowledgePointId)

  const perform = async (action: () => Promise<unknown>) => {
    onLoading(true)
    try {
      await action()
      await onRefresh()
    } finally {
      onLoading(false)
    }
  }

  if (run.status === 'locked') {
    return <Alert type="warning" showIcon message="本章暂未解锁" description={run.lock_reason?.unlock_condition || '请先完成前置知识点。'} />
  }

  return (
    <Space direction="vertical" size={20} style={{ width: '100%' }}>
      <div>
        <Text type="secondary">本章五阶段闭环</Text>
        <Title level={4} style={{ margin: '4px 0 0' }}>按阶段完成，不用离开课程目录</Title>
      </div>
      <Steps current={current} size="small" items={order.map((item) => ({ title: labels[item], status: item === stage ? 'process' : order.indexOf(item) < current ? 'finish' : 'wait' }))} />

      {stage === 'learn' && (
        <Card size="small" title={<Space><ReadOutlined />学习材料</Space>}>
          <Paragraph type="secondary">阅读本节点的讲义或案例后，再进入练习。完成记录会保留为本阶段证据。</Paragraph>
          {learningMaterials.length ? learningMaterials.map((item) => <div key={item.id} style={{ marginBottom: 8 }}><Text strong>{item.title}</Text><Text type="secondary"> · {item.resource_type}</Text></div>) : <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="本节点暂无额外材料，可阅读页面中的知识点说明" />}
          <Button type="primary" loading={loading} onClick={() => perform(() => learningRunApi.completeLearning(run.id, { resource_count: learningMaterials.length }))}>完成学习，开始练习</Button>
        </Card>
      )}

      {(stage === 'practice' || stage === 'remedial') && (
        <Card size="small" title={<Space><EditOutlined />{stage === 'remedial' ? '补救练习' : '针对性练习'}</Space>}>
          <Paragraph type="secondary">练习记录不计总分，只记录尝试与是否查看解析。</Paragraph>
          {exercises.length ? exercises.map((item) => <Card key={item.id} size="small" style={{ marginBottom: 10 }} title={item.title}><Text type="secondary">{item.content?.slice(0, 160) || '打开资源查看练习题。'}</Text></Card>) : <Alert type="info" showIcon message="暂未匹配练习题" description="可先完成学习材料；后续资源服务将按知识点补充等价练习。" />}
          <Space wrap>
            <Button disabled={!canRecord} loading={loading} onClick={() => perform(() => learningRunApi.addPracticeAttempt(run.id, { knowledge_point_id: knowledgePointId!, is_correct: true }))}>记录一次正确尝试</Button>
            <Button disabled={!canRecord} loading={loading} onClick={() => perform(() => learningRunApi.addPracticeAttempt(run.id, { knowledge_point_id: knowledgePointId!, is_correct: false, viewed_explanation: true, misconception_tags: ['needs_review'] }))}>记录一次需解析的尝试</Button>
            <Button type="primary" loading={loading} onClick={() => perform(() => learningRunApi.completePractice(run.id, { practice_resources: exercises.length }))}>完成练习，进入检测</Button>
          </Space>
        </Card>
      )}

      {stage === 'assess' && (
        <Card size="small" title="知识点检测">
          <Paragraph type="secondary">检测结果会更新该知识点的掌握度；请基于一题未做过的等价题记录结果。</Paragraph>
          <Space wrap>
            <Button type={assessmentCorrect === true ? 'primary' : 'default'} onClick={() => setAssessmentCorrect(true)}>本题答对</Button>
            <Button danger={assessmentCorrect === false} onClick={() => setAssessmentCorrect(false)}>本题答错</Button>
            <Button type="primary" disabled={!canRecord || assessmentCorrect === null} loading={loading} onClick={() => perform(async () => {
              const result = await learningRunApi.submitAssessment(run.id, { submission_key: `equivalent-${Date.now()}`, items: [{ item_id: `equivalent-${Date.now()}`, knowledge_point_id: knowledgePointId!, is_correct: assessmentCorrect!, score: assessmentCorrect ? 1 : 0 }] })
              onFeedback(result.data)
            })}>提交检测结果</Button>
          </Space>
        </Card>
      )}

      {(stage === 'review' || stage === 'feedback' || feedback) && (
        <Card size="small" title={<Space><CheckCircleOutlined />学习反馈</Space>}>
          {feedback ? <>
            <Tag color={feedback.result === 'mastered' ? 'success' : 'gold'}>{feedback.result === 'mastered' ? '已达到掌握阈值' : '需要补救'}</Tag>
            <Paragraph style={{ marginTop: 12 }}>{feedback.next_action.reason}</Paragraph>
            {feedback.weak.map((item) => <Text key={item.knowledge_point_id} type="secondary" style={{ display: 'block' }}>薄弱知识点 #{item.knowledge_point_id}：{Math.round(item.mastery * 100)}%</Text>)}
          </> : <Button loading={loading} onClick={async () => { onLoading(true); try { const result = await learningRunApi.feedback(run.id); onFeedback(result.data) } finally { onLoading(false) } }}>查看反馈</Button>}
          {stage === 'review' && <Alert style={{ marginTop: 12 }} type="success" showIcon icon={<ReloadOutlined />} message="建议在后续复习时使用新的等价题复测，确认长期记忆。" />}
        </Card>
      )}
      <Progress percent={Math.round(((current + (stage === 'review' ? 1 : 0)) / order.length) * 100)} showInfo={false} />
    </Space>
  )
}
