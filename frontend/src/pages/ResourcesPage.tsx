import React, { useEffect, useState } from 'react'
import { Card, Row, Col, Tag, Typography, Spin, Empty, Select, Space } from 'antd'
import {
  FileTextOutlined,
  ApartmentOutlined,
  FormOutlined,
  CodeOutlined,
  ReadOutlined,
  VideoCameraOutlined,
} from '@ant-design/icons'
import { resourceApi } from '../services/api'
import type { LearningResource } from '../types'

const { Title, Text, Paragraph } = Typography

const resourceTypeConfig: Record<string, { label: string; icon: React.ReactNode; color: string }> = {
  document: { label: '讲义', icon: <FileTextOutlined />, color: 'blue' },
  mindmap: { label: '思维导图', icon: <ApartmentOutlined />, color: 'green' },
  exercise: { label: '练习题', icon: <FormOutlined />, color: 'orange' },
  code: { label: '代码案例', icon: <CodeOutlined />, color: 'purple' },
  reading: { label: '拓展阅读', icon: <ReadOutlined />, color: 'cyan' },
  video: { label: '教学动画', icon: <VideoCameraOutlined />, color: 'red' },
}

const ResourcesPage: React.FC = () => {
  const [resources, setResources] = useState<LearningResource[]>([])
  const [loading, setLoading] = useState(true)
  const [typeFilter, setTypeFilter] = useState<string>('')

  useEffect(() => {
    const fetchResources = async () => {
      try {
        const params: Record<string, string> = {}
        if (typeFilter) params.resource_type = typeFilter
        const res = await resourceApi.list(params)
        setResources(res.data)
      } catch {
        // 处理错误
      } finally {
        setLoading(false)
      }
    }
    fetchResources()
  }, [typeFilter])

  if (loading) {
    return (
      <div style={{ textAlign: 'center', paddingTop: 100 }}>
        <Spin size="large" />
      </div>
    )
  }

  return (
    <div>
      <Title level={4}>资源中心</Title>
      <Space style={{ marginBottom: 16 }}>
        <Select
          allowClear
          placeholder="筛选资源类型"
          style={{ width: 160 }}
          value={typeFilter || undefined}
          onChange={(val) => setTypeFilter(val || '')}
          options={Object.entries(resourceTypeConfig).map(([key, cfg]) => ({
            label: cfg.label,
            value: key,
          }))}
        />
      </Space>

      {resources.length === 0 ? (
        <Empty description="暂无学习资源" />
      ) : (
        <Row gutter={[16, 16]}>
          {resources.map((res) => {
            const cfg = resourceTypeConfig[res.resource_type] || resourceTypeConfig.document
            return (
              <Col xs={24} sm={12} lg={8} key={res.id}>
                <Card hoverable>
                  <Space>
                    <span style={{ fontSize: 24, color: cfg.color }}>{cfg.icon}</span>
                    <div>
                      <Text strong>{res.title}</Text>
                      <br />
                      <Tag color={cfg.color}>{cfg.label}</Tag>
                    </div>
                  </Space>
                  <Paragraph
                    ellipsis={{ rows: 3 }}
                    style={{ marginTop: 12, fontSize: 13, color: '#666' }}
                  >
                    {res.content || '暂无内容'}
                  </Paragraph>
                </Card>
              </Col>
            )
          })}
        </Row>
      )}
    </div>
  )
}

export default ResourcesPage
