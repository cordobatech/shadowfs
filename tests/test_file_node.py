"""Tests for FileNode and DirectoryNode."""

import pytest
from shadowfs.file_node import FileNode, DirectoryNode, build_tree_from_paths


class TestFileNode:
    """Test cases for FileNode."""
    
    def test_create_file_node(self):
        """Test creating a FileNode."""
        node = FileNode(name="test.py", path="src/test.py", size=100)
        
        assert node.name == "test.py"
        assert node.path == "src/test.py"
        assert node.size == 100
        assert node.is_file is True
        assert node.is_dir is False
    
    def test_file_node_to_dict(self):
        """Test FileNode to_dict conversion."""
        node = FileNode(name="test.py", path="src/test.py", size=100, sha="abc123")
        
        d = node.to_dict()
        assert d["name"] == "test.py"
        assert d["path"] == "src/test.py"
        assert d["type"] == "file"
        assert d["size"] == 100
        assert d["sha"] == "abc123"


class TestDirectoryNode:
    """Test cases for DirectoryNode."""
    
    def test_create_directory_node(self):
        """Test creating a DirectoryNode."""
        node = DirectoryNode(name="src", path="src")
        
        assert node.name == "src"
        assert node.path == "src"
        assert node.is_file is False
        assert node.is_dir is True
        assert len(node.children) == 0
    
    def test_add_child(self):
        """Test adding children to DirectoryNode."""
        parent = DirectoryNode(name="src", path="src")
        child = FileNode(name="main.py", path="src/main.py")
        
        parent.add_child(child)
        
        assert len(parent.children) == 1
        assert parent.children[0] == child
    
    def test_get_child(self):
        """Test getting child by name."""
        parent = DirectoryNode(name="src", path="src")
        child1 = FileNode(name="main.py", path="src/main.py")
        child2 = FileNode(name="utils.py", path="src/utils.py")
        
        parent.add_child(child1)
        parent.add_child(child2)
        
        assert parent.get_child("main.py") == child1
        assert parent.get_child("utils.py") == child2
        assert parent.get_child("nonexistent.py") is None
    
    def test_list_names(self):
        """Test listing child names."""
        parent = DirectoryNode(name="src", path="src")
        parent.add_child(FileNode(name="main.py", path="src/main.py"))
        parent.add_child(FileNode(name="utils.py", path="src/utils.py"))
        parent.add_child(DirectoryNode(name="tests", path="src/tests"))
        
        names = parent.list_names()
        assert set(names) == {"main.py", "utils.py", "tests"}
    
    def test_list_files_and_dirs(self):
        """Test listing files and directories separately."""
        parent = DirectoryNode(name="src", path="src")
        file1 = FileNode(name="main.py", path="src/main.py")
        file2 = FileNode(name="utils.py", path="src/utils.py")
        dir1 = DirectoryNode(name="tests", path="src/tests")
        
        parent.add_child(file1)
        parent.add_child(file2)
        parent.add_child(dir1)
        
        files = parent.list_files()
        dirs = parent.list_dirs()
        
        assert len(files) == 2
        assert len(dirs) == 1
        assert file1 in files
        assert dir1 in dirs
    
    def test_walk(self):
        """Test directory walking."""
        root = DirectoryNode(name="/", path="/")
        src = DirectoryNode(name="src", path="src")
        root.add_child(src)
        root.add_child(FileNode(name="README.md", path="README.md"))
        src.add_child(FileNode(name="main.py", path="src/main.py"))
        
        walked = list(root.walk())
        
        assert len(walked) == 2
        assert walked[0][0] == "/"  # root path
        assert "README.md" in walked[0][2]  # files in root
        assert "src" in walked[0][1]  # dirs in root
    
    def test_to_dict(self):
        """Test DirectoryNode to_dict conversion."""
        parent = DirectoryNode(name="src", path="src")
        parent.add_child(FileNode(name="main.py", path="src/main.py"))
        
        d = parent.to_dict()
        
        assert d["name"] == "src"
        assert d["type"] == "dir"
        assert len(d["children"]) == 1


class TestBuildTreeFromPaths:
    """Test cases for build_tree_from_paths function."""
    
    def test_simple_tree(self):
        """Test building a simple tree."""
        paths = [
            "src/main.py",
            "src/utils.py",
            "README.md",
        ]
        
        root = build_tree_from_paths(paths)
        
        assert root.name == "/"
        assert len(root.children) == 2  # src dir + README.md
    
    def test_nested_tree(self):
        """Test building a nested tree."""
        paths = [
            "src/core/main.py",
            "src/core/utils.py",
            "src/tests/test_main.py",
            "README.md",
        ]
        
        root = build_tree_from_paths(paths)
        
        src = root.get_child("src")
        assert src is not None
        assert isinstance(src, DirectoryNode)
        
        core = src.get_child("core")
        assert core is not None
        assert len(core.children) == 2
