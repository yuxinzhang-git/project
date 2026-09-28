from pydantic import BaseModel, Field


class IncomePlanRequest(BaseModel):
    skills: str
    budget: str = ""
    location: str = ""
    frequency: str = ""
    available_time: str = ""
    risk_preference: str = ""
    avoid: str = ""
    income_cycle: str = ""


class IncomePlanItem(BaseModel):
    title: str
    fit_reason: str
    target_customers: list[str] = Field(default_factory=list)
    offer: str
    preparation_steps: list[str] = Field(default_factory=list)
    seven_day_plan: list[str] = Field(default_factory=list)
    cost_breakdown: str
    customer_acquisition: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    validation_metrics: list[str] = Field(default_factory=list)
    first_action: str
    idea_title: str
    idea_description: str
    idea_deliverable: str
    suggested_price: float = 0
    estimated_cost: float = 0


class IncomePlanResponse(BaseModel):
    plans: list[IncomePlanItem]
