from fastapi import APIRouter, HTTPException

from app.schemas.skills import SkillDetail, SkillListResponse, SkillSummary
from app.services.skills import SkillLoadError, skill_registry

router = APIRouter(prefix="/api/skills", tags=["skills"])


@router.get("", response_model=SkillListResponse)
def list_skills():
    return {"skills": [skill.summary() for skill in skill_registry.list()]}


@router.get("/{name}/manifest", response_model=SkillSummary)
def get_skill_manifest(name: str):
    try:
        return skill_registry.peek(name).summary()
    except SkillLoadError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{name}", response_model=SkillDetail)
def get_skill(name: str):
    try:
        return skill_registry.get(name).detail()
    except SkillLoadError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/reload", response_model=SkillListResponse)
def reload_skills():
    try:
        skills = skill_registry.reload()
    except SkillLoadError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {"skills": [skill.summary() for skill in skills.values()]}
