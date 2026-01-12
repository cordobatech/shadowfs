"""
FileNode and DirectoryNode - Tree node classes for filesystem representation.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Union
from datetime import datetime


@dataclass
class FileNode:
    """
    Represents a file in the virtual filesystem.
    """
    name: str
    path: str
    size: int = 0
    sha: Optional[str] = None
    mode: str = "100644"
    
    @property
    def is_file(self) -> bool:
        return True
    
    @property
    def is_dir(self) -> bool:
        return False
    
    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            "name": self.name,
            "path": self.path,
            "type": "file",
            "size": self.size,
            "sha": self.sha,
            "mode": self.mode,
        }
    
    def __repr__(self) -> str:
        return f"FileNode({self.name}, size={self.size})"


@dataclass
class DirectoryNode:
    """
    Represents a directory in the virtual filesystem.
    """
    name: str
    path: str
    children: List[Union["FileNode", "DirectoryNode"]] = field(default_factory=list)
    sha: Optional[str] = None
    
    @property
    def is_file(self) -> bool:
        return False
    
    @property
    def is_dir(self) -> bool:
        return True
    
    def add_child(self, node: Union["FileNode", "DirectoryNode"]) -> None:
        """Add a child node."""
        self.children.append(node)
    
    def get_child(self, name: str) -> Optional[Union["FileNode", "DirectoryNode"]]:
        """Get child by name."""
        for child in self.children:
            if child.name == name:
                return child
        return None
    
    def list_names(self) -> List[str]:
        """List names of children."""
        return [child.name for child in self.children]
    
    def list_files(self) -> List["FileNode"]:
        """List file children."""
        return [c for c in self.children if isinstance(c, FileNode)]
    
    def list_dirs(self) -> List["DirectoryNode"]:
        """List directory children."""
        return [c for c in self.children if isinstance(c, DirectoryNode)]
    
    def walk(self):
        """
        Walk the directory tree.
        
        Yields:
            Tuple of (dirpath, dirnames, filenames).
        """
        dirnames = [d.name for d in self.list_dirs()]
        filenames = [f.name for f in self.list_files()]
        yield self.path, dirnames, filenames
        
        for subdir in self.list_dirs():
            yield from subdir.walk()
    
    def to_dict(self, recursive: bool = True) -> dict:
        """Convert to dictionary representation."""
        result = {
            "name": self.name,
            "path": self.path,
            "type": "dir",
            "sha": self.sha,
        }
        
        if recursive:
            result["children"] = [
                child.to_dict() if isinstance(child, DirectoryNode) else child.to_dict()
                for child in self.children
            ]
        
        return result
    
    def to_tree_string(self, prefix: str = "", is_last: bool = True) -> str:
        """
        Generate ASCII tree representation.
        
        Returns:
            String representation of the tree.
        """
        lines = []
        connector = "└── " if is_last else "├── "
        lines.append(f"{prefix}{connector}{self.name}/")
        
        child_prefix = prefix + ("    " if is_last else "│   ")
        
        # Sort: directories first, then files
        sorted_children = sorted(
            self.children,
            key=lambda x: (x.is_file, x.name.lower())
        )
        
        for i, child in enumerate(sorted_children):
            is_last_child = i == len(sorted_children) - 1
            
            if isinstance(child, DirectoryNode):
                lines.append(child.to_tree_string(child_prefix, is_last_child))
            else:
                child_connector = "└── " if is_last_child else "├── "
                lines.append(f"{child_prefix}{child_connector}{child.name}")
        
        return "\n".join(lines)
    
    def __repr__(self) -> str:
        return f"DirectoryNode({self.name}, children={len(self.children)})"


def build_tree_from_paths(paths: List[str]) -> DirectoryNode:
    """
    Build a directory tree from a list of file paths.
    
    Args:
        paths: List of file paths.
        
    Returns:
        Root DirectoryNode.
    """
    root = DirectoryNode(name="/", path="/")
    
    for path in sorted(paths):
        parts = path.strip("/").split("/")
        current = root
        
        for i, part in enumerate(parts):
            is_file = i == len(parts) - 1 and "." in part
            
            existing = current.get_child(part)
            if existing:
                if isinstance(existing, DirectoryNode):
                    current = existing
            else:
                if is_file:
                    current.add_child(FileNode(name=part, path=path))
                else:
                    new_dir = DirectoryNode(name=part, path="/".join(parts[:i+1]))
                    current.add_child(new_dir)
                    current = new_dir
    
    return root
