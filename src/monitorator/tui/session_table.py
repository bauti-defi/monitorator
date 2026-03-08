from __future__ import annotations

import time

from textual.widgets import DataTable, Static
from textual.containers import Vertical
from textual.message import Message

from monitorator.models import MergedSession, SessionStatus


STATUS_DISPLAY: dict[SessionStatus, str] = {
    SessionStatus.THINKING: "[green]Thinking[/]",
    SessionStatus.EXECUTING: "[dodger_blue1]Executing[/]",
    SessionStatus.WAITING_PERMISSION: "[red]Waiting[/]",
    SessionStatus.IDLE: "[dim]Idle[/]",
    SessionStatus.SUBAGENT_RUNNING: "[magenta]Subagent[/]",
    SessionStatus.TERMINATED: "[dim]Terminated[/]",
    SessionStatus.UNKNOWN: "[dim]Unknown[/]",
}


def _activity_text(session: MergedSession) -> str:
    hs = session.hook_state
    if hs and hs.last_tool:
        summary = hs.last_tool_input_summary or ""
        if summary:
            return f"{hs.last_tool}: {summary[:30]}"
        return hs.last_tool
    if hs and hs.updated_at:
        ago = int(time.time() - hs.updated_at)
        if ago < 60:
            return f"{ago}s ago"
        return f"{ago // 60}m ago"
    return ""


def _cpu_text(session: MergedSession) -> str:
    if session.process_info:
        return f"{session.process_info.cpu_percent:.0f}%"
    return ""


class SessionTable(Vertical):
    class SessionSelected(Message):
        def __init__(self, session_id: str) -> None:
            super().__init__()
            self.session_id = session_id

    def __init__(self) -> None:
        super().__init__()
        self._table = DataTable()
        self._sessions: dict[str, MergedSession] = {}

    def compose(self):  # type: ignore[override]
        self._table.add_columns("Project", "Branch", "Status", "Activity", "CPU%")
        self._table.cursor_type = "row"
        yield self._table

    @property
    def row_count(self) -> int:
        return self._table.row_count

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        row_key = event.row_key
        if row_key and row_key.value:
            self.post_message(self.SessionSelected(str(row_key.value)))

    def update_sessions(self, sessions: list[MergedSession]) -> None:
        self._table.clear()
        self._sessions = {s.session_id: s for s in sessions}
        for session in sessions:
            status_text = STATUS_DISPLAY.get(session.effective_status, "[dim]?[/]")
            if session.is_stale:
                status_text = "[dim]Stale[/]"
            self._table.add_row(
                session.project_name,
                session.hook_state.git_branch if session.hook_state and session.hook_state.git_branch else "",
                status_text,
                _activity_text(session),
                _cpu_text(session),
                key=session.session_id,
            )

    def get_session(self, session_id: str) -> MergedSession | None:
        return self._sessions.get(session_id)
