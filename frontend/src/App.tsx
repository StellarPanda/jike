import { useEffect, useMemo, useState } from 'react'
import {
  Alert,
  App as AntApp,
  Button,
  Card,
  Col,
  Empty,
  Form,
  Input,
  Layout,
  List,
  Popconfirm,
  Row,
  Space,
  Spin,
  Table,
  Tabs,
  Tag,
  Tree,
  Typography,
} from 'antd'

import './App.css'

type HealthResponse = {
  status: string
  appName: string
  appVersion: string
  sqlitePath: string
  databaseReady: boolean
  pythonVersion: string
}

type DatabaseConnectionListItem = {
  id: string
  name: string
  databaseType: string
  createdAt: string
  updatedAt: string
}

type DatabaseConnectionDetail = DatabaseConnectionListItem & {
  connectionUrl: string
}

type TableMetadataItem = {
  id: string
  databaseId: string
  schemaName: string
  tableName: string
  tableType: string
}

type ColumnMetadataItem = {
  id: string
  tableId: string
  columnName: string
  dataType: string
  isNullable: number
  isPrimaryKey: number
  ordinalPosition: number
}

type MetadataResponse = {
  tables: TableMetadataItem[]
  columns: ColumnMetadataItem[]
}

type QueryValidationResponse = {
  databaseId: string
  statementType: string
  normalizedQuery: string
  appliedLimit: boolean
  limitValue: number
  isValid: boolean
}

type GenerateQueryResponse = QueryValidationResponse & {
  naturalLanguage: string
  generatedQuery: string
  model: string
}

type QueryExecutionResponse = {
  databaseId: string
  executedQuery: string
  rowCount: number
  columns: Array<{ key: string; title: string }>
  rows: Array<Record<string, unknown>>
}

type QueryHistoryItem = {
  id: string
  queryText: string
  querySource: string
  executionStatus: string
  errorMessage?: string | null
  createdAt: string
}

type CreateDatabasePayload = {
  name: string
  connectionUrl: string
}

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000/api/v1'
const { Content, Header } = Layout
const { Paragraph, Text, Title } = Typography
const { TextArea } = Input

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers ?? {}),
    },
    ...init,
  })

  if (!response.ok) {
    const fallback = `Request failed: ${response.status}`
    try {
      const payload = (await response.json()) as { detail?: string }
      throw new Error(payload.detail || fallback)
    } catch (error) {
      if (error instanceof Error && error.message !== fallback) {
        throw error
      }
      throw new Error(fallback)
    }
  }

  if (response.status === 204) {
    return undefined as T
  }

  return (await response.json()) as T
}

async function downloadExportFile(path: string, init: RequestInit, fallbackFilename: string) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(init.headers ?? {}),
    },
    ...init,
  })

  if (!response.ok) {
    const fallback = `Request failed: ${response.status}`
    try {
      const payload = (await response.json()) as { detail?: string }
      throw new Error(payload.detail || fallback)
    } catch (error) {
      if (error instanceof Error && error.message !== fallback) {
        throw error
      }
      throw new Error(fallback)
    }
  }

  const blob = await response.blob()
  const filename = response.headers
    .get('Content-Disposition')
    ?.match(/filename="([^"]+)"/)?.[1] ?? fallbackFilename
  const objectUrl = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = objectUrl
  anchor.download = filename
  anchor.click()
  URL.revokeObjectURL(objectUrl)
}

function buildTreeData(metadata: MetadataResponse | null) {
  if (!metadata) {
    return []
  }

  const columnsByTable = new Map<string, ColumnMetadataItem[]>()
  for (const column of metadata.columns) {
    const current = columnsByTable.get(column.tableId) ?? []
    current.push(column)
    columnsByTable.set(column.tableId, current)
  }

  const schemaMap = new Map<string, typeof metadata.tables>()
  for (const table of metadata.tables) {
    const current = schemaMap.get(table.schemaName) ?? []
    current.push(table)
    schemaMap.set(table.schemaName, current)
  }

  return Array.from(schemaMap.entries()).map(([schemaName, tables]) => ({
    key: schemaName,
    title: schemaName,
    children: tables.map((table) => ({
      key: table.id,
      title: `${table.tableName} (${table.tableType})`,
      children: (columnsByTable.get(table.id) ?? []).map((column) => ({
        key: column.id,
        title: `${column.columnName}: ${column.dataType}${column.isPrimaryKey ? ' [PK]' : ''}`,
        isLeaf: true,
      })),
    })),
  }))
}

function maskConnectionUrl(connectionUrl: string) {
  try {
    const parsedUrl = new URL(connectionUrl)
    if (parsedUrl.password) {
      parsedUrl.password = '****'
    }
    return parsedUrl.toString()
  } catch {
    return connectionUrl.replace(/:\/\/([^:]+):([^@]+)@/, '://$1:****@')
  }
}

function App() {
  const { message } = AntApp.useApp()
  const [form] = Form.useForm<CreateDatabasePayload>()
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [databases, setDatabases] = useState<DatabaseConnectionListItem[]>([])
  const [selectedDatabaseId, setSelectedDatabaseId] = useState<string | null>(null)
  const [selectedDatabase, setSelectedDatabase] = useState<DatabaseConnectionDetail | null>(null)
  const [metadata, setMetadata] = useState<MetadataResponse | null>(null)
  const [history, setHistory] = useState<QueryHistoryItem[]>([])
  const [queryText, setQueryText] = useState('select * from users')
  const [naturalLanguage, setNaturalLanguage] = useState('查询所有用户的姓名和邮箱，按注册时间倒序排列')
  const [generatedQuery, setGeneratedQuery] = useState<GenerateQueryResponse | null>(null)
  const [validatedQuery, setValidatedQuery] = useState<QueryValidationResponse | null>(null)
  const [queryResult, setQueryResult] = useState<QueryExecutionResponse | null>(null)
  const [lastQuerySource, setLastQuerySource] = useState('manual')
  const [loading, setLoading] = useState(false)
  const [queryLoading, setQueryLoading] = useState(false)
  const [exportLoading, setExportLoading] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const treeData = useMemo(() => buildTreeData(metadata), [metadata])

  async function loadDatabases() {
    const payload = await apiFetch<DatabaseConnectionListItem[]>('/databases')
    setDatabases(payload)

    if (payload.length > 0 && !selectedDatabaseId) {
      setSelectedDatabaseId(payload[0].id)
    }

    if (payload.length === 0) {
      setSelectedDatabaseId(null)
      setSelectedDatabase(null)
      setMetadata(null)
      setHistory([])
      setQueryResult(null)
      setValidatedQuery(null)
    }
  }

  async function loadDatabaseWorkspace(databaseId: string) {
    setLoading(true)
    setError(null)

    try {
      const [detail, metadataPayload, historyPayload] = await Promise.all([
        apiFetch<DatabaseConnectionDetail>(`/databases/${databaseId}`),
        apiFetch<MetadataResponse>(`/databases/${databaseId}/metadata`),
        apiFetch<QueryHistoryItem[]>(`/databases/${databaseId}/query-history`),
      ])

      setSelectedDatabase(detail)
      setMetadata(metadataPayload)
      setHistory(historyPayload)
    } catch (loadError) {
      const messageText = loadError instanceof Error ? loadError.message : 'Unknown error'
      setError(messageText)
      setSelectedDatabase(null)
      setMetadata(null)
      setHistory([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    async function loadInitialData() {
      try {
        const healthPayload = await apiFetch<HealthResponse>('/health')
        setHealth(healthPayload)
      } catch (loadError) {
        setError(loadError instanceof Error ? loadError.message : 'Failed to load health status')
      }

      try {
        const databasesPayload = await apiFetch<DatabaseConnectionListItem[]>('/databases')
        setDatabases(databasesPayload)
        if (databasesPayload.length > 0) {
          setSelectedDatabaseId(databasesPayload[0].id)
        }
      } catch (loadError) {
        setError(loadError instanceof Error ? loadError.message : 'Failed to load databases')
      }
    }

    void loadInitialData()
  }, [])

  useEffect(() => {
    if (!selectedDatabaseId) {
      return
    }

    void loadDatabaseWorkspace(selectedDatabaseId)
  }, [selectedDatabaseId])

  async function handleCreateDatabase(values: CreateDatabasePayload) {
    setLoading(true)
    setError(null)

    try {
      const created = await apiFetch<DatabaseConnectionDetail>('/databases', {
        method: 'POST',
        body: JSON.stringify(values),
      })

      await loadDatabases()
      setSelectedDatabaseId(created.id)
      form.resetFields()
      message.success('数据库连接已创建并同步元数据')
    } catch (createError) {
      const messageText = createError instanceof Error ? createError.message : 'Unknown error'
      setError(messageText)
      message.error(messageText)
    } finally {
      setLoading(false)
    }
  }

  async function handleRefreshMetadata() {
    if (!selectedDatabaseId) {
      return
    }

    setLoading(true)
    try {
      await apiFetch(`/databases/${selectedDatabaseId}/refresh-metadata`, {
        method: 'POST',
      })
      await loadDatabaseWorkspace(selectedDatabaseId)
      message.success('元数据已刷新')
    } catch (refreshError) {
      const messageText = refreshError instanceof Error ? refreshError.message : 'Unknown error'
      setError(messageText)
      message.error(messageText)
    } finally {
      setLoading(false)
    }
  }

  async function handleDeleteDatabase(databaseId: string) {
    setLoading(true)
    setError(null)
    try {
      await apiFetch(`/databases/${databaseId}`, { method: 'DELETE' })
      const remaining = databases.filter((database) => database.id !== databaseId)
      setDatabases(remaining)
      setSelectedDatabaseId(remaining[0]?.id ?? null)
      setSelectedDatabase(null)
      setMetadata(null)
      setHistory([])
      setQueryResult(null)
      setValidatedQuery(null)
      setGeneratedQuery(null)
      message.success('数据库连接已删除')
    } catch (deleteError) {
      const messageText = deleteError instanceof Error ? deleteError.message : 'Unknown error'
      setError(messageText)
      message.error(messageText)
    } finally {
      setLoading(false)
    }
  }

  async function handleValidateQuery() {
    if (!selectedDatabaseId) {
      message.warning('请先选择一个数据库连接')
      return
    }

    setQueryLoading(true)
    try {
      const payload = await apiFetch<QueryValidationResponse>('/query/validate', {
        method: 'POST',
        body: JSON.stringify({
          databaseId: selectedDatabaseId,
          queryText,
        }),
      })
      setValidatedQuery(payload)
      message.success('SQL 校验通过')
    } catch (validateError) {
      const messageText = validateError instanceof Error ? validateError.message : 'Unknown error'
      setError(messageText)
      message.error(messageText)
    } finally {
      setQueryLoading(false)
    }
  }

  async function executeQuery(queryValue: string, querySource: string) {
    if (!selectedDatabaseId) {
      message.warning('请先选择一个数据库连接')
      return
    }

    setQueryLoading(true)
    try {
      const payload = await apiFetch<QueryExecutionResponse>('/query/execute', {
        method: 'POST',
        body: JSON.stringify({
          databaseId: selectedDatabaseId,
          queryText: queryValue,
          querySource,
        }),
      })

      setQueryResult(payload)
      setLastQuerySource(querySource)
      setValidatedQuery({
        databaseId: payload.databaseId,
        statementType: 'SELECT',
        normalizedQuery: payload.executedQuery,
        appliedLimit: payload.executedQuery.toUpperCase().includes('LIMIT 1000'),
        limitValue: payload.rowCount,
        isValid: true,
      })
      await loadDatabaseWorkspace(selectedDatabaseId)
      message.success(`查询完成，返回 ${payload.rowCount} 行`)
    } catch (executeError) {
      const messageText = executeError instanceof Error ? executeError.message : 'Unknown error'
      setError(messageText)
      message.error(messageText)
    } finally {
      setQueryLoading(false)
    }
  }

  async function handleExecuteQuery() {
    await executeQuery(queryText, 'manual')
  }

  async function handleGenerateQuery() {
    if (!selectedDatabaseId) {
      message.warning('请先选择一个数据库连接')
      return
    }

    setQueryLoading(true)
    setError(null)
    try {
      const payload = await apiFetch<GenerateQueryResponse>('/query/generate', {
        method: 'POST',
        body: JSON.stringify({
          databaseId: selectedDatabaseId,
          naturalLanguage,
        }),
      })
      setGeneratedQuery(payload)
      setQueryText(payload.normalizedQuery)
      setValidatedQuery(payload)
      message.success('SQL 已生成并通过安全校验')
    } catch (generateError) {
      const messageText = generateError instanceof Error ? generateError.message : 'Unknown error'
      setError(messageText)
      message.error(messageText)
    } finally {
      setQueryLoading(false)
    }
  }

  async function handleExecuteGeneratedQuery() {
    if (!generatedQuery) {
      return
    }
    await executeQuery(generatedQuery.normalizedQuery, 'natural_language')
  }

  async function handleExport(format: 'csv' | 'json') {
    if (!selectedDatabaseId || !queryResult) {
      return
    }

    setExportLoading(format)
    setError(null)
    try {
      await downloadExportFile(
        '/query/export',
        {
          method: 'POST',
          body: JSON.stringify({
            databaseId: selectedDatabaseId,
            queryText: queryResult.executedQuery,
            exportFormat: format,
            querySource: lastQuerySource,
          }),
        },
        `query-result.${format}`,
      )
      message.success(`${format.toUpperCase()} 文件已下载`)
    } catch (exportError) {
      const messageText = exportError instanceof Error ? exportError.message : 'Unknown error'
      setError(messageText)
      message.error(messageText)
    } finally {
      setExportLoading(null)
    }
  }

  const resultColumns =
    queryResult?.columns.map((column) => ({
      title: column.title,
      dataIndex: column.key,
      key: column.key,
      ellipsis: true,
    })) ?? []

  const resultRows =
    queryResult?.rows.map((row, index) => ({
      key: `${index}`,
      ...row,
    })) ?? []

  return (
    <Layout className="app-shell">
      <Header className="app-header">
        <div>
          <Title level={2} className="app-title">
            DB Query Generator
          </Title>
          <Text className="app-subtitle">连接 PostgreSQL，查看 Schema，并安全执行只读 SQL</Text>
        </div>
        {health ? (
          <Space wrap>
            <Tag color="green">{health.status}</Tag>
            <Tag color={health.databaseReady ? 'blue' : 'red'}>
              SQLite {health.databaseReady ? 'ready' : 'not ready'}
            </Tag>
            <Tag>{health.pythonVersion}</Tag>
          </Space>
        ) : null}
      </Header>

      <Content className="app-content">
        <Row gutter={[18, 18]}>
          <Col xs={24} xl={8}>
            <Space direction="vertical" size={18} className="stack-full">
              <Card title="添加 PostgreSQL 连接" className="panel-card">
                <Form form={form} layout="vertical" onFinish={(values) => void handleCreateDatabase(values)}>
                  <Form.Item
                    label="连接名称"
                    name="name"
                    rules={[{ required: true, message: '请输入连接名称' }]}
                  >
                    <Input placeholder="例如：Local Demo DB" />
                  </Form.Item>
                  <Form.Item
                    label="连接串"
                    name="connectionUrl"
                    rules={[{ required: true, message: '请输入 PostgreSQL 连接串' }]}
                  >
                    <TextArea
                      rows={4}
                      placeholder="postgresql://postgres:postgres@127.0.0.1:5432/db_query_demo"
                    />
                  </Form.Item>
                  <Button type="primary" htmlType="submit" block loading={loading}>
                    创建并同步元数据
                  </Button>
                </Form>
              </Card>

              <Card title="数据库连接" className="panel-card" extra={<Button onClick={() => void loadDatabases()}>刷新</Button>}>
                <List
                  dataSource={databases}
                  locale={{ emptyText: '还没有数据库连接' }}
                  renderItem={(database) => (
                    <List.Item
                      className={database.id === selectedDatabaseId ? 'list-item-active' : 'list-item'}
                      onClick={() => setSelectedDatabaseId(database.id)}
                      actions={[
                        <Popconfirm
                          key="delete"
                          title="删除这个数据库连接？"
                          description="本地保存的 Schema 和查询历史也会被删除。"
                          okText="删除"
                          cancelText="取消"
                          onConfirm={() => void handleDeleteDatabase(database.id)}
                        >
                          <Button type="link" danger size="small" onClick={(event) => event.stopPropagation()}>
                            删除
                          </Button>
                        </Popconfirm>,
                      ]}
                    >
                      <List.Item.Meta
                        title={database.name}
                        description={`${database.databaseType} · ${new Date(database.updatedAt).toLocaleString()}`}
                      />
                    </List.Item>
                  )}
                />
              </Card>
            </Space>
          </Col>

          <Col xs={24} xl={16}>
            <Space direction="vertical" size={18} className="stack-full">
              {error ? (
                <Alert
                  type="warning"
                  showIcon
                  message="当前有一条错误信息"
                  description={error}
                />
              ) : null}

              <Card
                title={selectedDatabase ? `当前连接：${selectedDatabase.name}` : '当前连接'}
                className="panel-card"
                extra={
                  <Button onClick={() => void handleRefreshMetadata()} disabled={!selectedDatabaseId} loading={loading}>
                    刷新元数据
                  </Button>
                }
              >
                {selectedDatabase ? (
                  <Paragraph>
                    <Text strong>Connection URL:</Text> {maskConnectionUrl(selectedDatabase.connectionUrl)}
                  </Paragraph>
                ) : (
                  <Empty description="先创建或选择一个数据库连接" />
                )}
              </Card>

              <Tabs
                defaultActiveKey="schema"
                items={[
                  {
                    key: 'schema',
                    label: 'Schema',
                    children: (
                      <Card className="panel-card no-padding-card">
                        {loading ? (
                          <div className="panel-loading">
                            <Spin />
                          </div>
                        ) : treeData.length > 0 ? (
                          <Tree treeData={treeData} defaultExpandAll />
                        ) : (
                          <Empty description="还没有可展示的元数据" />
                        )}
                      </Card>
                    ),
                  },
                  {
                    key: 'query',
                    label: 'Manual SQL',
                    children: (
                      <Card className="panel-card">
                        <Space direction="vertical" size={16} className="stack-full">
                          <TextArea
                            value={queryText}
                            onChange={(event) => setQueryText(event.target.value)}
                            rows={10}
                            className="query-editor"
                          />
                          <Space wrap>
                            <Button onClick={() => void handleValidateQuery()} loading={queryLoading}>
                              校验 SQL
                            </Button>
                            <Button type="primary" onClick={() => void handleExecuteQuery()} loading={queryLoading}>
                              执行查询
                            </Button>
                          </Space>
                          {validatedQuery ? (
                            <Alert
                              type="success"
                              showIcon
                              message={`校验通过 · LIMIT ${validatedQuery.limitValue}`}
                              description={
                                <pre className="normalized-query">{validatedQuery.normalizedQuery}</pre>
                              }
                            />
                          ) : null}
                          <Table
                            size="small"
                            columns={resultColumns}
                            dataSource={resultRows}
                            scroll={{ x: true }}
                            pagination={{ pageSize: 10 }}
                            locale={{ emptyText: '执行查询后，结果会显示在这里' }}
                          />
                          <Space wrap>
                            <Text type="secondary">
                              {queryResult ? `最近一次查询返回 ${queryResult.rowCount} 行` : '执行查询后可导出结果'}
                            </Text>
                            <Button
                              disabled={!queryResult}
                              loading={exportLoading === 'csv'}
                              onClick={() => void handleExport('csv')}
                            >
                              导出 CSV
                            </Button>
                            <Button
                              disabled={!queryResult}
                              loading={exportLoading === 'json'}
                              onClick={() => void handleExport('json')}
                            >
                              导出 JSON
                            </Button>
                          </Space>
                        </Space>
                      </Card>
                    ),
                  },
                  {
                    key: 'ai-query',
                    label: 'AI Query',
                    children: (
                      <Card className="panel-card">
                        <Space direction="vertical" size={16} className="stack-full">
                          <div>
                            <Text strong>用自然语言描述你想查询的数据</Text>
                            <Paragraph type="secondary" className="helper-copy">
                              Schema 会随请求发送给模型，生成的 SQL 仍会经过只读校验和行数限制。
                            </Paragraph>
                          </div>
                          <TextArea
                            value={naturalLanguage}
                            onChange={(event) => setNaturalLanguage(event.target.value)}
                            rows={4}
                            placeholder="例如：查询每个用户的订单总金额，并按金额从高到低排列"
                          />
                          <Space wrap>
                            <Button type="primary" onClick={() => void handleGenerateQuery()} loading={queryLoading}>
                              生成 SQL
                            </Button>
                            <Button
                              onClick={() => void handleExecuteGeneratedQuery()}
                              disabled={!generatedQuery}
                              loading={queryLoading}
                            >
                              执行生成结果
                            </Button>
                          </Space>
                          {generatedQuery ? (
                            <Alert
                              type="success"
                              showIcon
                              message={`已通过安全校验 · ${generatedQuery.model}`}
                              description={
                                <pre className="normalized-query">{generatedQuery.normalizedQuery}</pre>
                              }
                            />
                          ) : (
                            <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="生成结果会显示在这里" />
                          )}
                          {queryResult ? (
                            <>
                              <Table
                                size="small"
                                columns={resultColumns}
                                dataSource={resultRows}
                                scroll={{ x: true }}
                                pagination={{ pageSize: 10 }}
                                title={() => `查询结果 · ${queryResult.rowCount} 行`}
                              />
                              <Space wrap>
                                <Button
                                  loading={exportLoading === 'csv'}
                                  onClick={() => void handleExport('csv')}
                                >
                                  导出 CSV
                                </Button>
                                <Button
                                  loading={exportLoading === 'json'}
                                  onClick={() => void handleExport('json')}
                                >
                                  导出 JSON
                                </Button>
                              </Space>
                            </>
                          ) : null}
                        </Space>
                      </Card>
                    ),
                  },
                  {
                    key: 'history',
                    label: 'History',
                    children: (
                      <Card className="panel-card">
                        <List
                          dataSource={history}
                          locale={{ emptyText: '还没有查询历史' }}
                          renderItem={(item) => (
                            <List.Item>
                              <List.Item.Meta
                                title={
                                  <Space wrap>
                                    <Tag color={item.executionStatus === 'success' ? 'green' : 'red'}>
                                      {item.executionStatus}
                                    </Tag>
                                    <Tag>{item.querySource}</Tag>
                                    <Text>{new Date(item.createdAt).toLocaleString()}</Text>
                                  </Space>
                                }
                                description={<pre className="history-query">{item.queryText}</pre>}
                              />
                            </List.Item>
                          )}
                        />
                      </Card>
                    ),
                  },
                ]}
              />
            </Space>
          </Col>
        </Row>
      </Content>
    </Layout>
  )
}

function RootApp() {
  return (
    <AntApp>
      <App />
    </AntApp>
  )
}

export default RootApp
