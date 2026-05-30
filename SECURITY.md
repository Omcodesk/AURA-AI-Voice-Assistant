# Security Policy

## Supported Versions

| Version | Supported |
|:---|:---|
| 1.0.x (Phase 4) | ✅ Active |
| < 1.0 | ❌ No longer supported |

## Reporting a Vulnerability

If you discover a security vulnerability in AURA — especially related to:
- **Biometric authentication bypass**
- **API key exposure**
- **Remote code execution via voice commands**
- **Privilege escalation via session guard**

**Please do NOT open a public GitHub issue.**

Instead, report it privately by emailing:
📧 **ommm4793@gmail.com**

Include:
- A clear description of the vulnerability
- Steps to reproduce
- Potential impact
- (Optional) A suggested fix

You will receive a response within **72 hours**. If the vulnerability is confirmed, a patch will be issued and you will be credited in the release notes (unless you prefer to remain anonymous).

## Security Design Notes

AURA is designed with the following security principles:

- **All API keys** are loaded exclusively from environment variables (`.env`) — never hardcoded.
- **Biometric data** (face embeddings) is stored locally in SQLite (`aura.db`) and is **never transmitted** to any external server.
- **Dangerous system commands** (shutdown, restart, lock) require explicit voice confirmation before execution.
- **Session Guard** enforces role-based access — sensitive actions require fresh biometric re-authentication.
- The `.env` file and `data/` directory are **gitignored** — they are never committed to version control.
