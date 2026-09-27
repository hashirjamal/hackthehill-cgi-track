# Next steps

Status as of 2026-09-27. For what is built, see [HANDOFF.md](HANDOFF.md).

## Done

- [x] Intake form → Laya → open case on the worklist
- [x] Laya owns category and urgency; backlog classified (resumable `python -m app.classify_backlog`)
- [x] Backlog rows without text fall back to their recorded category when Laya is unsure
- [x] Get context / Generate draft on the case page, on gemma4 (thinking off, ~20-50 s per click)
- [x] Five simulated Northwind systems (Aurora, Helix, CaseTrack, CallCentre One, Connect), each with
      its own API, ids and era-styled console; agent tools that call them; "Systems checked" trace
- [x] AI on / AI off switch on the case page (rules + templates, same systems, ~1 s)
- [x] Laya tuned and measured (`evals/laya_text_eval.py`); keyword-rules classifier as a no-AI option
- [x] Demo script and production architecture write-up

## Before the demo

- [ ] Re-check the four showcase cases load with saved results (DEMO_SCRIPT.md)
- [ ] Rehearse the demo once end to end, timing the live AI click
- [ ] Merge the open PR to `main`

## Worth doing if there is time

- **Laya accuracy.** Remaining misses: "estimated bill" vs "meter not read" (both route to the
  Metering team), general questions that mention bills, some water-quality wording. Change the
  wording in `app/classification/taxonomy.py`, then run
  `python -m evals.laya_text_eval --holdout --fresh --quiet` and keep only changes that improve the
  holdout and fresh scores.
- **Per-domain system prompts** in `app/agents/config.py` (currently one generic prompt per domain).
- **Draft workflow:** approve / edit / mark sent, so drafts have a status staff can track.
- **Simulator backend** for the what-if page.
