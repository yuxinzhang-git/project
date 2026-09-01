from pydantic import BaseModel


class MoneyRequest(BaseModel):
    need: str
    rules: str = ""
    context: str = ""


class MoneyResponse(BaseModel):
    title: str
    summary: str
    fit_reason: str
    steps: list[str]
    cost: str
    cycle: str
    income: str
    risks: list[str]
    needs: list[dict]
    first_action: str


class MoneyState(BaseModel):
    ideas: list[dict] = []
    mission: str = ""
    rules: str = ""
    initial_capital: float = 0
    target_amount: float = 0
    balance: float = 0
    status: str = "setup"
    active_task: str = ""
    subtasks: list[dict] = []
    permissions: list[dict] = []
    ledger: list[dict] = []
    activity: list[dict] = []
    artifacts: list[dict] = []


class MoneyIdeaCreate(BaseModel):
    title: str
    description: str = ""
    target_user: str = ""
    deliverable: str = ""
    suggested_price: float = 0
    estimated_cost: float = 0
    risk: str = ""


class MoneyIdea(BaseModel):
    id: str
    title: str
    description: str = ""
    target_user: str = ""
    deliverable: str = ""
    suggested_price: float = 0
    estimated_cost: float = 0
    risk: str = ""
    status: str = "draft"
    created_at: str
    updated_at: str


class MoneyAdvanceRequest(BaseModel):
    focus: str = ""


class MoneyRunRequest(BaseModel):
    focus: str = ""


class MoneyArtifactRequest(BaseModel):
    kind: str = "web-game"
    title: str = ""
