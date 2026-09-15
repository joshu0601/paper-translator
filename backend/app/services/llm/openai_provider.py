from __future__ import annotations

from app.services.llm.base import LLMMessage, LLMProvider, LLMResponse


class OpenAIProvider(LLMProvider):
    name = "openai"

    def __init__(self, api_key: str, model: str, base_url: str | None = None):
        from openai import OpenAI

        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model

    def chat(self, messages, *, system=None, max_tokens=2048, temperature=0.2) -> LLMResponse:
        payload: list[dict] = []
        if system:
            payload.append({"role": "system", "content": system})
        payload.extend({"role": m.role, "content": m.content} for m in messages)
        res = self.client.chat.completions.create(
            model=self.model,
            messages=payload,
            max_completion_tokens=max_tokens,
            temperature=temperature,
        )
        choice = res.choices[0]
        usage = res.usage.model_dump() if res.usage else {}
        return LLMResponse(text=choice.message.content or "", model=res.model, usage=usage)


__all__ = ["OpenAIProvider", "LLMMessage"]
