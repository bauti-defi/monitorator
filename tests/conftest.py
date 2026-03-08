from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Generator

import pytest


@pytest.fixture
def tmp_sessions_dir(tmp_path: Path) -> Path:
    """Provide a temporary sessions directory."""
    sessions = tmp_path / "sessions"
    sessions.mkdir()
    return sessions


@pytest.fixture
def tmp_settings_file(tmp_path: Path) -> Path:
    """Provide a temporary Claude settings.json file."""
    settings_file = tmp_path / "settings.json"
    settings_file.write_text(json.dumps({}))
    return settings_file
