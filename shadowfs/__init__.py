"""
ShadowFS - Virtual filesystem overlay for GitHub repositories.
"""

from .github_fs import GitHubFS
from .repository import Repository
from .file_node import FileNode, DirectoryNode
from .cache import Cache
from .checkpoint import Checkpoint, CheckpointManager, FileSnapshot
from .session import Session, AutoCheckpoint, LLMCall, create_restore_point
from .gui import CheckpointGUI, show_checkpoints, interactive_restore

__version__ = "0.1.0"
__all__ = [
    "GitHubFS",
    "Repository",
    "FileNode",
    "DirectoryNode",
    "Cache",
    "Checkpoint",
    "CheckpointManager",
    "FileSnapshot",
    # Session management (like GitHub Copilot)
    "Session",
    "AutoCheckpoint",
    "LLMCall",
    "create_restore_point",
    # GUI
    "CheckpointGUI",
    "show_checkpoints",
    "interactive_restore",
]
