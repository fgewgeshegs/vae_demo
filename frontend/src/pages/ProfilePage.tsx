import React, { useEffect, useState } from 'react'
import { Card, Descriptions, Tag, Spin, Empty, Typography, Row, Col, Divider } from 'antd'
import {
  RadarChartOutlined,
  UserOutlined,
  AimOutlined,
  ThunderboltOutlined,
  HeartOutlined,
} from '@ant-design/icons'
import { profileApi } from '../services/api'
import type { StudentProfile } from '../types'

const { Title, Text } = Typography

const ProfilePage: React.FC = () => {
  const [profile, setProfile] = useState<StudentProfile | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchProfile = async () => {
      try {
        const res = await profileApi.get()
        setProfile(res.data)
      } catch {
        // 处理错误
      } finally {
        setLoading(false)
      }
    }
    fetchProfile()
  }, [])

  if (loading) {
    return (
      <div style={{ textAlign: 'center', paddingTop: 100 }}>
        <Spin size="large" />
      </div>
    )
  }

  if (!profile) {
    return <Empty description="暂无画像数据" />
  }

  const pd = profile.profile_data

  return (
    <div>
      <Title level={4}>
        <UserOutlined style={{ marginRight: 8 }} />
        学习画像
      </Title>
      <Text type="secondary">
        通过对话自动构建，版本 {profile.version} · 最后更新 {new Date(profile.updated_at).toLocaleString('zh-CN')}
      </Text>

      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} lg={12}>
          <Card title={<><AimOutlined /> 知识基础</>}>
            <Descriptions column={1} size="small">
              <Descriptions.Item label="水平">
                <Tag color="blue">{((pd.knowledge_base?.level as string) || '未知')}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="熟悉领域">
                {(pd.knowledge_base?.subjects as string[] || []).join('、') || '暂无'}
              </Descriptions.Item>
            </Descriptions>
          </Card>
        </Col>

        <Col xs={24} lg={12}>
          <Card title={<><RadarChartOutlined /> 认知风格</>}>
            <Descriptions column={1} size="small">
              <Descriptions.Item label="偏好">
                <Tag color="purple">{((pd.cognitive_style?.preference as string) || '未知')}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="描述">{((pd.cognitive_style?.description as string) || '暂无')}</Descriptions.Item>
            </Descriptions>
          </Card>
        </Col>

        <Col xs={24} lg={12}>
          <Card title={<><ThunderboltOutlined /> 学习目标</>}>
            <Descriptions column={1} size="small">
              <Descriptions.Item label="短期">{((pd.learning_goals?.short_term as string) || '未设置')}</Descriptions.Item>
              <Descriptions.Item label="长期">{((pd.learning_goals?.long_term as string) || '未设置')}</Descriptions.Item>
            </Descriptions>
          </Card>
        </Col>

        <Col xs={24} lg={12}>
          <Card title={<><HeartOutlined /> 兴趣方向</>}>
            <Descriptions column={1} size="small">
              <Descriptions.Item label="感兴趣的领域">
                {(pd.interest_direction?.areas as string[] || []).length > 0
                  ? (pd.interest_direction?.areas as string[]).map((a) => <Tag key={a}>{a}</Tag>)
                  : '暂无'}
              </Descriptions.Item>
            </Descriptions>
          </Card>
        </Col>
      </Row>

      {(pd.knowledge_gaps as string[] || []).length > 0 && (
        <Card title="知识短板" style={{ marginTop: 16 }}>
          {(pd.knowledge_gaps as string[]).map((gap, i) => (
            <Tag key={i} color="orange" style={{ marginBottom: 4 }}>{gap}</Tag>
          ))}
        </Card>
      )}

      {(pd.weak_points as string[] || []).length > 0 && (
        <Card title="易错点" style={{ marginTop: 16 }}>
          {(pd.weak_points as string[]).map((wp, i) => (
            <Tag key={i} color="red" style={{ marginBottom: 4 }}>{wp}</Tag>
          ))}
        </Card>
      )}
    </div>
  )
}

export default ProfilePage

