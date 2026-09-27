-- For a database built from a version of db/schema.sql where agent_runs, draft_responses and
-- action_items had `complaint_id ... REFERENCES complaints(complaint_id)`. Run it once.
--
--   psql "$URL" -f db/migrations/002_agent_tables_complaint_fk.sql
--
-- It drops those three foreign keys, so the domain agents can run on new complaints that are not in
-- `complaints` yet (the same reason `classifications` has none). It only drops constraints: no rows
-- are changed or deleted.

BEGIN;

ALTER TABLE agent_runs      DROP CONSTRAINT IF EXISTS agent_runs_complaint_id_fkey;
ALTER TABLE draft_responses DROP CONSTRAINT IF EXISTS draft_responses_complaint_id_fkey;
ALTER TABLE action_items    DROP CONSTRAINT IF EXISTS action_items_complaint_id_fkey;

COMMIT;
