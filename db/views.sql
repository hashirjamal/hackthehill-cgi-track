-- Dashboard and simulator views (docs/db-schema.md section 4). Safe to re-run.
-- Views whose columns changed are dropped and recreated (DROP VIEW IF EXISTS), the rest use CREATE OR REPLACE.
-- "Live" figures use app_settings.as_of_date, never now(): the data ends 2026-09-30.

-- Every complaint with live SLA status. Replaces the unreliable source sla_breach on open cases.
-- Breach means days > sla_days (matches the source flag on all closed cases).
CREATE OR REPLACE VIEW v_case_sla AS
SELECT c.*,
       cat.agent_id                                                  AS domain,
       s.as_of_date,
       COALESCE(c.days_to_close, s.as_of_date - c.date_opened)       AS days_open,
       COALESCE(c.days_to_close, s.as_of_date - c.date_opened) - c.sla_days AS days_overdue,
       COALESCE(c.days_to_close, s.as_of_date - c.date_opened) > c.sla_days AS breached_live,
       CASE
           WHEN COALESCE(c.days_to_close, s.as_of_date - c.date_opened) <= 5  THEN '0-5'
           WHEN COALESCE(c.days_to_close, s.as_of_date - c.date_opened) <= 10 THEN '6-10'
           WHEN COALESCE(c.days_to_close, s.as_of_date - c.date_opened) <= 20 THEN '11-20'
           WHEN COALESCE(c.days_to_close, s.as_of_date - c.date_opened) <= 40 THEN '21-40'
           ELSE '41+'
       END                                                           AS age_band
FROM complaints c
JOIN categories cat USING (category)
CROSS JOIN (SELECT value::date AS as_of_date FROM app_settings WHERE key = 'as_of_date') s;

-- Historic profile per case type, over closed cases.
CREATE OR REPLACE VIEW v_case_profile AS
SELECT category, region, source_system,
       count(*)                                                   AS n,
       round(avg(days_to_close), 1)                               AS avg_days,
       round(avg(resolvable_by_information_only::int), 3)         AS info_only_share,
       round(avg(transferred_between_systems::int), 3)            AS transfer_rate,
       round(avg(reopened::int), 3)                               AS reopen_rate,
       round(avg(sla_breach::int), 3)                             AS breach_rate,
       mode() WITHIN GROUP (ORDER BY resolution_action)           AS top_resolution,
       round(avg(bill_correction_value), 2)                       AS avg_bill_correction
FROM complaints
WHERE status <> 'Open'
GROUP BY category, region, source_system;

-- Ranked worklist: open cases with current classification, latest draft and open actions.
-- Most urgent first: classified priority (or the data priority when not classified yet), then days overdue.
-- Dropped first because the column list changed with the classification layer.
DROP VIEW IF EXISTS v_worklist;
CREATE VIEW v_worklist AS
SELECT v.complaint_id, v.account_id, v.date_opened, v.channel, v.category, v.priority,
       v.region, v.source_system, v.sla_days, v.days_open, v.days_overdue, v.breached_live,
       COALESCE(ag.agent_id, v.domain)   AS domain,
       cl.id                             AS classification_id,
       cl.group_name, cl.subcategory,
       COALESCE(cl.priority, v.priority) AS classified_priority,
       cl.base_priority, cl.base_priority_source,
       cl.routed_team, cl.lane, cl.likely_cause, cl.low_confidence, cl.flags,
       m.estimated_read_rate             AS region_estimated_read_rate,
       d.draft_id, d.status              AS draft_status,
       COALESCE(a.open_actions, 0)       AS open_actions,
       a.next_action
FROM v_case_sla v
LEFT JOIN classifications cl ON cl.complaint_id = v.complaint_id AND cl.is_current
LEFT JOIN ai_agents ag ON ag.name = cl.group_name
LEFT JOIN meter_reads m ON m.region = v.region AND m.month = to_char(v.as_of_date, 'YYYY-MM')
LEFT JOIN LATERAL (
    SELECT draft_id, status FROM draft_responses dr
    WHERE dr.complaint_id = v.complaint_id
    ORDER BY created_at DESC, draft_id DESC LIMIT 1
) d ON TRUE
LEFT JOIN LATERAL (
    SELECT count(*) AS open_actions,
           (array_agg(description ORDER BY rank, action_id))[1] AS next_action
    FROM action_items ai
    WHERE ai.complaint_id = v.complaint_id AND ai.status IN ('open', 'in_progress')
) a ON TRUE
WHERE v.status = 'Open'
ORDER BY CASE COALESCE(cl.priority, v.priority) WHEN 'P1' THEN 1 WHEN 'P2' THEN 2 ELSE 3 END,
         v.days_overdue DESC;

-- D1: opened against closed per month, with the running backlog.
CREATE OR REPLACE VIEW v_backlog_flow AS
WITH opened AS (
    SELECT to_char(date_opened, 'YYYY-MM') AS month, count(*) AS opened
    FROM complaints GROUP BY 1
), closed AS (
    SELECT to_char(date_closed, 'YYYY-MM') AS month, count(*) AS closed
    FROM complaints WHERE date_closed IS NOT NULL GROUP BY 1
)
SELECT month,
       COALESCE(o.opened, 0)                              AS opened,
       COALESCE(c.closed, 0)                              AS closed,
       COALESCE(o.opened, 0) - COALESCE(c.closed, 0)      AS net_change,
       sum(COALESCE(o.opened, 0) - COALESCE(c.closed, 0)) OVER (ORDER BY month) AS backlog_end_of_month
FROM opened o FULL JOIN closed c USING (month)
ORDER BY month;

-- D1: current open backlog broken down, one row per combination (sum `open_cases` to filter).
CREATE OR REPLACE VIEW v_backlog_breakdown AS
SELECT region, category, domain, priority, age_band, breached_live,
       count(*)           AS open_cases,
       sum(days_overdue) FILTER (WHERE breached_live) AS total_days_overdue
FROM v_case_sla
WHERE status = 'Open'
GROUP BY region, category, domain, priority, age_band, breached_live;

-- D2: estimated reads against billing and metering complaints, region x month.
CREATE OR REPLACE VIEW v_region_meter_complaints AS
WITH c AS (
    SELECT region, to_char(date_opened, 'YYYY-MM') AS month,
           count(*) AS complaints,
           count(*) FILTER (WHERE category LIKE 'Billing%' OR category LIKE 'Metering%') AS billing_metering_complaints
    FROM complaints GROUP BY 1, 2
)
SELECT m.month, m.region, m.accounts,
       m.estimated_read_rate, m.smart_meter_penetration, m.billing_exceptions_raised,
       round(m.billing_exceptions_raised * 1000.0 / m.accounts, 2)             AS billing_exceptions_per_1000,
       COALESCE(c.complaints, 0)                                                AS complaints,
       COALESCE(c.billing_metering_complaints, 0)                               AS billing_metering_complaints,
       round(COALESCE(c.billing_metering_complaints, 0) * 1000.0 / m.accounts, 3) AS billing_metering_per_1000,
       round(c.billing_metering_complaints::numeric / NULLIF(c.complaints, 0), 3) AS billing_metering_share
FROM meter_reads m
LEFT JOIN c USING (region, month);

-- C2 / D4: every complaint per account, in order, with repeat information.
CREATE OR REPLACE VIEW v_account_history AS
SELECT account_id, complaint_id, date_opened, date_closed, status, category, region, channel,
       priority, resolution_action, days_to_close, reopened, transferred_between_systems,
       row_number() OVER w                                       AS complaint_seq,
       count(*) OVER (PARTITION BY account_id)                   AS complaints_on_account,
       date_opened - lag(date_opened) OVER w                     AS days_since_previous,
       row_number() OVER w > 1                                   AS is_repeat
FROM complaints
WINDOW w AS (PARTITION BY account_id ORDER BY date_opened, complaint_id);

-- D5: classification and agent results per domain. A classification counts for the agent whose name
-- is its group; the quick lane is the info-only lane.
DROP VIEW IF EXISTS v_agent_results;
CREATE VIEW v_agent_results AS
SELECT ag.agent_id, ag.name,
       (SELECT count(*) FROM classifications c WHERE c.group_name = ag.name AND c.is_current)                            AS classified,
       (SELECT count(*) FROM classifications c WHERE c.group_name = ag.name AND c.is_current AND c.lane = 'quick_lane') AS fast_lane,
       (SELECT count(*) FROM agent_runs r WHERE r.agent_id = ag.agent_id)                                               AS runs,
       (SELECT count(*) FROM agent_runs r WHERE r.agent_id = ag.agent_id AND r.status = 'failed')                       AS runs_failed,
       d.drafts, d.drafts_pending, d.drafts_approved, d.drafts_edited, d.drafts_rejected, d.drafts_sent
FROM ai_agents ag
LEFT JOIN LATERAL (
    SELECT count(*)                                   AS drafts,
           count(*) FILTER (WHERE dr.status = 'draft')    AS drafts_pending,
           count(*) FILTER (WHERE dr.status = 'approved') AS drafts_approved,
           count(*) FILTER (WHERE dr.status = 'edited')   AS drafts_edited,
           count(*) FILTER (WHERE dr.status = 'rejected') AS drafts_rejected,
           count(*) FILTER (WHERE dr.status = 'sent')     AS drafts_sent
    FROM draft_responses dr JOIN agent_runs r USING (run_id)
    WHERE r.agent_id = ag.agent_id
) d ON TRUE;

-- E2 / E7 / E8: simulator starting point, one row.
CREATE OR REPLACE VIEW v_sim_baseline AS
WITH s AS (SELECT value::date AS as_of_date FROM app_settings WHERE key = 'as_of_date')
SELECT s.as_of_date,
       count(*) FILTER (WHERE date_opened > (s.as_of_date - interval '12 months'))                                AS opened_last_12m,
       round(avg(transferred_between_systems::int) FILTER (WHERE date_opened > (s.as_of_date - interval '12 months')), 3) AS transfer_share_12m,
       round(avg(reopened::int) FILTER (WHERE status <> 'Open'), 3)                                              AS reopen_share,
       round(avg(resolvable_by_information_only::int), 3)                                                        AS info_only_share,
       round(count(*) FILTER (WHERE date_opened > (s.as_of_date - interval '6 months')) / 6.0, 1)                AS monthly_opened_6m,
       round(count(*) FILTER (WHERE date_closed > (s.as_of_date - interval '6 months')) / 6.0, 1)                AS monthly_closed_6m,
       count(*) FILTER (WHERE status = 'Open')                                                                   AS current_backlog,
       round(avg(days_to_close), 1)                                                                              AS avg_days_all,
       round(avg(days_to_close) FILTER (WHERE transferred_between_systems), 1)                                   AS avg_days_transferred,
       round(avg(days_to_close) FILTER (WHERE NOT transferred_between_systems), 1)                               AS avg_days_not_transferred,
       round(avg(days_to_close) FILTER (WHERE date_closed > (s.as_of_date - interval '12 months')), 1)            AS avg_days_closed_12m,
       round(avg(sla_breach::int) FILTER (WHERE status <> 'Open'), 3)                                            AS breach_rate_closed
FROM complaints CROSS JOIN s
GROUP BY s.as_of_date;

-- E7-E12: unit costs as named columns.
CREATE OR REPLACE VIEW v_unit_costs AS
SELECT max(unit_cost) FILTER (WHERE cost_key = 'call')                  AS call,
       max(unit_cost) FILTER (WHERE cost_key = 'complaint_standard')    AS complaint_standard,
       max(unit_cost) FILTER (WHERE cost_key = 'complaint_transferred') AS complaint_transferred,
       max(unit_cost) FILTER (WHERE cost_key = 'bill_correction')       AS bill_correction,
       max(unit_cost) FILTER (WHERE cost_key = 'field_visit')           AS field_visit,
       max(unit_cost) FILTER (WHERE cost_key = 'smart_meter_install')   AS smart_meter_install,
       max(unit_cost) FILTER (WHERE cost_key = 'staff_annual')          AS staff_annual,
       max(unit_cost) FILTER (WHERE cost_key = 'staff_hire')            AS staff_hire,
       max(unit_cost) FILTER (WHERE cost_key = 'ai_pilot_annual')       AS ai_pilot_annual,
       max(unit_cost) FILTER (WHERE cost_key = 'penalty_quarter')       AS penalty_quarter,
       max(unit_cost) FILTER (WHERE cost_key = 'compensation')          AS compensation
FROM unit_costs;

-- E4: linear fit of regulator score on average days (a correlation, label it as an estimate).
CREATE OR REPLACE VIEW v_score_relationship AS
SELECT regr_slope(regulator_satisfaction_score_of_5, avg_days_to_close)     AS slope,
       regr_intercept(regulator_satisfaction_score_of_5, avg_days_to_close) AS intercept,
       regr_r2(regulator_satisfaction_score_of_5, avg_days_to_close)        AS r2,
       regr_count(regulator_satisfaction_score_of_5, avg_days_to_close)     AS n_months
FROM monthly_kpis;
