import React, { useEffect, useState } from 'react'
import { Card, Row, Col, Typography, Spin, Empty, Tag, List, Progress } from 'antd'
import { BarChartOutlined } from '@ant-design/icons'
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

const EvaluationPage: React.FC = () => {
  const [evaluations, setEvaluations] = useState<Evaluation[]>([])
  const [latest, setLatest] = useState<Evaluation | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchData = async () => {
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
    fetchData()
  }, [])

  if (loading) {
    return (
      <div style={{ textAlign: 'center', paddingTop: 100 }}>
        <Spin size="large" />
      </div>
    )
  }

  if (!latest) {
    return <Empty description="暂无评估数据，完成更多学习后查看" />
  }

  return (
    <div>
      <Title level={4}>
        <BarChartOutlined style={{ marginRight: 8 }} />
        学习评估
      </Title>

      <Card title="最新评估概览">
        <Row gutter={[16, 16]}>
          {Object.entries(latest.scores).map(([key, value]) => (
            <Col xs={24} sm={12} lg={8} key={key}>
              <Card size="small">
                <Text>{scoreLabels[key] || key}</Text>
                <Progress
                  percent={Math.round(value)}
                  size="small"
                  strokeColor={
                    value >= 80 ? '#52c41a' : value >= 60 ? '#1677ff' : '#ff4d4f'
                  }
                />
              </Card>
            </Col>
          ))}
        </Row>
      </Card>

      {latest.suggestions?.length > 0 && (
        <Card title="改进建议" style={{ marginTop: 16 }}>
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

      {evaluations.length > 1 && (
        <Card title="历史评估" style={{ marginTop: 16 }}>
          <List
            dataSource={evaluations}
            renderItem={(evalItem) => (
              <List.Item>
                <List.Item.Meta
                  title={`评估报告 #${evalItem.id}`}
                  description={new Date(evalItem.created_at).toLocaleString('zh-CN')}
                />
                <Tag color="blue">
                  综合 {Math.round(Object.values(evalItem.scores).reduce((a, b) => a + b, 0) / Object.values(evalItem.scores).length)}
                </Tag>
              </List.Item>
            )}
          />
        </Card>
      )}
    </div>
  )
}

export default EvaluationPage
