from __future__ import annotations

from datetime import datetime

from textual.widgets import Static

from monitorator.models import MergedSession, SessionStatus

_ACTIVE_STATUSES = {
    SessionStatus.THINKING,
    SessionStatus.EXECUTING,
    SessionStatus.SUBAGENT_RUNNING,
}

# ── Block logo glyphs ──────────────────────────────────────
_LOGO_L1 = "\u2588\u2588\u2584"  # ██▄
_LOGO_L2 = "\u2588\u2588\u2580"  # ██▀

# ── Box-drawing characters ─────────────────────────────────
_TL = "\u2554"  # ╔
_TR = "\u2557"  # ╗
_BL = "\u255a"  # ╚
_BR = "\u255d"  # ╝
_H = "\u2550"   # ═
_V = "\u2551"   # ║

_BOX_WIDTH = 92


def count_sessions(sessions: list[MergedSession]) -> dict[str, int]:
    """Count sessions by status category."""
    total = len(sessions)
    active = sum(1 for s in sessions if s.effective_status in _ACTIVE_STATUSES)
    idle = sum(1 for s in sessions if s.effective_status == SessionStatus.IDLE)
    waiting = sum(
        1 for s in sessions if s.effective_status == SessionStatus.WAITING_PERMISSION
    )
    return {"total": total, "active": active, "idle": idle, "waiting": waiting}


class HeaderBanner(Static):
    """Bordered header banner with block logo, stats, and timestamp."""

    def __init__(self) -> None:
        super().__init__("")
        self._logo = "MONITORATOR"
        self._stats_text = ""
        self._do_render()

    # CRITICAL: never define _render_content — it shadows Textual 8 internals.

    def _do_render(self) -> None:
        """Rebuild the Rich markup and push it into the Static widget."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if self._stats_text:
            line1_right, line2_right = self._stats_text.split("\n", 1)
        else:
            line1_right = "[#666666]waiting for sessions\u2026[/]"
            line2_right = ""

        # Top border
        top_border = f"[#333300]{_TL}{_H * (_BOX_WIDTH - 2)}{_TR}[/]"

        # Line 1: logo + title + timestamp
        line1 = (
            f"[#333300]{_V}[/]  "
            f"[#ffcc00]{_LOGO_L1}[/] "
            f"[bold #ffcc00]{self._logo}[/]"
            f"    {line1_right}"
            f"    [#666666]{timestamp}[/]"
            f"    [#333300]{_V}[/]"
        )

        # Line 2: subtitle + stats
        line2 = (
            f"[#333300]{_V}[/]  "
            f"[#ffcc00]{_LOGO_L2}[/] "
            f"[#555555]claude code session monitor[/]"
            f"       {line2_right}"
            f"    [#333300]{_V}[/]"
        )

        # Bottom border
        bottom_border = f"[#333300]{_BL}{_H * (_BOX_WIDTH - 2)}{_BR}[/]"

        self.update(f"{top_border}\n{line1}\n{line2}\n{bottom_border}")

    def update_counts(self, sessions: list[MergedSession]) -> None:
        """Recompute stats from live session list and re-render."""
        counts = count_sessions(sessions)

        # ── Line 1 right: total + active + waiting ──────────
        parts_l1: list[str] = []
        parts_l1.append(
            f"[bold #ffcc00]\u25c6 {counts['total']}[/] [#999999]sessions[/]"
        )
        if counts["active"]:
            parts_l1.append(
                f"[bold #00ff66]\u25cf {counts['active']}[/] [#999999]active[/]"
            )
        if counts["waiting"]:
            parts_l1.append(
                f"[bold #ff3333]\u26a0 {counts['waiting']}[/]"
            )

        # ── Line 2 right: idle ──────────────────────────────
        parts_l2: list[str] = []
        if counts["idle"]:
            parts_l2.append(
                f"[#666666]\u25cb {counts['idle']} idle[/]"
            )

        self._stats_text = (
            "  ".join(parts_l1)
            + "\n"
            + "  ".join(parts_l2)
        )
        self._do_render()
