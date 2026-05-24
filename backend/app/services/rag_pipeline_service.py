from __future__ import annotations

import re

from app.config import settings
from app.services.knowledge_base_service import KnowledgeBaseService
from app.services.llm_service import LLMService
from app.services.rag_utils import format_contexts_for_prompt, local_contexts_to_sources
from app.services.rerank_service import RerankService
from app.services.web_search_service import WebSearchService


class RAGPipelineService:
    def __init__(
        self,
        knowledge_base_service: KnowledgeBaseService,
        llm_service: LLMService,
        web_search_service: WebSearchService,
    ):
        self.knowledge_base_service = knowledge_base_service
        self.llm_service = llm_service
        self.web_search_service = web_search_service
        self.rerank_service = RerankService()

    def expand_query(self, query: str) -> list[str]:
        queries = [query.strip()]

        tokens = re.findall(
            r"[A-Za-z0-9_.+-]+|(?:19|20)\d{2}|[\u4e00-\u9fff]{2,}",
            query,
        )
        keyword_query = " ".join(dict.fromkeys(tokens))
        if keyword_query and keyword_query not in queries:
            queries.append(keyword_query)

        important_terms = []
        important_patterns = (
            r"[\u4e00-\u9fff]{2,}(?:\u5956|\u676f|\u7ade\u8d5b|\u8bba\u6587|\u9879\u76ee|\u6210\u679c|\u670d\u52a1\u5668|GPU|Agent|RAG)",
            r"(?:19|20)\d{2}",
        )
        for pattern in important_patterns:
            important_terms.extend(re.findall(pattern, query))

        important_query = " ".join(dict.fromkeys(important_terms))
        if important_query and important_query not in queries:
            queries.append(important_query)

        return queries[:3]

    def _candidate_k(self, top_k: int) -> int:
        return max(
            top_k * settings.vector_candidate_multiplier,
            settings.vector_candidate_min,
        )

    def _get_best_rerank_score(self, contexts: list[dict]) -> float:
        scores = [
            float(item["rerank_score"])
            for item in contexts
            if item.get("rerank_score") is not None
        ]
        return max(scores) if scores else 0.0

    def _build_debug_fields(
        self,
        retrieved_count: int,
        contexts: list[dict],
        rejected: bool,
    ) -> dict:
        return {
            "best_rerank_score": self._get_best_rerank_score(contexts),
            "min_rerank_threshold": settings.rerank_threshold,
            "retrieved_count": retrieved_count,
            "reranked_count": len(contexts),
            "rejected_by_low_confidence": rejected,
        }

    def _should_refuse_by_confidence(self, contexts: list[dict]) -> bool:
        if not contexts:
            return True

        return self._get_best_rerank_score(contexts) < settings.rerank_threshold

    def ask_local(
        self,
        query: str,
        top_k: int = 5,
        metadata_filter: dict | None = None,
    ):
        expanded_queries = self.expand_query(query)
        candidate_contexts = self.knowledge_base_service.hybrid_search(
            queries=expanded_queries,
            candidate_k=self._candidate_k(top_k),
            bm25_top_k=settings.bm25_top_k,
            metadata_filter=metadata_filter,
        )
        retrieved_count = len(candidate_contexts) #这行代码记录这次一共召回了多少条候选资料。

        if not candidate_contexts: #如果没有检索到资料，直接拒答
            return {
                "query": query,
                "answer": "根据当前资料无法确定",
                "top_k": top_k,
                "contexts": [],
                **self._build_debug_fields(0, [], True),
            }

        contexts = self.rerank_service.rerank( #重排
            query=query,
            contexts=candidate_contexts,
            top_k=top_k,
        )

        rejected = self._should_refuse_by_confidence(contexts)#置信度回答
        if rejected: #置信度不够
            return {
                "query": query,
                "answer": "根据当前资料无法确定",
                "top_k": top_k,
                "contexts": contexts,
                **self._build_debug_fields(retrieved_count, contexts, True),
            }

        context_text = format_contexts_for_prompt(contexts) #把 contexts 格式化成 prompt
        answer = self.llm_service.generate_answer( #调用大模型
            query=query,
            context_text=context_text,
        )

        return {
            "query": query,
            "answer": answer,
            "top_k": top_k,
            "contexts": contexts,
            **self._build_debug_fields(retrieved_count, contexts, False),
        }

    def ask_web(
        self,
        query: str,
        top_k: int = 5,
        provider: str | None = None,
    ) -> dict:
        provider = provider or settings.web_search_provider

        sources = self.web_search_service.search(
            query=query,
            max_results=top_k,
            provider=provider,
        )

        answer = self.llm_service.generate_answer_from_sources(
            question=query,
            sources=sources,
            mode="web",
        )

        return {
            "query": query,
            "answer": answer,
            "provider": provider,
            "sources": sources,
        }

    def ask_hybrid(
        self,
        query: str,
        local_top_k: int = 5,
        web_top_k: int = 5,
        provider: str | None = None,
        metadata_filter: dict | None = None,
    ) -> dict:
        provider = provider or settings.web_search_provider
        expanded_queries = self.expand_query(query)

        candidate_contexts = self.knowledge_base_service.hybrid_search(
            queries=expanded_queries,
            candidate_k=self._candidate_k(local_top_k),
            bm25_top_k=settings.bm25_top_k,
            metadata_filter=metadata_filter,
        )
        retrieved_count = len(candidate_contexts)

        local_contexts = self.rerank_service.rerank(
            query=query,
            contexts=candidate_contexts,
            top_k=local_top_k,
        )

        rejected = self._should_refuse_by_confidence(local_contexts)
        if rejected:
            local_sources = []
        else:
            local_sources = local_contexts_to_sources(local_contexts)

        web_sources = self.web_search_service.search(
            query=query,
            max_results=web_top_k,
            provider=provider,
        )

        sources = local_sources + web_sources
        for index, item in enumerate(sources):
            item["rank"] = index + 1

        answer = self.llm_service.generate_answer_from_sources(
            question=query,
            sources=sources,
            mode="hybrid",
        )

        return {
            "query": query,
            "answer": answer,
            "local_top_k": local_top_k,
            "web_top_k": web_top_k,
            "provider": provider,
            "sources": sources,
            **self._build_debug_fields(retrieved_count, local_contexts, rejected),
        }

    def web_search_only(
        self,
        query: str,
        top_k: int = 5,
        provider: str | None = None,
    ) -> dict:
        provider = provider or settings.web_search_provider

        sources = self.web_search_service.search(
            query=query,
            max_results=top_k,
            provider=provider,
        )

        return {
            "query": query,
            "provider": provider,
            "top_k": top_k,
            "sources": sources,
        }
