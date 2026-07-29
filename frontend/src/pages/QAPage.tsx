import React, { useEffect, useState, useRef } from 'react'
import { Card, Input, Button, List, Typography, Spin, Space, Avatar, message, Tag } from 'antd'
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
    <div className="workspace-page workspace-page--qa" style={{ display: 'flex', flexDirection: 'column', height: 'calc(100vh - 160px)' }}>
      <Title level={4}>
        <RobotOutlined style={{ marginRight: 8 }} />
        智能辅导
      </Title>

      <div className="conversation-panel"
        ref={listRef}
        style={{
          flex: 1,
          overflow: 'auto',
          padding: 16,
          background: 'rgba(255, 255, 255, 0.64)',
          border: '1px solid rgba(72, 102, 153, 0.14)',
          borderRadius: 8,
          marginBottom: 16,
          boxShadow: '0 18px 50px rgba(42,68,112,0.08)',
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
                    background: '#2858d7',
                    color: '#fff',
                    padding: '8px 16px',
                    borderRadius: 12,
                    borderBottomRightRadius: 4,
                    maxWidth: '70%',
                  }}
                >
                  <Text style={{ color: '#fff' }}>{record.question}</Text>
                </div>
                <Avatar icon={<UserOutlined />} style={{ background: '#2858d7' }} />
              </Space>

              {/* AI 回答 */}
              {record.answer && (
                <Space align="start" style={{ width: '100%' }}>
                  <Avatar icon={<RobotOutlined />} style={{ background: '#53627a' }} />
                  <div
                  style={{
                      background: 'rgba(255, 255, 255, 0.86)',
                      color: 'var(--text-primary)',
                      padding: '10px 16px',
                      borderRadius: 12,
                      borderBottomLeftRadius: 4,
                      maxWidth: '70%',
                      whiteSpace: 'pre-wrap',
                      lineHeight: 1.75,
                      border: '1px solid rgba(72, 102, 153, 0.14)',
                      boxShadow: '0 10px 28px rgba(42, 68, 112, 0.10)',
                    }}
                  >
                    <Text style={{ color: 'var(--text-primary)', whiteSpace: 'pre-wrap' }}>
                      {record.answer}
                    </Text>
                  </div>
                </Space>
              )}
              {Array.isArray(record.metadata?.sources) && record.metadata.sources.length > 0 && (
                <div style={{ marginLeft: 48, marginTop: 8 }}>
                  <Text type="secondary" style={{ marginRight: 8 }}>参考资料：</Text>
                  {(record.metadata.sources as Array<{ source?: string; locator?: string }>).slice(0, 3).map((source, index) => (
                    <Tag key={`${source.source}-${source.locator}-${index}`} color="blue">
                      {source.locator || source.source || `资料 ${index + 1}`}
                    </Tag>
                  ))}
                </div>
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
          {sending ? 'Agent 正在检索并回答...' : '发送'}
        </Button>
      </Space.Compact>
    </div>
  )
}

export default QAPage
