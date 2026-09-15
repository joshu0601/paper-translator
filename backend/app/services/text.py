"""Small text utilities shared by the mock providers, search and chunking."""

from __future__ import annotations

import re

_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9\-]+|\d+(?:\.\d+)?|[一-鿿]{1,2}")
_SENT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z\(\[])")

STOPWORDS = {
    "the", "a", "an", "of", "to", "in", "and", "or", "is", "are", "was", "were", "be", "for", "on",
    "with", "as", "by", "that", "this", "it", "we", "our", "at", "from", "which", "these", "those",
    "can", "into", "than", "then", "such", "also", "its", "their", "has", "have", "been", "not",
    "where", "when", "each", "both", "using", "used", "use", "based", "via", "i.e", "e.g", "paper",
    "what", "how", "does", "do", "did", "why", "which", "who", "please", "explain", "describe",
}

# Minimal bilingual hints so Traditional Chinese questions still retrieve the
# English evidence when no real embedding model is configured.
ZH_EN_HINTS: dict[str, str] = {
    "問題": "problem challenge",
    "解決": "solve address propose",
    "貢獻": "contribution contributions propose novel",
    "方法": "method methodology approach algorithm",
    "系統": "system architecture",
    "模型": "model formulation",
    "實驗": "experiment experimental setup simulation",
    "設定": "setup settings parameters",
    "結果": "results performance achieves outperforms improvement",
    "證明": "results demonstrate show",
    "限制": "limitation limitations future work",
    "未來": "future work",
    "獎勵": "reward",
    "狀態": "state",
    "動作": "action",
    "資料集": "dataset data",
    "基準": "baseline baselines compared",
    "摘要": "abstract summary propose",
    "結論": "conclusion conclude",
    "演算法": "algorithm",
    "強化學習": "reinforcement learning",
    "延遲": "latency delay",
    "能源": "energy consumption",
    "卸載": "offloading",
    "邊緣": "edge",
    "目標": "objective goal minimize maximize",
    "定義": "define defined formulate",
    "簡報": "abstract introduction contribution method results conclusion",
}


def tokenize(text: str) -> list[str]:
    return [t.lower() for t in _TOKEN_RE.findall(text) if t.lower() not in STOPWORDS and len(t) > 1]


def sentences(text: str) -> list[str]:
    parts = _SENT_RE.split(text.strip())
    return [p.strip() for p in parts if len(p.strip()) > 20]


def sha256(text: str) -> str:
    import hashlib

    return hashlib.sha256(text.encode("utf-8")).hexdigest()
