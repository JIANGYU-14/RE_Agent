# Backend API 文档

本文档基于当前代码实现生成，入口为 `RE_Agent/app/main.py`，默认将业务 API 挂载在 `/paperapi` 前缀下。

## 1. 服务入口与路由

- FastAPI 应用：`RE_Agent/app/main.py:8`
- 路由挂载：
  - `/paperapi`：`sessions`、`chat`、`history`（`RE_Agent/app/main.py:54-56`）
  - 非 `/paperapi`：健康检查与初始化（`RE_Agent/app/main.py:27-50`）

## 2. 数据库结构（SQLAlchemy Core）

建表逻辑：`RE_Agent/app/core/db.py:34-41`（通过 `create_all` 创建，未使用迁移工具）。

### 2.1 `sessions` 表

定义：`RE_Agent/app/repositories/sessions_repo.py:23-33`

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| `id` | Integer | PK | 自增主键 |
| `session_id` | String | NOT NULL, UNIQUE | 对外会话 ID（UUID 字符串） |
| `user_id` | String | NOT NULL | 用户标识（来自请求 Body） |
| `status` | String | NOT NULL | `active` / `archived` |
| `title` | Text | NOT NULL | 会话标题，默认 `新对话` |
| `created_at` | DateTime | NOT NULL | 创建时间（北京时间，UTC+8） |
| `updated_at` | DateTime | NOT NULL | 更新时间（北京时间，UTC+8） |

仓储方法：

- 创建会话：`SessionsRepo.create_session`（`RE_Agent/app/repositories/sessions_repo.py:40-63`）
- 列表会话：`SessionsRepo.list_sessions`（仅 `status=active`，按 `updated_at desc`）（`RE_Agent/app/repositories/sessions_repo.py:65-93`）
- 查询会话：`SessionsRepo.get_session`（`RE_Agent/app/repositories/sessions_repo.py:95-122`）
- 更新时间：`SessionsRepo.touch_session`（`RE_Agent/app/repositories/sessions_repo.py:124-133`）
- 更新标题：`SessionsRepo.update_title`（`RE_Agent/app/repositories/sessions_repo.py:134-145`）
- 归档会话：`SessionsRepo.archive_session`（`RE_Agent/app/repositories/sessions_repo.py:147-158`）

### 2.2 `messages` 表

定义：`RE_Agent/app/repositories/messages_repo.py:26-33`

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| `id` | Integer | PK | 自增主键 |
| `session_id` | String | NOT NULL | 关联会话 ID（当前未加外键） |
| `role` | String(16) | NOT NULL | `user` / `assistant` 等 |
| `created_at` | DateTime | NOT NULL | 创建时间（北京时间，UTC+8） |

### 2.3 `message_parts` 表

定义：`RE_Agent/app/repositories/messages_repo.py:35-50`

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| `id` | Integer | PK | 自增主键 |
| `message_id` | Integer | NOT NULL, FK -> `messages.id` | 外键，`ondelete=CASCADE` |
| `type` | String(16) | NOT NULL | `text` / `image` / `audio` / `tool` |
| `content` | Text | nullable | 文本内容（常用于 `type=text`） |
| `url` | Text | nullable | 资源 URL（常用于 `type=image/audio`） |
| `metadata` | JSONB | nullable | 扩展信息（PostgreSQL `JSONB`） |
| `sort_order` | Integer | NOT NULL | parts 的顺序（从 0 开始） |

读写逻辑：

- 写入：`MessagesRepo.save_message` 先插入 `messages` 拿到 `id`，再按顺序插入 `message_parts`（`RE_Agent/app/repositories/messages_repo.py:61-103`）
- 读取：`MessagesRepo.list_messages` 将 JOIN 结果聚合为按 message 分组的结构（`RE_Agent/app/repositories/messages_repo.py:106-155`）

## 3. 认证与鉴权

当前 RE_Agent 不强制要求任何鉴权 Header。
对话接口调用 AgentKit 的鉴权来自环境变量 `AGENTKIT_API_KEY`（`RE_Agent/app/core/agentkit_client.py`）。

## 4. API 列表（/paperapi）

### 4.1 创建会话

- 方法：`POST /paperapi/sessions`
- 代码：`RE_Agent/app/api/sessions.py:23-31`
- Body：

```json
{
  "user_id": "u123"
}
```
- Response（200）：

```json
{
  "session_id": "c7b5f0b8-0000-0000-0000-000000000000",
  "user_id": "u123",
  "status": "active",
  "title": "新对话",
  "created_at": "2026-01-18T12:00:00.000000+08:00",
  "updated_at": "2026-01-18T12:00:00.000000+08:00"
}
```

### 4.2 获取用户会话列表（仅 active）

- 方法：`GET /paperapi/sessions/list`
- 代码：`RE_Agent/app/api/sessions.py:34-43`
- Query：
  - `user_id: string`（必填）
- Response（200）：

```json
{
  "sessions": [
    {
      "session_id": "c7b5f0b8-0000-0000-0000-000000000000",
      "user_id": "u123",
      "status": "active",
      "title": "新对话",
      "created_at": "2026-01-18T12:00:00.000000+08:00",
      "updated_at": "2026-01-18T12:00:10.000000+08:00"
    }
  ]
}
```

### 4.3 会话重命名

- 方法：`PATCH /paperapi/sessions/{session_id}/title`
- 代码：`RE_Agent/app/api/sessions.py`
- Body：

```json
{
  "title": "我的新标题"
}
```

- 示例：

```bash
curl -X PATCH "http://localhost:8002/paperapi/sessions/<session_id>/title" \
  -H "Content-Type: application/json" \
  -d '{"title":"我的新标题"}'
```

- Response（200）：返回更新后的 session

```json
{
  "session_id": "c7b5f0b8-0000-0000-0000-000000000000",
  "user_id": "u123",
  "status": "active",
  "title": "我的新标题",
  "created_at": "2026-01-18T12:00:00.000000+08:00",
  "updated_at": "2026-01-18T12:00:10.000000+08:00"
}
```

### 4.4 会话删除（归档 / 永久删除）

- 方法：`DELETE /paperapi/sessions/{session_id}`
- 代码：`RE_Agent/app/api/sessions.py`
- Query：
  - `hard: bool`（可选，默认 `false`）
- Response（200）：

```json
{"ok": true}
```

- 示例（归档，默认）：

```bash
curl -X DELETE "http://localhost:8002/paperapi/sessions/<session_id>"
```

- 示例（永久删除）：

```bash
curl -X DELETE "http://localhost:8002/paperapi/sessions/<session_id>?hard=true"
```

说明：
- `hard=false`：将会话 `status` 更新为 `archived`，会从 `GET /paperapi/sessions/list` 的返回中消失。
- `hard=true`：永久删除会话记录，并清理该会话下的 messages / message_parts。

### 4.5 对话（写入消息 + 调用 AgentKit 流式输出 + 写入回复 + 触发标题生成）

- 方法：`POST /paperapi/chat`
- 代码：`RE_Agent/app/api/chat.py:45-107`
- Body：`ChatRequest`（`RE_Agent/app/api/chat.py:22-25`）

```json
{
  "session_id": "c7b5f0b8-0000-0000-0000-000000000000",
  "text": "你好",
  "use_public_paper": false
}
```

- 参数说明：
  - `session_id`: (Required) 会话 ID
  - `text`: (Required) 用户输入文本
  - `use_public_paper`: (Optional, default=false) 是否启用公开知识库搜索。若为 true，Agent 将同时检索私有库与公开库并聚合结果。
- 错误码：
  - 404：`session not found`（会话不存在）
  - 409：`session is not active`（会话非 active，例如已归档）

- Response：`text/event-stream`

```
data: {"type": "text", "content": "你好！我是PaperAgent，企业知识问答助手。请问有什么可以帮到您的吗？"}

data: {"type": "thought", "content": "{...status-update...}"}
```

说明：
- `type=text`：可直接展示给用户的内容片段
- `type=thought`：过程状态与调试信息
- `type=error`：流式错误信息

### 4.6 获取会话消息历史

- 方法：`GET /paperapi/sessions/{session_id}/messages`
- 代码：`RE_Agent/app/api/history.py:12-18`
- Response（200）：

```json
{
  "session_id": "c7b5f0b8-0000-0000-0000-000000000000",
  "title": "新对话",
  "messages": [
    {
      "role": "user",
      "created_at": "2026-01-18T12:00:00.000000+08:00",
      "parts": [
        {
          "type": "text",
          "content": "你好",
          "url": null,
          "metadata": null
        }
      ]
    },
    {
      "role": "assistant",
      "created_at": "2026-01-18T12:00:01.000000+08:00",
      "parts": [
        {
          "type": "text",
          "content": "你好！",
          "url": null,
          "metadata": null
        }
      ]
    }
  ]
}
```

- 错误码：
  - 404：`session not found`（会话不存在，或已删除/归档）

## 5. 健康检查与初始化（非 /api）

### 5.1 数据库连通性检查

- 方法：`GET /health/db`
- 代码：`RE_Agent/app/main.py:27-39`
- 成功：

```json
{"ok": true}
```

- 失败（500）：

```json
{"detail": "db not ready: ..."}
```

### 5.2 初始化建表

- 方法：`POST /admin/init-db`
- 代码：`RE_Agent/app/main.py:41-50`
- 成功：

```json
{"ok": true}
```

## 6. 标题生成与更新规则

触发点：每次 `/paperapi/chat` 流式结束并保存助手消息后调用 `async_generate(session_id)`（`backend_stream/app/api/chat.py:95-101`）。

规则：`backend_stream/app/services/session_title.py:15-73`

- 若 session 不存在：跳过
- 若 session 的 `title != "新对话"`：跳过（即持续对话不会再次改标题）
- 若历史消息数 `< 2`：跳过
- 取前 4 条消息拼接生成标题
- 生成成功后调用 `SessionsRepo.update_title` 写回数据库

同步/异步开关：`backend_stream/app/services/session_title.py:76-86`

- `TITLE_GENERATION_SYNC=true`：同步生成（便于调试）
- 默认：后台线程异步生成

## 7. 外部依赖服务

### 7.1 AgentKit（对话生成）

实现：`backend_stream/app/core/agentkit_client.py:10-187`

- 环境变量：
  - `AGENTKIT_BASE_URL`
  - `AGENTKIT_API_KEY`
  - `AGENTKIT_TIMEOUT_SECONDS`（默认 60 秒）
- 请求：
  - `POST {AGENTKIT_BASE_URL}/`
  - JSON-RPC 2.0
  - `method: "message/stream"`
  - `params.metadata.session_id` 会携带当前会话 ID
- 返回解析：
  - 按 SSE `data:` 行解析事件，并抽取 `message`/`thought`/`artifact-update` 中的文本（`backend_stream/app/core/agentkit_client.py:120-179`）

### 7.2 LLM（标题生成）

实现：`backend/app/core/title_agent_client.py:14-119`

- 环境变量：
  - `LLM_BASE_URL`（默认 `https://ark.cn-beijing.volces.com`）
  - `LLM_API_KEY`
  - `LLM_MODEL`（默认 `doubao-seed-1-6-lite-251015`）
  - `LLM_TIMEOUT_SECONDS`（默认 20 秒）
  - `TITLE_LLM_MAX_COMPLETION_TOKENS`（默认 256）
- 请求：
  - `POST {LLM_BASE_URL}/api/v3/chat/completions`
  - `reasoning_effort: "minimal"`

## 8. 环境变量清单（Backend）

基础配置（`backend/app/config.py:15-19`）：

- `DATABASE_URL`
- `AGENTKIT_BASE_URL`
- `AGENTKIT_API_KEY`

其他可选：

- `AGENTKIT_TIMEOUT_SECONDS`
- `CHAT_MAX_ASSISTANT_CHARS`
- `TITLE_GENERATION_SYNC`
- `LLM_BASE_URL`
- `LLM_API_KEY`
- `LLM_MODEL`
- `LLM_TIMEOUT_SECONDS`
- `TITLE_LLM_MAX_COMPLETION_TOKENS`

## 9. 调用示例（curl）

假设服务地址为 `https://sd5mgjn9itm8rf8och9rg.apigateway-cn-beijing.volceapi.com`。

初始化建表：

```bash
curl -X POST 'https://sd5mgjn9itm8rf8och9rg.apigateway-cn-beijing.volceapi.com/admin/init-db'
```

创建会话：

```bash
curl -X POST 'https://sd5mgjn9itm8rf8och9rg.apigateway-cn-beijing.volceapi.com/paperapi/sessions' \
  -H 'Content-Type: application/json' \
  -d '{"user_id":"u123"}'
```

发送对话：

```bash
curl -X POST 'https://sd5mgjn9itm8rf8och9rg.apigateway-cn-beijing.volceapi.com/paperapi/chat' \
  -H 'Content-Type: application/json' \
  -d '{"session_id":"<session_id>","text":"你好","use_public_paper":false}'
```

获取历史：

```bash
curl 'https://sd5mgjn9itm8rf8och9rg.apigateway-cn-beijing.volceapi.com/paperapi/sessions/<session_id>/messages'
```

列出会话：

```bash
curl 'https://sd5mgjn9itm8rf8och9rg.apigateway-cn-beijing.volceapi.com/paperapi/sessions/list?user_id=debug_user'
```
