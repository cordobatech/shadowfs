"""
ShadowFS - Virtual filesystem overlay for GitHub repositories.
"""

from .github_fs import GitHubFS
from .repository import Repository
from .file_node import FileNode, DirectoryNode
from .cache import Cache

__version__ = "0.1.0"
__all__ = ["GitHubFS", "Repository", "FileNode", "DirectoryNode", "Cache"]
