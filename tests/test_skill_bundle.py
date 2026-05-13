"""Tests for SkillBundle."""

from __future__ import annotations

from pathlib import Path

import pytest

from agenteval.errors import SkillBundleError
from agenteval.skills.bundle import EMPTY_BUNDLE_SENTINEL, SkillBundle


def test_empty_bundle_has_stable_hash():
    a = SkillBundle.empty()
    b = SkillBundle.empty()
    assert a.hash == b.hash
    assert a.skills == ()
    assert a.source == "empty"
    # Hash is the SHA256 of the sentinel
    import hashlib

    assert a.hash == hashlib.sha256(EMPTY_BUNDLE_SENTINEL.encode("utf-8")).hexdigest()


def test_from_dir_parses_skills(tmp_path: Path):
    skill_dir = tmp_path / "my-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        "---\nname: my-skill\ndescription: Does the thing.\nlicense: MIT\n---\n\nDo things.",
        encoding="utf-8",
    )

    bundle = SkillBundle.from_dir(tmp_path)
    assert len(bundle.skills) == 1
    s = bundle.skills[0]
    assert s.name == "my-skill"
    assert s.description == "Does the thing."
    assert s.license == "MIT"
    assert "Do things." in s.body


def test_from_dir_missing_skill_md(tmp_path: Path):
    (tmp_path / "broken-skill").mkdir()
    # no SKILL.md
    with pytest.raises(SkillBundleError):
        SkillBundle.from_dir(tmp_path)


def test_from_dir_missing_frontmatter(tmp_path: Path):
    skill_dir = tmp_path / "s"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("no frontmatter here", encoding="utf-8")
    with pytest.raises(SkillBundleError):
        SkillBundle.from_dir(tmp_path)


def test_from_dir_missing_required_keys(tmp_path: Path):
    skill_dir = tmp_path / "s"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        "---\nname: s\n---\nbody",
        encoding="utf-8",
    )
    with pytest.raises(SkillBundleError):
        SkillBundle.from_dir(tmp_path)


def test_empty_dir_rejected_with_helpful_message(tmp_path: Path):
    with pytest.raises(SkillBundleError) as exc:
        SkillBundle.from_dir(tmp_path)
    assert "SkillBundle.empty()" in str(exc.value)


def test_from_claude_md(tmp_path: Path):
    md = tmp_path / "CLAUDE.md"
    md.write_text("# Project guide\n\nBe careful.\n", encoding="utf-8")
    bundle = SkillBundle.from_claude_md(md)
    assert len(bundle.skills) == 1
    assert bundle.skills[0].name == "claude-md"
    assert bundle.source.startswith("claude-md:")
