from __future__ import annotations

import time

import pytest

from monitorator.models import MergedSession, ProcessInfo, SessionState, SessionStatus


def make_merged(
    session_id: str = "test-1",
    project: str = "TestProj",
    status: SessionStatus = SessionStatus.THINKING,
    branch: str = "main",
    tool: str | None = "Edit",
    tool_summary: str | None = "file_path: src/app.py",
    prompt: str | None = "Build the monitor",
    cpu: float = 20.0,
    elapsed: int = 300,
    stale: bool = False,
    subagent_count: int = 0,
    updated_at: float | None = None,
    hook_state: bool = True,
) -> MergedSession:
    hs = (
        SessionState(
            session_id=session_id,
            cwd=f"/tmp/{project.lower()}",
            project_name=project,
            status=status,
            git_branch=branch,
            last_tool=tool,
            last_tool_input_summary=tool_summary,
            last_prompt_summary=prompt,
            updated_at=updated_at or time.time(),
            subagent_count=subagent_count,
        )
        if hook_state
        else None
    )
    return MergedSession(
        session_id=session_id,
        hook_state=hs,
        process_info=ProcessInfo(
            pid=12345,
            cpu_percent=cpu,
            elapsed_seconds=elapsed,
            cwd=f"/tmp/{project.lower()}",
            command="claude",
        ),
        effective_status=status,
        is_stale=stale,
    )


class TestSessionRowContent:
    def test_content_lines(self) -> None:
        """SessionRow renders 1 line without prompt, 2 lines with prompt."""
        from monitorator.tui.session_row import SessionRow

        # With hook prompt → 2 lines
        session = make_merged(prompt="Build the monitor")
        row = SessionRow(session)
        content = row._build_content()
        lines = content.strip().split("\n")
        assert len(lines) == 2

        # Without prompt → 1 line
        session_no_prompt = make_merged(prompt=None, tool=None, tool_summary=None)
        row2 = SessionRow(session_no_prompt)
        content2 = row2._build_content()
        lines2 = content2.strip().split("\n")
        assert len(lines2) == 1

    def test_contains_project_name(self) -> None:
        from monitorator.tui.session_row import SessionRow

        session = make_merged(project="agentator")
        row = SessionRow(session)
        content = row._build_content()
        assert "agentator" in content

    def test_contains_branch(self) -> None:
        from monitorator.tui.session_row import SessionRow

        session = make_merged(branch="feat/ui")
        row = SessionRow(session)
        content = row._build_content()
        assert "feat/ui" in content

    def test_contains_status_icon(self) -> None:
        from monitorator.tui.session_row import SessionRow

        session = make_merged(status=SessionStatus.THINKING)
        row = SessionRow(session)
        content = row._build_content()
        assert "\u25cf" in content  # ● thinking icon

    def test_contains_status_label(self) -> None:
        from monitorator.tui.session_row import SessionRow

        session = make_merged(status=SessionStatus.THINKING)
        row = SessionRow(session)
        content = row._build_content()
        assert "THINK" in content

    def test_contains_cpu(self) -> None:
        from monitorator.tui.session_row import SessionRow

        session = make_merged(cpu=45.0)
        row = SessionRow(session)
        content = row._build_content()
        assert "45%" in content

    def test_contains_elapsed(self) -> None:
        from monitorator.tui.session_row import SessionRow

        session = make_merged(elapsed=323)
        row = SessionRow(session)
        content = row._build_content()
        assert "5m 23s" in content

    def test_description_never_empty(self) -> None:
        """Description column must always have text."""
        from monitorator.tui.session_row import SessionRow

        for status in SessionStatus:
            session = make_merged(
                status=status,
                tool=None,
                tool_summary=None,
                prompt=None,
            )
            row = SessionRow(session)
            content = row._build_content()
            # The content should contain some meaningful activity text
            assert content.strip() != ""

    def test_no_branch_shows_dash(self) -> None:
        from monitorator.tui.session_row import SessionRow

        session = make_merged(branch=None)  # type: ignore[arg-type]
        row = SessionRow(session)
        content = row._build_content()
        assert "\u2014" in content  # em-dash

    def test_no_process_info_shows_dash_for_cpu(self) -> None:
        from monitorator.tui.session_row import SessionRow

        session = MergedSession(
            session_id="test",
            hook_state=SessionState(
                session_id="test",
                cwd="/tmp/test",
                project_name="Test",
                status=SessionStatus.THINKING,
                updated_at=time.time(),
            ),
            process_info=None,
            effective_status=SessionStatus.THINKING,
            is_stale=False,
        )
        row = SessionRow(session)
        content = row._build_content()
        # Should have dash for cpu/time when no process info
        assert "-" in content


class TestSessionRowIndex:
    def test_update_index(self) -> None:
        from monitorator.tui.session_row import SessionRow

        session = make_merged()
        row = SessionRow(session)
        row.update_index(3)
        assert row._row_index == 3

    def test_index_in_content(self) -> None:
        from monitorator.tui.session_row import SessionRow

        session = make_merged()
        row = SessionRow(session)
        row.update_index(5)
        content = row._build_content()
        assert "5" in content


class TestSessionRowWidget:
    @pytest.mark.asyncio
    async def test_row_is_focusable(self) -> None:
        from monitorator.tui.session_row import SessionRow

        row = SessionRow(make_merged())
        assert row.can_focus is True

    @pytest.mark.asyncio
    async def test_row_stores_session_id(self) -> None:
        from monitorator.tui.session_row import SessionRow

        session = make_merged(session_id="abc-123")
        row = SessionRow(session)
        assert row.session_id == "abc-123"

    @pytest.mark.asyncio
    async def test_update_session(self) -> None:
        from monitorator.tui.session_row import SessionRow

        session1 = make_merged(session_id="abc", project="Old")
        row = SessionRow(session1)
        session2 = make_merged(session_id="abc", project="New")
        row.update_session(session2)
        assert row.session.project_name == "New"

    @pytest.mark.asyncio
    async def test_selected_message_class(self) -> None:
        from monitorator.tui.session_row import SessionRow

        msg = SessionRow.Selected("test-id")
        assert msg.session_id == "test-id"


class TestSessionRowColors:
    def test_different_indexes_get_different_project_colors(self) -> None:
        from monitorator.tui.session_row import SessionRow, SESSION_COLORS

        # Use IDLE status — palette colors only apply to non-full-row statuses
        session = make_merged(project="ProjA", status=SessionStatus.IDLE, prompt=None)
        row1 = SessionRow(session)
        row1.update_index(1)
        row2 = SessionRow(session)
        row2.update_index(2)

        content1 = row1._build_content()
        content2 = row2._build_content()

        # Each row should use a different color from the palette
        color1 = SESSION_COLORS[(1 - 1) % len(SESSION_COLORS)]
        color2 = SESSION_COLORS[(2 - 1) % len(SESSION_COLORS)]
        assert color1 in content1
        assert color2 in content2
        assert color1 != color2

    def test_session_colors_palette_has_at_least_6(self) -> None:
        from monitorator.tui.session_row import SESSION_COLORS

        assert len(SESSION_COLORS) >= 6


class TestSessionRowPromptLine:
    def test_shows_session_prompt_on_second_line(self) -> None:
        from unittest.mock import patch

        from monitorator.tui.session_row import SessionRow

        session = make_merged(
            hook_state=False,
            project="MyProj",
        )
        session.process_info.session_uuid = "abc12345-dead-beef-cafe-123456789abc"  # type: ignore[union-attr]

        with patch("monitorator.tui.session_row.get_session_prompt", return_value="Implement auth flow"):
            row = SessionRow(session)
            content = row._build_content()

        assert "Implement auth flow" in content
        lines = content.strip().split("\n")
        assert len(lines) == 2

    def test_no_prompt_stays_single_line(self) -> None:
        from monitorator.tui.session_row import SessionRow

        session = make_merged(project="Simple", prompt=None, tool=None, tool_summary=None)
        row = SessionRow(session)
        content = row._build_content()
        lines = content.strip().split("\n")
        assert len(lines) == 1


class TestSessionRowPermission:
    def test_waiting_permission_shows_warning(self) -> None:
        from monitorator.tui.session_row import SessionRow

        session = make_merged(
            status=SessionStatus.WAITING_PERMISSION,
            tool="Bash",
            tool_summary="command: rm -rf dist",
        )
        row = SessionRow(session)
        content = row._build_content()
        assert "PERM!" in content
        assert "Permission" in content

    def test_executing_shows_exec_label(self) -> None:
        from monitorator.tui.session_row import SessionRow

        session = make_merged(status=SessionStatus.EXECUTING)
        row = SessionRow(session)
        content = row._build_content()
        assert "EXEC" in content


class TestSessionRowFullRowColoring:
    """Entire row should be painted in the status color."""

    def test_thinking_row_uses_green_for_project(self) -> None:
        from monitorator.tui.session_row import SessionRow

        session = make_merged(status=SessionStatus.THINKING, project="MyProject")
        row = SessionRow(session)
        row.update_index(1)
        content = row._build_content()
        # Project name should use green (#00ff66), not the palette color
        assert "#00ff66" in content
        assert "MyProject" in content

    def test_thinking_row_has_blink_on_status(self) -> None:
        from monitorator.tui.session_row import SessionRow

        session = make_merged(status=SessionStatus.THINKING)
        row = SessionRow(session)
        content = row._build_content()
        assert "blink" in content

    def test_permission_row_uses_red_for_project(self) -> None:
        from monitorator.tui.session_row import SessionRow

        session = make_merged(status=SessionStatus.WAITING_PERMISSION, project="NeedsPerm")
        row = SessionRow(session)
        row.update_index(1)
        content = row._build_content()
        assert "#ff3333" in content
        assert "NeedsPerm" in content

    def test_terminated_row_uses_blue_for_project(self) -> None:
        from monitorator.tui.session_row import SessionRow

        session = make_merged(status=SessionStatus.TERMINATED, project="DoneProj")
        row = SessionRow(session)
        row.update_index(1)
        content = row._build_content()
        # Terminated should use blue
        assert "#3399ff" in content
        assert "DoneProj" in content

    def test_executing_row_uses_green_for_project(self) -> None:
        from monitorator.tui.session_row import SessionRow

        session = make_merged(status=SessionStatus.EXECUTING, project="RunningProj")
        row = SessionRow(session)
        row.update_index(1)
        content = row._build_content()
        assert "#00ff66" in content

    def test_idle_row_uses_palette_color_for_project(self) -> None:
        from monitorator.tui.session_row import SessionRow, SESSION_COLORS

        session = make_merged(status=SessionStatus.IDLE, project="IdleProj", prompt=None)
        row = SessionRow(session)
        row.update_index(1)
        content = row._build_content()
        # Idle should still use palette colors, not a status color
        expected_color = SESSION_COLORS[0]
        assert expected_color in content
