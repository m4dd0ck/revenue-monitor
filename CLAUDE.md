# revenue-monitor: rules for agents

Read `README.md` for how it works, `RUNBOOK.md` for procedures, `TASK.md` for what is open.
Global rules in `~/.claude/CLAUDE.md` still apply.

- Public repo: no personal data, account figures, third-party names or the owner's email in any file; the git gate blocks them.
- Real-time commits only; never backdate, never set `GIT_AUTHOR_DATE`.
- Releases follow hq CONVENTIONS (`~/developer/hq/CONVENTIONS.md`); the RUNBOOK names the steps.
- Docs follow the four-file skeleton: a fact lives in one file, and the commands table is generated.
- Traps: MetricForge is pinned by tag and metric-helpdesk pins the same one, bump both; a metric definition change must keep `assert_mrr_bridge_reconciles` green and match README §Metric definitions, the dashboard and the mart have disagreed before; `make all` deletes nothing but `make clean` removes the warehouse; the dashboard deploys only from CI, never push a built site.
