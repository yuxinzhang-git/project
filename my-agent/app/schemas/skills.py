from pydantic import BaseModel


class SkillSummary(BaseModel):
    name: str
    description: str
    path: str
    agent_configs: list[str]
    loaded: bool


class SkillDetail(SkillSummary):
    metadata: dict[str, str]
    instructions: str


class SkillListResponse(BaseModel):
    skills: list[SkillSummary]
