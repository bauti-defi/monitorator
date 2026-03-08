from __future__ import annotations

from textual.widgets import Static
from textual.message import Message

from monitorator.models import MergedSession, SessionStatus
from monitorator.session_prompt import get_session_prompt
from monitorator.tui.formatting import (
    STATUS_ICONS,
    STATUS_COLORS,
    STATUS_LABELS,
    format_activity,
    format_elapsed,
)

# Rotating color palette for project names — each session gets a unique color
SESSION_COLORS: tuple[str, ...] = (
    "#ffcc00",  # yellow (original)
    "#00ccff",  # cyan
    "#ff6699",  # pink
    "#66ff66",  # lime
    "#ff9933",  # orange
    "#cc99ff",  # lavender
    "#33ffcc",  # mint
    "#ff6666",  # coral
    "#99ccff",  # sky blue
    "#ffff66",  # light yellow
)

# Status-specific decorators for the activity column
_STATUS_ACTIVITY_STYLE: dict[SessionStatus, tuple[str, str]] = {
    SessionStatus.WAITING_PERMISSION: ("bold #ff3333", " \u26a0\u26a0\u26a0"),  # ⚠⚠⚠
    SessionStatus.EXECUTING: ("#3399ff", ""),
    SessionStatus.THINKING: ("#00ff66", ""),
    SessionStatus.SUBAGENT_RUNNING: ("#cc66ff", ""),
}


class SessionRow(Static, can_focus=True):
    """Session row with rich status-based coloring.

    Line 1: idx | icon label | project | branch | activity | cpu | elapsed
    Line 2: (optional) last user prompt
    """

    class Selected(Message):
        def __init__(self, session_id: str) -> None:
            super().__init__()
            self.session_id = session_id

    def __init__(self, session: MergedSession) -> None:
        self.session = session
        self.session_id = session.session_id
        self._row_index: int = 0
        super().__init__(self._build_content(), markup=True)

    def _build_content(self) -> str:
        s = self.session
        status = s.effective_status
        icon = STATUS_ICONS.get(status, "?")
        color = STATUS_COLORS.get(status, "#666666")
        label = STATUS_LABELS.get(status, "???")

        project = s.project_name[:18]
        branch_raw = (
            s.hook_state.git_branch
            if s.hook_state and s.hook_state.git_branch
            else None
        )
        branch = branch_raw[:10] if branch_raw else "\u2014"
        activity = format_activity(s)[:36]
        cpu = (
            f"{s.process_info.cpu_percent:.0f}%"
            if s.process_info
            else "-"
        )
        elapsed = (
            format_elapsed(s.process_info.elapsed_seconds)
            if s.process_info
            else "-"
        )

        idx = self._row_index
        proj_color = SESSION_COLORS[(idx - 1) % len(SESSION_COLORS)] if idx > 0 else SESSION_COLORS[0]

        # Activity styling based on status
        style_info = _STATUS_ACTIVITY_STYLE.get(status)
        act_color = style_info[0] if style_info else color
        act_suffix = style_info[1] if style_info else ""

        # Permission rows get LOUD styling
        if status == SessionStatus.WAITING_PERMISSION:
            line1 = (
                f" [bold #ff3333]{idx:>2}[/]  "
                f"[bold #ff3333 blink]{icon} {label:<5s}[/]    "
                f"[bold {proj_color}]{project:<18s}[/]  "
                f"[#3399ff]{branch:<10s}[/]  "
                f"[bold #ff3333]{activity:<36s}{act_suffix}[/]  "
                f"[#ff6666]{cpu:>5s}[/]  "
                f"[#ff6666]{elapsed:>7s}[/]"
            )
        else:
            line1 = (
                f" [{color}]{idx:>2}[/]  "
                f"[{color}]{icon} {label:<5s}[/]    "
                f"[bold {proj_color}]{project:<18s}[/]  "
                f"[#3399ff]{branch:<10s}[/]  "
                f"[{act_color}]{activity:<36s}{act_suffix}[/]  "
                f"[#999999]{cpu:>5s}[/]  "
                f"[#666666]{elapsed:>7s}[/]"
            )

        # Line 2: session prompt (if available)
        prompt = self._get_prompt()
        if prompt:
            truncated = prompt[:70]
            line2 = f"      [{proj_color}]\u2514\u2500[/] [italic #888888]{truncated}[/]"
            return f"{line1}\n{line2}"

        return line1

    def _get_prompt(self) -> str | None:
        """Get session prompt — tries hook data first, then JSONL transcript."""
        s = self.session
        # Hook-based prompt
        if s.hook_state and s.hook_state.last_prompt_summary:
            return s.hook_state.last_prompt_summary
        # JSONL-based prompt (works for both hooked and hookless sessions)
        if s.process_info and s.process_info.session_uuid and s.process_info.cwd:
            return get_session_prompt(s.process_info.cwd, s.process_info.session_uuid)
        return None

    def update_index(self, index: int) -> None:
        """Set the row index and refresh display."""
        self._row_index = index
        self.refresh_content()

    def refresh_content(self) -> None:
        self.update(self._build_content())

    def update_session(self, session: MergedSession) -> None:
        """Update row with new session data without recreating widget."""
        self.session = session
        self.refresh_content()

    def on_click(self) -> None:
        self.post_message(self.Selected(self.session_id))

    def action_select(self) -> None:
        self.post_message(self.Selected(self.session_id))
