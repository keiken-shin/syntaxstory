from abc import ABC, abstractmethod

from app.crawler.models import CrawlerRequest, CrawlerResult

class CrawlerStrategy(ABC):
    """
    Base contract for hybrid repository crawlers (GitHub API vs Git Clone).
    Every implementation must adhere to this interface to abstract away the ingestion mechanism
    from the main ingestion pipeline and AI tutorial generation services.
    """
    
    @abstractmethod
    def can_handle(self, request: CrawlerRequest) -> bool:
        """
        Determine if this strategy is capable of or optimally suited to 
        handling the given request (e.g., checks if the URL is GitHub-like, 
        or if git-clone is needed).
        """
        pass

    @abstractmethod
    def crawl(self, request: CrawlerRequest) -> CrawlerResult:
        """
        Execute the crawl and return a normalized manifest and statistics.
        Crawler implementations should catch internal errors and map them to 
        CrawlerResult.errors rather than raising bare exceptions, ensuring 
        graceful degradation.
        """
        pass