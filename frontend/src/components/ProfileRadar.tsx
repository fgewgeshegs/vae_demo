import React from "react"
import {
  RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
  Radar, ResponsiveContainer,
} from "recharts"

interface Props {
  profileData: Record<string, any>
  size?: "small" | "large"
}

const computeRadarData = (pd: Record<string, any>) => {
  const levelMap: Record<string, number> = { beginner: 25, intermediate: 55, advanced: 90 }
  const kb = (pd.knowledge_base as any) || {}
  const level = ((kb.level as string) || "").toLowerCase()
  const knowledgeBase = levelMap[level] || 15
  const subjectsBonus = ((kb.subjects as string[]) || []).length * 5
  const kbScore = Math.min(knowledgeBase + subjectsBonus, 100)

  const cs = (pd.cognitive_style as any) || {}
  const hasPref = cs.preference ? 50 : 0
  const descLen = ((cs.description as string) || "").length
  const csScore = Math.min(hasPref + Math.min(descLen, 60), 100)

  const lg = (pd.learning_goals as any) || {}
  const shortLen = ((lg.short_term as string) || "").length
  const longLen = ((lg.long_term as string) || "").length
  const goalScore = Math.min((shortLen > 0 ? 40 : 0) + (longLen > 0 ? 40 : 0) + Math.min(shortLen + longLen, 20), 100)

  const gaps = (pd.knowledge_gaps as string[]) || []
  const masteryScore = Math.max(100 - gaps.length * 20, 0)

  const id = (pd.interest_direction as any) || {}
  const areas = (id.areas as string[]) || []
  const interestScore = Math.min(areas.length * 15 + (areas.length > 0 ? 10 : 0), 100)

  const lp = (pd.learning_pace as any) || {}
  const mins = (lp.preferred_session_minutes as number) || 30
  const speedStr = ((lp.speed as string) || "").toLowerCase()
  const speedVal = speedStr === "fast" ? 90 : speedStr === "normal" ? 60 : 30
  const paceScore = Math.round((Math.min(mins, 120) / 120) * 50 + speedVal * 0.5)

  return [
    { dimension: "Knowledge", value: kbScore, full: "知识基础" },
    { dimension: "Cognition", value: csScore, full: "认知风格" },
    { dimension: "Goals", value: goalScore, full: "目标清晰度" },
    { dimension: "Mastery", value: masteryScore, full: "知识掌握" },
    { dimension: "Interest", value: interestScore, full: "兴趣广度" },
    { dimension: "Pace", value: paceScore, full: "学习投入" },
  ]
}

const ProfileRadar: React.FC<Props> = ({ profileData, size = "small" }) => {
  const data = computeRadarData(profileData)
  const outer = size === "large" ? { h: 280, r: 100, cx: "50%", cy: "52%" } : { h: 200, r: 70, cx: "50%", cy: "52%" }

  return (
    <div style={{ width: "100%", height: outer.h }}>
      <ResponsiveContainer width="100%" height="100%">
        <RadarChart data={data} cx={outer.cx} cy={outer.cy} outerRadius={outer.r}>
          <PolarGrid stroke="#e2e8f0" />
          <PolarAngleAxis dataKey="full" tick={{ fontSize: size === "large" ? 11 : 9, fill: "#475569" }} />
          <PolarRadiusAxis angle={30} domain={[0, 100]} tick={false} axisLine={false} />
          <Radar name="Profile" dataKey="value"
            stroke="#2563eb"
            fill="#2563eb"
            fillOpacity={0.12}
            strokeWidth={2}
            animationDuration={1200}
          />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  )
}

export default ProfileRadar