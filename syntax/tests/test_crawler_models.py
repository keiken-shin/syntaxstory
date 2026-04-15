import pytest
from app.crawler.models import (
    CrawlerRequest,
    CrawlerResult,
    FileManifestItem,
    CrawlerStats,
    CrawlerError,
)
from app.crawler.base import CrawlerStrategy


class DummyStrategy(CrawlerStrategy):
    def can_handle(self, request: CrawlerRequest) -> bool:
        return "dummy" in request.url

    def crawl(self, request: CrawlerRequest) -> CrawlerResult:
        if not self.can_handle(request):
            return CrawlerResult(
                success=False,
                errors=[CrawlerError(code="INVALID_URL", message="Cannot handle URL")]
            )
            
        file_item = FileManifestItem(path="main.py", size_bytes=100, content="print('hello')")
        stats = CrawlerStats(files_scanned=1, files_ingested=1, bytes_ingested=100)
        return CrawlerResult(success=True, manifest=[file_item], stats=stats)


def test_crawler_models_serialization():
    req = CrawlerRequest(url="https://github.com/dummy/repo", auth_token="abc")
    assert req.max_file_size_bytes == 1024 * 1024

    strat = DummyStrategy()
    
    assert strat.can_handle(req) is True

    result = strat.crawl(req)
    assert result.success is True
    assert len(result.manifest) == 1
    assert result.manifest[0].path == "main.py"
    assert result.stats.files_scanned == 1

def test_crawler_contract_failure():
    req = CrawlerRequest(url="https://github.com/nothing/repo")
    
    strat = DummyStrategy()
    assert strat.can_handle(req) is False

    result = strat.crawl(req)
    assert result.success is False
    assert len(result.errors) == 1
    assert result.errors[0].code == "INVALID_URL"
