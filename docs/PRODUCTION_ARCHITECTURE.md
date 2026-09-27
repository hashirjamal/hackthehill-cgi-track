# Production architecture: running this at Northwind

The demo runs on one laptop. In production the same components run **on Northwind's own servers,
inside its network** - no customer data goes to an outside AI provider, and nothing is exposed to
the internet.

## Load (why this doesn't need a giant cluster)

- About 25,000 complaints in two years: **~35 new complaints a day**. Laya classifies one in a few
  seconds on an ordinary CPU.
- A few hundred staff clicking "Get context" / "Generate draft" a few thousand times a day - the
  only heavy part, and it scales with GPUs.
- A few million rows of data: small for PostgreSQL.

## Components

```
Staff browsers (internal network only, company sign-in)
        │
  [Load balancer + web server]  serves the React app, TLS, Active Directory sign-in
        │
  [API servers] ×2+            FastAPI, stateless - add copies to scale
        │            │
        │     [Job queue] → [Laya workers] ×N     classification on plain CPUs
        │
        ├──→ [LLM server] GPU machine(s), open-weights model served by vLLM
        │
        ├──→ [PostgreSQL] primary + standby replica, nightly backups
        │
        └──→ [Integration gateway] one internal read-only API in front of the old systems
                 ├── Aurora Billing (mainframe)
                 ├── Helix CIS
                 ├── CaseTrack
                 └── CallCentre One / Northwind Connect
```

| Piece | Production choice | Why |
|---|---|---|
| Servers | VMs on Northwind's existing virtualisation, or its Kubernetes/OpenShift if it runs one | Use what the IT team already operates |
| Web + sign-in | nginx behind the load balancer, Active Directory sign-in | No public exposure; staff see only their team's cases |
| API | This FastAPI app, 2+ copies | One fails, the other carries on |
| Classification | Laya in background workers fed by a queue | Intake answers instantly; a backlog run never slows the app |
| LLM | vLLM on 1-2 GPU servers (Ollama is for development: it serves one request at a time) | Many staff at once, ~5-15 s per click |
| Database | PostgreSQL, primary + standby | Same database as now; only the address changes |
| Integration gateway | One internal service the agent's tools call | The agent never talks to old systems directly: safer, logged, swappable |

## The hard part: connecting to Northwind's systems

Several systems don't have live APIs: they exchange **nightly batch files** (Aurora, Helix, CaseTrack,
MeterHub) or manual exports. So the integration gateway is a mix of:

- live API calls where a system supports them (CallCentre One and Connect have REST APIs), and
- a read-only copy refreshed from the nightly files where it doesn't, with tools telling staff
  "as of last night".

That is exactly what the simulated servers in `northwind_systems/` stand in for. Moving to
production replaces them with gateway endpoints; the agent, its tools and the rules don't change
(the addresses are settings: `HELIX_URL`, `AURORA_URL`, ...).

## Controls a regulated utility will ask about

- **Audit trail:** every AI run - what it looked at, the raw records, what it suggested - is stored
  (`agent_runs`, `action_items`, `draft_responses`).
- **Access control:** staff see only their team's cases.
- **Data protection:** a data-protection impact assessment, retention rules, encrypted disks,
  internal-only traffic. No data is sent to an outside AI provider.
- **Nothing acts on its own:** the agent suggests; staff decide, edit and send.
- **Fallbacks:** if the LLM is down, the no-AI rules produce the action items and reply; if Laya is
  down, keyword rules classify; if one system is down, the rest still answer. The worklist and
  dashboards never depend on AI.

## From demo to production

| Demo | Production |
|---|---|
| One laptop | Northwind's servers, as above |
| Ollama + gemma4 on the Mac GPU | vLLM + an open-weights model on GPU servers |
| Simulated systems (`northwind_systems/`) | Integration gateway (live APIs + nightly-file copies) |
| Tiger Cloud Postgres (dev database) | Self-hosted PostgreSQL |
| `uvicorn` | Containers behind the load balancer |
