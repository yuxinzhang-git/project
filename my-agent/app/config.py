from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    project_root: Path = Path(__file__).resolve().parent.parent

    @property
    def frontend_dir(self) -> Path:
        return self.project_root / "frontend"

    @property
    def data_dir(self) -> Path:
        return self.project_root / "data"

    @property
    def notes_dir(self) -> Path:
        return self.data_dir / "notes"

    @property
    def money_dir(self) -> Path:
        return self.data_dir / "money"

    @property
    def money_state_file(self) -> Path:
        return self.money_dir / "state.json"

    @property
    def money_artifacts_dir(self) -> Path:
        return self.money_dir / "artifacts"

    @property
    def xianyu_dir(self) -> Path:
        return self.data_dir / "xianyu"

    @property
    def xianyu_state_file(self) -> Path:
        return self.xianyu_dir / "state.json"

    @property
    def browser_dir(self) -> Path:
        return self.data_dir / "browser"

    @property
    def browser_profile_dir(self) -> Path:
        return self.browser_dir / "profile"

    @property
    def browser_screenshots_dir(self) -> Path:
        return self.browser_dir / "screenshots"

    @property
    def skills_dir(self) -> Path:
        return self.project_root / "skills"

    def ensure_runtime_dirs(self) -> None:
        for directory in (
            self.notes_dir,
            self.money_dir,
            self.money_artifacts_dir,
            self.xianyu_dir,
            self.browser_profile_dir,
            self.browser_screenshots_dir,
        ):
            directory.mkdir(parents=True, exist_ok=True)


settings = Settings()
load_dotenv(settings.project_root / ".env")

