import React, { useEffect, useState } from 'react'
import { Card, Form, Input, Select, Button, Typography, Spin, message, Space, Divider } from 'antd'
import { SettingOutlined, ApiOutlined, SaveOutlined } from '@ant-design/icons'
import { configApi } from '../services/api'
import type { SystemConfig } from '../types'

const { Title, Text } = Typography

const SettingsPage: React.FC = () => {
  const [configs, setConfigs] = useState<SystemConfig[]>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState<string | null>(null)

  // 本地编辑状态
  const [editedValues, setEditedValues] = useState<Record<string, string>>({})

  useEffect(() => {
    const fetchConfigs = async () => {
      try {
        const res = await configApi.list()
        setConfigs(res.data)
        // 初始化本地编辑值
        const values: Record<string, string> = {}
        res.data.forEach((c) => {
          values[c.config_key] = c.config_value
        })
        setEditedValues(values)
      } catch {
        message.error('获取配置失败')
      } finally {
        setLoading(false)
      }
    }
    fetchConfigs()
  }, [])

  const updateValue = (key: string, value: string) => {
    setEditedValues((prev) => ({ ...prev, [key]: value }))
  }

  const handleSave = async (configKey: string) => {
    setSaving(configKey)
    try {
      const value = editedValues[configKey] || ''
      await configApi.update(configKey, { config_key: configKey, config_value: value })
      message.success(`${configKey} 已更新`)
    } catch {
      message.error('更新失败')
    } finally {
      setSaving(null)
    }
  }

  const getConfig = (key: string) => configs.find((c) => c.config_key === key)

  if (loading) {
    return (
      <div style={{ textAlign: 'center', paddingTop: 100 }}>
        <Spin size="large" />
      </div>
    )
  }

  return (
    <div>
      <Title level={4}>
        <SettingOutlined style={{ marginRight: 8 }} />
        系统设置
      </Title>
      <Text type="secondary">配置热生效，无需重启服务</Text>

      <Card title={<><ApiOutlined /> LLM 供应商配置</>} style={{ marginTop: 16 }}>
        <Form layout="vertical">
          <Form.Item label="当前供应商">
            <Select
              value={editedValues['llm_provider'] || 'mock'}
              onChange={(val) => updateValue('llm_provider', val)}
              options={[
                { label: 'Mock 模式（开发测试）', value: 'mock' },
                { label: 'DeepSeek', value: 'deepseek' },
                { label: 'OpenAI', value: 'openai' },
                { label: 'GLM (智谱)', value: 'glm' },
                { label: 'Qwen (通义千问)', value: 'qwen' },
              ]}
            />
            <Button
              type="primary"
              size="small"
              icon={<SaveOutlined />}
              loading={saving === 'llm_provider'}
              onClick={() => handleSave('llm_provider')}
              style={{ marginTop: 8 }}
            >
              保存
            </Button>
          </Form.Item>

          <Divider />

          {[
            { key: 'deepseek_api_key', label: 'DeepSeek API Key', placeholder: 'sk-xxx' },
            { key: 'openai_api_key', label: 'OpenAI API Key', placeholder: 'sk-xxx' },
            { key: 'glm_api_key', label: 'GLM API Key', placeholder: 'xxx' },
            { key: 'qwen_api_key', label: 'Qwen API Key', placeholder: 'sk-xxx' },
          ].map(({ key, label, placeholder }) => (
            <Form.Item key={key} label={label}>
              <Space.Compact style={{ width: '100%' }}>
                <Input.Password
                  placeholder={placeholder}
                  value={editedValues[key] || ''}
                  onChange={(e) => updateValue(key, e.target.value)}
                  style={{ flex: 1 }}
                />
                <Button
                  type="primary"
                  icon={<SaveOutlined />}
                  loading={saving === key}
                  onClick={() => handleSave(key)}
                >
                  保存
                </Button>
              </Space.Compact>
            </Form.Item>
          ))}
        </Form>
      </Card>

      <Card title="其他设置" style={{ marginTop: 16 }}>
        <Form layout="vertical">
          {[
            { key: 'llm_mock_delay', label: 'Mock 模式延迟（秒）', type: 'number', step: 0.1, defaultVal: '0.5' },
            { key: 'jwt_expire_minutes', label: 'JWT 过期时间（分钟）', type: 'number', step: 1, defaultVal: '1440' },
          ].map(({ key, label, type, step, defaultVal }) => (
            <Form.Item key={key} label={label}>
              <Space.Compact style={{ width: '100%' }}>
                <Input
                  type={type}
                  step={step}
                  value={editedValues[key] ?? defaultVal}
                  onChange={(e) => updateValue(key, e.target.value)}
                  style={{ flex: 1 }}
                />
                <Button
                  type="primary"
                  icon={<SaveOutlined />}
                  loading={saving === key}
                  onClick={() => handleSave(key)}
                >
                  保存
                </Button>
              </Space.Compact>
            </Form.Item>
          ))}
        </Form>
      </Card>
    </div>
  )
}

export default SettingsPage
