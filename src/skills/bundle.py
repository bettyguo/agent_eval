"""SkillBundle: load .claude/skills/ directories or a single CLAUDE.md.

Implements DESIGN.md §1.2 SkillBundle. M1 implements `empty()` and a minimal
`from_dir()` that parses SKILL.md frontmatter; full skill execution-time
injection happens in M2.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from agenteval.errors import SkillBundleError
from agenteval.reproducibility import hash_normalized_directory

EMPTY_BUNDLE_SENTINEL = "AGENTEVAL_EMPTY_BUNDLE_v1"


@dataclass(frozen=True)
class Skill:
    """A single parsed skill: its frontmatter + body + auxiliary files."""

    name: str
    description: str
    body: str
    license: str | None = None
    extra_files: tuple[Path, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class SkillBundle:
    """An immutable collection of skills with a stable content hash."""

    skills: tuple[Skill, ...]
    hash: str
    source: str  # "dir:<path>" | "claude-md:<path>" | "empty"

    @classmethod
    def empty(cls) -> SkillBundle:
        """The no-skills baseline. Stable hash across runs."""
        h = hashlib.sha256(EMPTY_BUNDLE_SENTINEL.encode("utf-8")).hexdigest()
        return cls(skills=(), hash=h, source="empty")

    @classmethod
    def from_dir(cls, path: str | Path) -> SkillBundle:
        root = Path(path).resolve()
        if not root.is_dir():
            raise SkillBundleError(f"not a directory: {root}", path=str(root))

        skills: list[Skill] = []
        for child in sorted(root.iterdir(), key=lambda p: p.name):
            if not child.is_dir():
                continue
            skill_md = child / "SKILL.md"
            if not skill_md.exists():
                raise SkillBundleError(
                    f"skill directory missing SKILL.md: {child}",
                    skill_dir=str(child),
                )
            skills.append(_parse_skill_md(skill_md, child))

        if not skills:
            raise SkillBundleError(
                f"no skills found under {root} (no subdirectories with SKILL.md). "
                f"For the no-skills baseline, use SkillBundle.empty() rather than an empty dir.",
                path=str(root),
            )

        bundle_hash = hash_normalized_directory(root)
        return cls(skills=tuple(skills), hash=bundle_hash, source=f"dir:{root}")

    @classmethod
    def from_claude_md(cls, path: str | Path) -> SkillBundle:
        """Compatibility loader: a single CLAUDE.md becomes a synthetic single-skill bundle."""
        src = Path(path).resolve()
        if not src.is_file():
            raise SkillBundleError(f"not a file: {src}", path=str(src))
        text = src.read_text(encoding="utf-8")
        skill = Skill(
            name="claude-md",
            description="Compatibility-loaded from a single CLAUDE.md file.",
            body=text,
        )
        # Synthetic bundles hash the file content directly (no directory tarball).
        h = hashlib.sha256(text.encode("utf-8")).hexdigest()
        return cls(skills=(skill,), hash=h, source=f"claude-md:{src}")

    @property
    def license_summary(self) -> list[tuple[str, str | None]]:
        return [(s.name, s.license) for s in self.skills]


def _parse_skill_md(path: Path, skill_dir: Path) -> Skill:
    """Parse SKILL.md frontmatter (---YAML---) + body."""
    text = path.read_text(encoding="utf-8")
    fm, body = _split_frontmatter(text)
    if fm is None:
        raise SkillBundleError(
            f"{path} missing YAML frontmatter (---name: ... / description: ...---)",
            path=str(path),
        )
    try:
        meta = yaml.safe_load(fm) or {}
    except yaml.YAMLError as exc:
        raise SkillBundleError(
            f"{path} frontmatter is not valid YAML: {exc}", path=str(path)
        ) from exc
    if not isinstance(meta, dict):
        raise SkillBundleError(
            f"{path} frontmatter must be a YAML mapping, got {type(meta).__name__}",
            path=str(path),
        )
    name = meta.get("name")
    description = meta.get("description")
    if not isinstance(name, str) or not name:
        raise SkillBundleError(f"{path} frontmatter missing required 'name'", path=str(path))
    if not isinstance(description, str) or not description:
        raise SkillBundleError(f"{path} frontmatter missing required 'description'", path=str(path))
    license_value = meta.get("license")
    if license_value is not None and not isinstance(license_value, str):
        raise SkillBundleError(f"{path} 'license' must be a string if present", path=str(path))

    extras: list[Path] = []
    for sibling in sorted(skill_dir.rglob("*")):
        if sibling.is_file() and sibling != path:
            extras.append(sibling.relative_to(skill_dir))

    return Skill(
        name=name,
        description=description,
        body=body,
        license=license_value,
        extra_files=tuple(extras),
    )


def _split_frontmatter(text: str) -> tuple[str | None, str]:
    """Return (frontmatter, body). If no frontmatter, return (None, text)."""
    if not text.startswith("---\n") and not text.startswith("---\r\n"):
        return None, text
    # Find the closing ---
    rest = text.split("\n", 1)[1] if text.startswith("---\n") else text.split("\r\n", 1)[1]
    end_idx = rest.find("\n---")
    if end_idx == -1:
        return None, text
    fm = rest[:end_idx]
    body = rest[end_idx + len("\n---") :].lstrip("\r\n")
    return fm, body
