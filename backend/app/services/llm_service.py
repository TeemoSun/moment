"""LLM 客户端：调用 OpenAI 兼容接口生成评论。

大模型配置（base_url / api_key / model / timeout / max_tokens）存储在
``system_status`` 表，由管理员后台管理；不再从环境变量读取。
"""

from __future__ import annotations

import os
from dataclasses import dataclass

import httpx


@dataclass(frozen=True)
class LLMConfig:
    base_url: str
    api_key: str
    model: str
    timeout: int
    max_tokens: int


def _load_llm_config() -> LLMConfig:
    """从数据库读取全局 LLM 配置（system_status 单行表，id=1）。"""
    from app.database import SessionLocal
    from app.models.system_status import SystemStatus

    db = SessionLocal()
    try:
        row = db.query(SystemStatus).filter(SystemStatus.id == 1).first()
        if row is None:
            return LLMConfig(
                base_url="https://api.openai.com/v1",
                api_key="",
                model="gpt-4o-mini",
                timeout=30,
                max_tokens=300,
            )
        return LLMConfig(
            base_url=row.llm_base_url,
            api_key=row.llm_api_key,
            model=row.llm_model,
            timeout=row.llm_timeout,
            max_tokens=row.llm_max_tokens,
        )
    finally:
        db.close()


def _mock_response() -> str | None:
    return os.environ.get("LLM_MOCK_RESPONSE")


async def generate_comment(
    persona: str,
    post_content: str,
    author_name: str,
    images_b64: list[str] | None = None,
    model: str | None = None,
    cfg: LLMConfig | None = None,
    author_context: str | None = None,
) -> str:
    mock = _mock_response()
    if mock is not None:
        return mock
    if cfg is None:
        cfg = _load_llm_config()
    if not cfg.api_key:
        raise RuntimeError("LLM API Key 未配置")
    use_model = model or cfg.model
    user_text = (
        f"你是以下人设的角色，用第一人称简短自然地回复朋友圈动态。人设：{persona}\n"
        f"要求：中文，不超过100字，像真人评论，不要markdown不要链接。"
    )
    if author_context:
        user_text += f"\n\n{author_context}"
    user_text += f"\n\n{author_name} 发了一条朋友圈：\n{post_content}"
    content: list[dict] = [{"type": "text", "text": user_text}]
    if images_b64:
        for b64 in images_b64:
            content.append(
                {"type": "image_url", "image_url": {"url": f"data:image/webp;base64,{b64}"}}
            )
    payload = {
        "model": use_model,
        "max_tokens": cfg.max_tokens,
        "messages": [{"role": "user", "content": content}],
    }
    headers = {"Authorization": f"Bearer {cfg.api_key}"}
    url = f"{cfg.base_url.rstrip('/')}/chat/completions"
    async with httpx.AsyncClient(timeout=cfg.timeout) as client:
        resp = await client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()
    return data["choices"][0]["message"]["content"].strip()


async def generate_reply(
    persona: str,
    post_content: str,
    author_name: str,
    reply_to_name: str,
    reply_to_content: str,
    model: str | None = None,
    cfg: LLMConfig | None = None,
    author_context: str | None = None,
    images_b64: list[str] | None = None,
) -> str:
    mock = _mock_response()
    if mock is not None:
        return mock
    if cfg is None:
        cfg = _load_llm_config()
    if not cfg.api_key:
        raise RuntimeError("LLM API Key 未配置")
    use_model = model or cfg.model
    user_text = (
        f"你是以下人设的角色，用第一人称简短自然地回复别人对你评论的回复。人设：{persona}\n"
        f"要求：中文，不超过80字，像真人对话，不要markdown。"
    )
    if author_context:
        user_text += f"\n\n{author_context}"
    user_text += (
        f"\n\n朋友圈原动态({author_name}发)：{post_content}\n\n"
        f"{reply_to_name} 回复了你：{reply_to_content}"
    )
    content: list[dict] = [{"type": "text", "text": user_text}]
    if images_b64:
        for b64 in images_b64:
            content.append(
                {"type": "image_url", "image_url": {"url": f"data:image/webp;base64,{b64}"}}
            )
    payload = {
        "model": use_model,
        "max_tokens": cfg.max_tokens,
        "messages": [{"role": "user", "content": content}],
    }
    headers = {"Authorization": f"Bearer {cfg.api_key}"}
    url = f"{cfg.base_url.rstrip('/')}/chat/completions"
    async with httpx.AsyncClient(timeout=cfg.timeout) as client:
        resp = await client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()
    return data["choices"][0]["message"]["content"].strip()


async def test_llm(cfg: LLMConfig) -> str:
    """用给定配置发送一个最小请求，验证连通性。返回模型回复内容。

    用于后台"测试"按钮。失败时抛出异常（由调用方捕获并转 HTTP 错误）。
    """
    if not cfg.api_key:
        raise RuntimeError("LLM API Key 未配置")
    payload = {
        "model": cfg.model,
        "max_tokens": 16,
        "messages": [{"role": "user", "content": '你是测试助手。请回复"OK"。'}],
    }
    headers = {"Authorization": f"Bearer {cfg.api_key}"}
    url = f"{cfg.base_url.rstrip('/')}/chat/completions"
    async with httpx.AsyncClient(timeout=cfg.timeout) as client:
        resp = await client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()
    return data["choices"][0]["message"]["content"].strip()
