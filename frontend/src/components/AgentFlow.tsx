import React from "react"
import { Typography } from "antd"

const { Text } = Typography

const agents = [
  { key: "profile", label: "ProfileAgent", desc: "画像提取", color: "#2563eb", angle: -90, icon: "U" },
  { key: "path", label: "PathAgent", desc: "路径规划", color: "#3b82f6", angle: 0, icon: "P" },
  { key: "resource", label: "ResourceAgent", desc: "资源生成", color: "#60a5fa", angle: 90, icon: "R" },
  { key: "eval", label: "EvalAgent", desc: "效果评估", color: "#93c5fd", angle: 180, icon: "E" },
]

const AgentFlow: React.FC = () => {
  const cx = 160
  const cy = 140
  const radius = 90

  return (
    <div style={{ position: "relative", width: "100%", height: 280, overflow: "hidden" }}>
      <style>{`
        @keyframes dotFlow {
          0% { transform: translate(0,0); opacity: 1; }
          100% { transform: translate(var(--tx),var(--ty)); opacity: 0; }
        }
      `}</style>

      <svg width="100%" height="280" style={{ position: "absolute", left: 0, top: 0 }}>
        {agents.map((agent) => {
          const rad = (agent.angle * Math.PI) / 180
          const nx = cx + radius * Math.cos(rad)
          const ny = cy + radius * Math.sin(rad)
          return (
            <g key={agent.key}>
              <line x1={cx} y1={cy} x2={nx} y2={ny} stroke={agent.color} strokeWidth="1" strokeOpacity="0.2" strokeDasharray="4 4" />
              <line x1={cx} y1={cy} x2={nx} y2={ny} stroke={agent.color} strokeWidth="1.5" strokeOpacity="0.5" strokeDasharray="6 8">
                <animate attributeName="stroke-dashoffset" from="0" to="-28" dur="2s" repeatCount="indefinite" />
              </line>
            </g>
          )
        })}
        <circle cx={cx} cy={cy} r={3} fill="#2563eb" opacity="0.6">
          <animate attributeName="r" values="2;4;2" dur="2s" repeatCount="indefinite" />
        </circle>
      </svg>

      <div style={{
        position: "absolute", left: cx - 24, top: cy - 24, width: 48, height: 48,
        borderRadius: "50%", background: "#2563eb",
        display: "flex", alignItems: "center", justifyContent: "center",
        boxShadow: "0 0 0 4px rgba(37,99,235,0.1)", zIndex: 2,
      }}>
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round">
          <circle cx="12" cy="12" r="3" /><path d="M12 1v4" /><path d="M12 19v4" /><path d="M1 12h4" /><path d="M19 12h4" />
          <path d="M4.22 4.22l2.83 2.83" /><path d="M16.95 16.95l2.83 2.83" /><path d="M4.22 19.78l2.83-2.83" /><path d="M16.95 7.05l2.83-2.83" />
        </svg>
      </div>
      <div style={{ position: "absolute", left: cx - 24, top: cy + 28, zIndex: 2 }}>
        <Text style={{ fontSize: 10, color: "#2563eb", fontWeight: 600, letterSpacing: "0.5px" }}>Coordinator</Text>
      </div>

      {agents.map((agent) => {
        const rad = (agent.angle * Math.PI) / 180
        const nx = cx + radius * Math.cos(rad) - 20
        const ny = cy + radius * Math.sin(rad) - 20
        const labelY = cy + (radius + 50) * Math.sin(rad)

        return (
          <div key={agent.key}>
            <div style={{
              position: "absolute", left: nx, top: ny, width: 40, height: 40,
              borderRadius: "50%", background: "#ffffff", border: `2px solid ${agent.color}`,
              display: "flex", alignItems: "center", justifyContent: "center",
              zIndex: 2, boxShadow: "0 2px 8px rgba(0,0,0,0.06)",
            }}>
              <Text style={{ color: agent.color, fontWeight: 700, fontSize: 13 }}>{agent.icon}</Text>
            </div>
            <div style={{
              position: "absolute", left: Math.max(nx - 12, 0), top: labelY + 24,
              textAlign: "center", zIndex: 2, width: 70,
            }}>
              <Text style={{ fontSize: 10, fontWeight: 600, color: agent.color, display: "block", lineHeight: 1.3 }}>
                {agent.desc}
              </Text>
            </div>
          </div>
        )
      })}
    </div>
  )
}

export default AgentFlow