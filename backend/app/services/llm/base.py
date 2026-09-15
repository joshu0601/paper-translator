from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class LLMMessage:
    role: str  # "user" | "assistant"
    content: str


@dataclass
class LLMResponse:
    text: str
    model: str
    usage: dict = field(default_factory=dict)


class LLMProvider(ABC):
    """Provider abstraction (SPEC §57)."""

    name: str = "base"

    @abstractmethod
    def chat(
        self,
        messages: list[LLMMessage],
        *,
        system: str | None = None,
        max_tokens: int = 2048,
        temperature: float = 0.2,
    ) -> LLMResponse: ...

    def complete(self, prompt: str, *, system: str | None = None, max_tokens: int = 2048,
                 temperature: float = 0.2) -> str:
        return self.chat([LLMMessage("user", prompt)], system=system, max_tokens=max_tokens,
                         temperature=temperature).text
