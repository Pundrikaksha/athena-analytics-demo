# Security scan summary

- Tool: gitleaks 8.30.1, default ruleset, findings redacted
- Date: 2 Nov 2026 (IST)
- `gitleaks git .`: every commit in the history scanned. **No leaks found.**
- `gitleaks dir .`: working tree scanned, including untracked files. **No leaks found.**
- Tracked files: no `.env`, key, `.pem` or credential files. `.gitignore` blocks `.env*`, `*.key`, `*.pem`.
- Code guard: `tests/test_analytics.py::SafetyGuards` fails the build if order-placement, broker-SDK,
  API-key/token or outbound-network code appears in `athena_demo/` or `scripts/`, if any `.env` file exists,
  or if the page loads external scripts.

Re-run before every publish:

```sh
gitleaks git . --redact && gitleaks dir . --redact && python3 -m unittest
```
