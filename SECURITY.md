# Security Policy

## Supported Versions

We actively provide security patches and dependency updates for the following versions:

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |
| < 1.0   | :x:                |

---

## Reporting a Vulnerability

We take the security of FacelessReels and our community seriously. If you believe you have found a security vulnerability or credential leak, please report it responsibly:

1. **Do NOT open a public GitHub issue.**
2. Send an email to the repository maintainer or report via **GitHub Private Vulnerability Reporting** on the repository page under `Security` > `Advisories` > `Report a vulnerability`.
3. Include detailed steps to reproduce the issue, proof of concept (where safe), and any potential impact.
4. We will acknowledge receipt of your report within 48 hours and work on a coordinated fix.

---

## Credential Safety Guidelines for Developers & Users

- **Environment Variables**: Always store API keys (`GEMINI_API_KEY`, `ELEVENLABS_API_KEY`, etc.) in a local `.env` file or export them in your shell environment.
- **Git Ignore**: Verify that `.env`, `credentials/`, and `config/client_secrets.json` are listed in `.gitignore` before committing.
- **Accidental Leaks**: If you accidentally commit a live API key or credential, immediately revoke and rotate the key in the provider console (e.g. Google Cloud Console, ElevenLabs). Merely deleting the commit or deleting the file in a subsequent commit does NOT prevent past commit history from being read or indexed.
- **Dry-Run Mode**: For YouTube upload integrations, always verify your configuration in dry-run mode (`dry_run=True`) before executing live publish operations.

