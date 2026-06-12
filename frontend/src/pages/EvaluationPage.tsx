import React, { useEffect, useState } from 'react'
import {
  Card, Row, Col, Typography, Spin, Empty, Tag, List, Button, Progress,
} from 'antd'
import {
  BarChartOutlined, ReloadOutlined,
} from '@ant-design/icons'
import {
  RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
  Radar, ResponsiveContainer, Tooltip, Legend,
  LineChart, Line, XAxis, YAxis, CartesianGrid,
} from 'recharts'
import { evaluationApi } from '../services/api'
import type { Evaluation } from '../types'

const { Title, Text } = Typography

const scoreLabels: Record<string, string> = {
  knowledge_mastery: '知识掌握',
  learning_efficiency: '学习效率',
  engagement: '学习投入',
  consistency: '学习连贯性',
  improvement: '进步幅度',
}

const scoreColors: Record<string, string> = {
  knowledge_mastery: '#1677ff',
  learning_efficiency: '#52c41a',
  engagement: '#faad14',
  consistency: '#ff4d4f',
  improvement: '#722ed1',
}

const EvaluationPage: React.FC = () => {
  const [evaluations, setEvaluations] = useState<Evaluation[]>([])
  const [latest, setLatest] = useState<Evaluation | null>(null)
  const [loading, setLoading] = useState(true)
  const [generating, setGenerating] = useState(false)

  const fetchData = async () => {
    setLoading(true)
    try {
      const [listRes, latestRes] = await Promise.all([
        evaluationApi.list(),
        evaluationApi.latest().catch(() => null),
      ])
      setEvaluations(listRes.data)
      if (latestRes) setLatest(latestRes.data)
    } catch {
      // 处理错误
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [])

  const handleGenerate = async () => {
    setGenerating(true)
    try {
      await evaluationApi.generate()
      await fetchData()
    } catch {
      // 处理错误
    } finally {
      setGenerating(false)
    }
  }

  // 准备雷达图数据
  const radarData = latest
    ? Object.entries(latest.scores).map(([key, value]) => ({
      dimension: scoreLabels[key] || key,
      当前得分: value,
      fullMark: 100,
    }))
    : []

  // 准备趋势图数据
  const trendData = evaluations.length > 1
    ? [...evaluations].reverse().map((evalItem) => {
      const scores = evalItem.scores
      const avg = Object.values(scores).length > 0
        ? Math.round(Object.values(scores).reduce((a, b) => a + b, 0) / Object.values(scores).length)
        : 0
      return {
        date: new Date(evalItem.created_at).toLocaleDateString('zh-CN'),
        综合得分: avg,
      }
    })
    : []

  if (loading) {
    return (
      <div style={{ textAlign: 'center', paddingTop: 100 }}>
        <Spin size="large" />
      </div>
    )
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}>
          <BarChartOutlined style={{ marginRight: 8 }} />
          学习评估
        </Title>
        <Button
          type="primary"
          icon={<ReloadOutlined />}
          loading={generating}
          onClick={handleGenerate}
        >
          生成新评估
        </Button>
      </div>

      {!latest ? (
        <Card>
          <Empty
            description="暂无评估数据，点击「生成新评估」开始"
          >
            <Button type="primary" loading={generating} onClick={handleGenerate}>
              生成评估
            </Button>
          </Empty>
        </Card>
      ) : (
        <>
          {/* 雷达图 */}
          <Card title="多维度评估雷达图" style={{ marginBottom: 16 }}>
            <Row gutter={[16, 16]}>
              <Col xs={24} lg={14}>
                <div style={{ width: '100%', height: 320 }}>
                  <ResponsiveContainer>
                    <RadarChart data={radarData}>
                      <PolarGrid />
                      <PolarAngleAxis dataKey="dimension" />
                      <PolarRadiusAxis angle={30} domain={[0, 100]} />
                      <Radar
                        name="当前得分"
                        dataKey="当前得分"
                        stroke="#1677ff"
                        fill="#1677ff"
                        fillOpacity={0.3}
                      />
                      <Tooltip />
                    </RadarChart>
                  </ResponsiveContainer>
                </div>
              </Col>
              <Col xs={24} lg={10}>
                {Object.entries(latest.scores).map(([key, value]) => (
                  <div key={key} style={{ marginBottom: 12 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                      <Text style={{ color: scoreColors[key] || '#1677ff' }}>
                        {scoreLabels[key] || key}
                      </Text>
                      <Text strong>{value}</Text>
                    </div>
                    <Progress
                      percent={Math.round(value)}
                      size="small"
                      strokeColor={scoreColors[key] || '#1677ff'}
                      showInfo={false}
                    />
                  </div>
                ))}
                <div style={{ marginTop: 16, textAlign: 'center' }}>
                  <Text type="secondary">
                    综合评分：
                  </Text>
                  <Text strong style={{ fontSize: 24, color: '#1677ff' }}>
                    {Math.round(
                      Object.values(latest.scores).reduce((a, b) => a + b, 0) /
                      Object.values(latest.scores).length
                    )}
                  </Text>
                </div>
              </Col>
            </Row>
          </Card>

          {/* 趋势图 */}
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
                    <Line
                      type="monotone"
                      dataKey="综合得分"
                      stroke="#1677ff"
                      strokeWidth={2}
                      dot={{ fill: '#1677ff' }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </Card>
          )}

          {/* 改进建议 */}
          {latest.suggestions?.length > 0 && (
            <Card title="改进建议" style={{ marginBottom: 16 }}>
              <List
                dataSource={latest.suggestions}
                renderItem={(suggestion, i) => (
                  <List.Item>
                    <Text>{i + 1}. {suggestion}</Text>
                  </List.Item>
                )}
              />
            </Card>
          )}

          {/* 策略信号 */}
          {latest.strategy_signals && Object.keys(latest.strategy_signals).length > 0 && (
            <Card title="策略调整信号" style={{ marginBottom: 16 }}>
              <Row gutter={[16, 16]}>
                {(latest.strategy_signals as Record<string, boolean|string>).adjust_pace && (
                  <Col>
                    <Tag color="orange">🔄 建议调整学习节奏</Tag>
                  </Col>
                )}
                {(latest.strategy_signals as Record<string, boolean|string>).review_suggested && (
                  <Col>
                    <Tag color="blue">📖 建议安排复习</Tag>
                  </Col>
                )}
                {(latest.strategy_signals as Record<string, string>).difficulty_change === 'easier' && (
                  <Col>
                    <Tag color="green">📚 建议降低难度</Tag>
                  </Col>
                )}
                {(latest.strategy_signals as Record<string, string>).difficulty_change === 'harder' && (
                  <Col>
                    <Tag color="purple">🚀 可以挑战更高难度</Tag>
                  </Col>
                )}
                {(latest.strategy_signals as Record<string, boolean>).feynman_suggested && (
                  <Col>
                    <Tag color="cyan">🎓 尝试费曼学习法</Tag>
                  </Col>
                )}
                {(latest.strategy_signals as Record<string, boolean>).recall_suggested && (
                  <Col>
                    <Tag color="geekblue">🧠 尝试主动回忆</Tag>
                  </Col>
                )}
              </Row>
            </Card>
          )}

          {/* 历史评估 */}
          {evaluations.length > 1 && (
            <Card title="历史评估记录">
              <List
                dataSource={evaluations}
                renderItem={(evalItem) => {
                  const scores = evalItem.scores
                  const avg = Object.values(scores).length > 0
                    ? Math.round(Object.values(scores).reduce((a, b) => a + b, 0) / Object.values(scores).length)
                    : 0
                  return (
                    <List.Item>
                      <List.Item.Meta
                        title={`评估报告 #${evalItem.id}`}
                        description={new Date(evalItem.created_at).toLocaleString('zh-CN')}
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
