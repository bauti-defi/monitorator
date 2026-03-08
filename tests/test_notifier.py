from __future__ import annotations

import time
from unittest.mock import patch, call

import pytest

from monitorator.notifier import Notifier


class TestNotifier:
    def test_sends_notification(self) -> None:
        notifier = Notifier()
        with patch.object(notifier, "_osascript") as mock:
            notifier.notify("Session finished: Agentator", "session_finished", "s1")
        mock.assert_called_once()
        args = mock.call_args[0]
        assert "Session finished: Agentator" in args[0]

    def test_debounce_same_trigger(self) -> None:
        notifier = Notifier(debounce_seconds=30)
        with patch.object(notifier, "_osascript") as mock:
            notifier.notify("Idle", "idle", "s1")
            notifier.notify("Idle", "idle", "s1")
            notifier.notify("Idle", "idle", "s1")
        assert mock.call_count == 1

    def test_no_debounce_for_permission(self) -> None:
        notifier = Notifier(debounce_seconds=30)
        with patch.object(notifier, "_osascript") as mock:
            notifier.notify("Perm 1", "permission", "s1")
            notifier.notify("Perm 2", "permission", "s1")
        assert mock.call_count == 2

    def test_different_sessions_not_debounced(self) -> None:
        notifier = Notifier(debounce_seconds=30)
        with patch.object(notifier, "_osascript") as mock:
            notifier.notify("Idle", "idle", "s1")
            notifier.notify("Idle", "idle", "s2")
        assert mock.call_count == 2

    def test_different_triggers_not_debounced(self) -> None:
        notifier = Notifier(debounce_seconds=30)
        with patch.object(notifier, "_osascript") as mock:
            notifier.notify("Finished", "session_finished", "s1")
            notifier.notify("Idle", "idle", "s1")
        assert mock.call_count == 2

    def test_debounce_expires(self) -> None:
        notifier = Notifier(debounce_seconds=0)  # 0s debounce = always send
        with patch.object(notifier, "_osascript") as mock:
            notifier.notify("Idle", "idle", "s1")
            notifier.notify("Idle", "idle", "s1")
        assert mock.call_count == 2

    def test_osascript_failure_no_crash(self) -> None:
        notifier = Notifier()
        with patch.object(notifier, "_osascript", side_effect=OSError("fail")):
            # Should not raise
            notifier.notify("Test", "test", "s1")

    def test_check_transitions_session_finished(self) -> None:
        from monitorator.models import MergedSession, SessionState, SessionStatus

        notifier = Notifier()
        prev = MergedSession(
            session_id="s1",
            hook_state=SessionState(session_id="s1", cwd="/tmp", status=SessionStatus.THINKING, project_name="Proj"),
            process_info=None,
            effective_status=SessionStatus.THINKING,
            is_stale=False,
        )
        curr = MergedSession(
            session_id="s1",
            hook_state=SessionState(session_id="s1", cwd="/tmp", status=SessionStatus.TERMINATED, project_name="Proj"),
            process_info=None,
            effective_status=SessionStatus.TERMINATED,
            is_stale=False,
        )
        with patch.object(notifier, "_osascript") as mock:
            notifier.check_transitions({"s1": prev}, {"s1": curr})
        mock.assert_called_once()
        assert "finished" in mock.call_args[0][0].lower()

    def test_check_transitions_permission_needed(self) -> None:
        from monitorator.models import MergedSession, SessionState, SessionStatus

        notifier = Notifier()
        prev = MergedSession(
            session_id="s1",
            hook_state=SessionState(session_id="s1", cwd="/tmp", status=SessionStatus.THINKING, project_name="Proj"),
            process_info=None,
            effective_status=SessionStatus.THINKING,
            is_stale=False,
        )
        curr = MergedSession(
            session_id="s1",
            hook_state=SessionState(session_id="s1", cwd="/tmp", status=SessionStatus.WAITING_PERMISSION, project_name="Proj"),
            process_info=None,
            effective_status=SessionStatus.WAITING_PERMISSION,
            is_stale=False,
        )
        with patch.object(notifier, "_osascript") as mock:
            notifier.check_transitions({"s1": prev}, {"s1": curr})
        mock.assert_called_once()
        assert "permission" in mock.call_args[0][0].lower()
