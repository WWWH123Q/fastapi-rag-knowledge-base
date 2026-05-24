from __future__ import annotations

def parse_milvus_results(raw_results, retrieval_source: str = "vector") -> list[dict]:
    results = []
    rank = 1

    for hits in raw_results:
        for hit in hits:
            entity = hit.get("entity", {})

            results.append({
                "rank": rank,
                "text": entity.get("text", ""),
                "filename": entity.get("filename", ""),
                "file_hash": entity.get("file_hash", ""),
                "file_ext": entity.get("file_ext", ""),
                "uploaded_at": entity.get("uploaded_at", ""),
                "chunk_hash": entity.get("chunk_hash", ""),
                "score": hit.get("distance", 0),
                "vector_score": hit.get("distance", 0),
                "retrieval_source": retrieval_source,
            })

            rank += 1

    return results


def merge_contexts_by_chunk_hash(context_groups: list[list[dict]]) -> list[dict]:
    merged: dict[str, dict] = {}

    for contexts in context_groups:
        for item in contexts:
            key = item.get("chunk_hash") or f"{item.get('filename', '')}:{item.get('text', '')}"
            source = item.get("retrieval_source", "")

            if key not in merged:
                merged[key] = dict(item)
                if source:
                    merged[key]["retrieval_sources"] = [source]
                continue

            existing = merged[key]
            if source and source not in existing.setdefault("retrieval_sources", []):
                existing["retrieval_sources"].append(source)

            if existing.get("retrieval_source") != source:
                existing["retrieval_source"] = "hybrid"

            for score_field in ("vector_score", "bm25_score", "score"):
                if score_field in item and item.get(score_field) is not None:
                    existing.setdefault(score_field, item.get(score_field))

    results = list(merged.values())
    for rank, item in enumerate(results, start=1):
        item["rank"] = rank

    return results


def local_contexts_to_sources(contexts: list[dict]) -> list[dict]:
    sources = []

    for item in contexts:
        sources.append({
            "rank": item.get("rank", 0),
            "source_type": "local",
            "provider": "milvus",
            "title": item.get("filename", ""),
            "url": "",
            "filename": item.get("filename", ""),
            "text": item.get("text", ""),
            "file_hash": item.get("file_hash", ""),
            "file_ext": item.get("file_ext", ""),
            "uploaded_at": item.get("uploaded_at", ""),
            "chunk_hash": item.get("chunk_hash", ""),
            "score": item.get("score"),
            "retrieval_rank": item.get("retrieval_rank"),
            "rerank_score": item.get("rerank_score"),
            "retrieval_source": item.get("retrieval_source", "local"),
        })

    return sources


def format_contexts_for_prompt(contexts: list[dict]) -> str:
    if not contexts:
        return "No relevant reference material was retrieved."

    parts = []
    for item in contexts:
        rank = item.get("rank", "")
        filename = item.get("filename", "")
        text = item.get("text", "")

        parts.append(
            f"[资料{rank}]\n"
            f"source_type: local\n"
            f"filename: {filename}\n"
            f"text:\n{text}"
        )

    return "\n\n".join(parts)
