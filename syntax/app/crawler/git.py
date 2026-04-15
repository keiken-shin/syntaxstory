import fnmatch
import os
import tempfile
import time
from typing import List, Optional, Tuple
from urllib.parse import urlparse

import git
from git.exc import GitCommandError

from app.crawler.base import CrawlerStrategy
from app.crawler.models import (
    CrawlerError,
    CrawlerRequest,
    CrawlerResult,
    CrawlerStats,
    FileManifestItem,
)


class GitCloneCrawlerStrategy(CrawlerStrategy):
    """
    Crawler implementation that clones a git repository to a temporary directory
    and walks its local filesystem (good for private repos or non-GitHub hosts).
    """

    def can_handle(self, request: CrawlerRequest) -> bool:
        """
        Can handle typical git SSH urls or standard HTTPs paths.
        Since this is the general fallback, it returns True for Git URLs.
        """
        url = request.url.lower()
        return url.startswith("http") or url.startswith("git@") or url.endswith(".git")

    def _should_include(
        self, path: str, include_patterns: List[str], exclude_patterns: List[str]
    ) -> bool:
        """
        Determine if the given relative path meets inclusion and exclusion criteria.
        Checks both filename and full path. Automatically excludes .git folder contents.
        """
        if ".git/" in path or path.startswith(".git") or "/.git/" in path:
            return False

        filename = os.path.basename(path)
        
        include = True
        if include_patterns:
            include = False
            for pat in include_patterns:
                if fnmatch.fnmatch(filename, pat) or fnmatch.fnmatch(path, pat):
                    include = True
                    break
            
        if include and exclude_patterns:
            for pat in exclude_patterns:
                if fnmatch.fnmatch(filename, pat) or fnmatch.fnmatch(path, pat):
                    return False
                
        return include

    def _inject_token(self, url: str, token: Optional[str]) -> str:
        """Inject auth token into HTTPS URLs for cloning."""
        if not url.startswith("http") or not token:
            return url
        
        parsed = urlparse(url)
        # Avoid double-injecting if already has credentials
        if parsed.username or parsed.password:
            return url
            
        # e.g., https://<token>@github.com/owner/repo.git
        new_netloc = f"{token}@{parsed.netloc}"
        return parsed._replace(netloc=new_netloc).geturl()

    def crawl(self, request: CrawlerRequest) -> CrawlerResult:
        start_time = time.perf_counter()
        manifest: List[FileManifestItem] = []
        stats = CrawlerStats()
        errors: List[CrawlerError] = []

        url_to_clone = self._inject_token(request.url, request.auth_token)

        # Temporary directory for the cloned repository
        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                # Perform the git clone
                # Use depth=1 if no specific commit/branch is required for speed
                clone_kwargs = {}
                if not request.branch_or_commit:
                    clone_kwargs["depth"] = 1

                repo = git.Repo.clone_from(url_to_clone, tmpdir, **clone_kwargs)
                
                if request.branch_or_commit:
                    try:
                        repo.git.checkout(request.branch_or_commit)
                    except GitCommandError as e:
                        return CrawlerResult(
                            success=False,
                            errors=[CrawlerError(
                                code="CHECKOUT_ERROR",
                                message=f"Failed to checkout '{request.branch_or_commit}'. Details: {str(e)}"
                            )]
                        )
                        
                # Walk the local directory
                for root, dirs, filenames in os.walk(tmpdir):
                    # Prune .git from the traversal early
                    if ".git" in dirs:
                        dirs.remove(".git")

                    for filename in filenames:
                        abs_path = os.path.join(root, filename)
                        rel_path = os.path.relpath(abs_path, tmpdir)
                        # Normalize slashes for manifest paths
                        rel_path = rel_path.replace(os.sep, "/")

                        stats.files_scanned += 1

                        if not self._should_include(rel_path, request.include_patterns, request.exclude_patterns):
                            stats.files_skipped += 1
                            continue

                        # Check size
                        try:
                            file_size = os.path.getsize(abs_path)
                            if file_size > request.max_file_size_bytes:
                                stats.files_skipped += 1
                                continue
                                
                            # Read content
                            content, is_binary = self._read_file(abs_path)
                            
                            manifest.append(FileManifestItem(
                                path=rel_path,
                                size_bytes=file_size,
                                content=content,
                                binary=is_binary
                            ))
                            stats.files_ingested += 1
                            stats.bytes_ingested += file_size
                            
                        except OSError as e:
                            stats.files_skipped += 1
                            errors.append(CrawlerError(
                                code="LOCAL_READ_ERROR",
                                message=f"Failed to access file {rel_path}: {e}"
                            ))

            except GitCommandError as e:
                # Handle common git errors cleanly
                msg = str(e)
                code = "CLONE_ERROR"
                
                if "could not read Username" in msg or "Authentication failed" in msg or "Invalid username or password" in msg:
                    code = "AUTH_FAILED"
                elif "not found" in msg.lower():
                    code = "NOT_FOUND"

                return CrawlerResult(
                    success=False,
                    errors=[CrawlerError(code=code, message=msg)]
                )
            except Exception as e:
                return CrawlerResult(
                    success=False,
                    errors=[CrawlerError(code="UNKNOWN_ERROR", message=str(e))]
                )

        stats.duration_ms = (time.perf_counter() - start_time) * 1000

        return CrawlerResult(
            success=len(errors) == 0 or len(manifest) > 0,
            manifest=manifest,
            stats=stats,
            errors=errors
        )

    def _read_file(self, abs_path: str) -> Tuple[Optional[str], bool]:
        """Reads a local file. Determines if it's text or binary. Returns (content, is_binary)."""
        try:
            with open(abs_path, 'r', encoding='utf-8') as f:
                content = f.read()
                return content, False
        except UnicodeDecodeError:
            # It's a binary file (e.g., image, compiled binary), skip reading text
            return None, True
