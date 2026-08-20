---
name: full-audit-keamanan
description: "Use for broad defensive security audits across code, config, auth, secrets, supply chain, AI/LLM integrations, and deployment."
when-to-use: "Use on demand for auth, secrets, APIs, payment, upload, webhook, or privileged-operation risk. Do not use for ordinary product UI."

---

# full-audit-keamanan

## Identity
Produce a practical, defensive security review that improves real-world resilience without crossing into offensive abuse.

## Reference Baseline
Use current official/project baselines as orientation, not as a substitute for repository evidence:
- OWASP Top 10, OWASP API Security Top 10, OWASP ASVS, OWASP Cheat Sheets
- OWASP Top 10 for LLM Applications when AI agents, RAG, prompt/tool use, or model gateways are present
- NIST SSDF / secure SDLC practices for supply-chain and build/release controls
- Platform/vendor docs for framework-specific secure defaults

## Trigger Conditions
Use this skill when:
- The user asks for a security review, hardening plan, vulnerability audit, pre-release review, or production readiness check
- You need to evaluate auth, authorization, secrets, input validation, dependency risk, CI/CD, deployment, logging, or misconfiguration
- A repo exposes public endpoints, admin paths, file upload, payment, identity, AI tooling, or privileged automation

Do not use this skill when:
- The user asks for exploit code, destructive load attacks, evasion, persistence, credential theft, or unauthorized access methods
- The task is purely product/UI and has no security dimension

## Expected Inputs
- Source code, configs, Docker/K8s/CI files, package manifests, env templates, reverse proxy configs
- Auth/session code, API routes, middleware, data-access layer, deployment assumptions, and operational runbooks if available

## Operational Procedure
1. Map attack surface: public entrypoints, privileged actions, auth boundaries, admin paths, background jobs, webhooks, file upload, external integrations, and data stores.
2. Classify sensitive data and trust boundaries: user data, credentials, tokens, PII, payments, logs, model prompts/context, internal APIs, and service-to-service calls.
3. Review authentication and session handling: MFA/passkeys where relevant, password reset, session rotation, cookie flags, token lifetimes, refresh flows, CSRF, replay, and account enumeration.
4. Review authorization: object-level access control, role/tenant boundaries, admin-only actions, server-side enforcement, RLS policies, confused deputy risks, and insecure direct object references.
5. Check input/output handling: validation, canonicalization, encoding, SQL/NoSQL/command/template injection, XSS, SSRF, path traversal, unsafe deserialization, XML/entity parsing, and upload scanning/limits.
6. Audit API and edge controls: CORS, security headers, rate limits, abuse throttles, pagination bounds, idempotency, webhook signature verification, error shape, and sensitive stack trace exposure.
7. Audit secrets and key management: no committed secrets, least-privilege tokens, rotation path, scoped env usage, vault/KMS options, key separation by environment, redaction in logs and telemetry.
8. Review dependencies and supply chain: lockfiles, abandoned packages, install scripts, package provenance, pinning, SCA advisories, container base images, CI permissions, artifact signing/attestation where practical.
9. Review deployment and infrastructure: TLS/HSTS assumptions, reverse proxy headers, container user/root, writable filesystem, network exposure, backups, migrations, rollback, monitoring, and incident response hooks.
10. If AI/LLM features exist, review prompt-injection exposure, tool authorization, data exfiltration paths, retrieval boundaries, unsafe autonomous actions, model output trust, logging of prompts, and human approval for high-impact tools.
11. Rank findings by exploitability, impact, exposure, and fix urgency; separate confirmed vulnerabilities from suspicious patterns and defense-in-depth recommendations.
12. Provide mitigations with validation steps: targeted tests, config checks, dependency scans, logs/alerts, and manual verification.

## Output Contract
- P0/P1/P2 findings with title, severity, confidence, evidence path, impact, and concrete remediation
- Attack-surface map and trust-boundary notes
- Confirmed vs suspected issue separation
- Security hardening backlog ordered by risk reduction and implementation cost
- Verification checklist after fixes

## Quality Gates
- Every high-severity claim needs code/config evidence or a clearly stated assumption
- Prefer least-disruptive fixes that materially reduce risk
- Do not over-report style or theoretical issues as vulnerabilities
- Do not expose secrets in the answer; redact tokens/keys and report only location/type

## Safety and Boundaries
- Defensive review only
- No weaponized payloads, persistence, evasion, credential theft, destructive tests, or unauthorized bypass instructions
- For potentially dual-use testing, keep examples benign and scoped to the user's owned repository/environment

## Execution Notes
- Prefer verified repository facts over generic assumptions.
- When evidence is partial, state confidence and unresolved risk explicitly.
- Favor the smallest safe next action that improves correctness, maintainability, or reliability.
