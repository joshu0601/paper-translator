"""Translation provider abstraction (SPEC §16–18, §59, §72)."""

from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from functools import lru_cache

from app.config import get_settings
from app.services.llm import LLMProvider, build_llm

TRANSLATION_SYSTEM_PROMPT = """You are an expert academic translator.

Translate the provided English academic paper paragraph into Traditional Chinese.

Requirements:

1. Preserve the original technical meaning.
2. Use formal academic Traditional Chinese.
3. Do not unnecessarily rewrite the author's argument.
4. Keep technical terminology consistent.
5. Preserve citations.
6. Preserve equations.
7. Preserve variable names.
8. Preserve model names.
9. Preserve dataset names.
10. Preserve abbreviations.

For important terminology, the first appearance may use:

English Term（中文翻譯）

Example:

Markov Decision Process（馬可夫決策過程）

Later occurrences may use the Chinese translation or abbreviation where appropriate.

Do not translate equations, mathematical symbols, variable names, model names,
algorithm names, dataset names, citations such as [12], URLs, DOIs or code.

Return only the translated paragraph."""

# Seed glossary (SPEC §18). Per-document terms extracted from the paper extend it.
DEFAULT_TERMINOLOGY: dict[str, str] = {
    "Mobile Edge Computing": "行動邊緣運算",
    "Multi-access Edge Computing": "多接取邊緣運算",
    "Edge Computing": "邊緣運算",
    "Reinforcement Learning": "強化學習",
    "Deep Reinforcement Learning": "深度強化學習",
    "Multi-Agent Reinforcement Learning": "多代理強化學習",
    "Markov Decision Process": "馬可夫決策過程",
    "Deep Q-Network": "深度 Q 網路",
    "Neural Network": "神經網路",
    "Convolutional Neural Network": "卷積神經網路",
    "Graph Neural Network": "圖神經網路",
    "Transformer": "Transformer",
    "Attention": "注意力機制",
    "Computation Offloading": "計算卸載",
    "Task Offloading": "任務卸載",
    "Resource Allocation": "資源配置",
    "Latency": "延遲",
    "Energy Consumption": "能源消耗",
    "Reward Function": "獎勵函數",
    "State Space": "狀態空間",
    "Action Space": "動作空間",
    "Policy": "策略",
    "Baseline": "基準方法",
    "Ablation Study": "消融實驗",
    "Loss Function": "損失函數",
    "Gradient Descent": "梯度下降",
    "Large Language Model": "大型語言模型",
    "Retrieval-Augmented Generation": "檢索增強生成",
    "Federated Learning": "聯邦學習",
    "Internet of Things": "物聯網",
    "Quality of Service": "服務品質",
    "Optimization": "最佳化",
    "Simulation": "模擬",
    "Throughput": "吞吐量",
    "Bandwidth": "頻寬",
}

_TERM_WITH_ACRONYM = re.compile(r"((?:[A-Za-z][A-Za-z\-]*\s+){1,6})\(([A-Z][A-Za-z]{1,7}?)s?\)")
_STOP = {"of", "and", "the", "in", "for", "on", "to", "a", "an", "with", "by"}


def _term_for_acronym(words: list[str], acronym: str) -> str | None:
    """Pick the trailing words whose initials spell the acronym:
    'the problem in multi-access edge computing (MEC)' → 'multi-access edge computing'."""
    target = acronym.upper()
    chosen: list[str] = []
    variants = {""}
    for w in reversed(words):
        chosen.insert(0, w)
        if w.lower() in _STOP:
            continue
        parts = [p for p in w.split("-") if p]
        heads = {w[0].upper(), "".join(p[0].upper() for p in parts)}
        variants = {h + v for v in variants for h in heads}
        if target in variants:
            return " ".join(chosen)
        if all(len(v) >= len(target) for v in variants):
            return None
    return None


class TranslationProvider(ABC):
    name: str = "base"

    @abstractmethod
    def translate_batch(self, paragraphs: list[str], terminology: dict[str, str]) -> list[str]: ...

    def build_terminology(self, sample_text: str, candidates: list[str]) -> dict[str, str]:
        """Return translations for candidate terms found in the paper."""
        return {}


def extract_term_candidates(text: str, limit: int = 40) -> list[str]:
    """Terms introduced as `Long Form (ACRONYM)` are the paper's key vocabulary."""
    found: list[str] = []
    seen_lower: set[str] = set()
    for m in _TERM_WITH_ACRONYM.finditer(text):
        term = _term_for_acronym(m.group(1).split(), m.group(2))
        if not term or len(term) >= 60 or term.lower() in seen_lower:
            continue
        seen_lower.add(term.lower())
        found.append(term)
        if len(found) >= limit:
            break
    return found


class LLMTranslationProvider(TranslationProvider):
    """Translates with any LLMProvider (OpenAI, Anthropic...)."""

    def __init__(self, llm: LLMProvider):
        self.llm = llm
        self.name = llm.name

    def translate_batch(self, paragraphs: list[str], terminology: dict[str, str]) -> list[str]:
        if not paragraphs:
            return []
        glossary = "\n".join(f"- {k} → {v}" for k, v in list(terminology.items())[:80])
        numbered = "\n\n".join(f"<p id=\"{i}\">\n{p}\n</p>" for i, p in enumerate(paragraphs))
        prompt = (
            "Terminology to use consistently:\n"
            f"{glossary or '- (none)'}\n\n"
            "Translate each <p> block below. Return ONLY a JSON object mapping the id "
            "to the Traditional Chinese translation, e.g. {\"0\": \"...\", \"1\": \"...\"}.\n\n"
            f"{numbered}"
        )
        text = self.llm.complete(prompt, system=TRANSLATION_SYSTEM_PROMPT, max_tokens=8000, temperature=0.1)
        data = _parse_json_object(text)
        out: list[str] = []
        for i, original in enumerate(paragraphs):
            value = data.get(str(i)) if isinstance(data, dict) else None
            if not isinstance(value, str) or not value.strip():
                # Fall back to a single-paragraph call so one bad batch does not
                # leave holes in the reader.
                value = self.llm.complete(original, system=TRANSLATION_SYSTEM_PROMPT, max_tokens=4000, temperature=0.1)
            out.append(value.strip())
        return out

    def build_terminology(self, sample_text: str, candidates: list[str]) -> dict[str, str]:
        if not candidates:
            return {}
        prompt = (
            "Provide the standard Traditional Chinese (Taiwan) translation for each academic term. "
            "Return ONLY a JSON object mapping the English term to the Chinese translation.\n\n"
            + "\n".join(f"- {c}" for c in candidates)
        )
        data = _parse_json_object(self.llm.complete(prompt, max_tokens=2000, temperature=0))
        return {k: v for k, v in data.items() if isinstance(k, str) and isinstance(v, str)} if isinstance(data, dict) else {}


class MockTranslationProvider(TranslationProvider):
    """Offline stand-in: substitutes glossary terms and marks the text as untranslated."""

    name = "mock"

    def translate_batch(self, paragraphs: list[str], terminology: dict[str, str]) -> list[str]:
        out = []
        terms = sorted(terminology.items(), key=lambda kv: -len(kv[0]))
        for p in paragraphs:
            text = p
            for en, zh in terms:
                text = re.sub(rf"\b{re.escape(en)}\b", lambda m, zh=zh: f"{m.group(0)}（{zh}）", text, count=1, flags=re.I)
            out.append(f"〔模擬翻譯〕{text}")
        return out


def _parse_json_object(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.S)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", text, re.S)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                return {}
    return {}


def build_translator(kind: str | None = None) -> TranslationProvider:
    s = get_settings()
    kind = kind or s.translation_provider
    if kind in {"openai", "anthropic"}:
        llm = build_llm(kind, purpose="translation")
        if kind == "openai" and s.openai_translation_model != s.openai_chat_model:
            from app.services.llm.openai_provider import OpenAIProvider

            llm = OpenAIProvider(s.openai_api_key or "", s.openai_translation_model, s.openai_base_url)
        return LLMTranslationProvider(llm)
    return MockTranslationProvider()


@lru_cache
def get_translator() -> TranslationProvider:
    return build_translator()
