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
from .models import (
    ModelConfig,
    ModelProvider,
    ModelSelector,
    get_model_selector,
    get_model,
    set_model,
    show_models,
    select_model,
    BUILTIN_MODELS,
)

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
    # Model selector (like GitHub Copilot)
    "ModelConfig",
    "ModelProvider",
    "ModelSelector",
    "get_model_selector",
    "get_model",
    "set_model",
    "show_models",
    "select_model",
    "BUILTIN_MODELS",
]
