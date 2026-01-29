from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

import requests

logger = logging.getLogger(__name__)


class TitleAgentClient:
    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
        timeout_seconds: float = 20.0,
    ) -> None:
        self.base_url = (
            base_url or os.getenv("LLM_BASE_URL", "https://ark.cn-beijing.volces.com")
        ).rstrip("/")
        self.api_key = api_key or os.getenv("LLM_API_KEY", "")
        self.model = model or os.getenv("LLM_MODEL", "doubao-seed-1-6-lite-251015")

        timeout_env = os.getenv("LLM_TIMEOUT_SECONDS")
        if timeout_env:
            try:
                self.timeout_seconds = float(timeout_env)
            except ValueError:
                self.timeout_seconds = timeout_seconds
        else:
            self.timeout_seconds = timeout_seconds

    def generate(self, conversation: str) -> str:
        if not self.base_url:
            self.base_url = os.getenv("LLM_BASE_URL", "").rstrip("/")
        if not self.api_key:
            self.api_key = os.getenv("LLM_API_KEY", "")
        if not self.model:
            self.model = os.getenv("LLM_MODEL", "")

        if not self.base_url or not self.api_key or not self.model:
            return "新对话"

        system_text = (
            "你是一个标题生成器。请为给定对话生成一个简短的中文标题，严格遵守：\n"
            "1. 不超过10个汉字\n"
            "2. 使用名词或名词短语\n"
            "3. 不包含任何标点符号\n"
            "4. 不出现‘对话’‘聊天’等词\n"
            "只输出标题本身，不要输出解释。"
        )

        max_tokens_raw = os.getenv("TITLE_LLM_MAX_COMPLETION_TOKENS", "256")
        try:
            base_max_tokens = int(max_tokens_raw)
        except ValueError:
            base_max_tokens = 256

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        text: str | None = None
        last_data: Any = None

        for max_tokens in (base_max_tokens, base_max_tokens * 4):
            payload: dict[str, Any] = {
                "model": self.model,
                "max_completion_tokens": max_tokens,
                "messages": [
                    {"role": "system", "content": system_text},
                    {"role": "user", "content": conversation},
                ],
                "reasoning_effort": "minimal",
            }

            resp = requests.post(
                f"{self.base_url}/api/v3/chat/completions",
                json=payload,
                headers=headers,
                timeout=self.timeout_seconds,
            )
            resp.raise_for_status()
            data = resp.json()
            last_data = data

            choices = data.get("choices")
            finish_reason: str | None = None

            if isinstance(choices, list) and choices and isinstance(choices[0], dict):
                choice0 = choices[0]
                finish_reason = choice0.get("finish_reason")
                msg = choice0.get("message")
                if isinstance(msg, dict):
                    content = msg.get("content")
                    if isinstance(content, str):
                        text = content

            if text and text.strip():
                break

            if finish_reason != "length":
                break

        if not text or not text.strip():
            snippet = json.dumps(last_data or {}, ensure_ascii=False)[:1200]
            logger.debug(f"title llm response has no text: {snippet}")
            raise RuntimeError("LLM 响应未包含可解析的文本内容")

        title = text.strip()
        title = re.sub(r"[\s\t\r\n]+", "", title)
        title = re.sub(r"[，。！？、,.!?;:：；" + "“”‘’'\"()（）【】\[\]{}《》<>]", "", title)
        title = title[:10]
        return title or "新对话"
