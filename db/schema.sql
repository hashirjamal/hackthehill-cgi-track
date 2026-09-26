-- Northwind complaint triage schema. Source of truth: docs/db-schema.md.
-- Run once on an empty database, then db/views.sql, then the generated seed files (db/build_seed.py).

-- 1. Reference data (from the CSVs) -------------------------------------------

CREATE TABLE systems (
    system_id          TEXT PRIMARY KEY,           -- SYS-01 .. SYS-15
    system_name        TEXT NOT NULL,
    purpose            TEXT,
    year_installed     INT,
    vendor             TEXT,
    tech_stack         TEXT,
    records_held       BIGINT,
    integration_method TEXT,                        -- nightly batch, REST API, streaming ...
    annual_run_cost    NUMERIC(14,2),
    owning_function    TEXT,
    notes              TEXT
);

CREATE TABLE regions (
    region TEXT PRIMARY KEY                          -- Ashford, Barrowdale, Calderfield, Dunmoor, Eastmarch, Fenwick
);

-- Parsed from meter_reads.systems_serving_region ("SYS-01/SYS-06")
CREATE TABLE region_systems (
    region    TEXT REFERENCES regions(region),
    system_id TEXT REFERENCES systems(system_id),
    PRIMARY KEY (region, system_id)
);

-- Account id only: 284 accounts appear in more than one region, so region lives on the complaint.
CREATE TABLE accounts (
    account_id TEXT PRIMARY KEY
);

CREATE TABLE ai_agents (                            -- one row per domain agent
    agent_id       TEXT PRIMARY KEY,                -- billing, metering, supply_water, service, general
    name           TEXT NOT NULL,
    instructions   TEXT,                            -- system prompt / config version reference
    active         BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE categories (                           -- maps complaint category to a domain agent
    category TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL REFERENCES ai_agents(agent_id)
);

CREATE TABLE complaints (
    complaint_id                   TEXT PRIMARY KEY,   -- NW-100001
    account_id                     TEXT NOT NULL REFERENCES accounts(account_id),
    date_opened                    DATE NOT NULL,
    date_closed                    DATE,
    status                         TEXT NOT NULL CHECK (status IN ('Open','Closed','Closed - reopened')),
    channel                        TEXT NOT NULL CHECK (channel IN ('Phone','Web form','Email','Social','Post','Regulator referral')),
    category                       TEXT NOT NULL REFERENCES categories(category),
    priority                       TEXT NOT NULL CHECK (priority IN ('P1','P2','P3')),
    region                         TEXT NOT NULL REFERENCES regions(region),
    source_system                  TEXT NOT NULL REFERENCES systems(system_id),
    transferred_between_systems    BOOLEAN NOT NULL,
    sla_days                       INT NOT NULL,       -- 5 / 10 / 20
    days_to_close                  INT,                -- NULL while open
    sla_breach                     BOOLEAN NOT NULL,   -- source flag; unreliable on open cases, use v_case_sla
    reopened                       BOOLEAN NOT NULL,
    resolution_action              TEXT,               -- NULL while open
    resolvable_by_information_only BOOLEAN,            -- NULL while open
    bill_correction_value          NUMERIC(10,2)       -- NULL when no correction
);
CREATE INDEX ON complaints (status);
CREATE INDEX ON complaints (account_id);
CREATE INDEX ON complaints (region, category);
CREATE INDEX ON complaints (date_opened);

CREATE TABLE meter_reads (
    month                     TEXT NOT NULL,            -- 'YYYY-MM'
    region                    TEXT NOT NULL REFERENCES regions(region),
    accounts                  INT NOT NULL,
    estimated_read_rate       NUMERIC(4,3) NOT NULL,    -- share of bills based on an estimate
    smart_meter_penetration   NUMERIC(4,3) NOT NULL,
    billing_exceptions_raised INT NOT NULL,
    systems_serving_region    TEXT,                     -- raw CSV value
    PRIMARY KEY (month, region)
);

-- Not in the original schema proposal: northwind_contact_centre_staffing.csv, region x month.
-- "agent" in these column names means human contact-centre staff (CSV wording kept).
CREATE TABLE contact_centre_staffing (
    month                       TEXT NOT NULL,          -- 'YYYY-MM'
    region                      TEXT NOT NULL REFERENCES regions(region),
    agent_fte                   NUMERIC(7,1) NOT NULL,
    open_vacancies              INT,
    attrition_rate_12m          NUMERIC(4,3),
    complaints_opened_per_agent NUMERIC(6,2),
    note                        TEXT,
    PRIMARY KEY (month, region)
);

CREATE TABLE monthly_kpis (
    month                             TEXT PRIMARY KEY,
    complaints_opened                 INT,
    complaints_closed                 INT,
    avg_days_to_close                 NUMERIC(5,1),
    first_contact_resolution_rate     NUMERIC(4,3),
    inbound_calls                     INT,
    cost_to_serve_per_account         NUMERIC(6,2),
    regulator_satisfaction_score_of_5 NUMERIC(3,2)
);

CREATE TABLE ai_pilot_2025 (                          -- loaded for reference, no screen built
    month                               TEXT PRIMARY KEY,
    assistant_sessions                  INT,
    fully_contained_rate                NUMERIC(4,3),
    escalated_to_agent_rate             NUMERIC(4,3),
    abandoned_rate                      NUMERIC(4,3),
    repeat_contact_within_7_days_rate   NUMERIC(4,3),
    assistant_csat_of_5                 NUMERIC(3,2),
    complaint_raised_after_session_rate NUMERIC(4,3)
);

-- cost_key is a stable handle the simulator queries, so it never depends on the wording of `item`.
CREATE TABLE unit_costs (
    cost_key    TEXT PRIMARY KEY,
    item        TEXT NOT NULL UNIQUE,                 -- text from the CSV
    unit_cost   NUMERIC(12,2) NOT NULL,
    unit        TEXT,
    source_note TEXT
);

-- Live calculations use this date, not now(): the data runs to 2026-09-30.
CREATE TABLE app_settings (
    key   TEXT PRIMARY KEY,                           -- e.g. 'as_of_date'
    value TEXT NOT NULL
);

-- 2. Workflow tables (new) ----------------------------------------------------

CREATE TABLE staff (
    staff_id SERIAL PRIMARY KEY,
    name     TEXT NOT NULL,
    role     TEXT NOT NULL CHECK (role IN ('contact_centre','team_lead','manager')),
    team     TEXT                                     -- e.g. billing, metering, field
);

-- Output of Laya + rules. History is kept; one row per complaint is current.
CREATE TABLE classifications (
    classification_id      BIGSERIAL PRIMARY KEY,
    complaint_id           TEXT NOT NULL REFERENCES complaints(complaint_id),
    agent_id               TEXT NOT NULL REFERENCES ai_agents(agent_id),   -- domain
    fix_type               TEXT NOT NULL CHECK (fix_type IN
                              ('info_only','bill_correction','field_visit','payment_plan','appointment','complex')),
    info_only_prob         NUMERIC(4,3),
    urgency_score          SMALLINT CHECK (urgency_score BETWEEN 1 AND 5),
    likely_estimated_read  BOOLEAN NOT NULL DEFAULT FALSE,
    breach_risk            NUMERIC(4,3),
    fast_lane_eligible     BOOLEAN NOT NULL DEFAULT FALSE,
    routed_team            TEXT,
    rule_hits              JSONB,                     -- which custom rules fired
    laya_output            JSONB,                     -- raw Laya answers
    classifier_version     TEXT,
    is_current             BOOLEAN NOT NULL DEFAULT TRUE,
    classified_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX one_current_classification
    ON classifications (complaint_id) WHERE is_current;

-- Audit of each AI agent run
CREATE TABLE agent_runs (
    run_id            BIGSERIAL PRIMARY KEY,
    complaint_id      TEXT NOT NULL REFERENCES complaints(complaint_id),
    agent_id          TEXT NOT NULL REFERENCES ai_agents(agent_id),
    classification_id BIGINT REFERENCES classifications(classification_id),
    status            TEXT NOT NULL CHECK (status IN ('running','succeeded','failed')),
    model             TEXT,
    context           JSONB,                          -- profile, account history, meter data given to the agent
    error             TEXT,
    started_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at       TIMESTAMPTZ
);
CREATE INDEX ON agent_runs (complaint_id);

CREATE TABLE draft_responses (
    draft_id     BIGSERIAL PRIMARY KEY,
    complaint_id TEXT NOT NULL REFERENCES complaints(complaint_id),
    run_id       BIGINT REFERENCES agent_runs(run_id),
    body         TEXT NOT NULL,                       -- as generated
    status       TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft','approved','edited','rejected','sent')),
    final_body   TEXT,                                -- text after staff edits
    reviewed_by  INT REFERENCES staff(staff_id),
    reviewed_at  TIMESTAMPTZ,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ON draft_responses (complaint_id);

CREATE TABLE action_items (
    action_id     BIGSERIAL PRIMARY KEY,
    complaint_id  TEXT NOT NULL REFERENCES complaints(complaint_id),
    run_id        BIGINT REFERENCES agent_runs(run_id),
    action_type   TEXT NOT NULL,                      -- correct_bill, book_meter_read, rebook_appointment, escalate_field, call_customer, send_reply ...
    description   TEXT NOT NULL,
    rationale     TEXT,                               -- why the agent suggests it
    rank          SMALLINT NOT NULL DEFAULT 1,        -- suggested order within the case
    status        TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open','in_progress','done','dismissed')),
    assigned_team TEXT,
    assigned_to   INT REFERENCES staff(staff_id),
    due_date      DATE,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at  TIMESTAMPTZ
);
CREATE INDEX ON action_items (complaint_id);
CREATE INDEX ON action_items (status);

CREATE TABLE sim_scenarios (
    scenario_id SERIAL PRIMARY KEY,
    name        TEXT NOT NULL,                        -- base, conservative, target
    params      JSONB NOT NULL,                       -- transfer_reduction, fast_lane_share, fast_lane_days ...
    results     JSONB NOT NULL,                       -- avg_days, breach_rate, backlog, score, plus the cost block
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Optional (P2): staff chat assistant
CREATE TABLE chat_sessions (
    session_id   SERIAL PRIMARY KEY,
    staff_id     INT NOT NULL REFERENCES staff(staff_id),
    complaint_id TEXT REFERENCES complaints(complaint_id),   -- NULL for general questions
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE chat_messages (
    message_id BIGSERIAL PRIMARY KEY,
    session_id INT NOT NULL REFERENCES chat_sessions(session_id),
    role       TEXT NOT NULL CHECK (role IN ('staff','assistant')),
    content    TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 3. Fixed reference rows -----------------------------------------------------

INSERT INTO regions (region) VALUES
    ('Ashford'), ('Barrowdale'), ('Calderfield'), ('Dunmoor'), ('Eastmarch'), ('Fenwick');

INSERT INTO ai_agents (agent_id, name) VALUES
    ('billing',      'Billing'),
    ('metering',     'Metering'),
    ('supply_water', 'Supply and water'),
    ('service',      'Service'),
    ('general',      'General');

INSERT INTO categories (category, agent_id) VALUES
    ('Billing - disputed amount',    'billing'),
    ('Payment - plan or arrears',    'billing'),
    ('Billing - estimated read',     'metering'),
    ('Metering - no read taken',     'metering'),
    ('Supply - interruption',        'supply_water'),
    ('Water - pressure or quality',  'supply_water'),
    ('Service - poor communication', 'service'),
    ('Service - missed appointment', 'service'),
    ('Other',                        'general');

INSERT INTO app_settings (key, value) VALUES ('as_of_date', '2026-09-30');
