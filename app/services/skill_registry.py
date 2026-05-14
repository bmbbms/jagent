from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, List

from app.schemas import BizDomain, SkillInfo


DOMAIN_ALIASES = {
    "data": BizDomain.data_support,
}


class SkillRegistry:
    """Directory-backed skill registry.

    Expected layout:
        app/skills/{biz_domain}/{skill_id}/SKILL.md
    """

    def __init__(self, skills: Iterable[SkillInfo]) -> None:
        self._skills: Dict[BizDomain, List[SkillInfo]] = {}
        for skill in skills:
            self._skills.setdefault(skill.biz_domain, []).append(skill)
        for items in self._skills.values():
            items.sort(key=lambda item: item.skill_id)

    @classmethod
    def from_directory(cls, root: str | Path) -> "SkillRegistry":
        root_path = Path(root)
        if not root_path.exists():
            return cls([])

        skills: list[SkillInfo] = []
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
                SkillInfo(
                    skill_id=skill_id,
                    biz_domain=biz_domain,
                    name=_extract_title(content) or skill_id,
                    path=str(skill_file),
                    purpose=_extract_section_text(content, "Purpose"),
                    when_to_use=_extract_section_items(content, "When To Use"),
                )
            )
        return cls(skills)

    def get_skills(self, biz_domain: BizDomain) -> List[str]:
        return [skill.skill_id for skill in self._skills.get(biz_domain, [])]

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
