from pydantic import BaseModel


class SmartOperationRequest(BaseModel):
    command: str

