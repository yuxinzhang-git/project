from fastapi import APIRouter, HTTPException

from app.schemas.money import MoneyAdvanceRequest, MoneyArtifactRequest, MoneyIdea, MoneyIdeaCreate, MoneyRequest, MoneyResponse, MoneyRunRequest, MoneyState
from app.services.money import MoneyService

router = APIRouter(prefix="/api/money", tags=["money"])
service = MoneyService()


@router.get("/state", response_model=MoneyState)
def state():
    return service.read_state()


@router.put("/state", response_model=MoneyState)
def update(request: MoneyState):
    return service.write_state(request.model_dump())


@router.post("/generate", response_model=MoneyResponse)
def generate(request: MoneyRequest):
    try:
        return service.generate(request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/ideas", response_model=list[MoneyIdea])
def ideas():
    return service.list_ideas()


@router.post("/ideas", response_model=MoneyIdea)
def create_idea(request: MoneyIdeaCreate):
    try:
        return service.create_idea(request.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/artifacts/create", response_model=MoneyState)
def artifact(request: MoneyArtifactRequest):
    return service.create_artifact(request.kind, request.title)


@router.post("/advance", response_model=MoneyState)
def advance(request: MoneyAdvanceRequest):
    try:
        return service.advance(request.focus)
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/run", response_model=MoneyState)
def run(request: MoneyRunRequest):
    try:
        return service.run(request.focus)
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
