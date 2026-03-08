from __future__ import annotations

import json
import shutil
from pathlib import Path

HOOK_SCRIPT = Path(__file__).parent.parent.parent / "hooks" / "emit_event.py"
MARKER = "emit_event.py"

HOOK_EVENTS = [
    "PreToolUse",
    "PostToolUse",
    "Notification",
    "SubagentStart",
    "SubagentStop",
    "Stop",
    "UserPromptSubmit",
]


class HookInstaller:
    def __init__(self, settings_path: Path | None = None) -> None:
        if settings_path is None:
            settings_path = Path.home() / ".claude" / "settings.json"
        self._path = settings_path
        self._hook_command = f"python3 {HOOK_SCRIPT.resolve()}"

    def _read_settings(self) -> dict[str, object]:
        if self._path.exists():
            try:
                return json.loads(self._path.read_text())
            except (json.JSONDecodeError, OSError):
                return {}
        return {}

    def _write_settings(self, settings: dict[str, object]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(settings, indent=2) + "\n")

    def _make_hook_entry(self) -> dict[str, str]:
        return {"type": "command", "command": self._hook_command}

    def install(self) -> None:
        settings = self._read_settings()

        # Backup
        if self._path.exists():
            backup = self._path.with_suffix(".json.monitorator-backup")
            shutil.copy2(self._path, backup)

        hooks = settings.get("hooks")
        if not isinstance(hooks, dict):
            hooks = {}
            settings["hooks"] = hooks

        entry = self._make_hook_entry()

        for event in HOOK_EVENTS:
            event_hooks = hooks.get(event)
            if not isinstance(event_hooks, list):
                event_hooks = []
                hooks[event] = event_hooks

            # Remove existing monitorator hooks (idempotent)
            event_hooks[:] = [h for h in event_hooks if MARKER not in h.get("command", "")]
            event_hooks.append(entry)

        self._write_settings(settings)

    def uninstall(self) -> None:
        settings = self._read_settings()
        hooks = settings.get("hooks")
        if not isinstance(hooks, dict):
            return

        for event in list(hooks.keys()):
            event_hooks = hooks[event]
            if isinstance(event_hooks, list):
                event_hooks[:] = [h for h in event_hooks if MARKER not in h.get("command", "")]

        self._write_settings(settings)

    def is_installed(self) -> bool:
        settings = self._read_settings()
        hooks = settings.get("hooks")
        if not isinstance(hooks, dict):
            return False
        for event_hooks in hooks.values():
            if isinstance(event_hooks, list):
                for h in event_hooks:
                    if MARKER in h.get("command", ""):
                        return True
        return False
