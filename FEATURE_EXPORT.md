# 数据导出功能设计说明

## 1. 需求拆解

第三周作业要求在已有数据库查询工具上增加数据导出能力，并尝试把“执行查询”和“导出结果”组织成一个自动化流程。本次实现拆成四个子任务：

1. 获取查询结果：复用现有只读 SQL 校验和 PostgreSQL 执行逻辑。
2. 格式化数据：将列名和结果行分别转换为 CSV 或 JSON。
3. 创建文件：后端返回带文件名的下载响应，前端触发浏览器下载。
4. 自动化触发：提供前端按钮、Shell 命令和 Claude Code 自定义命令。

## 2. 功能设计

用户在 Manual SQL 或 AI Query 页面执行查询后，结果区显示“导出 CSV”和“导出 JSON”按钮。按钮只导出最近一次成功执行的查询，未执行查询时保持禁用，避免导出过期或不存在的结果。

导出接口为：

```text
POST /api/v1/query/export
```

请求示例：

```json
{
  "databaseId": "<database-id>",
  "queryText": "select id, name from users order by id",
  "exportFormat": "csv",
  "querySource": "manual"
}
```

CSV 文件包含第一行表头和后续数据行；JSON 文件包含 `executedQuery`、`rowCount`、`columns` 和 `rows`，便于后续程序继续处理。

## 3. 安全与一致性

导出接口不直接接收未经检查的数据库结果，而是复用原有的 `execute_sql` 流程。因此导出操作仍然具备：

- 只允许单条只读 SQL
- 自动补充 `LIMIT 1000`
- 显式限制最大 `LIMIT 5000`
- 成功或失败都记录查询历史
- 数据库连接信息不写入导出文件

## 4. 自动化流程

### 页面操作

用户执行查询后点击格式按钮，前端把最近一次执行的规范化 SQL 和目标格式发送给后端，浏览器自动下载文件。

### Shell 命令

可以使用：

```bash
./scripts/export-query.sh \
  --database-id "<database-id>" \
  --format json \
  --query "select * from users order by id" \
  --output users.json
```

这个命令把“调用 API、获取结果、保存文件、报告路径”串成一步。

### Claude Code 自定义命令

`.claude/commands/export-query.md` 描述了 `/export-query` 的 Agent 工作流。Agent 负责从自然语言中确认数据库 ID、导出格式和 SQL，然后调用 `scripts/export-query.sh`，最后报告文件位置。真正的安全校验仍由后端完成，不依赖 Agent 自己判断。

## 5. 验证方式

自动化测试覆盖 CSV 表头/数据行和 JSON 元数据/结果行。端到端验证使用本地 PostgreSQL 演示库执行查询后分别请求 CSV 和 JSON，并检查返回文件内容、媒体类型和下载文件名。

## 6. 后续可扩展方向

- 大结果集改用流式响应，降低内存占用
- 增加 Excel、Parquet 等格式
- 增加导出任务进度和历史下载记录
- 对导出文件增加脱敏规则和过期清理
