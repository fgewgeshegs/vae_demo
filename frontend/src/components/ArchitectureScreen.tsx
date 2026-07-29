import React from "react"

const BRAND = "#1877F2"

const ArchitectureScreen: React.FC = () => {
  const scrollToTop = () => {
    const el = document.querySelector(".scroll-container")
    el?.scrollTo({ top: 0, behavior: "smooth" })
  }

  return (
    <div style={{
      height: "100vh", scrollSnapAlign: "start", overflow: "hidden",
      background: "radial-gradient(ellipse at 50% 40%, #0F1A2E 0%, #060D18 100%)",
      position: "relative", display: "flex", flexDirection: "column",
      alignItems: "center", justifyContent: "center",
    }}>
      <div style={{
        position: "absolute", inset: 0, pointerEvents: "none", opacity: 0.15,
        backgroundImage: [
          "linear-gradient(rgba(24,119,242,0.06) 1px, transparent 1px)",
          "linear-gradient(90deg, rgba(24,119,242,0.06) 1px, transparent 1px)",
        ].join(", "),
        backgroundSize: "48px 48px",
      }} />
      <div style={{
        position: "absolute", top: "5%", left: "50%", transform: "translateX(-50%)",
        width: "60%", height: "40%", borderRadius: "50%",
        background: "radial-gradient(circle, rgba(24,119,242,0.06), transparent 70%)",
        filter: "blur(60px)", pointerEvents: "none",
      }} />

      <div style={{ textAlign: "center", marginBottom: 24, zIndex: 2 }}>
        <h2 style={{ fontSize: 30, fontWeight: 700, color: "#F1F5F9", margin: 0, letterSpacing: 2, fontFamily: "system-ui,sans-serif" }}>
          {"\u77e5\u5883"}
        </h2>
        <p style={{ fontSize: 13, color: "#64748B", margin: "6px 0 0", letterSpacing: 2, fontFamily: "system-ui,sans-serif" }}>
          多智能体个性化学习平台
        </p>
      </div>

      <div style={{ zIndex: 2, width: "100%", maxWidth: 480, padding: "0 24px" }}>
        <div style={{
          display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12,
        }}>
          {[
            { icon: "U", label: "画像构建", desc: "对话式学习画像", color: "#6366f1" },
            { icon: "P", label: "路径规划", desc: "个性化学习路径", color: "#06b6d4" },
            { icon: "R", label: "资源生成", desc: "多智能体协同", color: "#8b5cf6" },
            { icon: "Q", label: "智能辅导", desc: "即时问答答疑", color: "#f59e0b" },
            { icon: "E", label: "效果评估", desc: "学习效果评估", color: "#ec4899" },
          ].map((item) => (
            <div key={item.label} style={{
              padding: "14px 16px", borderRadius: 12,
              background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.08)",
              backdropFilter: "blur(8px)", textAlign: "center",
            }}>
              <div style={{
                width: 32, height: 32, borderRadius: 8,
                background: item.color, margin: "0 auto 8px",
                display: "flex", alignItems: "center", justifyContent: "center",
                color: "#fff", fontWeight: 700, fontSize: 13,
              }}>{item.icon}</div>
              <div style={{ color: "#E2E8F0", fontSize: 13, fontWeight: 600 }}>{item.label}</div>
              <div style={{ color: "#64748B", fontSize: 11, marginTop: 2 }}>{item.desc}</div>
            </div>
          ))}
        </div>
      </div>

      <div style={{ zIndex: 2, marginTop: 24, textAlign: "center" }}>
        <button
          onClick={() => window.location.href = "/dashboard"}
          style={{
            height: 44, borderRadius: 999, padding: "0 32px",
            background: "transparent", color: "#F1F5F9",
            border: "1px solid rgba(255,255,255,0.25)",
            fontSize: 14, fontWeight: 600, cursor: "pointer", letterSpacing: 1.5,
            transition: "background .25s, border-color .25s",
          }}
          onMouseEnter={e => { e.currentTarget.style.background = "rgba(24,119,242,0.12)"; e.currentTarget.style.borderColor = BRAND }}
          onMouseLeave={e => { e.currentTarget.style.background = "transparent"; e.currentTarget.style.borderColor = "rgba(255,255,255,0.25)" }}
        >
          {"\u8fdb\u5165\u7cfb\u7edf"}
        </button>
      </div>

      <div style={{
        position: "absolute", bottom: 28, left: "50%", transform: "translateX(-50%)",
        zIndex: 2, cursor: "pointer", opacity: 0.4, transition: "opacity .25s",
      }}
        onMouseEnter={e => e.currentTarget.style.opacity = "0.7"}
        onMouseLeave={e => e.currentTarget.style.opacity = "0.4"}
        onClick={scrollToTop}>
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"
          strokeLinecap="round" style={{ color: "#94A3B8" }}>
          <path d="M18 15l-6-6-6 6" />
        </svg>
      </div>
    </div>
  )
}

export default ArchitectureScreen