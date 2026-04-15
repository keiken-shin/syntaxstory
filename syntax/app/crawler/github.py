import base64
import fnmatch
import time
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

import requests

from app.crawler.base import CrawlerStrategy
from app.crawler.models import (
    CrawlerError,
    CrawlerRequest,
    CrawlerResult,
    CrawlerStats,
    FileManifestItem,
)


class GitHubCrawlerStrategy(CrawlerStrategy):
    """
    Crawler implementation that uses the GitHub REST API (Trees and Blobs).
    Extracts owner, repo, ref, and subpath from the URL.
    """
    
    def can_handle(self, request: CrawlerRequest) -> bool:
        """
        Handles github.com URLs.
        """
        parsed = urlparse(request.url)
        return parsed.netloc in ("github.com", "api.github.com")

    def _parse_url(self, url: str) -> Tuple[str, str, Optional[str], str]:
        """
        Extracts owner, repo, ref, and subpath from a GitHub URL.
        Example: https://github.com/owner/repo/tree/main/src/app
        Returns: (owner, repo, ref, subpath)
        """
        parsed = urlparse(url)
        parts = [p for p in parsed.path.strip("/").split("/") if p]
        
        if len(parts) < 2:
            raise ValueError("URL must contain at least owner and repo.")
            
        owner, repo = parts[0], parts[1]
        ref = None
        subpath = ""
        
        if len(parts) >= 4 and parts[2] == "tree":
            ref = parts[3]
            subpath = "/".join(parts[4:])
            
        return owner, repo, ref, subpath

    def _should_include(
        self, path: str, include_patterns: List[str], exclude_patterns: List[str]
    ) -> bool:
        """Evaluate if a path matches the given include and exclude patterns."""
        filename = path.split("/")[-1]
        
        include = True
        if include_patterns:
            include = any(
                fnmatch.fnmatch(filename, pat) or fnmatch.fnmatch(path, pat)
                for pat in include_patterns
            )
            
        if include and exclude_patterns:
            exclude = any(
                fnmatch.fnmatch(filename, pat) or fnmatch.fnmatch(path, pat)
                for pat in exclude_patterns
            )
            if exclude:
                return False
                
        return include

    def crawl(self, request: CrawlerRequest) -> CrawlerResult:
        start_time = time.perf_counter()
        manifest: List[FileManifestItem] = []
        stats = CrawlerStats()
        errors: List[CrawlerError] = []
        
        try:
            owner, repo, ref, subpath = self._parse_url(request.url)
        except ValueError as e:
            return CrawlerResult(
                success=False,
                errors=[CrawlerError(code="INVALID_URL", message=str(e))]
            )

        active_ref = request.branch_or_commit or ref
        
        headers = {"Accept": "application/vnd.github.v3+json"}
        if request.auth_token:
            headers["Authorization"] = f"Bearer {request.auth_token}"

        if not active_ref:
            repo_api_url = f"https://api.github.com/repos/{owner}/{repo}"
            resp = requests.get(repo_api_url, headers=headers, timeout=10)
            if resp.status_code != 200:
                stats.duration_ms = (time.perf_counter() - start_time) * 1000
                res = self._build_error_result("API_FETCH_ERROR", resp)
                res.stats = stats
                return res
            active_ref = resp.json().get("default_branch", "main")

        tree_url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{active_ref}?recursive=1"
        resp = requests.get(tree_url, headers=headers, timeout=20)
        
        if resp.status_code != 200:
            stats.duration_ms = (time.perf_counter() - start_time) * 1000
            res = self._build_error_result("TREE_FETCH_ERROR", resp)
            res.stats = stats
            return res
            
        tree_data = resp.json()
        if tree_data.get("truncated"):
            errors.append(CrawlerError(
                code="TREE_TRUNCATED",
                message="The repository is too large; the returned tree is truncated."
            ))
            
        items = tree_data.get("tree", [])
        
        for item in items:
            if item.get("type") != "blob":
                continue
                
            path = item.get("path", "")
            stats.files_scanned += 1
            
            if subpath and not path.startswith(subpath + "/"):
                if path != subpath:
                    stats.files_skipped += 1
                    continue
                
            size = item.get("size", 0)
            if size > request.max_file_size_bytes:
                stats.files_skipped += 1
                continue
                
            if not self._should_include(path, request.include_patterns, request.exclude_patterns):
                stats.files_skipped += 1
                continue
                
            # Fetch content via raw URL for speed and simplicity
            content, is_binary = self._fetch_raw(owner, repo, active_ref, path, request.auth_token)
            if content is not None:
                manifest.append(FileManifestItem(
                    path=path,
                    size_bytes=size,
                    content=content,
                    binary=is_binary
                ))
                stats.files_ingested += 1
                stats.bytes_ingested += size
            elif is_binary:
                # Keep it in manifest but signify it's binary with no text content
                manifest.append(FileManifestItem(
                    path=path,
                    size_bytes=size,
                    content=None,
                    binary=True
                ))
                stats.files_ingested += 1
                stats.bytes_ingested += size
            else:
                stats.files_skipped += 1
                errors.append(CrawlerError(
                    code="RAW_FETCH_ERROR",
                    message=f"Failed to fetch content for raw file {path}"
                ))

        stats.duration_ms = (time.perf_counter() - start_time) * 1000
        
        return CrawlerResult(
            success=len(errors) == 0 or len(manifest) > 0,
            manifest=manifest,
            stats=stats,
            errors=errors
        )

    def _fetch_raw(
        self, owner: str, repo: str, ref: str, path: str, token: Optional[str]
    ) -> Tuple[Optional[str], bool]:
        """Fetch raw file from GitHub. Returns (content, is_binary)."""
        url = f"https://raw.githubusercontent.com/{owner}/{repo}/{ref}/{path}"
        headers = {}
        if token:
            headers["Authorization"] = f"token {token}"
            
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code != 200:
            return None, False
            
        try:
            return resp.content.decode("utf-8"), False
        except UnicodeDecodeError:
            # It's a binary file
            return None, True

    def _build_error_result(self, code: str, response: requests.Response) -> CrawlerResult:
        """Helper to build a unified error result from an HTTP response."""
        msg = f"HTTP {response.status_code}: {response.text}"
        if response.status_code == 403 and "rate limit" in response.text.lower():
            code = "RATE_LIMIT_EXCEEDED"
            msg = "GitHub API rate limit exceeded."
        elif response.status_code == 404:
            code = "NOT_FOUND"
            msg = "Repository or reference not found (or requires auth)."
            
        return CrawlerResult(
            success=False,
            errors=[CrawlerError(code=code, message=msg)]
        )
