import React, { useEffect, useState, useRef } from 'react'
import { Card, Input, Button, List, Typography, Spin, Space, Avatar, message } from 'antd'
import { SendOutlined, RobotOutlined, UserOutlined } from '@ant-design/icons'
import { qaApi } from '../services/api'
import type { QARecord } from '../types'

const { Text, Title } = Typography
const { TextArea } = Input

const QAPage: React.FC = () => {
  const [records, setRecords] = useState<QARecord[]>([])
  const [loading, setLoading] = useState(true)
  const [sending, setSending] = useState(false)
  const [question, setQuestion] = useState('')
  const listRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const fetchQA = async () => {
      try {
        const res = await qaApi.list()
        // API 返回最新的在前，反转后按时间正序显示（旧→新）
        setRecords(res.data.reverse())
      } catch (e) {
        console.error('问答历史加载失败:', e)
      } finally {
        setLoading(false)
      }
    }
    fetchQA()
  }, [])

  useEffect(() => {
    if (listRef.current) {
      listRef.current.scrollTop = listRef.current.scrollHeight
    }
  }, [records])

  const handleSend = async () => {
    if (!question.trim()) return
    setSending(true)
    try {
      const res = await qaApi.ask(question.trim())
      // 追加到末尾（最新消息在底部）
      setRecords((prev) => [...prev, res.data])
      setQuestion('')
    } catch {
      message.error('发送失败')
    } finally {
      setSending(false)
    }
  }

  if (loading) {
    return (
      <div style={{ textAlign: 'center', paddingTop: 100 }}>
        <Spin size="large" />
      </div>
    )
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: 'calc(100vh - 160px)' }}>
      <Title level={4}>
        <RobotOutlined style={{ marginRight: 8 }} />
        智能辅导
      </Title>

      <div
        ref={listRef}
        style={{
          flex: 1,
          overflow: 'auto',
          padding: 16,
          background: '#fafafa',
          borderRadius: 8,
          marginBottom: 16,
        }}
      >
        <List
          dataSource={records}
          renderItem={(record) => (
            <List.Item style={{ display: 'block', padding: '12px 0' }}>
              {/* 用户问题 */}
              <Space align="start" style={{ marginBottom: 8, width: '100%', justifyContent: 'flex-end' }}>
                <div
                  style={{
                    background: '#1677ff',
                    color: '#fff',
                    padding: '8px 16px',
                    borderRadius: 12,
                    borderBottomRightRadius: 4,
                    maxWidth: '70%',
                  }}
                >
                  <Text style={{ color: '#fff' }}>{record.question}</Text>
                </div>
                <Avatar icon={<UserOutlined />} style={{ backgroundColor: '#1677ff' }} />
              </Space>

              {/* AI 回答 */}
              {record.answer && (
                <Space align="start" style={{ width: '100%' }}>
                  <Avatar icon={<RobotOutlined />} style={{ backgroundColor: '#52c41a' }} />
                  <div
                    style={{
                      background: '#fff',
                      padding: '8px 16px',
                      borderRadius: 12,
                      borderBottomLeftRadius: 4,
                      maxWidth: '70%',
                      whiteSpace: 'pre-wrap',
                      border: '1px solid #f0f0f0',
                    }}
                  >
                    <Text>{record.answer}</Text>
                  </div>
                </Space>
              )}
            </List.Item>
          )}
          locale={{ emptyText: '开始你的第一次提问吧！' }}
        />
      </div>

      <Space.Compact style={{ width: '100%' }}>
        <TextArea
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="输入你的学习问题..."
          autoSize={{ minRows: 1, maxRows: 4 }}
          onPressEnter={(e) => {
            if (!e.shiftKey) {
              e.preventDefault()
              handleSend()
            }
          }}
        />
        <Button
          type="primary"
          icon={<SendOutlined />}
          onClick={handleSend}
          loading={sending}
          style={{ height: 'auto' }}
        >
          发送
        </Button>
      </Space.Compact>
    </div>
  )
}

export default QAPage
