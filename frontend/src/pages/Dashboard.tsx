import React, { useEffect, useState } from "react"
import { Row, Col, Typography, Tag, Spin, Empty, Progress } from "antd"
import {
  BookOutlined, FileTextOutlined, QuestionCircleOutlined,
  ReadOutlined, FolderOpenOutlined, SmileOutlined,
  RightOutlined, ThunderboltOutlined, AimOutlined,
  CheckCircleOutlined, ClockCircleOutlined,
  StarOutlined, FieldNumberOutlined
} from "@ant-design/icons"
import { useNavigate } from "react-router-dom"
import { courseApi, evaluationApi, studyPathApi, qaApi, resourceApi } from "../services/api"
import type { Course, StudyPath, QARecord } from "../types"
import { useAuthStore } from "../store"
import FocusFlow from "../components/FocusFlow"
import KnowledgeConstellation from "../components/KnowledgeConstellation"
import AICompanion from "../components/AICompanion"
import LearningRhythm from "../components/LearningRhythm"

const { Title, Text } = Typography

const quickActions = [
  {
    key: "learn",  icon: <ReadOutlined />,
    label: "\u5f00\u59cb\u5b66\u4e60", desc: "\u5b66\u4e60\u8def\u5f84 \u00b7 \u667a\u80fd\u8f85\u5bfc \u00b7 \u8bfe\u7a0b",
    gradient: "linear-gradient(135deg, #06b6d4, #6366f1)",
    shadow: "rgba(6,182,212,0.15)", path: "/path", delay: 1,
  },
  {
    key: "resources", icon: <FolderOpenOutlined />,
    label: "\u63a2\u7d22\u8d44\u6e90", desc: "\u8d44\u6e90\u4e2d\u5fc3 \u00b7 \u77e5\u8bc6\u68c0\u7d22",
    gradient: "linear-gradient(135deg, #6366f1, #8b5cf6)",
    shadow: "rgba(99,102,241,0.15)", path: "/resources", delay: 2,
  },
  {
    key: "qa", icon: <QuestionCircleOutlined />,
    label: "\u5411 AI \u63d0\u95ee", desc: "\u667a\u80fd\u8f85\u5bfc \u00b7 \u5373\u65f6\u7b54\u7591",
    gradient: "linear-gradient(135deg, #8b5cf6, #ec4899)",
    shadow: "rgba(139,92,246,0.15)", path: "/qa", delay: 3,
  },
  {
    key: "profile", icon: <SmileOutlined />,
    label: "\u6211\u7684\u753b\u50cf", desc: "\u5b66\u4e60\u8bc4\u4f30 \u00b7 \u4e2a\u4eba\u753b\u50cf",
    gradient: "linear-gradient(135deg, #ec4899, #f43f5e)",
    shadow: "rgba(236,72,153,0.15)", path: "/profile", delay: 4,
  },
]

const Dashboard: React.FC = () => {
  const navigate = useNavigate()
  const user = useAuthStore((s) => s.user)
  const [courses, setCourses] = useState<Course[]>([])
  const [paths, setPaths] = useState<StudyPath[]>([])
  const [recentQA, setRecentQA] = useState<QARecord[]>([])
  const [qaCount, setQaCount] = useState(0)
  const [latestEval, setLatestEval] = useState<any>(null)
  const [resourceCount, setResourceCount] = useState(0)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchData = async () => {
      try {
        const loadCourses   = async () => { try { const r=await courseApi.list(); setCourses(r.data) } catch {} }
        const loadPaths     = async () => { try { const r=await studyPathApi.list(); setPaths(r.data) } catch {} }
        const loadQA = async () => {
          try { const r=await qaApi.list(); setRecentQA(r.data.slice(0,4)); const c=await qaApi.count(); setQaCount(c.data.count) } catch {}
        }
        const loadResources = async () => { try { const r=await resourceApi.list(); setResourceCount(r.data.length) } catch {} }
        const loadEval      = async () => { try { const r=await evaluationApi.latest(); setLatestEval(r.data) } catch {} }
        await Promise.all([loadCourses(), loadPaths(), loadQA(), loadResources(), loadEval()])
      } catch {} finally { setLoading(false) }
    }
    fetchData()
  }, [])

  const getGreeting = () => {
    const h = new Date().getHours()
    if (h < 6) return "\u591c\u6df1\u4e86\uff0c\u8fd8\u5728\u5b66\u4e60"
    if (h < 10) return "\u65e9\u4e0a\u597d"
    if (h < 14) return "\u4e0b\u5348\u597d"
    if (h < 19) return "\u4e0b\u5348\u597d"
    if (h < 22) return "\u665a\u4e0a\u597d"
    return "\u591c\u6df1\u4e86"
  }

  if (loading) {
    return (
      <div style={{ display: "flex", justifyContent: "center", alignItems: "center", height: "calc(100vh - 160px)" }}>
        <Spin size="large" tip="\u52a0\u8f7d\u4e2d..." />
      </div>
    )
  }

  return (
    <div style={{ position: "relative" }}>
      <div style={{
        position: "absolute", top: -80, left: -120, width: 500, height: 500,
        borderRadius: "50%",
        background: "radial-gradient(circle, rgba(6,182,212,0.06) 0%, transparent 70%)",
        pointerEvents: "none", zIndex: 0,
      }} />
      <div style={{
        position: "absolute", top: 200, right: -80, width: 400, height: 400,
        borderRadius: "50%",
        background: "radial-gradient(circle, rgba(139,92,246,0.05) 0%, transparent 70%)",
        pointerEvents: "none", zIndex: 0,
      }} />
      <div style={{
        position: "absolute", bottom: 100, left: "40%", width: 300, height: 300,
        borderRadius: "50%",
        background: "radial-gradient(circle, rgba(236,72,153,0.04) 0%, transparent 70%)",
        pointerEvents: "none", zIndex: 0,
      }} />

      <div className="animate-fadeInUp" style={{ marginBottom: 36, position: "relative", zIndex: 1 }}>
        <div style={{
          position: "relative", overflow: "hidden", borderRadius: 16,
          border: "1px solid rgba(255,255,255,0.05)",
          background: "linear-gradient(135deg, rgba(6,182,212,0.06) 0%, rgba(99,102,241,0.06) 50%, rgba(139,92,246,0.06) 100%)",
          backdropFilter: "blur(12px)",
        }}>
          <div style={{
            position: "absolute", top: 0, left: 0, right: 0, height: 1,
            background: "linear-gradient(90deg, transparent, rgba(99,102,241,0.3), transparent)",
          }} />
          <div style={{ padding: "24px 32px", display: "flex", alignItems: "center", gap: 18 }}>
            <div style={{
              width: 48, height: 48, borderRadius: 12,
              background: "linear-gradient(135deg, #06b6d4, #6366f1)",
              display: "flex", alignItems: "center", justifyContent: "center",
              boxShadow: "0 0 30px rgba(99,102,241,0.2)",
              flexShrink: 0,
            }}>
              <ThunderboltOutlined style={{ color: "#fff", fontSize: 22 }} />
            </div>
            <div style={{ flex: 1 }}>
              <Title level={4} style={{ margin: 0, color: "rgba(255,255,255,0.92)", fontSize: 18, fontWeight: 600 }}>
                {getGreeting()}{'\uff0c'}{user?.display_name || user?.username}
              </Title>
              <AICompanion />
            </div>
          </div>
        </div>
      </div>

      <div style={{ marginBottom: 36, position: "relative", zIndex: 1 }}>
        <Text style={{
          color: "rgba(255,255,255,0.20)", fontSize: 10, letterSpacing: 1.5,
          textTransform: "uppercase", display: "block", marginBottom: 14, fontWeight: 600,
        }}>
          {'\u5feb'}{'\u901f'}{'\u5f00'}{'\u59cb'}
        </Text>
        <Row gutter={[16, 16]}>
          {quickActions.map((action) => (
            <Col xs={12} lg={6} key={action.key}>
              <div className={`animate-fadeInUp delay-${action.delay}`}>
                <div onClick={() => navigate(action.path)} style={{
                  background: "rgba(255,255,255,0.025)", backdropFilter: "blur(10px)",
                  border: "1px solid rgba(255,255,255,0.05)", borderRadius: 14,
                  padding: "22px 22px", cursor: "pointer",
                  transition: "all 0.4s cubic-bezier(0.19,1,0.22,1)",
                  position: "relative", overflow: "hidden", height: "100%",
                }} onMouseEnter={(e) => {
                  e.currentTarget.style.transform = "translateY(-4px)"
                  e.currentTarget.style.borderColor = "rgba(255,255,255,0.12)"
                  e.currentTarget.style.boxShadow = `0 16px 48px ${action.shadow}`
                }} onMouseLeave={(e) => {
                  e.currentTarget.style.transform = "translateY(0)"
                  e.currentTarget.style.borderColor = "rgba(255,255,255,0.05)"
                  e.currentTarget.style.boxShadow = "none"
                }}>
                  <div style={{ position: "absolute", top: -24, right: -24, width: 100, height: 100, borderRadius: "50%", background: action.gradient, opacity: 0.06, filter: "blur(24px)", pointerEvents: "none" }} />
                  <div style={{ width: 38, height: 38, borderRadius: 10, background: action.gradient, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 16, color: 'white', marginBottom: 14, boxShadow: `0 0 24px ${action.shadow}` }}>
                    {action.icon}
                  </div>
                  <div style={{ color: "rgba(255,255,255,0.88)", fontWeight: 600, fontSize: 15, marginBottom: 4 }}>
                    {action.label}
                    <RightOutlined style={{ fontSize: 11, marginLeft: 6, color: "rgba(255,255,255,0.20)" }} />
                  </div>
                  <div style={{ color: "rgba(255,255,255,0.30)", fontSize: 12 }}>{action.desc}</div>
                </div>
              </div>
            </Col>
          ))}
        </Row>
      </div>

      <div style={{ position: "relative", zIndex: 1, marginBottom: 36 }}>
        <Text style={{ color: "rgba(255,255,255,0.20)", fontSize: 10, letterSpacing: 1.5, textTransform: "uppercase", display: "block", marginBottom: 14, fontWeight: 600 }}>
          <StarOutlined style={{ marginRight: 6 }} />{'\u8ba4'}{'\u77e5'}{'\u56fe'}{'\u8c31'}
        </Text>
        <Row gutter={[16, 16]}>
          <Col xs={24} lg={14}>
            <div className="animate-fadeInUp delay-2" style={{ height: "100%" }}>
              <div style={{ background: "rgba(255,255,255,0.025)", backdropFilter: "blur(10px)", border: "1px solid rgba(255,255,255,0.05)", borderRadius: 14, padding: "16px 20px 8px", height: "100%" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 4, paddingBottom: 8, borderBottom: "1px solid rgba(255,255,255,0.03)" }}>
                  <span style={{ color: "rgba(255,255,255,0.45)", fontWeight: 500, fontSize: 11, letterSpacing: 1 }}>
                    <FieldNumberOutlined style={{ marginRight: 6 }} />{'\u5b66'}{'\u79d1'}{'\u661f'}{'\u56fe'}
                  </span>
                  <span style={{ fontSize: 10, color: "rgba(255,255,255,0.15)", letterSpacing: 0.5 }}>
                    {paths.length} {'\u6761'}{'\u5b66'}{'\u4e60'}{'\u8def'}{'\u5f84'}
                  </span>
                </div>
                <KnowledgeConstellation insights="\u6bcf\u70b9\u4eae\u4e00\u9897\u661f\uff0c\u5c31\u638c\u63e1\u4e86\u4e00\u4e2a\u5b66\u79d1\u7684\u6838\u5fc3\u6982\u5ff5" />
              </div>
            </div>
          </Col>
          <Col xs={24} lg={10}>
            <div className="animate-fadeInUp delay-3" style={{ height: "100%" }}>
              <div style={{ background: "rgba(255,255,255,0.025)", backdropFilter: "blur(10px)", border: "1px solid rgba(255,255,255,0.05)", borderRadius: 14, padding: "16px 20px", height: "100%", display: "flex", flexDirection: "column" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", paddingBottom: 8, borderBottom: "1px solid rgba(255,255,255,0.03)" }}>
                  <span style={{ color: "rgba(255,255,255,0.45)", fontWeight: 500, fontSize: 11, letterSpacing: 1 }}>{'\u5fc3'}{'\u6d41'}{'\u4e13'}{'\u6ce8'}</span>
                </div>
                <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center" }}>
                  <FocusFlow
                    focusScore={latestEval?.focus_score ?? 72}
                    sessionMinutes={latestEval?.session_minutes ?? 28}
                    streakDays={latestEval?.streak_days ?? 5}
                  />
                </div>
              </div>
            </div>
          </Col>
        </Row>
      </div>

      <div style={{ position: "relative", zIndex: 1 }}>
        <Text style={{ color: "rgba(255,255,255,0.20)", fontSize: 10, letterSpacing: 1.5, textTransform: "uppercase", display: "block", marginBottom: 14, fontWeight: 600 }}>
          {'\u5b66'}{'\u4e60'}{'\u6570'}{'\u636e'}
        </Text>
        <Row gutter={[16, 16]}>
          <Col xs={24} lg={12}>
            <div className="animate-fadeInUp delay-4" style={{ height: "100%" }}>
              <div style={{ background: "rgba(255,255,255,0.025)", backdropFilter: "blur(10px)", border: "1px solid rgba(255,255,255,0.05)", borderRadius: 14, padding: "22px 24px", height: "100%" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16, paddingBottom: 14, borderBottom: "1px solid rgba(255,255,255,0.04)" }}>
                  <span style={{ color: "rgba(255,255,255,0.85)", fontWeight: 600, fontSize: 14 }}>
                    <ReadOutlined style={{ marginRight: 8 }} />{'\u5b66'}{'\u4e60'}{'\u8def'}{'\u5f84'}
                  </span>
                  <a onClick={() => navigate("/path")} style={{ color: "#818cf8", fontSize: 12, cursor: "pointer", display: "flex", alignItems: "center", gap: 4, opacity: 0.7, transition: "opacity 0.2s" }}
                    onMouseEnter={(e) => e.currentTarget.style.opacity = "1"}
                    onMouseLeave={(e) => e.currentTarget.style.opacity = "0.7"}>
                    {'\u67e5'}{'\u770b'}{'\u5168'}{'\u90e8'} <RightOutlined style={{ fontSize: 10 }} />
                  </a>
                </div>
                {paths.length > 0 ? (
                  <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
                    {paths.slice(0, 3).map((path) => (
                      <div key={path.id}>
                        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
                          <Text style={{ color: "rgba(255,255,255,0.78)", fontSize: 13 }}>
                            {path.path_data?.nodes?.[path.path_data.current_index]?.title || "\u5b66\u4e60\u4e2d"}
                          </Text>
                          <Tag color={path.is_active ? "purple" : "default"}
                            style={{ borderRadius: 6, fontSize: 11, lineHeight: "20px", padding: "0 8px",
                              border: path.is_active ? "1px solid rgba(139,92,246,0.25)" : "1px solid rgba(255,255,255,0.08)",
                              background: path.is_active ? "rgba(139,92,246,0.12)" : "transparent",
                              color: path.is_active ? "#a78bfa" : "rgba(255,255,255,0.30)",
                            }}
                          >
                            {path.is_active ? "\u8fdb\u884c\u4e2d" : "\u5df2\u5b8c\u6210"}
                          </Tag>
                        </div>
                        <Progress percent={Math.round(path.progress * 100)} size="small"
                          strokeColor={{ from: "#06b6d4", to: "#6366f1" }}
                          trailColor="rgba(255,255,255,0.04)"
                        />
                      </div>
                    ))}
                  </div>
                ) : (
                  <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={<span style={{ color: "rgba(255,255,255,0.30)" }}>\u6682\u65e0\u5b66\u4e60\u8def\u5f84</span>} />
                )}
              </div>
            </div>
          </Col>

          <Col xs={24} lg={12}>
            <div style={{ display: "flex", flexDirection: "column", gap: 16, height: "100%" }}>
              <div className="animate-fadeInUp delay-5">
                <div style={{ background: "rgba(255,255,255,0.025)", backdropFilter: "blur(10px)", border: "1px solid rgba(255,255,255,0.05)", borderRadius: 14, padding: "22px 24px" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16, paddingBottom: 14, borderBottom: "1px solid rgba(255,255,255,0.04)" }}>
                    <span style={{ color: "rgba(255,255,255,0.85)", fontWeight: 600, fontSize: 14 }}>
                      <QuestionCircleOutlined style={{ marginRight: 8 }} />{'\u6700'}{'\u8fd1'}{'\u95ee'}{'\u7b54'}
                    </span>
                    <a onClick={() => navigate("/qa")} style={{ color: "#818cf8", fontSize: 12, cursor: "pointer", display: "flex", alignItems: "center", gap: 4, opacity: 0.7, transition: "opacity 0.2s" }}
                      onMouseEnter={(e) => e.currentTarget.style.opacity = "1"}
                      onMouseLeave={(e) => e.currentTarget.style.opacity = "0.7"}>
                      {'\u53bb'}{'\u63d0'}{'\u95ee'} <RightOutlined style={{ fontSize: 10 }} />
                    </a>
                  </div>
                  {recentQA.length > 0 ? (
                    <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                      {recentQA.map((item) => (
                        <div key={item.id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "6px 0" }}>
                          <Text ellipsis style={{ maxWidth: 300, color: "rgba(255,255,255,0.78)", fontSize: 13 }}>
                            {item.question}
                          </Text>
                          {item.answer ? (
                            <CheckCircleOutlined style={{ color: "#34d399", fontSize: 14, flexShrink: 0 }} />
                          ) : (
                            <ClockCircleOutlined style={{ color: "#fbbf24", fontSize: 14, flexShrink: 0 }} />
                          )}
                        </div>
                      ))}
                    </div>
                  ) : (
                    <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={<span style={{ color: "rgba(255,255,255,0.30)" }}>\u6682\u65e0\u95ee\u7b54\u8bb0\u5f55</span>} />
                  )}
                </div>
              </div>
              <div className="animate-fadeInUp delay-6">
                <div style={{ background: "rgba(255,255,255,0.025)", backdropFilter: "blur(10px)", border: "1px solid rgba(255,255,255,0.05)", borderRadius: 14, padding: "12px 20px 8px" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", paddingBottom: 4, borderBottom: "1px solid rgba(255,255,255,0.03)" }}>
                    <span style={{ color: "rgba(255,255,255,0.45)", fontWeight: 500, fontSize: 11, letterSpacing: 1 }}>{'\u4eca'}{'\u65e5'}{'\u5b66'}{'\u4e60'}{'\u8282'}{'\u5f8b'}</span>
                  </div>
                  <LearningRhythm />
                </div>
              </div>
            </div>
          </Col>
        </Row>
      </div>
    </div>
  )
}

export default Dashboard