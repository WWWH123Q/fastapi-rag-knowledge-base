from __future__ import annotations

import re
from typing import Any

try:
    import jieba
except ImportError:  # pragma: no cover - fallback for incomplete local envs
    jieba = None

try:
    from rank_bm25 import BM25Okapi
except ImportError:  # pragma: no cover - fallback for incomplete local envs
    BM25Okapi = None


class BM25Service:
    def __init__(self):
        self.documents: list[dict[str, Any]] = []
        self.tokenized_documents: list[list[str]] = []
        self.index: BM25Okapi | None = None

    def tokenize(self, text: str) -> list[str]:
        if not text:
            return []

        if jieba is not None:
            chinese_tokens = [token.strip() for token in jieba.lcut(text) if token.strip()]
        else:
            chinese_tokens = re.findall(r"[\u4e00-\u9fff]{1,}", text)

        ascii_tokens = re.findall(r"[A-Za-z0-9_.+-]+", text.lower())
        return chinese_tokens + ascii_tokens

    def build_index(self, documents: list[dict]):
        self.documents = documents
        self.tokenized_documents = [
            self.tokenize(item.get("text", ""))
            for item in documents
        ]
        if BM25Okapi is None or not self.documents:
            self.index = None
        else:
            self.index = BM25Okapi(self.tokenized_documents)

    def search(self, query: str, top_k: int) -> list[dict]:
        if not self.index or not self.documents:
            return []

        query_tokens = self.tokenize(query)
        if not query_tokens:
            return []

        scores = self.index.get_scores(query_tokens)
        ranked_indexes = sorted(
            range(len(scores)),
            key=lambda index: scores[index],
            reverse=True,
        )[:top_k]

        results = []
        for rank, index in enumerate(ranked_indexes, start=1):
            score = float(scores[index])
            if score <= 0:
                continue

            item = dict(self.documents[index])
            item["rank"] = rank
            item["score"] = score
            item["bm25_score"] = score
            item["retrieval_source"] = "bm25"
            results.append(item)

        return results
