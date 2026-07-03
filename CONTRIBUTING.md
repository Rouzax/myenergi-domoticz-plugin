# Contributing

Thanks for your interest in improving the myenergi Monitor plugin. Issues and pull requests are
welcome.

## Branches

- **`main`** - development (source, tests, docs). Open PRs against this branch.
- **`dist`** - a lean, runtime-only branch that users install from. It is generated automatically
  on each release; **do not edit it by hand**.
- **`gh-pages`** - the built documentation site (generated). Do not edit by hand.

## Development setup

The runtime is **stdlib-only** and targets **Python 3.9**. Dev tooling is pinned in
`requirements-dev.txt`.

```bash
git clone https://github.com/Rouzax/myenergi-domoticz-plugin
cd myenergi-domoticz-plugin
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements-dev.txt
```

## Before you open a PR

Run the full local gate (the same checks CI runs):

```bash
ruff check --fix .        # lint + import sort
ruff format .             # format
python3 -m pyright        # static type check (basic)
python3 -m pytest         # tests (add tests for any behaviour change)
```

Conventions:

- Python 3.9 floor; no third-party packages at runtime (stdlib only).
- Keep repo-root `*.py` runtime-only - dev-only scripts live under `tools/` or `tests/`.
- No em-dash characters in code, comments, or docs.
- Never commit secrets or real serials; fixtures use placeholder values.

## Docs

The manual is [MkDocs](https://www.mkdocs.org/) + Material under `docs/`.

```bash
pip install mkdocs-material==9.6.23
mkdocs serve            # live preview at http://127.0.0.1:8000
mkdocs build --strict   # must pass
```
