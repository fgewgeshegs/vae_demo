import React, { useEffect, useState } from 'react'
import { Card, Row, Col, Typography, Spin, Empty, Button, Modal, Form, Input, Tag, List, message } from 'antd'
import { PlusOutlined, BookOutlined, DeleteOutlined } from '@ant-design/icons'
import { courseApi, chapterApi, documentApi } from '../services/api'
import type { Course, Chapter, Document } from '../types'

const { Title, Text } = Typography

const CourseManagement: React.FC = () => {
  const [courses, setCourses] = useState<Course[]>([])
  const [loading, setLoading] = useState(true)
  const [modalOpen, setModalOpen] = useState(false)
  const [form] = Form.useForm()
  const [selectedCourse, setSelectedCourse] = useState<Course | null>(null)
  const [chapters, setChapters] = useState<Chapter[]>([])
  const [documents, setDocuments] = useState<Document[]>([])
  const [detailLoading, setDetailLoading] = useState(false)

  // 删除确认对话框状态
  const [deleteModalOpen, setDeleteModalOpen] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [courseToDelete, setCourseToDelete] = useState<Course | null>(null)

  const fetchCourses = async () => {
    try {
      const res = await courseApi.list()
      setCourses(res.data)
    } catch {
      // 处理错误
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchCourses()
  }, [])

  const handleCreateCourse = async (values: { title: string; description?: string }) => {
    try {
      await courseApi.create(values)
      message.success('课程创建成功')
      setModalOpen(false)
      form.resetFields()
      fetchCourses()
    } catch (e: any) {
      const detail = e?.response?.data?.detail || e?.message || '创建失败'
      message.error(detail)
    }
  }

  const handleSelectCourse = async (course: Course) => {
    setSelectedCourse(course)
    setDetailLoading(true)
    try {
      const [chRes, docRes] = await Promise.all([
        chapterApi.listByCourse(course.id),
        documentApi.listByCourse(course.id),
      ])
      setChapters(chRes.data)
      setDocuments(docRes.data)
    } catch {
      // 处理错误
    } finally {
      setDetailLoading(false)
    }
  }

  const showDeleteConfirm = (course: Course) => {
    setCourseToDelete(course)
    setDeleteModalOpen(true)
  }

  const handleDeleteConfirm = async () => {
    if (!courseToDelete) return
    setDeleting(true)
    try {
      await courseApi.delete(courseToDelete.id)
      message.success('删除成功')
      setDeleteModalOpen(false)
      setCourseToDelete(null)
      if (selectedCourse?.id === courseToDelete.id) setSelectedCourse(null)
      fetchCourses()
    } catch (e: any) {
      const detail = e?.response?.data?.detail || e?.message || '未知错误'
      message.error(`删除失败: ${detail}`)
    } finally {
      setDeleting(false)
    }
  }

  const handleDeleteCancel = () => {
    setDeleteModalOpen(false)
    setCourseToDelete(null)
  }

  if (loading) {
    return (
      <div style={{ textAlign: 'center', paddingTop: 100 }}>
        <Spin size="large" />
      </div>
    )
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}>
          <BookOutlined style={{ marginRight: 8 }} />
          课程管理
        </Title>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setModalOpen(true)}>
          创建课程
        </Button>
      </div>

      {courses.length === 0 ? (
        <Empty description="暂无课程" />
      ) : (
        <Row gutter={[16, 16]}>
          {courses.map((course) => (
            <Col xs={24} sm={12} lg={8} key={course.id}>
              <Card
                hoverable
                actions={[
                  <Button type="link" key="detail" onClick={() => handleSelectCourse(course)}>
                    查看详情
                  </Button>,
                  <Button type="link" key="delete" danger icon={<DeleteOutlined />}
                    onClick={() => showDeleteConfirm(course)}>
                    删除
                  </Button>,
                ]}
              >
                <Card.Meta
                  title={course.title}
                  description={
                    <>
                      <Text type="secondary">{course.description || '暂无描述'}</Text>
                      <br />
                      {course.seed_course && <Tag color="blue" style={{ marginTop: 8 }}>种子课程</Tag>}
                    </>
                  }
                />
              </Card>
            </Col>
          ))}
        </Row>
      )}

      {/* 删除确认弹窗 */}
      <Modal
        title="确认删除"
        open={deleteModalOpen}
        onOk={handleDeleteConfirm}
        onCancel={handleDeleteCancel}
        okText="确认删除"
        cancelText="取消"
        okButtonProps={{ danger: true, loading: deleting }}
        maskClosable={!deleting}
      >
        <p>确定要删除课程「{courseToDelete?.title}」吗？</p>
        <p style={{ color: '#ff4d4f', fontSize: 13 }}>此操作不可撤销，课程下的章节和知识点将一并删除。</p>
      </Modal>

      {/* 课程详情 Modal */}
      <Modal
        title={selectedCourse?.title}
        open={!!selectedCourse}
        onCancel={() => setSelectedCourse(null)}
        footer={null}
        width={600}
      >
        {detailLoading ? (
          <div style={{ textAlign: 'center', padding: 40 }}><Spin /></div>
        ) : (
          <>
            <Title level={5}>章节 ({chapters.length})</Title>
            <List
              dataSource={chapters}
              renderItem={(ch) => (
                <List.Item>
                  <Text>[{ch.sort_order}] {ch.title}</Text>
                </List.Item>
              )}
              locale={{ emptyText: '暂无章节' }}
              size="small"
            />

            <Title level={5} style={{ marginTop: 16 }}>文档 ({documents.length})</Title>
            <List
              dataSource={documents}
              renderItem={(doc) => (
                <List.Item>
                  <List.Item.Meta
                    title={doc.title}
                    description={
                      <>
                        <Tag>{doc.file_type}</Tag>
                        <Text type="secondary">{Math.round(doc.file_size / 1024)}KB</Text>
                        <Tag color={doc.status === 'ready' ? 'success' : 'processing'}>
                          {doc.status === 'ready' ? '就绪' : doc.status === 'pending' ? '等待中' : doc.status === 'error' ? '错误' : '处理中'}
                        </Tag>
                      </>
                    }
                  />
                </List.Item>
              )}
              locale={{ emptyText: '暂无文档' }}
              size="small"
            />
          </>
        )}
      </Modal>

      {/* 创建课程 Modal */}
      <Modal
        title="创建课程"
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={() => form.submit()}
      >
        <Form form={form} layout="vertical" onFinish={handleCreateCourse}>
          <Form.Item name="title" label="课程标题" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="description" label="课程描述">
            <Input.TextArea rows={3} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default CourseManagement
