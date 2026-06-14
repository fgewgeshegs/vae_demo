import React, { useEffect, useState } from 'react'
import { Card, Timeline, Tag, Typography, Spin, Empty, Button, Progress, Space, message } from 'antd'
import { CheckCircleOutlined, ClockCircleOutlined, PlayCircleOutlined, BookOutlined, ReloadOutlined } from '@ant-design/icons'
import { studyPathApi, chatApi } from '../services/api'
import type { StudyPath } from '../types'

const { Title, Text } = Typography

const LearningPath: React.FC = () => {
  const [paths, setPaths] = useState<StudyPath[]>([])
  const [loading, setLoading] = useState(true)
  const [generating, setGenerating] = useState(false)

  useEffect(() => {
    const fetchPaths = async () => {
      try {
        const res = await studyPathApi.list()
        setPaths(res.data)
      } catch (err) {
        console.error('获取学习路径失败:', err)
      } finally {
        setLoading(false)
      }
    }
    fetchPaths()
  }, [])

  const handleGeneratePath = async () => {
    setGenerating(true)
    try {
      const res = await chatApi.send('帮我生成学习路径')
      message.success(res.data.message || '学习路径生成成功！')
      // 刷新路径列表
      const refreshed = await studyPathApi.list()
      setPaths(refreshed.data)
    } catch (err: unknown) {
      const errMsg = err instanceof Error ? err.message : '请稍后重试'
      message.error(`生成学习路径失败：${errMsg}`)
    } finally {
      setGenerating(false)
    }
  }

  if (loading) {
    return (
      <div style={{ textAlign: 'center', paddingTop: 100 }}>
        <Spin size="large" />
      </div>
    )
  }

  if (paths.length === 0) {
    return (
      <Empty description="暂无学习路径，点击下方按钮立即生成">
        <Button type="primary" onClick={handleGeneratePath} loading={generating} icon={<ReloadOutlined />}>
          {generating ? '正在生成...' : '生成学习路径'}
        </Button>
      </Empty>
    )
  }

  return (
    <div>
      <Title level={4}>
        <BookOutlined style={{ marginRight: 8 }} />
        学习路径
      </Title>

      {paths.map((path) => {
        const nodes = path.path_data?.nodes || []
        const currentIndex = path.path_data?.current_index || 0

        return (
          <Card key={path.id} style={{ marginTop: 16 }}>
            <div style={{ marginBottom: 16 }}>
              <Progress percent={Math.round(path.progress * 100)} />
              <Text type="secondary" style={{ marginTop: 8, display: 'block' }}>
                当前进度：第 {currentIndex + 1}/{nodes.length} 个节点
              </Text>
            </div>

            <Timeline
              items={nodes.map((node, index) => ({
                color:
                  node.status === 'completed'
                    ? 'green'
                    : node.status === 'in_progress'
                    ? 'blue'
                    : 'gray',
                dot:
                  node.status === 'completed' ? (
                    <CheckCircleOutlined />
                  ) : node.status === 'in_progress' ? (
                    <PlayCircleOutlined />
                  ) : (
                    <ClockCircleOutlined />
                  ),
                children: (
                  <div>
                    <Space>
                      <Text strong={index === currentIndex}>{node.title}</Text>
                      <Tag>{node.type === 'learn' ? '学习' : node.type === 'practice' ? '练习' : node.type === 'review' ? '复习' : '测试'}</Tag>
                      {node.status === 'completed' && <Tag color="success">已完成</Tag>}
                      {node.status === 'in_progress' && <Tag color="processing">进行中</Tag>}
                    </Space>
                    <br />
                    <Text type="secondary">预计 {node.estimated_minutes} 分钟</Text>
                  </div>
                ),
              }))}
            />
          </Card>
        )
      })}
    </div>
  )
}

export default LearningPath
