import React, { useEffect, useState } from 'react'
import { Row, Col, Card, Statistic, List, Typography, Tag, Spin, Empty, Progress } from 'antd'
import {
  BookOutlined,
  FileTextOutlined,
  QuestionCircleOutlined,
  BarChartOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
} from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { courseApi, evaluationApi, studyPathApi, qaApi } from '../services/api'
import type { Course, StudyPath, QARecord } from '../types'
import { useAuthStore } from '../store'

const { Title, Text } = Typography

const Dashboard: React.FC = () => {
  const navigate = useNavigate()
  const user = useAuthStore((s) => s.user)
  const [courses, setCourses] = useState<Course[]>([])
  const [paths, setPaths] = useState<StudyPath[]>([])
  const [recentQA, setRecentQA] = useState<QARecord[]>([])
  const [latestEval, setLatestEval] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [coursesRes, pathsRes, qaRes] = await Promise.all([
          courseApi.list(),
          studyPathApi.list(),
          qaApi.list(),
        ])
        setCourses(coursesRes.data)
        setPaths(pathsRes.data)
        setRecentQA(qaRes.data.slice(0, 5))

        try {
          const evalRes = await evaluationApi.latest()
          setLatestEval(evalRes.data)
        } catch {
          // 无评估数据
        }
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

  return (
    <div>
      <Title level={4} style={{ marginBottom: 16 }}>
        欢迎回来，{user?.display_name || user?.username} 👋
      </Title>

      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} lg={6}>
          <Card hoverable onClick={() => navigate('/courses')}>
            <Statistic title="课程数" value={courses.length} prefix={<BookOutlined />} />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card hoverable onClick={() => navigate('/resources')}>
            <Statistic title="学习资源" value={0} prefix={<FileTextOutlined />} />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card hoverable onClick={() => navigate('/qa')}>
            <Statistic title="问答次数" value={recentQA.length} prefix={<QuestionCircleOutlined />} />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card hoverable onClick={() => navigate('/evaluation')}>
            <Statistic title="学习评估" value={latestEval ? (latestEval.scores ? Object.keys(latestEval.scores).length : 1) : 0} suffix={latestEval ? "项" : ""} prefix={<BarChartOutlined />} />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} lg={12}>
          <Card title="学习路径" extra={<a onClick={() => navigate('/path')}>查看全部</a>}>
            {paths.length > 0 ? (
              <List
                dataSource={paths}
                renderItem={(path) => (
                  <List.Item>
                    <List.Item.Meta
                      title={path.path_data?.nodes?.[path.path_data.current_index]?.title || '学习中'}
                      description={
                        <Progress
                          percent={Math.round(path.progress * 100)}
                          size="small"
                          format={(p) => `${p}%`}
                        />
                      }
                    />
                    <Tag color={path.is_active ? 'blue' : 'default'}>
                      {path.is_active ? '进行中' : '已完成'}
                    </Tag>
                  </List.Item>
                )}
              />
            ) : (
              <Empty description="暂无学习路径，请先选择课程" />
            )}
          </Card>
        </Col>

        <Col xs={24} lg={12}>
          <Card title="最近问答" extra={<a onClick={() => navigate('/qa')}>去提问</a>}>
            {recentQA.length > 0 ? (
              <List
                dataSource={recentQA}
                renderItem={(item) => (
                  <List.Item>
                    <List.Item.Meta
                      title={
                        <Text ellipsis style={{ maxWidth: 300 }}>
                          {item.question}
                        </Text>
                      }
                      description={
                        <Text type="secondary" style={{ fontSize: 12 }}>
                          {new Date(item.created_at).toLocaleString('zh-CN')}
                        </Text>
                      }
                    />
                    {item.answer ? (
                      <CheckCircleOutlined style={{ color: '#52c41a' }} />
                    ) : (
                      <ClockCircleOutlined style={{ color: '#faad14' }} />
                    )}
                  </List.Item>
                )}
              />
            ) : (
              <Empty description="暂无问答记录" />
            )}
          </Card>
        </Col>
      </Row>
    </div>
  )
}

export default Dashboard
