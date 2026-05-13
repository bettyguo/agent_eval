"""Tests for tarball normalization + entry-hash composition."""

from __future__ import annotations

from pathlib import Path

import pytest

from agenteval.reproducibility import compute_entry_hash, hash_normalized_directory


def test_hash_deterministic(tmp_path: Path):
    (tmp_path / "a.txt").write_text("hello\n", encoding="utf-8")
    (tmp_path / "b.txt").write_text("world\n", encoding="utf-8")
    h1 = hash_normalized_directory(tmp_path)
    h2 = hash_normalized_directory(tmp_path)
    assert h1 == h2


def test_trailing_whitespace_normalized(tmp_path: Path):
    a = tmp_path / "dir-a"
    b = tmp_path / "dir-b"
    a.mkdir()
    b.mkdir()
    (a / "x.txt").write_text("hello\n", encoding="utf-8")
    (b / "x.txt").write_text("hello   \n", encoding="utf-8")  # trailing spaces
    assert hash_normalized_directory(a) == hash_normalized_directory(b)


def test_different_content_different_hash(tmp_path: Path):
    a = tmp_path / "dir-a"
    b = tmp_path / "dir-b"
    a.mkdir()
    b.mkdir()
    (a / "x.txt").write_text("hello", encoding="utf-8")
    (b / "x.txt").write_text("world", encoding="utf-8")
    assert hash_normalized_directory(a) != hash_normalized_directory(b)


def test_file_order_independence(tmp_path: Path):
    """Directory enumeration order should not affect the hash (we sort lexicographically)."""
    a = tmp_path / "dir-a"
    a.mkdir()
    # Write in non-sorted order — the loader still sorts.
    (a / "z.txt").write_text("z\n", encoding="utf-8")
    (a / "a.txt").write_text("a\n", encoding="utf-8")
    h1 = hash_normalized_directory(a)
    # Re-touch the files in reversed-order to test determinism more thoroughly
    (a / "a.txt").write_text("a\n", encoding="utf-8")
    (a / "z.txt").write_text("z\n", encoding="utf-8")
    h2 = hash_normalized_directory(a)
    assert h1 == h2


def test_symlinks_rejected(tmp_path: Path):
    target = tmp_path / "target.txt"
    target.write_text("x", encoding="utf-8")
    try:
        (tmp_path / "link").symlink_to(target)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks not supported on this platform")
    with pytest.raises(ValueError):
        hash_normalized_directory(tmp_path)


def test_compute_entry_hash_canonical_seeds():
    h = compute_entry_hash(
        skill_bundle_hash="a" * 64,
        task_set_hash="b" * 64,
        model="claude-opus-4-7",
        temperature=0.0,
        seed_list=[1, 2, 3, 4, 5],
        pricing_yaml_hash="c" * 64,
    )
    assert len(h) == 64
    # Different seed list yields different hash.
    h2 = compute_entry_hash(
        skill_bundle_hash="a" * 64,
        task_set_hash="b" * 64,
        model="claude-opus-4-7",
        temperature=0.0,
        seed_list=[1, 2, 3, 4, 6],
        pricing_yaml_hash="c" * 64,
    )
    assert h != h2
