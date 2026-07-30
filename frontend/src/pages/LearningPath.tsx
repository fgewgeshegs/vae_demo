import React, { useEffect, useMemo, useRef, useState } from 'react'
import {
  Button,
  Spin,
  message,
  Tooltip,
} from 'antd'
import {
  MenuOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  RobotOutlined,
} from '@ant-design/icons'
import WorkspacePageHeader from '../components/WorkspacePageHeader'
import CourseDrawer from '../components/CourseDrawer'
import ContentViewer from '../components/ContentViewer'
import AITutorPanel from '../components/AITutorPanel'
import ResourceModal from '../components/ResourceModal'
import { chapterApi, knowledgePointApi, resourceApi, studyPathApi, videoApi } from '../services/api'
import type { Chapter, KnowledgePoint, LearningResource, StudyPath } from '../types'
import type { VideoTask } from '../services/api'
import { useTaskRunner } from '../hooks/useTaskRunner'
import TaskProgress from '../components/TaskProgress'
import '../components/CourseDrawer.css'

const LearningPath: React.FC = () => {
  // ---- Path state ----
  const [paths, setPaths] = useState<StudyPath[]>([])
  const [loading, setLoading] = useState(true)
  const { activeTask, running, runTask, clearTask } = useTaskRunner()

  // ---- Chapter / KP state ----
  const [activeChapterId, setActiveChapterId] = useState<number | null>(null)
  const [activeKpId, setActiveKpId] = useState<number | null>(null)
  const [currentKp, setCurrentKp] = useState<KnowledgePoint | null>(null)
  const [courseChapters, setCourseChapters] = useState<Chapter[]>([])

  // ---- Drawer state ----
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [tutorCollapsed, setTutorCollapsed] = useState(false)

  // ---- Resource state ----
  const [resources, setResources] = useState<LearningResource[]>([])
  const [resourceLoading, setResourceLoading] = useState(false)

  // ---- Resource modal ----
  const [detailResource, setDetailResource] = useState<LearningResource | null>(null)
  const [detailModalOpen, setDetailModalOpen] = useState(false)
  const [detailModalLoading, setDetailModalLoading] = useState(false)

  // ---- Video state ----
  const [videoTasks, setVideoTasks] = useState<Record<number, VideoTask>>({})
  const [activeVideo, setActiveVideo] = useState<{ url: string; title: string } | null>(null)
  const pollRefs = useRef<Record<number, ReturnType<typeof setInterval>>>({})

  useEffect(() => {
    return () => { Object.values(pollRefs.current).forEach(clearInterval) }
  }, [])

  // ---- Derived ----
  const activePath = useMemo(() => {
    return paths.find((path) => path.is_active) || paths[0]
  }, [paths])
  const courseId = activePath?.course_id || 0
  const chapterTitle = useMemo(() => {
    if (!activeChapterId) return ''
    const nodes = activePath?.path_data?.nodes || []
    const node = nodes.find((n) => n.chapter_id === activeChapterId)
    return node?.chapter_title || ''
  }, [activeChapterId, activePath])
  const kpTitle = currentKp?.title || ''
  const sectionNumber = useMemo(() => {
    if (!activeChapterId || !activeKpId) return ''
    const chapters = [...courseChapters].sort((a, b) => a.sort_order - b.sort_order)
    const chapterIndex = chapters.findIndex((chapter) => chapter.id === activeChapterId)
    const chapter = chapters[chapterIndex]
    const points = [...(chapter?.knowledge_points || [])].sort((a, b) => a.sort_order - b.sort_order)
    const pointIndex = points.findIndex((point) => point.id === activeKpId)
    return chapterIndex >= 0 && pointIndex >= 0 ? `${chapterIndex + 1}-${pointIndex + 1}` : ''
  }, [activeChapterId, activeKpId, courseChapters])

  // ---- Load paths ----
  const loadPaths = async () => {
    try {
      const res = await studyPathApi.list()
      const allPaths = res.data
      setPaths(allPaths)
      const path = allPaths.find((item) => item.is_active) || allPaths[0]
      const nodes = path?.path_data?.nodes || []
      const currentNode = nodes[path?.path_data?.current_index || 0] || nodes[0]
      if (currentNode?.chapter_id) {
        setActiveChapterId(currentNode.chapter_id)
        if (currentNode.knowledge_point_id) {
          setActiveKpId(currentNode.knowledge_point_id)
        }
      }
    } catch {
      message.error('学习路径加载失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { loadPaths() }, [])

  useEffect(() => {
    if (!courseId) {
      setCourseChapters([])
      return
    }
    chapterApi.listByCourse(courseId)
      .then((res) => setCourseChapters(Array.isArray(res.data) ? res.data : []))
      .catch(() => setCourseChapters([]))
  }, [courseId])

  // ---- Load KP when selected ----
  useEffect(() => {
    if (!activeKpId) return
    knowledgePointApi.get(activeKpId)
      .then((res) => setCurrentKp(res.data))
      .catch(() => message.error('知识点加载失败'))
  }, [activeKpId])

  // ---- Load resources for current KP ----
  useEffect(() => {
    if (!activeKpId || !activePath) {
      setResources([])
      return
    }
    setResourceLoading(true)
    resourceApi.list({ knowledge_point_id: activeKpId })
      .then((res) => setResources(Array.isArray(res.data) ? res.data : []))
      .catch(() => { /* silently fallback */ })
      .finally(() => setResourceLoading(false))
  }, [activeKpId, activePath?.id])

  // ---- Handlers ----
  const handleSelectChapter = (chapterId: number) => {
    setActiveChapterId(chapterId)
    // Select first KP of this chapter
    knowledgePointApi.listByChapter(chapterId)
      .then((res) => {
        const kps = Array.isArray(res.data) ? res.data : []
        if (kps.length > 0) {
          setActiveKpId(kps[0].id)
        } else {
          setActiveKpId(null)
          setCurrentKp(null)
        }
      })
      .catch(() => message.error('知识点加载失败'))
  }

  const handleSelectKp = (chapterId: number, kpId: number) => {
    setActiveChapterId(chapterId)
    setActiveKpId(kpId)
  }

  const handleOpenDetail = async (resource: LearningResource) => {
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

  const handleGenerateOrPlayVideo = async (resource: LearningResource) => {
    if (!activePath) return
    const existingTask = videoTasks[resource.id]
    if (existingTask?.status === 'completed' && existingTask.video_url) {
      setActiveVideo({ url: existingTask.video_url, title: resource.title })
      return
    }
    setVideoTasks((prev) => ({
      ...prev,
      [resource.id]: {
        task_id: '',
        status: 'queued',
        progress: 0,
        video_path: null,
        video_url: null,
        title: resource.title,
        error: null,
        created_at: new Date().toISOString(),
      },
    }))
    try {
      const content = currentKp?.content || resource.content || undefined
      const res = await videoApi.generate(
        kpTitle || resource.title,
        kpTitle || undefined,
        chapterTitle || undefined,
        content,
      )
      const taskId = res.data?.task_id || ''
      setVideoTasks((prev) => ({
        ...prev,
        [resource.id]: { ...prev[resource.id], task_id: taskId, status: 'processing' },
      }))
      // Poll for completion
      pollRefs.current[resource.id] = setInterval(async () => {
        try {
          const statusRes = await videoApi.get(taskId)
          const task = statusRes.data
          setVideoTasks((prev) => ({
            ...prev,
            [resource.id]: { ...prev[resource.id], ...task },
          }))
          if (task.status === 'completed' || task.status === 'failed') {
            clearInterval(pollRefs.current[resource.id])
            if (task.status === 'completed') {
              setActiveVideo({ url: task.video_url!, title: resource.title })
            }
          }
        } catch {
          clearInterval(pollRefs.current[resource.id])
        }
      }, 3000)
    } catch {
      message.error('视频生成失败')
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

  if (loading) {
    return <div style={{ textAlign: 'center', paddingTop: 100 }}><Spin size="large" /></div>
  }

  return (
    <div className="workspace-page workspace-page--learning-path" style={{ height: '100vh', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      {/* Header */}
      <div className="learning-path-page-header" style={{ flexShrink: 0 }}>
        <WorkspacePageHeader
          title={
            <span className="learning-path-title">
              <Tooltip title="打开目录">
                <Button className="learning-path-title__catalogue" type="text" icon={<MenuOutlined />} aria-label={drawerOpen ? '关闭目录' : '打开目录'} onClick={() => setDrawerOpen((open) => !open)} />
              </Tooltip>
              <span>学习路径</span>
            </span>
          }
          description="按当前课程与进度组织学习任务"
          metrics={[
            { label: '路径进度', value: activePath ? `${Math.round((activePath.progress || 0) * 100)}%` : '未生成' },
          ]}
          metricAction={
            <Tooltip title={tutorCollapsed ? '展开智能辅导' : '收起智能辅导'}>
              <Button className="learning-path-header-toggle" type="text" icon={tutorCollapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />} aria-label={tutorCollapsed ? '展开智能辅导' : '收起智能辅导'} onClick={() => setTutorCollapsed((collapsed) => !collapsed)} />
            </Tooltip>
          }
          actions={
            <Button type="primary" icon={<RobotOutlined />} loading={running} onClick={generate}>
              {running ? 'Agent 正在执行...' : activePath ? '重新规划路径' : '生成学习路径'}
            </Button>
          }
        />
      </div>

      <TaskProgress task={activeTask} onClose={clearTask} />

      {/* Main area */}
      <div style={{ flex: 1, display: 'flex', position: 'relative', overflow: 'hidden' }}>
        {/* Left: Course Drawer overlay */}
        <CourseDrawer
          courseId={courseId}
          open={drawerOpen}
          onClose={() => setDrawerOpen(false)}
          activeChapterId={activeChapterId}
          activeKpId={activeKpId}
          onSelectChapter={handleSelectChapter}
          onSelectKp={handleSelectKp}
        />

        {/* Center: Content area */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
          {/* Main content */}
          <div style={{ flex: 1, overflow: 'hidden' }}>
            <ContentViewer
              kp={currentKp}
              sectionNumber={sectionNumber}
              resources={resources}
              resourceLoading={resourceLoading}
              videoTasks={videoTasks}
              activeVideo={activeVideo}
              onOpenDetail={handleOpenDetail}
              onGenerateVideo={handleGenerateOrPlayVideo}
              onCloseVideo={() => setActiveVideo(null)}
            />
          </div>
        </div>

        {/* Right: AI Tutor */}
        <div className={`learning-path-tutor${tutorCollapsed ? ' learning-path-tutor--collapsed' : ''}`} style={{
          width: tutorCollapsed ? 0 : 360,
          flexShrink: 0,
          overflow: 'hidden',
        }}>
          {!tutorCollapsed && (
            <AITutorPanel
              courseId={courseId}
              chapterTitle={chapterTitle}
              kpTitle={kpTitle}
            />
          )}
        </div>
      </div>

      {/* Resource detail modal */}
      <ResourceModal
        resource={detailResource}
        open={detailModalOpen}
        loading={detailModalLoading}
        onClose={() => {
          setDetailModalOpen(false)
          setDetailResource(null)
        }}
      />
    </div>
  )
}

export default LearningPath
