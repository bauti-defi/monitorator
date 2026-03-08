from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from monitorator.models import SessionState, SessionStatus
from monitorator.state_store import StateStore


class TestStateStore:
    def test_write_and_read(self, tmp_sessions_dir: Path) -> None:
        store = StateStore(tmp_sessions_dir)
        state = SessionState(
            session_id="abc-123",
            cwd="/tmp/project",
            status=SessionStatus.THINKING,
            project_name="TestProj",
        )
        store.write(state)
        result = store.read("abc-123")
        assert result is not None
        assert result.session_id == "abc-123"
        assert result.status == SessionStatus.THINKING
        assert result.project_name == "TestProj"

    def test_read_nonexistent(self, tmp_sessions_dir: Path) -> None:
        store = StateStore(tmp_sessions_dir)
        assert store.read("nonexistent") is None

    def test_list_all(self, tmp_sessions_dir: Path) -> None:
        store = StateStore(tmp_sessions_dir)
        store.write(SessionState(session_id="a", cwd="/a"))
        store.write(SessionState(session_id="b", cwd="/b"))
        store.write(SessionState(session_id="c", cwd="/c"))
        sessions = store.list_all()
        assert len(sessions) == 3
        ids = {s.session_id for s in sessions}
        assert ids == {"a", "b", "c"}

    def test_list_all_empty(self, tmp_sessions_dir: Path) -> None:
        store = StateStore(tmp_sessions_dir)
        assert store.list_all() == []

    def test_delete(self, tmp_sessions_dir: Path) -> None:
        store = StateStore(tmp_sessions_dir)
        store.write(SessionState(session_id="del-me", cwd="/tmp"))
        assert store.read("del-me") is not None
        store.delete("del-me")
        assert store.read("del-me") is None

    def test_delete_nonexistent_no_error(self, tmp_sessions_dir: Path) -> None:
        store = StateStore(tmp_sessions_dir)
        store.delete("nope")  # should not raise

    def test_cleanup_stale(self, tmp_sessions_dir: Path) -> None:
        store = StateStore(tmp_sessions_dir)
        old_state = SessionState(
            session_id="old",
            cwd="/tmp",
            updated_at=time.time() - 7200,  # 2 hours ago
        )
        new_state = SessionState(
            session_id="new",
            cwd="/tmp",
            updated_at=time.time(),
        )
        store.write(old_state)
        store.write(new_state)
        removed = store.cleanup_stale(max_age_seconds=3600)
        assert removed == ["old"]
        assert store.read("old") is None
        assert store.read("new") is not None

    def test_write_creates_dir_if_missing(self, tmp_path: Path) -> None:
        sessions_dir = tmp_path / "nonexistent" / "sessions"
        store = StateStore(sessions_dir)
        store.write(SessionState(session_id="auto", cwd="/tmp"))
        assert store.read("auto") is not None

    def test_write_is_atomic(self, tmp_sessions_dir: Path) -> None:
        """Verify no .tmp files left behind after write."""
        store = StateStore(tmp_sessions_dir)
        store.write(SessionState(session_id="atomic", cwd="/tmp"))
        tmp_files = list(tmp_sessions_dir.glob("*.tmp"))
        assert len(tmp_files) == 0
        json_files = list(tmp_sessions_dir.glob("*.json"))
        assert len(json_files) == 1

    def test_handles_corrupt_json(self, tmp_sessions_dir: Path) -> None:
        bad_file = tmp_sessions_dir / "corrupt.json"
        bad_file.write_text("{not valid json")
        store = StateStore(tmp_sessions_dir)
        assert store.read("corrupt") is None

    def test_list_all_skips_corrupt(self, tmp_sessions_dir: Path) -> None:
        store = StateStore(tmp_sessions_dir)
        store.write(SessionState(session_id="good", cwd="/tmp"))
        bad = tmp_sessions_dir / "bad.json"
        bad.write_text("nope")
        sessions = store.list_all()
        assert len(sessions) == 1
        assert sessions[0].session_id == "good"

    def test_cleanup_stale_exempts_active_cwds(self, tmp_sessions_dir: Path) -> None:
        store = StateStore(tmp_sessions_dir)
        active = SessionState(
            session_id="active",
            cwd="/projects/monitorator",
            updated_at=time.time() - 7200,
        )
        inactive = SessionState(
            session_id="inactive",
            cwd="/projects/old-thing",
            updated_at=time.time() - 7200,
        )
        store.write(active)
        store.write(inactive)
        removed = store.cleanup_stale(
            max_age_seconds=3600,
            active_cwds={"/projects/monitorator"},
        )
        assert removed == ["inactive"]
        assert store.read("active") is not None
        assert store.read("inactive") is None
