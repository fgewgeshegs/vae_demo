import React, { useState, useEffect, useMemo, useRef, useCallback } from "react"
import { Form, Button, message } from "antd"
import { UserOutlined, LockOutlined, MailOutlined, EyeOutlined, EyeInvisibleOutlined } from "@ant-design/icons"
import { useNavigate } from "react-router-dom"
import { authApi } from "../services/api"
import { useAuthStore } from "../store"
import ArchitectureScreen from "../components/ArchitectureScreen"

const BRAND = "#1877F2"

/* ========== 自定义输入框 ========== */
const CustomInput: React.FC<{
  icon: React.ReactNode; placeholder?: string; type?: "text" | "password"
  value?: string; onChange?: (e: React.ChangeEvent<HTMLInputElement>) => void
  onFocus?: () => void; onBlur?: () => void
}> = ({ icon, placeholder, type = "text", value, onChange, onFocus, onBlur }) => {
  const [focused, setFocused] = useState(false)
  const [showPwd, setShowPwd] = useState(false)
  return (
    <div style={{
      display: "flex", alignItems: "center", width: "100%", borderRadius: 8,
      border: "1px solid " + (focused ? BRAND : "#DDDFE2"),
      background: focused ? "#EBF5FF" : "#fff",
      transition: "background .15s, border-color .15s", overflow: "hidden",
    }}>
      <div style={{ width: 40, flexShrink: 0, display: "flex", alignItems: "center", justifyContent: "center", color: focused ? BRAND : "#9CA3AF", transition: "color .15s" }}>{icon}</div>
      <input type={type === "password" && !showPwd ? "password" : "text"} value={value ?? ""} onChange={onChange}
        placeholder={placeholder}
        style={{ flex: 1, width: "100%", height: 44, border: "none", background: "transparent", outline: "none", padding: "0 12px 0 0", fontSize: 15, color: focused ? BRAND : "#1D2129", transition: "color .15s", fontFamily: "inherit" }}
        onFocus={() => setFocused(true)} onBlur={() => setFocused(false)} />
      {type === "password" && (
        <button type="button" tabIndex={-1} style={{ flexShrink: 0, width: 36, height: "100%", border: "none", background: "transparent", cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center", padding: 0, color: focused ? BRAND : "#9CA3AF", transition: "color .15s" }}
          onClick={() => setShowPwd(p => !p)}>{showPwd ? <EyeInvisibleOutlined /> : <EyeOutlined />}</button>
      )}
    </div>
  )
}


/* ========== 系统 Logo ========== */
const SystemLogo: React.FC<{ size?: number }> = ({ size = 36 }) => (
  <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
    <div style={{
      width: size, height: size, borderRadius: 10,
      background: "linear-gradient(148deg, #2563EB, #1D4ED8)",
      display: "flex", alignItems: "center", justifyContent: "center",
      border: "1px solid rgba(255,255,255,0.35)",
      boxShadow: "0 8px 24px -6px rgba(29, 110, 240, 0.30)",
    }}>
      <svg viewBox="0 0 24 24" width={size * 0.6} height={size * 0.6} fill="none">
        <path d="M12 2 L20 6 L20 18 L12 22 L4 18 L4 6 Z" stroke="white" strokeWidth="1.5" />
        <path d="M12 6 L16 8 L16 16 L12 18 L8 16 L8 8 Z" stroke="white" strokeWidth="1" opacity="0.4" />
        <circle cx="12" cy="12" r="2" fill="white" opacity="0.8" />
      </svg>
    </div>
    <span style={{
      fontSize: size * 0.55, fontWeight: 700, color: "#1D2129",
      fontFamily: "system-ui,-apple-system,sans-serif", letterSpacing: 1.5,
    }}>知境</span>
  </div>
)

/* ========== 视觉中心 ========== */
const Centerpiece: React.FC = () => (
  <div style={{ position: "relative", width: 300, height: 300 }}>
    <div style={{ position: "absolute", inset: -30, borderRadius: "50%", background: "radial-gradient(circle, rgba(24,119,242,0.05), transparent 70%)", filter: "blur(30px)", animation: "pulseGlow 6s ease-in-out infinite" }} />
    <div style={{ position: "absolute", left: "15%", top: "10%", width: "70%", height: "80%", borderRadius: "50%", background: "radial-gradient(ellipse at 40% 30%, rgba(24,119,242,0.12), transparent 65%)", filter: "blur(35px)", animation: "flow1 14s ease-in-out infinite" }} />
    <div style={{ position: "absolute", left: "10%", top: "15%", width: "55%", height: "65%", borderRadius: "50%", background: "radial-gradient(ellipse at 60% 40%, rgba(139,92,246,0.08), transparent 65%)", filter: "blur(30px)", animation: "flow2 18s ease-in-out infinite" }} />
    <div style={{ position: "absolute", right: "12%", top: "20%", width: "45%", height: "55%", borderRadius: "50%", background: "radial-gradient(ellipse at 30% 50%, rgba(6,182,212,0.06), transparent 65%)", filter: "blur(25px)", animation: "flow3 12s ease-in-out infinite" }} />
    <div style={{ position: "absolute", left: "30%", bottom: "10%", width: "35%", height: "30%", borderRadius: "50%", background: "radial-gradient(ellipse at 50% 50%, rgba(251,191,36,0.03), transparent 65%)", filter: "blur(20px)", animation: "flow4 16s ease-in-out infinite" }} />
    <div style={{ position: "absolute", left: 0, top: 0, width: "100%", height: "100%", zIndex: 5, pointerEvents: "none", animation: "sunMove 10s linear infinite" }}>
      <div style={{ position: "absolute", left: "50%", top: "50%", transform: "translate(-50%,-50%)", width: 90, height: 90, borderRadius: "50%", background: "radial-gradient(circle at 38% 30%, rgba(24,119,242,0.15), rgba(24,119,242,0.04) 50%, transparent 70%)", filter: "blur(8px)", animation: "pulseGlow 4s ease-in-out infinite" }} />
      <div style={{ position: "absolute", left: "50%", top: "50%", transform: "translate(-50%,-50%)", width: 30, height: 30, borderRadius: "50%", background: "radial-gradient(circle at 40% 30%, rgba(24,119,242,0.35), rgba(24,119,242,0.10) 50%, transparent 70%)", boxShadow: "0 0 50px rgba(24,119,242,0.10)", animation: "pulseGlow 3s ease-in-out infinite" }} />
    </div>
  </div>
)

const AuroraBackground: React.FC = () => {
  const particles = React.useMemo(() =>
    Array.from({ length: 8 }, (_, i) => ({
      l: 10 + (i * 8.7 + 3) % 82, t: 6 + (i * 12.3 + 7) % 84,
      s: 3 + (i % 3), d: 8 + (i % 4) * 1.8,
      dl: (i * 1.1 + 0.2) % 5, kf: i % 4 + 1,
    })), [])

  return (
    <div style={{ position: "absolute", inset: 0, zIndex: 1, pointerEvents: "none", overflow: "hidden" }}>
      <style>{`
        @keyframes aurora1 {
          0%   { transform: translate(0,0) scale(1); } 33% { transform: translate(50px,-35px) scale(1.06); }
          66%  { transform: translate(-25px,25px) scale(0.94); } 100% { transform: translate(0,0) scale(1); }
        } @keyframes aurora2 {
          0%   { transform: translate(0,0) scale(1); } 50% { transform: translate(-40px,45px) scale(1.08); }
          100% { transform: translate(0,0) scale(1); }
        } @keyframes aurora3 {
          0%   { transform: translate(0,0) rotate(0deg); } 50% { transform: translate(30px,-25px) rotate(6deg); }
          100% { transform: translate(0,0) rotate(0deg); }
        } @keyframes aurora4 {
          0%   { transform: translate(0,0) scale(1); } 50% { transform: translate(-20px,30px) scale(1.12); }
          100% { transform: translate(0,0) scale(1); }
        } @keyframes flow1 {
          0%,100% { transform: translate(0,0) scale(1); }
          25% { transform: translate(55px,-40px) scale(1.08); }
          50% { transform: translate(-35px,30px) scale(0.92); }
          75% { transform: translate(40px,45px) scale(1.05); }
        } @keyframes flow2 {
          0%,100% { transform: translate(0,0) scale(1); }
          33% { transform: translate(-50px,35px) scale(1.12); }
          66% { transform: translate(30px,-40px) scale(0.88); }
        } @keyframes flow3 {
          0%,100% { transform: translate(0,0) scale(1); }
          50% { transform: translate(45px,45px) scale(1.06); }
        } @keyframes flow4 {
          0%,100% { transform: translate(0,0) scale(1) rotate(0deg); }
          50% { transform: translate(-35px,-25px) scale(0.92) rotate(12deg); }
        } @keyframes sunMove {
          0% { transform: translateX(-180px); opacity: 0; }
          8% { opacity: 0.5; }
          15% { opacity: 1; }
          80% { opacity: 1; }
          92% { opacity: 0.5; }
          100% { transform: translateX(180px); opacity: 0; }
        }
        @keyframes pulseGlow {
          0%,100% { transform: scale(1); opacity: .7; }
          50% { transform: scale(1.06); opacity: 1; }
        } @keyframes pdrft1 {
          0%,100% { transform: translate(0,0); opacity: .35; } 25% { transform: translate(22px,-28px); opacity: .70; }
          50% { transform: translate(-14px,14px); opacity: .20; } 75% { transform: translate(26px,8px); opacity: .55; }
        } @keyframes pdrft2 {
          0%,100% { transform: translate(0,0); opacity: .30; } 33% { transform: translate(-26px,-18px); opacity: .65; }
          66% { transform: translate(16px,24px); opacity: .15; }
        } @keyframes pdrft3 {
          0%,100% { transform: translate(0,0); opacity: .25; } 50% { transform: translate(-12px,30px); opacity: .60; }
        } @keyframes pdrft4 {
          0%,100% { transform: translate(0,0); opacity: .30; } 30% { transform: translate(28px,12px); opacity: .70; }
          70% { transform: translate(-16px,-22px); opacity: .15; }
        }
      `}</style>
      <div style={{ position: "absolute", left: "6%", top: "12%", width: 460, height: 460, borderRadius: "50%", zIndex: 1, background: "radial-gradient(circle, rgba(24,119,242,0.10), transparent 65%)", filter: "blur(65px)", animation: "aurora1 10s ease-in-out infinite" }} />
      <div style={{ position: "absolute", right: "2%", top: "35%", width: 360, height: 360, borderRadius: "50%", zIndex: 1, background: "radial-gradient(circle, rgba(139,92,246,0.07), transparent 65%)", filter: "blur(55px)", animation: "aurora2 12s ease-in-out infinite" }} />
      <div style={{ position: "absolute", left: "25%", bottom: "5%", width: 420, height: 420, borderRadius: "50%", zIndex: 1, background: "radial-gradient(circle, rgba(6,182,212,0.06), transparent 65%)", filter: "blur(70px)", animation: "aurora3 9s ease-in-out infinite" }} />
      <div style={{ position: "absolute", right: "10%", top: "8%", width: 200, height: 200, borderRadius: "50%", zIndex: 1, background: "radial-gradient(circle, rgba(251,191,36,0.04), transparent 65%)", filter: "blur(45px)", animation: "aurora4 11s ease-in-out infinite" }} />

      {particles.map((p, i) => (
        <div key={i} style={{
          position: "absolute", left: `${p.l}%`, top: `${p.t}%`,
          width: p.s, height: p.s, borderRadius: "50%", zIndex: 1,
          background: "rgba(24,119,242,0.40)",
          boxShadow: "0 0 6px rgba(24,119,242,0.25), 0 0 12px rgba(24,119,242,0.08)",
          animation: `pdrft${p.kf} ${p.d}s ease-in-out infinite`,
          animationDelay: `${p.dl}s`,
        }} />
      ))}
    </div>
  )
}

const TabBar: React.FC<{ active: "login" | "register"; onChange: (k: "login" | "register") => void }> = ({ active, onChange }) => {
  const idx = active === "login" ? 0 : 1
  return (
    <div style={{ display: "flex", borderBottom: "1px solid #E5E7EB", marginBottom: 24, position: "relative", width: "100%" }}>
      {(["登录", "注册"] as const).map((label, i) => (
        <button key={label} onClick={() => onChange(i === 0 ? "login" : "register")} style={{
          flex: 1, background: "none", border: "none", padding: "0 0 12px", cursor: "pointer",
          fontSize: 15, fontWeight: active === (i === 0 ? "login" : "register") ? 600 : 400,
          color: active === (i === 0 ? "login" : "register") ? "#1D2129" : "#8A8D91", letterSpacing: 1, transition: "color .2s",
        }}>{label}</button>
      ))}
      <div style={{ position: "absolute", bottom: 0, left: `${idx * 50}%`, width: "50%", height: 2, background: BRAND, borderRadius: 1, transition: "left .25s ease" }} />
    </div>
  )
}

const LoginPage: React.FC = () => {
  const [loading, setLoading] = useState(false)
  const [activeTab, setActiveTab] = useState<"login" | "register">("login")
  const [isMobile, setIsMobile] = useState(false)
  const navigate = useNavigate()
  const setAuth = useAuthStore((s) => s.setAuth)

  useEffect(() => {
    const check = () => setIsMobile(window.innerWidth <= 900)
    check()
    window.addEventListener("resize", check)
    return () => window.removeEventListener("resize", check)
  }, [])

  const handleLogin = async (values: { username: string; password: string }) => {
    setLoading(true)
    try { const res = await authApi.login(values.username, values.password); setAuth(res.data.access_token, res.data.user); message.success("登录成功"); navigate("/dashboard") }
    catch (err: unknown) { message.error((err as any)?.response?.data?.detail || "登录失败，请检查用户名和密码") }
    finally { setLoading(false) }
  }
  const handleRegister = async (values: { username: string; email: string; password: string; confirm: string }) => {
    if (values.password !== values.confirm) { message.error("两次密码不一致"); return }
    setLoading(true)
    try { const res = await authApi.register({ username: values.username, email: values.email, password: values.password }); setAuth(res.data.access_token, res.data.user); message.success("注册成功"); navigate("/dashboard") }
    catch (err: unknown) { message.error((err as any)?.response?.data?.detail || "注册失败，请检查信息") }
    finally { setLoading(false) }
  }
  const btnStyle: React.CSSProperties = { height: 44, borderRadius: 999, fontSize: 16, fontWeight: 600, display: "flex", alignItems: "center", justifyContent: "center", width: "100%", border: "none", cursor: "pointer", transition: "background .15s, transform .1s" }
  const inputField = (icon: React.ReactNode, placeholder: string, name: string, type: "text" | "password" = "text", extraRules?: any) => (
    <Form.Item name={name} rules={[{ required: true, message: "请填写此项" }, ...(extraRules || [])]} style={{ marginBottom: 12 }}>
      <CustomInput icon={icon} placeholder={placeholder} type={type} />
    </Form.Item>
  )
  const renderLoginForm = () => (
    <Form onFinish={handleLogin} layout="vertical" requiredMark={false} size="large">
      {inputField(<UserOutlined />, "用户名", "username")}
      {inputField(<LockOutlined />, "密码", "password", "password")}
      <div style={{ marginTop: 4 }}><Button type="primary" htmlType="submit" loading={loading} style={{ ...btnStyle, background: BRAND, boxShadow: "0 2px 8px rgba(24,119,242,0.15)" }} className="fb-btn-primary">登录</Button></div>
    </Form>
  )
  const renderRegisterForm = () => (
    <Form onFinish={handleRegister} layout="vertical" requiredMark={false} size="large">
      {inputField(<UserOutlined />, "用户名", "username")}
      {inputField(<MailOutlined />, "邮箱", "email", "text", [{ type: "email", message: "请输入有效邮箱" }])}
      {inputField(<LockOutlined />, "密码", "password", "password", [{ min: 6, message: "密码至少6位" }])}
      {inputField(<LockOutlined />, "确认密码", "confirm", "password")}
      <div style={{ marginTop: 4 }}><Button type="primary" htmlType="submit" loading={loading} style={{ ...btnStyle, background: BRAND, boxShadow: "0 2px 8px rgba(24,119,242,0.15)" }} className="fb-btn-primary">注册</Button></div>
    </Form>
  )

  const css = `.fb-btn-primary:hover{background:#1869D6!important}.fb-btn-primary:active{transform:scale(0.98)!important;background:#1558b0!important}.fb-link:hover{text-decoration:underline!important}.fb-ghost:hover{background:rgba(24,119,242,0.04)!important;box-shadow:0 2px 8px rgba(24,119,242,0.08)!important}.fb-ghost:active{transform:scale(0.98)!important}
@keyframes bounceDown { 0%,100% { transform: translateY(0); opacity: 0.4; } 50% { transform: translateY(8px); opacity: 1; } }`

  const containerRef = useRef<HTMLDivElement>(null)
  const isScrolling = useRef(false)
  const pageRef = useRef(0)
  const [page, setPage] = useState(0)

  const smoothScrollTo = useCallback((targetPage: number, duration = 200) => {
    const el = containerRef.current
    if (!el || isScrolling.current) return
    const startY = el.scrollTop
    const targetY = targetPage * window.innerHeight
    if (startY === targetY) return
    const startTime = performance.now()
    isScrolling.current = true
    const animate = (time: number) => {
      const p = Math.min((time - startTime) / duration, 1)
      const ease = p < 0.5 ? 4 * p * p * p : 1 - Math.pow(-2 * p + 2, 3) / 2
      el.scrollTop = startY + (targetY - startY) * ease
      if (p < 1) requestAnimationFrame(animate)
      else { isScrolling.current = false; pageRef.current = targetPage; setPage(targetPage) }
    }
    requestAnimationFrame(animate)
  }, [])

  useEffect(() => {
    const el = containerRef.current
    if (!el) return
    const onWheel = (e: WheelEvent) => {
      if (isScrolling.current) { e.preventDefault(); return }
      const dir = e.deltaY > 0 ? 1 : -1
      const next = Math.max(0, Math.min(1, pageRef.current + dir))
      if (next === pageRef.current) return
      e.preventDefault()
      smoothScrollTo(next, 1200)
    }
    el.addEventListener("wheel", onWheel, { passive: false })
    return () => el.removeEventListener("wheel", onWheel)
  }, [smoothScrollTo])

  useEffect(() => {
    const el = containerRef.current
    if (!el) return
    const onScroll = () => {
      if (isScrolling.current) return
      const cur = Math.round(el.scrollTop / window.innerHeight)
      if (cur !== pageRef.current) { pageRef.current = cur; setPage(cur) }
    }
    el.addEventListener("scroll", onScroll)
    return () => el.removeEventListener("scroll", onScroll)
  }, [])

  if (isMobile) return (
    <div style={{ height: "100vh", background: "#F9FAFB", display: "flex", flexDirection: "column" }}>
      <style>{css}</style>
      <div style={{ background: "linear-gradient(180deg, #f0f5ff 0%, #fff 100%)", padding: "56px 24px 28px", display: "flex", flexDirection: "column", alignItems: "center", position: "relative" }}>
        <div style={{ position: "absolute", top: 32, left: 24 }}><SystemLogo /></div>
        <div style={{ transform: "scale(0.55)", transformOrigin: "center center", margin: "-40px 0" }}><Centerpiece /></div>
        <p style={{ fontSize: 26, fontWeight: 700, color: "#1D2129", margin: "0 0 0", textAlign: "center", letterSpacing: "-.3px" }}>探索知识的<span style={{ color: BRAND }}>无限</span>可能。</p>
      </div>
      <div style={{ flex: 1, padding: "16px 16px 32px", display: "flex", flexDirection: "column", alignItems: "center" }}>
        <div style={{ width: "100%", maxWidth: 380 }}>
          <TabBar active={activeTab} onChange={setActiveTab} />
          {activeTab === "login" ? renderLoginForm() : renderRegisterForm()}
          <div style={{ fontSize: 11, color: "#9CA3AF", letterSpacing: ".5px", fontWeight: 500, textAlign: "center", marginTop: 24 }}>知境 路 Zhijing</div>
        </div>
      </div>
    </div>
  )

  return (
    <React.Fragment>
    <div ref={containerRef} style={{ height: "100vh", overflowY: "scroll", scrollBehavior: "smooth" }}>
      <div style={{ height: "100vh", overflow: "hidden" }}>
        <div style={{ height: "100vh", background: "#fff", display: "flex" }}>
      <style>{css}</style>

      {/* ===== 左栏 55% ===== */}
      <div style={{
        width: "55%", position: "relative",
        display: "flex", flexDirection: "column",
        alignItems: "center", justifyContent: "center",
        background: "#F9FAFB", overflow: "hidden",
      }}>
        {/* 极光 + 粒子 */}
        <AuroraBackground />

        {/* Logo */}
        <div style={{ position: "absolute", top: 40, left: 40, zIndex: 5 }}><SystemLogo /></div>

        {/* 视觉中心 — 发光环体 */}
        <div style={{ position: "absolute", left: "50%", top: "50%", transform: "translate(-50%,-55%)", zIndex: 2 }}>
          <Centerpiece />
        </div>

        {/* Slogan */}
        <div style={{ position: "absolute", bottom: "15%", left: "12%", zIndex: 5 }}>
          <p style={{ fontSize: 40, fontWeight: 700, lineHeight: 1.35, letterSpacing: "-.5px", color: "#1D2129", margin: 0 }}>
            探索知识的<br /><span style={{ color: BRAND }}>无限</span>可能。
          </p>
        </div>
      </div>

      {/* 分割线 */}
      <div style={{ width: 1, background: "#E5E7EB", flexShrink: 0 }} />

      {/* ===== 右栏 45% ===== */}
      <div style={{
        width: "45%", padding: "40px 10%",
        display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center",
      }}>
        <div style={{ width: "100%", maxWidth: 380, marginTop: "-5%" }}>
          <TabBar active={activeTab} onChange={setActiveTab} />
          {activeTab === "login" ? renderLoginForm() : renderRegisterForm()}
          <div style={{ fontSize: 11, color: "#9CA3AF", letterSpacing: "1px", fontWeight: 500, textAlign: "center", marginTop: 28 }}>知境 路 Zhijing</div>
        </div>
      </div>
    </div>
    </div>    <ArchitectureScreen />
    </div>
    <div style={{ position: "fixed", right: 14, top: "50%", transform: "translateY(-50%)", zIndex: 100, display: "flex", flexDirection: "column", gap: 10, pointerEvents: "none" }}>
      <div style={{ width: 8, height: 8, borderRadius: "50%", background: page === 0 ? "#1877F2" : "rgba(0,0,0,0.12)", transition: "background .3s", boxShadow: page === 0 ? "0 0 8px rgba(24,119,242,0.3)" : "none" }} />
      <div style={{ width: 8, height: 8, borderRadius: "50%", background: page === 1 ? "#1877F2" : "rgba(0,0,0,0.12)", transition: "background .3s", boxShadow: page === 1 ? "0 0 8px rgba(24,119,242,0.3)" : "none" }} />
    </div>
    {page === 0 && <div style={{ position: "fixed", bottom: 20, left: "50%", transform: "translateX(-50%)", zIndex: 100, animation: "bounceDown 2s ease-in-out infinite", cursor: "pointer" }} onClick={() => smoothScrollTo(1)}>
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#1877F2" strokeWidth="2" strokeLinecap="round"><path d="M12 5v14M5 12l7 7 7-7"/></svg>
    </div>}
  </React.Fragment>
  )
}

export default LoginPage
