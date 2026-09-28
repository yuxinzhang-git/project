from fastapi import APIRouter, HTTPException

from app.schemas.income_plan import IncomePlanRequest, IncomePlanResponse
from app.services.income_plan import IncomePlanService


router = APIRouter(prefix="/api/income-plan", tags=["income-plan"])
service = IncomePlanService()


@router.post("/generate", response_model=IncomePlanResponse)
def generate(request: IncomePlanRequest):
    try:
        return service.generate(request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
