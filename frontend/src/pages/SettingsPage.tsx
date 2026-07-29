import React, { useEffect, useState } from "react"
import {
  Button, Empty, Input, message, Modal, Select, Spin, Table, Tag, Typography,
} from "antd"
import type { ColumnsType } from "antd/es/table"
import {
  EditOutlined, KeyOutlined, SafetyOutlined, SettingOutlined,
} from "@ant-design/icons"
import { configApi } from "../services/api"
import type { SystemConfig } from "../types"

const { Title, Text } = Typography

const PROVIDER_OPTIONS = [
  { value: "mock", label: "Mock（离线开发）" },
  { value: "deepseek", label: "DeepSeek" },
  { value: "glm", label: "GLM（智谱）" },
  { value: "qwen", label: "Qwen（通义千问）" },
  { value: "openai", label: "OpenAI" },
]

const isProviderKey = (key: string) => /provider/i.test(key)

interface ApiError {
  response?: { status?: number; data?: { detail?: string } }
}

const SettingsPage: React.FC = () => {
  const [configs, setConfigs] = useState<SystemConfig[]>([])
  const [loading, setLoading] = useState(true)
  const [forbidden, setForbidden] = useState(false)
  const [editing, setEditing] = useState<SystemConfig | null>(null)
  const [editValue, setEditValue] = useState("")
  const [saving, setSaving] = useState(false)

  const load = async () => {
    setLoading(true)
    setForbidden(false)
    try {
      const res = await configApi.list()
      setConfigs(res.data)
    } catch (err: unknown) {
      if ((err as ApiError).response?.status === 403) {
        setForbidden(true)
      } else {
        message.error("配置加载失败")
      }
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const openEdit = (cfg: SystemConfig) => {
    setEditing(cfg)
    setEditValue(cfg.is_secret ? "" : cfg.config_value)
  }

  const save = async () => {
    if (!editing) return
    if (editing.is_secret && !editValue.trim()) {
      message.warning("请输入新的密钥值，或取消编辑")
      return
    }
    setSaving(true)
    try {
      await configApi.update(editing.config_key, { config_value: editValue.trim() })
      message.success("配置已更新（热生效）")
      setEditing(null)
      await load()
    } catch (err: unknown) {
      const detail = (err as ApiError).response?.data?.detail
      message.error(detail || "更新失败")
    } finally {
      setSaving(false)
    }
  }

  const columns: ColumnsType<SystemConfig> = [
    {
      title: "配置项",
      dataIndex: "config_key",
      key: "config_key",
      render: (key: string, record) => (
        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
          {record.is_secret ? <KeyOutlined style={{ color: "#f59e0b" }} /> : <SettingOutlined style={{ color: "#94a3b8" }} />}
          <Text strong style={{ fontSize: 13 }}>{key}</Text>
        </div>
      ),
    },
    {
      title: "当前值",
      dataIndex: "config_value",
      key: "config_value",
      render: (val: string, record) =>
        record.is_secret ? (
          <Tag color="orange" style={{ fontFamily: "var(--font-mono)", fontSize: 12 }}>********</Tag>
        ) : (
          <Text style={{ fontFamily: "var(--font-mono)", fontSize: 12, color: "#475569" }}>{val || "—"}</Text>
        ),
    },
    {
      title: "类型",
      dataIndex: "config_type",
      key: "config_type",
      render: (t: string) => <Tag style={{ fontSize: 11 }}>{t}</Tag>,
    },
    {
      title: "说明",
      dataIndex: "description",
      key: "description",
      render: (d: string) => <Text style={{ fontSize: 12, color: "#64748b" }}>{d || "—"}</Text>,
    },
    {
      title: "操作",
      key: "action",
      render: (_: unknown, record) => (
        <Button size="small" icon={<EditOutlined />} onClick={() => openEdit(record)}>编辑</Button>
      ),
    },
  ]

  if (loading) {
    return <div style={{ textAlign: "center", padding: 80 }}><Spin size="large" /></div>
  }

  if (forbidden) {
    return (
      <div>
        <Title level={4}>系统设置</Title>
        <Empty description={<span style={{ color: "#94a3b8" }}>需要管理员权限才能查看系统配置</span>}>
          <Button onClick={load}>重新加载</Button>
        </Empty>
      </div>
    )
  }

  return (
    <div className="workspace-page workspace-page--settings">
      <Title level={4}>系统设置</Title>

      <div className="card" style={{ padding: "16px 20px", marginBottom: 16, display: "flex", alignItems: "center", gap: 10 }}>
        <SafetyOutlined style={{ color: "#10b981" }} />
        <Text style={{ fontSize: 12, color: "#64748b" }}>
          密钥类配置以 ******** 掩码显示，编辑时需输入新值才会保存；后端拒绝保存掩码占位符。
        </Text>
      </div>

      <div className="card" style={{ padding: 0, overflow: "hidden" }}>
        <Table
          dataSource={configs}
          columns={columns}
          rowKey="id"
          pagination={false}
          locale={{ emptyText: <Empty description="暂无配置项" /> }}
        />
      </div>

      <Modal
        title={editing ? `编辑：${editing.config_key}` : ""}
        open={!!editing}
        onCancel={() => setEditing(null)}
        onOk={save}
        confirmLoading={saving}
        okText="保存"
        cancelText="取消"
      >
        {editing && (
          <div style={{ paddingTop: 8 }}>
            {editing.description && (
              <Text style={{ display: "block", fontSize: 12, color: "#94a3b8", marginBottom: 12 }}>
                {editing.description}
              </Text>
            )}
            {editing.is_secret ? (
              <>
                <Input.Password
                  value={editValue}
                  onChange={(e) => setEditValue(e.target.value)}
                  placeholder="输入新的密钥值（不会显示原值）"
                  prefix={<KeyOutlined style={{ color: "#f59e0b" }} />}
                />
                <Text style={{ display: "block", fontSize: 11, color: "#94a3b8", marginTop: 8 }}>
                  出于安全考虑，原密钥不会回显。输入新值后保存即可热生效。
                </Text>
              </>
            ) : isProviderKey(editing.config_key) ? (
              <Select
                value={editValue}
                onChange={setEditValue}
                options={PROVIDER_OPTIONS}
                style={{ width: "100%" }}
                placeholder="选择 LLM 供应商"
              />
            ) : (
              <Input.TextArea
                value={editValue}
                onChange={(e) => setEditValue(e.target.value)}
                rows={3}
                placeholder="输入配置值"
              />
            )}
          </div>
        )}
      </Modal>
    </div>
  )
}

export default SettingsPage
