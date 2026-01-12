"""
Checkpoint - Snapshot and restore system for file changes.
"""

import json
import hashlib
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from pathlib import Path


@dataclass
class FileSnapshot:
    """Snapshot of a single file."""
    path: str
    content: str
    sha: Optional[str] = None
    size: int = 0
    
    def __post_init__(self):
        if not self.sha:
            self.sha = hashlib.sha256(self.content.encode()).hexdigest()[:40]
        if not self.size:
            self.size = len(self.content)
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> "FileSnapshot":
        return cls(**data)


@dataclass
class Checkpoint:
    """
    A checkpoint representing a snapshot of multiple files at a point in time.
    """
    id: str
    name: str
    description: str
    created_at: str
    files: Dict[str, FileSnapshot] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def create(
        cls,
        name: str,
        description: str = "",
        files: Optional[Dict[str, str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "Checkpoint":
        """
        Create a new checkpoint.
        
        Args:
            name: Checkpoint name.
            description: Optional description.
            files: Dict mapping file paths to contents.
            metadata: Additional metadata.
            
        Returns:
            New Checkpoint instance.
        """
        timestamp = datetime.utcnow().isoformat() + "Z"
        checkpoint_id = hashlib.sha256(
            f"{name}:{timestamp}".encode()
        ).hexdigest()[:12]
        
        file_snapshots = {}
        if files:
            for path, content in files.items():
                file_snapshots[path] = FileSnapshot(path=path, content=content)
        
        return cls(
            id=checkpoint_id,
            name=name,
            description=description,
            created_at=timestamp,
            files=file_snapshots,
            metadata=metadata or {},
        )
    
    def add_file(self, path: str, content: str) -> None:
        """Add or update a file in the checkpoint."""
        self.files[path] = FileSnapshot(path=path, content=content)
    
    def get_file(self, path: str) -> Optional[FileSnapshot]:
        """Get a file snapshot by path."""
        return self.files.get(path)
    
    def list_files(self) -> List[str]:
        """List all file paths in the checkpoint."""
        return list(self.files.keys())
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "created_at": self.created_at,
            "files": {path: snap.to_dict() for path, snap in self.files.items()},
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Checkpoint":
        """Create from dictionary."""
        files = {
            path: FileSnapshot.from_dict(snap_data)
            for path, snap_data in data.get("files", {}).items()
        }
        return cls(
            id=data["id"],
            name=data["name"],
            description=data.get("description", ""),
            created_at=data["created_at"],
            files=files,
            metadata=data.get("metadata", {}),
        )
    
    def __repr__(self) -> str:
        return f"Checkpoint({self.id[:8]}, name={self.name}, files={len(self.files)})"


class CheckpointManager:
    """
    Manages checkpoints for a repository or workspace.
    
    Provides functionality to:
    - Create checkpoints (snapshots)
    - List available checkpoints
    - Restore to a previous checkpoint
    - Compare checkpoints
    - Delete old checkpoints
    """
    
    def __init__(self, max_checkpoints: int = 50):
        """
        Initialize CheckpointManager.
        
        Args:
            max_checkpoints: Maximum number of checkpoints to keep.
        """
        self.max_checkpoints = max_checkpoints
        self._checkpoints: Dict[str, Checkpoint] = {}
        self._checkpoint_order: List[str] = []  # Oldest to newest
        self._current_state: Dict[str, str] = {}  # path -> content
    
    def create_checkpoint(
        self,
        name: str,
        description: str = "",
        files: Optional[Dict[str, str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Checkpoint:
        """
        Create a new checkpoint from current state or provided files.
        
        Args:
            name: Checkpoint name.
            description: Optional description.
            files: Files to snapshot. If None, uses current state.
            metadata: Additional metadata.
            
        Returns:
            Created Checkpoint.
        """
        # Use provided files or current state
        snapshot_files = files if files is not None else self._current_state.copy()
        
        checkpoint = Checkpoint.create(
            name=name,
            description=description,
            files=snapshot_files,
            metadata=metadata,
        )
        
        # Add to storage
        self._checkpoints[checkpoint.id] = checkpoint
        self._checkpoint_order.append(checkpoint.id)
        
        # Enforce max checkpoints
        self._enforce_max_checkpoints()
        
        return checkpoint
    
    def get_checkpoint(self, checkpoint_id: str) -> Optional[Checkpoint]:
        """Get a checkpoint by ID."""
        return self._checkpoints.get(checkpoint_id)
    
    def get_checkpoint_by_name(self, name: str) -> Optional[Checkpoint]:
        """Get the most recent checkpoint with a given name."""
        for cp_id in reversed(self._checkpoint_order):
            cp = self._checkpoints.get(cp_id)
            if cp and cp.name == name:
                return cp
        return None
    
    def list_checkpoints(self) -> List[Checkpoint]:
        """List all checkpoints (newest first)."""
        return [
            self._checkpoints[cp_id]
            for cp_id in reversed(self._checkpoint_order)
            if cp_id in self._checkpoints
        ]
    
    def restore_checkpoint(
        self,
        checkpoint_id: str,
        paths: Optional[List[str]] = None,
    ) -> Dict[str, str]:
        """
        Restore files from a checkpoint.
        
        Args:
            checkpoint_id: Checkpoint ID to restore from.
            paths: Specific paths to restore. If None, restores all.
            
        Returns:
            Dict mapping paths to restored content.
        """
        checkpoint = self._checkpoints.get(checkpoint_id)
        if not checkpoint:
            raise ValueError(f"Checkpoint not found: {checkpoint_id}")
        
        restored = {}
        files_to_restore = paths or checkpoint.list_files()
        
        for path in files_to_restore:
            snapshot = checkpoint.get_file(path)
            if snapshot:
                restored[path] = snapshot.content
                self._current_state[path] = snapshot.content
        
        return restored
    
    def restore_file(self, checkpoint_id: str, path: str) -> Optional[str]:
        """
        Restore a single file from a checkpoint.
        
        Args:
            checkpoint_id: Checkpoint ID.
            path: File path to restore.
            
        Returns:
            File content or None if not found.
        """
        checkpoint = self._checkpoints.get(checkpoint_id)
        if not checkpoint:
            return None
        
        snapshot = checkpoint.get_file(path)
        if snapshot:
            self._current_state[path] = snapshot.content
            return snapshot.content
        
        return None
    
    def diff_checkpoint(
        self,
        checkpoint_id: str,
        current_files: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Dict[str, Any]]:
        """
        Compare checkpoint with current state.
        
        Args:
            checkpoint_id: Checkpoint ID to compare.
            current_files: Current file contents. If None, uses internal state.
            
        Returns:
            Dict with changes: {path: {status, old_content, new_content}}
        """
        checkpoint = self._checkpoints.get(checkpoint_id)
        if not checkpoint:
            raise ValueError(f"Checkpoint not found: {checkpoint_id}")
        
        current = current_files if current_files is not None else self._current_state
        diff = {}
        
        # Check for modified and deleted files
        for path, snapshot in checkpoint.files.items():
            if path in current:
                if current[path] != snapshot.content:
                    diff[path] = {
                        "status": "modified",
                        "old_content": snapshot.content,
                        "new_content": current[path],
                    }
            else:
                diff[path] = {
                    "status": "deleted",
                    "old_content": snapshot.content,
                    "new_content": None,
                }
        
        # Check for new files
        for path, content in current.items():
            if path not in checkpoint.files:
                diff[path] = {
                    "status": "added",
                    "old_content": None,
                    "new_content": content,
                }
        
        return diff
    
    def delete_checkpoint(self, checkpoint_id: str) -> bool:
        """Delete a checkpoint."""
        if checkpoint_id in self._checkpoints:
            del self._checkpoints[checkpoint_id]
            self._checkpoint_order.remove(checkpoint_id)
            return True
        return False
    
    def update_current_state(self, path: str, content: str) -> None:
        """Update the current state for a file."""
        self._current_state[path] = content
    
    def remove_from_current_state(self, path: str) -> None:
        """Remove a file from current state."""
        self._current_state.pop(path, None)
    
    def get_file_history(self, path: str) -> List[Dict[str, Any]]:
        """
        Get history of a file across all checkpoints.
        
        Args:
            path: File path.
            
        Returns:
            List of dicts with checkpoint info and content.
        """
        history = []
        
        for cp_id in self._checkpoint_order:
            checkpoint = self._checkpoints.get(cp_id)
            if checkpoint:
                snapshot = checkpoint.get_file(path)
                if snapshot:
                    history.append({
                        "checkpoint_id": checkpoint.id,
                        "checkpoint_name": checkpoint.name,
                        "created_at": checkpoint.created_at,
                        "content": snapshot.content,
                        "sha": snapshot.sha,
                        "size": snapshot.size,
                    })
        
        return history
    
    def _enforce_max_checkpoints(self) -> None:
        """Remove oldest checkpoints if over limit."""
        while len(self._checkpoint_order) > self.max_checkpoints:
            oldest_id = self._checkpoint_order.pop(0)
            self._checkpoints.pop(oldest_id, None)
    
    def to_json(self) -> str:
        """Serialize to JSON."""
        data = {
            "checkpoints": {
                cp_id: cp.to_dict()
                for cp_id, cp in self._checkpoints.items()
            },
            "order": self._checkpoint_order,
            "current_state": self._current_state,
        }
        return json.dumps(data, indent=2)
    
    @classmethod
    def from_json(cls, json_str: str, max_checkpoints: int = 50) -> "CheckpointManager":
        """Deserialize from JSON."""
        data = json.loads(json_str)
        
        manager = cls(max_checkpoints=max_checkpoints)
        manager._checkpoint_order = data.get("order", [])
        manager._current_state = data.get("current_state", {})
        
        for cp_id, cp_data in data.get("checkpoints", {}).items():
            manager._checkpoints[cp_id] = Checkpoint.from_dict(cp_data)
        
        return manager
    
    def save_to_file(self, path: str) -> None:
        """Save checkpoints to a file."""
        Path(path).write_text(self.to_json())
    
    @classmethod
    def load_from_file(cls, path: str, max_checkpoints: int = 50) -> "CheckpointManager":
        """Load checkpoints from a file."""
        json_str = Path(path).read_text()
        return cls.from_json(json_str, max_checkpoints)
    
    @property
    def checkpoint_count(self) -> int:
        """Number of checkpoints."""
        return len(self._checkpoints)
    
    def __len__(self) -> int:
        return self.checkpoint_count
