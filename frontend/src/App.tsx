import { useEffect, useState } from 'react'
import { Alert, Card, Col, Layout, List, Row, Space, Tag, Typography } from 'antd'

import './App.css'

type HealthResponse = {
  status: string
  appName: string
  appVersion: string
  sqlitePath: string
  databaseReady: boolean
  pythonVersion: string
}

const { Content, Header } = Layout
const { Paragraph, Text, Title } = Typography

const phases = [
  'Phase 1: 搭建 FastAPI、SQLite、React/Vite 基础骨架',
  'Phase 2: 实现 PostgreSQL 连接、元数据抓取和手写 SQL',
  'Phase 3: 接入自然语言生成 SQL 和一键执行',
  'Phase 4: 打磨界面、文档和启动体验',
]

function App() {
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const controller = new AbortController()

    async function loadHealth() {
      try {
        const response = await fetch('http://127.0.0.1:8000/api/v1/health', {
          signal: controller.signal,
        })

        if (!response.ok) {
          throw new Error(`Health check failed: ${response.status}`)
        }

        const payload = (await response.json()) as HealthResponse
        setHealth(payload)
      } catch (loadError) {
        if (controller.signal.aborted) {
          return
        }

        setError(loadError instanceof Error ? loadError.message : 'Unknown error')
      }
    }

    void loadHealth()

    return () => {
      controller.abort()
    }
  }, [])

  return (
    <Layout className="app-shell">
      <Header className="app-header">
        <Title level={3} className="app-title">
          DB Query Generator
        </Title>
        <Text className="app-subtitle">按课程计划推进的数据库查询生成器 MVP</Text>
      </Header>

      <Content className="app-content">
        <Space direction="vertical" size={24} className="content-stack">
          {error ? (
            <Alert
              message="后端暂未连通"
              description={error}
              showIcon
              type="warning"
            />
          ) : null}

          <Row gutter={[16, 16]}>
            <Col xs={24} lg={14}>
              <Card title="项目目标" className="panel-card">
                <Paragraph>
                  这个工具会支持连接 PostgreSQL、抓取元数据、执行手写 SQL，
                  并在后续阶段加入自然语言生成 SQL。
                </Paragraph>
                <List
                  dataSource={phases}
                  renderItem={(item) => (
                    <List.Item>
                      <Text>{item}</Text>
                    </List.Item>
                  )}
                />
              </Card>
            </Col>

            <Col xs={24} lg={10}>
              <Card title="系统状态" className="panel-card">
                {health ? (
                  <Space direction="vertical" size={12}>
                    <div>
                      <Tag color="green">{health.status}</Tag>
                      <Tag color={health.databaseReady ? 'blue' : 'red'}>
                        SQLite {health.databaseReady ? 'ready' : 'not ready'}
                      </Tag>
                    </div>
                    <Paragraph>
                      <Text strong>App Version:</Text> {health.appVersion}
                    </Paragraph>
                    <Paragraph>
                      <Text strong>Python:</Text> {health.pythonVersion}
                    </Paragraph>
                    <Paragraph>
                      <Text strong>SQLite Path:</Text> {health.sqlitePath}
                    </Paragraph>
                  </Space>
                ) : (
                  <Paragraph>正在等待后端健康检查结果...</Paragraph>
                )}
              </Card>
            </Col>
          </Row>
        </Space>
      </Content>
    </Layout>
  )
}

export default App
