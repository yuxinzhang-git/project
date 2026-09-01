from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api import chat, daily, learning, money, skills, smart, web, xianyu_tasks
from app.api.web import browser, run_browser_operation
from app.config import settings
from app.services.skills import skill_registry


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings.ensure_runtime_dirs()
    skill_registry.load_all()
    yield
    run_browser_operation(browser.close)


def create_app() -> FastAPI:
    settings.ensure_runtime_dirs()
    skill_registry.load_all()
    app = FastAPI(title="my-agent", lifespan=lifespan)
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
    app.mount("/ui", StaticFiles(directory=settings.frontend_dir / "ui", html=True), name="ui")
    app.mount("/browser-screenshots", StaticFiles(directory=settings.browser_screenshots_dir), name="browser-screenshots")
    # Include concrete routers directly. This also works with FastAPI builds
    # that preserve nested router wrappers instead of flattening them.
    for module in (chat, daily, learning, money, web, smart, xianyu_tasks, skills):
        app.include_router(module.router)

    @app.get("/api/status")
    def status():
        return {"app": "my-agent", "version": "2.0.0", "status": "running", "features": ["calculator", "weather", "sports", "billing", "notes", "money", "xianyu-tasks", "web", "browser", "smart-operation", "runtime-skills"], "skills": [skill.summary() for skill in skill_registry.list()]}

    @app.get("/")
    def root():
        return FileResponse(settings.frontend_dir / "index.html")

    @app.get("/{path:path}")
    def static_page(path: str):
        target = (settings.frontend_dir / path).resolve()
        if settings.frontend_dir.resolve() in target.parents and target.is_file():
            return FileResponse(target)

        # The daily module historically linked these pages from the site root,
        # while their files live in the UI subdirectory. Keep those URLs
        # working without exposing paths outside the frontend tree.
        ui_root = (settings.frontend_dir / "ui").resolve()
        ui_target = (ui_root / path).resolve()
        if ui_root in ui_target.parents and ui_target.is_file():
            return FileResponse(ui_target)

        raise HTTPException(status_code=404, detail="Not Found")

    return app


app = create_app()

