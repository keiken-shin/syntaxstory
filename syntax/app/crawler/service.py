from typing import List, Optional

from app.crawler.base import CrawlerStrategy
from app.crawler.git import GitCloneCrawlerStrategy
from app.crawler.github import GitHubCrawlerStrategy
from app.crawler.models import CrawlerError, CrawlerRequest, CrawlerResult


class CrawlerService:
    """
    Coordinates repository ingestion by selecting the most appropriate 
    CrawlerStrategy out of registered implementations cleanly.
    """
    
    def __init__(self, strategies: Optional[List[CrawlerStrategy]] = None):
        # Order matters! Prefer optimized API crawlers over raw git cloning fallbacks
        if strategies is None:
            self.strategies = [
                GitHubCrawlerStrategy(),
                GitCloneCrawlerStrategy(),
            ]
        else:
            self.strategies = strategies

    def crawl_repository(self, request: CrawlerRequest) -> CrawlerResult:
        """
        Ingest the repository specified in the request by selecting the 
        first capable strategy.
        """
        for strategy in self.strategies:
            if strategy.can_handle(request):
                return strategy.crawl(request)
                
        return CrawlerResult(
            success=False,
            errors=[
                CrawlerError(
                    code="UNSUPPORTED_REPOSITORY",
                    message=f"No suitable crawler strategy found for URL: {request.url}"
                )
            ]
        )
