"""How well does Laya classify complaints from the customer's own words?

    python -m evals.laya_text_eval             # the tuning set, case by case
    python -m evals.laya_text_eval --holdout   # plus the holdout set (scores only; --verbose for detail)
    python -m evals.laya_text_eval --holdout --keywords   # the same, for the no-AI keyword rules
    python -m evals.laya_text_eval --quiet --fresh [--keywords]   # the fair comparison (see FRESH)

The backlog has no text, so it can't answer this. These are hand-written complaints (not from the
data pack, not from the simulated systems' templates), each labelled by us with the group, the
subcategory and the urgency a sensible Northwind team lead would give it. Runs the real Laya with
the real pipeline (app/classification/service.py), exactly as the intake form does.

Urgency labels: P1 harm now (safety, vulnerable customer at risk, disconnection threat),
P2 money or service at risk soon, P3 routine.
"""
from collections import Counter
from datetime import date

from app.classification.schemas import ComplaintIn
from app.classification.service import classify_complaint
from app.classification.taxonomy import CATEGORY_TO_GROUP
from app.laya_service import get_laya

# (text, expected subcategory, expected priority)
CASES: list[tuple[str, str, str]] = [
    # Billing - disputed amount
    ("My bill this month is £340, it's normally about £120. Nothing has changed at home. Please check it.",
     "Billing - disputed amount", "P2"),
    ("There's a £45 'admin charge' on my statement I never agreed to. Can you take it off?",
     "Billing - disputed amount", "P3"),
    ("You've charged me twice for August. Two direct debits came out and now I'm overdrawn.",
     "Billing - disputed amount", "P2"),
    # Billing - estimated read
    ("Every bill says ESTIMATED. Nobody has read my meter in a year and the estimate is way too high.",
     "Billing - estimated read", "P2"),
    ("I submitted my meter reading on the app but the new bill is still an estimate. Why?",
     "Billing - estimated read", "P3"),
    ("My bill is based on an estimated reading of 48,000 but the meter actually shows 41,200.",
     "Billing - estimated read", "P2"),
    # Metering - no read taken
    ("The meter reader was booked for Tuesday and never came. No card, no call.",
     "Metering - no read taken", "P3"),
    ("No one has come to read my meter for eight months. Can you send someone?",
     "Metering - no read taken", "P3"),
    # Payment - plan or arrears
    ("I lost my job and I can't pay the £600 I owe. I got a letter saying you'll cut us off next week. I have two small kids.",
     "Payment - plan or arrears", "P1"),
    ("Can I spread my arrears over six months? I can manage about £40 a month.",
     "Payment - plan or arrears", "P3"),
    ("I agreed a payment plan of £50 a month but you took £210 this month. I can't afford food now.",
     "Payment - plan or arrears", "P1"),
    # Supply - interruption
    ("The power has gone off four times this week. My dad uses a home oxygen machine and it keeps stopping.",
     "Supply - interruption", "P1"),
    ("We've had no water since this morning. Is there a problem in the area?",
     "Supply - interruption", "P2"),
    ("Lights keep flickering and going off for a few seconds every evening.",
     "Supply - interruption", "P2"),
    # Water - pressure or quality
    ("The tap water is brown and smells of chlorine. I have a newborn and I'm scared to use it for formula.",
     "Water - pressure or quality", "P1"),
    ("Water pressure upstairs has been really low for two weeks, the shower barely works.",
     "Water - pressure or quality", "P3"),
    ("Our water tastes metallic since the roadworks started outside.",
     "Water - pressure or quality", "P2"),
    # Service - missed appointment
    ("I took a day off work for the engineer, 8 to 1 slot. Nobody turned up. Second time this has happened.",
     "Service - missed appointment", "P2"),
    ("Your technician was supposed to fix my boiler connection yesterday and didn't show up.",
     "Service - missed appointment", "P2"),
    # Service - poor communication
    ("I've called five times and every time I have to explain everything again. Nobody ever calls back. I'm going to the ombudsman.",
     "Service - poor communication", "P2"),
    ("You promised a callback within 48 hours. It's been two weeks.",
     "Service - poor communication", "P3"),
    ("The person on the phone was rude and hung up on me.",
     "Service - poor communication", "P3"),
    # Other
    ("I'm moving house next month. How do I close my account and get a final bill?",
     "Other", "P3"),
    ("How do I change my tariff to a cheaper one?",
     "Other", "P3"),
    # Emergencies (should skip the queue: P1 + emergency dispatch)
    ("I can smell gas in my kitchen and it's getting stronger.", "EMERGENCY", "P1"),
    ("There's water pouring out of the road outside, it's flooding into our front garden.", "EMERGENCY", "P1"),
]


# A second set, written before any tuning and never used to choose wording - it checks that
# changes made while looking at CASES also hold up on complaints nobody tuned for.
HOLDOUT: list[tuple[str, str, str]] = [
    ("The amount you've billed me is wrong - I've checked my meter and I've used half what you say.",
     "Billing - disputed amount", "P2"),
    ("Why am I being charged a standing charge for a property I moved out of in June?",
     "Billing - disputed amount", "P3"),
    ("Third estimated bill in a row. Please use a real reading, I can send a photo.",
     "Billing - estimated read", "P2"),
    ("Your meter man hasn't been since last winter.", "Metering - no read taken", "P3"),
    ("I'm a pensioner and I can't afford the £280 you're asking for. I'm frightened of the bailiffs.",
     "Payment - plan or arrears", "P1"),
    ("I'd like to set up a direct debit to pay off what I owe gradually.", "Payment - plan or arrears", "P3"),
    ("Power cut on our street for the third night running. We have no heating.", "Supply - interruption", "P2"),
    ("The electricity keeps tripping out and my freezer has defrosted twice.", "Supply - interruption", "P2"),
    ("There are bits floating in my drinking water.", "Water - pressure or quality", "P1"),
    ("We only get a trickle from the kitchen tap in the mornings.", "Water - pressure or quality", "P3"),
    ("The engineer cancelled at the last minute and nobody has rebooked me.", "Service - missed appointment", "P2"),
    ("I waited in all day for the meter fitter and he never arrived.", "Service - missed appointment", "P2"),
    ("I've emailed three times and had no reply at all.", "Service - poor communication", "P3"),
    ("Every time I call I get passed around departments and nobody takes ownership.",
     "Service - poor communication", "P3"),
    ("What time does your customer service line open on Saturdays?", "Other", "P3"),
    ("There are sparks coming from the meter box and a burning smell.", "EMERGENCY", "P1"),
]


# A third set, written after both the Laya wording and the keyword lists were final, and never
# used to change either - the fair comparison between Laya and the keyword rules.
FRESH: list[tuple[str, str, str]] = [
    ("Got a statement for £512 this quarter. That can't be right for a one-bed flat.", "Billing - disputed amount", "P2"),
    ("You've put someone else's usage on my account, the address on the bill isn't even mine.", "Billing - disputed amount", "P3"),
    ("Please stop guessing my usage. Every quarter it's a made-up number.", "Billing - estimated read", "P2"),
    ("I keep sending readings and you keep ignoring them and billing me on a guess.", "Billing - estimated read", "P2"),
    ("I haven't seen anyone from Northwind at the house to check the meter in ages.", "Metering - no read taken", "P3"),
    ("My husband died last month and I can't keep up with the payments. I don't know what to do.", "Payment - plan or arrears", "P1"),
    ("I'm two months behind, can we come to some arrangement?", "Payment - plan or arrears", "P3"),
    ("The whole estate has been without electricity since 6pm.", "Supply - interruption", "P2"),
    ("Taps have been dry since yesterday morning, we can't flush the toilet.", "Supply - interruption", "P2"),
    ("My kettle is full of white flakes and the water looks milky.", "Water - pressure or quality", "P2"),
    ("The shower is so weak it's basically dripping.", "Water - pressure or quality", "P3"),
    ("Booked a smart meter install for Friday, nobody showed and nobody told me why.", "Service - missed appointment", "P2"),
    ("Your contractor was meant to repair the leak outside on Monday. Still waiting.", "Service - missed appointment", "P2"),
    ("I sent a letter a month ago and heard nothing back.", "Service - poor communication", "P3"),
    ("Your staff member was sarcastic and wouldn't give me her name.", "Service - poor communication", "P3"),
    ("Do you offer a discount for paying annually?", "Other", "P3"),
    ("My elderly mother's heating is electric and it's been off since last night, she's 91.", "Supply - interruption", "P1"),
    ("There's a strong smell of gas outside near the meter.", "EMERGENCY", "P1"),
]


def evaluate(cases: list[tuple[str, str, str]], label: str, laya, verbose: bool = True) -> dict:
    as_of = date(2026, 9, 30)
    levels = {"P1": 2, "P2": 1, "P3": 0}
    group_ok = sub_ok = prio_ok = prio_close = over = 0
    confusions: Counter = Counter()
    if verbose:
        print(f"\n== {label} ==\n{'expected':30} {'got':30} {'prio exp/got (base, raised by)':34} text")
    for i, (text_, expected_sub, expected_prio) in enumerate(cases, start=1):
        complaint = ComplaintIn(text=text_, channel="Phone", region="Ashford", source_system="SYS-05")
        result, _ = classify_complaint(complaint, f"EVAL-{i}", as_of, laya)
        got_sub = "EMERGENCY" if result.emergency else (result.subcategory.name if result.subcategory else "-")
        expected_group = "EMERGENCY" if expected_sub == "EMERGENCY" else CATEGORY_TO_GROUP[expected_sub]
        got_group = "EMERGENCY" if result.emergency else (result.group.name if result.group else "-")
        group_ok += got_group == expected_group
        sub_ok += got_sub == expected_sub
        got_prio = result.priority.level
        prio_ok += got_prio == expected_prio
        prio_close += abs(levels[got_prio] - levels[expected_prio]) <= 1
        over += levels[got_prio] > levels[expected_prio]
        if got_group != expected_group:
            confusions[(expected_group, got_group)] += 1
        if verbose:
            why = f"{expected_prio}/{got_prio} ({result.priority.base_level}, {'+'.join(result.priority.raised_by) or '-'})"
            mark = "  " if got_sub == expected_sub else "✗ "
            print(f"{mark}{expected_sub:28} {got_sub:30} {why:34} {text_[:55]}")
    n = len(cases)
    scores = {"group": group_ok / n, "subcategory": sub_ok / n, "urgency": prio_ok / n,
              "urgency_within_one": prio_close / n, "urgency_too_high": over / n}
    print(f"{label}: group {scores['group']:.0%} | subcategory {scores['subcategory']:.0%} | urgency exact "
          f"{scores['urgency']:.0%}, within one {scores['urgency_within_one']:.0%}, too high {scores['urgency_too_high']:.0%}")
    if confusions and verbose:
        print("  group mix-ups (expected -> got):", dict(confusions))
    return scores


def main() -> None:
    import sys

    if "--keywords" in sys.argv:  # the no-AI keyword rules instead of Laya
        from app.classification.keywords import KeywordModel

        model, name = KeywordModel(), "keyword rules (no AI)"
    else:
        model, name = get_laya(), "Laya"
    evaluate(CASES, f"Tuning set, {name}", model, verbose="--quiet" not in sys.argv)
    if "--holdout" in sys.argv:
        evaluate(HOLDOUT, f"Holdout set, {name}", model, verbose="--verbose" in sys.argv)
    if "--fresh" in sys.argv:
        evaluate(FRESH, f"Fresh set, {name}", model, verbose="--verbose" in sys.argv)


if __name__ == "__main__":
    main()
