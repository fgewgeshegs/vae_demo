import React, { useState } from 'react'
import { Card, Form, Input, Button, Tabs, message, Typography, Space } from 'antd'
import { UserOutlined, LockOutlined, MailOutlined, RobotOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { authApi } from '../services/api'
import { useAuthStore } from '../store'

const { Title, Text } = Typography

const LoginPage: React.FC = () => {
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()
  const setAuth = useAuthStore((s) => s.setAuth)

  const handleLogin = async (values: { username: string; password: string }) => {
    setLoading(true)
    try {
      const res = await authApi.login(values.username, values.password)
      setAuth(res.data.access_token, res.data.user)
      message.success('登录成功')
      navigate('/dashboard')
    } catch (err: unknown) {
      console.error('登录失败:', err)
      const detail = (err as any)?.response?.data?.detail
      message.error(detail || '登录失败，请检查用户名和密码')
    } finally {
      setLoading(false)
    }
  }

  const handleRegister = async (values: {
    username: string
    email: string
    password: string
    confirm: string
  }) => {
    if (values.password !== values.confirm) {
      message.error('两次密码不一致')
      return
    }
    setLoading(true)
    try {
      const res = await authApi.register({
        username: values.username,
        email: values.email,
        password: values.password,
      })
      setAuth(res.data.access_token, res.data.user)
      message.success('注册成功')
      navigate('/dashboard')
    } catch (err: unknown) {
      console.error('注册失败:', err)
      const detail = (err as any)?.response?.data?.detail
      message.error(detail || '注册失败，请检查信息')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
      }}
    >
      <Card style={{ width: 420, borderRadius: 12, boxShadow: '0 8px 24px rgba(0,0,0,0.15)' }}>
        <Space direction="vertical" style={{ width: '100%', textAlign: 'center', marginBottom: 24 }}>
          <RobotOutlined style={{ fontSize: 48, color: '#1677ff' }} />
          <Title level={3} style={{ margin: 0 }}>AI 个性化学习平台</Title>
          <Text type="secondary">智能学习，因材施教</Text>
        </Space>

        <Tabs
          centered
          items={[
            {
              key: 'login',
              label: '登录',
              children: (
                <Form onFinish={handleLogin} layout="vertical" size="large">
                  <Form.Item name="username" rules={[{ required: true, message: '请输入用户名' }]}>
                    <Input prefix={<UserOutlined />} placeholder="用户名" />
                  </Form.Item>
                  <Form.Item name="password" rules={[{ required: true, message: '请输入密码' }]}>
                    <Input.Password prefix={<LockOutlined />} placeholder="密码" />
                  </Form.Item>
                  <Button type="primary" htmlType="submit" loading={loading} block>
                    登录
                  </Button>
                </Form>
              ),
            },
            {
              key: 'register',
              label: '注册',
              children: (
                <Form onFinish={handleRegister} layout="vertical" size="large">
                  <Form.Item name="username" rules={[{ required: true, message: '请输入用户名' }]}>
                    <Input prefix={<UserOutlined />} placeholder="用户名" />
                  </Form.Item>
                  <Form.Item name="email" rules={[{ required: true, type: 'email', message: '请输入有效邮箱' }]}>
                    <Input prefix={<MailOutlined />} placeholder="邮箱" />
                  </Form.Item>
                  <Form.Item name="password" rules={[{ required: true, min: 6, message: '密码至少6位' }]}>
                    <Input.Password prefix={<LockOutlined />} placeholder="密码" />
                  </Form.Item>
                  <Form.Item name="confirm" rules={[{ required: true, message: '请确认密码' }]}>
                    <Input.Password prefix={<LockOutlined />} placeholder="确认密码" />
                  </Form.Item>
                  <Button type="primary" htmlType="submit" loading={loading} block>
                    注册
                  </Button>
                </Form>
              ),
            },
          ]}
        />
      </Card>
    </div>
  )
}

export default LoginPage

