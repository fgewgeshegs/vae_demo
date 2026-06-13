import React, { useState } from 'react'
import { Form, Input, Button, Tabs, message, Typography } from 'antd'
import { UserOutlined, LockOutlined, MailOutlined, RightCircleOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { authApi } from '../services/api'
import { useAuthStore } from '../store'
import NeuralNetwork from '../components/NeuralNetwork'

const { Title, Text } = Typography

const PARTICLE_COUNT = 50

const LoginPage: React.FC = () => {
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()
  const setAuth = useAuthStore((s) => s.setAuth)

  const handleLogin = async (values: { username: string; password: string }) => {
    setLoading(true)
    try {
      const res = await authApi.login(values.username, values.password)
      setAuth(res.data.access_token, res.data.user)
      message.success('\u767b\u5f55\u6210\u529f')
      navigate('/dashboard')
    } catch (err: unknown) {
      console.error('\u767b\u5f55\u5931\u8d25:', err)
      const detail = (err as any)?.response?.data?.detail
      message.error(detail || '\u767b\u5f55\u5931\u8d25\uff0c\u8bf7\u68c0\u67e5\u7528\u6237\u540d\u548c\u5bc6\u7801')
    } finally { setLoading(false) }
  }

  const handleRegister = async (values: { username: string; email: string; password: string; confirm: string }) => {
    if (values.password !== values.confirm) { message.error('\u4e24\u6b21\u5bc6\u7801\u4e0d\u4e00\u81f4'); return }
    setLoading(true)
    try {
      const res = await authApi.register({ username: values.username, email: values.email, password: values.password })
      setAuth(res.data.access_token, res.data.user)
      message.success('\u6ce8\u518c\u6210\u529f')
      navigate('/dashboard')
    } catch (err: unknown) {
      console.error('\u6ce8\u518c\u5931\u8d25:', err)
      const detail = (err as any)?.response?.data?.detail
      message.error(detail || '\u6ce8\u518c\u5931\u8d25\uff0c\u8bf7\u68c0\u67e5\u4fe1\u606f')
    } finally { setLoading(false) }
  }

  const particles = Array.from({ length: PARTICLE_COUNT }, (_, i) => ({
    id: i,
    left: '' + Math.random() * 100 + '%',
    size: '' + (2 + Math.random() * 4) + 'px',
    delay: '' + Math.random() * 12 + 's',
    duration: '' + (12 + Math.random() * 18) + 's',
    opacity: 0.2 + Math.random() * 0.4,
    drift: '' + (Math.random() - 0.5) * 120 + 'px',
  }))

  const getSubtitle = () => {
    const h = new Date().getHours()
    if (h < 6) return '\u591c\u6df1\u4e86\uff0c\u4f60\u7684\u5927\u8111\u6b63\u5728\u6574\u7406\u4eca\u5929\u7684\u6240\u5b66'
    if (h < 10) return '\u65b0\u7684\u4e00\u5929\uff0c\u8ba9\u77e5\u8bc6\u7684\u5149\u8292\u7167\u4eae\u524d\u8def'
    if (h < 14) return '\u5348\u540e\u65f6\u5149\uff0c\u6700\u9002\u5408\u6df1\u5ea6\u601d\u8003'
    if (h < 19) return '\u6bcf\u4e00\u5206\u949f\u7684\u4e13\u6ce8\uff0c\u90fd\u5728\u91cd\u5851\u4f60\u7684\u8ba4\u77e5'
    if (h < 22) return '\u591c\u665a\u7684\u5b81\u9759\uff0c\u662f\u6c89\u6d78\u5b66\u4e60\u7684\u6700\u4f73\u4f19\u4f34'
    return '\u661f\u8fb0\u4e3a\u4f34\uff0c\u5b66\u6d77\u65e0\u6daf'
  }

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      position: 'relative',
      overflow: 'hidden',
      background: '#0a0e1a',
    }}>
      <NeuralNetwork />
      <div style={{
        position: 'absolute', inset: 0,
        backgroundImage: [
          'linear-gradient(rgba(99, 102, 241, 0.05) 1px, transparent 1px)',
          'linear-gradient(90deg, rgba(99, 102, 241, 0.05) 1px, transparent 1px)',
        ].join(', '),
        backgroundSize: '60px 60px',
        mask: 'radial-gradient(ellipse at 50% 40%, black 30%, transparent 70%)',
        WebkitMask: 'radial-gradient(ellipse at 50% 40%, black 30%, transparent 70%)',
      }} />
      {particles.map((p) => (
        <div key={p.id} style={{
          position: 'absolute',
          left: p.left,
          bottom: '-10px',
          width: p.size, height: p.size,
          borderRadius: '50%',
          background: 'linear-gradient(135deg, #00d4ff, #6366f1)',
          boxShadow: '0 0 6px rgba(0, 212, 255, 0.4)',
          animation: 'particleDrift ' + p.duration + ' ease-in infinite',
          animationDelay: p.delay,
          opacity: p.opacity,
          '--drift-x': p.drift,
          '--p-opacity': p.opacity,
        } as React.CSSProperties} />
      ))}
      <div style={{
        position: 'absolute', top: '-20%', left: '50%',
        transform: 'translateX(-50%)',
        width: '700px', height: '700px', borderRadius: '50%',
        background: 'radial-gradient(circle, rgba(99,102,241,0.12) 0%, transparent 70%)',
        pointerEvents: 'none',
      }} />
      <div style={{
        position: 'absolute', bottom: '-15%', right: '-10%',
        width: '500px', height: '500px', borderRadius: '50%',
        background: 'radial-gradient(circle, rgba(0,212,255,0.08) 0%, transparent 70%)',
        pointerEvents: 'none',
      }} />
      <div style={{
        width: 420, position: 'relative', zIndex: 1,
        animation: 'fadeInUp 0.8s ease-out',
      }}>
        <div style={{
          position: 'absolute', top: -2, left: -2, right: -2, bottom: -2,
          borderRadius: 16,
          background: 'linear-gradient(135deg, rgba(0,212,255,0.3), rgba(99,102,241,0.3), rgba(124,58,237,0.3), rgba(0,212,255,0.3))',
          backgroundSize: '300% 300%',
          animation: 'gradientShift 6s ease infinite',
          zIndex: -1,
          mask: 'linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0)',
          maskComposite: 'exclude',
          WebkitMask: 'linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0)',
          WebkitMaskComposite: 'xor',
          padding: '2px',
        }} />
        <div style={{ position: 'absolute', top: -12, right: -8, width: 6, height: 6, borderRadius: '50%', background: '#06b6d4', opacity: 0.4, animation: 'twinkle 3s ease-in-out infinite' }} />
        <div style={{ position: 'absolute', bottom: -6, left: -10, width: 4, height: 4, borderRadius: '50%', background: '#818cf8', opacity: 0.3, animation: 'twinkle 4s ease-in-out infinite 1s' }} />
        <div style={{
          background: 'rgba(20, 27, 45, 0.85)',
          backdropFilter: 'blur(20px) saturate(1.2)',
          WebkitBackdropFilter: 'blur(20px) saturate(1.2)',
          border: '1px solid rgba(255, 255, 255, 0.08)',
          borderRadius: 14,
          padding: '40px 36px 28px',
          boxShadow: '0 8px 40px rgba(0, 0, 0, 0.5), 0 0 40px rgba(99, 102, 241, 0.08)',
        }}>
          <div style={{ textAlign: 'center', marginBottom: 32 }}>
            <div style={{
              display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
              width: 56, height: 56, borderRadius: 14,
              background: 'linear-gradient(135deg, #00d4ff, #6366f1)',
              marginBottom: 16,
              animation: 'breatheGlow 3s ease-in-out infinite',
              position: 'relative',
            }}>
              <div style={{
                position: 'absolute', inset: -4, borderRadius: 18,
                border: '1.5px solid rgba(99,102,241,0.15)',
                animation: 'spinSlow 6s linear infinite',
              }} />
              <svg width='28' height='28' viewBox='0 0 24 24' fill='none' stroke='white' strokeWidth='2' strokeLinecap='round' strokeLinejoin='round'>
                <path d='M12 2a7 7 0 0 1 7 7c0 2.4-1.2 4.5-3 5.7V18a1 1 0 0 1-1 1H9a1 1 0 0 1-1-1v-3.3C6.2 13.5 5 11.4 5 9a7 7 0 0 1 7-7z' />
                <path d='M9 21h6' />
                <path d='M12 2v1' />
                <path d='M4.93 4.93l.7.7' />
                <path d='M19.07 4.93l-.7.7' />
              </svg>
            </div>
            <Title level={3} style={{
              margin: 0,
              background: 'linear-gradient(135deg, #00d4ff, #818cf8)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              fontSize: 22, letterSpacing: 1,
            }}>
              Neural Learning
            </Title>
            <div style={{ marginTop: 8, position: 'relative', height: 20 }}>
              <Text style={{
                color: 'rgba(255,255,255,0.35)', fontSize: 12,
                display: 'block', letterSpacing: 1,
                animation: 'fadeIn 0.8s ease-out',
              }}>
                {getSubtitle()}
              </Text>
            </div>
          </div>
          <Tabs centered style={{ marginBottom: 0 }}
            items={[
              {
                key: 'login',
                label: <span style={{ letterSpacing: 1 }}>{'\u767b\u5f55'}</span>,
                children: (
                  <Form onFinish={handleLogin} layout='vertical' size='large'>
                    <Form.Item name='username' rules={[{ required: true, message: '\u8bf7\u8f93\u5165\u7528\u6237\u540d' }]}>
                      <Input prefix={<UserOutlined style={{ color: 'rgba(255,255,255,0.3)' }} />}
                        placeholder='\u7528\u6237\u540d'
                        style={{ background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.10)' }}
                      />
                    </Form.Item>
                    <Form.Item name='password' rules={[{ required: true, message: '\u8bf7\u8f93\u5165\u5bc6\u7801' }]}>
                      <Input.Password prefix={<LockOutlined style={{ color: 'rgba(255,255,255,0.3)' }} />}
                        placeholder='\u5bc6\u7801'
                        style={{ background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.10)' }}
                      />
                    </Form.Item>
                    <Button type='primary' htmlType='submit' loading={loading} block size='large'
                      style={{
                        height: 44, fontSize: 15, borderRadius: 8, letterSpacing: 2,
                        background: 'linear-gradient(135deg, #6366f1, #7c3aed)',
                        border: 'none',
                        boxShadow: '0 0 20px rgba(99, 102, 241, 0.3)',
                      }}
                      icon={!loading ? <RightCircleOutlined /> : undefined}
                    >
                      {'\u767b \u5f55'}
                    </Button>
                  </Form>
                ),
              },
              {
                key: 'register',
                label: <span style={{ letterSpacing: 1 }}>{'\u6ce8\u518c'}</span>,
                children: (
                  <Form onFinish={handleRegister} layout='vertical' size='large'>
                    <Form.Item name='username' rules={[{ required: true, message: '\u8bf7\u8f93\u5165\u7528\u6237\u540d' }]}>
                      <Input prefix={<UserOutlined style={{ color: 'rgba(255,255,255,0.3)' }} />}
                        placeholder='\u7528\u6237\u540d'
                        style={{ background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.10)' }}
                      />
                    </Form.Item>
                    <Form.Item name='email' rules={[{ required: true, type: 'email', message: '\u8bf7\u8f93\u5165\u6709\u6548\u90ae\u7bb1' }]}>
                      <Input prefix={<MailOutlined style={{ color: 'rgba(255,255,255,0.3)' }} />}
                        placeholder='\u90ae\u7bb1'
                        style={{ background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.10)' }}
                      />
                    </Form.Item>
                    <Form.Item name='password' rules={[{ required: true, min: 6, message: '\u5bc6\u7801\u81f3\u5c116\u4f4d' }]}>
                      <Input.Password prefix={<LockOutlined style={{ color: 'rgba(255,255,255,0.3)' }} />}
                        placeholder='\u5bc6\u7801'
                        style={{ background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.10)' }}
                      />
                    </Form.Item>
                    <Form.Item name='confirm' rules={[{ required: true, message: '\u8bf7\u786e\u8ba4\u5bc6\u7801' }]}>
                      <Input.Password prefix={<LockOutlined style={{ color: 'rgba(255,255,255,0.3)' }} />}
                        placeholder='\u786e\u8ba4\u5bc6\u7801'
                        style={{ background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.10)' }}
                      />
                    </Form.Item>
                    <Button type='primary' htmlType='submit' loading={loading} block size='large'
                      style={{
                        height: 44, fontSize: 15, borderRadius: 8, letterSpacing: 2,
                        background: 'linear-gradient(135deg, #6366f1, #7c3aed)',
                        border: 'none',
                        boxShadow: '0 0 20px rgba(99, 102, 241, 0.3)',
                      }}
                      icon={!loading ? <RightCircleOutlined /> : undefined}
                    >
                      {'\u6ce8 \u518c'}
                    </Button>
                  </Form>
                ),
              },
            ]}
          />
        </div>
      </div>
    </div>
  )
}

export default LoginPage