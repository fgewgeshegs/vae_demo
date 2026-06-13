import React, { useEffect, useState } from "react"
import { Layout, Menu, Avatar, Dropdown, Typography, Space } from "antd"
import { Outlet, useNavigate, useLocation } from "react-router-dom"
import {
  DashboardOutlined, UserOutlined, DeploymentUnitOutlined,
  FileTextOutlined, QuestionCircleOutlined, BarChartOutlined,
  BookOutlined, SearchOutlined, SettingOutlined, LogoutOutlined,
  AppstoreOutlined, ReadOutlined, FolderOpenOutlined, SmileOutlined
} from "@ant-design/icons"
import { useAuthStore, useUIStore } from "../store"
import QuickThoughtFAB from "../components/QuickThoughtFAB"

const { Header, Sider, Content } = Layout
const { Text } = Typography

const modes = [
  { key: "dashboard", label: "\u4eea\u8868\u76d8", icon: <AppstoreOutlined />, glow: "#6366f1" },
  { key: "learn",     label: "\u5b66\u4e60",   icon: <ReadOutlined />,     glow: "#06b6d4" },
  { key: "resources", label: "\u8d44\u6e90",   icon: <FolderOpenOutlined />, glow: "#8b5cf6" },
  { key: "profile",   label: "\u4e2a\u4eba",   icon: <SmileOutlined />,    glow: "#ec4899" },
]

const modeMenu: Record<string, { key: string; icon: React.ReactNode; label: string }[]> = {
  dashboard: [],
  learn: [
    { key: "/path",   icon: <DeploymentUnitOutlined />, label: "\u5b66\u4e60\u8def\u5f84" },
    { key: "/qa",     icon: <QuestionCircleOutlined />, label: "\u667a\u80fd\u8f85\u5bfc" },
    { key: "/courses",icon: <BookOutlined />,           label: "\u8bfe\u7a0b\u7ba1\u7406" },
  ],
  resources: [
    { key: "/resources", icon: <FileTextOutlined />, label: "\u8d44\u6e90\u4e2d\u5fc3" },
    { key: "/search",    icon: <SearchOutlined />,   label: "\u77e5\u8bc6\u68c0\u7d22" },
  ],
  profile: [
    { key: "/profile",     icon: <UserOutlined />,     label: "\u5bf9\u8bdd\u753b\u50cf" },
    { key: "/evaluation",  icon: <BarChartOutlined />, label: "\u5b66\u4e60\u8bc4\u4f30" },
    { key: "/settings",    icon: <SettingOutlined />,  label: "\u7cfb\u7edf\u8bbe\u7f6e" },
  ],
}

const pathToMode = (path: string): string => {
  if (path === "/dashboard")   return "dashboard"
  if (["/path","/qa","/courses"].includes(path)) return "learn"
  if (["/resources","/search"].includes(path))   return "resources"
  if (["/profile","/evaluation","/settings"].includes(path)) return "profile"
  return "dashboard"
}

const AppLayout: React.FC = () => {
  const navigate = useNavigate()
  const location = useLocation()
  const { user, logout } = useAuthStore()
  const { sidebarCollapsed, toggleSidebar } = useUIStore()

  const currentMode = pathToMode(location.pathname)
  const currentModeMeta = modes.find((m) => m.key === currentMode) || modes[0]
  const menuItems = modeMenu[currentMode] || []
  const showSidebar = menuItems.length > 0

  const [ambientColor, setAmbientColor] = useState(currentModeMeta.glow)
  useEffect(() => {
    setAmbientColor(currentModeMeta.glow)
  }, [currentModeMeta.glow])

  const handleLogout = () => { logout(); navigate("/login") }
  const userMenuItems = [
    { key: "profile", icon: <UserOutlined />, label: "\u4e2a\u4eba\u753b\u50cf", onClick: () => navigate("/profile") },
    { type: "divider" as const },
    { key: "logout", icon: <LogoutOutlined />, label: "\u9000\u51fa\u767b\u5f55", onClick: handleLogout },
  ]

  return (
    <Layout style={{ minHeight: "100vh", background: "var(--bg-primary)", position: "relative" }}>
      <div style={{
        position: "fixed", top: -200, left: "50%", transform: "translateX(-50%)",
        width: 600, height: 600, borderRadius: "50%",
        background: 'radial-gradient(circle, ' + ambientColor + '08 0%, transparent 70%)',
        pointerEvents: "none", zIndex: 0,
        transition: 'background 1.2s cubic-bezier(0.19,1,0.22,1)',
      }} />
      <div style={{
        position: "fixed", bottom: -150, right: -100,
        width: 400, height: 400, borderRadius: "50%",
        background: 'radial-gradient(circle, ' + ambientColor + '06 0%, transparent 70%)',
        pointerEvents: "none", zIndex: 0,
        transition: 'background 1.2s cubic-bezier(0.19,1,0.22,1)',
      }} />
      <div style={{
        position: "fixed", top: 0, left: 0, right: 0, height: 1, zIndex: 9999,
        background: 'linear-gradient(90deg, transparent, ' + ambientColor + '44, transparent)',
        animation: 'ambientShift 3s ease-in-out infinite',
      }} />

      <QuickThoughtFAB />

      <Header style={{
        height: 64, lineHeight: "64px",
        background: "rgba(7,11,23,0.85)",
        backdropFilter: "blur(20px) saturate(1.4)",
        WebkitBackdropFilter: "blur(20px) saturate(1.4)",
        borderBottom: "1px solid rgba(255,255,255,0.05)",
        display: "flex", alignItems: "center", justifyContent: "space-between",
        padding: "0 32px", position: "sticky", top: 0, zIndex: 200,
      }}>
        <Space size={40} style={{ alignItems: "center" }}>
          <Space style={{ cursor: "pointer", alignItems: "center", gap: 10 }}
            onClick={() => navigate("/dashboard")}
          >
            <div style={{ width: 30, height: 30, borderRadius: 8, background: "linear-gradient(135deg, #06b6d4, #6366f1)", boxShadow: "0 0 20px rgba(99,102,241,0.3)", display: "flex", alignItems: "center", justifyContent: "center" }}>
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M12 2a7 7 0 0 1 7 7c0 2.4-1.2 4.5-3 5.7V18a1 1 0 0 1-1 1H9a1 1 0 0 1-1-1v-3.3C6.2 13.5 5 11.4 5 9a7 7 0 0 1 7-7z" />
                <path d="M9 21h6" />
              </svg>
            </div>
            <Text style={{ fontSize: 17, fontWeight: 700, letterSpacing: -0.3, background: "linear-gradient(135deg, #06b6d4, #a5b4fc)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>
              Neural
            </Text>
          </Space>

          <Space size={4} style={{ background: "rgba(255,255,255,0.035)", borderRadius: 12, padding: 3, border: "1px solid rgba(255,255,255,0.05)" }}>
            {modes.map((m) => {
              const active = currentMode === m.key
              return (
                <div key={m.key} onClick={() => {
                  if (m.key === "dashboard") navigate("/dashboard")
                  else if (m.key === "learn") navigate("/path")
                  else if (m.key === "resources") navigate("/resources")
                  else if (m.key === "profile") navigate("/profile")
                }} style={{
                  display: "flex", alignItems: "center", gap: 7,
                  padding: "7px 16px", borderRadius: 9, cursor: "pointer",
                  transition: "all 0.35s cubic-bezier(0.19,1,0.22,1)",
                  background: active ? 'linear-gradient(135deg, ' + m.glow + '33, ' + m.glow + '22)' : "transparent",
                  boxShadow: active ? '0 0 20px ' + m.glow + '1a, inset 0 1px 0 rgba(255,255,255,0.06)' : "none",
                  color: active ? "#fff" : "rgba(255,255,255,0.40)",
                  fontWeight: active ? 600 : 500, fontSize: 14, userSelect: "none",
                }} onMouseEnter={(e) => { if (!active) e.currentTarget.style.background = "rgba(255,255,255,0.05)" }}
                onMouseLeave={(e) => { if (!active) e.currentTarget.style.background = "transparent" }}>
                  <span style={{ fontSize: 16, opacity: active ? 1 : 0.5 }}>{m.icon}</span>
                  <span>{m.label}</span>
                </div>
              )
            })}
          </Space>
        </Space>

        <Dropdown menu={{ items: userMenuItems }} placement="bottomRight">
          <div style={{ cursor: "pointer", display: "flex", alignItems: "center", gap: 10, padding: "4px 10px", borderRadius: 8, transition: "background 0.2s" }} className="header-user-btn">
            <Avatar icon={<UserOutlined />} style={{ background: "linear-gradient(135deg, #6366f1, #8b5cf6)", boxShadow: "0 0 14px rgba(99,102,241,0.25)" }} />
            <Text style={{ color: "rgba(255,255,255,0.80)", fontSize: 14 }}>{user?.display_name || user?.username}</Text>
          </div>
        </Dropdown>
      </Header>

      <Layout style={{ background: "var(--bg-primary)", position: "relative", zIndex: 1 }}>
        {showSidebar && (
          <Sider trigger={null} collapsible collapsed={sidebarCollapsed} width={200} collapsedWidth={0}
            theme="dark" style={{ background: "transparent", borderRight: "1px solid rgba(255,255,255,0.03)", overflow: "hidden", transition: "all 0.3s cubic-bezier(0.4,0,0.2,1)" }}>
            <div style={{ height: 44, display: "flex", alignItems: "center", padding: "0 20px", borderBottom: "1px solid rgba(255,255,255,0.03)" }}>
              <Text style={{ color: "rgba(255,255,255,0.20)", fontSize: 10, letterSpacing: 1.5, textTransform: "uppercase", fontWeight: 600 }}>
                {modes.find((m) => m.key === currentMode)?.label || ""}
              </Text>
            </div>
            <Menu theme="dark" mode="inline" selectedKeys={[location.pathname]} items={menuItems}
              onClick={({ key }) => navigate(key)} style={{ background: "transparent", borderRight: "none", paddingTop: 6 }}
            />
          </Sider>
        )}
        <Content style={{
          padding: showSidebar ? "28px 32px" : "28px 32px",
          minHeight: "calc(100vh - 64px)",
          animation: "fadeInUp 0.5s cubic-bezier(0.19,1,0.22,1)",
          maxWidth: showSidebar ? undefined : 1200,
          margin: showSidebar ? undefined : "0 auto",
          width: "100%",
        }}>
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  )
}

export default AppLayout