import React, { useEffect, useMemo, useState } from 'react'
import { Button, Card, Empty, Modal, Progress, Space, Spin, Tag, Tooltip, Typography } from 'antd'
import { EditOutlined, FileTextOutlined, LeftOutlined, PlayCircleOutlined, RightOutlined } from '@ant-design/icons'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import type { KnowledgePoint, LearningResource, VideoTask } from '../types'
import './ContentViewer.css'

const { Title, Text, Paragraph } = Typography

const resourceTypeLabels: Record<string, string> = {
  document: '讲义', mindmap: '思维导图', exercise: '练习题',
  code: '代码案例', reading: '拓展阅读', video: '教学脚本',
}

interface LearningStep {
  id: string
  label: string
  resources: LearningResource[]
  includesLesson: boolean
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
    const result: LearningStep[] = [{ id: 'understand', label: '理解', resources: byType(['document']), includesLesson: true }]
    const exampleResources = byType(['video', 'mindmap'])
    const applyResources = byType(['code', 'reading'])
    const practiceResources = byType(['exercise'])
    if (exampleResources.length) result.push({ id: 'example', label: '示例', resources: exampleResources, includesLesson: false })
    if (applyResources.length) result.push({ id: 'apply', label: '应用', resources: applyResources, includesLesson: false })
    if (practiceResources.length) result.push({ id: 'practice', label: '练习', resources: practiceResources, includesLesson: false })
    return result
  }, [resources])

  useEffect(() => { setActiveStepIndex(0) }, [kp?.id])

  if (!kp) {
    return <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%' }}><Empty description="请从左侧目录选择章节开始学习" /></div>
  }

  const safeStepIndex = Math.min(activeStepIndex, steps.length - 1)
  const activeStep = steps[safeStepIndex]
  const renderLesson = () => kp.content ? (
    <div className="course-content" style={{ marginBottom: 24 }}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          h1: ({ children }) => <Title level={2} style={{ marginTop: 24 }}>{children}</Title>,
          h2: ({ children }) => <Title level={3} style={{ marginTop: 20 }}>{children}</Title>,
          h3: ({ children }) => <Title level={4} style={{ marginTop: 16 }}>{children}</Title>,
          p: ({ children }) => <Paragraph style={{ lineHeight: 1.8, fontSize: 15, color: '#334155' }}>{children}</Paragraph>,
          code: ({ className, children, ...props }: any) => !className ? <code style={{ background: '#f1f5f9', padding: '2px 6px', borderRadius: 4, fontSize: 13 }} {...props}>{children}</code> : <pre style={{ background: '#1e293b', color: '#e2e8f0', padding: '16px 20px', borderRadius: 8, overflowX: 'auto', fontSize: 13, lineHeight: 1.6 }}><code className={className} {...props}>{children}</code></pre>,
          img: ({ src, alt }) => <img src={src} alt={alt} style={{ maxWidth: '100%', borderRadius: 8, margin: '12px 0' }} />,
          table: ({ children }) => <div style={{ overflowX: 'auto' }}><table style={{ borderCollapse: 'collapse', width: '100%', margin: '12px 0' }}>{children}</table></div>,
          th: ({ children }) => <th style={{ border: '1px solid #e2e8f0', padding: '8px 12px', background: '#f8fafc', fontWeight: 600, fontSize: 13 }}>{children}</th>,
          td: ({ children }) => <td style={{ border: '1px solid #e2e8f0', padding: '8px 12px', fontSize: 13 }}>{children}</td>,
          blockquote: ({ children }) => <blockquote style={{ borderLeft: '3px solid #3b82f6', margin: '12px 0', padding: '8px 16px', background: '#f0f7ff', borderRadius: '0 6px 6px 0' }}>{children}</blockquote>,
        }}
      >
        {kp.content}
      </ReactMarkdown>
    </div>
  ) : <Paragraph type="secondary">暂无详细内容</Paragraph>

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
          {activeStep.includesLesson && renderLesson()}
          {resourceLoading ? <div style={{ textAlign: 'center', padding: 32 }}><Spin /></div> : activeStep.resources.length ? <div className="learning-step-resources">{activeStep.resources.map(renderResource)}</div> : !activeStep.includesLesson ? <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="本步骤暂无学习资源" /> : null}
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
