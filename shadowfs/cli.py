"""
ShadowFS CLI - Command line interface for ShadowFS.
"""

import os
import sys
import json
import argparse
from typing import Optional
from pathlib import Path

from .github_fs import GitHubFS
from .checkpoint import CheckpointManager


# Global checkpoint manager (persisted to file)
CHECKPOINT_FILE = os.path.expanduser("~/.shadowfs/checkpoints.json")


def get_checkpoint_manager() -> CheckpointManager:
    """Get or create checkpoint manager."""
    checkpoint_dir = Path(CHECKPOINT_FILE).parent
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    
    if Path(CHECKPOINT_FILE).exists():
        return CheckpointManager.load_from_file(CHECKPOINT_FILE)
    return CheckpointManager()


def save_checkpoint_manager(manager: CheckpointManager) -> None:
    """Save checkpoint manager to file."""
    manager.save_to_file(CHECKPOINT_FILE)


def get_fs(token: Optional[str] = None) -> GitHubFS:
    """Get GitHubFS instance."""
    return GitHubFS(token=token)


def cmd_ls(args):
    """List directory contents."""
    fs = get_fs(args.token)
    repo = fs.mount(args.repo, branch=args.branch)
    
    path = args.path or "/"
    
    try:
        if args.tree:
            tree = repo.get_tree(path, recursive=True)
            print(tree.to_tree_string())
        else:
            entries = repo.listdir(path)
            for entry in sorted(entries):
                print(entry)
    except NotADirectoryError:
        print(f"Error: {path} is not a directory", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_cat(args):
    """Display file contents."""
    fs = get_fs(args.token)
    repo = fs.mount(args.repo, branch=args.branch)
    
    try:
        content = repo.read(args.path)
        print(content, end="")
    except IsADirectoryError:
        print(f"Error: {args.path} is a directory", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_write(args):
    """Write content to a file."""
    fs = get_fs(args.token)
    repo = fs.mount(args.repo, branch=args.branch)
    
    # Read content from stdin or argument
    if args.content:
        content = args.content
    else:
        content = sys.stdin.read()
    
    try:
        repo.write(args.path, content)
        repo.commit(args.message or f"Update {args.path}")
        print(f"Successfully wrote to {args.path}")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_tree(args):
    """Display directory tree."""
    fs = get_fs(args.token)
    repo = fs.mount(args.repo, branch=args.branch)
    
    path = args.path or "/"
    
    try:
        tree = repo.get_tree(path, recursive=True)
        print(f"{args.repo}")
        print(tree.to_tree_string())
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_info(args):
    """Display repository info."""
    fs = get_fs(args.token)
    repo = fs.mount(args.repo, branch=args.branch)
    
    print(f"Repository: {repo.path}")
    print(f"Owner: {repo.owner}")
    print(f"Name: {repo.name}")
    print(f"Branch: {repo.branch}")
    
    if args.verbose:
        tree = repo.get_tree("/", recursive=True)
        file_count = sum(1 for _, _, files in tree.walk() for _ in files)
        dir_count = sum(1 for _, dirs, _ in tree.walk() for _ in dirs)
        print(f"Files: {file_count}")
        print(f"Directories: {dir_count}")


def cmd_exists(args):
    """Check if path exists."""
    fs = get_fs(args.token)
    repo = fs.mount(args.repo, branch=args.branch)
    
    exists = repo.exists(args.path)
    
    if args.quiet:
        sys.exit(0 if exists else 1)
    else:
        if exists:
            print(f"✓ {args.path} exists")
        else:
            print(f"✗ {args.path} does not exist")
            sys.exit(1)


# =============================================================================
# Checkpoint Commands - Similar to GitHub Copilot's restore functionality
# =============================================================================


def cmd_checkpoint_create(args):
    """Create a new checkpoint (snapshot) of files."""
    manager = get_checkpoint_manager()
    
    files = {}
    
    if args.repo and args.paths:
        # Snapshot specific files from a GitHub repo
        fs = get_fs(args.token)
        repo = fs.mount(args.repo, branch=args.branch)
        
        for path in args.paths:
            try:
                content = repo.read(path)
                files[f"{args.repo}:{path}"] = content
            except Exception as e:
                print(f"Warning: Could not read {path}: {e}", file=sys.stderr)
    
    elif args.files:
        # Snapshot local files
        for filepath in args.files:
            try:
                content = Path(filepath).read_text(encoding="utf-8")
                files[filepath] = content
            except Exception as e:
                print(f"Warning: Could not read {filepath}: {e}", file=sys.stderr)
    
    if not files:
        print("Error: No files to checkpoint", file=sys.stderr)
        sys.exit(1)
    
    checkpoint = manager.create_checkpoint(
        name=args.name,
        description=args.description or "",
        files=files,
        metadata={"source": args.repo or "local"},
    )
    
    save_checkpoint_manager(manager)
    
    print(f"✓ Created checkpoint: {checkpoint.name}")
    print(f"  ID: {checkpoint.id}")
    print(f"  Files: {len(checkpoint.files)}")
    print(f"  Created: {checkpoint.created_at}")


def cmd_checkpoint_list(args):
    """List all checkpoints."""
    manager = get_checkpoint_manager()
    checkpoints = manager.list_checkpoints()
    
    if not checkpoints:
        print("No checkpoints found.")
        return
    
    print(f"{'ID':<14} {'Name':<20} {'Files':<6} {'Created':<24}")
    print("-" * 70)
    
    for cp in checkpoints:
        name = cp.name[:18] + ".." if len(cp.name) > 20 else cp.name
        created = cp.created_at[:19].replace("T", " ")
        print(f"{cp.id:<14} {name:<20} {len(cp.files):<6} {created:<24}")


def cmd_checkpoint_show(args):
    """Show checkpoint details."""
    manager = get_checkpoint_manager()
    
    checkpoint = manager.get_checkpoint(args.checkpoint_id)
    if not checkpoint:
        # Try by name
        checkpoint = manager.get_checkpoint_by_name(args.checkpoint_id)
    
    if not checkpoint:
        print(f"Checkpoint not found: {args.checkpoint_id}", file=sys.stderr)
        sys.exit(1)
    
    print(f"Checkpoint: {checkpoint.name}")
    print(f"ID: {checkpoint.id}")
    print(f"Description: {checkpoint.description or '(none)'}")
    print(f"Created: {checkpoint.created_at}")
    print(f"Files ({len(checkpoint.files)}):")
    
    for path in sorted(checkpoint.list_files()):
        snap = checkpoint.get_file(path)
        print(f"  {path} ({snap.size} bytes)")
    
    if args.verbose:
        print(f"\nMetadata: {json.dumps(checkpoint.metadata, indent=2)}")


def cmd_checkpoint_restore(args):
    """Restore files from a checkpoint."""
    manager = get_checkpoint_manager()
    
    checkpoint = manager.get_checkpoint(args.checkpoint_id)
    if not checkpoint:
        checkpoint = manager.get_checkpoint_by_name(args.checkpoint_id)
    
    if not checkpoint:
        print(f"Checkpoint not found: {args.checkpoint_id}", file=sys.stderr)
        sys.exit(1)
    
    paths_to_restore = args.paths if args.paths else None
    
    if args.dry_run:
        print(f"Would restore from checkpoint: {checkpoint.name} ({checkpoint.id})")
        files = paths_to_restore or checkpoint.list_files()
        for path in files:
            snap = checkpoint.get_file(path)
            if snap:
                print(f"  {path} ({snap.size} bytes)")
        return
    
    restored = manager.restore_checkpoint(checkpoint.id, paths_to_restore)
    save_checkpoint_manager(manager)
    
    print(f"✓ Restored from checkpoint: {checkpoint.name}")
    
    # Write restored files to disk if they are local paths
    for path, content in restored.items():
        if ":" not in path or path[1] == ":":  # Local path (not repo:path)
            if args.output_dir:
                out_path = Path(args.output_dir) / Path(path).name
            else:
                out_path = Path(path)
            
            if args.force or not out_path.exists():
                out_path.parent.mkdir(parents=True, exist_ok=True)
                out_path.write_text(content, encoding="utf-8")
                print(f"  Wrote: {out_path}")
            else:
                print(f"  Skipped (exists): {out_path}")
        else:
            # Repo file - just show it was restored
            print(f"  Restored in memory: {path}")


def cmd_checkpoint_diff(args):
    """Show diff between checkpoint and current state."""
    manager = get_checkpoint_manager()
    
    checkpoint = manager.get_checkpoint(args.checkpoint_id)
    if not checkpoint:
        checkpoint = manager.get_checkpoint_by_name(args.checkpoint_id)
    
    if not checkpoint:
        print(f"Checkpoint not found: {args.checkpoint_id}", file=sys.stderr)
        sys.exit(1)
    
    # Build current state from local files
    current_files = {}
    for path in checkpoint.list_files():
        if ":" not in path or path[1] == ":":  # Local path
            try:
                current_files[path] = Path(path).read_text(encoding="utf-8")
            except FileNotFoundError:
                pass  # File was deleted
    
    diff = manager.diff_checkpoint(checkpoint.id, current_files)
    
    if not diff:
        print("No changes since checkpoint.")
        return
    
    print(f"Changes since checkpoint: {checkpoint.name}")
    print("-" * 50)
    
    for path, change in diff.items():
        status = change["status"]
        if status == "added":
            print(f"  + {path} (added)")
        elif status == "deleted":
            print(f"  - {path} (deleted)")
        elif status == "modified":
            print(f"  ~ {path} (modified)")
            if args.verbose:
                old_lines = len(change["old_content"].splitlines())
                new_lines = len(change["new_content"].splitlines())
                print(f"      {old_lines} lines -> {new_lines} lines")


def cmd_checkpoint_delete(args):
    """Delete a checkpoint."""
    manager = get_checkpoint_manager()
    
    checkpoint = manager.get_checkpoint(args.checkpoint_id)
    if not checkpoint:
        checkpoint = manager.get_checkpoint_by_name(args.checkpoint_id)
    
    if not checkpoint:
        print(f"Checkpoint not found: {args.checkpoint_id}", file=sys.stderr)
        sys.exit(1)
    
    if not args.force:
        confirm = input(f"Delete checkpoint '{checkpoint.name}' ({checkpoint.id})? [y/N] ")
        if confirm.lower() != "y":
            print("Cancelled.")
            return
    
    manager.delete_checkpoint(checkpoint.id)
    save_checkpoint_manager(manager)
    
    print(f"✓ Deleted checkpoint: {checkpoint.name} ({checkpoint.id})")


def cmd_checkpoint_history(args):
    """Show file history across checkpoints."""
    manager = get_checkpoint_manager()
    
    history = manager.get_file_history(args.path)
    
    if not history:
        print(f"No history found for: {args.path}")
        return
    
    print(f"History for: {args.path}")
    print("-" * 60)
    
    for entry in history:
        created = entry["created_at"][:19].replace("T", " ")
        print(f"  [{entry['checkpoint_id']}] {entry['checkpoint_name']}")
        print(f"    Created: {created}")
        print(f"    Size: {entry['size']} bytes")
        print(f"    SHA: {entry['sha'][:12]}...")
        print()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        prog="shadowfs",
        description="ShadowFS - Virtual filesystem for GitHub repositories",
    )
    parser.add_argument(
        "--token",
        "-t",
        help="GitHub token (or set GITHUB_TOKEN env var)",
        default=os.environ.get("GITHUB_TOKEN"),
    )
    parser.add_argument(
        "--version",
        "-v",
        action="version",
        version="%(prog)s 0.1.0",
    )
    
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    # ls command
    ls_parser = subparsers.add_parser("ls", help="List directory contents")
    ls_parser.add_argument("repo", help="Repository (owner/repo)")
    ls_parser.add_argument("path", nargs="?", help="Path to list")
    ls_parser.add_argument("--branch", "-b", help="Branch name")
    ls_parser.add_argument("--tree", action="store_true", help="Show as tree")
    ls_parser.set_defaults(func=cmd_ls)
    
    # cat command
    cat_parser = subparsers.add_parser("cat", help="Display file contents")
    cat_parser.add_argument("repo", help="Repository (owner/repo)")
    cat_parser.add_argument("path", help="File path")
    cat_parser.add_argument("--branch", "-b", help="Branch name")
    cat_parser.set_defaults(func=cmd_cat)
    
    # write command
    write_parser = subparsers.add_parser("write", help="Write to a file")
    write_parser.add_argument("repo", help="Repository (owner/repo)")
    write_parser.add_argument("path", help="File path")
    write_parser.add_argument("--content", "-c", help="Content to write")
    write_parser.add_argument("--message", "-m", help="Commit message")
    write_parser.add_argument("--branch", "-b", help="Branch name")
    write_parser.set_defaults(func=cmd_write)
    
    # tree command
    tree_parser = subparsers.add_parser("tree", help="Display directory tree")
    tree_parser.add_argument("repo", help="Repository (owner/repo)")
    tree_parser.add_argument("path", nargs="?", help="Root path")
    tree_parser.add_argument("--branch", "-b", help="Branch name")
    tree_parser.set_defaults(func=cmd_tree)
    
    # info command
    info_parser = subparsers.add_parser("info", help="Display repository info")
    info_parser.add_argument("repo", help="Repository (owner/repo)")
    info_parser.add_argument("--branch", "-b", help="Branch name")
    info_parser.add_argument("--verbose", "-v", action="store_true")
    info_parser.set_defaults(func=cmd_info)
    
    # exists command
    exists_parser = subparsers.add_parser("exists", help="Check if path exists")
    exists_parser.add_argument("repo", help="Repository (owner/repo)")
    exists_parser.add_argument("path", help="Path to check")
    exists_parser.add_argument("--branch", "-b", help="Branch name")
    exists_parser.add_argument("--quiet", "-q", action="store_true")
    exists_parser.set_defaults(func=cmd_exists)
    
    # =========================================================================
    # Checkpoint commands (like GitHub Copilot restore)
    # =========================================================================
    
    # checkpoint create
    cp_create = subparsers.add_parser(
        "checkpoint",
        aliases=["cp"],
        help="Create a checkpoint (snapshot) of files",
    )
    cp_create.add_argument("name", help="Checkpoint name")
    cp_create.add_argument("--description", "-d", help="Checkpoint description")
    cp_create.add_argument("--repo", "-r", help="Repository (owner/repo)")
    cp_create.add_argument("--branch", help="Branch name")
    cp_create.add_argument("--paths", "-p", nargs="+", help="Paths in repo to snapshot")
    cp_create.add_argument("--files", "-f", nargs="+", help="Local files to snapshot")
    cp_create.set_defaults(func=cmd_checkpoint_create)
    
    # checkpoint-list (list all checkpoints)
    cp_list = subparsers.add_parser(
        "checkpoint-list",
        aliases=["cp-ls"],
        help="List all checkpoints",
    )
    cp_list.set_defaults(func=cmd_checkpoint_list)
    
    # checkpoint-show (show checkpoint details)
    cp_show = subparsers.add_parser(
        "checkpoint-show",
        aliases=["cp-show"],
        help="Show checkpoint details",
    )
    cp_show.add_argument("checkpoint_id", help="Checkpoint ID or name")
    cp_show.add_argument("--verbose", "-v", action="store_true")
    cp_show.set_defaults(func=cmd_checkpoint_show)
    
    # restore (restore from checkpoint) - main command!
    restore = subparsers.add_parser(
        "restore",
        help="Restore files from a checkpoint",
    )
    restore.add_argument("checkpoint_id", help="Checkpoint ID or name")
    restore.add_argument("--paths", "-p", nargs="+", help="Specific paths to restore")
    restore.add_argument("--output-dir", "-o", help="Output directory for restored files")
    restore.add_argument("--dry-run", "-n", action="store_true", help="Show what would be restored")
    restore.add_argument("--force", "-f", action="store_true", help="Overwrite existing files")
    restore.set_defaults(func=cmd_checkpoint_restore)
    
    # checkpoint-diff (compare checkpoint with current state)
    cp_diff = subparsers.add_parser(
        "checkpoint-diff",
        aliases=["cp-diff"],
        help="Show diff between checkpoint and current state",
    )
    cp_diff.add_argument("checkpoint_id", help="Checkpoint ID or name")
    cp_diff.add_argument("--verbose", "-v", action="store_true")
    cp_diff.set_defaults(func=cmd_checkpoint_diff)
    
    # checkpoint-delete (delete a checkpoint)
    cp_delete = subparsers.add_parser(
        "checkpoint-delete",
        aliases=["cp-rm"],
        help="Delete a checkpoint",
    )
    cp_delete.add_argument("checkpoint_id", help="Checkpoint ID or name")
    cp_delete.add_argument("--force", "-f", action="store_true", help="Skip confirmation")
    cp_delete.set_defaults(func=cmd_checkpoint_delete)
    
    # checkpoint-history (show file history across checkpoints)
    cp_history = subparsers.add_parser(
        "checkpoint-history",
        aliases=["cp-history"],
        help="Show file history across checkpoints",
    )
    cp_history.add_argument("path", help="File path to show history for")
    cp_history.set_defaults(func=cmd_checkpoint_history)
    
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
