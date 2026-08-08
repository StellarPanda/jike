# 本地运行说明

## 1. 当前项目状态

当前项目包含以下本地服务：

- 前端：Vite + React
- 后端：FastAPI + uv
- 应用存储：SQLite
- 演示业务库：PostgreSQL（通过 Docker Compose 启动）

## 2. 启动前端和后端

### 后端

```bash
cd backend
uv run backend
```

后端地址：

- `http://127.0.0.1:8000`
- `http://127.0.0.1:8000/api/v1/health`

### 前端

```bash
cd frontend
npm run dev -- --host 0.0.0.0
```

前端地址：

- `http://127.0.0.1:5173`

## 3. 启动本地 PostgreSQL 示例库

确保 Docker Desktop 已启动后，在项目根目录运行：

```bash
docker compose up -d
```

示例数据库配置：

- Host: `127.0.0.1`
- Port: `5432`
- Database: `db_query_demo`
- User: `postgres`
- Password: `postgres`

推荐在前端中填写的连接串：

```text
postgresql://postgres:postgres@127.0.0.1:5432/db_query_demo
```

## 4. 当前已实现能力

- 添加 PostgreSQL 连接
- 拉取表和列元数据
- 展示 Schema 树
- 校验只读 SQL
- 自动补 `LIMIT 1000`
- 执行查询并显示结果
- 记录最近查询历史

## 5. 当前未完成能力

- 更完整的错误态展示
- Monaco 风格 SQL 编辑器
- 更复杂的查询结果交互

## 6. 配置自然语言生成

复制 `backend/.env.example` 为 `backend/.env`，填写 `OPENAI_API_KEY`，然后重启后端。也可以通过 shell 环境变量配置 `OPENAI_API_KEY`、`OPENAI_BASE_URL` 和 `OPENAI_MODEL`。

没有配置 API Key 时，AI Query 页面会保留可用的手写 SQL 功能，并显示明确的配置错误。
