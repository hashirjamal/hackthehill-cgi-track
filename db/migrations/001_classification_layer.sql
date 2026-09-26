-- For a database built from the first version of db/schema.sql (old `classifications` design,
-- old ai_agents and categories). Run it once, then re-run db/views.sql.
--
--   psql "$URL" -f db/migrations/001_classification_layer.sql && psql "$URL" -f db/views.sql
--
-- It refuses to run if the old classifications table already has rows, because those cannot be
-- carried over (they have no group, subcategory or priority source).

BEGIN;

DO $$
BEGIN
    IF to_regclass('classifications') IS NOT NULL AND EXISTS (SELECT 1 FROM classifications) THEN
        RAISE EXCEPTION 'classifications has rows; migrate them by hand instead';
    END IF;
END $$;

-- Views that read the old columns; db/views.sql recreates them.
DROP VIEW IF EXISTS v_worklist;
DROP VIEW IF EXISTS v_agent_results;

ALTER TABLE agent_runs DROP CONSTRAINT IF EXISTS agent_runs_classification_id_fkey;
DROP TABLE IF EXISTS classifications;

CREATE TABLE classifications (
    id                     BIGSERIAL PRIMARY KEY,
    complaint_id           TEXT NOT NULL,
    classifier_version     TEXT NOT NULL,
    is_current             BOOLEAN NOT NULL DEFAULT TRUE,
    created_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
    as_of_date             DATE NOT NULL,
    input                  JSONB NOT NULL,
    emergency              BOOLEAN NOT NULL,
    emergency_probability  REAL,
    group_name             TEXT,
    group_confidence       REAL,
    group_source           TEXT,
    laya_group             TEXT,
    subcategory            TEXT,
    subcategory_confidence REAL,
    subcategory_source     TEXT,
    low_confidence         BOOLEAN NOT NULL DEFAULT FALSE,
    group_matches_data     BOOLEAN,
    subcategory_matches_data BOOLEAN,
    priority               TEXT NOT NULL,
    base_priority          TEXT NOT NULL,
    base_priority_source   TEXT NOT NULL,
    urgency_score          REAL,
    routed_team            TEXT NOT NULL,
    lane                   TEXT NOT NULL,
    likely_cause           TEXT,
    flags                  JSONB NOT NULL,
    laya_output            JSONB NOT NULL
);
CREATE INDEX ON classifications (complaint_id);
CREATE UNIQUE INDEX one_current_classification
    ON classifications (complaint_id) WHERE is_current;

ALTER TABLE agent_runs
    ADD CONSTRAINT agent_runs_classification_id_fkey
    FOREIGN KEY (classification_id) REFERENCES classifications(id);

-- Domains follow the classifier's groups.
INSERT INTO ai_agents (agent_id, name) VALUES
    ('billing',          'Billing'),
    ('metering',         'Metering'),
    ('field_services',   'Field services'),
    ('customer_support', 'Customer support'),
    ('general',          'General')
ON CONFLICT (agent_id) DO UPDATE SET name = EXCLUDED.name;

UPDATE categories SET agent_id = CASE category
    WHEN 'Billing - disputed amount'    THEN 'billing'
    WHEN 'Billing - estimated read'     THEN 'billing'
    WHEN 'Payment - plan or arrears'    THEN 'billing'
    WHEN 'Metering - no read taken'     THEN 'metering'
    WHEN 'Supply - interruption'        THEN 'field_services'
    WHEN 'Water - pressure or quality'  THEN 'field_services'
    WHEN 'Service - missed appointment' THEN 'field_services'
    WHEN 'Service - poor communication' THEN 'customer_support'
    ELSE 'general'
END;

-- Fails if agent_runs still points at them, which is the right outcome.
DELETE FROM ai_agents WHERE agent_id IN ('supply_water', 'service');

COMMIT;
