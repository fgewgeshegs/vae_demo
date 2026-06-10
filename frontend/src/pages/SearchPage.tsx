import React, { useState } from 'react'
import { Card, Input, List, Typography, Tag, Empty, Spin } from 'antd'
import { SearchOutlined, FileTextOutlined } from '@ant-design/icons'
import { searchApi } from '../services/api'

const { Title, Text, Paragraph } = Typography

interface SearchResult {
  chunk_id: number
  document_id: number
  content: string
  score: number
  method: string
}

const SearchPage: React.FC = () => {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<SearchResult[]>([])
  const [loading, setLoading] = useState(false)
  const [searched, setSearched] = useState(false)

  const handleSearch = async (value: string) => {
    if (!value.trim()) return
    setLoading(true)
    setSearched(true)
    try {
      const res = await searchApi.search(value)
      setResults(res.data.results || [])
    } catch {
      setResults([])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <Title level={4}>
        <SearchOutlined style={{ marginRight: 8 }} />
        知识检索
      </Title>

      <Input.Search
        placeholder="搜索课程内容..."
        allowClear
        enterButton="搜索"
        size="large"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        onSearch={handleSearch}
        style={{ marginBottom: 24 }}
      />

      {loading ? (
        <div style={{ textAlign: 'center', padding: 40 }}>
          <Spin size="large" />
        </div>
      ) : searched && results.length === 0 ? (
        <Empty description="未找到相关内容" />
      ) : (
        <List
          dataSource={results}
          renderItem={(item) => (
            <Card
              size="small"
              style={{ marginBottom: 8 }}
              hoverable
            >
              <Paragraph ellipsis={{ rows: 3 }} style={{ marginBottom: 8 }}>
                {item.content}
              </Paragraph>
              <div>
                <Tag icon={<FileTextOutlined />}>文档 #{item.document_id}</Tag>
                <Tag color={item.method === 'keyword' ? 'blue' : 'green'}>
                  {item.method === 'keyword' ? '关键词匹配' : '向量检索'}
                </Tag>
                <Text type="secondary" style={{ fontSize: 12 }}>
                  相关度: {(item.score * 100).toFixed(0)}%
                </Text>
              </div>
            </Card>
          )}
        />
      )}
    </div>
  )
}

export default SearchPage
