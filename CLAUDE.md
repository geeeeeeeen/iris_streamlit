# CLAUDE.md

Guidance for AI assistants working in this repository.

## Read this first: two unrelated apps live here

The repository name says `iris_streamlit`, but **nothing here touches the Iris
dataset** — no ML, no scikit-learn. Treat the name as a historical artifact. Do
not add Iris code because the name implies it; if a task genuinely concerns the
Iris dataset, confirm intent first.

`main` itself contains **no application code** — only `.gitkeep`. The code lives
on branches:

| Branch | Contents |
| --- | --- |
| `main` | `.gitkeep` only |
| `claude/claude-md-documentation-exsomn` | **USJ route planner** — `usj_app.py`, `usj/`, `tests/` |
| `codex/redesign-conference-website-ui` (open PR #1) | Conference homepage — `app.py` |

The two apps are unrelated and share no code. They are deliberately kept in
separate entry points so they do not collide:

- `usj_app.py` — USJ wait-times / route planner (this branch)
- `app.py` — Japanese academic-conference homepage (PR #1)

**Do not rename either entry point to `app.py`** without merging first. The USJ
app was named `usj_app.py` specifically so it would not conflict with PR #1's
`app.py` at merge time.

## The USJ route planner

Fetches Universal Studios Japan wait times and proposes an optimal touring
order. An unofficial fan tool — say so in any UI you add.

```bash
pip install -r requirements.txt
streamlit run usj_app.py        # http://localhost:8501
python3 -m pytest tests/ -q     # 37 tests, ~0.5s
```

### Layout

| Path | Role |
| --- | --- |
| `usj_app.py` | Streamlit UI only — widgets, layout, rendering |
| `usj/attractions.py` | Seed dataset: 17 attractions, coords, ride length, popularity |
| `usj/wait_times.py` | Wait-time sourcing (live API / simulation) + time-of-day model |
| `usj/router.py` | Route optimization |
| `tests/test_usj.py` | Tests for the whole `usj` package |

**Keep the split.** `usj/` holds pure logic with no Streamlit import — that is
what makes it testable. Put UI in `usj_app.py`, decisions in `usj/`. Do not
`import streamlit` inside the package.

### Wait-time sourcing, and the rule about it

Two sources, selected by `load_wait_times()`:

1. `fetch_live()` — queue-times.com public API, matched to the Japanese
   attraction names via each `Attraction.aliases` tuple.
2. `simulate()` — deterministic estimate from popularity × time-of-day curve ×
   crowd level, used whenever live fetch fails.

**Never present estimated waits as real ones.** `WaitSnapshot.degraded` says
which source was used, and the UI must show it. This is the one convention in
this app worth protecting: a plausible-looking fake number that the user
believes is live is the app's worst failure mode.

Related: keep exception text out of user-facing copy. `WaitSnapshot.note` is the
human message; `WaitSnapshot.detail` carries the technical reason, shown in a
collapsed expander. A test enforces this separation.

The live API was **never reachable from the sandbox** it was developed in
(egress policy returns 403 for `queue-times.com`), so `fetch_live()` is written
against the documented API shape but has not been exercised against the real
endpoint. Verify it before trusting it; the fallback path is well tested.

### The optimizer

`plan_route()` solves a **time-dependent orienteering problem**: not everything
fits in a day, so it chooses *which* attractions and *in what order*.

- cost = walk + predicted wait on arrival + ride time + buffer
- value = `attraction_value()` — `popularity ** bias`, must-see gets +1000
- Method: greedy construction, then local search (2-opt, Or-opt, insertion)

Two things to know before changing it:

- **It is a heuristic. It does not return optimal routes** and should never be
  described as if it did.
- `attraction_value()` is the single source of truth for value. It is convex in
  popularity on purpose: with linear value, value-per-minute always favors
  two-minute kiddie rides and the plan silently drops the headliners.

When you change scoring or timing, run the tests — several encode invariants
that a plausible-looking route can violate: the deadline is never exceeded,
times are monotonic, no attraction is visited twice, visited ∪ skipped covers
the candidates.

### Modeling caveats to preserve in the UI

Coordinates, ride durations, and the attraction roster are **approximations**
maintained by hand in `usj/attractions.py`, not park data. Walk times come from
haversine × 1.35 detour factor. The wait prediction just scales the current wait
by the ratio of demand-curve values. The UI states these limits; keep it that
way rather than quietly implying precision.

## The conference homepage (PR #1)

Single-file Streamlit page for a Japanese academic conference. ~204 lines,
top-to-bottom, no functions. Styling is **CSS-in-markdown**: 12 of its 15 `st.*`
calls pass `unsafe_allow_html=True` with raw HTML strings. Design tokens live on
`:root` (`--brand-navy`, `--brand-blue`, `--brand-cyan`, `--brand-gold`); the
class vocabulary is `.hero`, `.chip`, `.section-title`, `.card`, `.event-list`,
`.event-date`, `.footer-note`. Section headings are `<div class="section-title">`,
not `st.header`. Content is deliberately placeholder (`○○`, `第XX回`,
`office@example.jp`) — invent no real institutions or contacts.

## Shared conventions

- **UI copy is Japanese** in both apps. Code identifiers, docstrings for
  structure, and commit messages follow the existing files (docstrings and
  comments are Japanese in `usj/`).
- **CSS-in-markdown with `:root` design tokens** is the house style. Both apps
  define one `<style>` block up top and reuse a small class vocabulary. Follow
  the app you are editing rather than mixing the two palettes.
- **`unsafe_allow_html=True` is safe only while every interpolated value is
  trusted.** `usj_app.py` runs attraction names through `html.escape()` for this
  reason. If you introduce user input, query params, or fetched data, escape it
  or use a normal Streamlit widget — never interpolate it raw.
- `st.set_page_config(...)` must stay the first Streamlit call in an entry point.

## Testing and CI

`tests/` covers the `usj` package (37 tests). There is **no CI, no linter
config, and no test coverage at all for `app.py`** — so outside `usj/`, nothing
verifies a change but running the app and looking at it.

- Say what you actually did. "37 tests pass" is a real claim; "verified" for a
  CSS change you never rendered is not.
- Visual changes need the app running (or a screenshot) to confirm.
- Adding a linter or CI is a real change — propose it, don't slip it into an
  unrelated diff.

## Git conventions

- Default branch: `main`. Remote: `https://github.com/geeeeeeeen/iris_streamlit` (public).
- Branches carry the prefix of the agent that created them: `claude/…`, `codex/…`,
  kebab-case description.
- Work reaches `main` through pull requests. Commit subjects are short imperative
  descriptions; no issue-number or type prefix convention.
- Push with `git push -u origin <branch>`. Do not push to a branch you were not
  asked to use, and do not open a PR unless asked.

## Maintaining this file

Describes the repo as of `main` = `df2a1bd`, PR #1 head = `80535e0`. Update it in
the same PR when: PR #1 merges (`app.py` lands on `main`), the USJ branch merges,
`usj/attractions.py` changes shape, or the optimizer's scoring model changes.
