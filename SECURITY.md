# Security Policy

SENTINEL-X is a proof-of-concept threat-fusion platform. Security reports are
welcome and handled with priority.

## Supported versions

| Version | Supported |
|---------|-----------|
| `main`  | Yes       |
| Older tags / forks | No |

## Reporting a vulnerability

Please **do not open a public issue** for security problems.

1. Use GitHub's private reporting: **Security → Report a vulnerability** on this repository, or
2. Email **wisnualfiannurashar@gmail.com** with the subject `SENTINEL-X security`.

Include where possible:

- affected component (API, gateway, ingestor, correlation engine, frontend, Docker/Ansible deployment)
- steps to reproduce or a proof of concept
- impact you observed and any suggested fix

## What to expect

| Step | Target |
|------|--------|
| Acknowledgement | within 3 days |
| Triage and severity rating (CVSS 3.1) | within 7 days |
| Fix or mitigation for High/Critical | as soon as possible, typically within 30 days |
| Public disclosure | coordinated with the reporter after a fix is available |

Reporters who follow this process are credited in the release notes unless they prefer to stay anonymous.

## Scope notes

- Values in `.env.example` and the Hardhat development key used for the local test chain are public placeholders, not secrets.
- Never deploy with default credentials; rotate every value in `.env` before exposing the stack.

## Automated checks

Every push runs secret scanning (Gitleaks), dependency auditing, CodeQL static analysis and Dockerfile linting (hadolint).
