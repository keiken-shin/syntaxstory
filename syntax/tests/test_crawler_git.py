import os
from unittest.mock import MagicMock, patch

import pytest
from git.exc import GitCommandError

from app.crawler.git import GitCloneCrawlerStrategy
from app.crawler.models import CrawlerRequest


def test_git_can_handle():
    strategy = GitCloneCrawlerStrategy()
    assert strategy.can_handle(CrawlerRequest(url="https://github.com/owner/repo.git"))
    assert strategy.can_handle(CrawlerRequest(url="git@github.com:owner/repo.git"))
    assert strategy.can_handle(CrawlerRequest(url="http://gitlab.com/owner/repo"))


def test_git_inject_token():
    strategy = GitCloneCrawlerStrategy()
    url = "https://github.com/owner/repo"
    
    # HTTPs without token
    assert strategy._inject_token(url, None) == url
    
    # HTTPs with token
    injected = strategy._inject_token(url, "mytoken")
    assert injected == "https://mytoken@github.com/owner/repo"
    
    # SSH should ignore token
    ssh_url = "git@github.com:owner/repo.git"
    assert strategy._inject_token(ssh_url, "mytoken") == ssh_url

    # URL with existing creds should be ignored
    creds_url = "https://user:pass@github.com/owner/repo"
    assert strategy._inject_token(creds_url, "mytoken") == creds_url


def test_git_should_include():
    strategy = GitCloneCrawlerStrategy()
    
    assert strategy._should_include(".git/config", [], []) is False
    assert strategy._should_include("src/.git/config", [], []) is False
    assert strategy._should_include("main.py", [], []) is True
    
    assert strategy._should_include("main.py", ["*.py"], []) is True
    assert strategy._should_include("main.txt", ["*.py"], []) is False
    assert strategy._should_include("src/main.py", ["*.py"], ["src/*"]) is False


@patch("app.crawler.git.git.Repo.clone_from")
@patch("app.crawler.git.os.walk")
@patch("app.crawler.git.os.path.getsize")
@patch("builtins.open")
def test_git_crawl_success(mock_open, mock_getsize, mock_walk, mock_clone):
    # Mock clone
    mock_repo = MagicMock()
    mock_clone.return_value = mock_repo
    
    # Needs to match the behavior properly
    def mock_walk_func(tmpdir, *args, **kwargs):
        # Using the actual received tempdir so os.path.relpath works across OS
        return [
            (tmpdir, [], ["main.py", "logo.png"])
        ]
        
    mock_walk.side_effect = mock_walk_func
    
    # Mock getsize
    mock_getsize.side_effect = lambda path: 1024 if "main.py" in path else 2048
    
    # Mock open to simulate text and binary reads
    def mock_file_read(path, *args, **kwargs):
        mock_file = MagicMock()
        if "main.py" in path:
            mock_file.read.return_value = "print('hello')"
        else:
            mock_file.read.side_effect = UnicodeDecodeError("utf-8", b"", 0, 1, "invalid")
        
        # We need an enter and exit for the context manager
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_file
        return mock_context

    mock_open.side_effect = mock_file_read

    strategy = GitCloneCrawlerStrategy()
    request = CrawlerRequest(url="https://github.com/owner/repo", branch_or_commit="dev")
    
    result = strategy.crawl(request)
    
    # Checking branch checkout was called
    mock_repo.git.checkout.assert_called_once_with("dev")
    
    assert result.success is True
    assert result.stats.files_ingested == 2 # 1 text + 1 binary
    assert result.stats.bytes_ingested == 3072 # 1024 + 2048


    # Check manifest mapping
    text_file = next(f for f in result.manifest if f.path == "main.py")
    binary_file = next(f for f in result.manifest if f.path == "logo.png")
    
    assert text_file.content == "print('hello')"
    assert text_file.binary is False
    assert binary_file.content is None
    assert binary_file.binary is True


@patch("app.crawler.git.git.Repo.clone_from")
def test_git_crawl_clone_failure(mock_clone):
    # Raise a clone error
    mock_clone.side_effect = GitCommandError("clone", 1, b"", b"Authentication failed")
    
    strategy = GitCloneCrawlerStrategy()
    request = CrawlerRequest(url="https://github.com/owner/repo")
    
    result = strategy.crawl(request)
    
    assert result.success is False
    assert len(result.errors) == 1
    assert result.errors[0].code == "AUTH_FAILED"
