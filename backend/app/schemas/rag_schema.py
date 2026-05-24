from typing import List, Literal, Optional

from pydantic import BaseModel, Field, field_validator


class QueryMixin(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000)

    @field_validator("query")
    @classmethod
    def query_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("query must not be blank")
        return value


class MetadataFilterMixin(BaseModel):
    filename: Optional[str] = None
    file_hash: Optional[str] = None
    file_ext: Optional[str] = None
    uploaded_after: Optional[str] = None
    uploaded_before: Optional[str] = None

    def metadata_filter(self) -> dict:
        return {
            "filename": self.filename,
            "file_hash": self.file_hash,
            "file_ext": self.file_ext,
            "uploaded_after": self.uploaded_after,
            "uploaded_before": self.uploaded_before,
        }


class SearchRequest(QueryMixin, MetadataFilterMixin):
    top_k: int = Field(default=5, ge=1, le=20)


class AskRequest(QueryMixin, MetadataFilterMixin):
    top_k: int = Field(default=5, ge=1, le=20)


class ContextItem(BaseModel):
    rank: int
    text: str
    filename: str = ""
    file_hash: str = ""
    file_ext: str = ""
    uploaded_at: str = ""
    chunk_hash: str = ""
    score: Optional[float] = None
    vector_score: Optional[float] = None
    bm25_score: Optional[float] = None
    retrieval_rank: Optional[int] = None
    rerank_score: Optional[float] = None
    retrieval_source: str = ""
    retrieval_sources: List[str] = Field(default_factory=list)


class SearchResponse(BaseModel):
    query: str
    top_k: int
    embedding_dimension: int
    results: List[ContextItem]


class AskResponse(BaseModel):
    query: str
    answer: str
    top_k: int
    contexts: List[ContextItem]
    best_rerank_score: Optional[float] = None
    min_rerank_threshold: float = 0.55
    retrieved_count: int = 0
    reranked_count: int = 0
    rejected_by_low_confidence: bool = False


class WebSearchRequest(QueryMixin):
    top_k: int = Field(default=5, ge=1, le=10)
    provider: Optional[Literal["tavily", "duckduckgo"]] = None


class WebSourceItem(BaseModel):
    rank: int
    source_type: str = "web"
    provider: str = ""
    title: str = ""
    url: str = ""
    filename: str = ""
    text: str = ""
    file_hash: str = ""
    file_ext: str = ""
    uploaded_at: str = ""
    chunk_hash: str = ""
    score: Optional[float] = None
    vector_score: Optional[float] = None
    bm25_score: Optional[float] = None
    retrieval_rank: Optional[int] = None
    rerank_score: Optional[float] = None
    retrieval_source: str = ""
    retrieval_sources: List[str] = Field(default_factory=list)


class WebAskResponse(BaseModel):
    query: str
    answer: str
    provider: str
    sources: List[WebSourceItem]


class HybridAskRequest(QueryMixin, MetadataFilterMixin):
    local_top_k: int = Field(default=5, ge=1, le=20)
    web_top_k: int = Field(default=5, ge=1, le=10)
    provider: Optional[Literal["tavily", "duckduckgo"]] = None


class HybridAskResponse(BaseModel):
    query: str
    answer: str
    local_top_k: int
    web_top_k: int
    provider: str
    sources: List[WebSourceItem]
    best_rerank_score: Optional[float] = None
    min_rerank_threshold: float = 0.55
    retrieved_count: int = 0
    reranked_count: int = 0
    rejected_by_low_confidence: bool = False


class UploadResponse(BaseModel):
    message: str
    filename: str
    file_hash: str
    chunk_count: int
    embedding_dimension: Optional[int] = None
    duplicated: bool
    file_ext: Optional[str] = None
    uploaded_at: Optional[str] = None


class DocumentItem(BaseModel):
    filename: str
    file_hash: str
    file_ext: str = ""
    uploaded_at: str = ""
    chunk_count: int


class DocumentListResponse(BaseModel):
    total: int
    documents: List[DocumentItem]


class DeleteDocumentResponse(BaseModel):
    found: bool
    message: str = ""
    filename: str = ""
    file_hash: str
    deleted: bool = False
