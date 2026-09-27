"""A no-AI stand-in for Laya: answers the same questions with keyword rules.

It has Laya's interface (`predict(state, questions)` returning answers in Laya's shape), so the
whole classification pipeline - emergency screen, groups, subcategories, flags, priority rules,
routing - runs unchanged with it. Only the "reading" is different: plain keyword matching on what
the customer said, and on the recorded category when there is no text. Used when staff pick
"Keyword rules (no AI)" on the intake form, and scored against Laya by evals/laya_text_eval.py.
"""
import re

KEYWORDS_VERSION = "keywords-v1"

EMERGENCY = ["gas", "sparks", "sparking", "burning smell", "smoke", "exposed wire", "power line down",
             "line down", "burst main", "burst water main", "flooding", "flooded", "pouring out", "electric shock"]

SUBCATEGORY_WORDS: dict[str, list[str]] = {
    "Billing - disputed amount": ["bill", "charge", "charged", "overcharged", "amount", "twice", "double", "fee",
                                  "refund", "statement", "standing charge", "direct debit", "too high", "wrong"],
    "Billing - estimated read": ["estimate", "estimated", "estimation", "actual reading", "real reading"],
    "Payment - plan or arrears": ["arrears", "owe", "debt", "afford", "payment plan", "pay off", "instalment",
                                  "final notice", "bailiff", "behind on", "spread", "cut us off", "cut off"],
    "Metering - no read taken": ["meter reader", "read my meter", "meter read", "meter man", "reading visit",
                                 "not been read", "hasn't been read"],
    "Supply - interruption": ["power cut", "power has gone", "no power", "no electricity", "outage", "tripping",
                              "trips out", "flicker", "no water", "supply off", "went off", "going off", "blackout"],
    "Water - pressure or quality": ["brown", "discoloured", "cloudy", "smells", "taste", "tastes", "pressure",
                                    "trickle", "bits in", "floating", "drinking water", "tap water", "metallic"],
    "Service - missed appointment": ["engineer", "technician", "fitter", "appointment", "didn't show", "no-show",
                                     "never arrived", "didn't turn up", "never came", "waited in", "cancelled", "slot"],
    "Service - poor communication": ["no reply", "callback", "call back", "called back", "emailed", "nobody replies",
                                     "passed around", "repeat", "rude", "hung up", "unhelpful", "chat bot", "ignored"],
    "Other": ["moving house", "move house", "close my account", "closing my account", "tariff", "opening hours",
              "what time", "how do i", "change my", "switch"],
}

FLAG_WORDS: dict[str, list[str]] = {
    "disconnection": ["cut off", "cut us off", "disconnect", "disconnection", "shut off", "final notice"],
    "vulnerable": ["pensioner", "elderly", "disabled", "disability", "oxygen", "medical", "baby", "newborn",
                   "small kids", "young children", "my kids", "can't afford food", "carer", "ill ", "illness"],
    "safety_risk": ["drinking water", "bits in", "floating", "unsafe", "not safe", "brown", "oxygen", "no heating",
                    "for formula"],
    "escalation_threat": ["ombudsman", "regulator", "ofgem", "ofwat", "solicitor", "lawyer", "media", "newspaper"],
    "repeat_contact": ["again", "second time", "third time", "times", "already", "still", "before", "chased"],
    "high_bill": ["double", "twice", "much higher", "too high", "way more", "£"],
    "info_only": ["how do i", "what time", "can you tell me", "how can i", "where can i"],
}

LOSING_OUT = ["overdrawn", "can't afford", "no power", "no water", "no heating", "power cut", "took £", "taken £",
              "charged twice", "double", "defrosted", "day off work", "lost"]


def _text(state: str) -> tuple[str, str | None]:
    """The customer's words (lower case) and the recorded category from a rendered state."""
    said = state.split("Customer said:", 1)[1] if "Customer said:" in state else ""
    category = re.search(r"Category: (.+?)\.", state)
    return said.lower(), category.group(1) if category else None


def _has(text: str, words: list[str]) -> bool:
    return any(w in text for w in words)


def _choice(scores: dict[str, float]) -> dict[str, float]:
    """Turn keyword hit counts into Laya-shaped probabilities: a clear winner gets 0.9."""
    total = sum(scores.values())
    if total == 0:
        return {k: 1 / len(scores) for k in scores}
    best = max(scores, key=scores.get)
    clear = scores[best] > 1.5 * max([v for k, v in scores.items() if k != best] or [0])
    rest = (0.1 if clear else 0.5) / max(1, len(scores) - 1)
    return {k: (0.9 if clear else 0.5) if k == best else rest for k in scores}


class KeywordModel:
    """Answers Laya's questions with keyword rules. No model, no AI."""

    def __init__(self):
        from app.classification.taxonomy import GROUPS

        self._groups = GROUPS

    def _subcategory_scores(self, said: str, category: str | None, names: list[str]) -> dict[str, float]:
        scores = {n: float(sum(w in said for w in SUBCATEGORY_WORDS.get(n, []))) for n in names}
        if not any(scores.values()) and category in scores:
            scores[category] = 1.0  # no text to go on: the recorded category is the only evidence
        return scores

    def predict(self, state: str, questions: dict) -> dict:
        said, category = _text(state)
        answers: dict = {}
        for name, q in questions.items():
            if name == "emergency":
                answers[name] = {"noul": 0.95 if _has(said, EMERGENCY) else 0.0}
            elif name == "group":
                groups = list(q["criteria"])
                scores = {g: sum(self._subcategory_scores(said, category, self._groups[g]["subcategories"]).values())
                          for g in groups}
                answers[name] = {"probabilities": _choice(scores)}
            elif name == "subcategory":
                answers[name] = {"probabilities": _choice(self._subcategory_scores(said, category, list(q["criteria"])))}
            elif name == "urgency":
                level = 1 if _has(said, LOSING_OUT) else 0
                answers[name] = {"score": float(level), "probabilities": {str(i): float(i == level) for i in range(3)}}
            elif name in FLAG_WORDS:
                answers[name] = {"noul": 1.0 if said and _has(said, FLAG_WORDS[name]) else 0.0}
            else:
                answers[name] = {"noul": 0.0}
        return {"answers": answers}
