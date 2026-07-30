import React, { useEffect, useState, useRef } from "react"
import {
  Alert, Button, Card, Descriptions, Tag, Spin, Empty, Typography,
  Row, Col, Input, Space, message, Select, Slider,
} from "antd"
import {
  RadarChartOutlined,
  UserOutlined,
  AimOutlined,
  ThunderboltOutlined,
  HeartOutlined,
  RobotOutlined,
  EditOutlined,
  CloseOutlined,
  SaveOutlined,
} from "@ant-design/icons"
import TaskProgress from "../components/TaskProgress"
import { profileApi } from "../services/api"
import { useTaskRunner } from "../hooks/useTaskRunner"
import type { StudentProfile } from "../types"

const { Title, Text } = Typography

interface ProfileAnalysisResult {
  message?: string
  updated_fields?: string[]
  insufficient_evidence?: string[]
}

const cleanProfileTags = (values: unknown): string[] => {
  if (!Array.isArray(values)) return []
  const noisePatterns = [/[?？]/, /如果/, /不清/, /请/, /吗/, /告诉/]
  return Array.from(new Set(
    values
      .filter((value): value is string => typeof value === "string")
      .map((value) => value.trim())
      .filter(Boolean)
      .filter((value) => value.length <= 12)
      .filter((value) => !noisePatterns.some((pattern) => pattern.test(value)))
  ))
}

const cleanProfileDescription = (value: unknown): string => {
  if (typeof value !== 'string') return ''
  const normalized = value.replace(/\s+/g, ' ').trim()
  const looksLikeInternalPrompt = /\b(analyze|update|agent|profile|only when|durable|instruction|prompt)\b/i.test(normalized)
  if (looksLikeInternalPrompt || normalized.length > 120) return ''
  return normalized
}

const LEVEL_OPTIONS = [
  { label: "入门", value: "beginner" },
  { label: "中级", value: "intermediate" },
  { label: "高级", value: "advanced" },
]

const PREFERENCE_OPTIONS = [
  { label: "视觉", value: "visual" },
  { label: "听觉", value: "auditory" },
  { label: "阅读", value: "reading" },
  { label: "实践", value: "kinesthetic" },
  { label: "混合", value: "mixed" },
]

const RESOURCE_TYPE_OPTIONS = [
  { label: "讲义", value: "document" },
  { label: "教学视频", value: "video" },
  { label: "练习题", value: "exercise" },
  { label: "代码案例", value: "code" },
  { label: "思维导图", value: "mindmap" },
  { label: "拓展阅读", value: "reading" },
]

const RESOURCE_TYPE_LABELS = Object.fromEntries(
  RESOURCE_TYPE_OPTIONS.map(({ label, value }) => [value, label])
)

const LEVEL_LABELS: Record<string, string> = { beginner: '入门', intermediate: '中等', advanced: '进阶' }
const PREFERENCE_LABELS: Record<string, string> = { visual: '视觉化学习', auditory: '听讲学习', reading: '阅读学习', kinesthetic: '实践学习', mixed: '混合学习' }
const SPEED_LABELS: Record<string, string> = { slow: '循序渐进', normal: '适中', fast: '快速推进' }

const SPEED_OPTIONS = [
  { label: "慢而扎实", value: "slow" },
  { label: "适中", value: "normal" },
  { label: "快速", value: "fast" },
]

const SUBJECT_OPTIONS = [
  "Python", "机器学习", "深度学习", "数学基础", "数据分析",
  "神经网络", "自然语言处理", "计算机视觉", "统计学", "线性代数",
]

const INTEREST_OPTIONS = [
  "机器学习", "深度学习", "自然语言处理", "计算机视觉",
  "数据分析", "大语言模型", "强化学习", "AI 安全",
  "知识图谱", "语音识别", "推荐系统", "机器人学",
]

const ProfilePage: React.FC = () => {
  const [profile, setProfile] = useState<StudentProfile | null>(null)
  const [loading, setLoading] = useState(true)
  const [editing, setEditing] = useState(false)
  const [saving, setSaving] = useState(false)

  const [description, setDescription] = useState("")
  const [analysisResult, setAnalysisResult] = useState<ProfileAnalysisResult | null>(null)
  const { activeTask, running, runTask, clearTask } = useTaskRunner()
  const [titleCompact, setTitleCompact] = useState(false)
  const lastTitleY = useRef(0)

  useEffect(() => {
    const onScroll = () => {
      const sy = window.scrollY
      setTitleCompact(sy > 60)
      lastTitleY.current = sy
    }
    window.addEventListener("scroll", onScroll, { passive: true })
    return () => window.removeEventListener("scroll", onScroll)
  }, [])


  const [form, setForm] = useState({
    level: "",
    subjects: [] as string[],
    preference: "",
    prefDesc: "",
    shortTermGoal: "",
    longTermGoal: "",
    speed: "",
    sessionMinutes: 30,
    interestAreas: [] as string[],
    resourceTypes: [] as string[],
  })

  const fetchProfile = async () => {
    try {
      const res = await profileApi.get()
      setProfile(res.data)
    } catch {
      message.error("获取画像失败")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchProfile() }, [])

  const updateProfileViaAgent = async () => {
    if (!description.trim()) return
    await runTask("update_profile", {
      input: { description: description.trim() },
      failureMessage: "画像更新失败",
      onSuccess: async (task) => {
        await fetchProfile()
        const data = task.result?.data as ProfileAnalysisResult | undefined
        setAnalysisResult(data || null)
        setDescription("")
      },
    })
  }

  const startEditing = () => {
    if (!profile) return
    const pd = profile.profile_data
    setForm({
      level: ((pd.knowledge_base as any)?.level as string) || "",
      subjects: ((pd.knowledge_base as any)?.subjects as string[]) || [],
      preference: ((pd.cognitive_style as any)?.preference as string) || "",
      prefDesc: ((pd.cognitive_style as any)?.description as string) || "",
      shortTermGoal: ((pd.learning_goals as any)?.short_term as string) || "",
      longTermGoal: ((pd.learning_goals as any)?.long_term as string) || "",
      speed: ((pd.learning_pace as any)?.speed as string) || "",
      sessionMinutes: ((pd.learning_pace as any)?.preferred_session_minutes as number) || 30,
      interestAreas: ((pd.interest_direction as any)?.areas as string[]) || [],
      resourceTypes: ((pd.resource_preferences as any)?.types as string[]) || [],
    })
    setEditing(true)
  }

  const cancelEditing = () => setEditing(false)

  const saveProfile = async () => {
    setSaving(true)
    try {
      await profileApi.update({
        knowledge_base: { level: form.level || null, subjects: form.subjects.length > 0 ? form.subjects : null },
        cognitive_style: { preference: form.preference || null, description: form.prefDesc || null },
        learning_goals: { short_term: form.shortTermGoal || null, long_term: form.longTermGoal || null },
        learning_pace: { speed: form.speed || null, preferred_session_minutes: form.sessionMinutes },
        interest_direction: { areas: form.interestAreas.length > 0 ? form.interestAreas : null },
        resource_preferences: { types: form.resourceTypes },
      })
      message.success("画像已保存")
      setEditing(false)
      await fetchProfile()
    } catch {
      message.error("保存失败，请稍后重试")
    } finally {
      setSaving(false)
    }
  }


  if (loading) {
    return <div style={{ textAlign: "center", paddingTop: 100 }}><Spin size="large" /></div>
  }

  if (!profile) {
    return <Empty description="暂无画像数据" />
  }

  const pd = profile.profile_data
  const interestAreas = cleanProfileTags((pd.interest_direction as any)?.areas)
  const preferenceDescription = cleanProfileDescription((pd.cognitive_style as any)?.description)
  const resourceTypes = (pd.resource_preferences as any)?.types as string[] || []

  return (
    <div className="workspace-page workspace-page--profile">
      <div style={{
        position: "sticky", top: 0, zIndex: 10,
        background: titleCompact ? "#ffffff" : "transparent",
        marginBottom: titleCompact ? 12 : 8, padding: titleCompact ? "8px 0" : 0,
        borderBottom: titleCompact ? "1px solid #e2e8f0" : "none",
        display: "flex", justifyContent: "space-between", alignItems: "center",
        transition: "all 0.2s ease",
      }}>
        {titleCompact ? (
          <>
            <Text style={{ fontWeight: 600, fontSize: 14, color: "#0f172a" }}>
              <UserOutlined style={{ marginRight: 6 }} />学习画像
            </Text>
            {!editing ? (
              <Button size="small" icon={<EditOutlined />} onClick={startEditing}>编辑</Button>
            ) : (
              <Space>
                <Button size="small" icon={<CloseOutlined />} onClick={cancelEditing} disabled={saving}>取消</Button>
                <Button size="small" type="primary" icon={<SaveOutlined />} onClick={saveProfile} loading={saving}>保存</Button>
              </Space>
            )}
          </>
        ) : (
          <>
            <div>
              <Title level={4} style={{ margin: 0 }}>
                <UserOutlined style={{ marginRight: 8 }} />学习画像
              </Title>
              <Text type="secondary">
                版本 {profile.version} · 最后更新 {new Date(profile.updated_at).toLocaleString("zh-CN")}
              </Text>
            </div>
            {!editing ? (
              <Button icon={<EditOutlined />} onClick={startEditing}>编辑画像</Button>
            ) : (
              <Space>
                <Button icon={<CloseOutlined />} onClick={cancelEditing} disabled={saving}>取消</Button>
                <Button type="primary" icon={<SaveOutlined />} onClick={saveProfile} loading={saving}>保存</Button>
              </Space>
            )}
          </>
        )}
      </div>

      {editing ? (
        <div>
          <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
            <Col xs={24} lg={12}>
              <Card title={<><AimOutlined /> 知识基础</>}>
                <div style={{ marginBottom: 16 }}>
                  <Text strong style={{ fontSize: 13, display: "block", marginBottom: 6 }}>水平</Text>
                  <Select value={form.level || undefined} onChange={v => setForm(f => ({ ...f, level: v }))}
                    placeholder="选择水平" allowClear style={{ width: "100%" }} options={LEVEL_OPTIONS} />
                </div>
                <div>
                  <Text strong style={{ fontSize: 13, display: "block", marginBottom: 6 }}>熟悉领域</Text>
                  <Select mode="tags" value={form.subjects} onChange={v => setForm(f => ({ ...f, subjects: v }))}
                    placeholder="输入或选择领域" style={{ width: "100%" }} tokenSeparators={[",", "，", ";", "；"]}>
                    {SUBJECT_OPTIONS.map(s => <Select.Option key={s} value={s}>{s}</Select.Option>)}
                  </Select>
                </div>
              </Card>
            </Col>
            <Col xs={24} lg={12}>
              <Card title={<><RadarChartOutlined /> 认知风格</>}>
                <div style={{ marginBottom: 16 }}>
                  <Text strong style={{ fontSize: 13, display: "block", marginBottom: 6 }}>偏好</Text>
                  <Select value={form.preference || undefined} onChange={v => setForm(f => ({ ...f, preference: v }))}
                    placeholder="选择偏好" allowClear style={{ width: "100%" }} options={PREFERENCE_OPTIONS} />
                </div>
                <div>
                  <Text strong style={{ fontSize: 13, display: "block", marginBottom: 6 }}>描述</Text>
                  <Input.TextArea value={form.prefDesc} onChange={e => setForm(f => ({ ...f, prefDesc: e.target.value }))}
                    placeholder="描述你的学习偏好..." rows={2} />
                </div>
                <div style={{ marginTop: 16 }}>
                  <Text strong style={{ fontSize: 13, display: "block", marginBottom: 6 }}>资源形式</Text>
                  <Select mode="multiple" value={form.resourceTypes}
                    onChange={v => setForm(f => ({ ...f, resourceTypes: v }))}
                    placeholder="可多选偏好的资源形式" style={{ width: "100%" }} options={RESOURCE_TYPE_OPTIONS} />
                </div>
              </Card>
            </Col>
          </Row>

          <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
            <Col xs={24} lg={12}>
              <Card title={<><ThunderboltOutlined /> 学习目标</>}>
                <div style={{ marginBottom: 16 }}>
                  <Text strong style={{ fontSize: 13, display: "block", marginBottom: 6 }}>短期目标</Text>
                  <Input.TextArea value={form.shortTermGoal} onChange={e => setForm(f => ({ ...f, shortTermGoal: e.target.value }))}
                    placeholder="例如：一个月内理解神经网络的基本原理" rows={2} />
                </div>
                <div>
                  <Text strong style={{ fontSize: 13, display: "block", marginBottom: 6 }}>长期目标</Text>
                  <Input.TextArea value={form.longTermGoal} onChange={e => setForm(f => ({ ...f, longTermGoal: e.target.value }))}
                    placeholder="例如：能够独立完成一个 AI 项目" rows={2} />
                </div>
              </Card>
            </Col>
            <Col xs={24} lg={12}>
              <Card title={<><HeartOutlined /> 兴趣方向</>}>
                <div style={{ marginBottom: 16 }}>
                  <Text strong style={{ fontSize: 13, display: "block", marginBottom: 6 }}>感兴趣的方向</Text>
                  <Select mode="tags" value={form.interestAreas} onChange={v => setForm(f => ({ ...f, interestAreas: v }))}
                    placeholder="输入或选择感兴趣的方向" style={{ width: "100%" }} tokenSeparators={[",", "，", ";", "；"]}>
                    {INTEREST_OPTIONS.map(s => <Select.Option key={s} value={s}>{s}</Select.Option>)}
                  </Select>
                </div>
              </Card>
            </Col>
          </Row>

          <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
            <Col xs={24} lg={12}>
              <Card title={<><RadarChartOutlined /> 学习节奏</>}>
                <div style={{ marginBottom: 16 }}>
                  <Text strong style={{ fontSize: 13, display: "block", marginBottom: 6 }}>学习速度</Text>
                  <Select value={form.speed || undefined} onChange={v => setForm(f => ({ ...f, speed: v }))}
                    placeholder="选择速度" allowClear style={{ width: "100%" }} options={SPEED_OPTIONS} />
                </div>
                <div>
                  <Text strong style={{ fontSize: 13, display: "block", marginBottom: 6 }}>
                    单次专注时长：<Text style={{ color: "#2563eb" }}>{form.sessionMinutes} 分钟</Text>
                  </Text>
                  <Slider value={form.sessionMinutes} onChange={v => setForm(f => ({ ...f, sessionMinutes: v }))}
                    min={5} max={120} step={5}
                    marks={{ 5: "5min", 30: "30min", 60: "1h", 90: "1.5h", 120: "2h" }}
                    trackStyle={{ background: "linear-gradient(90deg, #2563eb, #3b82f6)" }}
                    handleStyle={{ borderColor: "#2563eb" }}
                    railStyle={{ background: "rgba(0,0,0,0.08)" }} />
                </div>
              </Card>
            </Col>
          </Row>
        </div>
      ) : (
        <>
          <Card style={{ marginTop: 16 }} title={<Space><RobotOutlined />画像分析 Agent</Space>}>
            <Space.Compact style={{ width: "100%" }}>
              <Input value={description} onChange={e => setDescription(e.target.value)}
                onPressEnter={updateProfileViaAgent}
                placeholder="例如：Python 基础，目标学习机器学习；每天 1 小时；薄弱点是数学，喜欢案例式学习" />
              <Button type="primary" loading={running} onClick={updateProfileViaAgent}>
                {running ? "Agent 正在分析..." : "分析并更新"}
              </Button>
            </Space.Compact>
            <TaskProgress task={activeTask} onClose={clearTask} />
            {analysisResult && (
              <Alert style={{ marginTop: 12 }}
                type={(analysisResult.updated_fields || []).length > 0 ? "success" : "info"}
                showIcon message={analysisResult.message || "画像分析完成"}
                description={
                  <div>
                    {(analysisResult.updated_fields || []).length > 0 && <div>已更新：{(analysisResult.updated_fields || []).join("、")}</div>}
                    {(analysisResult.insufficient_evidence || []).length > 0 && <div>证据不足：{(analysisResult.insufficient_evidence || []).join("、")}</div>}
                  </div>
                } />
            )}
          </Card>

          <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
            <Col xs={24} lg={12}>
              <Card title={<><AimOutlined /> 知识基础</>}>
                <Descriptions column={1} size="small">
                  <Descriptions.Item label="水平"><Tag color="blue">{LEVEL_LABELS[((pd.knowledge_base as any)?.level as string)] || "未设置"}</Tag></Descriptions.Item>
                  <Descriptions.Item label="熟悉领域">{(pd.knowledge_base as any)?.subjects?.join("、") || "暂无"}</Descriptions.Item>
                </Descriptions>
              </Card>
            </Col>
            <Col xs={24} lg={12}>
              <Card title={<><RadarChartOutlined /> 认知风格</>}>
                <Descriptions column={1} size="small">
                  <Descriptions.Item label="偏好"><Tag color="purple">{PREFERENCE_LABELS[((pd.cognitive_style as any)?.preference as string)] || "未设置"}</Tag></Descriptions.Item>
                  <Descriptions.Item label="描述">{preferenceDescription || "暂无"}</Descriptions.Item>
                  <Descriptions.Item label="资源形式">
                    {resourceTypes.length > 0 ? (
                      <Space size={[6, 6]} wrap>
                        {resourceTypes.map((type) => <Tag key={type} color="geekblue" style={{ margin: 0 }}>{RESOURCE_TYPE_LABELS[type] || type}</Tag>)}
                      </Space>
                    ) : "暂无"}
                  </Descriptions.Item>
                </Descriptions>
              </Card>
            </Col>
          </Row>

          <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
            <Col xs={24} lg={12}>
              <Card title={<><ThunderboltOutlined /> 学习目标</>}>
                <Descriptions column={1} size="small">
                  <Descriptions.Item label="短期">{((pd.learning_goals as any)?.short_term as string) || "未设置"}</Descriptions.Item>
                  <Descriptions.Item label="长期">{((pd.learning_goals as any)?.long_term as string) || "未设置"}</Descriptions.Item>
                </Descriptions>
              </Card>
            </Col>
            <Col xs={24} lg={12}>
              <Card title={<><HeartOutlined /> 兴趣方向</>}>
                <Descriptions column={1} size="small">
                  <Descriptions.Item label="感兴趣的领域">
                    {interestAreas.length > 0 ? (
                      <Space size={[6, 6]} wrap>
                        {interestAreas.map((area) => <Tag key={area} color="cyan" style={{ margin: 0 }}>{area}</Tag>)}
                      </Space>
                    ) : "暂无"}
                  </Descriptions.Item>
                </Descriptions>
              </Card>
            </Col>
          </Row>

          <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
            <Col xs={24} lg={12}>
              <Card title={<><RadarChartOutlined /> 学习节奏</>}>
                <Descriptions column={1} size="small">
                  <Descriptions.Item label="速度"><Tag color="green">{SPEED_LABELS[((pd.learning_pace as any)?.speed as string)] || "未设置"}</Tag></Descriptions.Item>
                  <Descriptions.Item label="单次专注时长">{((pd.learning_pace as any)?.preferred_session_minutes as number) || 30} 分钟</Descriptions.Item>
                </Descriptions>
              </Card>
            </Col>
          </Row>

          {(pd.knowledge_gaps as string[] || []).length > 0 && (
            <Card title="知识短板" style={{ marginTop: 16 }}>
              {(pd.knowledge_gaps as string[]).map((gap, i) => <Tag key={i} color="orange" style={{ marginBottom: 4 }}>{gap}</Tag>)}
            </Card>
          )}

          {(pd.weak_points as string[] || []).length > 0 && (
            <Card title="易错点" style={{ marginTop: 16 }}>
              {(pd.weak_points as string[]).map((wp, i) => <Tag key={i} color="red" style={{ marginBottom: 4 }}>{wp}</Tag>)}
            </Card>
          )}
        </>
      )}
    </div>
  )
}

export default ProfilePage

