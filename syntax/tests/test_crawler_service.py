from unittest.mock import MagicMock

from app.crawler.models import CrawlerError, CrawlerRequest, CrawlerResult
from app.crawler.service import CrawlerService


def test_service_strategy_routing():
    mock_strategy1 = MagicMock()
    mock_strategy1.can_handle.return_value = False

    mock_strategy2 = MagicMock()
    mock_strategy2.can_handle.return_value = True
    
    mock_result = CrawlerResult(success=True)
    mock_strategy2.crawl.return_value = mock_result

    service = CrawlerService([mock_strategy1, mock_strategy2])
    request = CrawlerRequest(url="https://some-repo.com")

    result = service.crawl_repository(request)

    mock_strategy1.can_handle.assert_called_once_with(request)
    mock_strategy1.crawl.assert_not_called()

    mock_strategy2.can_handle.assert_called_once_with(request)
    mock_strategy2.crawl.assert_called_once_with(request)

    assert result is mock_result


def test_service_no_strategy():
    mock_strategy1 = MagicMock()
    mock_strategy1.can_handle.return_value = False

    service = CrawlerService([mock_strategy1])
    request = CrawlerRequest(url="https://unknown-repo.com")

    result = service.crawl_repository(request)

    assert result.success is False
    assert len(result.errors) == 1
    assert result.errors[0].code == "UNSUPPORTED_REPOSITORY"
    assert "unknown-repo.com" in result.errors[0].message


def test_service_default_instantiation():
    service = CrawlerService()
    # It should have GitHub and Git as defaults
    assert len(service.strategies) == 2
    assert type(service.strategies[0]).__name__ == "GitHubCrawlerStrategy"
    assert type(service.strategies[1]).__name__ == "GitCloneCrawlerStrategy"
