from fastapi import APIRouter, HTTPException

from app.schemas.notes import NoteDeleteRequest, NoteFolderRequest, NoteSaveRequest
from app.services.notes import NotesService

router = APIRouter(prefix="/api/notes", tags=["learning"])
service = NotesService()


@router.get("/tree")
def tree():
    return service.tree()


@router.get("/read")
def read(path: str):
    try:
        return service.read(path)
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=404, detail="Not found") from exc


@router.post("/save")
def save(request: NoteSaveRequest):
    try:
        return service.save(request.path, request.content)
    except ValueError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.post("/folder")
def folder(request: NoteFolderRequest):
    try:
        return service.folder(request.path, request.name)
    except ValueError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.delete("/delete")
def delete(request: NoteDeleteRequest):
    try:
        return service.delete(request.path)
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=404, detail="Not found") from exc

