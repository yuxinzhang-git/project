from dataclasses import dataclass
from pathlib import Path

from app.config import settings


@dataclass
class RuntimeSkill:
    name: str
    description: str
    path: Path
    metadata: dict[str, str]
    agent_configs: tuple[Path, ...]
    instructions: str | None = None
    loaded: bool = False

    def summary(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "path": str(self.path),
            "agent_configs": [str(path) for path in self.agent_configs],
            "loaded": self.loaded,
        }

    def detail(self) -> dict:
        self.ensure_loaded()
        data = self.summary()
        data.update({"metadata": dict(self.metadata), "instructions": self.instructions or ""})
        return data

    def ensure_loaded(self) -> "RuntimeSkill":
        if self.loaded:
            return self
        raw = self.path.read_text(encoding="utf-8")
        _, body = _split_frontmatter(raw)
        self.instructions = body.strip()
        self.loaded = True
        return self


class SkillLoadError(RuntimeError):
    """Raised when a local runtime skill cannot be loaded."""


class RuntimeSkillRegistry:
    def __init__(self, skills_dir: Path | None = None) -> None:
        self.skills_dir = skills_dir or settings.skills_dir
        self._skills: dict[str, RuntimeSkill] = {}

    def load_all(self) -> dict[str, RuntimeSkill]:
        loaded: dict[str, RuntimeSkill] = {}
        if not self.skills_dir.exists():
            self._skills = loaded
            return loaded

        for skill_file in sorted(self.skills_dir.glob("*/SKILL.md")):
            skill = self._load_manifest(skill_file)
            if skill.name in loaded:
                raise SkillLoadError(f"duplicate skill name: {skill.name}")
            loaded[skill.name] = skill

        self._skills = loaded
        return dict(self._skills)

    def list(self) -> list[RuntimeSkill]:
        return list(self._skills.values())

    def peek(self, name: str) -> RuntimeSkill:
        try:
            return self._skills[name]
        except KeyError as exc:
            raise SkillLoadError(f"skill not loaded: {name}") from exc

    def get(self, name: str) -> RuntimeSkill:
        return self.peek(name).ensure_loaded()

    def reload(self) -> dict[str, RuntimeSkill]:
        return self.load_all()

    def _load_manifest(self, skill_file: Path) -> RuntimeSkill:
        metadata = _read_frontmatter(skill_file)
        fallback_name = skill_file.parent.name
        name = metadata.get("name", fallback_name).strip() or fallback_name
        description = metadata.get("description", "").strip()
        agent_configs = tuple(sorted((skill_file.parent / "agents").glob("*.yaml")))
        return RuntimeSkill(
            name=name,
            description=description,
            path=skill_file,
            metadata=metadata,
            agent_configs=agent_configs,
        )


def _read_frontmatter(skill_file: Path) -> dict[str, str]:
    metadata: dict[str, str] = {}
    with skill_file.open("r", encoding="utf-8") as handle:
        first_line = handle.readline()
        if first_line.lstrip("\ufeff").strip() != "---":
            return metadata
        for line in handle:
            stripped = line.strip()
            if stripped == "---":
                break
            key, separator, value = line.partition(":")
            if separator and key.strip():
                metadata[key.strip()] = value.strip()
    return metadata


def _split_frontmatter(raw: str) -> tuple[dict[str, str], str]:
    text = raw.lstrip("\ufeff")
    if not text.startswith("---"):
        return {}, raw

    lines = text.splitlines()
    metadata: dict[str, str] = {}
    closing_index: int | None = None
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            closing_index = index
            break
        key, separator, value = line.partition(":")
        if separator and key.strip():
            metadata[key.strip()] = value.strip()

    if closing_index is None:
        return {}, raw

    body = "\n".join(lines[closing_index + 1 :])
    return metadata, body


skill_registry = RuntimeSkillRegistry()

