import React, { useEffect, useMemo, useRef, useState } from 'react'
import {
  Button,
  Card,
  Col,
  Empty,
  List,
  message,
  Modal,
  Progress,
  Row,
  Space,
  Spin,
  Tag,
  Timeline,
  Tooltip,
  Typography,
} from 'antd'
import {
  BookOutlined,
  CheckCircleOutlined,
  EditOutlined,
  FileTextOutlined,
  PlayCircleOutlined,
  QuestionCircleOutlined,
  ReloadOutlined,
  RobotOutlined,
  ToolOutlined,
} from '@ant-design/icons'
import TaskProgress from '../components/TaskProgress'
import { chapterPlanApi, resourceApi, studyPathApi, videoApi } from '../services/api'
import type { VideoTask } from '../services/api'
import { useTaskRunner } from '../hooks/useTaskRunner'
import ResourceModal from '../components/ResourceModal'
import type { ChapterPlan, ChapterTask, LearningResource, StudyPath, StudyPathNode, TaskProgress as TaskProgressData } from '../types'
import WorkspacePageHeader from '../components/WorkspacePageHeader'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
const { Title, Text, Paragraph } = Typography

// ---- MCQ Parser ----
interface MCQQuestion {
  index: number
  stem: string
  options: { label: string; text: string }[]
  correctAnswer: string
  explanation: string
}

function parseExerciseMCQ(content: string): MCQQuestion[] {
  const questions: MCQQuestion[] = []
  const blocks = content.split(/(?=## 题目\s*\d+)/)
  for (const block of blocks) {
    const lines = block.split('\n')
    const stemParts: string[] = []
    const options: { label: string; text: string }[] = []
    let correctAnswer = ''
    let explanation = ''
    let inOptions = false

    for (const line of lines) {
      const trimmed = line.trim()
      if (!trimmed || trimmed.startsWith('#')) continue

      // Detect option line: A. xxx or A) xxx
      const optionMatch = trimmed.match(/^([A-D])[.、．)]\s*(.+)/)
      if (optionMatch) {
        inOptions = true
        options.push({ label: optionMatch[1], text: optionMatch[2].trim() })
        continue
      }

      // Detect answer line
      const answerMatch = trimmed.match(/^>\s*答案[：:]\s*([A-D])/)
      if (answerMatch) {
        correctAnswer = answerMatch[1]
        continue
      }

      // Detect explanation
      const explMatch = trimmed.match(/^>\s*解析[：:]\s*(.+)/)
      if (explMatch) {
        explanation = explMatch[1].trim()
        continue
      }

      // If we have options already, this is probably the next question's stem
      if (!inOptions && !trimmed.startsWith('>') && !trimmed.startsWith('---')) {
        stemParts.push(trimmed)
      }
    }

    if (options.length >= 2 && stemParts.length > 0) {
      questions.push({
        index: questions.length,
        stem: stemParts.join('\n').replace(/^\*\*|\*\*$/g, '').trim(),
        options,
        correctAnswer,
        explanation,
      })
    }
  }
  return questions
}

const nodeTypeLabels: Record<string, string> = {
  preview: '预览',
  learn: '学习',
  practice: '练习',
  review: '复习',
  exam: '测试',
}
const resourceTypeLabels: Record<string, string> = {
  document: '讲义',
  mindmap: '思维导图',
  exercise: '练习题',
  code: '代码案例',
  reading: '拓展阅读',
  video: '教学脚本',
}
const taskTypeLabels: Record<string, string> = {
  learn: '学习',
  practice: '练习',
  review: '复习',
  exam: '测试',
  read: '阅读',
  watch: '观看',
  quiz: '测验',
}
const taskTypeIcons: Record<string, React.ReactNode> = {
  learn: <BookOutlined />,
  practice: <ToolOutlined />,
  review: <ReloadOutlined />,
  exam: <CheckCircleOutlined />,
  read: <FileTextOutlined />,
  watch: <PlayCircleOutlined />,
  quiz: <QuestionCircleOutlined />,
}
const LearningPath: React.FC = () => {
  const [paths, setPaths] = useState<StudyPath[]>([])
  const [selectedNodeId, setSelectedNodeId] = useState<string>()
  const [resources, setResources] = useState<LearningResource[]>([])
  const [loading, setLoading] = useState(true)
  const [resourceLoading, setResourceLoading] = useState(false)
  // ---- chapter plan state ----
  const [chapterPlan, setChapterPlan] = useState<ChapterPlan | null>(null)
  const [currentTaskIndex, setCurrentTaskIndex] = useState(0)
  const [learningMode, setLearningMode] = useState(false)
  const [planCollapsed, setPlanCollapsed] = useState(false)
  const [taskProgress, setTaskProgress] = useState<Map<string, TaskProgressData>>(new Map())
  const [planLoading, setPlanLoading] = useState(false)
  // ---- resource detail modal ----
  const [detailResource, setDetailResource] = useState<LearningResource | null>(null)
  const [detailModalOpen, setDetailModalOpen] = useState(false)
  const [detailModalLoading, setDetailModalLoading] = useState(false)
  // ---- video generation state ----
  const [videoTasks, setVideoTasks] = useState<Record<number, VideoTask>>({})
  const [activeVideo, setActiveVideo] = useState<{ url: string; title: string } | null>(null)
  const pollRefs = useRef<Record<number, ReturnType<typeof setInterval>>>({})
  useEffect(() => {
    return () => { Object.values(pollRefs.current).forEach(clearInterval) }
  }, [])

  const { activeTask, running, runTask, clearTask } = useTaskRunner()
  const activePath = useMemo(() => {
    return paths.find((path) => path.is_active) || paths[0]
  }, [paths])
  const nodes = activePath?.path_data?.nodes || []
  const currentIndex = activePath?.path_data?.current_index || 0
  const selectedNode = useMemo(() => {
    return nodes.find((node) => node.id === selectedNodeId) || nodes[currentIndex] || nodes[0]
  }, [nodes, currentIndex, selectedNodeId])
  // current task derived from plan + index
  const currentTask = useMemo(() => {
    if (!chapterPlan) return null
    return chapterPlan.tasks[currentTaskIndex] || chapterPlan.tasks[0] || null
  }, [chapterPlan, currentTaskIndex])
  // resources filtered to current task's resource_types
  const currentTaskResources = useMemo(() => {
    if (!chapterPlan || !currentTask || !resources.length) return resources
    return resources.filter((r) => currentTask.resource_types.includes(r.resource_type))
  }, [resources, chapterPlan, currentTask])
  // Separate resources by type for layout
  const displayResources = chapterPlan && currentTask ? currentTaskResources : resources
  const lectureResources = useMemo(() => displayResources.filter(r => r.resource_type === 'document'), [displayResources])
  const exerciseResources = useMemo(() => displayResources.filter(r => r.resource_type === 'exercise'), [displayResources])
  const otherResources = useMemo(() => displayResources.filter(r => !['document', 'exercise'].includes(r.resource_type)), [displayResources])
  // Exercise selection state: resourceId -> questionIndex -> selectedOption
  const [exerciseAnswers, setExerciseAnswers] = useState<Record<number, Record<number, string>>>({})
  // Group nodes by chapter for hierarchical display
  const chapterGroups = useMemo(() => {
    const groups: { chapterTitle: string; nodes: StudyPathNode[] }[] = []
    const seen = new Set<string>()
    for (const node of nodes) {
      const key = node.chapter_title || '未分类'
      if (!seen.has(key)) {
        seen.add(key)
        groups.push({ chapterTitle: key, nodes: [] })
      }
      const g = groups.find((g) => g.chapterTitle === key)
      if (g) g.nodes.push(node)
    }
    return groups
  }, [nodes])
  const loadPaths = async () => {
    try {
      const res = await studyPathApi.list()
      const allPaths = res.data
      setPaths(allPaths)
      const path = allPaths.find((item) => item.is_active) || allPaths[0]
      const pathNodes = path?.path_data?.nodes || []
      setSelectedNodeId(pathNodes[path?.path_data?.current_index || 0]?.id || pathNodes[0]?.id)
    } catch {
      message.error('学习路径加载失败')
    } finally {
      setLoading(false)
    }
  }
  useEffect(() => { loadPaths() }, [])

  // load resources for selected node
  useEffect(() => {
    const loadNodeResources = async () => {
      if (!activePath || !selectedNode) {
        setResources([])
        return
      }
      if (!selectedNode.knowledge_point_id && !selectedNode.chapter_id) {
        setResources([])
        return
      }
      setResourceLoading(true)
      try {
        const res = await resourceApi.list({
          course_id: activePath.course_id,
          chapter_id: selectedNode.chapter_id || undefined,
          knowledge_point_id: selectedNode.knowledge_point_id,
        })
        setResources(res.data)
      } catch {
        message.error('节点资源加载失败')
      } finally {
        setResourceLoading(false)
      }
    }
    loadNodeResources()
  }, [activePath?.id, selectedNode?.id])
  // clear chapter plan and exercise selection when switching nodes
  useEffect(() => {
    setChapterPlan(null)
    setLearningMode(false)
    setPlanCollapsed(false)
    setExerciseAnswers({})
  }, [selectedNode?.id])

  const loadChapterPlan = async () => {
    const chapterId = selectedNode?.chapter_id
    if (!chapterId) return
    setPlanLoading(true)
    try {
      const [planRes, progressRes] = await Promise.all([
        chapterPlanApi.get(chapterId),
        chapterPlanApi.progress(chapterId).catch(() => ({ data: [] as TaskProgressData[] })),
      ])
      const plan = planRes.data
      setChapterPlan(plan)
      const progressList = progressRes.data || []
      const progressMap = new Map<string, TaskProgressData>()
      progressList.forEach((p) => progressMap.set(p.task_id, p))
      setTaskProgress(progressMap)
      const firstIncomplete = plan.tasks.findIndex(
        (t) => progressMap.get(t.task_id)?.status !== 'completed',
      )
      setCurrentTaskIndex(firstIncomplete >= 0 ? firstIncomplete : 0)
    } catch {
      message.error('章节学习计划加载失败')
      setChapterPlan(null)
    } finally {
      setPlanLoading(false)
    }
  }
  const generate = async () => {
    await runTask('generate_study_path', {
      input: { message: 'generate personalized study path' },
      successMessage: '学习路径生成成功',
      failureMessage: '学习路径生成失败',
      onSuccess: loadPaths,
    })
  }

  const completeNode = async (path: StudyPath, node: StudyPathNode) => {
    const nextNodes = [...(path.path_data?.nodes || [])]
    const nodeIndex = nextNodes.findIndex((item) => item.id === node.id)
    if (nodeIndex < 0) return
    nextNodes[nodeIndex] = {
      ...nextNodes[nodeIndex],
      status: 'completed',
      completed_at: new Date().toISOString(),
    }
    const firstUnfinishedIndex = nextNodes.findIndex((item) => item.status !== 'completed')
    const nextIndex = firstUnfinishedIndex >= 0 ? firstUnfinishedIndex : nextNodes.length
    if (nextIndex < nextNodes.length) {
      nextNodes[nextIndex] = { ...nextNodes[nextIndex], status: 'in_progress' }
    }
    try {
      await studyPathApi.update(path.id, {
        path_data: { ...path.path_data, nodes: nextNodes, current_index: nextIndex },
        progress: nextNodes.length ? nextNodes.filter((item) => item.status === 'completed').length / nextNodes.length : 0,
        is_active: nextIndex < nextNodes.length,
      })
      message.success(nextIndex < nextNodes.length ? '已完成该节点' : '恭喜完成整条学习路径')
      await loadPaths()
    } catch {
      message.error('更新学习进度失败')
    }
  }

  // ---- chapter task completion ----
  const completeChapterTask = async (taskId: string) => {
    if (!chapterPlan || !selectedNode?.chapter_id) return
    try {
      await chapterPlanApi.completeTask(selectedNode.chapter_id, taskId)
      const updatedProgress = new Map(taskProgress)
      updatedProgress.set(taskId, { task_id: taskId, status: 'completed' })
      setTaskProgress(updatedProgress)
      // advance to next unfinished task
      const nextUnfinished = chapterPlan.tasks.findIndex(
        (t, i) => i !== currentTaskIndex && updatedProgress.get(t.task_id)?.status !== 'completed',
      )
      if (nextUnfinished >= 0) {
        setCurrentTaskIndex(nextUnfinished)
        message.success('任务已完成，继续下一项')
      } else {
        message.success('恭喜完成本章所有学习任务！')
      }
    } catch {
      message.error('完成任务失败')
    }
  }
  const backToNodes = () => {
    setChapterPlan(null)
    setLearningMode(false)
    setPlanCollapsed(false)
  }

  const startLearning = async () => {
    if (!selectedNode) return
    setLearningMode(true)
    setPlanCollapsed(true)
    if (selectedNode.chapter_id && !chapterPlan) await loadChapterPlan()
  }

  const handleGenerateOrPlayVideo = async (resource: LearningResource) => {
    if (!activePath || !selectedNode) return

    // If already completed, play directly
    const existingTask = videoTasks[resource.id]
    if (existingTask?.status === 'completed' && existingTask.video_url) {
      setActiveVideo({ url: existingTask.video_url, title: resource.title })
      return
    }

    // Start generation
    setVideoTasks(prev => ({
      ...prev,
      [resource.id]: { task_id: '', status: 'queued', progress: 0, video_path: null, video_url: null, title: resource.title, error: null, created_at: new Date().toISOString() },
    }))

    try {
      const content = selectedNode.learning_content || resource.content || undefined
      const res = await videoApi.generate(
        selectedNode.knowledge_point_title || resource.title,
        selectedNode.knowledge_point_title || undefined,
        selectedNode.chapter_title || undefined,
        content,
        selectedNode.knowledge_point_id,
      )
      const { task_id, video_url } = res.data

      if (video_url) {
        // Cached - complete immediately
        setVideoTasks(prev => ({
          ...prev,
          [resource.id]: { task_id, status: 'completed', progress: 100, video_path: null, video_url, title: resource.title, error: null, created_at: new Date().toISOString(), completed_at: new Date().toISOString() },
        }))
        setActiveVideo({ url: video_url, title: resource.title })
        message.success('视频已就绪')
        return
      }

      // Poll for completion
      pollRefs.current[resource.id] = setInterval(async () => {
        try {
          const statusRes = await videoApi.status(task_id)
          const task = statusRes.data
          setVideoTasks(prev => ({ ...prev, [resource.id]: task }))
          if (task.status === 'completed') {
            clearInterval(pollRefs.current[resource.id])
            delete pollRefs.current[resource.id]
            message.success('视频生成完成')
            if (task.video_url) {
              setActiveVideo({ url: task.video_url, title: resource.title })
            }
          } else if (task.status === 'failed') {
            clearInterval(pollRefs.current[resource.id])
            delete pollRefs.current[resource.id]
            message.error('视频生成失败：' + (task.error || '未知错误'))
          }
        } catch {
          clearInterval(pollRefs.current[resource.id])
          delete pollRefs.current[resource.id]
        }
      }, 3000)
    } catch {
      message.error('视频生成请求失败')
      setVideoTasks(prev => ({
        ...prev,
        [resource.id]: { task_id: '', status: 'failed', progress: 0, video_path: null, video_url: null, title: resource.title, error: '生成请求失败', created_at: new Date().toISOString() },
      }))
    }
  }

  const openDetailModal = async (resource: LearningResource) => {
    setDetailResource(resource)
    setDetailModalOpen(true)
    setDetailModalLoading(true)
    try {
      const fullRes = await resourceApi.get(resource.id)
      setDetailResource(fullRes.data)
    } catch {
      setDetailResource(resource)
    } finally {
      setDetailModalLoading(false)
    }
  }
  if (loading) {
    return <div style={{ textAlign: 'center', paddingTop: 100 }}><Spin size="large" /></div>
  }

  return (
    <div className="workspace-page workspace-page--learning-path">
      <WorkspacePageHeader title="学习路径" description="按当前课程与进度组织学习任务，专注完成下一项可执行任务。" metrics={[{ label: '路径进度', value: activePath ? `${Math.round((activePath.progress || 0) * 100)}%` : '未生成' }, { label: '任务节点', value: nodes.length }]} actions={<Button type="primary" icon={<RobotOutlined />} loading={running} onClick={generate}>
          {running ? 'Agent 正在执行...' : activePath ? '重新规划路径' : '生成学习路径'}
        </Button>} />
      <TaskProgress task={activeTask} onClose={clearTask} />

      {!activePath ? (
        <Empty style={{ marginTop: 80 }} description="暂无学习路径" />
      ) : (
        <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
          {/* ===== Left Panel ===== */}
          {(!learningMode || !planCollapsed) && <Col xs={24} lg={learningMode ? 9 : 24}>
            <Card className={learningMode ? 'learning-plan-panel' : 'learning-plan-panel learning-plan-panel--overview'}>
              {chapterPlan ? (
                <PlanTaskFlow
                  chapterPlan={chapterPlan}
                  taskProgress={taskProgress}
                  currentTaskIndex={currentTaskIndex}
                  planLoading={planLoading}
                  onBack={backToNodes}
                  onSelectTask={setCurrentTaskIndex}
                />
              ) : (
                <Space direction="vertical" size={12} style={{ width: '100%' }}>
                  <div>
                    <Text strong>{activePath.path_data?.course_title || '当前课程'}</Text>
                    {paths.length > 1 && (
                      <Text type="secondary" style={{ marginLeft: 8 }}>
                        已隐藏 {paths.length - 1} 条历史路径
                      </Text>
                    )}
                  </div>
                  <Progress percent={Math.round((activePath.progress || 0) * 100)} />
                  <Text type="secondary">
                    当前进度：第 {Math.min(currentIndex + 1, nodes.length)}/{nodes.length} 个节点
                  </Text>
                  {activePath.path_data?.strategies_applied && activePath.path_data.strategies_applied.length > 0 && (
                    <div style={{ marginTop: 8 }}>
                      <Text type="secondary" style={{ fontSize: 12 }}>学习策略：</Text>
                      <div style={{ marginTop: 4 }}>
                        {activePath.path_data.strategies_applied.map((strategy, index) => (
                          <Tag key={index} color="blue" style={{ marginBottom: 4 }}>
                            {strategy === 'spaced_repetition' && '间隔重复'}
                            {strategy === 'feynman_technique' && '费曼学习法'}
                            {strategy === 'active_recall' && '主动回忆'}
                            {strategy === 'interleaving' && '交错练习'}
                            {strategy === 'dual_coding' && '双重编码'}
                            {strategy === 'elaboration' && '精细加工'}
                          </Tag>
                        ))}
                      </div>
                    </div>
                  )}
                  {chapterGroups.map((group) => (
                    <div key={group.chapterTitle} style={{ marginBottom: 16 }}>
                      <div style={{ padding: '6px 0 4px', borderBottom: '1px solid #e2e8f0', marginBottom: 4, display: 'flex', alignItems: 'center', gap: 6 }}>
                        <BookOutlined style={{ fontSize: 12, color: '#64748b' }} />
                        <Text style={{ fontSize: 11, fontWeight: 600, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                          {group.chapterTitle}
                        </Text>
                        <Text type="secondary" style={{ fontSize: 11 }}>({group.nodes.length} 项)</Text>
                      </div>
                      <Timeline
                        items={group.nodes.map((node) => ({
                          color: node.status === 'completed' ? 'green' : selectedNode?.id === node.id ? 'blue' : node.type === 'preview' ? 'orange' : 'gray',
                          children: (
                            <div role="button" tabIndex={0} className={`learning-plan-node ${selectedNode?.id === node.id ? 'is-selected' : ''}`} onClick={() => setSelectedNodeId(node.id)}
                              style={{
                                width: '100%', border: 0,
                                background: selectedNode?.id === node.id ? 'rgba(65, 105, 225, 0.10)' : 'transparent',
                                cursor: 'pointer', padding: '6px 8px', textAlign: 'left', borderRadius: 8,
                              }}
                            >
                              <Space direction="vertical" size={3}>
                                <Text strong={selectedNode?.id === node.id} style={{ fontSize: 13, color: selectedNode?.id === node.id ? '#2563eb' : '#334155' }}>
                                  {node.title}
                                </Text>
                                <Space wrap>
                                  <Tag style={{ fontSize: 11, lineHeight: '18px' }} color={node.type === 'preview' ? 'orange' : undefined}>
                                    {nodeTypeLabels[node.type] || node.type}
                                  </Tag>
                                  <Text type="secondary" style={{ fontSize: 12 }}>{node.estimated_minutes} 分钟</Text>
                                </Space>
                                {selectedNode?.id === node.id && node.status !== 'completed' && (
                                  <Button type="primary" size="small" className="learning-plan-start-button" onClick={(event) => { event.stopPropagation(); void startLearning() }}>
                                    {node.status === 'in_progress' ? '继续学习' : '开始学习'}
                                  </Button>
                                )}
                              </Space>
                            </div>
                          ),
                        }))}
                      />
                    </div>
                  ))}
                </Space>
              )}
            </Card>
          </Col>}
          {/* ===== Right Panel ===== */}
          {learningMode && <Col xs={24} lg={planCollapsed ? 24 : 15}>
            <Card>
              <div className="learning-plan-study-toolbar">
                <Button type="link" className="learning-plan-back" onClick={() => setLearningMode(false)}>← 返回学习计划</Button>
                <Button size="small" onClick={() => setPlanCollapsed((value) => !value)}>{planCollapsed ? '显示目录' : '收起目录'}</Button>
              </div>
              {chapterPlan && currentTask ? (
                <PlanTaskDetail
                  task={currentTask}
                  taskProgress={taskProgress}
                  resourceLoading={resourceLoading}
                  resources={currentTaskResources}
                  onComplete={completeChapterTask}
                  onGenerateVideo={handleGenerateOrPlayVideo}
                  videoTasks={videoTasks}
                  setActiveVideo={setActiveVideo}
                  selectedNode={selectedNode}
                  onOpenDetail={openDetailModal}
                />
              ) : selectedNode ? (
                <Space direction="vertical" size={16} style={{ width: '100%' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', gap: 16 }}>
                    <div>
                      <Title level={5} style={{ margin: 0 }}>{selectedNode.title}</Title>
                      <Space wrap style={{ marginTop: 8 }}>
                        <Tag>{nodeTypeLabels[selectedNode.type] || selectedNode.type}</Tag>
                        {selectedNode.difficulty && <Tag color="blue">{selectedNode.difficulty}</Tag>}
                        <Text type="secondary">{selectedNode.estimated_minutes} 分钟</Text>
                      </Space>
                    </div>
                    <Space>
                      {selectedNode.chapter_id && (
                        <Button
                          icon={<BookOutlined />}
                          loading={planLoading}
                          onClick={loadChapterPlan}
                        >
                          查看学习计划
                        </Button>
                      )}
                      {selectedNode.status !== 'completed' && (
                        <Button
                          icon={<CheckCircleOutlined />}
                          onClick={() => completeNode(activePath, selectedNode)}
                        >
                          完成学习
                        </Button>
                      )}
                    </Space>
                  </div>
                  {/* ---- 学习内容 ---- */}
                  <div>
                    <Text strong style={{ fontSize: 14 }}>学习内容</Text>

                    {/* 讲义 */}
                    {lectureResources.length > 0 ? (
                      <div style={{ marginTop: 12 }}>
                        {lectureResources.map((resource) => (
                          <Card
                            key={resource.id}
                            size="small"
                            style={{ marginBottom: 12, cursor: 'pointer' }}
                            onClick={() => openDetailModal(resource)}
                            title={
                              <Space size={4}>
                                <FileTextOutlined style={{ color: '#2563eb' }} />
                                <Text strong style={{ fontSize: 13 }}>{resource.title}</Text>
                                <Tag color="blue" style={{ fontSize: 10, lineHeight: '16px', marginLeft: 4 }}>讲义</Tag>
                              </Space>
                            }
                          >
                            {resource.content ? (
                              <ReactMarkdown
                                remarkPlugins={[remarkGfm]}
                                components={{
                                  p: ({children}) => <span style={{ display: 'block', marginBottom: 4, color: '#334155', lineHeight: 1.8, fontSize: 13 }}>{children}</span>,
                                  h3: ({children}) => <Text strong style={{ display: 'block', marginTop: 8, marginBottom: 4, fontSize: 14 }}>{children}</Text>,
                                  li: ({children}) => <li style={{ marginBottom: 2, color: '#475569', fontSize: 13, lineHeight: 1.6 }}>{children}</li>,
                                }}
                              >
                                {resource.content.slice(0, 1500)}
                              </ReactMarkdown>
                            ) : (
                              <Text type="secondary" style={{ fontSize: 13 }}>暂无讲义内容</Text>
                            )}
                          </Card>
                        ))}
                      </div>
                    ) : selectedNode.learning_content ? (
                      <div style={{ marginTop: 12, padding: '12px 16px', background: '#f8fafc', borderRadius: 8, border: '1px solid #e2e8f0' }}>
                        <ReactMarkdown
                          remarkPlugins={[remarkGfm]}
                          components={{
                            p: ({children}) => <span style={{ display: 'block', marginBottom: 4, color: '#334155', lineHeight: 1.8, fontSize: 13 }}>{children}</span>,
                          }}
                        >
                          {selectedNode.learning_content}
                        </ReactMarkdown>
                      </div>
                    ) : (
                      <div style={{ marginTop: 12 }}>
                        <Text type="secondary" style={{ fontSize: 13 }}>该节点暂未写入知识点内容，请先检查课程知识点内容是否已导入。</Text>
                      </div>
                    )}

                    {/* 练习题 */}
                    {exerciseResources.length > 0 ? (
                      <div style={{ marginTop: 20 }}>
                        <Text strong style={{ fontSize: 13, color: '#64748b' }}>练习题</Text>
                        <div style={{ marginTop: 8 }}>
                          {exerciseResources.map((resource) => {
                            const questions = parseExerciseMCQ(resource.content || '')
                            const resourceAnswers = exerciseAnswers[resource.id] || {}
                            const answeredCount = Object.keys(resourceAnswers).length
                            const correctCount = questions.filter(q => resourceAnswers[q.index] === q.correctAnswer).length
                            return (
                              <Card key={resource.id} size="small" style={{ marginBottom: 16 }}
                                title={
                                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                    <Space size={4}>
                                      <EditOutlined style={{ color: '#16a34a', fontSize: 13 }} />
                                      <Text strong style={{ fontSize: 13 }}>{resource.title}</Text>
                                      <Tag color="green" style={{ fontSize: 10, lineHeight: '16px' }}>练习</Tag>
                                    </Space>
                                    {questions.length > 0 && (
                                      <Text type="secondary" style={{ fontSize: 11 }}>
                                        {answeredCount}/{questions.length} 完成
                                        {answeredCount > 0 && ` · 正确 ${correctCount}/${answeredCount}`}
                                      </Text>
                                    )}
                                  </div>
                                }
                              >
                                {questions.length === 0 ? (
                                  <Text type="secondary" style={{ fontSize: 12 }}>暂无选择题</Text>
                                ) : (
                                  <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                                    {questions.map((q) => {
                                      const selectedOption = resourceAnswers[q.index]
                                      const isAnswered = !!selectedOption
                                      const isCorrect = selectedOption === q.correctAnswer
                                      return (
                                        <div key={q.index} style={{ padding: '10px 12px', background: '#fafbfc', borderRadius: 8, border: '1px solid #e8ecf0' }}>
                                          <Text strong style={{ fontSize: 12, color: '#475569' }}>
                                            第{q.index + 1}题 · {q.stem.slice(0, 80)}{q.stem.length > 80 ? '...' : ''}
                                          </Text>
                                          <div style={{ marginTop: 8, display: 'flex', flexDirection: 'column', gap: 4 }}>
                                            {q.options.map((opt) => {
                                              let bg = '#fff'
                                              let border = '#e2e8f0'
                                              let textColor = '#334155'
                                              if (isAnswered) {
                                                if (opt.label === q.correctAnswer) {
                                                  bg = '#f0fdf4'; border = '#86efac'; textColor = '#166534'
                                                } else if (selectedOption === opt.label && !isCorrect) {
                                                  bg = '#fef2f2'; border = '#fca5a5'; textColor = '#991b1b'
                                                }
                                              }
                                              return (
                                                <div
                                                  key={opt.label}
                                                  onClick={() => {
                                                    if (isAnswered) return
                                                    setExerciseAnswers(prev => ({
                                                      ...prev,
                                                      [resource.id]: { ...(prev[resource.id] || {}), [q.index]: opt.label },
                                                    }))
                                                  }}
                                                  style={{
                                                    padding: '6px 10px', borderRadius: 6, border: `1px solid ${border}`,
                                                    background: bg, cursor: isAnswered ? 'default' : 'pointer',
                                                    display: 'flex', alignItems: 'center', gap: 8,
                                                    transition: 'all 0.15s',
                                                    opacity: isAnswered && opt.label !== selectedOption && opt.label !== q.correctAnswer ? 0.6 : 1,
                                                  }}
                                                >
                                                  <span style={{
                                                    width: 22, height: 22, borderRadius: '50%',
                                                    border: `2px solid ${isAnswered ? (opt.label === q.correctAnswer ? '#16a34a' : selectedOption === opt.label ? '#dc2626' : '#cbd5e1') : '#cbd5e1'}`,
                                                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                                                    fontWeight: 700, fontSize: 11, flexShrink: 0,
                                                    color: textColor,
                                                  }}>
                                                    {opt.label}
                                                  </span>
                                                  <Text style={{ fontSize: 12, color: textColor, lineHeight: 1.5 }}>{opt.text}</Text>
                                                  {isAnswered && opt.label === q.correctAnswer && (
                                                    <CheckCircleOutlined style={{ color: '#16a34a', marginLeft: 'auto', fontSize: 13 }} />
                                                  )}
                                                  {isAnswered && selectedOption === opt.label && !isCorrect && (
                                                    <span style={{ color: '#dc2626', fontSize: 11, marginLeft: 'auto' }}>✗</span>
                                                  )}
                                                </div>
                                              )
                                            })}
                                          </div>
                                          {isAnswered && q.explanation && (
                                            <div style={{ marginTop: 8, padding: '6px 10px', background: '#eff6ff', borderRadius: 6, border: '1px solid #bfdbfe' }}>
                                              <Text style={{ fontSize: 11, color: '#1e40af' }}>
                                                {isCorrect ? '✓ 正确！' : `✗ 正确答案是 ${q.correctAnswer}`} {q.explanation}
                                              </Text>
                                            </div>
                                          )}
                                        </div>
                                      )
                                    })}
                                  </div>
                                )}
                              </Card>
                            )
                          })}
                        </div>
                      </div>
                    ) : null}
                  </div>

                  {/* ---- 学习资源 ---- */}
                  {resourceLoading ? (
                    <div style={{ padding: 32, textAlign: 'center' }}><Spin /></div>
                  ) : otherResources.length > 0 ? (
                    <div>
                      <Text strong style={{ fontSize: 14 }}>学习资源</Text>
                      <List
                        style={{ marginTop: 8 }}
                        dataSource={otherResources}
                        split={false}
                        renderItem={(resource) => {
                          const videoTask = videoTasks[resource.id]
                          const isVideoCompleted = videoTask?.status === 'completed' && videoTask?.video_url
                          const isVideoGenerating = videoTask?.status === 'queued' || videoTask?.status === 'processing'
                          const isVideoFailed = videoTask?.status === 'failed'
                          return (
                            <List.Item
                              style={{ padding: '10px 0', borderBottom: '1px solid #f0f0f0', cursor: 'pointer' }}
                              onClick={() => openDetailModal(resource)}
                            >
                              <div style={{ width: '100%', minWidth: 0, display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 8 }}>
                                <Space size={4}>
                                  <FileTextOutlined style={{ color: '#64748b', fontSize: 12 }} />
                                  <Text style={{ fontSize: 13 }}>{resource.title}</Text>
                                  <Tag style={{ fontSize: 10, lineHeight: '16px', margin: 0 }}>
                                    {resourceTypeLabels[resource.resource_type] || resource.resource_type}
                                  </Tag>
                                </Space>
                                {resource.resource_type === 'video' && (
                                  <div style={{ flexShrink: 0 }} onClick={(e) => e.stopPropagation()}>
                                    {isVideoCompleted ? (
                                      <Button icon={<PlayCircleOutlined />} size="small" type="primary"
                                        onClick={() => setActiveVideo({ url: videoTask!.video_url!, title: resource.title })}>
                                        播放
                                      </Button>
                                    ) : isVideoFailed ? (
                                      <Tooltip title={videoTask?.error || '生成失败'}>
                                        <Button size="small" danger onClick={() => handleGenerateOrPlayVideo(resource)}>重试</Button>
                                      </Tooltip>
                                    ) : isVideoGenerating ? (
                                      <Progress type="circle" percent={videoTask?.progress || 0} size={20} style={{ margin: 0 }} />
                                    ) : (
                                      <Button icon={<PlayCircleOutlined />} size="small"
                                        onClick={() => handleGenerateOrPlayVideo(resource)}>生成视频</Button>
                                    )}
                                  </div>
                                )}
                              </div>
                            </List.Item>
                          )
                        }}
                      />
                    </div>
                  ) : resources.length === 0 && !resourceLoading ? (
                    <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="该节点暂无已保存资源" />
                  ) : null}
                </Space>
              ) : (
                <Empty description="请选择一个学习节点" />
              )}
            </Card>
          </Col>}
        </Row>
      )}
      <ResourceModal
        resource={detailResource}
        open={detailModalOpen}
        loading={detailModalLoading}
        onClose={() => {
          setDetailModalOpen(false)
          setDetailResource(null)
        }}
      />
      {activeVideo && (
        <Modal
          title={activeVideo.title}
          open={true}
          onCancel={() => setActiveVideo(null)}
          footer={null}
          width={800}
          destroyOnClose
        >
          <video controls autoPlay style={{ width: '100%', borderRadius: 8 }} src={activeVideo.url}>
            您的浏览器不支持视频播放
          </video>
        </Modal>
      )}
    </div>
  )
}

// ============================================================
// Sub-component: left-panel task flow
// ============================================================
const PlanTaskFlow: React.FC<{
  chapterPlan: ChapterPlan
  taskProgress: Map<string, TaskProgressData>
  currentTaskIndex: number
  planLoading: boolean
  onBack: () => void
  onSelectTask: (index: number) => void
}> = ({ chapterPlan, taskProgress, currentTaskIndex, planLoading, onBack, onSelectTask }) => {
  if (planLoading) {
    return <div style={{ textAlign: 'center', padding: 40 }}><Spin /></div>
  }
  const completedCount = chapterPlan.tasks.filter(
    (t) => taskProgress.get(t.task_id)?.status === 'completed',
  ).length
  const progressPercent = Math.round((completedCount / chapterPlan.tasks.length) * 100)
  return (
    <Space direction="vertical" size={12} style={{ width: '100%' }}>
      {/* header row */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Text strong style={{ fontSize: 15 }}>学习计划</Text>
        <Button size="small" type="text" icon={<FileTextOutlined />} onClick={onBack}>
          返回节点
        </Button>
      </div>
      {chapterPlan.description && (
        <Text type="secondary" style={{ fontSize: 13 }}>{chapterPlan.description}</Text>
      )}
      {/* summary bar */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Text type="secondary" style={{ fontSize: 12 }}>
          共 {chapterPlan.tasks.length} 项 · 约 {chapterPlan.estimated_total_minutes} 分钟
        </Text>
        <Text type="secondary" style={{ fontSize: 12 }}>
          {completedCount}/{chapterPlan.tasks.length} 完成
        </Text>
      </div>
      <Progress percent={progressPercent} size="small" />
      {/* task list */}
      <div style={{ marginTop: 4 }}>
        {chapterPlan.tasks.map((task, index) => {
          const isCompleted = taskProgress.get(task.task_id)?.status === 'completed'
          const isCurrent = index === currentTaskIndex
          return (
            <div
              key={task.task_id}
              onClick={() => onSelectTask(index)}
              style={{
                padding: '10px 12px',
                marginBottom: 8,
                borderRadius: 8,
                cursor: 'pointer',
                background: isCurrent ? 'rgba(65, 105, 225, 0.08)' : 'transparent',
                border: isCurrent ? '1px solid rgba(65, 105, 225, 0.25)' : '1px solid transparent',
                transition: 'all 0.2s',
              }}
            >
              {/* title row */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Space>
                  {isCompleted ? (
                    <CheckCircleOutlined style={{ color: '#52c41a' }} />
                  ) : isCurrent ? (
                    <BookOutlined style={{ color: 'var(--accent-indigo)' }} />
                  ) : (
                    <span
                      style={{
                        width: 14,
                        height: 14,
                        borderRadius: '50%',
                        border: '2px solid #d9d9d9',
                        display: 'inline-block',
                      }}
                    />
                  )}
                  <Text
                    strong={isCurrent}
                    style={{ color: isCurrent ? 'var(--accent-indigo)' : undefined, fontSize: 13 }}
                  >
                    {task.title}
                  </Text>
                </Space>
                {isCompleted && (
                  <Text style={{ color: '#52c41a', fontSize: 12 }}>已完成</Text>
                )}
              </div>
              {/* meta row */}
              <Space size={6} style={{ marginTop: 6, marginLeft: 22 }}>
                <Tag style={{ fontSize: 11, lineHeight: '18px' }}>
                  {taskTypeLabels[task.task_type] || task.task_type}
                </Tag>
                <Text type="secondary" style={{ fontSize: 12 }}>{task.estimated_minutes} 分钟</Text>
                {task.resource_types.map((rt) => (
                  <Tag key={rt} color="purple" style={{ fontSize: 11, lineHeight: '18px' }}>
                    {resourceTypeLabels[rt] || rt}
                  </Tag>
                ))}
              </Space>
            </div>
          )
        })}
      </div>
    </Space>
  )
}
// ============================================================
// Sub-component: right-panel current-task detail + filtered resources
// ============================================================
const PlanTaskDetail: React.FC<{
  task: ChapterTask
  taskProgress: Map<string, TaskProgressData>
  resourceLoading: boolean
  resources: LearningResource[]
  onComplete: (taskId: string) => void
  onGenerateVideo: (resource: LearningResource) => void
  videoTasks: Record<number, VideoTask>
  setActiveVideo: (v: { url: string; title: string } | null) => void
  selectedNode: StudyPathNode | null
  onOpenDetail: (resource: LearningResource) => void
}> = ({ task, taskProgress, resourceLoading, resources, onComplete, onGenerateVideo, videoTasks, setActiveVideo, selectedNode, onOpenDetail }) => {
  const isCompleted = taskProgress.get(task.task_id)?.status === 'completed'
  return (
    <Space direction="vertical" size={16} style={{ width: '100%' }}>
      {/* header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 16 }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            {taskTypeIcons[task.task_type] || <FileTextOutlined />}
            <Title level={5} style={{ margin: 0 }}>{task.title}</Title>
          </div>
          <Space wrap style={{ marginTop: 8 }}>
            <Tag>{taskTypeLabels[task.task_type] || task.task_type}</Tag>
            {task.difficulty && <Tag color="blue">{task.difficulty}</Tag>}
            <Text type="secondary">{task.estimated_minutes} 分钟</Text>
          </Space>
        </div>
        {!isCompleted ? (
          <Button
            type="primary"
            icon={<CheckCircleOutlined />}
            onClick={() => onComplete(task.task_id)}
          >
            完成任务
          </Button>
        ) : (
          <Tag icon={<CheckCircleOutlined />} color="success">已完成</Tag>
        )}
      </div>
      {/* description */}
      {task.description && (
        <div>
          <Text strong>任务说明</Text>
          <Paragraph style={{ whiteSpace: 'pre-wrap', marginTop: 8, color: '#64748b' }}>
            {task.description}
          </Paragraph>
        </div>
      )}
      {/* filtered resources */}
      {resourceLoading ? (
        <div style={{ padding: 32, textAlign: 'center' }}><Spin /></div>
      ) : resources.length ? (
        <>
          {/* 讲义 */}
          {resources.filter(r => r.resource_type === 'document').map(resource => (
            <Card
              key={resource.id}
              size="small"
              style={{ marginBottom: 10, cursor: 'pointer' }}
              onClick={() => onOpenDetail(resource)}
              title={
                <Space size={4}>
                  <FileTextOutlined style={{ color: '#2563eb' }} />
                  <Text strong style={{ fontSize: 13 }}>{resource.title}</Text>
                  <Tag color="blue" style={{ fontSize: 10, lineHeight: '16px' }}>讲义</Tag>
                </Space>
              }
            >
              {resource.content ? (
                <ReactMarkdown
                  remarkPlugins={[remarkGfm]}
                  components={{
                    p: ({children}) => <span style={{ display: 'block', marginBottom: 4, color: '#334155', lineHeight: 1.7, fontSize: 13 }}>{children}</span>,
                  }}
                >
                  {resource.content.slice(0, 800)}
                </ReactMarkdown>
              ) : (
                <Text type="secondary" style={{ fontSize: 12 }}>暂无内容</Text>
              )}
            </Card>
          ))}
          {/* 练习题 */}
          {resources.filter(r => r.resource_type === 'exercise').length > 0 && (
            <div style={{ marginBottom: 10 }}>
              <Text strong style={{ fontSize: 13, color: '#64748b' }}>练习题 · 点击进入答题</Text>
              {resources.filter(r => r.resource_type === 'exercise').map(resource => (
                <Card key={resource.id} size="small" style={{ marginTop: 8, marginBottom: 6, cursor: 'pointer', borderColor: '#86efac' }}
                  onClick={() => onOpenDetail(resource)}>
                  <Space size={4}>
                    <EditOutlined style={{ color: '#16a34a', fontSize: 12 }} />
                    <Text style={{ fontSize: 13 }}>{resource.title}</Text>
                    <Tag color="green" style={{ fontSize: 10, lineHeight: '16px' }}>练习</Tag>
                    <Text type="secondary" style={{ fontSize: 10, marginLeft: 'auto' }}>点击答题 →</Text>
                  </Space>
                </Card>
              ))}
            </div>
          )}
          {/* 其他资源 */}
          {resources.filter(r => !['document', 'exercise'].includes(r.resource_type)).length > 0 && (
            <div>
              <Text strong style={{ fontSize: 13, color: '#64748b' }}>学习资源</Text>
              <List
                style={{ marginTop: 6 }}
                dataSource={resources.filter(r => !['document', 'exercise'].includes(r.resource_type))}
                split={false}
                renderItem={(resource) => {
                  const videoTask = videoTasks[resource.id]
                  const isVideoCompleted = videoTask?.status === 'completed' && videoTask?.video_url
                  const isVideoGenerating = videoTask?.status === 'queued' || videoTask?.status === 'processing'
                  return (
                    <List.Item
                      style={{ padding: '8px 0', borderBottom: '1px solid #f0f0f0', cursor: 'pointer' }}
                      onClick={() => onOpenDetail(resource)}
                    >
                      <div style={{ width: '100%', display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 8 }}>
                        <Space size={4}>
                          <FileTextOutlined style={{ color: '#64748b', fontSize: 12 }} />
                          <Text style={{ fontSize: 13 }}>{resource.title}</Text>
                          <Tag style={{ fontSize: 10, lineHeight: '16px', margin: 0 }}>
                            {resourceTypeLabels[resource.resource_type] || resource.resource_type}
                          </Tag>
                        </Space>
                        {resource.resource_type === 'video' && (
                          <div style={{ flexShrink: 0 }} onClick={(e) => e.stopPropagation()}>
                            {isVideoCompleted ? (
                              <Button icon={<PlayCircleOutlined />} size="small" type="primary"
                                onClick={() => setActiveVideo({ url: videoTask!.video_url!, title: resource.title })}>播放</Button>
                            ) : isVideoGenerating ? (
                              <Progress type="circle" percent={videoTask?.progress || 0} size={20} style={{ margin: 0 }} />
                            ) : (
                              <Button icon={<PlayCircleOutlined />} size="small"
                                onClick={() => onGenerateVideo(resource)}>生成视频</Button>
                            )}
                          </div>
                        )}
                      </div>
                    </List.Item>
                  )
                }}
              />
            </div>
          )}
        </>
      ) : (
        <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="该任务暂无可用资源" />
      )}
    </Space>
  )
}

export default LearningPath

