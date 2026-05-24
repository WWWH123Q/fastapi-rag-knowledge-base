import json
import csv
import requests
from pathlib import Path
from typing import Any, Dict, List, Optional


BASE_URL = "http://127.0.0.1:8001"
SEARCH_URL = f"{BASE_URL}/rag/search"

EVAL_FILE = Path(__file__).parent / "eval_questions.jsonl"
OUTPUT_FILE = Path(__file__).parent / "retrieval_eval_result.csv"


def load_eval_questions(file_path: Path) -> List[Dict[str, Any]]:
    questions = []

    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            questions.append(json.loads(line))

    return questions


def call_search_api(question: str, top_k: int = 5) -> List[Dict[str, Any]]:
    payload = {
        "query": question,
        "top_k": top_k,
    }

    response = requests.post(SEARCH_URL, json=payload, timeout=60)
    response.raise_for_status()

    data = response.json()

    # 兼容不同返回格式
    if isinstance(data, list):
        return data

    if isinstance(data, dict):
        if "results" in data:
            return data["results"]
        if "contexts" in data:
            return data["contexts"]
        if "data" in data:
            return data["data"]

    return []


def get_result_text(result: Dict[str, Any]) -> str:
    parts = []

    for key in ["text", "content", "chunk", "filename", "source", "file_name"]:
        value = result.get(key)
        if value:
            parts.append(str(value))

    return " ".join(parts)


def is_hit(result: Dict[str, Any], expected_source: str, expected_keywords: List[str]) -> bool:
    result_text = get_result_text(result)

    source_hit = expected_source and expected_source in result_text
    keyword_hit = any(keyword in result_text for keyword in expected_keywords)

    return source_hit or keyword_hit


def evaluate_one_question(item: Dict[str, Any], top_k: int = 5) -> Dict[str, Any]:
    question = item["question"]
    expected_source = item.get("expected_source", "")
    expected_keywords = item.get("expected_keywords", [])

    results = call_search_api(question, top_k=top_k)

    hit_rank: Optional[int] = None

    for index, result in enumerate(results, start=1):
        if is_hit(result, expected_source, expected_keywords):
            hit_rank = index
            break

    hit_at_k = 1 if hit_rank is not None else 0
    mrr = 1 / hit_rank if hit_rank is not None else 0

    top1_text = get_result_text(results[0])[:120] if results else ""

    return {
        "question": question,
        "expected_source": expected_source,
        "hit_at_k": hit_at_k,
        "hit_rank": hit_rank if hit_rank is not None else "",
        "mrr": round(mrr, 4),
        "top1_preview": top1_text,
    }


def main():
    top_k = 5
    eval_questions = load_eval_questions(EVAL_FILE)

    if not eval_questions:
        print("没有读取到评估问题，请检查 eval_questions.jsonl")
        return

    rows = []

    for item in eval_questions:
        print(f"正在评估：{item['question']}")
        row = evaluate_one_question(item, top_k=top_k)
        rows.append(row)

    total = len(rows)
    hit_count = sum(row["hit_at_k"] for row in rows)
    avg_hit_at_k = hit_count / total if total else 0
    avg_mrr = sum(row["mrr"] for row in rows) / total if total else 0

    print("\n========== 检索评估结果 ==========")
    print(f"问题总数: {total}")
    print(f"Hit@{top_k}: {avg_hit_at_k:.4f}")
    print(f"MRR: {avg_mrr:.4f}")

    with open(OUTPUT_FILE, "w", encoding="utf-8-sig", newline="") as f:
        fieldnames = [
            "question",
            "expected_source",
            "hit_at_k",
            "hit_rank",
            "mrr",
            "top1_preview",
        ]

        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\n详细结果已保存到：{OUTPUT_FILE}")


if __name__ == "__main__":
    main()