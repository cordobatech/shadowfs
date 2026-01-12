"""
GUI - Rich console interface for checkpoint/restore.
Similar to GitHub Copilot's checkpoint GUI in VS Code.
"""

import os
import sys
from datetime import datetime
from typing import Optional, List, Callable
from dataclasses import dataclass

from .session import Session, LLMCall, AutoCheckpoint
from .checkpoint import CheckpointManager, Checkpoint


# ANSI color codes
class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    
    BG_BLACK = "\033[40m"
    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_YELLOW = "\033[43m"
    BG_BLUE = "\033[44m"
    BG_MAGENTA = "\033[45m"
    BG_CYAN = "\033[46m"
    BG_WHITE = "\033[47m"


def supports_color() -> bool:
    """Check if terminal supports colors."""
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("FORCE_COLOR"):
        return True
    return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()


def c(text: str, *colors: str) -> str:
    """Apply colors to text if supported."""
    if not supports_color():
        return text
    color_str = "".join(colors)
    return f"{color_str}{text}{Colors.RESET}"


class CheckpointGUI:
    """
    Rich console GUI for checkpoint visualization.
    
    Mimics GitHub Copilot's checkpoint interface:
    - Shows timeline of changes
    - Highlights restore points before LLM calls
    - Allows interactive restore
    
    Usage:
        gui = CheckpointGUI(session)
        gui.show()  # Display checkpoint history
        gui.show_call_details("call-0001")
        gui.interactive_restore()
    """
    
    def __init__(self, session: Optional[Session] = None):
        """
        Initialize GUI.
        
        Args:
            session: Session to display. If None, uses global AutoCheckpoint.
        """
        if session:
            self.session = session
        else:
            self.session = AutoCheckpoint.get_instance().session
    
    def _format_time(self, timestamp: str) -> str:
        """Format timestamp for display."""
        try:
            dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            return dt.strftime("%I:%M %p")
        except:
            return timestamp[:8]
    
    def _format_duration(self, ms: Optional[int]) -> str:
        """Format duration."""
        if ms is None:
            return ""
        if ms < 1000:
            return f"{ms}ms"
        return f"{ms/1000:.1f}s"
    
    def _status_badge(self, status: str) -> str:
        """Get colored status badge."""
        badges = {
            "completed": c(" ✓ DONE ", Colors.BG_GREEN, Colors.BLACK),
            "failed": c(" ✗ FAIL ", Colors.BG_RED, Colors.WHITE),
            "pending": c(" ⏳ RUN  ", Colors.BG_YELLOW, Colors.BLACK),
            "restored": c(" ↩ REST ", Colors.BG_BLUE, Colors.WHITE),
        }
        return badges.get(status, c(f" {status} ", Colors.DIM))
    
    def header(self, title: str, width: int = 70) -> str:
        """Generate header box."""
        lines = []
        lines.append(c("╔" + "═" * (width - 2) + "╗", Colors.CYAN))
        
        # Center title
        padding = (width - 4 - len(title)) // 2
        title_line = "║" + " " * padding + c(title, Colors.BOLD, Colors.WHITE) + " " * (width - 4 - padding - len(title)) + "║"
        lines.append(c("║", Colors.CYAN) + " " * (width - 2) + c("║", Colors.CYAN))
        lines.append(c("║", Colors.CYAN) + " " * padding + c(title, Colors.BOLD, Colors.WHITE) + " " * (width - 4 - padding - len(title)) + c("║", Colors.CYAN))
        lines.append(c("║", Colors.CYAN) + " " * (width - 2) + c("║", Colors.CYAN))
        lines.append(c("╠" + "═" * (width - 2) + "╣", Colors.CYAN))
        
        return "\n".join(lines)
    
    def footer(self, width: int = 70) -> str:
        """Generate footer."""
        return c("╚" + "═" * (width - 2) + "╝", Colors.CYAN)
    
    def show(self, limit: int = 10) -> None:
        """
        Display checkpoint history GUI.
        
        Similar to GitHub Copilot's checkpoint panel.
        """
        width = 70
        
        print(self.header("🔄 Restore Points (Before LLM Calls)", width))
        
        history = self.session.get_history()[:limit]
        
        if not history:
            print(c("║", Colors.CYAN) + "  No restore points yet. " + " " * 42 + c("║", Colors.CYAN))
            print(c("║", Colors.CYAN) + "  Use session.llm_call() to create checkpoints automatically." + " " * 6 + c("║", Colors.CYAN))
            print(self.footer(width))
            return
        
        for i, call in enumerate(history):
            self._render_call_card(call, width, is_last=(i == len(history) - 1))
        
        # Help text
        print(c("╠" + "═" * (width - 2) + "╣", Colors.CYAN))
        print(c("║", Colors.CYAN) + c("  💡 Commands:", Colors.YELLOW) + " " * 53 + c("║", Colors.CYAN))
        print(c("║", Colors.CYAN) + f"     {c('session.restore_before_call', Colors.GREEN)}('{c('call-XXXX', Colors.CYAN)}')" + " " * 24 + c("║", Colors.CYAN))
        print(c("║", Colors.CYAN) + f"     {c('session.show_diff_since_call', Colors.GREEN)}('{c('call-XXXX', Colors.CYAN)}')" + " " * 22 + c("║", Colors.CYAN))
        print(self.footer(width))
    
    def _render_call_card(self, call: LLMCall, width: int, is_last: bool = False) -> None:
        """Render a single LLM call card."""
        # Time and status line
        time_str = self._format_time(call.timestamp)
        status = self._status_badge(call.status)
        duration = self._format_duration(call.duration_ms)
        
        # Call ID
        call_id = c(call.id, Colors.CYAN, Colors.BOLD)
        
        # Model
        model = c(call.model, Colors.MAGENTA)
        
        # Files
        file_count = len(call.files_modified)
        files_str = c(f"{file_count} file{'s' if file_count != 1 else ''}", Colors.DIM)
        
        # Prompt preview
        prompt = call.prompt_preview[:50] + ("..." if len(call.prompt_preview) > 50 else "")
        
        print(c("║", Colors.CYAN) + " " * (width - 2) + c("║", Colors.CYAN))
        print(c("║", Colors.CYAN) + f"  {status}  {call_id}  {time_str}" + " " * 25 + c("║", Colors.CYAN))
        print(c("║", Colors.CYAN) + f"  │  🤖 {model:<15} {duration:>10}" + " " * 25 + c("║", Colors.CYAN))
        print(c("║", Colors.CYAN) + f"  │  📝 {c(prompt, Colors.DIM):<50}" + " " * 5 + c("║", Colors.CYAN))
        
        if call.files_modified:
            files_preview = ", ".join(call.files_modified[:3])
            if len(call.files_modified) > 3:
                files_preview += f" +{len(call.files_modified) - 3} more"
            print(c("║", Colors.CYAN) + f"  │  📁 {c(files_preview[:50], Colors.DIM):<50}" + " " * 5 + c("║", Colors.CYAN))
        
        if not is_last:
            print(c("║", Colors.CYAN) + c("  │", Colors.DIM) + " " * (width - 5) + c("║", Colors.CYAN))
            print(c("║", Colors.CYAN) + c("  ▼", Colors.DIM) + " " * (width - 5) + c("║", Colors.CYAN))
    
    def show_call_details(self, call_id: str) -> None:
        """Show detailed view of a specific call."""
        call = self.session.get_call(call_id)
        if not call:
            print(c(f"Call not found: {call_id}", Colors.RED))
            return
        
        width = 70
        
        print(self.header(f"📋 Restore Point Details: {call_id}", width))
        
        print(c("║", Colors.CYAN) + " " * (width - 2) + c("║", Colors.CYAN))
        print(c("║", Colors.CYAN) + f"  {c('Call ID:', Colors.BOLD)} {call.id}" + " " * (width - 15 - len(call.id)) + c("║", Colors.CYAN))
        print(c("║", Colors.CYAN) + f"  {c('Model:', Colors.BOLD)} {call.model}" + " " * (width - 13 - len(call.model)) + c("║", Colors.CYAN))
        print(c("║", Colors.CYAN) + f"  {c('Status:', Colors.BOLD)} {self._status_badge(call.status)}" + " " * (width - 23) + c("║", Colors.CYAN))
        print(c("║", Colors.CYAN) + f"  {c('Time:', Colors.BOLD)} {call.timestamp}" + " " * (width - 12 - len(call.timestamp)) + c("║", Colors.CYAN))
        
        if call.duration_ms:
            dur = self._format_duration(call.duration_ms)
            print(c("║", Colors.CYAN) + f"  {c('Duration:', Colors.BOLD)} {dur}" + " " * (width - 15 - len(dur)) + c("║", Colors.CYAN))
        
        print(c("║", Colors.CYAN) + " " * (width - 2) + c("║", Colors.CYAN))
        print(c("║", Colors.CYAN) + f"  {c('Prompt:', Colors.BOLD)}" + " " * (width - 12) + c("║", Colors.CYAN))
        
        # Word wrap prompt
        prompt = call.prompt_preview
        for i in range(0, len(prompt), width - 8):
            chunk = prompt[i:i + width - 8]
            print(c("║", Colors.CYAN) + f"    {c(chunk, Colors.DIM)}" + " " * (width - 6 - len(chunk)) + c("║", Colors.CYAN))
        
        if call.files_modified:
            print(c("║", Colors.CYAN) + " " * (width - 2) + c("║", Colors.CYAN))
            print(c("║", Colors.CYAN) + f"  {c('Files Modified:', Colors.BOLD)}" + " " * (width - 20) + c("║", Colors.CYAN))
            for f in call.files_modified:
                print(c("║", Colors.CYAN) + f"    • {c(f, Colors.GREEN)}" + " " * (width - 8 - len(f)) + c("║", Colors.CYAN))
        
        print(c("║", Colors.CYAN) + " " * (width - 2) + c("║", Colors.CYAN))
        print(c("╠" + "═" * (width - 2) + "╣", Colors.CYAN))
        print(c("║", Colors.CYAN) + f"  {c('Restore:', Colors.YELLOW)} session.restore_before_call('{call.id}')" + " " * 10 + c("║", Colors.CYAN))
        print(self.footer(width))
    
    def show_diff(self, call_id: str) -> None:
        """Show diff since a call with rich formatting."""
        call = self.session.get_call(call_id)
        if not call:
            print(c(f"Call not found: {call_id}", Colors.RED))
            return
        
        diff = self.session.checkpoint_manager.diff_checkpoint(
            call.checkpoint_id,
            self.session._tracked_files,
        )
        
        width = 70
        print(self.header(f"📊 Changes Since {call_id}", width))
        
        if not diff:
            print(c("║", Colors.CYAN) + c("  No changes.", Colors.DIM) + " " * (width - 16) + c("║", Colors.CYAN))
            print(self.footer(width))
            return
        
        for path, change in sorted(diff.items()):
            status = change["status"]
            
            if status == "added":
                icon = c("➕", Colors.GREEN)
                label = c("added", Colors.GREEN)
            elif status == "deleted":
                icon = c("➖", Colors.RED)
                label = c("deleted", Colors.RED)
            else:
                icon = c("✏️ ", Colors.YELLOW)
                label = c("modified", Colors.YELLOW)
            
            line = f"  {icon} {path} ({label})"
            padding = width - 4 - len(path) - 15
            print(c("║", Colors.CYAN) + f"  {icon} {c(path, Colors.WHITE)} ({label})" + " " * max(1, padding) + c("║", Colors.CYAN))
            
            if status == "modified":
                old_lines = len(change["old_content"].splitlines())
                new_lines = len(change["new_content"].splitlines())
                delta = new_lines - old_lines
                delta_str = f"+{delta}" if delta > 0 else str(delta)
                print(c("║", Colors.CYAN) + f"      {old_lines} → {new_lines} lines ({delta_str})" + " " * 40 + c("║", Colors.CYAN))
        
        print(self.footer(width))
    
    def interactive_restore(self) -> Optional[str]:
        """
        Interactive restore selection.
        
        Returns the call ID that was restored, or None if cancelled.
        """
        history = self.session.get_history()
        
        if not history:
            print(c("No restore points available.", Colors.YELLOW))
            return None
        
        print(c("\n📍 Select a restore point:\n", Colors.BOLD))
        
        for i, call in enumerate(history):
            time_str = self._format_time(call.timestamp)
            status_icon = {"completed": "✅", "failed": "❌", "pending": "⏳", "restored": "↩️"}.get(call.status, "❓")
            
            print(f"  {c(str(i + 1), Colors.CYAN)}) {status_icon} [{call.id}] {call.model} @ {time_str}")
            print(f"      {c(call.prompt_preview[:60], Colors.DIM)}")
            print()
        
        print(f"  {c('0', Colors.CYAN)}) Cancel")
        print()
        
        try:
            choice = input(c("Enter number: ", Colors.YELLOW))
            idx = int(choice) - 1
            
            if idx < 0:
                print(c("Cancelled.", Colors.DIM))
                return None
            
            if idx >= len(history):
                print(c("Invalid choice.", Colors.RED))
                return None
            
            call = history[idx]
            
            confirm = input(c(f"Restore to before {call.id}? [y/N] ", Colors.YELLOW))
            if confirm.lower() != 'y':
                print(c("Cancelled.", Colors.DIM))
                return None
            
            restored = self.session.restore_before_call(call.id)
            print(c(f"\n✅ Restored {len(restored)} files to state before {call.id}", Colors.GREEN))
            
            for path in restored:
                print(f"   • {c(path, Colors.WHITE)}")
            
            return call.id
            
        except (ValueError, KeyboardInterrupt):
            print(c("\nCancelled.", Colors.DIM))
            return None


def show_checkpoints(session: Optional[Session] = None, limit: int = 10) -> None:
    """Convenience function to show checkpoint GUI."""
    gui = CheckpointGUI(session)
    gui.show(limit)


def interactive_restore(session: Optional[Session] = None) -> Optional[str]:
    """Convenience function for interactive restore."""
    gui = CheckpointGUI(session)
    return gui.interactive_restore()
