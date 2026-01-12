"""
Repository - Represents a mounted GitHub repository.
"""

import base64
import requests
from typing import TYPE_CHECKING, Dict, List, Optional, Any
from pathlib import PurePosixPath
from .file_node import FileNode, DirectoryNode

if TYPE_CHECKING:
    from .github_fs import GitHubFS
    from .cache import Cache


class Repository:
    """
    Represents a mounted GitHub repository with filesystem operations.
    """
    
    def __init__(
        self,
        path: str,
        fs: "GitHubFS",
        branch: Optional[str] = None,
        cache: Optional["Cache"] = None,
    ):
        """
        Initialize Repository.
        
        Args:
            path: Repository path (owner/repo).
            fs: Parent GitHubFS instance.
            branch: Branch name. If None, uses default branch.
            cache: Cache instance for API responses.
        """
        self.path = path
        self._fs = fs
        self._cache = cache
        self._staged_changes: Dict[str, str] = {}
        
        # Parse owner and repo
        parts = path.split("/")
        if len(parts) != 2:
            raise ValueError(f"Invalid repository path: {path}. Expected 'owner/repo'.")
        self.owner, self.name = parts
        
        # Get default branch if not specified
        self._branch = branch or self._get_default_branch()
    
    @property
    def branch(self) -> str:
        """Current branch name."""
        return self._branch
    
    def _api_url(self, endpoint: str) -> str:
        """Build API URL for endpoint."""
        return f"{self._fs.api_url}/repos/{self.path}/{endpoint}"
    
    def _request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """Make API request."""
        url = self._api_url(endpoint)
        response = requests.request(
            method,
            url,
            headers=self._fs.headers,
            **kwargs,
        )
        response.raise_for_status()
        return response
    
    def _get_default_branch(self) -> str:
        """Get the default branch name."""
        cache_key = f"default_branch:{self.path}"
        if self._cache:
            cached = self._cache.get(cache_key)
            if cached:
                return cached
        
        response = self._request("GET", "")
        branch = response.json().get("default_branch", "main")
        
        if self._cache:
            self._cache.set(cache_key, branch)
        
        return branch
    
    def listdir(self, path: str = "/") -> List[str]:
        """
        List directory contents.
        
        Args:
            path: Directory path (relative to repo root).
            
        Returns:
            List of file/directory names.
        """
        path = self._normalize_path(path)
        cache_key = f"listdir:{self.path}:{self._branch}:{path}"
        
        if self._cache:
            cached = self._cache.get(cache_key)
            if cached:
                return cached
        
        endpoint = f"contents/{path}" if path else "contents"
        response = self._request("GET", endpoint, params={"ref": self._branch})
        
        contents = response.json()
        if not isinstance(contents, list):
            raise NotADirectoryError(f"Not a directory: {path}")
        
        names = [item["name"] for item in contents]
        
        if self._cache:
            self._cache.set(cache_key, names)
        
        return names
    
    def read(self, path: str) -> str:
        """
        Read file contents.
        
        Args:
            path: File path (relative to repo root).
            
        Returns:
            File contents as string.
        """
        path = self._normalize_path(path)
        cache_key = f"read:{self.path}:{self._branch}:{path}"
        
        if self._cache:
            cached = self._cache.get(cache_key)
            if cached:
                return cached
        
        response = self._request("GET", f"contents/{path}", params={"ref": self._branch})
        data = response.json()
        
        if data.get("type") != "file":
            raise IsADirectoryError(f"Is a directory: {path}")
        
        content = base64.b64decode(data["content"]).decode("utf-8")
        
        if self._cache:
            self._cache.set(cache_key, content)
        
        return content
    
    def read_binary(self, path: str) -> bytes:
        """
        Read file contents as bytes.
        
        Args:
            path: File path (relative to repo root).
            
        Returns:
            File contents as bytes.
        """
        path = self._normalize_path(path)
        response = self._request("GET", f"contents/{path}", params={"ref": self._branch})
        data = response.json()
        
        if data.get("type") != "file":
            raise IsADirectoryError(f"Is a directory: {path}")
        
        return base64.b64decode(data["content"])
    
    def write(self, path: str, content: str, message: Optional[str] = None) -> None:
        """
        Write file contents (stages for commit).
        
        Args:
            path: File path (relative to repo root).
            content: File contents.
            message: Commit message (if auto-commit enabled).
        """
        path = self._normalize_path(path)
        self._staged_changes[path] = content
        
        # Invalidate cache
        if self._cache:
            self._cache.invalidate(f"read:{self.path}:{self._branch}:{path}")
            parent = str(PurePosixPath(path).parent)
            self._cache.invalidate(f"listdir:{self.path}:{self._branch}:{parent}")
    
    def commit(self, message: str) -> str:
        """
        Commit staged changes.
        
        Args:
            message: Commit message.
            
        Returns:
            Commit SHA.
        """
        if not self._staged_changes:
            raise ValueError("No staged changes to commit")
        
        # Get current tree
        ref_response = self._request("GET", f"git/ref/heads/{self._branch}")
        current_sha = ref_response.json()["object"]["sha"]
        
        # Create blobs for each file
        tree_items = []
        for path, content in self._staged_changes.items():
            blob_response = self._request(
                "POST",
                "git/blobs",
                json={"content": content, "encoding": "utf-8"},
            )
            blob_sha = blob_response.json()["sha"]
            tree_items.append({
                "path": path,
                "mode": "100644",
                "type": "blob",
                "sha": blob_sha,
            })
        
        # Create tree
        tree_response = self._request(
            "POST",
            "git/trees",
            json={"base_tree": current_sha, "tree": tree_items},
        )
        tree_sha = tree_response.json()["sha"]
        
        # Create commit
        commit_response = self._request(
            "POST",
            "git/commits",
            json={
                "message": message,
                "tree": tree_sha,
                "parents": [current_sha],
            },
        )
        commit_sha = commit_response.json()["sha"]
        
        # Update ref
        self._request(
            "PATCH",
            f"git/refs/heads/{self._branch}",
            json={"sha": commit_sha},
        )
        
        # Clear staged changes
        self._staged_changes.clear()
        
        return commit_sha
    
    def exists(self, path: str) -> bool:
        """Check if path exists."""
        try:
            self._get_content_info(path)
            return True
        except:
            return False
    
    def is_file(self, path: str) -> bool:
        """Check if path is a file."""
        try:
            info = self._get_content_info(path)
            return info.get("type") == "file"
        except:
            return False
    
    def is_dir(self, path: str) -> bool:
        """Check if path is a directory."""
        try:
            info = self._get_content_info(path)
            return info.get("type") == "dir"
        except:
            return False
    
    def _get_content_info(self, path: str) -> Dict[str, Any]:
        """Get content info for path."""
        path = self._normalize_path(path)
        response = self._request("GET", f"contents/{path}", params={"ref": self._branch})
        return response.json()
    
    def checkout(self, branch: str) -> None:
        """
        Switch to a different branch.
        
        Args:
            branch: Branch name.
        """
        if self._staged_changes:
            raise RuntimeError("Cannot switch branches with uncommitted changes")
        
        self._branch = branch
        
        # Clear cache for this repo
        if self._cache:
            self._cache.invalidate_prefix(f"*:{self.path}:{self._branch}:")
    
    def get_tree(self, path: str = "/", recursive: bool = False) -> DirectoryNode:
        """
        Get directory tree.
        
        Args:
            path: Root path for tree.
            recursive: Include subdirectories recursively.
            
        Returns:
            DirectoryNode representing the tree.
        """
        path = self._normalize_path(path)
        endpoint = f"contents/{path}" if path else "contents"
        response = self._request("GET", endpoint, params={"ref": self._branch})
        
        contents = response.json()
        if not isinstance(contents, list):
            raise NotADirectoryError(f"Not a directory: {path}")
        
        root = DirectoryNode(name=path or "/", path=path or "/")
        
        for item in contents:
            if item["type"] == "file":
                root.add_child(FileNode(
                    name=item["name"],
                    path=item["path"],
                    size=item["size"],
                    sha=item["sha"],
                ))
            elif item["type"] == "dir":
                if recursive:
                    subdir = self.get_tree(item["path"], recursive=True)
                    root.add_child(subdir)
                else:
                    root.add_child(DirectoryNode(
                        name=item["name"],
                        path=item["path"],
                    ))
        
        return root
    
    @staticmethod
    def _normalize_path(path: str) -> str:
        """Normalize path (remove leading/trailing slashes)."""
        return path.strip("/")
