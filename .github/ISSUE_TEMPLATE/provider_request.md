---
name: Provider request
about: Request or plan a read-only utility provider fetcher
title: "Provider: "
labels: provider
assignees: ""
---

## Provider

- Utility/provider name:
- Login style: username/password / magic link / SSO / unknown
- Bill format: PDF / HTML / unknown

## Read-only download flow

Describe the pages and actions needed to reach the latest bill download. Keep it high level and omit private account details.

## Required secrets

List environment variable names only, using placeholder names like `PROVIDER_URL`, `PROVIDER_USERNAME`, and `PROVIDER_PASSWORD`.

## Safety notes

- Fetcher only downloads bills; it must not submit charges or payments.
- Real credentials, tenant names, account numbers, and bill files stay out of the repository.
