import React from 'react'
import { Layout, Menu, Avatar, Dropdown, Button, Typography } from 'antd'
import { Outlet, useNavigate, useLocation } from 'react-router-dom'
import {
  DashboardOutlined,
  UserOutlined,
  DeploymentUnitOutlined,
  FileTextOutlined,
  QuestionCircleOutlined,
  BarChartOutlined,
  BookOutlined,
  SearchOutlined,
  SettingOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  LogoutOutlined,
  RobotOutlined,
} from '@ant-design/icons'
import { useAuthStore, useUIStore } from '../store'

const { Header, Sider, Content } = Layout
const { Text } = Typography

const menuItems = [
  { key: '/dashboard', icon: <DashboardOutlined />, label: '学习仪表盘' },
  { key: '/profile', icon: <UserOutlined />, label: '对话画像' },
  { key: '/path', icon: <DeploymentUnitOutlined />, label: '学习路径' },
  { key: '/resources', icon: <FileTextOutlined />, label: '资源中心' },
  { key: '/qa', icon: <QuestionCircleOutlined />, label: '智能辅导' },
  { key: '/evaluation', icon: <BarChartOutlined />, label: '学习评估' },
  { key: '/courses', icon: <BookOutlined />, label: '课程管理' },
  { key: '/search', icon: <SearchOutlined />, label: '知识检索' },
  { key: '/settings', icon: <SettingOutlined />, label: '系统设置' },
]

const AppLayout: React.FC = () => {
  const navigate = useNavigate()
  const location = useLocation()
  const { user, logout } = useAuthStore()
  const { sidebarCollapsed, toggleSidebar } = useUIStore()

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  const userMenuItems = [
    { key: 'profile', icon: <UserOutlined />, label: '个人画像', onClick: () => navigate('/profile') },
    { type: 'divider' as const },
    { key: 'logout', icon: <LogoutOutlined />, label: '退出登录', onClick: handleLogout },
  ]

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider
        trigger={null}
        collapsible
        collapsed={sidebarCollapsed}
        theme="light"
        style={{
          borderRight: '1px solid #f0f0f0',
          boxShadow: sidebarCollapsed ? undefined : '2px 0 8px rgba(0,0,0,0.05)',
        }}
      >
        <div
          style={{
            height: 64,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            borderBottom: '1px solid #f0f0f0',
            cursor: 'pointer',
          }}
          onClick={() => navigate('/dashboard')}
        >
          <RobotOutlined style={{ fontSize: 24, color: '#1677ff' }} />
          {!sidebarCollapsed && (
            <Text strong style={{ marginLeft: 8, fontSize: 16, whiteSpace: 'nowrap' }}>
              学习平台
            </Text>
          )}
        </div>
        <Menu
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
          style={{ borderRight: 'none' }}
        />
      </Sider>
      <Layout>
        <Header
          style={{
            background: '#fff',
            padding: '0 24px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            borderBottom: '1px solid #f0f0f0',
            height: 64,
          }}
        >
          <Button
            type="text"
            icon={sidebarCollapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
            onClick={toggleSidebar}
          />
          <Dropdown menu={{ items: userMenuItems }} placement="bottomRight">
            <div style={{ cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 8 }}>
              <Avatar icon={<UserOutlined />} style={{ backgroundColor: '#1677ff' }} />
              <Text>{user?.display_name || user?.username}</Text>
            </div>
          </Dropdown>
        </Header>
        <Content style={{ margin: 24, minHeight: 'calc(100vh - 112px)' }}>
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  )
}

export default AppLayout
