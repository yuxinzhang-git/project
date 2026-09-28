from typing import Literal

from pydantic import BaseModel, Field


TaskStatus = Literal["draft", "ready", "delivered", "settled", "archived"]
PaymentStatus = Literal["unpaid", "pending", "paid"]


class XianyuTaskCreate(BaseModel):
    title: str
    task_type: str = "one_off_delivery"
    customer_need: str = ""
    deliverable: str = ""
    amount: float = Field(default=0, ge=0)
    costs: float = Field(default=0, ge=0)
    notes: str = ""


class XianyuTaskUpdate(BaseModel):
    status: TaskStatus | None = None
    payment_status: PaymentStatus | None = None
    amount: float | None = Field(default=None, ge=0)
    costs: float | None = Field(default=None, ge=0)
    deliverable: str | None = None
    artifact_path: str | None = None
    notes: str | None = None


class XianyuTask(BaseModel):
    id: str
    title: str
    task_type: str
    customer_need: str
    deliverable: str
    amount: float
    costs: float
    status: TaskStatus
    payment_status: PaymentStatus
    artifact_path: str
    notes: str
    created_at: str
    updated_at: str
    delivered_at: str | None = None
    settled_at: str | None = None


class XianyuSummary(BaseModel):
    total_tasks: int
    settled_tasks: int
    gross_revenue: float
    total_costs: float
    net_revenue: float
