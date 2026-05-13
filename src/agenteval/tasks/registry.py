"""TaskSet loader and built-in registry.

Implements DESIGN.md §1.2 TaskSet class. Loads `<dir>/meta.yaml` and all
sibling `*.yaml` files, validates against the schema, computes the normalized
task_set_hash, and resolves each task's effective `panel` (inheriting from
meta.yaml if unspecified at the task level).
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import yaml

from agenteval.errors import TaskSetError
from agenteval.reproducibility import hash_normalized_directory
from agenteval.tasks.schema import Panel, TaskMeta, TaskSetMeta

BUILTIN_TASK_SETS = {
    "skill-specific-v1": Path(__file__).resolve().parents[3] / "tasks" / "skill-specific-v1",
    "tau-bench-v1": Path(__file__).resolve().parents[3] / "tasks" / "tau-bench-v1",
    "swe-bench-lite-v1": Path(__file__).resolve().parents[3] / "tasks" / "swe-bench-lite-v1",
}


@dataclass(frozen=True)
class Task:
    """A fully-resolved task: schema record + effective panel."""

    meta: TaskMeta
    effective_panel: Panel
    source_path: Path

    @property
    def id(self) -> str:
        return self.meta.id

    @property
    def category(self) -> str:
        return self.meta.category


@dataclass(frozen=True)
class TaskSet:
    """A loaded task set with its content hash. Immutable. Build via classmethods."""

    name: str
    version: str
    panel: Panel
    description: str
    license: str
    contamination_notes: str | None
    tasks: tuple[Task, ...]
    hash: str
    source_dir: Path

    @classmethod
    def load(cls, name: str) -> TaskSet:
        if name not in BUILTIN_TASK_SETS:
            raise TaskSetError(
                f"unknown built-in task set {name!r}; known: {sorted(BUILTIN_TASK_SETS)}",
                requested=name,
            )
        path = BUILTIN_TASK_SETS[name]
        if not path.exists():
            raise TaskSetError(
                f"task-set directory missing on disk: {path}",
                name=name,
                path=str(path),
            )
        return cls.from_dir(path)

    @classmethod
    def from_dir(cls, path: str | Path) -> TaskSet:
        root = Path(path).resolve()
        if not root.is_dir():
            raise TaskSetError(f"not a directory: {root}", path=str(root))
        meta_path = root / "meta.yaml"
        if not meta_path.exists():
            raise TaskSetError(
                f"task set missing meta.yaml: {root}",
                path=str(root),
            )

        try:
            meta_doc = yaml.safe_load(meta_path.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            raise TaskSetError(f"meta.yaml is not valid YAML: {exc}", path=str(meta_path)) from exc
        try:
            meta = TaskSetMeta.model_validate(meta_doc)
        except Exception as exc:
            raise TaskSetError(
                f"meta.yaml failed schema validation: {exc}",
                path=str(meta_path),
            ) from exc

        tasks: list[Task] = []
        seen_ids: set[str] = set()
        for task_path in sorted(_iter_task_yamls(root)):
            try:
                task_doc = yaml.safe_load(task_path.read_text(encoding="utf-8"))
            except yaml.YAMLError as exc:
                raise TaskSetError(
                    f"{task_path.name} is not valid YAML: {exc}",
                    path=str(task_path),
                ) from exc
            try:
                task_meta = TaskMeta.model_validate(task_doc)
            except Exception as exc:
                raise TaskSetError(
                    f"{task_path.name} failed schema validation: {exc}",
                    path=str(task_path),
                ) from exc
            if task_meta.id in seen_ids:
                raise TaskSetError(
                    f"duplicate task id {task_meta.id!r} in {root}",
                    duplicate_id=task_meta.id,
                )
            seen_ids.add(task_meta.id)
            if task_path.stem != task_meta.id:
                raise TaskSetError(
                    f"task YAML filename {task_path.name!r} does not match id {task_meta.id!r}",
                    file=str(task_path),
                    id=task_meta.id,
                )

            effective_panel = task_meta.panel or meta.panel
            tasks.append(
                Task(meta=task_meta, effective_panel=effective_panel, source_path=task_path)
            )

        task_set_hash = hash_normalized_directory(root)

        return cls(
            name=meta.name,
            version=meta.version,
            panel=meta.panel,
            description=meta.description,
            license=meta.license,
            contamination_notes=meta.contamination_notes,
            tasks=tuple(tasks),
            hash=task_set_hash,
            source_dir=root,
        )

    def __iter__(self) -> Iterator[Task]:
        return iter(self.tasks)

    def __len__(self) -> int:
        return len(self.tasks)

    def task_by_id(self, task_id: str) -> Task:
        for task in self.tasks:
            if task.id == task_id:
                return task
        raise TaskSetError(f"no task with id {task_id!r} in task set {self.name!r}")


def _iter_task_yamls(root: Path) -> Iterator[Path]:
    for p in root.iterdir():
        if p.is_file() and p.suffix == ".yaml" and p.name != "meta.yaml":
            yield p
