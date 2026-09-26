from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.classification.taxonomy import ROUTES


class ComplaintIn(BaseModel):
    complaint_id: str | None = None  # generated if missing
    # Laya reads a description of these fields (and the text, if there is any). New complaints have no text.
    text: str | None = Field(default=None, description="What the customer said, if recorded")
    category: str | None = Field(default=None, description="A Northwind data category, e.g. 'Billing - disputed amount'")
    priority: Literal["P1", "P2", "P3"] | None = None
    sla_days: int | None = Field(default=None, gt=0, description="Northwind's existing target, if the case has one")
    channel: str | None = None  # e.g. "Phone", "Regulator referral"
    region: str | None = None
    source_system: str | None = None  # e.g. "SYS-05"
    transferred_between_systems: bool | None = None
    date_opened: date | None = None  # used for deadline risk, not shown to Laya
    account_id: str | None = None

    @model_validator(mode="after")
    def check_input(self):
        if self.text is not None and not self.text.strip():
            self.text = None
        if self.category is not None and self.category not in ROUTES:
            raise ValueError(f"unknown category {self.category!r}; use one of {sorted(ROUTES)}")
        if self.text is None and self.category is None:
            raise ValueError("give the complaint's category or text, so there is something to classify")
        return self


class ProcessRequest(BaseModel):
    complaints: list[ComplaintIn] = Field(min_length=1, max_length=100)
    as_of_date: date | None = Field(default=None, description="Days open are measured to this date")


class GroupOut(BaseModel):
    name: str  # the group used for routing
    source: str  # "laya", or "data" when Laya was under the confidence threshold and the data had a category
    laya_name: str  # Laya's own pick, kept for comparison
    confidence: float  # Laya's top stage 1 probability
    probabilities: dict[str, float]


class SubcategoryOut(BaseModel):
    name: str  # a Northwind data category
    source: str  # "laya" or "data"
    confidence: float | None  # None when the group has only one subcategory, or the data was used


class PriorityOut(BaseModel):
    level: str  # P1, P2 or P3
    target_days: int
    base_level: str  # before flags: Northwind's priority when it has one, else Laya's urgency score
    base_source: str  # "data", "laya" or "emergency"
    urgency_score: float | None  # None when the base came from the data, and for emergencies
    raised_by: list[str]


class RoutingOut(BaseModel):
    team: str
    lane: str  # emergency, review, quick_lane or standard


class FlagOut(BaseModel):
    name: str
    source: str  # text or data
    effect: str
    probability: float | None = None
    reason: str = ""


class ClassificationResult(BaseModel):
    complaint_id: str
    classifier_version: str
    emergency: bool
    emergency_probability: float
    group: GroupOut | None = None  # None for emergencies
    subcategory: SubcategoryOut | None = None  # None for emergencies, and for low confidence with no data category
    low_confidence: bool = False  # Laya's top group probability was under the threshold
    priority: PriorityOut
    routing: RoutingOut
    flags: list[FlagOut] = []  # flags that fired
    text_flag_probabilities: dict[str, float] = {}
    # How Laya's answers compare with the category already in the data (None when the data has none).
    data_category: str | None = None
    group_matches_data: bool | None = None
    subcategory_matches_data: bool | None = None
    likely_cause: str | None = None
    classification_id: int | None = None


class ProcessResponse(BaseModel):
    as_of_date: date
    results: list[ClassificationResult]
