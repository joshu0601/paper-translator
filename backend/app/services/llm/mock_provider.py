"""Offline LLM stand-in.

It never invents content: it extracts the sentences from the supplied context
that best match the question and returns them with their citation tags, so the
whole RAG → citation → navigation loop can be exercised without API keys.
"""

from __future__ import annotations

import re

from app.services.llm.base import LLMMessage, LLMProvider, LLMResponse
from app.services.text import ZH_EN_HINTS, sentences, tokenize

_CHUNK_RE = re.compile(
    r"\[CHUNK \d+\]\s*(?P<cite>\[Page[^\]]*\])\s*\n(?P<text>.*?)(?=\n\s*\[CHUNK \d+\]|\n\s*\[END OF CONTEXT\]|\Z)", re.S
)
_QUESTION_RE = re.compile(r"(?:^|\n)(?:Question|Task|User question)\s*:\s*(?P<q>.+?)\s*$", re.S)

NOT_FOUND = "目前在這篇論文中找不到足夠資訊回答這個問題。"


class MockLLMProvider(LLMProvider):
    name = "mock"

    def chat(self, messages: list[LLMMessage], *, system=None, max_tokens=2048, temperature=0.2) -> LLMResponse:
        prompt = messages[-1].content if messages else ""
        chunks = [(m.group("cite"), m.group("text").strip()) for m in _CHUNK_RE.finditer(prompt)]
        qm = _QUESTION_RE.search(prompt)
        question = qm.group("q") if qm else prompt[-500:]
        return LLMResponse(text=self.answer(question, chunks), model="mock")

    # ------------------------------------------------------------------ #

    @staticmethod
    def answer(question: str, chunks: list[tuple[str, str]], max_sentences: int = 5) -> str:
        if not chunks:
            return NOT_FOUND

        q_tokens = set(tokenize(question))
        for zh, en in ZH_EN_HINTS.items():
            if zh in question:
                q_tokens.update(tokenize(en))

        scored: list[tuple[float, str, str]] = []
        for rank, (cite, text) in enumerate(chunks):
            for sent in sentences(text):
                toks = set(tokenize(sent))
                if len(toks) < 4:
                    continue
                overlap = len(toks & q_tokens)
                # Earlier chunks come from the retriever ranked higher.
                score = overlap * 10 + max(0, 5 - rank) * 0.5 + min(len(toks), 40) / 40
                scored.append((score, sent, cite))

        if not scored:
            return NOT_FOUND
        scored.sort(key=lambda s: -s[0])
        best = scored[0][0]
        picked = [s for s in scored if s[0] >= max(best * 0.4, 1)][:max_sentences]
        if all(s[0] < 10 for s in picked):
            # No lexical overlap at all: still return the strongest evidence but say so.
            lines = [f"{NOT_FOUND}\n\n以下是與問題最相關的段落（模擬模式，未連接真實 LLM）："]
        else:
            lines = ["根據論文內容（模擬模式：未設定 LLM API 金鑰，以下為原文摘錄）："]
        seen: set[str] = set()
        for _, sent, cite in picked:
            key = sent[:80]
            if key in seen:
                continue
            seen.add(key)
            lines.append(f"- {sent} {cite}")
        lines.append("\n設定 `LLM_PROVIDER=openai` 或 `anthropic` 後即可獲得完整的繁體中文解答。")
        return "\n\n".join(lines[:1]) + "\n" + "\n".join(lines[1:])
