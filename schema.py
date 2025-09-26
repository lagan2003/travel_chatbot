# schema.py
from pydantic import BaseModel, Field
from typing import List, Optional


class Activity(BaseModel):
    time_block: str = Field(..., description="morning | afternoon | evening | night")
    title: str
    description: str
    neighborhood: Optional[str] = None
    transport: Optional[str] = None
    est_cost: Optional[float] = None
    tips: Optional[str] = None


class DayPlan(BaseModel):
    day: int
    date: Optional[str] = None
    summary: Optional[str] = None
    activities: List[Activity]
    est_daily_cost: Optional[float] = None


class BudgetBreakdown(BaseModel):
    currency: str
    total_budget: float
    lodging: float
    food: float
    transport: float
    attractions: float
    buffer_misc: float


class Itinerary(BaseModel):
    destination: str
    days: int
    start_date: Optional[str] = None
    travelers: Optional[int] = 1
    currency: str = "INR"
    budget: BudgetBreakdown
    day_plans: List[DayPlan]
    packing_list: List[str]
    safety_notes: List[str]
    local_tips: List[str]
