"""
ShadowFS CLI - Command line interface for ShadowFS.
"""

import os
import sys
import argparse
from typing import Optional

from .github_fs import GitHubFS


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
    
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
