# Changelog（新功能与接口变更）

变更日期：2026-02-01

## Sessions

- 新增：PATCH /paperapi/sessions/{session_id}/title（会话重命名）
- 新增：DELETE /paperapi/sessions/{session_id}（会话删除；默认归档，status=archived）
- 增强：DELETE /paperapi/sessions/{session_id}?hard=true（硬删除；永久删除会话并清理该会话消息）

## Chat

- 增强：POST /paperapi/chat 增加会话校验（必须存在且为 active）
  - 404：session not found
  - 409：session is not active
