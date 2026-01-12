"""
GitHubFS - Main class for GitHub filesystem operations.
"""

import os
from typing import Dict, Optional, List
from .repository import Repository
from .cache import Cache


class GitHubFS:
    """
    Virtual filesystem interface for GitHub repositories.
    
    Example:
        >>> fs = GitHubFS(token="ghp_xxx")
        >>> repo = fs.mount("owner/repo")
        >>> files = repo.listdir("/")
    """
    
    def __init__(
        self,
        token: Optional[str] = None,
        api_url: str = "https://api.github.com",
        cache_enabled: bool = True,
        cache_ttl: int = 300,
    ):
        """
        Initialize GitHubFS.
        
        Args:
            token: GitHub personal access token. If None, reads from GITHUB_TOKEN env var.
            api_url: GitHub API URL (for GitHub Enterprise support).
            cache_enabled: Enable caching of API responses.
            cache_ttl: Cache time-to-live in seconds.
        """
        self.token = token or os.environ.get("GITHUB_TOKEN")
        self.api_url = api_url.rstrip("/")
        self._mounts: Dict[str, Repository] = {}
        self._cache = Cache(enabled=cache_enabled, ttl=cache_ttl) if cache_enabled else None
        
        if not self.token:
            raise ValueError(
                "GitHub token required. Provide via token parameter or GITHUB_TOKEN environment variable."
            )
    
    @property
    def headers(self) -> Dict[str, str]:
        """Get headers for GitHub API requests."""
        return {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github.v3+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
    
    def mount(self, repo_path: str, branch: Optional[str] = None) -> Repository:
        """
        Mount a GitHub repository.
        
        Args:
            repo_path: Repository path in format "owner/repo".
            branch: Branch to mount. If None, uses default branch.
            
        Returns:
            Repository object for filesystem operations.
        """
        if repo_path in self._mounts:
            return self._mounts[repo_path]
        
        repo = Repository(
            path=repo_path,
            branch=branch,
            fs=self,
            cache=self._cache,
        )
        self._mounts[repo_path] = repo
        return repo
    
    def unmount(self, repo_path: str) -> bool:
        """
        Unmount a repository.
        
        Args:
            repo_path: Repository path to unmount.
            
        Returns:
            True if unmounted, False if not mounted.
        """
        if repo_path in self._mounts:
            del self._mounts[repo_path]
            return True
        return False
    
    def list_mounts(self) -> List[str]:
        """
        List all mounted repositories.
        
        Returns:
            List of mounted repository paths.
        """
        return list(self._mounts.keys())
    
    def get_mount(self, repo_path: str) -> Optional[Repository]:
        """
        Get a mounted repository.
        
        Args:
            repo_path: Repository path.
            
        Returns:
            Repository object or None if not mounted.
        """
        return self._mounts.get(repo_path)
