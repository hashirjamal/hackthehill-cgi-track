"""Text templates for the simulated Northwind systems, by complaint category.

Three voices, on purpose:
- the customer (Northwind Connect web messages): full sentences, emotional, sometimes typos
- call-centre agents (CallCentre One wrap-up notes): terse shorthand typed during a call
- case handlers (CaseTrack notes): semi-formal, often written days apart by different people

Placeholders: {amount} {usual} {afford} {months} {date} {reading} {days}.
"""

CUSTOMER_MESSAGES: dict[str, list[str]] = {
    "Billing - estimated read": [
        "My bill this month is {amount} which is way more than the usual {usual}. It says ESTIMATED at the top. "
        "Nobody has read my meter in months and I submitted a reading on the app on {date} which you seem to have ignored. "
        "Please correct this.",
        "Hi, why is my bill estimated AGAIN? That's {months} bills in a row now. I sent you a photo of the meter "
        "showing {reading}. The estimate is miles off and I am not paying {amount} for electricity I haven't used.",
        "I have been estimated for ages and now I've got a bill for {amount}. I can read the meter myself - it's "
        "{reading}. Can someone actually look at this instead of sending another automated email",
    ],
    "Billing - disputed amount": [
        "I've been charged {amount} this month. I normally pay around {usual}. Nothing has changed in the house. "
        "I think there's been a mistake and I'd like the bill checked and corrected.",
        "There is a charge on my latest bill I don't recognise. Total came to {amount}. I've looked at my usage in the "
        "app and it doesnt add up. Please explain or refund.",
        "Second time I'm writing about this. The bill for {amount} is wrong. I was told on the phone it would be "
        "looked into and heard nothing since. I want a breakdown of the charges.",
    ],
    "Metering - no read taken": [
        "Nobody has come to read my meter for {months} months. Every bill is an estimate. I work from home, I'm "
        "in most days, there's no reason for this. Can you book a reading please.",
        "Your meter reader was supposed to come on {date} and never turned up. No card through the door, nothing. "
        "My bills keep going up on estimates.",
    ],
    "Payment - plan or arrears": [
        "I've fallen behind on my bills after losing hours at work and I've got a letter saying I owe {amount}. "
        "I want to pay but I can't do it all at once. Can I set up a payment plan I can actually afford?",
        "I agreed a payment plan on the phone but the amount taken this month was higher than agreed. I'm now "
        "overdrawn. I'm really worried about getting cut off, I have a young baby at home.",
        "I received a final notice for {amount}. I didn't know I was in arrears - my direct debit was cancelled "
        "without anyone telling me. Please don't disconnect us, I'll pay what I can.",
    ],
    "Supply - interruption": [
        "We've had the power go off three times this week, each time for a few hours. Food in the freezer is "
        "ruined. Is there a fault in the area? Nobody is telling us anything.",
        "Supply cut out again last night. My mum is on oxygen at home and this is really dangerous. I need to "
        "know what's being done.",
    ],
    "Water - pressure or quality": [
        "The water from the kitchen tap has been brown for {days} days. I'm not letting the kids drink it. "
        "Is it safe? When will it be fixed?",
        "Water pressure has been really low since the roadworks started - barely a trickle upstairs in the "
        "mornings. Can someone check it.",
    ],
    "Service - missed appointment": [
        "I took a day off work for an engineer appointment on {date} (8am-1pm slot). Nobody came and nobody called. "
        "This is the second time. I want compensation for my lost day.",
        "Engineer no-show AGAIN. I waited in all day. When I called I was told the job had been 'closed'. "
        "I still have the fault.",
    ],
    "Service - poor communication": [
        "I've called four times about my complaint and every time I have to explain everything from the start. "
        "Nobody calls back when they say they will. I'm going to the ombudsman if this isn't sorted.",
        "I was promised a call back within 48 hours. That was {days} days ago. Your chat bot just loops. "
        "I'd like a named person to deal with my case please.",
    ],
    "Other": [
        "I'm moving house at the end of the month and want to know how to close my account and get a final bill. "
        "The website doesn't say.",
        "Can you tell me how to change my tariff? I've been on the same one for years and I think I'm paying "
        "too much.",
    ],
}

# CallCentre One wrap-up notes. Agents type these at speed, between calls.
CALL_NOTES: dict[str, dict[str, list[str]]] = {
    "Billing - estimated read": {
        "first": [
            "cust rang re high bill {amount}, bill est (E) - cust says no rdg taken in {months} mths. adv submit own rdg "
            "via app. cust unhappy, says already did. raised to billing",
            "HIGH BILL - EST RD. cust gave rdg {reading} over phone. told him bill will be revised 5-7 wd. cust sceptical",
            "cust v upset re est bill. checked Aurora, last actual rd over {months} mths ago. logged for re-bill",
        ],
        "chase": [
            "cust chasing re-bill, nothing recvd. 2nd call re same. apologised, re-escalated. cb req",
            "3rd contact re est bill. cust threatening to cancel DD. adv case still with billing. no ETA avail",
            "cust called back - says rdg submitted but new bill STILL est. couldnt see rdg in our sys. referred again",
            "cust asking why DD still taking est amt while disputed. adv cant amend DD from CRM - raised w billing",
        ],
    },
    "Billing - disputed amount": {
        "first": [
            "cust disputing bill {amount} (usual ~{usual}). no change in occupancy. raised dispute w billing",
            "BILL DISP - cust says charges incorrect. couldnt see breakdown in Connect, had to check Aurora screen. "
            "adv 10 wd for review",
            "cust querying {amount} charge. explained std charge + unit rate, cust not satisfied, wants itemised bill",
        ],
        "chase": [
            "cust chasing dispute outcome. no update on case. apologised. cust asked for manager - none avail, cb req",
            "2nd call re disputed bill. cust says DD still taking full amt. adv DD can be paused - not done by prev agent",
            "cust chasing itemised bill - still not sent. cust says will go to ombudsman. escalated to TL",
            "cust rang for update. billing say review 'in progress'. no date. cust v frustrated",
        ],
    },
    "Metering - no read taken": {
        "first": [
            "no rd taken {months} mths. cust in most days. booked meter visit (FieldForce ref not avail - no link). "
            "adv cust we'd call to confirm",
            "cust says meter reader missed appt {date}. no card left. rebooked. cust wants bills revised",
        ],
        "chase": [
            "cust chasing meter visit - no confirmation recvd. couldnt see booking in our sys. rebooked AGAIN",
            "cust says 2nd visit also missed. no card left. cust asked if they can send photo instead - adv use app",
            "cust chasing revised bill after rd. no re-bill yet. referred to billing",
        ],
    },
    "Payment - plan or arrears": {
        "first": [
            "cust in arrears {amount}, reduced hrs at work. discussed PP - cust can afford approx {afford}/mth. "
            "sent to collections for approval. VULN? - young child mentioned",
            "cust recvd final notice {amount}. says DD cancelled w/o notice. put 14 day hold on recovery. PP req",
            "PP DISP - cust says amt taken > agreed. checked - PP not applied correctly. raised to collections URGENT",
        ],
        "chase": [
            "cust chasing PP confirmation. still showing full arrears. cust v distressed re disconnection. escalated",
            "cust rang re letter threatening recovery action despite hold. apologised. confirmed hold still on (?)",
            "cust asking if PP approved - collections no response on case. cust says cant afford full amt this mth",
            "cust in tears on call, worried re cutoff w young child. escalated URGENT to collections TL. cb req today",
        ],
    },
    "Supply - interruption": {
        "first": [
            "SUPPLY INT - cust reports repeated outages this wk. checked - no GridWatch view from CRM. logged w network",
            "cust reports power off x3 this wk. MEDICAL - relative on oxygen. flagged PRIORITY, passed to network ops",
        ],
        "chase": [
            "cust chasing outage cause. network have no update on case. cust asked about compensation",
            "another outage overnight per cust. still no fault ref from network. cust wants engineer out",
        ],
    },
    "Water - pressure or quality": {
        "first": [
            "WTR QUAL - brown water {days} days. adv run cold tap 20 mins, do not drink if persists. logged w water ops",
            "low pressure since roadworks. no visibility of AquaTrack jobs from here. logged, adv 5 wd",
        ],
        "chase": [
            "cust chasing water quality issue. still discoloured. no update from water ops on case",
            "cust says neighbours same issue. asked if water safe for baby formula - adv boil + use bottled til cleared",
        ],
    },
    "Service - missed appointment": {
        "first": [
            "APPT MISSED {date} AM slot. no engineer, no call. 2nd time. apologised. rebooked. cust wants comp",
            "cust says eng no-show, job showing closed in FieldForce?? couldnt reopen from CRM. raised manually",
        ],
        "chase": [
            "cust chasing comp for missed appt. no record of claim on case. raised again",
            "rebooked appt ALSO missed per cust. v angry. escalated to field TL",
        ],
    },
    "Service - poor communication": {
        "first": [
            "cust frustrated - 4th call, has to repeat story every time. no notes from prev calls visible. "
            "cust mentioned ombudsman",
            "COMMS COMP - promised cb 48hrs, none recvd {days} days. apologised, cust wants named contact",
        ],
        "chase": [
            "cust called again, no cb recvd AGAIN. v angry. says will go to regulator. escalated to TL",
            "cust asking for named contact - none assigned on case. apologised. cb req",
        ],
    },
    "Other": {
        "first": [
            "GEN ENQ - cust moving house, asked how to close acct + final bill. explained process, sent link",
            "cust asked re tariff options. explained, sent comparison by email",
        ],
        "chase": [
            "cust called back - didnt recv email. resent",
        ],
    },
}

WRAP_CODES: dict[str, str] = {
    "Billing - estimated read": "EST-RD",
    "Billing - disputed amount": "BILL-DISP",
    "Metering - no read taken": "NO-RD",
    "Payment - plan or arrears": "PAY-ARR",
    "Supply - interruption": "SUPPLY-INT",
    "Water - pressure or quality": "WTR-QUAL",
    "Service - missed appointment": "APPT-MISS",
    "Service - poor communication": "COMMS-COMP",
    "Other": "GEN-ENQ",
}

# CaseTrack case notes: (who, note).
CASE_NOTES: dict[str, list[str]] = {
    "Billing - estimated read": [
        "Customer disputes estimated bill of {amount}. Last actual read on record is over {months} months old. "
        "Requested actual read from metering.",
        "Checked meter read history. Estimation appears high relative to prior consumption. Awaiting read.",
    ],
    "Billing - disputed amount": [
        "Customer disputes bill of {amount} (typical {usual}). Requested bill breakdown from billing team.",
        "Billing confirm charges under review. No breakdown available from self-service; manual extract requested.",
    ],
    "Metering - no read taken": [
        "No read obtained for {months} months. Meter visit requested. FieldForce booking to be confirmed by phone.",
    ],
    "Payment - plan or arrears": [
        "Customer in arrears ({amount}). Affordability discussed; payment plan proposal sent to Collections.",
        "Recovery action placed on hold pending payment plan approval. Possible vulnerability noted.",
    ],
    "Supply - interruption": [
        "Repeated supply interruptions reported. Passed to Network Operations for fault investigation.",
    ],
    "Water - pressure or quality": [
        "Water quality/pressure issue reported. Passed to Water Operations. Customer advised on interim safety.",
    ],
    "Service - missed appointment": [
        "Missed engineer appointment on {date}. Rebooked. Customer requests compensation - to be assessed.",
    ],
    "Service - poor communication": [
        "Customer reports repeated failure to call back. Case assigned a named handler.",
    ],
    "Other": [
        "General enquiry logged. Information to be sent to customer.",
    ],
}

TRANSFER_NOTE = (
    "Case received via nightly batch import from {system}. Prior notes and contact history were not migrated - "
    "see originating system."
)

STILL_OPEN_NOTES = [
    "Awaiting response from {team}. Chased.",
    "No update received. Chased {team} again.",
    "Customer contacted for update - advised case still under review.",
]

FIRST_NAMES = [
    "James", "Sarah", "Mohammed", "Emma", "David", "Olivia", "Daniel", "Aisha", "Thomas", "Chloe", "Priya",
    "Michael", "Hannah", "Oliver", "Grace", "Liam", "Fatima", "Jack", "Sophie", "Ryan", "Megan", "Adam", "Zara",
    "Christopher", "Lucy", "Samuel", "Amelia", "Ben", "Jessica", "Tariq", "Ellie", "George", "Niamh", "Kwame",
    "Rachel", "Harry", "Imran", "Katie", "Lewis", "Anna", "Joseph", "Yasmin", "Callum", "Rebecca", "Nathan",
]
LAST_NAMES = [
    "Smith", "Jones", "Taylor", "Brown", "Williams", "Wilson", "Johnson", "Davies", "Patel", "Robinson", "Wright",
    "Thompson", "Evans", "Walker", "White", "Roberts", "Green", "Hall", "Wood", "Jackson", "Clarke", "Khan",
    "Hughes", "Edwards", "Turner", "Hill", "Moore", "Cooper", "Ward", "Morris", "King", "Harris", "Ali", "Begum",
    "Murphy", "Kelly", "Bennett", "Shaw", "Holmes", "Mills", "Okafor", "Nowak", "Singh", "Price", "Marshall",
]
STREETS = [
    "Mill Lane", "Station Road", "Church Street", "Victoria Road", "Park Avenue", "Queens Road", "The Crescent",
    "Oak Drive", "Meadow Close", "High Street", "Kingsway", "Orchard Way", "Willow Grove", "Bridge Street",
]
# Fictional postcode areas for the fictional regions.
POSTCODE_AREAS = {
    "Ashford": "AF", "Barrowdale": "BW", "Calderfield": "CF", "Dunmoor": "DM", "Eastmarch": "EM", "Fenwick": "FN",
}
PSR_NEEDS = [
    "Medical equipment reliant on power", "Pensionable age", "Young children under 5", "Hearing impaired",
    "Mental health condition", "Temporary - recent bereavement",
]
AGENTS = [
    ("AGT-0412", "K. Mensah"), ("AGT-0233", "L. Carter"), ("AGT-0587", "J. Novak"), ("AGT-0119", "S. Reid"),
    ("AGT-0654", "M. Hussain"), ("AGT-0301", "D. Lowe"), ("AGT-0776", "P. Quinn"), ("AGT-0048", "R. Bell"),
]
CASE_HANDLERS = ["T. Ashworth", "B. Osei", "C. Fairbairn", "N. Doyle", "H. Lindqvist", "E. Varga"]
OWNER_TEAMS = {
    "Billing - estimated read": "Metering",
    "Billing - disputed amount": "Billing Ops",
    "Metering - no read taken": "Metering",
    "Payment - plan or arrears": "Collections",
    "Supply - interruption": "Network Operations",
    "Water - pressure or quality": "Water Operations",
    "Service - missed appointment": "Field Services",
    "Service - poor communication": "Customer Care",
    "Other": "Customer Care",
}
