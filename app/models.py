from datetime import date, datetime

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

# JSON everywhere, JSONB on Postgres to match db/schema.sql.
JsonType = JSON().with_variant(JSONB(), "postgresql")


class Item(Base):
    """Example table -- replace with your own models."""

    __tablename__ = "items"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Classification(Base):
    """Output of the Laya classification layer. One row is current per complaint; older ones are history."""

    __tablename__ = "classifications"
    __table_args__ = (
        Index(
            "one_current_classification",
            "complaint_id",
            unique=True,
            sqlite_where=text("is_current"),
            postgresql_where=text("is_current"),
        ),
    )

    # Integer on SQLite (local dev), so the key autoincrements there.
    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    complaint_id: Mapped[str] = mapped_column(String(64), index=True)
    classifier_version: Mapped[str] = mapped_column(String(64))
    is_current: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    as_of_date: Mapped[date] = mapped_column(Date)

    input: Mapped[dict] = mapped_column(JsonType)  # the complaint as submitted

    emergency: Mapped[bool] = mapped_column(Boolean)
    emergency_probability: Mapped[float | None] = mapped_column(Float)  # NULL when there was no text
    group_name: Mapped[str | None] = mapped_column(String(32))
    group_confidence: Mapped[float | None] = mapped_column(Float)  # Laya's top probability
    group_source: Mapped[str | None] = mapped_column(String(8))  # laya, or data on a low-confidence fallback
    laya_group: Mapped[str | None] = mapped_column(String(32))  # Laya's own pick
    subcategory: Mapped[str | None] = mapped_column(String(64))  # a Northwind data category
    subcategory_confidence: Mapped[float | None] = mapped_column(Float)
    subcategory_source: Mapped[str | None] = mapped_column(String(8))
    low_confidence: Mapped[bool] = mapped_column(Boolean, default=False)  # Laya's top probability was under the threshold
    group_matches_data: Mapped[bool | None] = mapped_column(Boolean)  # NULL when the data has no category
    subcategory_matches_data: Mapped[bool | None] = mapped_column(Boolean)

    priority: Mapped[str] = mapped_column(String(2))  # P1..P3, after flags
    base_priority: Mapped[str] = mapped_column(String(2))  # before flags
    base_priority_source: Mapped[str] = mapped_column(String(16))  # data, laya or emergency
    urgency_score: Mapped[float | None] = mapped_column(Float)
    routed_team: Mapped[str] = mapped_column(String(64))
    lane: Mapped[str] = mapped_column(String(16))  # emergency, review, quick_lane, standard
    likely_cause: Mapped[str | None] = mapped_column(String(32))
    flags: Mapped[list] = mapped_column(JsonType)  # flags that fired
    laya_output: Mapped[dict] = mapped_column(JsonType)  # raw Laya answers, for audit

    # complaint_id has no FK to complaints on purpose (see AgentRun): classification can run ahead of the
    # complaints table being loaded. agent_runs.classification_id does have one.
    agent_runs: Mapped[list["AgentRun"]] = relationship(back_populates="classification")


# --- Reference data (from the CSVs) ------------------------------------------------------------


class System(Base):
    """One of the 15 Northwind IT systems (northwind_systems.csv)."""

    __tablename__ = "systems"

    system_id: Mapped[str] = mapped_column(String(16), primary_key=True)  # SYS-01 .. SYS-15
    system_name: Mapped[str] = mapped_column(Text)
    purpose: Mapped[str | None] = mapped_column(Text)
    year_installed: Mapped[int | None] = mapped_column(Integer)
    vendor: Mapped[str | None] = mapped_column(Text)
    tech_stack: Mapped[str | None] = mapped_column(Text)
    records_held: Mapped[int | None] = mapped_column(BigInteger)
    integration_method: Mapped[str | None] = mapped_column(Text)  # nightly batch, REST API, streaming ...
    annual_run_cost: Mapped[float | None] = mapped_column(Numeric(14, 2))
    owning_function: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)

    region_links: Mapped[list["RegionSystem"]] = relationship(back_populates="system")
    complaints: Mapped[list["Complaint"]] = relationship(back_populates="system")


class Region(Base):
    """Ashford, Barrowdale, Calderfield, Dunmoor, Eastmarch, Fenwick."""

    __tablename__ = "regions"

    region: Mapped[str] = mapped_column(String(32), primary_key=True)

    system_links: Mapped[list["RegionSystem"]] = relationship(back_populates="region_ref")
    complaints: Mapped[list["Complaint"]] = relationship(back_populates="region_ref")
    meter_reads: Mapped[list["MeterRead"]] = relationship(back_populates="region_ref")
    staffing: Mapped[list["ContactCentreStaffing"]] = relationship(back_populates="region_ref")


class RegionSystem(Base):
    """Parsed from meter_reads.systems_serving_region ("SYS-01/SYS-06")."""

    __tablename__ = "region_systems"

    region: Mapped[str] = mapped_column(ForeignKey("regions.region"), primary_key=True)
    system_id: Mapped[str] = mapped_column(ForeignKey("systems.system_id"), primary_key=True)

    region_ref: Mapped["Region"] = relationship(back_populates="system_links")
    system: Mapped["System"] = relationship(back_populates="region_links")


class Account(Base):
    """Account id only: 284 accounts appear in more than one region, so region lives on the complaint."""

    __tablename__ = "accounts"

    account_id: Mapped[str] = mapped_column(String(32), primary_key=True)

    complaints: Mapped[list["Complaint"]] = relationship(back_populates="account")


class AiAgent(Base):
    """One row per domain agent: billing, metering, field_services, customer_support, general."""

    __tablename__ = "ai_agents"

    agent_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(Text)  # matches the classifier's group name
    instructions: Mapped[str | None] = mapped_column(Text)  # system prompt / config version reference
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    categories: Mapped[list["Category"]] = relationship(back_populates="agent")
    agent_runs: Mapped[list["AgentRun"]] = relationship(back_populates="agent")


class Category(Base):
    """Maps a Northwind complaint category to the domain agent that handles it."""

    __tablename__ = "categories"

    category: Mapped[str] = mapped_column(String(64), primary_key=True)
    agent_id: Mapped[str] = mapped_column(ForeignKey("ai_agents.agent_id"))

    agent: Mapped["AiAgent"] = relationship(back_populates="categories")
    complaints: Mapped[list["Complaint"]] = relationship(back_populates="category_ref")


class AppSetting(Base):
    """Live calculations use this, not now(): the data runs to 2026-09-30."""

    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)  # e.g. 'as_of_date'
    value: Mapped[str] = mapped_column(Text)


# --- Loaded from the CSVs, kept as a mirror of the source data ---------------------------------


class Complaint(Base):
    """One Northwind complaint (northwind_complaints.csv)."""

    __tablename__ = "complaints"
    __table_args__ = (
        CheckConstraint("status IN ('Open', 'Closed', 'Closed - reopened')", name="complaints_status_check"),
        CheckConstraint(
            "channel IN ('Phone', 'Web form', 'Email', 'Social', 'Post', 'Regulator referral')",
            name="complaints_channel_check",
        ),
        CheckConstraint("priority IN ('P1', 'P2', 'P3')", name="complaints_priority_check"),
        Index("complaints_status_idx", "status"),
        Index("complaints_account_id_idx", "account_id"),
        Index("complaints_region_category_idx", "region", "category"),
        Index("complaints_date_opened_idx", "date_opened"),
    )

    complaint_id: Mapped[str] = mapped_column(String(32), primary_key=True)  # NW-100001
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.account_id"))
    date_opened: Mapped[date] = mapped_column(Date)
    date_closed: Mapped[date | None] = mapped_column(Date)  # NULL while open
    status: Mapped[str] = mapped_column(String(16))
    channel: Mapped[str] = mapped_column(String(32))
    category: Mapped[str] = mapped_column(ForeignKey("categories.category"))
    priority: Mapped[str] = mapped_column(String(2))
    region: Mapped[str] = mapped_column(ForeignKey("regions.region"))
    source_system: Mapped[str] = mapped_column(ForeignKey("systems.system_id"))
    transferred_between_systems: Mapped[bool] = mapped_column(Boolean)
    sla_days: Mapped[int] = mapped_column(Integer)  # 5 / 10 / 20
    days_to_close: Mapped[int | None] = mapped_column(Integer)  # NULL while open
    sla_breach: Mapped[bool] = mapped_column(Boolean)  # source flag; unreliable on open cases, use v_case_sla
    reopened: Mapped[bool] = mapped_column(Boolean)
    resolution_action: Mapped[str | None] = mapped_column(Text)  # NULL while open
    resolvable_by_information_only: Mapped[bool | None] = mapped_column(Boolean)  # NULL while open
    bill_correction_value: Mapped[float | None] = mapped_column(Numeric(10, 2))  # NULL when no correction

    account: Mapped["Account"] = relationship(back_populates="complaints")
    category_ref: Mapped["Category"] = relationship(back_populates="complaints")
    region_ref: Mapped["Region"] = relationship(back_populates="complaints")
    system: Mapped["System"] = relationship(back_populates="complaints")
    chat_sessions: Mapped[list["ChatSession"]] = relationship(back_populates="complaint")


class MeterRead(Base):
    """Region x month meter picture (northwind_meter_reads.csv)."""

    __tablename__ = "meter_reads"

    month: Mapped[str] = mapped_column(String(7), primary_key=True)  # 'YYYY-MM'
    region: Mapped[str] = mapped_column(ForeignKey("regions.region"), primary_key=True)
    accounts: Mapped[int] = mapped_column(Integer)
    estimated_read_rate: Mapped[float] = mapped_column(Numeric(4, 3))  # share of bills based on an estimate
    smart_meter_penetration: Mapped[float] = mapped_column(Numeric(4, 3))
    billing_exceptions_raised: Mapped[int] = mapped_column(Integer)
    systems_serving_region: Mapped[str | None] = mapped_column(Text)  # raw CSV value, e.g. "SYS-01/SYS-06"

    region_ref: Mapped["Region"] = relationship(back_populates="meter_reads")


class ContactCentreStaffing(Base):
    """Region x month contact-centre FTE (northwind_contact_centre_staffing.csv).

    "agent" in the CSV's column names means human contact-centre staff, not an AI agent.
    """

    __tablename__ = "contact_centre_staffing"

    month: Mapped[str] = mapped_column(String(7), primary_key=True)
    region: Mapped[str] = mapped_column(ForeignKey("regions.region"), primary_key=True)
    agent_fte: Mapped[float] = mapped_column(Numeric(7, 1))
    open_vacancies: Mapped[int | None] = mapped_column(Integer)
    attrition_rate_12m: Mapped[float | None] = mapped_column(Numeric(4, 3))
    complaints_opened_per_agent: Mapped[float | None] = mapped_column(Numeric(6, 2))
    note: Mapped[str | None] = mapped_column(Text)

    region_ref: Mapped["Region"] = relationship(back_populates="staffing")


class MonthlyKpi(Base):
    """24 monthly KPI rows (northwind_monthly_kpis.csv). Stands alone; the simulator reads it."""

    __tablename__ = "monthly_kpis"

    month: Mapped[str] = mapped_column(String(7), primary_key=True)
    complaints_opened: Mapped[int | None] = mapped_column(Integer)
    complaints_closed: Mapped[int | None] = mapped_column(Integer)
    avg_days_to_close: Mapped[float | None] = mapped_column(Numeric(5, 1))
    first_contact_resolution_rate: Mapped[float | None] = mapped_column(Numeric(4, 3))
    inbound_calls: Mapped[int | None] = mapped_column(Integer)
    cost_to_serve_per_account: Mapped[float | None] = mapped_column(Numeric(6, 2))
    regulator_satisfaction_score_of_5: Mapped[float | None] = mapped_column(Numeric(3, 2))


class AiPilot2025(Base):
    """Results of the 2025 chatbot pilot (northwind_ai_pilot_2025.csv). Loaded for reference, no screen built."""

    __tablename__ = "ai_pilot_2025"

    month: Mapped[str] = mapped_column(String(7), primary_key=True)
    assistant_sessions: Mapped[int | None] = mapped_column(Integer)
    fully_contained_rate: Mapped[float | None] = mapped_column(Numeric(4, 3))
    escalated_to_agent_rate: Mapped[float | None] = mapped_column(Numeric(4, 3))
    abandoned_rate: Mapped[float | None] = mapped_column(Numeric(4, 3))
    repeat_contact_within_7_days_rate: Mapped[float | None] = mapped_column(Numeric(4, 3))
    assistant_csat_of_5: Mapped[float | None] = mapped_column(Numeric(3, 2))
    complaint_raised_after_session_rate: Mapped[float | None] = mapped_column(Numeric(4, 3))


class UnitCost(Base):
    """Cost per complaint, transfer, bill correction, penalty and so on (northwind_unit_costs.csv).

    cost_key is a stable handle the simulator queries, so it never depends on the wording of `item`.
    """

    __tablename__ = "unit_costs"

    cost_key: Mapped[str] = mapped_column(String(32), primary_key=True)
    item: Mapped[str] = mapped_column(Text, unique=True)  # text from the CSV
    unit_cost: Mapped[float] = mapped_column(Numeric(12, 2))
    unit: Mapped[str | None] = mapped_column(Text)
    source_note: Mapped[str | None] = mapped_column(Text)


# --- Workflow tables (new) ----------------------------------------------------------------------


class Staff(Base):
    """A contact-centre staff member."""

    __tablename__ = "staff"
    __table_args__ = (
        CheckConstraint("role IN ('contact_centre', 'team_lead', 'manager')", name="staff_role_check"),
    )

    staff_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(Text)
    role: Mapped[str] = mapped_column(String(16))
    team: Mapped[str | None] = mapped_column(String(32))  # e.g. billing, metering, field

    drafts_reviewed: Mapped[list["DraftResponse"]] = relationship(back_populates="reviewer")
    action_items_assigned: Mapped[list["ActionItem"]] = relationship(back_populates="assignee")
    chat_sessions: Mapped[list["ChatSession"]] = relationship(back_populates="staff")


class AgentRun(Base):
    """Audit of one AI agent run."""

    __tablename__ = "agent_runs"
    __table_args__ = (
        CheckConstraint("status IN ('running', 'succeeded', 'failed')", name="agent_runs_status_check"),
        Index("agent_runs_complaint_id_idx", "complaint_id"),
    )

    # Integer on SQLite (local dev), so the key autoincrements there (see Classification.id).
    run_id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    complaint_id: Mapped[str] = mapped_column(String(32))  # no FK on purpose, see Classification
    agent_id: Mapped[str] = mapped_column(ForeignKey("ai_agents.agent_id"))
    classification_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("classifications.id"))
    status: Mapped[str] = mapped_column(String(16))
    model: Mapped[str | None] = mapped_column(Text)
    context: Mapped[dict | None] = mapped_column(JsonType)  # profile, account history, meter data given to the agent
    error: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    agent: Mapped["AiAgent"] = relationship(back_populates="agent_runs")
    classification: Mapped["Classification | None"] = relationship(back_populates="agent_runs")
    draft_responses: Mapped[list["DraftResponse"]] = relationship(back_populates="agent_run")
    action_items: Mapped[list["ActionItem"]] = relationship(back_populates="agent_run")


class DraftResponse(Base):
    """A drafted reply for staff to approve, edit or reject."""

    __tablename__ = "draft_responses"
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'approved', 'edited', 'rejected', 'sent')", name="draft_responses_status_check"
        ),
        Index("draft_responses_complaint_id_idx", "complaint_id"),
    )

    # Integer on SQLite (local dev), so the key autoincrements there (see Classification.id).
    draft_id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    complaint_id: Mapped[str] = mapped_column(String(32))  # no FK on purpose, see Classification
    run_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("agent_runs.run_id"))
    body: Mapped[str] = mapped_column(Text)  # as generated
    status: Mapped[str] = mapped_column(String(16), default="draft")
    final_body: Mapped[str | None] = mapped_column(Text)  # text after staff edits
    reviewed_by: Mapped[int | None] = mapped_column(Integer, ForeignKey("staff.staff_id"))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    agent_run: Mapped["AgentRun | None"] = relationship(back_populates="draft_responses")
    reviewer: Mapped["Staff | None"] = relationship(back_populates="drafts_reviewed")


class ActionItem(Base):
    """A suggested next action for staff, produced by a domain agent."""

    __tablename__ = "action_items"
    __table_args__ = (
        CheckConstraint(
            "status IN ('open', 'in_progress', 'done', 'dismissed')", name="action_items_status_check"
        ),
        Index("action_items_complaint_id_idx", "complaint_id"),
        Index("action_items_status_idx", "status"),
    )

    # Integer on SQLite (local dev), so the key autoincrements there (see Classification.id).
    action_id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    complaint_id: Mapped[str] = mapped_column(String(32))  # no FK on purpose, see Classification
    run_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("agent_runs.run_id"))
    action_type: Mapped[str] = mapped_column(Text)  # correct_bill, book_meter_read, escalate_field ...
    description: Mapped[str] = mapped_column(Text)
    rationale: Mapped[str | None] = mapped_column(Text)  # why the agent suggests it
    rank: Mapped[int] = mapped_column(SmallInteger, default=1)  # suggested order within the case
    status: Mapped[str] = mapped_column(String(16), default="open")
    assigned_team: Mapped[str | None] = mapped_column(Text)
    assigned_to: Mapped[int | None] = mapped_column(Integer, ForeignKey("staff.staff_id"))
    due_date: Mapped[date | None] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    agent_run: Mapped["AgentRun | None"] = relationship(back_populates="action_items")
    assignee: Mapped["Staff | None"] = relationship(back_populates="action_items_assigned")


class SimScenario(Base):
    """A saved what-if simulator scenario (name, settings, results), for the demo."""

    __tablename__ = "sim_scenarios"

    scenario_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(Text)  # base, conservative, target
    params: Mapped[dict] = mapped_column(JsonType)  # transfer_reduction, fast_lane_share, fast_lane_days ...
    results: Mapped[dict] = mapped_column(JsonType)  # avg_days, breach_rate, backlog, score, plus the cost block
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ChatSession(Base):
    """Optional (P2): one staff chat session, about a case or general."""

    __tablename__ = "chat_sessions"

    session_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    staff_id: Mapped[int] = mapped_column(ForeignKey("staff.staff_id"))
    complaint_id: Mapped[str | None] = mapped_column(ForeignKey("complaints.complaint_id"))  # NULL = general
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    staff: Mapped["Staff"] = relationship(back_populates="chat_sessions")
    complaint: Mapped["Complaint | None"] = relationship(back_populates="chat_sessions")
    messages: Mapped[list["ChatMessage"]] = relationship(back_populates="session")


class ChatMessage(Base):
    """Optional (P2): one message in a staff chat session."""

    __tablename__ = "chat_messages"
    __table_args__ = (CheckConstraint("role IN ('staff', 'assistant')", name="chat_messages_role_check"),)

    message_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("chat_sessions.session_id"))
    role: Mapped[str] = mapped_column(String(16))
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    session: Mapped["ChatSession"] = relationship(back_populates="messages")
