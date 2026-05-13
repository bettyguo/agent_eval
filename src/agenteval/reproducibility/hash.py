"""Tarball normalization + SHA256 hashing.

Implements docs/reproducibility.md §2 (normalization) and §1 (entry hash). Pure
stdlib; no Docker / no network. Tested in tests/test_reproducibility.py.
"""

from __future__ import annotations

import hashlib
import io
import tarfile
from collections.abc import Sequence
from pathlib import Path


def hash_normalized_directory(root: str | Path) -> str:
    """Return SHA256 of the normalized tarball of `root`.

    Normalization (docs/reproducibility.md §2):
      1. Files enumerated in lexicographic order.
      2. Symlinks rejected.
      3. Trailing whitespace stripped from text files.
      4. Permissions normalized: 0644 for files, 0755 for dirs.
      5. Timestamps zeroed.
      6. Tar with ustar format, no compression.
    """
    root_path = Path(root).resolve()
    if not root_path.exists():
        raise FileNotFoundError(f"directory not found: {root_path}")
    if not root_path.is_dir():
        raise NotADirectoryError(f"not a directory: {root_path}")

    files = _enumerate_files(root_path)

    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w", format=tarfile.USTAR_FORMAT) as tar:
        for relpath, abspath in files:
            data = _read_normalized(abspath)
            info = tarfile.TarInfo(name=str(relpath).replace("\\", "/"))
            info.size = len(data)
            info.mtime = 0
            info.uid = 0
            info.gid = 0
            info.uname = ""
            info.gname = ""
            info.mode = 0o644
            info.type = tarfile.REGTYPE
            tar.addfile(info, io.BytesIO(data))

    return hashlib.sha256(buf.getvalue()).hexdigest()


def _enumerate_files(root: Path) -> list[tuple[Path, Path]]:
    """Return [(rel_path, abs_path), ...] sorted lexicographically. Reject symlinks."""
    result: list[tuple[Path, Path]] = []
    for path in sorted(root.rglob("*"), key=lambda p: str(p.relative_to(root)).replace("\\", "/")):
        if path.is_symlink():
            raise ValueError(f"symlinks not permitted in normalized tarball: {path}")
        if path.is_file():
            result.append((path.relative_to(root), path))
    return result


def _read_normalized(path: Path) -> bytes:
    """Read file; if it's text, strip trailing whitespace per line. Else verbatim."""
    raw = path.read_bytes()
    if _looks_like_text(raw):
        text = raw.decode("utf-8")
        lines = [line.rstrip() for line in text.splitlines()]
        # Preserve a trailing newline if the original ended with one
        if text.endswith("\n"):
            return ("\n".join(lines) + "\n").encode("utf-8")
        return "\n".join(lines).encode("utf-8")
    return raw


def _looks_like_text(data: bytes) -> bool:
    """Cheap text sniffer: valid UTF-8, no NUL bytes."""
    if b"\x00" in data:
        return False
    try:
        data.decode("utf-8")
        return True
    except UnicodeDecodeError:
        return False


def compute_entry_hash(
    *,
    skill_bundle_hash: str,
    task_set_hash: str,
    model: str,
    temperature: float,
    seed_list: Sequence[int],
    pricing_yaml_hash: str,
) -> str:
    """Compose entry_hash from its components per docs/reproducibility.md §1.

    The seed_list is rendered without spaces ("[1,2,3,4,5]"); the temperature is
    rendered with 3-digit precision. All components are concatenated with a fixed
    delimiter ("|") and the result is SHA256'd.
    """
    seeds_str = "[" + ",".join(str(s) for s in seed_list) + "]"
    temp_str = f"{temperature:.3f}"
    parts = [
        skill_bundle_hash,
        task_set_hash,
        model,
        temp_str,
        seeds_str,
        pricing_yaml_hash,
    ]
    serialized = "|".join(parts).encode("utf-8")
    return hashlib.sha256(serialized).hexdigest()
