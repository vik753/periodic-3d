# periodic-3d — instructions for the agent

Project: interactive 3D periodic table with compound exploration.
Customer: Ihor (repo owner, github.com/vik753). Team lead and developer: Claude.
The customer approved the plan (docs/plan.md) and gave carte blanche:
choose between options yourself, ask only on real blockers.

## Communication with the customer

- Language: Russian. Short sentences, one instruction per sentence, active voice,
  consistent terms (ASD-STE100 style).
- Instructions for the customer: complete commands, structure
  "goal → commands → explanation → expected result". Add short theory blocks on
  important backend and AI topics.
- No job-interview "key rules" blocks in this project.
- Send a short report after each stage. Put blockers in docs/BLOCKERS.md and in the
  chat, then continue with other tasks.

## Resume protocol — do this at the start of every session or resumed turn

1. `cd /home/claude/periodic-3d && git pull --rebase` (clone the repo if it is missing).
2. Read docs/agent/PROGRESS.md and docs/agent/TASKS.md.
3. Re-arm the auto-resume alarms (next section).
4. Smoke check: `make check` locally, then look at the latest CI runs on main
   (`gh run list -L 5`).
5. Continue with the first unchecked task in docs/agent/TASKS.md.
   Small steps: change → check → commit → push.
6. Update docs/agent/PROGRESS.md after each task.

## Auto-resume alarms

The customer asked to continue automatically after usage-limit stops.
Alarms are `send_later` messages into the main session, named
"periodic-3d: автопродолжение (…)".

- Keep four alarms: about +6 h, +1 day, +3 days and +7 days from now.
- During active work, move the +6 h alarm forward about every hour
  (`update_trigger` with a new `run_once_at`).
- When an alarm fires, create a replacement further out.
- Current trigger IDs live in docs/agent/PROGRESS.md. Keep them up to date.
- When the project is done, delete all alarms.

## Environment constraints (cloud session)

- The container has no internet except GitHub: git, repo-scoped api.github.com
  endpoints and codeload.github.com.
- npm and PyPI registries are NOT reachable. Data sources (PubChem, Wikidata,
  Wikipedia, COD, Materials Project) are NOT reachable. Do not try mirrors or other
  routes around the egress policy.
- Therefore installs, builds, tests and data fetching run in GitHub Actions.
- Local tools that work: python3 (numpy, pandas, pydantic, networkx, scipy,
  scikit-learn, uvicorn), node 22 (typescript, tsx), Playwright + Chromium
  (/opt/pw-browsers), PostgreSQL 16 binaries (/usr/lib/postgresql/16/bin).
- Lockfiles (package-lock.json, uv.lock) are created in CI and committed back to main
  (tools/ci/commit-back.sh, `[skip ci]`). Run `git pull --rebase` before every push.
- Machine outputs from CI (reports, screenshots, built previews) go to the
  `ci-results` branch. Fetch them with git.
- GitHub Pages hosts the live demo (static mode):
  https://vik753.github.io/periodic-3d/ . The container cannot open github.io —
  check the demo through CI screenshots.

## Repository map

- `apps/web` — React 19 + TypeScript + Vite + React Three Fiber (3D frontend).
- `apps/api` — FastAPI + SQLAlchemy 2 (async) + PostgreSQL/pgvector, read-only API,
  static export.
- `pipeline` — Python CLI: fetch → normalize → enrich → compute → dataset.
- `tools` — CI helpers and probes.
- `infra` — docker compose and deploy configs.
- `docs` — plan, ADRs, deploy guide, agent state.

## Conventions

- Code, comments and commit messages: English. Customer-facing docs in `docs/`: Russian.
- Conventional Commits: feat, fix, chore, docs, ci, refactor, test, perf.
- Never commit secrets. Secrets live in env vars and GitHub secrets.
- Data licenses: store the license per record, exclude the GNoME dataset (CC BY-NC),
  keep the "Sources and licenses" page current.
- Performance budgets are in docs/plan.md. Do not ship features that break them.
- Versions (SemVer): `apps/web/package.json` is the single source. For each customer-visible
  change bump it, add an entry to CHANGELOG.md, CHANGELOG.uk.md and CHANGELOG.ru.md and the
  "Current version" line of the three READMEs, then push a tag `vX.Y.Z` on that commit.
