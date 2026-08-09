# DB Query Generator

一个面向 PostgreSQL 的数据库查询生成器 MVP。用户可以连接数据库、查看 Schema、手写只读 SQL，也可以输入自然语言生成 SQL 并预览后执行。

## 已完成能力

- PostgreSQL 连接创建、选择和删除
- 表、视图、列和主键元数据同步
- Schema 导航树
- 只读 SQL 校验，自动补充 `LIMIT 1000`
- SQL 执行、结果表格和查询历史
- 查询结果导出为 CSV 或 JSON
- OpenAI 兼容接口的自然语言生成 SQL
- SQLite 保存连接、元数据和查询历史

## 快速启动

准备 Python 3.12、Node.js、uv 和 Docker Desktop，然后分别启动：

```bash
docker compose up -d

cd backend
uv sync
uv run backend

cd ../frontend
npm install
npm run dev -- --host 0.0.0.0
```

打开 `http://127.0.0.1:5173`。后端健康检查地址为 `http://127.0.0.1:8000/api/v1/health`。

## 自然语言生成配置

```bash
cp backend/.env.example backend/.env
```

在 `backend/.env` 中填写 `OPENAI_API_KEY`。`OPENAI_BASE_URL` 可用于 OpenAI 兼容服务，`OPENAI_MODEL` 用于指定模型。前端 API 地址可通过 `frontend/.env` 中的 `VITE_API_BASE_URL` 覆盖。

未配置 API Key 时，手写 SQL 功能仍可使用，AI Query 会返回明确的配置提示。

## 数据导出

查询成功后，在结果区点击“导出 CSV”或“导出 JSON”。也可以使用命令行：

```bash
./scripts/export-query.sh \
  --database-id "<database-id>" \
  --format csv \
  --query "select * from users order by id" \
  --output users.csv
```

设计说明见 [FEATURE_EXPORT.md](FEATURE_EXPORT.md)。

## 测试与检查

```bash
cd backend
uv run python -m unittest discover -s tests -v

cd ../frontend
npm run lint
npm run build
```

更多本地运行和演示数据库说明见 [RUNBOOK.md](RUNBOOK.md)，项目分阶段计划见 [PROJECT_PLAN.md](PROJECT_PLAN.md)。
