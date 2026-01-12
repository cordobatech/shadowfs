# ShadowFS

A virtual filesystem overlay for GitHub repositories. Access GitHub repos as if they were local files.

## Features

- 🗂️ **Virtual File Tree** - Browse GitHub repositories like a local filesystem
- 📖 **Read Files** - Read any file from any branch
- ✏️ **Write Files** - Commit changes directly through the filesystem
- 🔄 **Real-time Sync** - Changes sync with GitHub automatically
- 🌳 **Branch Support** - Switch between branches seamlessly
- 📁 **Directory Listing** - Full directory traversal support

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
# Mount a repository
shadowfs mount owner/repo /mnt/repo

# List files
shadowfs ls owner/repo /src

# Read a file
shadowfs cat owner/repo /README.md

# Write a file
echo "content" | shadowfs write owner/repo /file.txt
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

## License

MIT License - see [LICENSE](LICENSE) for details.

## Contributing

Contributions welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) first.
