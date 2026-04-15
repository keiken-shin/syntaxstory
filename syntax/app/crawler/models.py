from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field

class FileManifestItem(BaseModel):
    path: str
    size_bytes: int
    content: str | None = None
    binary: bool = False

class CrawlerStats(BaseModel):
    files_scanned: int = 0
    files_ingested: int = 0
    bytes_ingested: int = 0
    files_skipped: int = 0
    duration_ms: float = 0.0

class CrawlerError(BaseModel):
    code: str
    message: str
    details: Dict[str, Any] = Field(default_factory=dict)

class CrawlerRequest(BaseModel):
    url: str = Field(description="URL of the repository (or sub-path) to crawl.")
    auth_token: Optional[str] = Field(default=None, description="Optional token for private repos or rate-limit lifting.")
    max_file_size_bytes: int = Field(default=1024 * 1024, description="Max file size in bytes to read content for.")
    include_patterns: List[str] = Field(default_factory=list, description="Glob patterns for files to include.")
    exclude_patterns: List[str] = Field(default_factory=list, description="Glob patterns for files to exclude.")
    branch_or_commit: Optional[str] = Field(default=None, description="Specific git reference to use.")

class CrawlerResult(BaseModel):
    success: bool
    manifest: List[FileManifestItem] = Field(default_factory=list)
    stats: CrawlerStats = Field(default_factory=CrawlerStats)
    errors: List[CrawlerError] = Field(default_factory=list)
