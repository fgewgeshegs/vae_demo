import React, { useEffect, useState, useRef } from "react"
import {
  Button, Card, Col, Collapse, Empty, Input, message, Modal, Popconfirm,
  Progress, Row, Spin, Tag, Tooltip, Typography, Upload,
} from "antd"
import type { UploadProps } from "antd"
import {
  ApartmentOutlined, ArrowLeftOutlined, BookOutlined,
  DeleteOutlined, FileTextOutlined, PlayCircleOutlined,
  PlusOutlined, UploadOutlined, VideoCameraOutlined,
} from "@ant-design/icons"
import { chapterApi, courseApi, documentApi, knowledgePointApi, videoApi } from "../services/api"
import type { VideoTask } from "../services/api"
import type { Chapter, Course, Document, KnowledgePoint } from "../types"
import WorkspacePageHeader from "../components/WorkspacePageHeader"

const { Title, Text, Paragraph } = Typography

const difficultyColor: Record<string, string> = {
  easy: "green",
  medium: "orange",
  hard: "red",
}

const CoursesPage: React.FC = () => {
  const [courses, setCourses] = useState<Course[]>([])
  const [loading, setLoading] = useState(true)
  const [selected, setSelected] = useState<Course | null>(null)
  const [chapters, setChapters] = useState<Chapter[]>([])
  const [kpCache, setKpCache] = useState<Record<number, KnowledgePoint[]>>({})
  const [docs, setDocs] = useState<Document[]>([])
  const [detailLoading, setDetailLoading] = useState(false)
  const [uploadTitle, setUploadTitle] = useState("")
  const [uploadFile, setUploadFile] = useState<File | null>(null)
  const [uploading, setUploading] = useState(false)
  const [videoTasks, setVideoTasks] = useState<Record<number, VideoTask>>({})
  const [activeVideo, setActiveVideo] = useState<{ url: string; title: string } | null>(null)
  const pollRefs = useRef<Record<number, ReturnType<typeof setInterval>>>({})

  // Cleanup polling on unmount
  useEffect(() => {
    return () => { Object.values(pollRefs.current).forEach(clearInterval) }
  }, [])

  const handleGenerateVideo = async (kp: KnowledgePoint) => {
    const kpId = kp.id
    const topic = kp.title
    const content = kp.content || ""

    setVideoTasks(prev => ({
      ...prev,
      [kpId]: { task_id: "", status: "queued", progress: 0, video_path: null, video_url: null, title: topic, error: null, created_at: new Date().toISOString() },
    }))

    try {
      const res = await videoApi.generate(topic, kp.title, undefined, content)
      const { task_id, video_url } = res.data

      if (video_url) {
        setVideoTasks(prev => ({
          ...prev,
          [kpId]: { task_id, status: "completed", progress: 100, video_path: null, video_url, title: topic, error: null, created_at: new Date().toISOString(), completed_at: new Date().toISOString() },
        }))
        return
      }

      pollRefs.current[kpId] = setInterval(async () => {
        try {
          const statusRes = await videoApi.status(task_id)
          const task = statusRes.data
          setVideoTasks(prev => ({ ...prev, [kpId]: task }))
          if (task.status === "completed" || task.status === "failed") {
            clearInterval(pollRefs.current[kpId])
            delete pollRefs.current[kpId]
          }
        } catch {
          clearInterval(pollRefs.current[kpId])
          delete pollRefs.current[kpId]
        }
      }, 2000)
    } catch (e: any) {
      message.error(e?.response?.data?.detail || "视频生成失败")
      setVideoTasks(prev => ({
        ...prev,
        [kpId]: { task_id: "", status: "failed", progress: 0, video_path: null, video_url: null, title: topic, error: e?.response?.data?.detail || "生成失败", created_at: new Date().toISOString() },
      }))
    }
  }

  const loadCourses = async () => {
    setLoading(true)
    try {
      const res = await courseApi.list()
      setCourses(res.data)
    } catch {
      message.error("课程加载失败")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { loadCourses() }, [])

  const openCourse = async (course: Course) => {
    setSelected(course)
    setDetailLoading(true)
    setChapters([])
    setDocs([])
    setKpCache({})
    try {
      const [chRes, docRes] = await Promise.all([
        chapterApi.listByCourse(course.id),
        documentApi.listByCourse(course.id),
      ])
      setChapters(chRes.data)
      setDocs(docRes.data)
    } catch {
      message.error("课程详情加载失败")
    } finally {
      setDetailLoading(false)
    }
  }

  const loadKnowledgePoints = async (chapterId: number) => {
    if (kpCache[chapterId]) return
    try {
      const res = await knowledgePointApi.listByChapter(chapterId)
      setKpCache((prev) => ({ ...prev, [chapterId]: res.data }))
    } catch {
      message.error("知识点加载失败")
    }
  }

  const handleUpload = async () => {
    if (!selected || !uploadFile || !uploadTitle.trim()) {
      message.warning("请填写标题并选择文件")
      return
    }
    setUploading(true)
    try {
      await documentApi.upload(selected.id, uploadTitle.trim(), uploadFile)
      message.success("文档上传成功")
      setUploadTitle("")
      setUploadFile(null)
      const res = await documentApi.listByCourse(selected.id)
      setDocs(res.data)
    } catch {
      message.error("文档上传失败")
    } finally {
      setUploading(false)
    }
  }

  const deleteDoc = async (id: number) => {
    try {
      await documentApi.delete(id)
      message.success("已删除")
      if (selected) {
        const res = await documentApi.listByCourse(selected.id)
        setDocs(res.data)
      }
    } catch {
      message.error("删除失败")
    }
  }

  const uploadProps: UploadProps = {
    beforeUpload: (file) => { setUploadFile(file); return false },
    onRemove: () => setUploadFile(null),
    fileList: uploadFile ? [{ uid: "-1", name: uploadFile.name, status: "done" }] : [],
    maxCount: 1,
  }

  if (loading) {
    return <div style={{ textAlign: "center", padding: 80 }}><Spin size="large" /></div>
  }

  if (selected) {
    return (
      <div>
        <div style={{ marginBottom: 16, display: "flex", alignItems: "center", gap: 8 }}>
          <Button icon={<ArrowLeftOutlined />} onClick={() => setSelected(null)}>返回课程列表</Button>
          <Title level={4} style={{ margin: 0 }}>{selected.title}</Title>
        </div>

        {detailLoading ? (
          <div style={{ textAlign: "center", padding: 60 }}><Spin /></div>
        ) : (
          <Row gutter={[16, 16]}>
            <Col xs={24} lg={14}>
              <div className="card" style={{ padding: "20px 22px" }}>
                <Text style={{ color: "#64748b", fontWeight: 500, fontSize: 11, letterSpacing: "0.5px", textTransform: "uppercase" }}>章节与知识点</Text>
                {chapters.length === 0 ? (
                  <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无章节" style={{ marginTop: 24 }} />
                ) : (
                  <Collapse
                    style={{ marginTop: 12 }}
                    onChange={(keys) => {
                      const active = Array.isArray(keys) ? keys : [keys]
                      const key = active.find((k) => !kpCache[Number(k)])
                      if (key) loadKnowledgePoints(Number(key))
                    }}
                    items={chapters
                      .slice()
                      .sort((a, b) => a.sort_order - b.sort_order)
                      .map((ch) => ({
                        key: String(ch.id),
                        label: (
                          <span style={{ fontSize: 13, fontWeight: 500, color: "#0f172a" }}>
                            <ApartmentOutlined style={{ marginRight: 8, color: "#2563eb" }} />
                            {ch.title}
                          </span>
                        ),
                        children: (kpCache[ch.id] || []).length === 0 ? (
                          <Text style={{ color: "#94a3b8", fontSize: 12 }}>暂无知识点</Text>
                        ) : (
                          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                            {(kpCache[ch.id] || []).map((kp) => (
                              <div key={kp.id} style={{ padding: "6px 10px", background: "#f8fafc", borderRadius: 6, fontSize: 13, display: "flex", alignItems: "center", gap: 8 }}>
                                <Text style={{ color: "#334155", flex: 1, minWidth: 0 }} ellipsis>{kp.title}</Text>
                                <Tag style={{ fontSize: 10, flexShrink: 0 }} color={difficultyColor[kp.difficulty] || "default"}>{kp.difficulty}</Tag>
                                {videoTasks[kp.id]?.status === "completed" ? (
                                  <Tooltip title="播放视频">
                                    <Button type="link" size="small" icon={<PlayCircleOutlined style={{ color: "#16a34a", fontSize: 16 }} />}
                                      onClick={() => setActiveVideo({ url: videoTasks[kp.id].video_url!, title: kp.title })}
                                      style={{ padding: 0, height: "auto" }} />
                                  </Tooltip>
                                ) : videoTasks[kp.id]?.status === "failed" ? (
                                  <Tooltip title={videoTasks[kp.id].error || "生成失败，点击重试"}>
                                    <Button type="link" size="small"
                                      icon={<VideoCameraOutlined style={{ color: "#ef4444", fontSize: 14 }} />}
                                      onClick={() => handleGenerateVideo(kp)}
                                      style={{ padding: "0 4px", height: "auto", fontSize: 11, color: "#ef4444" }}>
                                      重试
                                    </Button>
                                  </Tooltip>
                                ) : videoTasks[kp.id]?.status === "queued" || videoTasks[kp.id]?.status === "processing" ? (
                                  <Progress type="circle" percent={videoTasks[kp.id].progress} size={20} strokeColor="#2563eb" style={{ margin: 0 }} />
                                ) : (
                                  <Button type="text" size="small" icon={<PlayCircleOutlined style={{ color: "#2563eb", fontSize: 14 }} />}
                                    onClick={() => handleGenerateVideo(kp)}
                                    style={{ padding: "0 4px", height: "auto", fontSize: 11, color: "#2563eb" }}>
                                    生成视频
                                  </Button>
                                )}
                              </div>
                            ))}
                          </div>
                        ),
                      }))}
                  />
                )}
              </div>
            </Col>

            <Col xs={24} lg={10}>
              <div className="card" style={{ padding: "20px 22px" }}>
                <Text style={{ color: "#64748b", fontWeight: 500, fontSize: 11, letterSpacing: "0.5px", textTransform: "uppercase" }}>课程文档</Text>
                <div style={{ marginTop: 12, marginBottom: 16, display: "flex", flexDirection: "column", gap: 8 }}>
                  <Input
                    placeholder="文档标题"
                    value={uploadTitle}
                    onChange={(e) => setUploadTitle(e.target.value)}
                    prefix={<FileTextOutlined style={{ color: "#94a3b8" }} />}
                  />
                  <Upload {...uploadProps}>
                    <Button icon={<UploadOutlined />}>选择文件</Button>
                  </Upload>
                  <Button
                    type="primary"
                    icon={<PlusOutlined />}
                    loading={uploading}
                    onClick={handleUpload}
                    disabled={!uploadTitle.trim() || !uploadFile}
                  >
                    上传文档
                  </Button>
                </div>
                {docs.length === 0 ? (
                  <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无文档" />
                ) : (
                  <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                    {docs.map((d) => (
                      <div key={d.id} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "8px 10px", background: "#f8fafc", borderRadius: 6 }}>
                        <div style={{ minWidth: 0, flex: 1 }}>
                          <Text ellipsis style={{ fontSize: 12, color: "#0f172a" }}>{d.title}</Text>
                          <div style={{ fontSize: 10, color: "#94a3b8" }}>{d.file_type} · {d.status}</div>
                        </div>
                        <Popconfirm title="确认删除？" onConfirm={() => deleteDoc(d.id)}>
                          <Button type="text" size="small" danger icon={<DeleteOutlined />} />
                        </Popconfirm>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </Col>
          </Row>
        )}
        {activeVideo && (
          <Modal
            title={activeVideo.title}
            open={true}
            onCancel={() => setActiveVideo(null)}
            footer={null}
            width={720}
            destroyOnClose
          >
            <video controls style={{ width: "100%", borderRadius: 8 }} src={activeVideo.url}>
              您的浏览器不支持视频播放
            </video>
          </Modal>
        )}
      </div>
    )
  }

  return (
    <div className="workspace-page workspace-page--courses">
      <WorkspacePageHeader title="课程管理" description="维护课程内容、章节资料与知识点，确保学习内容可持续更新。" metrics={[{ label: '课程数量', value: courses.length }]} />
      {courses.length === 0 ? (
        <Empty description="暂无课程" />
      ) : (
        <Row gutter={[16, 16]}>
          {courses.map((c) => (
            <Col xs={24} sm={12} lg={8} key={c.id}>
              <Card hoverable onClick={() => openCourse(c)} style={{ height: "100%" }}>
                <div style={{ display: "flex", alignItems: "flex-start", gap: 12 }}>
                  <div style={{ width: 40, height: 40, borderRadius: 8, background: "#eff6ff", display: "flex", alignItems: "center", justifyContent: "center", color: "#2563eb", fontSize: 18, flexShrink: 0 }}>
                    <BookOutlined />
                  </div>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <Text strong style={{ fontSize: 14, color: "#0f172a" }}>{c.title}</Text>
                    <Paragraph ellipsis={{ rows: 2 }} style={{ fontSize: 12, color: "#64748b", marginTop: 4, marginBottom: 0 }}>
                      {c.description || "暂无描述"}
                    </Paragraph>
                    <div style={{ marginTop: 8, display: "flex", gap: 6 }}>
                      {c.seed_course && <Tag color="blue" style={{ fontSize: 10 }}>种子课程</Tag>}
                      <Tag color={c.is_active ? "green" : "default"} style={{ fontSize: 10 }}>
                        {c.is_active ? "启用" : "停用"}
                      </Tag>
                    </div>
                  </div>
                </div>
              </Card>
            </Col>
          ))}
        </Row>
      )}
    </div>
  )
}

export default CoursesPage
