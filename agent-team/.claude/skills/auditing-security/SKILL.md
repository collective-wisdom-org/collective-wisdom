---
name: auditing-security
description: Perform a systematic security audit of a codebase, checking for OWASP Top 10 vulnerabilities, secrets exposure, and insecure patterns.
---

# Security Audit

Use when the user asks to audit security, check for vulnerabilities, review code for security issues, or harden an application.

## Steps

1. **Hardcoded secrets.** Search source for API keys, tokens, passwords and connection strings: `password=`, `secret=`, `token=`, `api_key=`; base64-encoded credentials; AWS keys (`AKIA...`), Stripe keys (`sk_live_...`), GitHub tokens (`ghp_...`); a committed `.env`, a `config.json` with credentials.
2. **Authentication and authorization.** Every API route checks authentication before processing. Role-based access is enforced server-side, not only in the UI. Passwords hashed with bcrypt or argon2, not MD5 or SHA1. Session tokens HTTP-only, secure, with reasonable expiry.
3. **Injection.**
   - SQL: string concatenation in queries instead of parameters.
   - XSS: `dangerouslySetInnerHTML`, `innerHTML`, unescaped user input in templates.
   - Command: `exec()`, `eval()`, `child_process.exec()` with user input.
   - Path traversal: unsanitized user input in file paths.
4. **Dependencies.** Run `npm audit` or `pip audit`. Flag outdated dependencies with known CVEs and overly permissive ranges.
5. **CORS and CSP.** No `Access-Control-Allow-Origin: *` in production. Content Security Policy present. `X-Frame-Options`, `X-Content-Type-Options` and `Strict-Transport-Security` set.
6. **Data exposure.** API responses leak no sensitive fields (password hashes, internal IDs, PII). Production errors show no stack traces or internals. Logs hold no sensitive data.
7. **Report.** Findings with severity (Critical / High / Medium / Low), file path, line number and recommended fix.

## Notes

- A code review, not a penetration test. Recommend `npm audit`, `trivy` or `snyk` for automated scanning, and the OWASP Testing Guide for a comprehensive audit.
- Check `.gitignore` excludes `.env`, credentials and key files.
