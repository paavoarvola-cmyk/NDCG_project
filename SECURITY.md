# Secret Management Setup

This repository uses secure defaults for API key handling.

## 1) Local development

1. Copy `.env.example` to `.env`.
2. Set real credentials in `.env` only (for example: `OPENAI_API_KEY`, `SCOPUS_API_KEY`, `OPENALEX_API_KEY`).
2. Set real credentials in `.env` only.
3. Never commit `.env`.

```bash
cp .env.example .env
```

## 2) Pre-commit secret scanning

This repository includes a pre-commit hook powered by Gitleaks.

### Install once

```bash
pip install pre-commit
pre-commit install
```

### Run manually

```bash
pre-commit run --all-files
```

## 3) Production secret management

For production, store secrets in a managed secret store (for example: AWS Secrets Manager, GCP Secret Manager, Azure Key Vault, or Vault).

## 4) Minimum key policy

- Use separate keys for dev/staging/prod.
- Grant the narrowest permissions possible.
- Rotate keys on a regular cadence.
- Revoke and rotate immediately after any suspected exposure.
- Do not log API keys or include them in error messages.
