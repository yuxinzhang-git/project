from pathlib import Path
from app.config import settings
from app.services.skills import skill_registry


def main() -> None:
    skill_registry.load_all()
    skills = skill_registry.list()
    print(f"skills={len(skills)}")
    if skills:
        first = skills[0]
        print(f"loaded_initial={first.loaded}")
        print(f"manifest_keys={sorted(first.summary().keys())}")


if __name__ == "__main__":
    main()
