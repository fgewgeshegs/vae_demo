import React, { useEffect, useMemo, useState } from 'react'
import { Button, Card, Empty, Modal, Progress, Space, Spin, Tag, Tooltip, Typography } from 'antd'
import { EditOutlined, ExpandOutlined, FileTextOutlined, LeftOutlined, PlayCircleOutlined, RightOutlined } from '@ant-design/icons'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import type { KnowledgePoint, LearningResource, VideoTask } from '../types'
import { LearningResourceContent } from './ResourceModal'
import './ContentViewer.css'

const { Title, Text } = Typography

const resourceTypeLabels: Record<string, string> = {
  document: '讲义', mindmap: '思维导图', exercise: '练习题',
  code: '代码案例', reading: '拓展阅读', video: '教学脚本',
}

interface LearningStep {
  id: string
  label: string
  description: string
  resources: LearningResource[]
}

interface ContentViewerProps {
  kp: KnowledgePoint | null
  sectionNumber: string
  resources: LearningResource[]
  resourceLoading: boolean
  videoTasks: Record<number, VideoTask>
  activeVideo: { url: string; title: string } | null
  onOpenDetail: (resource: LearningResource) => void
  onGenerateVideo: (resource: LearningResource) => void
  onCloseVideo: () => void
}

const ContentViewer: React.FC<ContentViewerProps> = ({
  kp,
  sectionNumber,
  resources,
  resourceLoading,
  videoTasks,
  activeVideo,
  onOpenDetail,
  onGenerateVideo,
  onCloseVideo,
}) => {
  const [activeStepIndex, setActiveStepIndex] = useState(0)
  const steps = useMemo<LearningStep[]>(() => {
    const byType = (types: LearningResource['resource_type'][]) => resources.filter((resource) => types.includes(resource.resource_type))
    return [
      {
        id: 'understand',
        label: '概念理解',
        description: '先建立本节的核心概念、学习目标与关键边界。',
        resources: byType(['document']),
      },
      {
        id: 'example',
        label: '结构与示例',
        description: '借助结构图和讲解示例，形成对知识点的整体认识。',
        resources: byType(['mindmap', 'video']),
      },
      {
        id: 'apply',
        label: '应用与延伸',
        description: '将概念迁移到实际场景，并按需阅读扩展材料。',
        resources: byType(['code', 'reading']),
      },
      {
        id: 'practice',
        label: '练习与反馈',
        description: '通过练习检验掌握程度，并定位仍需巩固的内容。',
        resources: byType(['exercise']),
      },
    ]
  }, [resources])

  useEffect(() => { setActiveStepIndex(0) }, [kp?.id])

  if (!kp) {
    return <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%' }}><Empty description="请从左侧目录选择章节开始学习" /></div>
  }

  const safeStepIndex = Math.min(activeStepIndex, steps.length - 1)
  const activeStep = steps[safeStepIndex]
  const renderLearningMaterial = (resource: LearningResource) => (
    <section key={resource.id} className="learning-material">
      <div className="learning-material__header">
        <div>
          <Tag className="learning-material__type">{resourceTypeLabels[resource.resource_type] || resource.resource_type}</Tag>
          <Title level={5} className="learning-material__title">{resource.title}</Title>
        </div>
        <Tooltip title="在弹窗中打开">
          <Button type="text" icon={<ExpandOutlined />} aria-label={`在弹窗中打开：${resource.title}`} onClick={() => onOpenDetail(resource)} />
        </Tooltip>
      </div>
      <div className="learning-material__content"><LearningResourceContent resource={resource} /></div>
    </section>
  )
  const renderResource = (resource: LearningResource) => {
    const videoTask = videoTasks[resource.id]
    const isVideoCompleted = videoTask?.status === 'completed' && videoTask?.video_url
    const isVideoGenerating = videoTask?.status === 'queued' || videoTask?.status === 'processing'
    if (resource.resource_type === 'document') {
      return <Card key={resource.id} size="small" className="learning-step-resource" onClick={() => onOpenDetail(resource)} title={<Space size={4}><FileTextOutlined style={{ color: '#2563eb' }} /><Text strong style={{ fontSize: 13 }}>{resource.title}</Text><Tag color="blue" style={{ fontSize: 10 }}>讲义</Tag></Space>}>
        {resource.content ? <ReactMarkdown remarkPlugins={[remarkGfm]}>{resource.content.slice(0, 600)}</ReactMarkdown> : <Text type="secondary" style={{ fontSize: 12 }}>暂无内容</Text>}
      </Card>
    }
    if (resource.resource_type === 'exercise') {
      return <Card key={resource.id} size="small" className="learning-step-resource" style={{ borderColor: '#86efac' }} onClick={() => onOpenDetail(resource)}><Space size={4}><EditOutlined style={{ color: '#16a34a', fontSize: 12 }} /><Text style={{ fontSize: 13 }}>{resource.title}</Text><Tag color="green" style={{ fontSize: 10 }}>练习</Tag></Space></Card>
    }
    return <Card key={resource.id} size="small" className="learning-step-resource" onClick={() => onOpenDetail(resource)}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12 }}>
        <Space size={4}><FileTextOutlined style={{ color: '#64748b', fontSize: 12 }} /><Text style={{ fontSize: 13 }}>{resource.title}</Text><Tag style={{ fontSize: 10 }}>{resourceTypeLabels[resource.resource_type] || resource.resource_type}</Tag></Space>
        {resource.resource_type === 'video' && <div onClick={(event) => event.stopPropagation()}>{isVideoCompleted ? <Button icon={<PlayCircleOutlined />} size="small" type="primary" onClick={() => onGenerateVideo(resource)}>播放</Button> : isVideoGenerating ? <Progress type="circle" percent={videoTask?.progress || 0} size={20} /> : <Button icon={<PlayCircleOutlined />} size="small" onClick={() => onGenerateVideo(resource)}>生成视频</Button>}</div>}
      </div>
    </Card>
  }

  return (
    <div className="learning-step-viewer">
      <div className="learning-step-viewer__scroll">
        <div className="learning-step-viewer__content">
          <div style={{ marginBottom: 24 }}>
            <Title level={3} style={{ margin: 0 }}>{sectionNumber ? `${sectionNumber}：${kp.title}` : kp.title}</Title>
            <Space wrap style={{ marginTop: 8 }}><Tag color="blue">{kp.difficulty || 'medium'}</Tag></Space>
          </div>
          <Title level={4} style={{ marginBottom: 20 }}>{activeStep.label}</Title>
          <Text type="secondary" style={{ display: 'block', marginBottom: 20 }}>{activeStep.description}</Text>
          {resourceLoading ? <div style={{ textAlign: 'center', padding: 32 }}><Spin /></div> : activeStep.resources.length ? <div className="learning-step-resources">{activeStep.resources.map(renderLearningMaterial)}</div> : <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="本页资源正在准备中" />}
        </div>
      </div>

      <nav className="learning-step-pagination" aria-label="本节学习步骤">
        <Tooltip title="上一步"><Button type="text" className="learning-step-pagination__arrow" icon={<LeftOutlined />} aria-label="上一步" disabled={safeStepIndex === 0} onClick={() => setActiveStepIndex((index) => Math.max(0, index - 1))} /></Tooltip>
        <div className="learning-step-pagination__pages">
          {steps.map((step, index) => <Tooltip title={step.label} key={step.id}><Button className={`learning-step-pagination__page${index === safeStepIndex ? ' learning-step-pagination__page--active' : ''}`} shape="circle" aria-label={`第 ${index + 1} 步：${step.label}`} aria-current={index === safeStepIndex ? 'step' : undefined} onClick={() => setActiveStepIndex(index)}>{index + 1}</Button></Tooltip>)}
        </div>
        <Tooltip title="下一步"><Button type="text" className="learning-step-pagination__arrow" icon={<RightOutlined />} aria-label="下一步" disabled={safeStepIndex === steps.length - 1} onClick={() => setActiveStepIndex((index) => Math.min(steps.length - 1, index + 1))} /></Tooltip>
      </nav>

      {activeVideo && <Modal title={activeVideo.title} open={true} onCancel={onCloseVideo} footer={null} width={800} destroyOnClose><video controls autoPlay style={{ width: '100%', borderRadius: 8 }} src={activeVideo.url}>您的浏览器不支持视频播放</video></Modal>}
    </div>
  )
}

export default ContentViewer
