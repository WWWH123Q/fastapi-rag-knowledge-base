from __future__ import annotations

from typing import Any, Dict, List

from sentence_transformers import CrossEncoder

from app.config import settings


class RerankService:
    def __init__(self, model_name: str | None = None):
        self.model_name = model_name or settings.rerank_model_name
        self.model = CrossEncoder(self.model_name)

    def rerank(
        self,
        query: str,
        contexts: List[Dict[str, Any]],
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        if not contexts:
            return []

        pairs = [[query, item.get("text", "")] for item in contexts]
        scores = self.model.predict(pairs)

        reranked_contexts = []
        for index, (item, score) in enumerate(zip(contexts, scores), start=1):
            new_item = dict(item)
            new_item["retrieval_rank"] = item.get("rank", index)
            new_item["rerank_score"] = float(score)
            reranked_contexts.append(new_item)

        reranked_contexts.sort(
            key=lambda x: x.get("rerank_score", 0),
            reverse=True,
        )

        final_contexts = reranked_contexts[:top_k]
        for new_rank, item in enumerate(final_contexts, start=1):
            item["rank"] = new_rank

        return final_contexts
