"""Priority, flag and routing rules. Pure functions, no Laya or DB, so they are easy to test.

Priority is a level: 0 = P3 (routine), 1 = P2 (at risk soon), 2 = P1 (harm now).
Flags can only raise the level, never lower it, and the result is capped at P1.
"""
from dataclasses import dataclass
from datetime import date

from app.classification.taxonomy import (
    PRIORITY_TARGET_DAYS,
    ROUTES,
    TEAM_DISPATCH,
    TEAM_METERING,
)

LEVEL_TO_PRIORITY = {0: "P3", 1: "P2", 2: "P1"}
PRIORITY_TO_LEVEL = {p: level for level, p in LEVEL_TO_PRIORITY.items()}
MAX_LEVEL = 2

LEGACY_REGIONS = {"barrowdale", "dunmoor"}
LEGACY_SUBCATEGORIES = {"Billing - estimated read", "Metering - no read taken"}
DEADLINE_RISK_SHARE = 0.75

# Text flags: name -> (effect, level). "at_least" sets a floor, "raise_one" adds a level,
# "quick_lane" changes the lane and not the priority.
TEXT_FLAG_EFFECTS: dict[str, tuple[str, int | None]] = {
    "disconnection": ("at_least", 1),
    "vulnerable": ("at_least", 2),
    "escalation_threat": ("at_least", 1),
    "repeat_contact": ("raise_one", None),
    "high_bill": ("at_least", 1),
    "info_only": ("quick_lane", None),
}


@dataclass
class FlagHit:
    name: str
    source: str  # "text" or "data"
    effect: str  # "at_least", "raise_one", "quick_lane", "route_metering" or "marker" (display only)
    level: int | None = None  # for "at_least"
    probability: float | None = None  # for text flags
    reason: str = ""


@dataclass
class PriorityDecision:
    base_level: int
    level: int
    driving_flags: list[str]  # flags that set the final level (empty if nothing raised it)

    @property
    def priority(self) -> str:
        return LEVEL_TO_PRIORITY[self.level]

    @property
    def target_days(self) -> int:
        return PRIORITY_TARGET_DAYS[self.priority]


def text_flag_hits(probabilities: dict[str, float], threshold: float) -> list[FlagHit]:
    """Text flags that fired, from Laya's yes-probabilities."""
    hits = []
    for name, (effect, level) in TEXT_FLAG_EFFECTS.items():
        p = probabilities.get(name)
        if p is not None and p >= threshold:
            hits.append(FlagHit(name, "text", effect, level, probability=p))
    return hits


def legacy_region_hit(region: str | None, subcategory: str | None) -> FlagHit | None:
    if region and region.lower() in LEGACY_REGIONS and subcategory in LEGACY_SUBCATEGORIES:
        return FlagHit(
            "legacy_region", "data", "route_metering",
            reason="Barrowdale or Dunmoor with an estimated-read or no-read complaint: likely estimated reading",
        )
    return None


def regulator_referral_hit(channel: str | None) -> FlagHit | None:
    if channel and channel.strip().lower() == "regulator referral":
        return FlagHit("regulator_referral", "data", "at_least", 1, reason="arrived through the regulator")
    return None


def days_open(date_opened: date | None, as_of: date) -> int | None:
    return (as_of - date_opened).days if date_opened else None


def deadline_risk_hit(open_days: int | None, target_days: int) -> FlagHit | None:
    if open_days is not None and open_days > DEADLINE_RISK_SHARE * target_days:
        return FlagHit(
            # "marker": shown to staff, but it never changes the urgency. Urgency is about what the
            # complaint says; how long it has waited is the worklist's second sort key (days overdue).
            "deadline_risk", "data", "marker",
            reason=f"open {open_days} days, over {int(DEADLINE_RISK_SHARE * 100)}% of the {target_days}-day target",
        )
    return None


def combine_priority(base_level: int, hits: list[FlagHit]) -> PriorityDecision:
    """Start from the urgency score, then take the highest level any flag requires."""
    required = {}
    for hit in hits:
        if hit.effect == "at_least":
            required[hit.name] = hit.level
        elif hit.effect == "raise_one":
            required[hit.name] = min(MAX_LEVEL, base_level + 1)
    final = min(MAX_LEVEL, max([base_level, *required.values()]))
    driving = [name for name, level in required.items() if level == final] if final > base_level else []
    return PriorityDecision(base_level=base_level, level=final, driving_flags=driving)


def route(subcategory: str, *, hits: list[FlagHit]) -> tuple[str, str]:
    """Return (team, lane). Lanes: quick_lane, standard (emergencies are routed before this)."""
    team = ROUTES[subcategory]
    if any(h.effect == "route_metering" for h in hits):
        team = TEAM_METERING
    lane = "quick_lane" if any(h.effect == "quick_lane" for h in hits) else "standard"
    return team, lane


def emergency_route() -> tuple[str, str]:
    return TEAM_DISPATCH, "emergency"
