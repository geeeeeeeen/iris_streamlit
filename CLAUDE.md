# CLAUDE.md

Guidance for AI assistants working in this repository.

## Read this first: the default branch is empty

`main` contains **no application code** — only `.gitkeep` (and this file). If you
check out `main`, look for `app.py`, and find nothing, that is expected; the
repository has not gone missing.

All existing application code lives on one **unmerged** branch:

| Branch | Contents |
| --- | --- |
| `main` | `.gitkeep`, `CLAUDE.md` — no app code |
| `codex/redesign-conference-website-ui` (open PR #1) | `app.py` — the entire application |

Before starting work, decide which of these you are building on and say so:

```bash
# inspect the app without checking it out
git fetch origin codex/redesign-conference-website-ui
git show origin/codex/redesign-conference-website-ui:app.py

# or branch from it, to build on the PR's work
git checkout -b <your-branch> origin/codex/redesign-conference-website-ui
```

Starting from `main` means starting from an empty directory. That is the right
choice only for work that is genuinely independent of the PR.

## What this project is

A **single-file Streamlit web app** rendering the homepage of a Japanese
academic conference ("第XX回 日本○○学会 学術集会 2026"). It is a static
presentational page: no data layer, no forms, no user input, no persistence.

**The repository name is misleading.** `iris_streamlit` suggests the Iris
dataset; the code is a conference website with no ML or dataset code anywhere.
Treat the name as a historical artifact — do not add Iris/scikit-learn code just
because the name implies it, and do not "fix" the conference content to match
the name. If a task genuinely concerns the Iris dataset, confirm intent first.

All UI copy is **Japanese**. Content is deliberately placeholder — `○○`, `第XX回`,
`office@example.jp`, `03-1234-5678`, `〒000-0000`. Preserve that convention:
invent no real institutions, addresses, or contact details.

## Architecture of `app.py`

~204 lines, executed top to bottom on every rerun — Streamlit's standard
execution model. No functions, no classes, no modules, no imports beyond
`streamlit as st`. Structure in order:

1. **`st.set_page_config(...)`** — must stay the first Streamlit call in the
   file; Streamlit errors if anything else precedes it.
2. **One global `<style>` block** injected via `st.markdown(..., unsafe_allow_html=True)`.
3. **Hero banner** — gradient header with title, subtitle, and `.chip` badges.
4. **Two-column body** — `st.columns([1.4, 1], gap="large")`:
   - left: 開催概要 (two nested `.card` columns), then お知らせ (a Python list of
     `(date, body)` tuples looped into `.event-list` blocks — the only loop in
     the file);
   - right: 主要日程 (Important Dates) and お問い合わせ (contact).
5. **Footer** — `.footer-note` copyright line.

### Styling conventions

Styling is **CSS-in-markdown, not Streamlit widgets**. 12 of the 15 `st.*` calls
pass `unsafe_allow_html=True` and hand Streamlit a raw HTML string. Follow the
existing system rather than introducing a second one:

- **Design tokens** are CSS custom properties on `:root`: `--brand-navy`
  (`#10233f`), `--brand-blue` (`#1d4e89`), `--brand-cyan` (`#2d8fce`),
  `--brand-gold` (`#d2a756`), `--text-main`, `--bg-soft`. Reference these
  instead of pasting new hex literals.
- **Class vocabulary**: `.hero`, `.chip`, `.section-title`, `.card`,
  `.event-list`, `.event-date`, `.footer-note`. Reuse before inventing.
- Section headings are `<div class="section-title">`, **not** `st.header` /
  `st.subheader` — matching the surrounding code matters more here than using
  the idiomatic Streamlit widget.
- Keep all CSS in the single `<style>` block at the top; do not scatter
  per-component `<style>` tags.

### On `unsafe_allow_html=True`

Safe as written **because every interpolated value is a hardcoded literal**. The
one f-string (the お知らせ loop) interpolates from a list defined inches above it.

If you introduce dynamic content — user input, query params, uploaded files, or
fetched data — do not interpolate it into these HTML strings. Render it through
a normal Streamlit widget, or escape it (`html.escape`), otherwise the page
becomes an HTML/script injection vector.

## Running the app

There is **no dependency manifest** — no `requirements.txt`, `pyproject.toml`,
`Pipfile`, or lockfile. Streamlit is the only third-party import.

```bash
pip install streamlit
streamlit run app.py        # serves on http://localhost:8501
```

Environment in the standard container: Python 3.11.15, with `pip` 24.0,
`uv` 0.8.17, and `poetry` 2.3.3 available. **Streamlit is not preinstalled**, and
neither are pandas/numpy/scikit-learn/plotly/altair/matplotlib — install what you
need. `python3 -m py_compile app.py` syntax-checks the file without installing
anything, which is the cheapest useful check available today.

If you add a dependency, add a manifest in the same change — pinning `streamlit`
alongside it — rather than leaving the install implicit.

## Testing, linting, CI

**None exist.** No test suite, no `pytest`/`ruff`/`black` config, no
`.github/workflows`, no `.gitignore`, no pre-commit hooks. There is no command
that verifies a change beyond `py_compile` and running the app by eye.

Consequences for how you work:

- Do not claim a change is "tested" or "verified" — nothing verifies it. Say what
  you actually did: compiled it, ran it locally, read the diff.
- Visual/CSS changes need a running app (or a screenshot) to confirm. State
  plainly when you could not run it.
- Adding tooling is welcome but is a real change: propose it rather than slipping
  a linter config into an unrelated diff.

## Git conventions

- Default branch: `main`. Remote: `https://github.com/geeeeeeeen/iris_streamlit` (public).
- Branches are **prefixed by the agent or tool that created them**:
  `codex/<description>`, `claude/<description>`. Use kebab-case descriptions.
- Work reaches `main` through pull requests; `main` has one commit
  (`df2a1bd Initialize repository`) and no direct-push history to imitate.
- Commit subjects are short imperative descriptions
  (`Create polished Streamlit conference homepage redesign`). No prefix
  convention, no issue-number convention.
- Push with `git push -u origin <branch>`. Do not push to a branch you were not
  asked to use, and do not open a PR unless asked.

## Maintaining this file

This document describes the repository as of `main` = `df2a1bd` and PR #1 head =
`80535e0`. Two changes would make it wrong; update it in the same PR that causes
them:

- **PR #1 merges** — delete the "default branch is empty" section, since `app.py`
  will then be on `main`.
- **`app.py` gains structure** — multiple pages, modules, a data layer, or a
  dependency manifest — the architecture and running sections need rewriting.
