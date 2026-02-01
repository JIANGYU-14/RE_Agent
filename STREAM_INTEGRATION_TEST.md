# Agent Service 本地流式联调文档

本文档用于指导和验证 `RE_Agent` (8002) 与 `agent_service` (8000) 之间的流式通信链路。

## 1. 环境准备

### 1.1 服务架构
*   **Agent Service**: 负责 LLM 交互与工具调用。
    *   路径: `agent_service/src`
    *   端口: `8000`
    *   启动: `python agent.py`
*   **RE_Agent Backend**: 负责 API 接入、流式转发与数据持久化。
    *   路径: `RE_Agent`
    *   端口: `8002`
    *   启动: `python run.py`

### 1.2 启动步骤
确保两个服务均已启动。

**Terminal A (Agent Service):**
```bash
cd agent_service/src
# 确保已安装依赖: pip install -r requirements.txt
python agent.py
```

**Terminal B (RE_Agent Backend):**
```bash
cd RE_Agent
# 确保已安装依赖: pip install -r requirements.txt
python run.py
```

## 2. 测试用例

### 2.1 数据库健康检查
验证数据库连通性。

**请求命令:**
```bash
curl http://localhost:8002/health/db
```

**预期输出:**
```json
{"ok": true}
```

### 2.2 初始化建表
仅首次启动或本地重置后执行。

**请求命令:**
```bash
curl -X POST http://localhost:8002/admin/init-db
```

**预期输出:**
```json
{"ok": true}
```

### 2.3 创建会话

**请求命令:**
```bash
curl -X POST http://localhost:8002/paperapi/sessions \
  -H "Content-Type: application/json" \
  -d '{"user_id":"debug_user"}'
```
记录返回的 `session_id`，用于后续请求。

### 2.4 获取会话列表
验证只返回 `active` 会话。

**请求命令:**
```bash
curl "http://localhost:8002/paperapi/sessions/list?user_id=debug_user"
```

**预期输出:**
返回包含 `sessions` 数组，并能找到上一步创建的 `session_id`。

### 2.5 会话重命名

**请求命令:**
```bash
curl -X PATCH http://localhost:8002/paperapi/sessions/<session_id>/title \
  -H "Content-Type: application/json" \
  -d '{"title":"我的新标题"}'
```

**预期输出:**
返回更新后的会话对象，`title` 为新值。

### 2.6 会话删除（归档 / 永久删除）

**请求命令（归档，默认）:**
```bash
curl -X DELETE http://localhost:8002/paperapi/sessions/<session_id>
```

**预期输出:**
```json
{"ok": true}
```

**验证命令（可选）:**
```bash
curl "http://localhost:8002/paperapi/sessions/list?user_id=debug_user"
```
预期已归档会话不再出现在列表中。

**请求命令（永久删除）:**
```bash
curl -X DELETE "http://localhost:8002/paperapi/sessions/<session_id>?hard=true"
```

**预期输出:**
```json
{"ok": true}
```

**验证要点:**
- 永久删除后再次调用 `POST /paperapi/chat`，预期返回 404 `session not found`。
- 归档后再次调用 `POST /paperapi/chat`，预期返回 409 `session is not active`。

### 2.7 基础问候 (Basic Greeting)
验证链路连通性及基础 SSE 格式。

**前置步骤：创建会话（必须）**
```bash
curl -X POST http://localhost:8002/paperapi/sessions \
  -H "Content-Type: application/json" \
  -d '{"user_id":"debug_user"}'
```
记录返回的 `session_id`，用于后续请求。

**请求命令:**
```bash
curl -N -X POST http://localhost:8002/paperapi/chat \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "<session_id>",
    "text": "你好"
  }'
```

**预期输出 (示例):**
```
data: {"type": "text", "content": "你好"}

data: {"type": "text", "content": "！"}

data: {"type": "text", "content": "有什么"}
...
```

### 2.8 知识库检索 (KB Retrieval)
验证 Agent 执行复杂工具调用时的流式响应。

**前置步骤：创建会话（必须）**
```bash
curl -X POST http://localhost:8002/paperapi/sessions \
  -H "Content-Type: application/json" \
  -d '{"user_id":"debug_user"}'
```
记录返回的 `session_id`，用于后续请求。

**请求命令:**
```bash
curl -N -X POST http://localhost:8002/paperapi/chat \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "<session_id>",
    "text": "总结稀土改性3D打印材料的研究",
    "use_public_paper": false
  }'
```

**预期输出:**
应包含逐步生成的总结内容，而非一次性返回长文本。

### 2.9 获取会话消息历史
验证 chat 写入的消息已持久化。

**前置步骤：完成一次对话**
执行 2.7 或 2.8 后再进行本步骤。

**请求命令:**
```bash
curl http://localhost:8002/paperapi/sessions/<session_id>/messages
```

**预期输出:**
返回 `messages` 数组，包含 `user` 与 `assistant` 的消息记录。

### 2.10 异常处理
验证 Agent 服务未启动时的报错。

**操作:** 停止 8000 端口服务后执行 2.7 或 2.8 的请求命令。

**预期输出:**
```
data: {"type": "error", "content": "Agent 服务请求失败: ..."}
```

## 3. 实际测试记录

### 3.1 基础问候测试 (2026-01-28)
**状态**: ✅ 通过
**执行命令**:
```bash
curl -X POST http://localhost:8002/paperapi/sessions \
  -H "Content-Type: application/json" \
  -d '{"user_id":"debug_user"}'
```
记录返回的 `session_id`，用于后续请求。
```bash
curl -N -X POST http://localhost:8002/paperapi/chat \
  -H "Content-Type: application/json" \
  -d '{"session_id": "<session_id>", "text": "你好"}'
```
**实际输出**:
```
data: {"type": "thought", "content": "{\"contextId\": \"eba20a57-57d5-46b5-b8c0-546d898d8f21\", \"final\": false, \"kind\": \"status-update\", \"status\": {\"message\": {\"contextId\": \"eba20a57-57d5-46b5-b8c0-546d898d8f21\", \"kind\": \"message\", \"messageId\": \"c83dfe07-6d91-438b-9ee7-cbf034cad628\", \"parts\": [{\"kind\": \"text\", \"text\": \"你好\"}], \"role\": \"user\", \"taskId\": \"08fa3006-0ba5-4a24-88de-7c81888ad83f\"}, \"state\": \"submitted\", \"timestamp\": \"2026-01-28T15:07:00.029596+00:00\"}, \"taskId\": \"08fa3006-0ba5-4a24-88de-7c81888ad83f\"}"}

data: {"type": "thought", "content": "{\"contextId\": \"eba20a57-57d5-46b5-b8c0-546d898d8f21\", \"final\": false, \"kind\": \"status-update\", \"metadata\": {\"adk_app_name\": \"PaperAgent\", \"adk_user_id\": \"A2A_USER_eba20a57-57d5-46b5-b8c0-546d898d8f21\", \"adk_session_id\": \"eba20a57-57d5-46b5-b8c0-546d898d8f21\"}, \"status\": {\"state\": \"working\", \"timestamp\": \"2026-01-28T15:07:00.079437+00:00\"}, \"taskId\": \"08fa3006-0ba5-4a24-88de-7c81888ad83f\"}"}

data: {"type": "text", "content": "你好！我是PaperAgent，企业知识问答助手。请问有什么可以帮到您的吗？"}

data: {"type": "thought", "content": "{\"contextId\": \"eba20a57-57d5-46b5-b8c0-546d898d8f21\", \"final\": true, \"kind\": \"status-update\", \"status\": {\"state\": \"completed\", \"timestamp\": \"2026-01-28T15:07:04.060257+00:00\"}, \"taskId\": \"08fa3006-0ba5-4a24-88de-7c81888ad83f\"}"}
```

### 3.2 知识库检索测试 (2026-01-28)
**状态**: ✅ 通过
**执行命令**:
```bash
curl -X POST http://localhost:8002/paperapi/sessions \
  -H "Content-Type: application/json" \
  -d '{"user_id":"debug_user"}'
```
记录返回的 `session_id`，用于后续请求。
```bash
curl -N -X POST http://localhost:8002/paperapi/chat \
  -H "Content-Type: application/json" \
  -d '{"session_id": "<session_id>", "text": "总结稀土改性3D打印材料的研究", "use_public_paper": false}'
```
**实际输出（节选）**:
```
data: {"type": "text", "content": "根据检索到的信息，相关技术可为公司带来以下收益：  \n- 降低劳动力和材料成本  \n- 提高批次一致性  \n- 降低受伤风险  \n- 减少产品和包装浪费  \n- 支持高度定制化产品生产及按需制造，加快生产周期（尤其适用于原型或小批量生产）  \n- 无需额外工具即可构建复杂几何形状，简化生产流程  \n- 优化成本、可靠性、灵活性、产量和速度等制造目标  \n- 改善资源分配，提高劳动力、机械和软件工具的利用率  \n\n引用来源：检索结果中的相关条目（包含收益列表的条目及关于增材制造优势的条目）  \n（注：检索结果未直接提及PaperAgent名称，但上述收益基于与PaperAgent关联的技术领域信息整理）"}
```
