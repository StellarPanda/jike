# 数据库查询生成器项目计划

## 1. 项目目标

基于课程文字稿，本项目将实现一个数据库查询生成器 MVP。用户可以连接 PostgreSQL 数据库，查看数据库元数据，手动执行 SQL 查询，或者通过自然语言生成 SQL 并获取结果。

本项目优先验证以下能力：

- 连接并管理 PostgreSQL 数据库
- 抓取并展示表、视图、列等基础元数据
- 执行手写 SQL 查询
- 校验 SQL，仅允许安全的 `SELECT` 查询
- 当查询未设置 `LIMIT` 时自动补充默认限制
- 使用大模型根据自然语言和数据库 Schema 生成 SQL
- 将查询历史和元数据存储到 SQLite

## 2. MVP 范围

### 2.1 本期要做

- 支持添加、查看、删除数据库连接
- 支持从 PostgreSQL 读取表、视图、列、主键信息
- 支持展示数据库导航树
- 支持手写 SQL 查询并返回表格结果
- 支持 SQL 语法校验和只读限制
- 支持自然语言生成 SQL
- 支持保存查询历史
- 支持基础错误提示和健康检查接口

### 2.2 本期不做

- 用户注册、登录、权限控制
- 多数据库联合查询
- PostgreSQL 之外的数据库类型
- 复杂图表、分析报表和 BI 能力
- 移动端适配
- 复杂导出能力

## 3. 用户流程

### 3.1 数据库连接

1. 用户输入数据库名称和 PostgreSQL 连接串
2. 后端测试连接是否有效
3. 连接成功后读取元数据
4. 元数据写入 SQLite
5. 前端展示已连接数据库及其 Schema 导航

### 3.2 手写 SQL 查询

1. 用户选择数据库
2. 用户在编辑器输入 SQL
3. 后端解析 SQL
4. 若不是 `SELECT` 或语法有误，则返回错误
5. 若未带 `LIMIT`，后端自动补上默认值
6. 执行查询并返回结果表格
7. 写入查询历史

### 3.3 自然语言生成 SQL

1. 用户选择数据库
2. 用户输入自然语言需求
3. 后端读取该数据库的表结构元数据
4. 将用户输入和 Schema 一起发送给 LLM
5. LLM 返回 SQL
6. 后端再次校验 SQL 安全性
7. 可选择直接执行并展示结果

## 4. 技术方案

### 4.1 后端

- 语言：Python 3.12
- 框架：FastAPI
- 运行与依赖：uv
- 本地存储：SQLite
- PostgreSQL 驱动：`psycopg`
- SQL 解析：`sqlglot`
- 数据模型：Pydantic

### 4.2 前端

- 语言：TypeScript
- 框架：React + Vite
- UI：Ant Design
- 样式：Tailwind CSS
- 数据请求：优先使用轻量方案，避免过度封装

### 4.3 LLM 集成

- 使用 OpenAI API
- 通过环境变量注入 `OPENAI_API_KEY`
- 提示词中注入数据库 Schema
- 要求输出单条可执行 SQL，不允许解释性文本

## 5. 数据模型

SQLite 中至少包含以下核心表：

### 5.1 database_connections

- `id`
- `name`
- `database_type`
- `connection_url`
- `created_at`
- `updated_at`

### 5.2 table_metadata

- `id`
- `database_id`
- `schema_name`
- `table_name`
- `table_type`
- `created_at`
- `updated_at`

### 5.3 column_metadata

- `id`
- `table_id`
- `column_name`
- `data_type`
- `is_nullable`
- `is_primary_key`
- `ordinal_position`

### 5.4 query_history

- `id`
- `database_id`
- `query_text`
- `query_source`
- `execution_status`
- `error_message`
- `created_at`

说明：

- `query_source` 用于区分 `manual` 和 `natural_language`
- 查询结果本期不长期存 SQLite，只在请求时返回

## 6. API 草案

### 6.1 系统接口

- `GET /api/v1/health`

### 6.2 数据库连接

- `GET /api/v1/databases`
- `POST /api/v1/databases`
- `GET /api/v1/databases/{databaseId}`
- `DELETE /api/v1/databases/{databaseId}`
- `POST /api/v1/databases/{databaseId}/refresh-metadata`

### 6.3 元数据

- `GET /api/v1/databases/{databaseId}/metadata`

### 6.4 SQL 查询

- `POST /api/v1/query/execute`
- `POST /api/v1/query/validate`

### 6.5 自然语言生成 SQL

- `POST /api/v1/query/generate`

### 6.6 查询历史

- `GET /api/v1/databases/{databaseId}/query-history`

## 7. 关键规则

- 仅允许执行 `SELECT` 查询
- 默认 `LIMIT` 设为 `1000`
- 如果用户显式设置 `LIMIT`，则保留，但后续可考虑上限保护
- 后端返回 JSON 字段统一使用 CamelCase
- 前后端保持明确类型定义
- 后端开启 CORS，便于本地联调

## 8. 分阶段实施计划

### Phase 1：基础架构

交付内容：

- 初始化前后端项目
- 搭建 FastAPI 基础结构
- 搭建 React + Vite 前端壳子
- 建立 SQLite 数据库和基础模型
- 健康检查接口
- 基础页面布局

验收标准：

- 前后端项目都能本地启动
- 健康检查接口可访问
- SQLite 初始化成功

### Phase 2：数据库连接与手写 SQL

交付内容：

- 添加 PostgreSQL 数据库连接
- 抓取数据库元数据
- 展示数据库导航树
- SQL 校验器
- 手写 SQL 执行
- 查询历史记录

验收标准：

- 可以成功连接 PostgreSQL
- 可以看到表和列信息
- 非 `SELECT` 语句被拦截
- 无 `LIMIT` 查询会自动补全
- 查询结果可以表格展示

### Phase 3：自然语言生成 SQL

交付内容：

- Schema 注入
- 自然语言转 SQL
- 生成结果预览
- 一键执行生成 SQL

验收标准：

- 输入简单自然语言可生成合理 SQL
- 生成 SQL 仍会经过安全校验
- 查询结果能正常返回

### Phase 4：打磨与文档

交付内容：

- 界面整理
- 错误提示优化
- README 和快速启动文档
- 环境变量说明

验收标准：

- 新人按文档可在本地跑起来
- 常见错误有清晰提示
- 页面结构清晰可用

## 9. 开发顺序建议

建议按以下顺序推进：

1. 先做后端健康检查和 SQLite 初始化
2. 完成数据库连接管理和元数据抓取
3. 完成 SQL 校验和执行接口
4. 再接前端页面和查询结果展示
5. 最后接入自然语言生成 SQL

## 10. 风险与注意事项

- 本机 Python 原先为 3.9，项目应固定到 3.12 环境
- PostgreSQL 连接串需要真实可访问实例
- LLM 生成 SQL 可能不稳定，必须二次校验
- Python 项目在缺少测试时，批量替换代码有风险
- 元数据同步在大库上可能耗时较高，后续可增加分页或懒加载

## 11. 当前执行决定

本项目将优先实现一个可运行的本地 MVP，目标是在保证结构清晰的前提下，先打通完整链路：

- 数据库连接
- 元数据读取
- 手写查询
- 自然语言生成 SQL
- 结果展示

后续如需要，再扩展导出、多数据库支持和更强的 UI 体验。
