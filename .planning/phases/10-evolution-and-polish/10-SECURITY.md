---
phase: 10
slug: evolution-and-polish
status: verified
threats_open: 0
asvs_level: 1
created: 2026-04-06
---

# Phase 10 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| Save file -> model validation | Evolution fields loaded from JSON save file | OwnedCreature.battles_won_with (int), evolution_declined (bool) |
| User input -> evolution prompt | Player accepts/declines evolution via input() | Single character string |
| Creature JSON -> template loading | evolves_to field references another template ID | String template ID |
| Terminal -> render modules | console.width used for narrow detection | Integer width value |

---

## Threat Register

| Threat ID | Category | Component | Disposition | Mitigation | Status |
|-----------|----------|-----------|-------------|------------|--------|
| T-10-01 | Tampering | OwnedCreature.battles_won_with in save file | accept | Local save file — user controls their own data. Pydantic validates type (int). No competitive multiplayer. | closed |
| T-10-02 | Denial of Service | evolution_condition dict with unexpected keys | mitigate | check_condition_evolution returns False for unknown condition types — never crashes. Verified in evolution_engine.py:51-70. | closed |
| T-10-03 | Spoofing | Evolution prompt input | accept | Local CLI game — input().strip().lower() == "y", anything else declines. No injection risk. | closed |
| T-10-04 | Tampering | evolves_to pointing to nonexistent template | mitigate | get_creature() wrapped in try/except KeyError in battle.py:172-180. Evolution skipped gracefully with dim error message. | closed |
| T-10-05 | Denial of Service | Circular evolution chain in JSON | mitigate | apply_evolution mutates template_id once — no loop. Each battle checks once per creature. Verified in evolution_engine.py:87-102. | closed |
| T-10-06 | Information Disclosure | console.width returns 0 or negative | mitigate | Rich Console defaults width to 80 when terminal detection fails. narrow=False when width >= 40. Verified in battle.py:247. | closed |

*Status: open · closed*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-10-01 | T-10-01 | Local single-player game — save file tampering is user's prerogative. Pydantic type validation prevents crashes. | GSD security audit | 2026-04-06 |
| AR-10-03 | T-10-03 | Local CLI input — no network surface, no injection vector. Strict equality check on "y". | GSD security audit | 2026-04-06 |

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-04-06 | 6 | 6 | 0 | GSD orchestrator (inline verification) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-04-06
