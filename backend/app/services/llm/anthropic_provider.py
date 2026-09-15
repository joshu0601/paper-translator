from __future__ import annotations

from app.services.llm.base import LLMProvider, LLMResponse


class AnthropicProvider(LLMProvider):
    name = "anthropic"

    def __init__(self, api_key: str | None, model: str = "claude-opus-5"):
        import anthropic

        # api_key=None lets the SDK resolve ANTHROPIC_API_KEY / `ant auth login`.
        self.client = anthropic.Anthropic(api_key=api_key) if api_key else anthropic.Anthropic()
        self.model = model

    def chat(self, messages, *, system=None, max_tokens=2048, temperature=0.2) -> LLMResponse:
        # Claude 4.6+ models reject sampling parameters; temperature is ignored.
        res = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system or "",
            messages=[{"role": m.role, "content": m.content} for m in messages],
        )
        if res.stop_reason == "refusal":
            text = "目前無法回答這個問題。"
        else:
            text = "".join(block.text for block in res.content if block.type == "text")
        usage = res.usage.model_dump() if res.usage else {}
        return LLMResponse(text=text, model=res.model, usage=usage)
