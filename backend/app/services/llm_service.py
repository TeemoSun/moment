"""LLM 客户端：调用 OpenAI 兼容接口生成评论。"""

from __future__ import annotations

import os

import httpx

from app.config import settings


async def generate_comment(
    persona: str,
    post_content: str,
    author_name: str,
    images_b64: list[str] | None = None,
    model: str | None = None,
) -> str:
    if os.environ.get("LLM_MOCK_RESPONSE"):
        return os.environ["LLM_MOCK_RESPONSE"]
    if not settings.LLM_API_KEY:
        raise RuntimeError("LLM_API_KEY 未配置")
    use_model = model or settings.LLM_MODEL
    system_msg = (
        f"你是以下人设的角色，用第一人称简短自然地回复朋友圈动态。人设：{persona}\n"
        f"要求：中文，不超过100字，像真人评论，不要markdown不要链接。"
    )
    user_text = f"{author_name} 发了一条朋友圈：\n{post_content}"
    content: list[dict] = [{"type": "text", "text": user_text}]
    if images_b64:
        for b64 in images_b64:
            content.append(
                {"type": "image_url", "image_url": {"url": f"data:image/webp;base64,{b64}"}}
            )
    payload = {
        "model": use_model,
        "max_tokens": settings.LLM_MAX_TOKENS,
        "messages": [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": content},
        ],
    }
    headers = {"Authorization": f"Bearer {settings.LLM_API_KEY}"}
    url = f"{settings.LLM_BASE_URL.rstrip('/')}/chat/completions"
    async with httpx.AsyncClient(timeout=settings.LLM_TIMEOUT) as client:
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
) -> str:
    if os.environ.get("LLM_MOCK_RESPONSE"):
        return os.environ["LLM_MOCK_RESPONSE"]
    if not settings.LLM_API_KEY:
        raise RuntimeError("LLM_API_KEY 未配置")
    use_model = model or settings.LLM_MODEL
    system_msg = (
        f"你是以下人设的角色，用第一人称简短自然地回复别人对你评论的回复。人设：{persona}\n"
        f"要求：中文，不超过80字，像真人对话，不要markdown。"
    )
    user_text = (
        f"朋友圈原动态({author_name}发)：{post_content}\n\n"
        f"{reply_to_name} 回复了你：{reply_to_content}"
    )
    payload = {
        "model": use_model,
        "max_tokens": settings.LLM_MAX_TOKENS,
        "messages": [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_text},
        ],
    }
    headers = {"Authorization": f"Bearer {settings.LLM_API_KEY}"}
    url = f"{settings.LLM_BASE_URL.rstrip('/')}/chat/completions"
    async with httpx.AsyncClient(timeout=settings.LLM_TIMEOUT) as client:
        resp = await client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()
    return data["choices"][0]["message"]["content"].strip()
