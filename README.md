# ShadowFS

A virtual filesystem overlay for GitHub repositories. Access GitHub repos as if they were local files.

## Features

- 🗂️ **Virtual File Tree** - Browse GitHub repositories like a local filesystem
- 📖 **Read Files** - Read any file from any branch
- ✏️ **Write Files** - Commit changes directly through the filesystem
- 🔄 **Real-time Sync** - Changes sync with GitHub automatically
- 🌳 **Branch Support** - Switch between branches seamlessly
- 📁 **Directory Listing** - Full directory traversal support
- ⏪ **Checkpoint/Restore** - Save snapshots and restore files like GitHub Copilot
- 📊 **File History** - Track changes across checkpoints with diff support

## Installation

```bash
pip install shadowfs
```

## Quick Start

```python
from shadowfs import GitHubFS

# Initialize with your GitHub token
fs = GitHubFS(token="your_github_token")

# Mount a repository
repo = fs.mount("owner/repo")

# List files
files = repo.listdir("/")
print(files)

# Read a file
content = repo.read("/README.md")
print(content)

# Write a file
repo.write("/new_file.txt", "Hello, World!")

# Commit changes
repo.commit("Added new file")
```

## CLI Usage

```bash
# List files
shadowfs ls owner/repo /src

# Read a file
shadowfs cat owner/repo /README.md

# Write a file
echo "content" | shadowfs write owner/repo /file.txt
```

## Checkpoint/Restore (Like GitHub Copilot)

ShadowFS includes a checkpoint system similar to GitHub Copilot's restore functionality. Create snapshots of your files and restore them at any time.

### Creating Checkpoints

```bash
# Create a checkpoint from local files
shadowfs checkpoint "before-refactor" -f src/app.py src/utils.py

# Create a checkpoint from GitHub repo files
shadowfs checkpoint "backup" -r owner/repo -p /src/main.py /config.yaml

# With description
shadowfs checkpoint "feature-complete" -d "All tests passing" -f *.py
```

### Listing Checkpoints

```bash
# List all checkpoints
shadowfs checkpoint-list

# Output:
# ID             Name                 Files  Created
# ----------------------------------------------------------------------
# 4a8b2c3d4e5f   before-refactor      3      2026-01-12 10:30:45
# 1f2e3d4c5b6a   backup               2      2026-01-12 09:15:22
```

### Restoring Files

```bash
# Restore all files from a checkpoint
shadowfs restore before-refactor

# Restore specific files only
shadowfs restore before-refactor -p src/app.py

# Preview what would be restored (dry run)
shadowfs restore before-refactor --dry-run

# Force overwrite existing files
shadowfs restore before-refactor --force

# Restore to a different directory
shadowfs restore before-refactor -o ./restored/
```

### Comparing Changes

```bash
# See what changed since a checkpoint
shadowfs checkpoint-diff before-refactor

# Output:
# Changes since checkpoint: before-refactor
# --------------------------------------------------
#   ~ src/app.py (modified)
#   + src/new_feature.py (added)
#   - src/old_code.py (deleted)
```

### File History

```bash
# View history of a file across checkpoints
shadowfs checkpoint-history src/app.py
```

### Python API

```python
from shadowfs import CheckpointManager

# Create manager
manager = CheckpointManager()

# Create checkpoint
cp = manager.create_checkpoint(
    name="before-changes",
    description="Working state before major refactor",
    files={
        "src/app.py": open("src/app.py").read(),
        "config.yaml": open("config.yaml").read(),
    }
)

# List checkpoints
for checkpoint in manager.list_checkpoints():
    print(f"{checkpoint.id}: {checkpoint.name}")

# Restore files
restored = manager.restore_checkpoint(cp.id)
for path, content in restored.items():
    with open(path, "w") as f:
        f.write(content)

# Get file history
history = manager.get_file_history("src/app.py")
for entry in history:
    print(f"{entry['checkpoint_name']}: {entry['sha'][:8]}")
```

## Configuration

Create `~/.shadowfs/config.yaml`:

```yaml
github:
  token: ${GITHUB_TOKEN}
  api_url: https://api.github.com

cache:
  enabled: true
  ttl: 300  # seconds
  max_size: 100MB

sync:
  auto_commit: false
  auto_push: false
```

## API Reference

### GitHubFS

Main class for interacting with GitHub as a filesystem.

| Method | Description |
|--------|-------------|
| `mount(repo)` | Mount a repository |
| `unmount(repo)` | Unmount a repository |
| `list_mounts()` | List mounted repositories |

### Repository

Represents a mounted GitHub repository.

| Method | Description |
|--------|-------------|
| `listdir(path)` | List directory contents |
| `read(path)` | Read file contents |
| `write(path, content)` | Write file contents |
| `mkdir(path)` | Create directory |
| `rmdir(path)` | Remove directory |
| `delete(path)` | Delete file |
| `exists(path)` | Check if path exists |
| `is_file(path)` | Check if path is file |
| `is_dir(path)` | Check if path is directory |
| `commit(message)` | Commit staged changes |
| `push()` | Push commits to remote |
| `pull()` | Pull changes from remote |
| `checkout(branch)` | Switch branches |

### CheckpointManager

Manages file snapshots and restore operations.

| Method | Description |
|--------|-------------|
| `create_checkpoint(name, files)` | Create a new checkpoint |
| `list_checkpoints()` | List all checkpoints (newest first) |
| `get_checkpoint(id)` | Get checkpoint by ID |
| `restore_checkpoint(id, paths)` | Restore files from checkpoint |
| `restore_file(id, path)` | Restore single file |
| `diff_checkpoint(id, current)` | Compare checkpoint with current state |
| `delete_checkpoint(id)` | Delete a checkpoint |
| `get_file_history(path)` | Get file history across checkpoints |
| `save_to_file(path)` | Persist checkpoints to file |
| `load_from_file(path)` | Load checkpoints from file |

## License

MIT License - see [LICENSE](LICENSE) for details.

## Contributing

Contributions welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) first.
