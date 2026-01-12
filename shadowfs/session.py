"""
Session - Automatic checkpoint management for LLM interactions.
Similar to GitHub Copilot's restore functionality in the GUI.
"""

import os
import time
import functools
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, field
from pathlib import Path
from contextlib import contextmanager

from .checkpoint import Checkpoint, CheckpointManager, FileSnapshot


@dataclass
class LLMCall:
    """Represents an LLM call with its checkpoint."""
    id: str
    checkpoint_id: str
    model: str
    prompt_preview: str
    timestamp: str
    status: str = "pending"  # pending, completed, failed, restored
    response_preview: Optional[str] = None
    files_modified: List[str] = field(default_factory=list)
    duration_ms: Optional[int] = None
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "checkpoint_id": self.checkpoint_id,
            "model": self.model,
            "prompt_preview": self.prompt_preview,
            "timestamp": self.timestamp,
            "status": self.status,
            "response_preview": self.response_preview,
            "files_modified": self.files_modified,
            "duration_ms": self.duration_ms,
        }


class Session:
    """
    Manages a coding session with automatic checkpoints before LLM calls.
    
    Similar to GitHub Copilot's checkpoint/restore GUI:
    - Automatically creates restore points before each LLM interaction
    - Shows timeline of changes
    - Allows restoring to any previous state
    
    Usage:
        session = Session(workspace_path="/path/to/project")
        
        # Auto-checkpoint before LLM call
        with session.llm_call("gpt-4", "Refactor this function"):
            # Your LLM interaction here
            response = call_llm(...)
            session.track_file("src/app.py")
        
        # Or use decorator
        @session.auto_checkpoint
        def my_llm_function():
            ...
        
        # View history (like Copilot GUI)
        session.show_history()
        
        # Restore to before a specific call
        session.restore_before_call(call_id)
    """
    
    def __init__(
        self,
        workspace_path: Optional[str] = None,
        session_name: Optional[str] = None,
        auto_track_extensions: Optional[List[str]] = None,
        max_checkpoints: int = 100,
    ):
        """
        Initialize a session.
        
        Args:
            workspace_path: Root path of the workspace to track.
            session_name: Name for this session.
            auto_track_extensions: File extensions to auto-track (e.g., ['.py', '.js']).
            max_checkpoints: Maximum number of checkpoints to keep.
        """
        self.workspace_path = Path(workspace_path) if workspace_path else Path.cwd()
        self.session_name = session_name or f"session-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        self.auto_track_extensions = auto_track_extensions or ['.py', '.js', '.ts', '.jsx', '.tsx', '.md', '.yaml', '.yml', '.json']
        
        self._checkpoint_manager = CheckpointManager(max_checkpoints=max_checkpoints)
        self._llm_calls: List[LLMCall] = []
        self._call_counter = 0
        self._tracked_files: Dict[str, str] = {}  # path -> content
        self._current_call: Optional[LLMCall] = None
        
        # Load workspace files
        self._scan_workspace()
    
    def _scan_workspace(self) -> None:
        """Scan workspace for trackable files."""
        if not self.workspace_path.exists():
            return
        
        for ext in self.auto_track_extensions:
            for filepath in self.workspace_path.rglob(f"*{ext}"):
                # Skip common ignore patterns
                path_str = str(filepath)
                if any(ignore in path_str for ignore in [
                    'node_modules', '__pycache__', '.git', 'venv', 
                    '.env', 'dist', 'build', '.next'
                ]):
                    continue
                
                try:
                    rel_path = str(filepath.relative_to(self.workspace_path))
                    content = filepath.read_text(encoding='utf-8', errors='ignore')
                    self._tracked_files[rel_path] = content
                except Exception:
                    pass
    
    def _generate_call_id(self) -> str:
        """Generate unique call ID."""
        self._call_counter += 1
        return f"call-{self._call_counter:04d}"
    
    def track_file(self, path: str, content: Optional[str] = None) -> None:
        """
        Track a file for checkpoint management.
        
        Args:
            path: File path (relative to workspace or absolute).
            content: File content. If None, reads from disk.
        """
        if content is None:
            filepath = Path(path)
            if not filepath.is_absolute():
                filepath = self.workspace_path / path
            content = filepath.read_text(encoding='utf-8')
        
        rel_path = path
        if Path(path).is_absolute():
            try:
                rel_path = str(Path(path).relative_to(self.workspace_path))
            except ValueError:
                rel_path = path
        
        self._tracked_files[rel_path] = content
        self._checkpoint_manager.update_current_state(rel_path, content)
        
        if self._current_call and rel_path not in self._current_call.files_modified:
            self._current_call.files_modified.append(rel_path)
    
    def track_files(self, paths: List[str]) -> None:
        """Track multiple files."""
        for path in paths:
            self.track_file(path)
    
    @contextmanager
    def llm_call(
        self,
        model: str = "unknown",
        prompt: str = "",
        description: Optional[str] = None,
    ):
        """
        Context manager for LLM calls with automatic checkpoint.
        
        Creates a checkpoint before the LLM call, similar to
        GitHub Copilot's restore points.
        
        Args:
            model: LLM model name.
            prompt: The prompt being sent.
            description: Optional description for the checkpoint.
            
        Usage:
            with session.llm_call("gpt-4", "Refactor function"):
                response = my_llm_api(prompt)
                session.track_file("modified.py")
        """
        call_id = self._generate_call_id()
        timestamp = datetime.utcnow().isoformat() + "Z"
        
        # Create checkpoint BEFORE the LLM call
        checkpoint_name = description or f"Before {model} call"
        checkpoint = self._checkpoint_manager.create_checkpoint(
            name=checkpoint_name,
            description=f"Auto-checkpoint before LLM call: {prompt[:100]}...",
            files=self._tracked_files.copy(),
            metadata={
                "call_id": call_id,
                "model": model,
                "type": "pre-llm-call",
            },
        )
        
        # Create LLM call record
        llm_call = LLMCall(
            id=call_id,
            checkpoint_id=checkpoint.id,
            model=model,
            prompt_preview=prompt[:200] + ("..." if len(prompt) > 200 else ""),
            timestamp=timestamp,
            status="pending",
        )
        
        self._llm_calls.append(llm_call)
        self._current_call = llm_call
        
        start_time = time.time()
        
        try:
            yield llm_call
            llm_call.status = "completed"
        except Exception as e:
            llm_call.status = "failed"
            raise
        finally:
            llm_call.duration_ms = int((time.time() - start_time) * 1000)
            self._current_call = None
    
    def auto_checkpoint(self, model: str = "unknown"):
        """
        Decorator for automatic checkpointing before LLM calls.
        
        Usage:
            @session.auto_checkpoint("gpt-4")
            def call_gpt(prompt):
                return openai.chat(prompt)
        """
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                # Try to extract prompt from args/kwargs
                prompt = ""
                if args:
                    prompt = str(args[0])[:200]
                elif "prompt" in kwargs:
                    prompt = str(kwargs["prompt"])[:200]
                elif "messages" in kwargs:
                    prompt = str(kwargs["messages"])[:200]
                
                with self.llm_call(model, prompt):
                    return func(*args, **kwargs)
            return wrapper
        return decorator
    
    def get_history(self) -> List[LLMCall]:
        """Get all LLM calls (newest first)."""
        return list(reversed(self._llm_calls))
    
    def get_call(self, call_id: str) -> Optional[LLMCall]:
        """Get an LLM call by ID."""
        for call in self._llm_calls:
            if call.id == call_id:
                return call
        return None
    
    def restore_before_call(
        self,
        call_id: str,
        paths: Optional[List[str]] = None,
        write_to_disk: bool = True,
    ) -> Dict[str, str]:
        """
        Restore files to state before an LLM call.
        
        Args:
            call_id: The LLM call ID to restore before.
            paths: Specific paths to restore. If None, restores all.
            write_to_disk: Whether to write restored files to disk.
            
        Returns:
            Dict mapping paths to restored content.
        """
        call = self.get_call(call_id)
        if not call:
            raise ValueError(f"Call not found: {call_id}")
        
        restored = self._checkpoint_manager.restore_checkpoint(
            call.checkpoint_id,
            paths,
        )
        
        if write_to_disk:
            for path, content in restored.items():
                filepath = self.workspace_path / path
                filepath.parent.mkdir(parents=True, exist_ok=True)
                filepath.write_text(content, encoding='utf-8')
        
        # Mark the call as restored
        call.status = "restored"
        
        # Update tracked files
        self._tracked_files.update(restored)
        
        return restored
    
    def restore_latest(self, write_to_disk: bool = True) -> Dict[str, str]:
        """Restore to state before the most recent LLM call."""
        if not self._llm_calls:
            raise ValueError("No LLM calls to restore from")
        
        return self.restore_before_call(
            self._llm_calls[-1].id,
            write_to_disk=write_to_disk,
        )
    
    def show_history(self, limit: int = 10) -> str:
        """
        Generate a visual history display (like Copilot GUI).
        
        Returns formatted string showing checkpoint history.
        """
        lines = []
        lines.append("")
        lines.append("╔══════════════════════════════════════════════════════════════════╗")
        lines.append("║                    🔄 Session History                            ║")
        lines.append("║              (Restore to any checkpoint below)                   ║")
        lines.append("╠══════════════════════════════════════════════════════════════════╣")
        
        if not self._llm_calls:
            lines.append("║  No LLM calls recorded yet.                                     ║")
            lines.append("╚══════════════════════════════════════════════════════════════════╝")
            return "\n".join(lines)
        
        history = self.get_history()[:limit]
        
        for i, call in enumerate(history):
            # Status indicator
            status_icon = {
                "completed": "✅",
                "failed": "❌",
                "pending": "⏳",
                "restored": "↩️",
            }.get(call.status, "❓")
            
            # Time formatting
            try:
                dt = datetime.fromisoformat(call.timestamp.replace("Z", "+00:00"))
                time_str = dt.strftime("%H:%M:%S")
            except:
                time_str = call.timestamp[:8]
            
            # Files indicator
            files_str = f"{len(call.files_modified)} files" if call.files_modified else "no files"
            
            # Duration
            duration_str = f"{call.duration_ms}ms" if call.duration_ms else ""
            
            lines.append("║                                                                  ║")
            lines.append(f"║  {status_icon} [{call.id}] {call.model:<12} @ {time_str}              ║")
            lines.append(f"║     📝 {call.prompt_preview[:45]:<45} ║")
            lines.append(f"║     📁 {files_str:<20} {duration_str:<10}                   ║")
            
            if i < len(history) - 1:
                lines.append("║  ────────────────────────────────────────────────────────────  ║")
        
        lines.append("║                                                                  ║")
        lines.append("╠══════════════════════════════════════════════════════════════════╣")
        lines.append("║  💡 Use session.restore_before_call('call-XXXX') to restore     ║")
        lines.append("╚══════════════════════════════════════════════════════════════════╝")
        
        return "\n".join(lines)
    
    def show_diff_since_call(self, call_id: str) -> str:
        """Show what changed since an LLM call."""
        call = self.get_call(call_id)
        if not call:
            raise ValueError(f"Call not found: {call_id}")
        
        diff = self._checkpoint_manager.diff_checkpoint(
            call.checkpoint_id,
            self._tracked_files,
        )
        
        lines = []
        lines.append(f"\n📊 Changes since {call.id} ({call.model}):")
        lines.append("─" * 50)
        
        if not diff:
            lines.append("  No changes.")
            return "\n".join(lines)
        
        for path, change in sorted(diff.items()):
            status = change["status"]
            if status == "added":
                lines.append(f"  ➕ {path}")
            elif status == "deleted":
                lines.append(f"  ➖ {path}")
            elif status == "modified":
                old_lines = len(change["old_content"].splitlines())
                new_lines = len(change["new_content"].splitlines())
                lines.append(f"  ✏️  {path} ({old_lines} → {new_lines} lines)")
        
        return "\n".join(lines)
    
    @property
    def checkpoint_manager(self) -> CheckpointManager:
        """Access underlying checkpoint manager."""
        return self._checkpoint_manager
    
    @property
    def call_count(self) -> int:
        """Number of LLM calls in this session."""
        return len(self._llm_calls)
    
    def save(self, path: Optional[str] = None) -> None:
        """Save session to file."""
        import json
        
        save_path = path or str(self.workspace_path / ".shadowfs" / "session.json")
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            "session_name": self.session_name,
            "workspace_path": str(self.workspace_path),
            "llm_calls": [call.to_dict() for call in self._llm_calls],
            "checkpoints": self._checkpoint_manager.to_json(),
        }
        
        Path(save_path).write_text(json.dumps(data, indent=2))
    
    @classmethod
    def load(cls, path: str) -> "Session":
        """Load session from file."""
        import json
        
        data = json.loads(Path(path).read_text())
        
        session = cls(
            workspace_path=data["workspace_path"],
            session_name=data["session_name"],
        )
        
        session._checkpoint_manager = CheckpointManager.from_json(data["checkpoints"])
        
        for call_data in data["llm_calls"]:
            call = LLMCall(**call_data)
            session._llm_calls.append(call)
            session._call_counter = max(
                session._call_counter,
                int(call.id.split("-")[1])
            )
        
        return session


class AutoCheckpoint:
    """
    Global auto-checkpoint system for any LLM framework.
    
    Usage:
        # Initialize once
        auto_cp = AutoCheckpoint("/path/to/project")
        
        # Wrap any LLM call
        response = auto_cp.wrap(
            lambda: openai.chat.completions.create(...),
            model="gpt-4",
            prompt="your prompt"
        )
        
        # Or use as context manager
        with auto_cp.before_call("gpt-4", "prompt"):
            response = call_llm()
        
        # Show history
        print(auto_cp.history())
        
        # Restore
        auto_cp.restore()  # Latest
        auto_cp.restore("call-0001")  # Specific
    """
    
    _instance: Optional["AutoCheckpoint"] = None
    
    def __init__(self, workspace_path: Optional[str] = None):
        self.session = Session(workspace_path=workspace_path)
        AutoCheckpoint._instance = self
    
    @classmethod
    def get_instance(cls) -> "AutoCheckpoint":
        """Get or create global instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def wrap(
        self,
        func: Callable,
        model: str = "unknown",
        prompt: str = "",
    ) -> Any:
        """Wrap an LLM call with automatic checkpoint."""
        with self.session.llm_call(model, prompt):
            return func()
    
    @contextmanager
    def before_call(self, model: str = "unknown", prompt: str = ""):
        """Context manager for checkpointing before LLM call."""
        with self.session.llm_call(model, prompt) as call:
            yield call
    
    def track(self, path: str, content: Optional[str] = None) -> None:
        """Track a file."""
        self.session.track_file(path, content)
    
    def restore(self, call_id: Optional[str] = None) -> Dict[str, str]:
        """Restore to before an LLM call."""
        if call_id:
            return self.session.restore_before_call(call_id)
        return self.session.restore_latest()
    
    def history(self, limit: int = 10) -> str:
        """Get visual history."""
        return self.session.show_history(limit)
    
    def diff(self, call_id: str) -> str:
        """Show diff since a call."""
        return self.session.show_diff_since_call(call_id)


# Convenience function
def create_restore_point(
    name: str = "manual",
    files: Optional[Dict[str, str]] = None,
) -> str:
    """
    Create a manual restore point.
    
    Returns the checkpoint ID.
    """
    auto_cp = AutoCheckpoint.get_instance()
    
    if files:
        for path, content in files.items():
            auto_cp.track(path, content)
    
    cp = auto_cp.session.checkpoint_manager.create_checkpoint(
        name=name,
        description="Manual restore point",
        files=files or auto_cp.session._tracked_files.copy(),
    )
    
    return cp.id
