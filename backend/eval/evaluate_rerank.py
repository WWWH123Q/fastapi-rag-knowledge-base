import json
import csv
import requests
from pathlib import Path
from typing import Any, Dict, List, Optional


BASE_URL = "http://127.0.0.1:8001"

SEARCH_URL = f"{BASE_URL}/rag/search"
ASK_URL = f"{BASE_URL}/rag/ask"

EVAL_FILE = Path(__file__).parent / "eval_questions.jsonl"

# 详细版 CSV：保留所有字段，适合排查细节
OUTPUT_FILE = Path(__file__).parent / "rerank_eval_result.csv"

# 精简版 CSV：只保留关键字段，适合快速查看
READABLE_CSV_FILE = Path(__file__).parent / "rerank_eval_readable.csv"

# Markdown 报告：最适合人看
REPORT_FILE = Path(__file__).parent / "rerank_eval_report.md"

FINAL_TOP_K = 5
RAW_CANDIDATE_K = 20


def load_eval_questions(file_path: Path) -> List[Dict[str, Any]]:
    items = []

    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            items.append(json.loads(line))

    return items


def call_search_api(question: str, top_k: int = 20) -> List[Dict[str, Any]]:
    payload = {
        "query": question,
        "top_k": top_k,
    }

    response = requests.post(SEARCH_URL, json=payload, timeout=120)
    response.raise_for_status()

    data = response.json()
    return data.get("results", [])


def call_ask_api(question: str, top_k: int = 5) -> Dict[str, Any]:
    payload = {
        "query": question,
        "top_k": top_k,
    }

    response = requests.post(ASK_URL, json=payload, timeout=180)
    response.raise_for_status()

    return response.json()


def result_to_text(result: Dict[str, Any]) -> str:
    parts = []

    for key in [
        "text",
        "filename",
        "file_hash",
        "chunk_hash",
        "file_ext",
        "uploaded_at",
    ]:
        value = result.get(key)
        if value:
            parts.append(str(value))

    return " ".join(parts)


def get_expected_sources(item: Dict[str, Any]) -> List[str]:
    """
    兼容两种写法：
    expected_source: "竞赛获奖记录"
    expected_sources: ["竞赛获奖记录", "学生论文成果汇总"]
    """

    if "expected_sources" in item:
        return item.get("expected_sources") or []

    expected_source = item.get("expected_source", "")
    if expected_source:
        return [expected_source]

    return []


def source_is_expected(result: Dict[str, Any], expected_sources: List[str]) -> bool:
    """
    如果没有配置 expected_sources，则不限制来源。
    如果配置了，则 filename/text 中命中任意一个来源关键词即可。
    """

    if not expected_sources:
        return True

    text = result_to_text(result)

    return any(source in text for source in expected_sources)


def keyword_hit_count(text: str, keywords: List[str]) -> int:
    count = 0

    for keyword in keywords:
        if keyword in text:
            count += 1

    return count


def chunk_fact_is_hit(result: Dict[str, Any], item: Dict[str, Any]) -> bool:
    """
    严格 chunk 级命中：
    1. 来源要对；
    2. chunk 内容中要命中足够多的事实关键词。
    """

    expected_sources = get_expected_sources(item)
    expected_chunk_keywords = item.get("expected_chunk_keywords", [])

    # 兼容旧字段 expected_keywords
    if not expected_chunk_keywords:
        expected_chunk_keywords = item.get("expected_keywords", [])

    min_chunk_keyword_hits = item.get("min_chunk_keyword_hits")

    if min_chunk_keyword_hits is None:
        # 默认至少命中 60% 的关键词，且至少 1 个
        min_chunk_keyword_hits = max(1, int(len(expected_chunk_keywords) * 0.6))

    if not source_is_expected(result, expected_sources):
        return False

    if not expected_chunk_keywords:
        return True

    text = result_to_text(result)
    hit_count = keyword_hit_count(text, expected_chunk_keywords)

    return hit_count >= min_chunk_keyword_hits


def find_first_fact_hit_rank(
    results: List[Dict[str, Any]],
    item: Dict[str, Any],
    max_rank: Optional[int] = None,
) -> Optional[int]:
    if max_rank is not None:
        results = results[:max_rank]

    for index, result in enumerate(results, start=1):
        if chunk_fact_is_hit(result, item):
            return index

    return None


def calculate_mrr(rank: Optional[int]) -> float:
    if rank is None:
        return 0.0

    return 1.0 / rank


def context_keyword_coverage(
    results: List[Dict[str, Any]],
    keywords: List[str],
    top_k: int,
) -> float:
    """
    看前 top_k 个 contexts 合起来，覆盖了多少预期事实关键词。
    适合“答案跨多个 chunk”的问题。
    """

    if not keywords:
        return 0.0

    selected_results = results[:top_k]
    combined_text = " ".join(result_to_text(result) for result in selected_results)

    hit_count = keyword_hit_count(combined_text, keywords)

    return hit_count / len(keywords)


def is_refusal_answer(answer: str) -> bool:
    """
    判断大模型是否在拒答。
    避免出现这种假高分：
    “没有找到 SCI 期刊投稿经验” 里面虽然包含 SCI、期刊、投稿，
    但它其实是在说没找到。
    """

    refusal_phrases = [
        "没有找到相关信息",
        "未找到相关信息",
        "没有检索到相关",
        "资料中没有",
        "参考资料中没有",
        "无法根据参考资料",
        "未提供",
        "没有提供",
        "抱歉",
    ]

    return any(phrase in answer for phrase in refusal_phrases)


def answer_keyword_coverage(answer: str, expected_answer_keywords: List[str]) -> float:
    if not expected_answer_keywords:
        return 0.0

    # 如果答案是拒答，就直接记为 0，避免关键词误判
    if is_refusal_answer(answer):
        return 0.0

    hit_count = keyword_hit_count(answer, expected_answer_keywords)

    return hit_count / len(expected_answer_keywords)


def get_matched_context_info(
    results: List[Dict[str, Any]],
    hit_rank: Optional[int],
) -> Dict[str, Any]:
    if hit_rank is None:
        return {
            "matched_filename": "",
            "matched_chunk_hash": "",
            "matched_retrieval_rank": "",
            "matched_milvus_score": "",
            "matched_rerank_score": "",
        }

    item = results[hit_rank - 1]

    return {
        "matched_filename": item.get("filename", ""),
        "matched_chunk_hash": item.get("chunk_hash", ""),
        "matched_retrieval_rank": item.get("retrieval_rank", ""),
        "matched_milvus_score": item.get("score", ""),
        "matched_rerank_score": item.get("rerank_score", ""),
    }


def evaluate_one(item: Dict[str, Any]) -> Dict[str, Any]:
    question = item["question"]
    expected_chunk_keywords = item.get("expected_chunk_keywords", [])
    expected_answer_keywords = item.get("expected_answer_keywords", [])

    # 1. 原始 Milvus 检索结果：不经过 rerank
    raw_results = call_search_api(question, top_k=RAW_CANDIDATE_K)

    raw_fact_hit_rank_at_5 = find_first_fact_hit_rank(
        raw_results,
        item=item,
        max_rank=FINAL_TOP_K,
    )

    raw_fact_hit_rank_at_20 = find_first_fact_hit_rank(
        raw_results,
        item=item,
        max_rank=RAW_CANDIDATE_K,
    )

    raw_context_coverage_at_5 = context_keyword_coverage(
        results=raw_results,
        keywords=expected_chunk_keywords,
        top_k=FINAL_TOP_K,
    )

    # 2. RAG ask：内部已经经过 rerank
    ask_data = call_ask_api(question, top_k=FINAL_TOP_K)
    answer = ask_data.get("answer", "")
    reranked_contexts = ask_data.get("contexts", [])

    rerank_fact_hit_rank_at_5 = find_first_fact_hit_rank(
        reranked_contexts,
        item=item,
        max_rank=FINAL_TOP_K,
    )

    rerank_context_coverage_at_5 = context_keyword_coverage(
        results=reranked_contexts,
        keywords=expected_chunk_keywords,
        top_k=FINAL_TOP_K,
    )

    matched_info = get_matched_context_info(
        results=reranked_contexts,
        hit_rank=rerank_fact_hit_rank_at_5,
    )

    answer_coverage = answer_keyword_coverage(
        answer=answer,
        expected_answer_keywords=expected_answer_keywords,
    )

    return {
        "question": question,
        "expected_sources": "|".join(get_expected_sources(item)),
        "expected_chunk_keywords": "|".join(expected_chunk_keywords),

        "raw_fact_hit_at_5": 1 if raw_fact_hit_rank_at_5 is not None else 0,
        "raw_fact_hit_rank_at_5": raw_fact_hit_rank_at_5 or "",
        "raw_fact_hit_rank_at_20": raw_fact_hit_rank_at_20 or "",
        "raw_mrr_at_5": round(calculate_mrr(raw_fact_hit_rank_at_5), 4),
        "raw_context_keyword_coverage_at_5": round(raw_context_coverage_at_5, 4),

        "rerank_fact_hit_at_5": 1 if rerank_fact_hit_rank_at_5 is not None else 0,
        "rerank_fact_hit_rank_at_5": rerank_fact_hit_rank_at_5 or "",
        "rerank_mrr_at_5": round(calculate_mrr(rerank_fact_hit_rank_at_5), 4),
        "rerank_context_keyword_coverage_at_5": round(rerank_context_coverage_at_5, 4),

        "matched_filename": matched_info["matched_filename"],
        "matched_chunk_hash": matched_info["matched_chunk_hash"],
        "matched_retrieval_rank": matched_info["matched_retrieval_rank"],
        "matched_milvus_score": matched_info["matched_milvus_score"],
        "matched_rerank_score": matched_info["matched_rerank_score"],

        "answer_keyword_coverage": round(answer_coverage, 4),
        "is_refusal_answer": 1 if is_refusal_answer(answer) else 0,
        "answer_preview": answer[:240].replace("\n", " "),
    }


def get_status(row: Dict[str, Any]) -> str:
    """
    给每个问题一个直观状态。
    """

    if row["rerank_fact_hit_at_5"] == 1 and row["answer_keyword_coverage"] >= 0.8:
        return "✅ 通过"

    if row["rerank_fact_hit_at_5"] == 1 and row["answer_keyword_coverage"] < 0.8:
        return "⚠️ 资料命中但答案不完整"

    if row["raw_fact_hit_rank_at_20"] == "":
        return "❌ Milvus 未召回正确 chunk"

    if row["raw_fact_hit_rank_at_20"] != "" and row["rerank_fact_hit_at_5"] == 0:
        return "❌ Rerank 未排进前5"

    return "⚠️ 需要检查"


def get_diagnosis(row: Dict[str, Any]) -> str:
    """
    根据指标自动生成简单诊断。
    """

    if row["rerank_fact_hit_at_5"] == 1 and row["answer_keyword_coverage"] >= 0.8:
        return "检索、重排、答案覆盖整体正常。"

    if row["rerank_fact_hit_at_5"] == 1 and row["answer_keyword_coverage"] < 0.8:
        return "资料已经命中，但答案没有充分覆盖关键词，优先优化 prompt 或 top_k。"

    if row["raw_fact_hit_rank_at_20"] == "":
        return "正确 chunk 没有进入 Milvus top20，优先检查文档是否入库、chunk 切分或 embedding。"

    if row["raw_fact_hit_rank_at_20"] != "" and row["rerank_fact_hit_at_5"] == 0:
        return "正确 chunk 进入了候选集，但 rerank 没排进前5，优先调整 reranker 或 candidate_k。"

    return "需要人工查看详细结果。"


def write_csv(rows: List[Dict[str, Any]], output_file: Path) -> None:
    """
    输出详细版 CSV。
    """

    fieldnames = [
        "question",
        "expected_sources",
        "expected_chunk_keywords",

        "raw_fact_hit_at_5",
        "raw_fact_hit_rank_at_5",
        "raw_fact_hit_rank_at_20",
        "raw_mrr_at_5",
        "raw_context_keyword_coverage_at_5",

        "rerank_fact_hit_at_5",
        "rerank_fact_hit_rank_at_5",
        "rerank_mrr_at_5",
        "rerank_context_keyword_coverage_at_5",

        "matched_filename",
        "matched_chunk_hash",
        "matched_retrieval_rank",
        "matched_milvus_score",
        "matched_rerank_score",

        "answer_keyword_coverage",
        "is_refusal_answer",
        "answer_preview",
    ]

    with open(output_file, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_readable_csv(rows: List[Dict[str, Any]], output_file: Path) -> None:
    """
    输出一个更适合人看的精简版 CSV。
    """

    readable_rows = []

    for row in rows:
        readable_rows.append({
            "状态": get_status(row),
            "问题": row["question"],
            "预期来源": row["expected_sources"],
            "原始检索是否命中": row["raw_fact_hit_at_5"],
            "原始命中排名": row["raw_fact_hit_rank_at_5"],
            "Rerank是否命中": row["rerank_fact_hit_at_5"],
            "Rerank命中排名": row["rerank_fact_hit_rank_at_5"],
            "答案关键词覆盖率": row["answer_keyword_coverage"],
            "是否拒答": row["is_refusal_answer"],
            "诊断建议": get_diagnosis(row),
        })

    fieldnames = [
        "状态",
        "问题",
        "预期来源",
        "原始检索是否命中",
        "原始命中排名",
        "Rerank是否命中",
        "Rerank命中排名",
        "答案关键词覆盖率",
        "是否拒答",
        "诊断建议",
    ]

    with open(output_file, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(readable_rows)


def write_markdown_report(rows: List[Dict[str, Any]], output_file: Path) -> None:
    total = len(rows)

    if total == 0:
        output_file.write_text("# RAG 评估报告\n\n没有评估样本。", encoding="utf-8")
        return

    raw_hit = sum(row["raw_fact_hit_at_5"] for row in rows)
    rerank_hit = sum(row["rerank_fact_hit_at_5"] for row in rows)

    raw_mrr = sum(row["raw_mrr_at_5"] for row in rows) / total
    rerank_mrr = sum(row["rerank_mrr_at_5"] for row in rows) / total

    raw_context_coverage = (
        sum(row["raw_context_keyword_coverage_at_5"] for row in rows) / total
    )

    rerank_context_coverage = (
        sum(row["rerank_context_keyword_coverage_at_5"] for row in rows) / total
    )

    answer_coverage = (
        sum(row["answer_keyword_coverage"] for row in rows) / total
    )

    pass_count = sum(1 for row in rows if get_status(row) == "✅ 通过")
    warning_count = sum(1 for row in rows if get_status(row).startswith("⚠️"))
    fail_count = sum(1 for row in rows if get_status(row).startswith("❌"))

    lines = []

    lines.append("# RAG / Rerank 评估报告")
    lines.append("")
    lines.append("## 一、总体指标")
    lines.append("")
    lines.append("| 指标 | 数值 | 含义 |")
    lines.append("|---|---:|---|")
    lines.append(f"| 问题总数 | {total} | 本次参与评估的问题数量 |")
    lines.append(f"| 通过数量 | {pass_count} | 检索命中且答案覆盖率较高的问题数量 |")
    lines.append(f"| 警告数量 | {warning_count} | 检索命中但答案不完整，或需要人工检查的问题数量 |")
    lines.append(f"| 失败数量 | {fail_count} | 检索或重排失败的问题数量 |")
    lines.append(f"| Raw Milvus Fact Hit@5 | {raw_hit / total:.4f} | 原始向量检索前5个结果是否命中事实chunk |")
    lines.append(f"| Rerank Fact Hit@5 | {rerank_hit / total:.4f} | rerank后前5个结果是否命中事实chunk |")
    lines.append(f"| Raw Milvus MRR@5 | {raw_mrr:.4f} | 原始检索中正确chunk的平均排名质量 |")
    lines.append(f"| Rerank MRR@5 | {rerank_mrr:.4f} | rerank后正确chunk的平均排名质量 |")
    lines.append(f"| Raw Context Keyword Coverage@5 | {raw_context_coverage:.4f} | 原始前5个chunk覆盖事实关键词的比例 |")
    lines.append(f"| Rerank Context Keyword Coverage@5 | {rerank_context_coverage:.4f} | rerank后前5个chunk覆盖事实关键词的比例 |")
    lines.append(f"| Answer Keyword Coverage | {answer_coverage:.4f} | 最终答案覆盖预期关键词的比例 |")
    lines.append("")

    lines.append("## 二、逐题结果")
    lines.append("")
    lines.append("| 状态 | 问题 | 原始命中排名 | Rerank命中排名 | 答案覆盖率 | 是否拒答 | 诊断 |")
    lines.append("|---|---|---:|---:|---:|---:|---|")

    for row in rows:
        raw_rank = row["raw_fact_hit_rank_at_5"] or "-"
        rerank_rank = row["rerank_fact_hit_rank_at_5"] or "-"
        lines.append(
            f"| {get_status(row)} | {row['question']} | {raw_rank} | {rerank_rank} | {row['answer_keyword_coverage']} | {row['is_refusal_answer']} | {get_diagnosis(row)} |"
        )

    lines.append("")
    lines.append("## 三、结论")
    lines.append("")

    if rerank_hit / total >= 0.9 and answer_coverage >= 0.8:
        lines.append("当前 RAG 系统在本测试集上表现较好：事实召回稳定，答案覆盖率较高。")
    elif rerank_hit / total >= 0.9 and answer_coverage < 0.8:
        lines.append("当前检索效果较好，但答案覆盖率不足，建议优先优化 prompt 和回答格式。")
    else:
        lines.append("当前系统仍存在检索不稳定问题，建议查看失败问题并定位是文档入库、chunk、embedding 还是 rerank 的问题。")

    lines.append("")
    lines.append("## 四、下一步建议")
    lines.append("")
    lines.append("1. 如果某些问题 Fact Hit@5 为 0，优先检查对应文件是否入库、chunk 是否切碎。")
    lines.append("2. 如果 raw 命中但 rerank 未命中，优先调整 reranker 或 candidate_k。")
    lines.append("3. 如果资料命中但答案覆盖率低，优先优化 prompt。")
    lines.append("4. 当测试集扩大到 20-50 条后，再考虑是否更换中文 embedding 模型。")

    output_file.write_text("\n".join(lines), encoding="utf-8")


def print_summary(rows: List[Dict[str, Any]]) -> None:
    total = len(rows)

    if total == 0:
        print("没有评估样本。")
        return

    raw_hit = sum(row["raw_fact_hit_at_5"] for row in rows)
    rerank_hit = sum(row["rerank_fact_hit_at_5"] for row in rows)

    raw_mrr = sum(row["raw_mrr_at_5"] for row in rows) / total
    rerank_mrr = sum(row["rerank_mrr_at_5"] for row in rows) / total

    raw_context_coverage = (
        sum(row["raw_context_keyword_coverage_at_5"] for row in rows) / total
    )
    rerank_context_coverage = (
        sum(row["rerank_context_keyword_coverage_at_5"] for row in rows) / total
    )

    avg_answer_coverage = (
        sum(row["answer_keyword_coverage"] for row in rows) / total
    )

    pass_count = sum(1 for row in rows if get_status(row) == "✅ 通过")
    warning_count = sum(1 for row in rows if get_status(row).startswith("⚠️"))
    fail_count = sum(1 for row in rows if get_status(row).startswith("❌"))

    print("\n========== 严格 Rerank 评估结果 ==========")
    print(f"问题总数: {total}")
    print(f"通过数量: {pass_count}")
    print(f"警告数量: {warning_count}")
    print(f"失败数量: {fail_count}")
    print(f"Raw Milvus Fact Hit@{FINAL_TOP_K}: {raw_hit / total:.4f}")
    print(f"Rerank Fact Hit@{FINAL_TOP_K}: {rerank_hit / total:.4f}")
    print(f"Raw Milvus MRR@{FINAL_TOP_K}: {raw_mrr:.4f}")
    print(f"Rerank MRR@{FINAL_TOP_K}: {rerank_mrr:.4f}")
    print(f"Raw Context Keyword Coverage@{FINAL_TOP_K}: {raw_context_coverage:.4f}")
    print(f"Rerank Context Keyword Coverage@{FINAL_TOP_K}: {rerank_context_coverage:.4f}")
    print(f"Answer Keyword Coverage: {avg_answer_coverage:.4f}")

    print("\n说明：")
    print("- Fact Hit@5：前 5 个 chunk 中是否存在一个真正包含关键事实的 chunk。")
    print("- MRR@5：命中的事实 chunk 排得越靠前，分数越高。")
    print("- Context Keyword Coverage@5：前 5 个 chunk 合起来覆盖了多少事实关键词。")
    print("- Answer Keyword Coverage：最终答案覆盖了多少预期答案关键词。")


def main():
    eval_items = load_eval_questions(EVAL_FILE)

    rows = []

    for item in eval_items:
        print(f"正在评估：{item['question']}")
        try:
            row = evaluate_one(item)
            rows.append(row)
        except Exception as e:
            print(f"评估失败：{item['question']}")
            print(f"错误信息：{e}")

    write_csv(rows, OUTPUT_FILE)
    write_readable_csv(rows, READABLE_CSV_FILE)
    write_markdown_report(rows, REPORT_FILE)

    print_summary(rows)

    print(f"\n详细结果已保存到：{OUTPUT_FILE}")
    print(f"精简结果已保存到：{READABLE_CSV_FILE}")
    print(f"评估报告已保存到：{REPORT_FILE}")


if __name__ == "__main__":
    main()