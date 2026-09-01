from pydantic import BaseModel


class XianyuEstimateRequest(BaseModel):
    keyword: str
