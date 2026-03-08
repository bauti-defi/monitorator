from __future__ import annotations

import time

import pytest

from monitorator.models import MergedSession, ProcessInfo, SessionState, SessionStatus
from monitorator.tui.app import MonitoratorApp
from monitorator.tui.header_banner import HeaderBanner
from monitorator.tui.column_header import ColumnHeader
from monitorator.tui.session_row import SessionRow
from monitorator.tui.detail_panel import DetailPanel, _box_row


def make_merged(
    session_id: str = "test-1",
    project: str = "TestProj",
    status: SessionStatus = SessionStatus.THINKING,
    branch: str = "main",
    tool: str | None = "Edit",
    cpu: float = 20.0,
    stale: bool = False,
) -> MergedSession:
    return MergedSession(
        session_id=session_id,
        hook_state=SessionState(
            session_id=session_id,
            cwd=f"/tmp/{project.lower()}",
            project_name=project,
            status=status,
            git_branch=branch,
            last_tool=tool,
            last_tool_input_summary="file_path: src/app.py",
            last_prompt_summary="Build the monitor",
            updated_at=time.time(),
        ),
        process_info=ProcessInfo(
            pid=12345,
            cpu_percent=cpu,
            elapsed_seconds=300,
            cwd=f"/tmp/{project.lower()}",
            command="claude",
        ),
        effective_status=status,
        is_stale=stale,
    )


class TestMonitoratorApp:
    @pytest.mark.asyncio
    async def test_app_composes(self) -> None:
        async with MonitoratorApp().run_test(size=(120, 30)) as pilot:
            assert pilot.app.query_one(HeaderBanner) is not None
            assert pilot.app.query_one(ColumnHeader) is not None
            assert pilot.app.query_one(DetailPanel) is not None

    @pytest.mark.asyncio
    async def test_app_has_keybindings(self) -> None:
        async with MonitoratorApp().run_test(size=(120, 30)) as pilot:
            bindings = {b.key for b in pilot.app.BINDINGS}
            assert "q" in bindings
            assert "r" in bindings
            assert "o" in bindings
            assert "j" in bindings
            assert "k" in bindings


class TestHeaderBannerWidget:
    @pytest.mark.asyncio
    async def test_banner_renders(self) -> None:
        async with MonitoratorApp().run_test(size=(120, 30)) as pilot:
            banner = pilot.app.query_one(HeaderBanner)
            assert banner is not None

    @pytest.mark.asyncio
    async def test_banner_update_counts(self) -> None:
        async with MonitoratorApp().run_test(size=(120, 30)) as pilot:
            banner = pilot.app.query_one(HeaderBanner)
            sessions = [
                make_merged("s1", status=SessionStatus.THINKING),
                make_merged("s2", status=SessionStatus.IDLE),
                make_merged("s3", status=SessionStatus.WAITING_PERMISSION),
            ]
            banner.update_counts(sessions)


class TestColumnHeaderWidget:
    @pytest.mark.asyncio
    async def test_column_header_renders(self) -> None:
        async with MonitoratorApp().run_test(size=(120, 30)) as pilot:
            ch = pilot.app.query_one(ColumnHeader)
            assert ch is not None


class TestDetailPanelToolLabel:
    def _get_content(self, session: MergedSession) -> str:
        """Build the detail panel content string."""
        panel = DetailPanel()
        captured: list[str] = []
        original_update = panel.update
        def capture_update(content: str, **kwargs: object) -> None:
            captured.append(content)
        panel.update = capture_update  # type: ignore[assignment]
        panel.show_session(session)
        return captured[0] if captured else ""

    def test_tool_row_shows_actual_tool_name(self) -> None:
        session = make_merged("d1", "Agentator", SessionStatus.EXECUTING, tool="Bash")
        content = self._get_content(session)
        for line in content.split("\n"):
            if "tool" in line and "tool " in line:
                assert "Bash" in line, f"Tool row should contain 'Bash': {line}"
                return
        pytest.fail("No tool row found in detail panel output")

    def test_tool_row_hidden_when_no_tool(self) -> None:
        session = make_merged("d2", "Agentator", SessionStatus.IDLE, tool=None)
        content = self._get_content(session)
        for line in content.split("\n"):
            if "tool " in line and "tool" in line.lower():
                pytest.fail(f"Tool row should be hidden when no tool: {line}")

    def test_tool_row_does_not_show_idle(self) -> None:
        session = make_merged("d3", "Agentator", SessionStatus.IDLE, tool=None)
        content = self._get_content(session)
        for line in content.split("\n"):
            assert "Idle" not in line or "IDLE" in line, f"Should not show 'Idle' in tool context: {line}"


class TestDetailPanelWidget:
    @pytest.mark.asyncio
    async def test_detail_shows_session(self) -> None:
        async with MonitoratorApp().run_test(size=(120, 30)) as pilot:
            panel = pilot.app.query_one(DetailPanel)
            session = make_merged("d1", "Agentator", SessionStatus.THINKING)
            panel.show_session(session)

    @pytest.mark.asyncio
    async def test_detail_clear(self) -> None:
        async with MonitoratorApp().run_test(size=(120, 30)) as pilot:
            panel = pilot.app.query_one(DetailPanel)
            panel.clear_session()
