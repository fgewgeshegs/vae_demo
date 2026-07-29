import React, { useEffect, useState } from 'react'
import { Avatar, Breadcrumb, FloatButton, Layout } from 'antd'
import { Outlet, useLocation, useNavigate } from 'react-router-dom'
import {
  ApartmentOutlined, BookOutlined, CheckCircleOutlined, DashboardOutlined,
  FolderOpenOutlined, MenuFoldOutlined, MenuUnfoldOutlined, QuestionCircleOutlined, SettingOutlined,
  ThunderboltOutlined, UserOutlined, VerticalAlignTopOutlined,
} from '@ant-design/icons'
import { useAuthStore } from '../store'
import QuickThoughtFAB from './QuickThoughtFAB'
import './AppLayout.css'

const { Content, Sider } = Layout

type NavItem = { key: string; label: string; route: string; icon: React.ReactNode }

const learningItems: NavItem[] = [
  { key: 'profile', label: '学习画像', route: '/profile', icon: <UserOutlined /> },
  { key: 'path', label: '学习路径', route: '/path', icon: <ApartmentOutlined /> },
  { key: 'resources', label: '资源中心', route: '/resources', icon: <FolderOpenOutlined /> },
  { key: 'qa', label: '智能辅导', route: '/qa', icon: <QuestionCircleOutlined /> },
  { key: 'evaluation', label: '学习评估', route: '/evaluation', icon: <CheckCircleOutlined /> },
]

const systemItems: NavItem[] = [
  { key: 'courses', label: '课程管理', route: '/courses', icon: <BookOutlined /> },
  { key: 'agent', label: 'Agent 工作台', route: '/agent', icon: <ThunderboltOutlined /> },
  { key: 'settings', label: '系统设置', route: '/settings', icon: <SettingOutlined /> },
]

const dashboardItem: NavItem = { key: 'dashboard', label: '仪表盘', route: '/dashboard', icon: <DashboardOutlined /> }

const pageNames: Record<string, string> = {
  '/dashboard': '仪表盘', '/profile': '学习画像', '/path': '学习路径', '/resources': '资源中心',
  '/qa': '智能辅导', '/evaluation': '学习评估', '/courses': '课程管理', '/agent': 'Agent 工作台', '/settings': '系统设置',
}

const AppLayout: React.FC = () => {
  const navigate = useNavigate()
  const location = useLocation()
  const { user } = useAuthStore()
  const [isMobile, setIsMobile] = useState(() => window.innerWidth < 768)
  const [sidebarOpen, setSidebarOpen] = useState(() => window.innerWidth >= 768)
  const [showTop, setShowTop] = useState(false)

  useEffect(() => {
    const onScroll = () => setShowTop(window.scrollY > 400)
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  useEffect(() => {
    const onResize = () => {
      const nextIsMobile = window.innerWidth < 768
      setIsMobile(nextIsMobile)
      if (nextIsMobile) setSidebarOpen(false)
    }
    window.addEventListener('resize', onResize)
    return () => window.removeEventListener('resize', onResize)
  }, [])


  const renderNavItem = (item: NavItem) => {
    const active = item.route === location.pathname
    return <button key={item.key} type="button" className={`workspace-nav-item ${active ? 'is-active' : ''}`} onClick={() => navigate(item.route)} title={item.label}>
      <span className="workspace-nav-icon">{item.icon}</span>
      <span>{item.label}</span>
    </button>
  }

  return (
    <Layout className="workspace-layout">
      <Layout className="workspace-body">
        <Sider trigger={null} collapsible collapsed={!sidebarOpen} collapsedWidth={isMobile ? 0 : 68} width={248} className="workspace-sider">
          <nav className="workspace-navigation" aria-label="学习工作台导航">
            <div className="workspace-brand">
              <button type="button" className="workspace-brand-button" onClick={() => navigate('/dashboard')} title="学习工作台首页">
                <span className="workspace-brand-mark"><ThunderboltOutlined /></span>
                <span className="workspace-brand-name">知境</span>
              </button>
              <button type="button" className="workspace-sidebar-toggle" onClick={() => setSidebarOpen(!sidebarOpen)} title={sidebarOpen ? '收起导航' : '展开导航'} aria-label={sidebarOpen ? '收起导航' : '展开导航'}>
                {sidebarOpen ? <MenuFoldOutlined /> : <MenuUnfoldOutlined />}
              </button>
            </div>
            <span className="workspace-section-label">学习工作台</span>
            {renderNavItem(dashboardItem)}
            <span className="workspace-section-label workspace-section-gap">学习闭环</span>
            {learningItems.map(renderNavItem)}
            <span className="workspace-section-label workspace-section-gap">课程与系统</span>
            {systemItems.map(renderNavItem)}
          </nav>
          <div className="workspace-profile-card" title={user?.display_name || user?.username || '学习者'}>
            <Avatar icon={<UserOutlined />} />
            <div><strong>{user?.display_name || user?.username || '学习者'}</strong><span>学习空间已就绪</span></div>
          </div>
        </Sider>

        <Layout className={`workspace-main ${location.pathname === '/dashboard' ? 'workspace-main--dashboard' : 'workspace-main--workspace'}`}>
          <header className="workspace-topbar">
            <div className="workspace-page-context">
              <button type="button" className="workspace-menu-button" onClick={() => setSidebarOpen(!sidebarOpen)} aria-label={sidebarOpen ? '收起导航' : '展开导航'}>
                {sidebarOpen ? <MenuFoldOutlined /> : <MenuUnfoldOutlined />}
              </button>
              <div>
                <Breadcrumb items={[{ title: '学习工作台' }, { title: pageNames[location.pathname] || '工作区' }]} />
                <strong>{pageNames[location.pathname] || '工作区'}</strong>
              </div>
            </div>
            <button type="button" className="workspace-account-button" onClick={() => navigate('/profile')} aria-label="查看学习画像">
              <Avatar size={30} icon={<UserOutlined />} />
              <span>{user?.display_name || user?.username || '学习者'}</span>
            </button>
          </header>
          <Content className={`workspace-content ${location.pathname === '/dashboard' ? 'workspace-content--dashboard' : 'workspace-content--workspace'}`}>
            <div className="fade-in"><Outlet /></div>
          </Content>
        </Layout>
      </Layout>

      {!sidebarOpen && <button type="button" className="workspace-expand-rail" onClick={() => setSidebarOpen(true)} title="展开导航"><MenuFoldOutlined /></button>}
      <QuickThoughtFAB />
      {showTop && <FloatButton icon={<VerticalAlignTopOutlined />} type="default" className="workspace-back-top" onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })} />}
    </Layout>
  )
}

export default AppLayout
