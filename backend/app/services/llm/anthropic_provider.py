from __future__ import annotations

import os

from app.services.llm.base import LLMProvider, LLMResponse


class AnthropicProvider(LLMProvider):
    name = "anthropic"

    def __init__(self, api_key: str | None, model: str = "claude-opus-5", effort: str | None = None):
        import anthropic

        # api_key=None lets the SDK resolve ANTHROPIC_API_KEY / `ant auth login`.
        if not api_key and not os.environ.get("ANTHROPIC_API_KEY") and not os.environ.get("ANTHROPIC_AUTH_TOKEN"):
            raise RuntimeError(
                "ANTHROPIC_API_KEY is not set. Add it to backend/.env (or run `ant auth login`) "
                "before selecting the anthropic provider."
            )
        self.client = anthropic.Anthropic(api_key=api_key) if api_key else anthropic.Anthropic()
        self.model = model
        self.effort = effort

    def chat(self, messages, *, system=None, max_tokens=2048, temperature=0.2) -> LLMResponse:
        # Claude 4.6+ models reject sampling parameters, so `temperature` is ignored;
        # adaptive thinking is on by default. Streaming avoids HTTP timeouts on
        # long outputs (translation batches) - the final message is collected.
        kwargs: dict = {}
        if self.effort:
            kwargs["output_config"] = {"effort": self.effort}
        with self.client.messages.stream(
            model=self.model,
            max_tokens=max_tokens,
            system=system or "",
            messages=[{"role": m.role, "content": m.content} for m in messages],
            **kwargs,
        ) as stream:
            res = stream.get_final_message()
        if res.stop_reason == "refusal":
            text = "目前無法回答這個問題。"
        else:
            text = "".join(block.text for block in res.content if block.type == "text")
        usage = res.usage.model_dump() if res.usage else {}
        return LLMResponse(text=text, model=res.model, usage=usage)
