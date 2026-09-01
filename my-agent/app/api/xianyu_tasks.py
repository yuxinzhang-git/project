from fastapi import APIRouter, HTTPException

from app.schemas.xianyu_tasks import XianyuSummary, XianyuTask, XianyuTaskCreate, XianyuTaskUpdate
from app.services.xianyu_tasks import XianyuTaskService


router = APIRouter(prefix="/api/xianyu", tags=["xianyu-tasks"])
service = XianyuTaskService()


@router.get("/tasks", response_model=list[XianyuTask])
def list_tasks():
    return service.list_tasks()


@router.post("/tasks", response_model=XianyuTask)
def create_task(request: XianyuTaskCreate):
    try:
        return service.create_task(request.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.patch("/tasks/{task_id}", response_model=XianyuTask)
def update_task(task_id: str, request: XianyuTaskUpdate):
    try:
        return service.update_task(task_id, request.model_dump(exclude_unset=True))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/summary", response_model=XianyuSummary)
def summary():
    return service.summary()
