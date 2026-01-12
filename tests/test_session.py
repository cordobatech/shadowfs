"""
Tests for the session module - automatic LLM checkpoint management.
"""

import pytest
from pathlib import Path
from shadowfs.session import Session, AutoCheckpoint, LLMCall, create_restore_point


class TestSession:
    """Tests for Session class."""
    
    def test_create_session(self, tmp_path):
        """Test creating a session."""
        session = Session(workspace_path=str(tmp_path))
        
        assert session.workspace_path == tmp_path
        assert session.call_count == 0
    
    def test_track_file(self, tmp_path):
        """Test tracking a file."""
        session = Session(workspace_path=str(tmp_path))
        
        # Create a test file
        test_file = tmp_path / "test.py"
        test_file.write_text("print('hello')")
        
        session.track_file(str(test_file))
        
        assert "test.py" in session._tracked_files
        assert session._tracked_files["test.py"] == "print('hello')"
    
    def test_track_file_with_content(self, tmp_path):
        """Test tracking a file with provided content."""
        session = Session(workspace_path=str(tmp_path))
        
        session.track_file("virtual.py", "# virtual file content")
        
        assert "virtual.py" in session._tracked_files
        assert session._tracked_files["virtual.py"] == "# virtual file content"
    
    def test_llm_call_context_manager(self, tmp_path):
        """Test LLM call context manager creates checkpoint."""
        session = Session(workspace_path=str(tmp_path))
        session.track_file("app.py", "original content")
        
        with session.llm_call("gpt-4", "Refactor code") as call:
            assert call.status == "pending"
            assert call.model == "gpt-4"
            session.track_file("app.py", "modified content")
        
        assert call.status == "completed"
        assert session.call_count == 1
        assert "app.py" in call.files_modified
    
    def test_llm_call_creates_checkpoint_before(self, tmp_path):
        """Test that checkpoint is created BEFORE llm call executes."""
        session = Session(workspace_path=str(tmp_path))
        session.track_file("app.py", "version 1")
        
        with session.llm_call("gpt-4", "Test"):
            # Checkpoint should have version 1
            pass
        
        # Change content
        session.track_file("app.py", "version 2")
        
        # Restore should get version 1
        call = session.get_history()[0]
        restored = session.restore_before_call(call.id, write_to_disk=False)
        
        assert restored["app.py"] == "version 1"
    
    def test_llm_call_failed_status(self, tmp_path):
        """Test that failed LLM calls are marked correctly."""
        session = Session(workspace_path=str(tmp_path))
        
        try:
            with session.llm_call("gpt-4", "Will fail"):
                raise RuntimeError("API Error")
        except RuntimeError:
            pass
        
        call = session.get_history()[0]
        assert call.status == "failed"
    
    def test_get_history(self, tmp_path):
        """Test getting call history (newest first)."""
        session = Session(workspace_path=str(tmp_path))
        
        with session.llm_call("model1", "First"):
            pass
        
        with session.llm_call("model2", "Second"):
            pass
        
        with session.llm_call("model3", "Third"):
            pass
        
        history = session.get_history()
        
        assert len(history) == 3
        assert history[0].model == "model3"
        assert history[2].model == "model1"
    
    def test_restore_before_call(self, tmp_path):
        """Test restoring to state before a call."""
        session = Session(workspace_path=str(tmp_path))
        
        # Initial state
        session.track_file("config.py", "DEBUG = False")
        
        with session.llm_call("gpt-4", "Enable debug"):
            session.track_file("config.py", "DEBUG = True")
        
        call = session.get_history()[0]
        restored = session.restore_before_call(call.id, write_to_disk=False)
        
        assert restored["config.py"] == "DEBUG = False"
        assert call.status == "restored"
    
    def test_restore_latest(self, tmp_path):
        """Test restoring to latest checkpoint."""
        session = Session(workspace_path=str(tmp_path))
        
        session.track_file("app.py", "original")
        
        with session.llm_call("gpt-4", "Modify"):
            session.track_file("app.py", "modified")
        
        restored = session.restore_latest(write_to_disk=False)
        
        assert restored["app.py"] == "original"
    
    def test_restore_writes_to_disk(self, tmp_path):
        """Test that restore writes files to disk."""
        session = Session(workspace_path=str(tmp_path))
        
        test_file = tmp_path / "test.py"
        test_file.write_text("original")
        session.track_file(str(test_file))
        
        with session.llm_call("gpt-4", "Modify"):
            test_file.write_text("modified")
            session.track_file(str(test_file))
        
        # Verify file was modified
        assert test_file.read_text() == "modified"
        
        # Restore
        session.restore_latest(write_to_disk=True)
        
        # Verify file was restored
        assert test_file.read_text() == "original"
    
    def test_show_history(self, tmp_path):
        """Test visual history output."""
        session = Session(workspace_path=str(tmp_path))
        
        with session.llm_call("gpt-4", "Test prompt"):
            pass
        
        output = session.show_history()
        
        assert "gpt-4" in output
        assert "call-0001" in output
    
    def test_show_diff_since_call(self, tmp_path):
        """Test diff output."""
        session = Session(workspace_path=str(tmp_path))
        
        session.track_file("a.py", "original")
        
        with session.llm_call("gpt-4", "Changes"):
            session.track_file("a.py", "modified")
            session.track_file("b.py", "new file")
        
        call = session.get_history()[0]
        diff = session.show_diff_since_call(call.id)
        
        assert "a.py" in diff
        assert "b.py" in diff
    
    def test_auto_checkpoint_decorator(self, tmp_path):
        """Test the auto_checkpoint decorator."""
        session = Session(workspace_path=str(tmp_path))
        
        @session.auto_checkpoint("claude-3")
        def my_llm_function(prompt):
            return f"Response to: {prompt}"
        
        result = my_llm_function("Hello")
        
        assert result == "Response to: Hello"
        assert session.call_count == 1
        
        call = session.get_history()[0]
        assert call.model == "claude-3"
    
    def test_session_save_load(self, tmp_path):
        """Test session persistence."""
        session = Session(workspace_path=str(tmp_path), session_name="test-session")
        session.track_file("test.py", "content")
        
        with session.llm_call("gpt-4", "Test"):
            pass
        
        save_path = tmp_path / "session.json"
        session.save(str(save_path))
        
        # Load
        loaded = Session.load(str(save_path))
        
        assert loaded.session_name == "test-session"
        assert loaded.call_count == 1
        
        call = loaded.get_history()[0]
        assert call.model == "gpt-4"


class TestAutoCheckpoint:
    """Tests for AutoCheckpoint class."""
    
    def test_singleton_pattern(self, tmp_path):
        """Test that AutoCheckpoint follows singleton pattern."""
        AutoCheckpoint._instance = None  # Reset singleton
        
        ac1 = AutoCheckpoint(str(tmp_path))
        ac2 = AutoCheckpoint.get_instance()
        
        assert ac1 is ac2
    
    def test_wrap_function(self, tmp_path):
        """Test wrapping an LLM call."""
        AutoCheckpoint._instance = None
        ac = AutoCheckpoint(str(tmp_path))
        
        def my_llm_call():
            return "response"
        
        result = ac.wrap(my_llm_call, model="gpt-4", prompt="test")
        
        assert result == "response"
        assert ac.session.call_count == 1
    
    def test_before_call_context(self, tmp_path):
        """Test before_call context manager."""
        AutoCheckpoint._instance = None
        ac = AutoCheckpoint(str(tmp_path))
        
        with ac.before_call("claude-3", "Test prompt"):
            pass
        
        assert ac.session.call_count == 1
    
    def test_restore(self, tmp_path):
        """Test restore functionality."""
        AutoCheckpoint._instance = None
        ac = AutoCheckpoint(str(tmp_path))
        
        ac.track("test.py", "original")
        
        with ac.before_call("gpt-4", "Modify"):
            ac.track("test.py", "modified")
        
        restored = ac.restore()
        
        assert restored["test.py"] == "original"
    
    def test_history(self, tmp_path):
        """Test history display."""
        AutoCheckpoint._instance = None
        ac = AutoCheckpoint(str(tmp_path))
        
        with ac.before_call("gpt-4", "Test"):
            pass
        
        history = ac.history()
        
        assert "gpt-4" in history
        assert "call-0001" in history


class TestCreateRestorePoint:
    """Tests for create_restore_point function."""
    
    def test_create_manual_restore_point(self, tmp_path):
        """Test creating a manual restore point."""
        AutoCheckpoint._instance = None
        AutoCheckpoint(str(tmp_path))
        
        checkpoint_id = create_restore_point(
            name="before-big-change",
            files={"app.py": "content"}
        )
        
        assert checkpoint_id is not None
        assert len(checkpoint_id) == 12


class TestLLMCall:
    """Tests for LLMCall dataclass."""
    
    def test_to_dict(self):
        """Test converting LLMCall to dict."""
        call = LLMCall(
            id="call-0001",
            checkpoint_id="abc123",
            model="gpt-4",
            prompt_preview="Test prompt",
            timestamp="2026-01-12T10:00:00Z",
            status="completed",
            files_modified=["test.py"],
            duration_ms=500,
        )
        
        data = call.to_dict()
        
        assert data["id"] == "call-0001"
        assert data["model"] == "gpt-4"
        assert data["duration_ms"] == 500
        assert data["files_modified"] == ["test.py"]
