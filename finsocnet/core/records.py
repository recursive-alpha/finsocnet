"""Record dataclasses and JSON-Schema validation (docs/spec/00-conventions.md §7)."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from functools import lru_cache
from typing import Any

from jsonschema import Draft202012Validator
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012

from finsocnet.core import config
from finsocnet.core.output import CliError

SCHEMA_NAMES = ["content_record", "card", "query_card", "decision", "person", "person_skill", "eval_case"]


@lru_cache(maxsize=None)
def load_schema(name: str) -> dict[str, Any]:
    return json.loads((config.schemas_dir() / f"{name}.schema.json").read_text(encoding="utf-8"))


@lru_cache(maxsize=None)
def _registry() -> Registry:
    reg: Registry = Registry()
    for n in SCHEMA_NAMES:
        reg = reg.with_resource(f"{n}.schema.json", Resource.from_contents(load_schema(n), default_specification=DRAFT202012))
    return reg


def validator(name: str) -> Draft202012Validator:
    return Draft202012Validator(load_schema(name), registry=_registry())


def schema_errors(name: str, instance: Any) -> list[dict[str, str]]:
    """All schema problems at once: `[{"path": "/terms/2", "problem": "..."}]`."""
    out = []
    for e in sorted(validator(name).iter_errors(instance), key=lambda e: list(e.absolute_path)):
        path = "/" + "/".join(str(p) for p in e.absolute_path)
        out.append({"path": path, "problem": e.message})
    return out


def validate_or_raise(name: str, instance: Any) -> None:
    errs = schema_errors(name, instance)
    if errs:
        raise CliError("VALIDATION_ERROR", f"{name} failed schema validation ({len(errs)} problem(s))", details=errs)


@dataclass
class Segment:
    seq: int
    kind: str
    text: str
    locator: dict[str, Any] = field(default_factory=dict)
    author: dict[str, Any] | None = None
    speaker_hint: str | None = None


@dataclass
class ContentRecord:
    id: str
    platform: str
    content_type: str
    segments: list[Segment] = field(default_factory=list)
    source: dict[str, Any] | None = None
    url: str | None = None
    title: str | None = None
    author: dict[str, Any] | None = None
    published_at: str | None = None
    language: str | None = None
    description: str | None = None
    duration_sec: int | None = None
    metrics: dict[str, Any] = field(default_factory=dict)
    links: list[str] = field(default_factory=list)
    mentions: list[str] = field(default_factory=list)
    media: list[dict[str, Any]] = field(default_factory=list)
    parent_content_id: str | None = None
    raw_path: str | None = None
    fetched_at: str | None = None
    fetch_method: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "ContentRecord":
        validate_or_raise("content_record", d)
        data = dict(d)
        data["segments"] = [Segment(**s) for s in d["segments"]]
        return cls(**data)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def check_contiguous(segments: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Segments must start at 0 and be contiguous."""
    errs = []
    for i, s in enumerate(segments):
        if s.get("seq") != i:
            errs.append({"path": f"/segments/{i}/seq", "problem": f"expected seq {i}, got {s.get('seq')}"})
            break
    return errs
