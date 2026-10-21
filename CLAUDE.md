# revenue-monitor: rules for agents

Instructions for coding agents working in this repo; a human reader wants `README.md`. Read
`README.md` for how it works, `RUNBOOK.md` for procedures, `TASK.md` for what is open. The
owner's global agent rules apply on top of these.

- Public repo: no personal data, account figures, third-party names or the owner's email in any file; a pre-commit scan blocks them.
- Real-time commits only; never backdate, never set `GIT_AUTHOR_DATE`.
- Release steps: `RUNBOOK.md` §Release.
- README, RUNBOOK, CLAUDE and TASK each hold one kind of fact; the README commands table is
  generated, never hand-edited.
- Traps: MetricForge is pinned by tag and metric-helpdesk pins the same one, bump both; a metric definition change must keep `assert_mrr_bridge_reconciles` green and match README §Metric definitions, the dashboard and the mart have disagreed before; `make all` deletes nothing but `make clean` removes the warehouse; the dashboard deploys only from CI, never push a built site.
