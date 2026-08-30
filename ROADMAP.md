# Roadmap

Utility Split Agent is usable as a tested reference implementation today. The
next work is about making it easier to adopt, demo, and extend safely.

## Now

- Add a one-command local setup path with pinned developer dependencies.
- Add a sample output file so visitors can inspect results without running code.
- Add GitHub issue templates for bug reports, provider requests, and roadmap
  tasks.
- Document how to add a real provider fetcher without committing secrets or
  tenant data.

## Next

- Package the CLI so it can run as `utility-split` after install.
- Add JSON and CSV output modes for importing split results into spreadsheets.
- Add validation for tenant config files with clearer error messages.
- Add a dry-run provider harness that records selector expectations without
  logging into a real account.

## Later

- Support multiple bills in one run.
- Add a minimal web UI for non-technical users.
- Add optional OCR fallback before LLM parsing.
- Add provider-specific examples once they can be documented without exposing
  private account details.

## Contribution Ideas

- Improve README screenshots or terminal output examples.
- Add tests for edge cases around rounding, zero weights, and malformed config.
- Add a new allocation method with a clear real-world use case.
- Create a provider fetcher template for a common utility portal.

## Non-Goals

- Do not automate payment or tenant charge submission.
- Do not store real tenant names, credentials, bills, or account data in the
  repository.
- Do not let LLM output directly determine final charges without validation.
