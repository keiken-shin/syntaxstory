from unittest.mock import patch, MagicMock
from app.crawler.github import GitHubCrawlerStrategy
from app.crawler.models import CrawlerRequest

def test_github_can_handle():
    strategy = GitHubCrawlerStrategy()
    assert strategy.can_handle(CrawlerRequest(url="https://github.com/owner/repo"))
    assert not strategy.can_handle(CrawlerRequest(url="https://gitlab.com/owner/repo"))

def test_github_parse_url():
    strategy = GitHubCrawlerStrategy()
    owner, repo, ref, subpath = strategy._parse_url("https://github.com/owner/repo")
    assert owner == "owner"
    assert repo == "repo"
    assert ref is None
    assert subpath == ""

    # With branch and subpath
    owner, repo, ref, subpath = strategy._parse_url("https://github.com/owner/repo/tree/dev/src/main.py")
    assert owner == "owner"
    assert repo == "repo"
    assert ref == "dev"
    assert subpath == "src/main.py"

@patch("app.crawler.github.requests.get")
def test_github_crawl_success(mock_get):
    
    # Mocking first call: repo details
    mock_repo_resp = MagicMock()
    mock_repo_resp.status_code = 200
    mock_repo_resp.json.return_value = {"default_branch": "main"}
    
    # Mocking second call: tree
    mock_tree_resp = MagicMock()
    mock_tree_resp.status_code = 200
    mock_tree_resp.json.return_value = {
        "tree": [
            {"type": "blob", "path": "file1.txt", "size": 10},
            {"type": "blob", "path": "file2.py", "size": 20}
        ]
    }
    
    # Mocking third/fourth calls: raw fetches
    mock_raw_resp1 = MagicMock()
    mock_raw_resp1.status_code = 200
    mock_raw_resp1.content = b"hello txt"
    
    mock_raw_resp2 = MagicMock()
    mock_raw_resp2.status_code = 200
    mock_raw_resp2.content = b"print('hello')"

    mock_get.side_effect = [mock_repo_resp, mock_tree_resp, mock_raw_resp1, mock_raw_resp2]

    strategy = GitHubCrawlerStrategy()
    req = CrawlerRequest(url="https://github.com/owner/repo")
    res = strategy.crawl(req)
    
    assert res.success is True
    assert len(res.manifest) == 2
    assert res.stats.files_ingested == 2
    assert res.manifest[0].path == "file1.txt"
    assert res.manifest[0].content == "hello txt"

def test_github_should_include():
    strategy = GitHubCrawlerStrategy()
    assert strategy._should_include("src/main.py", [], []) is True
    assert strategy._should_include("src/main.py", ["*.py"], []) is True
    assert strategy._should_include("src/main.py", ["*.txt"], []) is False
    assert strategy._should_include("src/main.py", ["*.py"], ["src/*"]) is False
    assert strategy._should_include("tests/main.py", ["*.py"], ["src/*"]) is True
