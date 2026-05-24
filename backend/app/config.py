from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    llm_base_url: str = "https://api.deepseek.com"
    llm_api_key: str = ""
    llm_model: str = "deepseek-chat"

    web_search_provider: str = "tavily"
    tavily_api_key: str = ""
    web_search_max_results: int = 3

    embedding_model_name: str = "BAAI/bge-m3"
    rerank_model_name: str = "BAAI/bge-reranker-base"
    rerank_threshold: float = 0.55
    vector_candidate_multiplier: int = 4
    vector_candidate_min: int = 20
    enable_bm25: bool = True
    bm25_top_k: int = 20

    api_key: str = ""
    cors_allowed_origins: str = "http://localhost:3000,http://localhost:5173,http://127.0.0.1:5173"
    max_upload_mb: int = 20
    rate_limit_requests: int = 60
    rate_limit_window_seconds: int = 60

    @property
    def cors_origins(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.cors_allowed_origins.split(",")
            if origin.strip()
        ]

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024


settings = Settings()
