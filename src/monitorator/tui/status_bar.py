from __future__ import annotations

from textual.widgets import Static

from monitorator.models import MergedSession, SessionStatus


class StatusBar(Static):
    def __init__(self) -> None:
        super().__init__("")
        self._update_text(0, 0, 0, 0, 0)

    def _update_text(
        self,
        total: int,
        active: int,
        idle: int,
        waiting: int,
        stale: int,
    ) -> None:
        parts = [
            "MONITORATOR",
            f"{total} sessions",
            f"{active} active",
            f"{idle} idle",
        ]
        if waiting:
            parts.append(f"{waiting} wait")
        if stale:
            parts.append(f"{stale} stale")
        self.update("  |  ".join(parts))

    def update_counts(self, sessions: list[MergedSession]) -> None:
        total = len(sessions)
        active = sum(
            1 for s in sessions
            if s.effective_status in {
                SessionStatus.THINKING,
                SessionStatus.EXECUTING,
                SessionStatus.SUBAGENT_RUNNING,
            }
        )
        idle = sum(1 for s in sessions if s.effective_status == SessionStatus.IDLE)
        waiting = sum(1 for s in sessions if s.effective_status == SessionStatus.WAITING_PERMISSION)
        stale = sum(1 for s in sessions if s.is_stale)
        self._update_text(total, active, idle, waiting, stale)
