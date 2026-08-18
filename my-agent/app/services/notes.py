from pathlib import Path

from app.config import settings


class NotesService:
    def __init__(self, root: Path | None = None):
        self.root = (root or settings.notes_dir).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, relative: str) -> Path:
        target = (self.root / relative).resolve()
        if self.root not in target.parents and target != self.root:
            raise ValueError("Forbidden path")
        return target

    def _tree(self, directory: Path, prefix: str = "") -> list[dict]:
        items = []
        for entry in sorted(directory.iterdir(), key=lambda item: (not item.is_dir(), item.name.lower())):
            relative = f"{prefix}/{entry.name}".strip("/")
            if entry.is_dir():
                items.append({"name": entry.name, "path": relative, "type": "folder", "children": self._tree(entry, relative)})
            elif entry.suffix == ".md":
                items.append({"name": entry.stem, "path": relative, "type": "file"})
        return items

    def tree(self) -> dict:
        return {"items": self._tree(self.root)}

    def read(self, relative: str) -> dict:
        path = self._path(relative)
        if not path.is_file() or path.suffix != ".md":
            raise FileNotFoundError(relative)
        return {"path": relative, "content": path.read_text(encoding="utf-8"), "name": path.stem}

    def save(self, relative: str, content: str) -> dict:
        if not relative.endswith(".md"):
            relative += ".md"
        path = self._path(relative)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return {"status": "ok", "path": relative}

    def folder(self, relative: str, name: str) -> dict:
        path = self._path(str(Path(relative) / name))
        path.mkdir(parents=True, exist_ok=True)
        return {"status": "ok"}

    def delete(self, relative: str) -> dict:
        path = self._path(relative)
        if path.is_dir():
            import shutil
            shutil.rmtree(path)
        elif path.is_file():
            path.unlink()
        else:
            raise FileNotFoundError(relative)
        return {"status": "ok"}

