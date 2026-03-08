from __future__ import annotations

import json
import os
import re

_CACHE: dict[str, str] = {}
_MAX_DESC_LEN = 60


def get_project_description(cwd: str) -> str | None:
    """Read project metadata from cwd, cached. Returns short description or None."""
    if not cwd:
        return None
    if cwd in _CACHE:
        return _CACHE[cwd]

    desc = _scan(cwd)
    if desc:
        _CACHE[cwd] = desc
    return desc


def _scan(cwd: str) -> str | None:
    """Walk the priority chain and return first match."""
    if not os.path.isdir(cwd):
        return None

    # 1. CLAUDE.md in root
    result = _read_heading(os.path.join(cwd, "CLAUDE.md"))
    if result:
        return _truncate(result)

    # 2. CLAUDE.md in immediate subdirectories
    try:
        for entry in os.scandir(cwd):
            if entry.is_dir(follow_symlinks=False):
                sub_claude = os.path.join(entry.path, "CLAUDE.md")
                result = _read_heading(sub_claude)
                if result:
                    return _truncate(result)
    except OSError:
        pass

    # 3. pyproject.toml
    result = _read_pyproject_toml(os.path.join(cwd, "pyproject.toml"))
    if result:
        return _truncate(result)

    # 4. package.json
    result = _read_package_json(os.path.join(cwd, "package.json"))
    if result:
        return _truncate(result)

    # 5. README.md
    result = _read_heading(os.path.join(cwd, "README.md"))
    if result:
        return _truncate(result)

    return None


_SKIP_HEADINGS = {"claude.md", "claude", "readme.md", "readme"}


def _read_heading(path: str) -> str | None:
    """Extract first meaningful markdown heading from a file.

    Skips headings that just repeat the filename (e.g., '# CLAUDE.md' in CLAUDE.md).
    """
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if stripped.startswith("#"):
                    heading = stripped.lstrip("#").strip()
                    if heading.lower() in _SKIP_HEADINGS:
                        continue
                    return heading
    except OSError:
        pass
    return None


def _read_pyproject_toml(path: str) -> str | None:
    """Extract description from pyproject.toml using regex."""
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
        match = re.search(r'''description\s*=\s*["']([^"']+)["']''', text)
        if match:
            return match.group(1).strip()
    except OSError:
        pass
    return None


def _read_package_json(path: str) -> str | None:
    """Extract description from package.json."""
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        desc = data.get("description", "")
        if desc:
            return str(desc)
    except (OSError, json.JSONDecodeError, TypeError):
        pass
    return None


def _truncate(text: str) -> str:
    """Truncate to max length."""
    if len(text) <= _MAX_DESC_LEN:
        return text
    return text[:_MAX_DESC_LEN]
