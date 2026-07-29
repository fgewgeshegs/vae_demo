import React, { useEffect, useState } from 'react'
import { Button, Card, Col, Empty, List, message, Progress, Row, Spin, Tag, Typography } from 'antd'
import { BarChartOutlined, ReloadOutlined } from '@ant-design/icons'
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import TaskProgress from '../components/TaskProgress'
import { evaluationApi } from '../services/api'
import { useTaskRunner } from '../hooks/useTaskRunner'
import type { Evaluation } from '../types'
import WorkspacePageHeader from '../components/WorkspacePageHeader'

const { Title, Text } = Typography

const scoreLabels: Record<string, string> = {
  knowledge_mastery: '知识掌握',
  learning_efficiency: '学习效率',
  engagement: '学习投入',
  consistency: '学习连续性',
  improvement: '进步幅度',
}

const scoreColors: Record<string, string> = {
  knowledge_mastery: '#1677ff',
  learning_efficiency: '#52c41a',
  engagement: '#faad14',
  consistency: '#ff4d4f',
  improvement: '#722ed1',
}

const averageScore = (scores: Record<string, number>) => {
  const values = Object.values(scores)
  return values.length ? Math.round(values.reduce((sum, value) => sum + value, 0) / values.length) : 0
}

const evaluationSource = (evaluation: Evaluation | null) => {
  const method = String(evaluation?.report_data?.method || '')
  if (method === 'llm') return { label: '智能分析', color: 'green' }
  if (method === 'rule_fallback') return { label: '学习记录', color: 'blue' }
  return { label: '近期学习记录', color: 'blue' }
}

const EvaluationPage: React.FC = () => {
  const [evaluations, setEvaluations] = useState<Evaluation[]>([])
  const [latest, setLatest] = useState<Evaluation | null>(null)
  const [loading, setLoading] = useState(true)
  const { activeTask, running, runTask, clearTask } = useTaskRunner()

  const fetchData = async () => {
    setLoading(true)
    try {
      const [listRes, latestRes] = await Promise.all([
        evaluationApi.list(),
        evaluationApi.latest().catch(() => null),
      ])
      setEvaluations(listRes.data)
      setLatest(latestRes?.data || null)
    } catch (err) {
      console.error('获取评估数据失败:', err)
      message.error('获取评估数据失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchData() }, [])

  const handleGenerate = async () => {
    await runTask('generate_evaluation', {
      successMessage: '评估 Agent 已生成新的学习报告',
      failureMessage: '评估生成失败，请稍后重试',
      onSuccess: fetchData,
    })
  }

  const trendData = evaluations.length > 1
    ? [...evaluations].reverse().map((item) => ({
      date: new Date(item.created_at).toLocaleDateString('zh-CN'),
      综合得分: averageScore(item.scores),
    }))
    : []

  if (loading) {
    return <div style={{ textAlign: 'center', paddingTop: 100 }}><Spin size="large" /></div>
  }

  return (
    <div className="workspace-page workspace-page--evaluation">
      <WorkspacePageHeader title="学习评估" description="基于近期学习行为，识别当前能力状态和下一步改进重点。" metrics={[{ label: '评估记录', value: evaluations.length }, { label: '当前得分', value: latest ? averageScore(latest.scores) : '—' }]} actions={<Button type="primary" icon={<ReloadOutlined />} loading={running} onClick={handleGenerate}>
          {running ? '评估 Agent 正在分析...' : 'Agent 生成新评估'}
        </Button>} />

      <TaskProgress task={activeTask} onClose={clearTask} />

      {!latest ? (
        <Card>
          <Empty description="暂无评估数据，点击生成新评估开始">
            <Button type="primary" loading={running} onClick={handleGenerate}>
              生成评估
            </Button>
          </Empty>
        </Card>
      ) : (
        <>
          <Card title="学习能力评分" style={{ marginBottom: 16 }}>
            <Row gutter={[16, 16]}>
              <Col xs={24} lg={16}>
                <Text type="secondary">根据近期学习行为生成。每项分数均有对应的学习证据，适合直接比较与跟进。</Text>
                <div style={{ marginTop: 24 }}>
                <div style={{ marginBottom: 12, textAlign: 'right' }}>
                  <Tag color={evaluationSource(latest).color}>
                    评估依据：{evaluationSource(latest).label}
                  </Tag>
                </div>
                {Object.entries(latest.scores).map(([key, value]) => (
                  <div key={key} style={{ marginBottom: 18 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                      <Text style={{ color: scoreColors[key] || '#1677ff' }}>
                        {scoreLabels[key] || key}
                      </Text>
                      <Text strong>{value}</Text>
                    </div>
                    <Progress
                      percent={Math.round(value)}
                      strokeWidth={10}
                      strokeColor={scoreColors[key] || '#1677ff'}
                      showInfo={false}
                    />
                  </div>
                ))}
                </div>
              </Col>
              <Col xs={24} lg={8}>
                <div style={{ background: '#EEF3FF', borderRadius: 12, padding: 24, textAlign: 'center' }}>
                  <Text type="secondary">综合评分</Text>
                  <div style={{ color: '#315EF7', fontSize: 40, fontWeight: 650, lineHeight: 1.2, margin: '10px 0' }}>{averageScore(latest.scores)}</div>
                  <Text type="secondary">目标分数 70</Text>
                </div>
              </Col>
            </Row>
          </Card>

          {trendData.length > 1 && (
            <Card title="综合得分趋势" style={{ marginBottom: 16 }}>
              <div style={{ width: '100%', height: 250 }}>
                <ResponsiveContainer>
                  <LineChart data={trendData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="date" />
                    <YAxis domain={[0, 100]} />
                    <Tooltip />
                    <Legend />
                    <Line type="monotone" dataKey="综合得分" stroke="#1677ff" strokeWidth={2} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </Card>
          )}

          {latest.suggestions?.length > 0 && (
            <Card title="改进建议" style={{ marginBottom: 16 }}>
              <List
                dataSource={latest.suggestions}
                renderItem={(suggestion, index) => (
                  <List.Item>
                    <Text>{index + 1}. {suggestion}</Text>
                  </List.Item>
                )}
              />
            </Card>
          )}

          {latest.strategy_signals && Object.keys(latest.strategy_signals).length > 0 && (
            <Card title="策略调整信号" style={{ marginBottom: 16 }}>
              <Row gutter={[16, 16]}>
                {Object.entries(latest.strategy_signals).map(([key, value]) => (
                  value ? <Col key={key}><Tag color="blue">{key}: {String(value)}</Tag></Col> : null
                ))}
              </Row>
            </Card>
          )}

          {evaluations.length > 1 && (
            <Card title="历史评估记录">
              <List
                dataSource={evaluations}
                renderItem={(item) => {
                  const avg = averageScore(item.scores)
                  return (
                    <List.Item>
                      <List.Item.Meta
                        title={`评估报告 #${item.id}`}
                        description={new Date(item.created_at).toLocaleString('zh-CN')}
                      />
                      <Tag color={avg >= 70 ? 'green' : avg >= 50 ? 'blue' : 'red'}>
                        综合 {avg}
                      </Tag>
                    </List.Item>
                  )
                }}
              />
            </Card>
          )}
        </>
      )}
    </div>
  )
}

export default EvaluationPage
