"""
Tests for the checkpoint module.
"""

import pytest
from shadowfs.checkpoint import FileSnapshot, Checkpoint, CheckpointManager


class TestFileSnapshot:
    """Tests for FileSnapshot class."""
    
    def test_create_snapshot(self):
        """Test creating a file snapshot."""
        snap = FileSnapshot(path="test.py", content="print('hello')")
        
        assert snap.path == "test.py"
        assert snap.content == "print('hello')"
        assert snap.size == len("print('hello')")
        assert len(snap.sha) == 40
    
    def test_snapshot_with_sha(self):
        """Test snapshot with provided SHA."""
        snap = FileSnapshot(
            path="test.py",
            content="test",
            sha="abc123",
            size=4,
        )
        
        assert snap.sha == "abc123"
        assert snap.size == 4
    
    def test_snapshot_to_dict(self):
        """Test converting snapshot to dict."""
        snap = FileSnapshot(path="test.py", content="test")
        data = snap.to_dict()
        
        assert data["path"] == "test.py"
        assert data["content"] == "test"
        assert "sha" in data
        assert "size" in data
    
    def test_snapshot_from_dict(self):
        """Test creating snapshot from dict."""
        data = {
            "path": "test.py",
            "content": "test",
            "sha": "abc123",
            "size": 4,
        }
        snap = FileSnapshot.from_dict(data)
        
        assert snap.path == "test.py"
        assert snap.content == "test"
        assert snap.sha == "abc123"


class TestCheckpoint:
    """Tests for Checkpoint class."""
    
    def test_create_checkpoint(self):
        """Test creating a checkpoint."""
        files = {
            "test.py": "print('hello')",
            "README.md": "# Test",
        }
        
        cp = Checkpoint.create(
            name="test-checkpoint",
            description="Test checkpoint",
            files=files,
        )
        
        assert cp.name == "test-checkpoint"
        assert cp.description == "Test checkpoint"
        assert len(cp.files) == 2
        assert cp.id is not None
        assert cp.created_at is not None
    
    def test_add_file(self):
        """Test adding a file to checkpoint."""
        cp = Checkpoint.create(name="test")
        cp.add_file("new.py", "# new file")
        
        assert "new.py" in cp.files
        assert cp.files["new.py"].content == "# new file"
    
    def test_get_file(self):
        """Test getting a file from checkpoint."""
        cp = Checkpoint.create(name="test", files={"test.py": "test"})
        
        snap = cp.get_file("test.py")
        assert snap is not None
        assert snap.content == "test"
        
        assert cp.get_file("nonexistent.py") is None
    
    def test_list_files(self):
        """Test listing files in checkpoint."""
        files = {"a.py": "a", "b.py": "b", "c.py": "c"}
        cp = Checkpoint.create(name="test", files=files)
        
        file_list = cp.list_files()
        assert len(file_list) == 3
        assert set(file_list) == {"a.py", "b.py", "c.py"}
    
    def test_to_dict_from_dict(self):
        """Test serialization round-trip."""
        cp = Checkpoint.create(
            name="test",
            description="desc",
            files={"test.py": "test"},
            metadata={"key": "value"},
        )
        
        data = cp.to_dict()
        restored = Checkpoint.from_dict(data)
        
        assert restored.id == cp.id
        assert restored.name == cp.name
        assert restored.description == cp.description
        assert len(restored.files) == 1
        assert restored.metadata["key"] == "value"


class TestCheckpointManager:
    """Tests for CheckpointManager class."""
    
    def test_create_manager(self):
        """Test creating checkpoint manager."""
        manager = CheckpointManager(max_checkpoints=10)
        
        assert manager.max_checkpoints == 10
        assert len(manager) == 0
    
    def test_create_checkpoint(self):
        """Test creating a checkpoint via manager."""
        manager = CheckpointManager()
        
        cp = manager.create_checkpoint(
            name="test",
            description="test checkpoint",
            files={"test.py": "print('hello')"},
        )
        
        assert len(manager) == 1
        assert cp.name == "test"
    
    def test_get_checkpoint(self):
        """Test getting a checkpoint by ID."""
        manager = CheckpointManager()
        cp = manager.create_checkpoint(name="test", files={"a.py": "a"})
        
        retrieved = manager.get_checkpoint(cp.id)
        assert retrieved is not None
        assert retrieved.name == "test"
        
        assert manager.get_checkpoint("nonexistent") is None
    
    def test_get_checkpoint_by_name(self):
        """Test getting a checkpoint by name."""
        manager = CheckpointManager()
        manager.create_checkpoint(name="first", files={"a.py": "a"})
        manager.create_checkpoint(name="second", files={"b.py": "b"})
        
        cp = manager.get_checkpoint_by_name("first")
        assert cp is not None
        assert cp.name == "first"
    
    def test_list_checkpoints(self):
        """Test listing checkpoints (newest first)."""
        manager = CheckpointManager()
        manager.create_checkpoint(name="first", files={"a.py": "a"})
        manager.create_checkpoint(name="second", files={"b.py": "b"})
        manager.create_checkpoint(name="third", files={"c.py": "c"})
        
        checkpoints = manager.list_checkpoints()
        assert len(checkpoints) == 3
        assert checkpoints[0].name == "third"
        assert checkpoints[2].name == "first"
    
    def test_restore_checkpoint(self):
        """Test restoring from a checkpoint."""
        manager = CheckpointManager()
        
        original_files = {
            "test.py": "original content",
            "config.yaml": "key: value",
        }
        cp = manager.create_checkpoint(name="backup", files=original_files)
        
        # Modify current state
        manager.update_current_state("test.py", "modified content")
        
        # Restore
        restored = manager.restore_checkpoint(cp.id)
        
        assert restored["test.py"] == "original content"
        assert restored["config.yaml"] == "key: value"
    
    def test_restore_specific_paths(self):
        """Test restoring specific files from checkpoint."""
        manager = CheckpointManager()
        
        cp = manager.create_checkpoint(
            name="backup",
            files={"a.py": "a", "b.py": "b", "c.py": "c"},
        )
        
        restored = manager.restore_checkpoint(cp.id, paths=["a.py", "c.py"])
        
        assert "a.py" in restored
        assert "c.py" in restored
        assert "b.py" not in restored
    
    def test_restore_file(self):
        """Test restoring a single file."""
        manager = CheckpointManager()
        cp = manager.create_checkpoint(name="backup", files={"test.py": "test"})
        
        content = manager.restore_file(cp.id, "test.py")
        assert content == "test"
        
        content = manager.restore_file(cp.id, "nonexistent.py")
        assert content is None
    
    def test_diff_checkpoint(self):
        """Test diffing checkpoint with current state."""
        manager = CheckpointManager()
        
        cp = manager.create_checkpoint(
            name="backup",
            files={"test.py": "original", "deleted.py": "will be deleted"},
        )
        
        # Set current state with changes
        current = {
            "test.py": "modified",  # Modified
            "new.py": "new file",   # Added
            # deleted.py is missing - deleted
        }
        
        diff = manager.diff_checkpoint(cp.id, current)
        
        assert diff["test.py"]["status"] == "modified"
        assert diff["deleted.py"]["status"] == "deleted"
        assert diff["new.py"]["status"] == "added"
    
    def test_delete_checkpoint(self):
        """Test deleting a checkpoint."""
        manager = CheckpointManager()
        cp = manager.create_checkpoint(name="test", files={"a.py": "a"})
        
        assert len(manager) == 1
        
        result = manager.delete_checkpoint(cp.id)
        assert result is True
        assert len(manager) == 0
        
        result = manager.delete_checkpoint("nonexistent")
        assert result is False
    
    def test_get_file_history(self):
        """Test getting file history across checkpoints."""
        manager = CheckpointManager()
        
        manager.create_checkpoint(name="v1", files={"test.py": "version 1"})
        manager.create_checkpoint(name="v2", files={"test.py": "version 2"})
        manager.create_checkpoint(name="v3", files={"test.py": "version 3"})
        
        history = manager.get_file_history("test.py")
        
        assert len(history) == 3
        assert history[0]["checkpoint_name"] == "v1"
        assert history[0]["content"] == "version 1"
        assert history[2]["content"] == "version 3"
    
    def test_max_checkpoints_enforcement(self):
        """Test that old checkpoints are removed when max is exceeded."""
        manager = CheckpointManager(max_checkpoints=3)
        
        manager.create_checkpoint(name="1", files={"a.py": "1"})
        manager.create_checkpoint(name="2", files={"a.py": "2"})
        manager.create_checkpoint(name="3", files={"a.py": "3"})
        manager.create_checkpoint(name="4", files={"a.py": "4"})
        
        assert len(manager) == 3
        
        checkpoints = manager.list_checkpoints()
        names = [cp.name for cp in checkpoints]
        assert "1" not in names
        assert "4" in names
    
    def test_json_serialization(self):
        """Test JSON serialization round-trip."""
        manager = CheckpointManager()
        manager.create_checkpoint(name="test", files={"a.py": "a"})
        manager.update_current_state("a.py", "modified")
        
        json_str = manager.to_json()
        restored = CheckpointManager.from_json(json_str)
        
        assert len(restored) == 1
        checkpoints = restored.list_checkpoints()
        assert checkpoints[0].name == "test"
    
    def test_update_current_state(self):
        """Test updating current state."""
        manager = CheckpointManager()
        
        manager.update_current_state("test.py", "content")
        assert manager._current_state["test.py"] == "content"
        
        manager.remove_from_current_state("test.py")
        assert "test.py" not in manager._current_state


class TestCheckpointManagerPersistence:
    """Tests for checkpoint persistence."""
    
    def test_save_and_load(self, tmp_path):
        """Test saving and loading checkpoints to/from file."""
        filepath = tmp_path / "checkpoints.json"
        
        # Create and save
        manager = CheckpointManager()
        manager.create_checkpoint(name="test", files={"a.py": "content"})
        manager.save_to_file(str(filepath))
        
        # Load
        loaded = CheckpointManager.load_from_file(str(filepath))
        
        assert len(loaded) == 1
        cp = loaded.list_checkpoints()[0]
        assert cp.name == "test"
        assert cp.get_file("a.py").content == "content"
