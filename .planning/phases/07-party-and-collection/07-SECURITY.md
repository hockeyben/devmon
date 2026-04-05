---
phase: 07-party-and-collection
auditor: gsd-secure-phase
asvs_level: 1
audit_date: "2026-04-05"
threats_total: 10
threats_closed: 10
threats_open: 0
result: SECURED
---

# Phase 7 Security Audit — Party and Collection

## Summary

**Phase:** 7 — party-and-collection
**Threats Closed:** 10/10
**ASVS Level:** 1
**Result:** SECURED

All ten threats in the Phase 7 threat register are accounted for. Nine mitigate threats have
confirmed code evidence. One accept threat (T-07-08) is documented below. T-07-10 is recorded
as human-verified per the 07-04 plan checkpoint gate.

---

## Threat Verification

| Threat ID | Category | Disposition | Status | Evidence |
|-----------|----------|-------------|--------|----------|
| T-07-01 | T (Tampering) | mitigate | CLOSED | migrations.py:129 — `data.setdefault("codex_state", {})` in `_migrate_6_to_7`; existing values never overwritten. `schema_version` stamped to 7 at line 130. Migration registered at key `6` in the dispatch dict (line 36). |
| T-07-02 | I (Info Disclosure) | mitigate | CLOSED | party.py renders name via `display_name()` (line 111), level (line 116), HP (line 122), status (line 125). No `capture_rate` attribute accessed or printed anywhere in party.py. Whole-src scan confirms `capture_rate` absent from all render output paths. |
| T-07-03 | T (Tampering) | mitigate | CLOSED | party.py:181-182 — `if slot not in (1, 2, 3): console.print("Slot must be 1, 2, or 3.")`. Creature validated against `state.creature_collection` before assignment (lines 199-209); unknown templates rejected at line 206. Raw input never used directly as a state key. |
| T-07-04 | I (Info Disclosure) | mitigate | CLOSED | party.py:258-265 — interactive candidate list prints only name (via `display_name()`), level, and rarity. No `capture_rate` field accessed or rendered. Comment at line 258 explicitly documents the HARD RULE. Whole-src scan confirms absence from output paths. |
| T-07-05 | D (Denial of Service) | mitigate | CLOSED | party.py:271 — first `input()` prompt. party.py:282 — second `input()` prompt on invalid first input (re-prompt once). Lines 283-295 abort to "Swap cancelled." after second invalid input. No loop construct (while/for) wraps the prompt pair — no infinite loop possible. |
| T-07-06 | T (Tampering) | mitigate | CLOSED | collection.py:330 — `if new_name is None or not new_name.strip(): console.print("Name cannot be empty.")`. collection.py:333-334 — `if len(new_name) > 20: console.print("Name must be 20 characters or fewer.")`. Both guards fire before any state mutation. |
| T-07-07 | I (Info Disclosure) | mitigate | CLOSED | collection.py renders name via `_display_name()` (line 147), rarity (line 155), level (line 156), status (line 158). Codex renders `template.name` or "???" (lines 392, 397, 403). No `capture_rate` field accessed or printed anywhere in collection.py. Whole-src scan confirms absence from output paths. |
| T-07-08 | S (Spoofing) | accept | CLOSED | Accepted risk. Substring match in `_show_detail()` and `rename_cmd()` could match an unintended creature when multiple names share a substring. Risk is low: DevMon is a single-player game with no authentication or multi-user trust boundary; worst-case outcome is the player renames or views the wrong creature, which is immediately visible and correctable. The implementation shows multiple matches when ambiguity is detected (collection.py:217-222, 320-326) and asks the player to be more specific, further reducing practical impact. No escalation warranted. |
| T-07-09 | D (Denial of Service) | mitigate | CLOSED | collection.py:285 — first `input()` prompt in rename interactive mode. collection.py:295 — second `input()` prompt on invalid first selection ("Invalid selection. Which creature to rename [1-N]: "). collection.py:304 — `console.print("Rename cancelled.")` aborts after second failure. No loop construct wraps the pair — no infinite loop possible. |
| T-07-10 | I (Info Disclosure) | mitigate | CLOSED | Human-verified during Phase 7 Plan 04 checkpoint gate (07-04-PLAN.md, Task 2, checklist item 8: "Verify capture_rate is NEVER displayed anywhere"). Whole-src scan of `src/` directory confirms `capture_rate` appears only in: data JSON files (data layer), `models/creature.py` field definition, `engine/battle_engine.py` computation with explicit "NEVER shown to player" comment, and comment-only lines in party.py and collection.py. No render output path in party.py, collection.py, or render/party.py accesses or displays `capture_rate`. |

---

## Accepted Risks Log

| Threat ID | Category | Risk Description | Acceptance Rationale |
|-----------|----------|-----------------|----------------------|
| T-07-08 | S (Spoofing) | Substring match in collection detail and rename could resolve to an unintended creature when multiple creatures share name substrings. | Single-player game — no authentication, no trust boundary between users. Ambiguous matches are surfaced to the player with a list and "be more specific" prompt before any action is taken. Worst-case impact is a misdirected rename or detail view, both of which are immediately visible and trivially correctable. Accepted in 07-03-PLAN.md threat model. |

---

## Unregistered Flags

No unregistered threat flags. The `## Threat Flags` section in 07-02-SUMMARY.md states: "No new security-relevant surface introduced beyond what the plan's threat model covers." 07-03-SUMMARY.md states: "No new network endpoints, auth paths, or file access patterns introduced." No unregistered surface was flagged by any executor.

---

## Verification Methodology

Each `mitigate` threat was verified by grepping the source files cited in the mitigation plan for
the declared mitigation pattern. Results below map threat to file location:

| Threat ID | File Searched | Pattern Verified |
|-----------|---------------|-----------------|
| T-07-01 | src/devmon/persistence/migrations.py | `setdefault("codex_state"` at line 129; `schema_version = 7` at line 130; key `6: _migrate_6_to_7` at line 36 |
| T-07-02 | src/devmon/commands/party.py | No `capture_rate` in render paths; confirmed by whole-src scan |
| T-07-03 | src/devmon/commands/party.py | `slot not in (1, 2, 3)` at line 181; creature validated from collection lines 199-209 |
| T-07-04 | src/devmon/commands/party.py | No `capture_rate` in candidate list output (lines 259-266); confirmed by whole-src scan |
| T-07-05 | src/devmon/commands/party.py | Two-prompt pattern at lines 271 and 282; abort at lines 284-295; no loop |
| T-07-06 | src/devmon/commands/collection.py | Empty/whitespace check at line 330; length check at line 333 |
| T-07-07 | src/devmon/commands/collection.py | No `capture_rate` in table, detail, or codex render paths; confirmed by whole-src scan |
| T-07-08 | — | Accepted risk; documented above |
| T-07-09 | src/devmon/commands/collection.py | Two-prompt pattern at lines 285 and 295; abort at lines 287, 297, 304; no loop |
| T-07-10 | src/devmon/ (full scan) | `capture_rate` absent from all output paths in party.py, collection.py, render/party.py; human checkpoint gate passed in 07-04 |
