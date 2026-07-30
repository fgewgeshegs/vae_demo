import React, { useEffect, useState } from 'react'
import { Button, Card, Empty, Input, message, Select, Space, Spin, Tag, Typography } from 'antd'
import { ArrowRightOutlined, FileTextOutlined, PlayCircleOutlined, RobotOutlined } from '@ant-design/icons'
import TaskProgress from '../components/TaskProgress'
import ResourceModal from '../components/ResourceModal'
import { resourceApi } from '../services/api'
import { useTaskRunner } from '../hooks/useTaskRunner'
import type { LearningResource } from '../types'
import WorkspacePageHeader from '../components/WorkspacePageHeader'

const { Paragraph, Title, Text } = Typography

const typeLabels: Record<string, string> = {
  document: '讲义',
  mindmap: '思维导图',
  exercise: '练习题',
  code: '代码案例',
  reading: '拓展阅读',
  video: '教学视频',
}

const resourceHints: Record<string, string> = {
  document: '点击查看课程讲义',
  mindmap: '点击查看可视化思维导图',
  exercise: '点击查看练习题',
  code: '点击查看代码案例',
  reading: '点击查看拓展阅读',
  video: '点击播放仿视频微课',
}

const resourceIcon = (type: LearningResource['resource_type']) =>
  type === 'video' ? <PlayCircleOutlined /> : <FileTextOutlined />

const ResourcesPage: React.FC = () => {
  const [resources, setResources] = useState<LearningResource[]>([])
  const [loading, setLoading] = useState(true)
  const [typeFilter, setTypeFilter] = useState<string>()
  const [request, setRequest] = useState('')
  const [selected, setSelected] = useState<LearningResource | null>(null)
  const [modalOpen, setModalOpen] = useState(false)
  const [modalLoading, setModalLoading] = useState(false)
  const { activeTask, running, runTask, clearTask } = useTaskRunner()

  const loadResources = async () => {
    setLoading(true)
    try {
      const res = await resourceApi.list(typeFilter ? { resource_type: typeFilter } : undefined)
      setResources(res.data)
    } catch {
      message.error('资源加载失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { loadResources() }, [typeFilter])

  const generate = async () => {
    if (!request.trim()) return
    await runTask('generate_learning_resource', {
      input: { request: request.trim() },
      successMessage: '资源生成成功',
      failureMessage: '资源生成失败',
      onSuccess: async () => {
        setRequest('')
        await loadResources()
      },
    })
  }

  const previewContent = (resource: LearningResource) => {
    return resourceHints[resource.resource_type] || '点击查看资源'
  }

  const openResource = async (resource: LearningResource) => {
    setSelected(resource)
    setModalOpen(true)
    setModalLoading(true)
    try {
      const res = await resourceApi.get(resource.id)
      setSelected(res.data)
    } catch {
      setSelected(resource)
    } finally {
      setModalLoading(false)
    }
  }

  return (
    <div className="workspace-page workspace-page--resources">
      <WorkspacePageHeader title="资源中心" description="集中管理学习资料，并由 Agent 按需生成新的内容。" metrics={[{ label: '当前资源', value: loading ? '加载中' : resources.length }]} />
      <Card style={{ marginBottom: 16 }} title={<Space><RobotOutlined />资源生成 Agent</Space>}>
        <Space.Compact style={{ width: '100%' }}>
          <Input
            value={request}
            onChange={(e) => setRequest(e.target.value)}
            onPressEnter={generate}
            placeholder="例如：生成一份 A* 算法练习题，并附答案解析"
          />
          <Button type="primary" loading={running} onClick={generate}>
            {running ? 'Agent 正在生成资源...' : '生成资源'}
          </Button>
        </Space.Compact>
        <TaskProgress task={activeTask} onClose={clearTask} />
      </Card>

      <Select
        allowClear
        placeholder="筛选资源类型"
        style={{ width: 180, marginBottom: 16 }}
        value={typeFilter}
        onChange={setTypeFilter}
        options={Object.entries(typeLabels).map(([value, label]) => ({ value, label }))}
      />

      {loading ? <div style={{ textAlign: 'center', padding: 80 }}><Spin size="large" /></div>
        : resources.length === 0 ? <Empty description="暂无学习资源，可以让 Agent 生成第一份资料" />
        : (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(250px, 1fr))', gap: 24 }}>
            {resources.map((resource) => {
              return (
                <Card
                  key={resource.id}
                  hoverable
                  onClick={() => openResource(resource)}
                  styles={{ body: { padding: 20, minHeight: 166, display: 'flex', flexDirection: 'column' } }}
                  style={{ height: '100%', borderColor: '#E3E8EF' }}
                >
                  <div style={{
                    alignItems: 'center',
                    background: resource.resource_type === 'video' ? '#F3F0FF' : '#EEF3FF',
                    borderRadius: 10,
                    color: resource.resource_type === 'video' ? '#7257D9' : '#315EF7',
                    display: 'flex',
                    fontSize: 24,
                    height: 48,
                    justifyContent: 'center',
                    flexShrink: 0,
                    width: 48,
                  }}>
                    {resourceIcon(resource.resource_type)}
                  </div>
                  <Paragraph strong ellipsis={{ rows: 2 }} style={{ color: '#172033', fontSize: 16, lineHeight: 1.45, margin: '14px 0 0' }}>
                    {resource.title}
                  </Paragraph>
                  <div style={{ alignItems: 'center', display: 'flex', gap: 8, marginTop: 'auto', paddingTop: 16 }}>
                    <Tag color={resource.resource_type === 'video' ? 'purple' : 'blue'} style={{ margin: 0 }}>{typeLabels[resource.resource_type]}</Tag>
                    <Text type="secondary" style={{ fontSize: 12 }}>{new Date(resource.created_at).toLocaleDateString('zh-CN')}</Text>
                  </div>
                  <div style={{ color: '#315EF7', fontSize: 13, fontWeight: 650, marginTop: 14 }}>
                    查看资源 <ArrowRightOutlined />
                  </div>
                </Card>
              )
            })}
          </div>
        )}
      <ResourceModal
        resource={selected}
        open={modalOpen}
        loading={modalLoading}
        onClose={() => {
          setModalOpen(false)
          setSelected(null)
        }}
      />
    </div>
  )
}

export default ResourcesPage
