"""The no-AI version of the two case buttons: same systems, plain rules, no model.

"Get context" and "Generate draft" normally run a local LLM. This does the same job without any AI:
it pulls the same records from Northwind's systems (app/agents/systems.py - that part was never AI),
reads our own database with SQL, and turns the facts into action items and a reply with fixed,
readable rules and templates. It runs when staff switch AI off, when AI is disabled
(AGENT_ENABLED=false, requirement N6), and as the fallback when an AI run fails.

If Helix can't be reached, the rules still work from our own database (the case, the account's
earlier complaints, how similar cases were resolved).
"""
from dataclasses import dataclass, field

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.agents.systems import NorthwindLookups
from app.models import ActionItem, Complaint, DraftResponse

MAX_ACTIONS = 5
_DISTRESS_WORDS = ("disconnect", "cut off", "cutoff", "final notice", "in tears", "distressed", "oxygen")
_ESCALATION_WORDS = ("ombudsman", "regulator", "solicitor", "lawyer", "media")
# How the draft names the complaint: "Thank you for getting in touch about your ...".
_TOPIC = {
    "Billing - estimated read": "estimated bill", "Billing - disputed amount": "bill",
    "Metering - no read taken": "meter readings", "Payment - plan or arrears": "account balance and payment plan",
    "Supply - interruption": "supply interruptions", "Water - pressure or quality": "water supply",
    "Service - missed appointment": "missed appointment", "Service - poor communication": "complaint",
    "Other": "enquiry",
}


@dataclass
class Facts:
    complaint: Complaint
    customer: dict | None = None
    bills: list[dict] | None = None
    calls: list[dict] | None = None
    case: dict | None = None
    connect: dict | None = None
    profile: dict | None = None  # similar closed cases (our database)
    history: list[dict] = field(default_factory=list)  # the account's other complaints (our database)

    # Derived, for the rules and the draft.
    @property
    def regular_bills(self) -> list[dict]:
        return [b for b in (self.bills or []) if b["read_type"] != "CORRECTION"]

    @property
    def estimated_streak(self) -> int:
        n = 0
        for b in self.regular_bills:
            if b["read_type"] != "ESTIMATED":
                break
            n += 1
        return n

    @property
    def typical_amount(self) -> float | None:
        older = sorted(b["amount"] for b in self.regular_bills[3:])
        return older[len(older) // 2] if older else None

    @property
    def unprocessed_reading(self) -> dict | None:
        readings = (self.connect or {}).get("readings", [])
        return next((r for r in readings if "NOT PROCESSED" in r["processingStatus"]), None)

    @property
    def chases(self) -> int:
        return sum(1 for c in self.calls or [] if c["wrapUpCode"].endswith("-CHS"))

    def mentions(self, words: tuple[str, ...]) -> str | None:
        """The first call note or customer message that mentions any of the words."""
        texts = [c["notes"] for c in self.calls or []] + [m["body"] for m in (self.connect or {}).get("messages", [])]
        return next((t for t in texts if any(w in t.lower() for w in words)), None)


def gather(db: Session, complaint: Complaint, look: NorthwindLookups) -> Facts:
    """Everything the rules need, from the systems (traced) and from our own database."""
    facts = Facts(complaint=complaint)
    facts.customer, _ = look.customer()
    if facts.customer:
        facts.bills, _ = look.bills()
        facts.calls, _ = look.calls()
        facts.connect, _ = look.messages()
    facts.case, _ = look.case()
    facts.profile = db.execute(text(
        "SELECT n, avg_days, top_resolution FROM v_case_profile "
        "WHERE category = :c AND region = :r AND source_system = :s"
    ), {"c": complaint.category, "r": complaint.region, "s": complaint.source_system}).mappings().first()
    facts.history = [dict(r) for r in db.execute(text(
        "SELECT complaint_id, date_opened, category, status, resolution_action FROM v_account_history "
        "WHERE account_id = :a AND complaint_id != :id ORDER BY date_opened DESC LIMIT 10"
    ), {"a": complaint.account_id, "id": complaint.complaint_id}).mappings().all()]
    return facts


def _money(v: float) -> str:
    return f"£{v:,.2f}"


def _clip(s: str, n: int = 90) -> str:
    return s if len(s) <= n else s[: n - 1].rstrip() + "…"


def action_items(f: Facts) -> list[tuple[str, str, str]]:
    """(action_type, description, rationale), most urgent first. Every item names its source."""
    items: list[tuple[str, str, str]] = []
    c = f.customer
    cat = f.complaint.category

    if c and c["priorityServicesRegister"]:
        needs = ", ".join(p["need"] for p in c["priorityServicesRegister"])
        items.append(("vulnerability", "Handle under Priority Services: prioritise contact and do not start recovery "
                      "or disconnection steps.", f"Helix CIS: on the Priority Services Register ({needs})."))
    distress = f.mentions(_DISTRESS_WORDS)
    if distress:
        items.append(("hold_recovery", "Confirm to the customer that any recovery or disconnection action is on hold "
                      "while the complaint is open.", f"Customer contact: \"{_clip(distress)}\""))
    if f.chases >= 2:
        items.append(("call_back", f"Call the customer back today with a named contact - they have chased {f.chases} "
                      "times without an update.", f"CallCentre One: {f.chases} chase calls, latest "
                      f"{f.calls[0]['startedAt'][:10]}."))
    escalation = f.mentions(_ESCALATION_WORDS)
    if escalation:
        items.append(("escalation_risk", "Treat as an escalation risk: have a team lead review the case this week.",
                      f"Customer contact: \"{_clip(escalation)}\""))

    reading = f.unprocessed_reading
    if f.estimated_streak >= 2 and reading:
        items.append(("rebill_from_reading", f"Re-bill using the reading the customer already submitted ({reading['value']} "
                      f"on {reading['submittedAt'][:10]}) instead of booking a visit.",
                      f"Connect: reading {reading['processingStatus'].lower()}; billing: last {f.estimated_streak} "
                      "bills estimated."))
    elif f.estimated_streak >= 2:
        items.append(("book_meter_read", "Book an actual meter read and re-bill from it.",
                      f"Billing: last {f.estimated_streak} bills were estimated."))
    typical, bills = f.typical_amount, f.regular_bills
    if typical and bills and bills[0]["amount"] > 1.4 * typical:
        items.append(("review_bill", f"Review and correct the {bills[0]['issued']} bill of {_money(bills[0]['amount'])} "
                      f"against the usual ~{_money(typical)}.", f"Billing: latest bill is "
                      f"{bills[0]['amount'] / typical:.1f}x the usual amount."))
        if c and c["paymentMethod"] == "Direct Debit" and bills[0]["status"] == "DISPUTED":
            items.append(("pause_direct_debit", "Pause the Direct Debit for the disputed amount until the bill is corrected.",
                          "Helix CIS: pays by Direct Debit; billing: latest bill disputed."))

    if c and c["balance"]["arrears"] > 0:
        plan, arrears = c["paymentArrangement"], _money(c["balance"]["arrears"])
        if plan and plan["status"] == "ACTIVE - NOT APPLIED":
            items.append(("apply_payment_plan", f"Apply the agreed payment plan ({_money(plan['agreed_monthly'])}/month) - "
                          "it is agreed but not applied to the account.", f"Helix CIS: arrears {arrears}, plan {plan['status']}."))
        elif plan and plan["status"] == "PROPOSED":
            items.append(("approve_payment_plan", f"Approve the proposed payment plan of {_money(plan['agreed_monthly'])}/month "
                          "and confirm it to the customer.", f"Helix CIS: arrears {arrears}, plan proposed {plan['agreed_on']}."))
        elif plan:
            items.append(("reset_payment_plan", "Contact the customer to agree a new, affordable payment plan.",
                          f"Helix CIS: arrears {arrears}, plan {plan['status'].lower()}."))
        else:
            items.append(("offer_payment_plan", f"Offer an affordable payment plan for the {arrears} outstanding.",
                          f"Helix CIS: arrears {arrears}, no arrangement in place."))

    if f.case and f.case["importedViaBatch"]:
        items.append(("restore_history", "Add the call history and customer messages to the CaseTrack case before it is "
                      "handed on.", f"CaseTrack {f.case['caseRef']}: imported by batch, earlier notes not migrated."))

    category_step = {
        "Supply - interruption": ("check_network_fault", "Check GridWatch for a fault in the area and give the customer a fault reference."),
        "Water - pressure or quality": ("raise_water_ops", "Raise with Water Operations and confirm the safety advice given to the customer."),
        "Service - missed appointment": ("rebook_and_compensate", "Rebook the appointment at a confirmed time and assess compensation for the missed one."),
        "Service - poor communication": ("named_handler", "Assign a named handler and agree a callback date with the customer."),
        "Other": ("send_information", "Send the customer the information they asked for."),
    }.get(cat)
    if category_step:
        items.append((*category_step, f"Case category: {cat}."))

    if f.profile and f.profile["top_resolution"]:
        items.append(("likely_resolution", f"Likely resolution: {f.profile['top_resolution'].lower()}.",
                      f"Northwind case history: most common outcome for {f.profile['n']} similar cases "
                      f"(average {float(f.profile['avg_days']):.0f} days)."))
    if not c and f.history:
        last = f.history[0]
        items.append(("review_history", f"Review the account's {len(f.history)} earlier complaints before contacting the customer.",
                      f"Northwind database: last one {last['date_opened']} ({last['category']}, {last['status']})."))

    seen, unique = set(), []
    for item in items:
        if item[0] not in seen:
            seen.add(item[0])
            unique.append(item)
    return unique[:MAX_ACTIONS]


def draft_reply(f: Facts) -> str:
    """A reply from fixed templates and the facts found. Promises nothing the records don't confirm."""
    c = f.customer
    greeting = f"Dear {c['name']['title']} {c['name']['family']}," if c else "Dear Customer,"
    topic = _TOPIC.get(f.complaint.category, "complaint")
    sorry = (f"I'm sorry you've had to contact us {f.chases + 1} times about this, and that you haven't had the update you were promised."
             if f.chases >= 2 else "I'm sorry for the trouble this has caused.")
    paras = [f"Thank you for getting in touch about your {topic}. {sorry}"]

    facts = []
    bills, typical, reading = f.regular_bills, f.typical_amount, f.unprocessed_reading
    if f.estimated_streak >= 2:
        facts.append(f"your last {f.estimated_streak} bills were based on estimated readings rather than an actual reading")
    if typical and bills and bills[0]["amount"] > 1.4 * typical:
        facts.append(f"your bill of {_money(bills[0]['amount'])} dated {bills[0]['issued']} is well above your usual "
                     f"amount of around {_money(typical)}")
    if reading:
        facts.append(f"you sent us a meter reading of {reading['value']} on {reading['submittedAt'][:10]}, which has not yet "
                     "been used on your bill")
    if c and c["balance"]["arrears"] > 0:
        facts.append(f"your account currently shows {_money(c['balance']['arrears'])} outstanding")
    if facts:
        paras.append("I've looked at your account, and I can see that " + "; ".join(facts[:-1])
                     + (" and " if len(facts) > 1 else "") + facts[-1] + ".")

    next_steps = []
    if reading and f.estimated_streak >= 2:
        next_steps.append("I've asked for your bill to be reviewed using the reading you sent us")
    elif f.estimated_streak >= 2:
        next_steps.append("I've asked for an actual meter reading to be arranged so your bill can be reviewed")
    elif typical and bills and bills[0]["amount"] > 1.4 * typical:
        next_steps.append("I've asked our billing team to check that bill in detail")
    if c and c["balance"]["arrears"] > 0:
        next_steps.append("we'll work with you on a payment arrangement you can afford, and no recovery action will be "
                          "taken while we sort this out")
    if not next_steps:
        next_steps.append("I've passed your case to the right team and asked them to look into it")
    paras.append(next_steps[0][0].upper() + next_steps[0][1:] + ("; " + "; ".join(next_steps[1:]) if next_steps[1:] else "")
                 + ". I'll contact you again as soon as I have an update.")
    if c and c["priorityServicesRegister"]:
        paras.append("As you're on our Priority Services Register, please call us straight away if anything changes "
                     "or you need extra support.")
    return greeting + "\n\n" + "\n\n".join(paras) + "\n\nKind regards,\n\n[Your name], Northwind Energy & Water"


def run_context(db: Session, complaint: Complaint, look: NorthwindLookups, run_id: int) -> None:
    facts = gather(db, complaint, look)
    for rank, (action_type, description, rationale) in enumerate(action_items(facts), start=1):
        db.add(ActionItem(complaint_id=complaint.complaint_id, run_id=run_id, action_type=action_type,
                          description=description, rationale=rationale, rank=rank))
    db.flush()


def run_draft(db: Session, complaint: Complaint, look: NorthwindLookups, run_id: int) -> None:
    db.add(DraftResponse(complaint_id=complaint.complaint_id, run_id=run_id, body=draft_reply(gather(db, complaint, look))))
    db.flush()
