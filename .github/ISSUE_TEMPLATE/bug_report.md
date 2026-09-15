---
name: Bug report
about: Report incorrect parsing, splitting, CLI, or fetcher behavior
title: "Bug: "
labels: bug
assignees: ""
---

## What happened

Describe the unexpected behavior and what you expected instead.

## Reproduction

```bash
python -m pip install -e ".[dev]"
python -m pytest -q
utility-split --amount 247.86 --config config/tenants.example.yaml
```

Replace the commands above with the smallest command or test that reproduces the issue.

## Input shape

- Split method:
- Config source: example config / sanitized real config
- Bill source: `--amount` / local PDF / provider fetcher

Do not include real tenant names, credentials, bills, or account data.

## Environment

- Python version:
- OS:
- Package install method:
