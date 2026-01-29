from __future__ import annotations

import os
import uuid
import json
from typing import Any, AsyncGenerator

import requests
import httpx


class AgentKitClient:
    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout_seconds: float = 60.0,
    ) -> None:
        self.base_url = (base_url or os.getenv("AGENTKIT_BASE_URL", "")).rstrip("/")
        self.api_key = api_key or os.getenv("AGENTKIT_API_KEY", "")

        timeout_env = os.getenv("AGENTKIT_TIMEOUT_SECONDS")
        if timeout_env:
            try:
                self.timeout_seconds = float(timeout_env)
            except ValueError:
                self.timeout_seconds = timeout_seconds
        else:
            self.timeout_seconds = timeout_seconds

    def _extract_text(self, result: Any) -> str | None:
        if not isinstance(result, dict):
            return None

        if result.get("kind") == "message" or ("role" in result and "parts" in result):
            parts = result.get("parts") or []
            if isinstance(parts, list) and parts:
                for part in parts:
                    if not isinstance(part, dict):
                        continue
                    part_type = part.get("type") or part.get("kind")
                    if part_type != "text":
                        continue
                    txt = str(part.get("text") or "").strip()
                    if txt:
                        return txt

        if result.get("kind") == "task" or ("artifacts" in result or "history" in result):
            artifacts = result.get("artifacts")
            if isinstance(artifacts, list) and artifacts:
                parts = (artifacts[0] or {}).get("parts")
                if (
                    isinstance(parts, list)
                    and parts
                    and isinstance(parts[0], dict)
                    and (parts[0].get("type") or parts[0].get("kind")) == "text"
                ):
                    txt = str(parts[0].get("text") or "").strip()
                    return txt or None

            history = result.get("history")
            if isinstance(history, list) and history:
                for msg in reversed(history):
                    if not isinstance(msg, dict):
                        continue
                    if msg.get("kind") != "message":
                        continue
                    role = msg.get("role")
                    if role not in {"agent", "assistant"}:
                        continue
                    parts = msg.get("parts")
                    if (
                        isinstance(parts, list)
                        and parts
                        and isinstance(parts[0], dict)
                        and (parts[0].get("type") or parts[0].get("kind")) == "text"
                    ):
                        txt = str(parts[0].get("text") or "").strip()
                        if txt:
                            return txt

        return None

    async def astream_chat(
        self, session_id: str, text: str, use_public_paper: bool = False
    ) -> AsyncGenerator[dict[str, Any], None]:
        if not self.base_url:
            yield {"type": "error", "content": "AgentKit 未配置：请设置环境变量 AGENTKIT_BASE_URL"}
            return
        if not self.api_key:
            yield {"type": "error", "content": "AgentKit 未配置：请设置环境变量 AGENTKIT_API_KEY"}
            return

        payload: dict[str, Any] = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "message/stream",
            "params": {
                "configuration": {"blocking": False},  # Enable streaming
                "metadata": {
                    "user_id": "default_user",
                    "session_id": session_id,
                    "use_public_paper": use_public_paper,
                },
                "message": {
                    "messageId": str(uuid.uuid4()),
                    "role": "user",
                    "parts": [{"type": "text", "text": text}],
                },
            },
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            try:
                async with client.stream(
                    "POST", f"{self.base_url}/", json=payload, headers=headers
                ) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line:
                            continue
                        if line.startswith("data:"):
                            data_str = line[5:].strip()
                            if not data_str:
                                continue
                            try:
                                raw_data = json.loads(data_str)
                                # 1. Unwrap JSON-RPC result if present
                                event = raw_data.get("result", raw_data)
                                
                                # 2. Handle errors in JSON-RPC
                                if "error" in raw_data:
                                    error_content = raw_data["error"]
                                    if isinstance(error_content, dict):
                                        error_msg = error_content.get("message", str(error_content))
                                    else:
                                        error_msg = str(error_content)
                                    yield {"type": "error", "content": error_msg}
                                    continue

                                kind = event.get("kind")
                                
                                if kind == "message":
                                    parts = event.get("parts") or []
                                    if isinstance(parts, list):
                                        for part in parts:
                                            if not isinstance(part, dict):
                                                continue
                                            part_type = part.get("type") or part.get("kind")
                                            if part_type != "text":
                                                continue
                                            content = part.get("text", "")
                                            if content:
                                                yield {"type": "text", "content": content}
                                            
                                elif kind == "thought":
                                    # Forward thoughts
                                    text = event.get("text", "")
                                    if text:
                                        yield {"type": "thought", "content": text}
                                elif kind == "artifact-update":
                                    artifact = event.get("artifact") or {}
                                    artifact_parts = artifact.get("parts") or []
                                    if isinstance(artifact_parts, list):
                                        for part in artifact_parts:
                                            if not isinstance(part, dict):
                                                continue
                                            part_type = part.get("type") or part.get("kind")
                                            if part_type != "text":
                                                continue
                                            content = part.get("text", "")
                                            if content:
                                                yield {"type": "text", "content": content}
                                elif kind == "status-update":
                                    yield {"type": "thought", "content": json.dumps(event, ensure_ascii=False)}
                                    
                            except json.JSONDecodeError:
                                continue
            except httpx.RequestError as e:
                yield {"type": "error", "content": f"Agent 服务请求失败: {str(e)}"}
            except httpx.HTTPStatusError as e:
                yield {"type": "error", "content": f"Agent 服务响应错误: {e.response.status_code}"}

    def send(self, session_id: str, text: str, use_public_paper: bool = False) -> str:
        if not self.base_url:
            return "AgentKit 未配置：请设置环境变量 AGENTKIT_BASE_URL"
        if not self.api_key:
            return "AgentKit 未配置：请设置环境变量 AGENTKIT_API_KEY"

        payload: dict[str, Any] = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "message/send",
            "params": {
                "configuration": {"blocking": True},
                "metadata": {
                    "user_id": "default_user",
                    "session_id": session_id,
                    "use_public_paper": use_public_paper,
                },
                "message": {
                    "messageId": str(uuid.uuid4()),
                    "role": "user",
                    "parts": [{"type": "text", "text": text}],
                },
            },
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        resp = requests.post(
            f"{self.base_url}/",
            json=payload,
            headers=headers,
            timeout=self.timeout_seconds,
        )
        resp.raise_for_status()
        data = resp.json()

        result = data.get("result")
        extracted = self._extract_text(result)
        if extracted is not None:
            return extracted

        if isinstance(result, dict) and ("artifacts" in result or "history" in result):
            extracted = self._extract_text(result)
            if extracted is not None:
                return extracted

        return str(data)
