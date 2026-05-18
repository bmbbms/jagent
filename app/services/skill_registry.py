from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List

from app.schemas import BizDomain, SkillInfo


DOMAIN_ALIASES = {
    "data": BizDomain.data_support,
}


@dataclass(frozen=True)
class SkillRuntimeSpec:
    skill_id: str
    biz_domain: BizDomain
    name: str
    path: str
    purpose: str = ""
    when_to_use: List[str] = field(default_factory=list)
    required_inputs: List[str] = field(default_factory=list)
    steps: List[str] = field(default_factory=list)
    output_fields: List[str] = field(default_factory=list)
    allowed_tools: List[str] = field(default_factory=list)
    human_escalation: List[str] = field(default_factory=list)
    content: str = ""

    def to_skill_info(self) -> SkillInfo:
        return SkillInfo(
            skill_id=self.skill_id,
            biz_domain=self.biz_domain,
            name=self.name,
            path=self.path,
            purpose=self.purpose,
            when_to_use=list(self.when_to_use),
        )


class SkillRegistry:
    """Directory-backed skill registry.

    Expected layout:
        app/skills/{biz_domain}/{skill_id}/SKILL.md
    """

    def __init__(self, skills: Iterable[SkillRuntimeSpec]) -> None:
        self._skills: Dict[BizDomain, List[SkillInfo]] = {}
        self._runtime_specs: Dict[str, SkillRuntimeSpec] = {}
        for skill in skills:
            self._skills.setdefault(skill.biz_domain, []).append(skill.to_skill_info())
            self._runtime_specs[skill.skill_id] = skill
        for items in self._skills.values():
            items.sort(key=lambda item: item.skill_id)

    @classmethod
    def from_directory(cls, root: str | Path) -> "SkillRegistry":
        root_path = Path(root)
        if not root_path.exists():
            return cls([])

        skills: list[SkillRuntimeSpec] = []
        for skill_file in sorted(root_path.glob("*/*/SKILL.md")):
            domain_name = skill_file.parent.parent.name
            biz_domain = DOMAIN_ALIASES.get(domain_name)
            if biz_domain is None:
                try:
                    biz_domain = BizDomain(domain_name)
                except ValueError:
                    continue
            skill_id = skill_file.parent.name
            content = skill_file.read_text(encoding="utf-8")
            skills.append(
                SkillRuntimeSpec(
                    skill_id=skill_id,
                    biz_domain=biz_domain,
                    name=_extract_title(content) or skill_id,
                    path=str(skill_file),
                    purpose=_extract_section_text(content, "Purpose"),
                    when_to_use=_extract_section_items(content, "When To Use"),
                    required_inputs=_extract_section_items(content, "Required Inputs"),
                    steps=_extract_ordered_items(content, "Steps"),
                    output_fields=_extract_section_items(content, "Output"),
                    allowed_tools=_extract_section_items(content, "Allowed Tools"),
                    human_escalation=_extract_section_items(content, "Human Escalation"),
                    content=content,
                )
            )
        return cls(skills)

    def get_skills(self, biz_domain: BizDomain) -> List[str]:
        return [skill.skill_id for skill in self._skills.get(biz_domain, [])]

    def get_runtime_spec(self, skill_id: str) -> SkillRuntimeSpec | None:
        return self._runtime_specs.get(skill_id)

    def load_runtime_skills(self, skill_ids: Iterable[str]) -> List[SkillRuntimeSpec]:
        items: list[SkillRuntimeSpec] = []
        for skill_id in skill_ids:
            spec = self._runtime_specs.get(skill_id)
            if spec is not None:
                items.append(spec)
        return items

    def describe_skills(self, biz_domain: BizDomain | None = None) -> List[SkillInfo]:
        if biz_domain is not None:
            return list(self._skills.get(biz_domain, []))
        return [skill for items in self._skills.values() for skill in items]


def _extract_title(content: str) -> str:
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("# Skill:"):
            return stripped.removeprefix("# Skill:").strip()
        if stripped.startswith("# "):
            return stripped.removeprefix("# ").strip()
    return ""


def _extract_section_text(content: str, heading: str) -> str:
    lines = _extract_section_lines(content, heading)
    return " ".join(line.strip() for line in lines if line.strip() and not line.strip().startswith("-"))


def _extract_section_items(content: str, heading: str) -> List[str]:
    items: list[str] = []
    for line in _extract_section_lines(content, heading):
        stripped = line.strip()
        if stripped.startswith("- "):
            items.append(stripped[2:].strip())
    return items


def _extract_ordered_items(content: str, heading: str) -> List[str]:
    items: list[str] = []
    for line in _extract_section_lines(content, heading):
        stripped = line.strip()
        if not stripped:
            continue
        marker, separator, remainder = stripped.partition(". ")
        if separator and marker.isdigit():
            items.append(remainder.strip())
    return items


def _extract_section_lines(content: str, heading: str) -> List[str]:
    lines = content.splitlines()
    marker = f"## {heading}".lower()
    start: int | None = None
    for index, line in enumerate(lines):
        if line.strip().lower() == marker:
            start = index + 1
            break
    if start is None:
        return []

    result: list[str] = []
    for line in lines[start:]:
        if line.startswith("## "):
            break
        result.append(line)
    return result
