"""Complaint groups, subcategories, routing, and the Laya questions built from them."""

# Group descriptions are what Laya matches the complaint against, so they use the words customers use.
# Tuned against evals/laya_text_eval.py (run it after any change here).
GROUPS: dict[str, dict] = {
    "Billing": {
        "description": "money: a bill or charge that is too high, wrong, doubled or not recognised, a bill "
        "based on an estimated reading, fees or direct debits taken, or trouble paying - arrears, debt, "
        "final notices and payment plans",
        "subcategories": ["Billing - disputed amount", "Billing - estimated read", "Payment - plan or arrears"],
    },
    "Metering": {
        "description": "the meter reading itself: nobody has come to read the meter for months, or a meter "
        "reading visit did not happen",
        "subcategories": ["Metering - no read taken"],
    },
    "Field services": {
        "description": "the physical supply or a home visit: an engineer or technician who did not turn up "
        "or cancelled, power cuts, electricity tripping, flickering or going off, no water, low water "
        "pressure, brown, cloudy, smelly or bad-tasting water, or bits in the water",
        "subcategories": ["Supply - interruption", "Water - pressure or quality", "Service - missed appointment"],
    },
    "Customer support": {
        "description": "our staff or our communication, not the supply: no reply to emails, no callback, "
        "being passed between departments, having to repeat themselves, rude or unhelpful staff",
        "subcategories": ["Service - poor communication"],
    },
    "General": {
        "description": "a simple question or request where nothing has gone wrong: moving house and getting a "
        "final bill, closing or opening an account, switching to a different tariff, opening hours",
        "subcategories": ["Other"],
    },
}

# Stage 2 descriptions, only used for groups with more than one subcategory.
SUBCATEGORY_CRITERIA: dict[str, str] = {
    "Billing - disputed amount": "the customer disputes the amount billed: bill too high, wrong or duplicate charge",
    "Billing - estimated read": "the bill is based on an estimated reading instead of an actual meter reading",
    "Payment - plan or arrears": "the customer cannot pay, is in arrears, or asks for a payment plan or more time",
    "Supply - interruption": "the power or water supply is off or keeps cutting out",
    "Water - pressure or quality": "low water pressure, or water that is discoloured, smelly or tastes bad",
    "Service - missed appointment": "an engineer or technician did not turn up to a booked appointment",
}

CATEGORY_TO_GROUP: dict[str, str] = {
    category: group for group, g in GROUPS.items() for category in g["subcategories"]
}

# Northwind data category -> team.
ROUTES: dict[str, str] = {
    "Billing - disputed amount": "Billing team",
    "Billing - estimated read": "Metering team",
    "Payment - plan or arrears": "Collections",
    "Metering - no read taken": "Metering team",
    "Supply - interruption": "Network operations",
    "Water - pressure or quality": "Water operations",
    "Service - missed appointment": "Field services",
    "Service - poor communication": "Customer care leads",
    "Other": "General review queue",
}

TEAM_METERING = "Metering team"
TEAM_REVIEW = "General review queue"
TEAM_DISPATCH = "Emergency dispatch"

# Northwind priority -> target resolution days.
PRIORITY_TARGET_DAYS = {"P1": 5, "P2": 10, "P3": 20}
TARGET_DAYS_TO_PRIORITY = {days: p for p, days in PRIORITY_TARGET_DAYS.items()}

URGENCY_LEVELS = [
    "Routine: a question, a request, a disputed charge or poor service - annoying, but nobody is losing "
    "money or going without a service right now",
    "Losing out now: the customer is out of pocket right now, or is going without power, water or a "
    "service they need",
    "Danger: someone's health or safety is at risk, or a vulnerable person (elderly, ill, young children, "
    "medical equipment) could be seriously harmed",
]

# The spec does not word the emergency screen, so this is our wording.
EMERGENCY_QUESTION = {
    "type": "noul",
    "instructions": "Does the complaint describe an immediate safety emergency, such as a gas smell, "
    "sparking or exposed wires, a downed power line, a burst water main or flooding?",
}

TEXT_FLAG_QUESTIONS: dict[str, str] = {
    "disconnection": "Does the customer mention a disconnection or shutoff notice?",
    "vulnerable": "Does the customer mention a medical need, disability, old age, young children or a baby, "
    "or serious financial hardship such as not affording food?",
    "safety_risk": "Does the complaint describe a risk to someone's health or safety, such as unsafe or "
    "contaminated drinking water, or no heating or power for someone who is ill?",
    "escalation_threat": "Does the customer mention the regulator, a lawyer, or the media?",
    "repeat_contact": "Does the customer say they have complained about this before?",
    "high_bill": "Does the customer say the bill is much higher than normal?",
    "info_only": "Can this be resolved by providing information alone?",
}


def stage1_questions() -> dict[str, dict]:
    """Group, urgency score and the text flags, answered in one Laya call."""
    questions: dict[str, dict] = {
        "group": {
            "type": "choice",
            "instructions": "What is the customer mainly complaining about?",
            "criteria": {name: g["description"] for name, g in GROUPS.items()},
        },
    }
    questions["urgency"] = {
        "type": "score",
        "instructions": "How urgent is this complaint?",
        "criteria": URGENCY_LEVELS,
    }
    for name, instructions in TEXT_FLAG_QUESTIONS.items():
        questions[name] = {"type": "noul", "instructions": instructions}
    return questions


def stage2_question(group: str) -> dict:
    """Subcategory choice within one group. Only call for groups with several subcategories."""
    subcategories = GROUPS[group]["subcategories"]
    return {
        "type": "choice",
        "instructions": "Which of these is the complaint about?",
        "criteria": {name: SUBCATEGORY_CRITERIA[name] for name in subcategories},
    }
