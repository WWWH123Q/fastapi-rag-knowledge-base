from typing import Optional

from app.config import settings


class WebSearchService:
    """
    网络搜索服务：
    支持 Tavily 和 DuckDuckGo/DDGS。
    统一返回 sources，后面交给大模型生成答案。
    """

    def __init__(self):
        self.provider = settings.web_search_provider

    def search(  #根据 provider 选择具体使用哪个搜索引擎。
        self,
        query: str,
        max_results: Optional[int] = None,
        provider: Optional[str] = None,
    ) -> list[dict]:
        provider = provider or self.provider
        max_results = max_results or settings.web_search_max_results

        if provider == "tavily":
            return self._search_tavily(query, max_results)

        if provider == "duckduckgo":
            return self._search_duckduckgo(query, max_results)

        raise ValueError(f"不支持的搜索引擎 provider: {provider}")

    def _search_tavily(self, query: str, max_results: int) -> list[dict]:
        if not settings.tavily_api_key:
            raise ValueError("当前使用 Tavily，但 .env 中没有配置 TAVILY_API_KEY")

        from tavily import TavilyClient

        client = TavilyClient(api_key=settings.tavily_api_key)
        # Tavily是一个比较适合给AI应用做联网搜索的搜索服务。它不仅能返回标题和链接，还可以返回网页内容。

        response = client.search(
            query=query,
            max_results=max_results,
            search_depth="advanced", #搜索深度设置为高级，搜索更深入，结果可能更丰富，但速度可能更慢。
            include_raw_content=True,#不只返回网页标题和摘要，还尽量返回网页正文内容。
            include_answer=False, #不让 Tavily 自己生成总结答案，只要搜索结果。
        )

        #整理 Tavily 返回结果
        sources = []

        for index, item in enumerate(response.get("results", [])):
            title = item.get("title", "")
            url = item.get("url", "")
            content = item.get("raw_content") or item.get("content") or ""

            sources.append(
                {
                    "rank": index + 1,
                    "source_type": "web",
                    "provider": "tavily",
                    "title": title,
                    "url": url,
                    "filename": "",
                    "text": str(content).strip()[:4000],
                    "score": item.get("score"),
                }
            )

        return sources

    def _search_duckduckgo(self, query: str, max_results: int) -> list[dict]:
        from ddgs import DDGS

        ddgs = DDGS(timeout=10)

        search_results = ddgs.text(
            query,
            max_results=max_results,
            backend="duckduckgo",
        )

        sources = []

        for index, item in enumerate(search_results):
            title = item.get("title", "")
            url = item.get("href") or item.get("url") or ""
            snippet = item.get("body", "")

            content = snippet

            # 尝试进一步抓取网页正文；失败就退回搜索摘要
            if url:
                try:
                    extracted = ddgs.extract(url, fmt="text_plain")
                    content = extracted.get("content") or snippet
                except Exception:
                    content = snippet

            sources.append(
                {
                    "rank": index + 1,
                    "source_type": "web",
                    "provider": "duckduckgo",
                    "title": title,
                    "url": url,
                    "filename": "",
                    "text": str(content).strip()[:4000],
                    "score": None,
                }
            )

        return sources