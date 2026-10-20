# Runbook

Procedures for revenue-monitor. `README.md` describes what each command does; this file says
when to run it and in what order.

## On open

```bash
git status --short
git log -3 --oneline
```

## On close

```bash
make lint
make test
```

## Rebuild from nothing

1. `make build` once per machine (Python and Node dependencies).
2. `make all`: generate, load, dbt build, dashboard sources. Everything lands under `data/`
   and the Evidence source cache; nothing is committed.
3. `make metrics` to see the numbers; `make dashboard-dev` to browse them.
4. After a change to models or macros: `make dbt`, then `make test-all` before committing.

## Bump the MetricForge pin

1. Change the tag in `pyproject.toml` (`metricforge @ git+...@vX.Y.Z`); `uv lock`.
2. `make lint && make test-all`.
3. Commit `chore(deps): Pin metricforge to vX.Y.Z`; do the same in metric-helpdesk and update
   the version recorded for metricforge in hq (`~/developer/hq/repos.json`).

## Release

Conventions in `~/developer/hq/CONVENTIONS.md` §Versioning.

1. Bump `version` in `pyproject.toml` and `__version__` in `src/revenue_monitor/__init__.py` to
   the same value; `uv lock`.
2. Commit `chore: Release vX.Y.Z`, then `git tag -a vX.Y.Z -m "vX.Y.Z"` and
   `git push origin main --tags`.
3. `gh release create vX.Y.Z --title "revenue-monitor vX.Y.Z" --notes "<what changed>"` with
   the compare link to the previous tag, marked latest.
4. CI must be green on the tagged commit (both jobs). Nothing pins this package.

## Deploy

Nothing to do by hand: every push to `main` runs `ci.yml`, whose pipeline job regenerates the
data, builds dbt, runs the integration tests and builds Evidence strictly; the deploy job
publishes to GitHub Pages only when lint-test and pipeline both pass. A stale site means a red
run: read the Actions log. If Pages was never enabled, set the source to "GitHub Actions" once.

## Restore on a new machine

1. Clone `git@github.com:m4dd0ck/revenue-monitor.git`; install Node 18+; `make build`.
2. `make all`. No secrets: the data is generated. `STRIPE_API_KEY` is only for the optional
   test-mode pull.

## Validate

```bash
make lint
make test-all
make dbt
make dashboard-build
python3 ~/.claude/scripts/doc-check.py --repo .
```
