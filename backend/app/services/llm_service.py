from __future__ import annotations

from openai import OpenAI

from app.config import settings


class LLMService:
    def __init__(self):
        self.client = OpenAI(
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
        )
        self.model = settings.llm_model

    def generate_answer(self, query: str, context_text: str) -> str:
        system_prompt = """
你是一个严谨的本地知识库问答助手。

要求：
1. 优先依据给定资料回答。
2. 不要编造资料中没有出现的内容。
3. 如果资料不足，明确说“根据当前资料无法确定”。
4. 如果资料中有多个事实，尽量逐条覆盖。
5. 回答结尾列出参考资料编号和文件名。
"""

        user_prompt = f"""
【参考资料】
{context_text}

【用户问题】
{query}

请用中文回答。
"""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt.strip()},
                {"role": "user", "content": user_prompt.strip()},
            ],
            temperature=0.2,
        )

        return response.choices[0].message.content

    def generate_answer_from_sources(
        self,
        question: str,
        sources: list[dict],
        mode: str = "web",
    ) -> str:
        source_text = self._format_sources(sources)

        if mode == "hybrid":
            system_prompt = """
你是一个严谨的混合 RAG 问答助手。

要求：
1. 明确区分本地资料和网络资料。
2. 优先使用本地资料，网络资料只作为补充。
3. 如果本地资料和网络资料冲突，以本地资料为主，并说明存在差异。
4. 不要编造资料中没有出现的内容。
5. 如果资料不足，明确说“根据当前资料无法确定”。
6. 回答结尾列出参考资料编号和文件名或网页标题。
"""
        else:
            system_prompt = """
你是一个严谨的检索增强问答助手。

要求：
1. 只能根据给定参考资料回答。
2. 不要编造资料中没有出现的内容。
3. 如果资料不足，明确说“根据当前资料无法确定”。
4. 回答结尾列出参考资料编号和文件名或网页标题。
"""

        user_prompt = f"""
【参考资料】
{source_text}

【用户问题】
{question}

请用中文回答。
"""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt.strip()},
                {"role": "user", "content": user_prompt.strip()},
            ],
            temperature=0.2,
        )

        return response.choices[0].message.content

    def _format_sources(self, sources: list[dict]) -> str:
        if not sources:
            return "No relevant reference material was retrieved."

        parts = []
        for item in sources:
            rank = item.get("rank", "")
            source_type = item.get("source_type", "web")
            filename = item.get("filename") or item.get("title", "")
            text = item.get("text", "")

            parts.append(
                f"[资料{rank}]\n"
                f"source_type: {source_type}\n"
                f"filename: {filename}\n"
                f"text:\n{text}"
            )

        return "\n\n".join(parts)
