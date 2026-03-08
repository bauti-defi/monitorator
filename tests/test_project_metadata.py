from __future__ import annotations

import json
import os

import pytest

from monitorator.project_metadata import get_project_description, _CACHE


@pytest.fixture(autouse=True)
def _clear_cache() -> None:
    """Clear the module-level cache before each test."""
    _CACHE.clear()


class TestReadClaudeMd:
    def test_extracts_first_heading(self, tmp_path: object) -> None:
        p = tmp_path  # type: ignore[assignment]
        (p / "CLAUDE.md").write_text("# BB Media Creative Studio\n\nSome content\n")
        assert get_project_description(str(p)) == "BB Media Creative Studio"

    def test_ignores_non_heading_lines(self, tmp_path: object) -> None:
        p = tmp_path  # type: ignore[assignment]
        (p / "CLAUDE.md").write_text("Some preamble\n# My Project\nMore text\n")
        assert get_project_description(str(p)) == "My Project"

    def test_skips_filename_heading_uses_next(self, tmp_path: object) -> None:
        """When CLAUDE.md has '# CLAUDE.md' as heading, skip it and use next heading."""
        p = tmp_path  # type: ignore[assignment]
        (p / "CLAUDE.md").write_text("# CLAUDE.md\n\n## What is Monitorator\n\nA TUI dashboard\n")
        assert get_project_description(str(p)) == "What is Monitorator"

    def test_skips_filename_heading_falls_through(self, tmp_path: object) -> None:
        """When CLAUDE.md only has '# CLAUDE.md' and no other heading, fall through to next source."""
        p = tmp_path  # type: ignore[assignment]
        (p / "CLAUDE.md").write_text("# CLAUDE.md\n\nThis file has no other heading.\n")
        (p / "pyproject.toml").write_text('[project]\ndescription = "TUI dashboard"\n')
        assert get_project_description(str(p)) == "TUI dashboard"

    def test_strips_leading_hashes_and_spaces(self, tmp_path: object) -> None:
        p = tmp_path  # type: ignore[assignment]
        (p / "CLAUDE.md").write_text("##  Spaced Heading  \n")
        assert get_project_description(str(p)) == "Spaced Heading"

    def test_has_highest_priority_over_others(self, tmp_path: object) -> None:
        p = tmp_path  # type: ignore[assignment]
        (p / "CLAUDE.md").write_text("# From Claude\n")
        (p / "package.json").write_text(json.dumps({"description": "From package"}))
        (p / "README.md").write_text("# From Readme\n")
        assert get_project_description(str(p)) == "From Claude"


class TestReadPyprojectToml:
    def test_extracts_description(self, tmp_path: object) -> None:
        p = tmp_path  # type: ignore[assignment]
        (p / "pyproject.toml").write_text(
            '[project]\nname = "monitorator"\ndescription = "TUI dashboard to monitor"\n'
        )
        assert get_project_description(str(p)) == "TUI dashboard to monitor"

    def test_handles_single_quotes_in_value(self, tmp_path: object) -> None:
        p = tmp_path  # type: ignore[assignment]
        (p / "pyproject.toml").write_text(
            "[project]\ndescription = 'A cool project'\n"
        )
        assert get_project_description(str(p)) == "A cool project"


class TestReadPackageJson:
    def test_extracts_description(self, tmp_path: object) -> None:
        p = tmp_path  # type: ignore[assignment]
        (p / "package.json").write_text(json.dumps({"name": "my-app", "description": "A web app"}))
        assert get_project_description(str(p)) == "A web app"

    def test_skips_empty_description(self, tmp_path: object) -> None:
        p = tmp_path  # type: ignore[assignment]
        (p / "package.json").write_text(json.dumps({"name": "my-app", "description": ""}))
        assert get_project_description(str(p)) is None

    def test_skips_missing_description(self, tmp_path: object) -> None:
        p = tmp_path  # type: ignore[assignment]
        (p / "package.json").write_text(json.dumps({"name": "my-app"}))
        assert get_project_description(str(p)) is None


class TestReadReadmeMd:
    def test_extracts_first_heading(self, tmp_path: object) -> None:
        p = tmp_path  # type: ignore[assignment]
        (p / "README.md").write_text("# My Awesome Project\n\nDescription here.\n")
        assert get_project_description(str(p)) == "My Awesome Project"

    def test_lower_priority_than_package_json(self, tmp_path: object) -> None:
        p = tmp_path  # type: ignore[assignment]
        (p / "package.json").write_text(json.dumps({"description": "From package"}))
        (p / "README.md").write_text("# From Readme\n")
        assert get_project_description(str(p)) == "From package"


class TestPriorityChain:
    def test_pyproject_before_package_json(self, tmp_path: object) -> None:
        p = tmp_path  # type: ignore[assignment]
        (p / "pyproject.toml").write_text('[project]\ndescription = "From pyproject"\n')
        (p / "package.json").write_text(json.dumps({"description": "From package"}))
        assert get_project_description(str(p)) == "From pyproject"

    def test_package_json_before_readme(self, tmp_path: object) -> None:
        p = tmp_path  # type: ignore[assignment]
        (p / "package.json").write_text(json.dumps({"description": "From package"}))
        (p / "README.md").write_text("# From Readme\n")
        assert get_project_description(str(p)) == "From package"


class TestSubdirClaudeMd:
    def test_reads_from_subdirectory(self, tmp_path: object) -> None:
        p = tmp_path  # type: ignore[assignment]
        sub = p / "nanoclaw"
        sub.mkdir()
        (sub / "CLAUDE.md").write_text("# NanoClaw Agent\n")
        assert get_project_description(str(p)) == "NanoClaw Agent"

    def test_root_claude_md_wins_over_subdir(self, tmp_path: object) -> None:
        p = tmp_path  # type: ignore[assignment]
        (p / "CLAUDE.md").write_text("# Root Project\n")
        sub = p / "subdir"
        sub.mkdir()
        (sub / "CLAUDE.md").write_text("# Sub Project\n")
        assert get_project_description(str(p)) == "Root Project"


class TestTruncation:
    def test_long_description_truncated_to_60(self, tmp_path: object) -> None:
        p = tmp_path  # type: ignore[assignment]
        long_desc = "A" * 100
        (p / "CLAUDE.md").write_text(f"# {long_desc}\n")
        result = get_project_description(str(p))
        assert result is not None
        assert len(result) <= 60


class TestCaching:
    def test_caches_result(self, tmp_path: object) -> None:
        p = tmp_path  # type: ignore[assignment]
        (p / "CLAUDE.md").write_text("# Cached Project\n")
        result1 = get_project_description(str(p))
        # Remove the file — should still return cached result
        os.remove(str(p / "CLAUDE.md"))
        result2 = get_project_description(str(p))
        assert result1 == result2 == "Cached Project"

    def test_none_result_not_cached(self, tmp_path: object) -> None:
        """If no metadata found, don't cache so future polls can try again."""
        p = tmp_path  # type: ignore[assignment]
        result1 = get_project_description(str(p))
        assert result1 is None
        # Now add a file — should find it
        (p / "CLAUDE.md").write_text("# Now Found\n")
        result2 = get_project_description(str(p))
        assert result2 == "Now Found"


class TestFallback:
    def test_no_metadata_returns_none(self, tmp_path: object) -> None:
        p = tmp_path  # type: ignore[assignment]
        assert get_project_description(str(p)) is None

    def test_nonexistent_dir_returns_none(self) -> None:
        assert get_project_description("/nonexistent/path/xyz") is None

    def test_empty_string_returns_none(self) -> None:
        assert get_project_description("") is None


class TestMalformedFiles:
    def test_malformed_package_json(self, tmp_path: object) -> None:
        p = tmp_path  # type: ignore[assignment]
        (p / "package.json").write_text("not valid json{{{")
        assert get_project_description(str(p)) is None

    def test_empty_claude_md(self, tmp_path: object) -> None:
        p = tmp_path  # type: ignore[assignment]
        (p / "CLAUDE.md").write_text("")
        assert get_project_description(str(p)) is None

    def test_claude_md_no_heading(self, tmp_path: object) -> None:
        p = tmp_path  # type: ignore[assignment]
        (p / "CLAUDE.md").write_text("Just some text without headings\n")
        assert get_project_description(str(p)) is None
