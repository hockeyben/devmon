---
phase: 08-economy-and-shop
plan: 03
subsystem: economy
tags: [shop, items, cli, render, rich, typer]
dependency_graph:
  requires: [08-01, 08-02]
  provides: [shop_command, items_command, shop_render]
  affects: [main_app, battle_capture]
tech_stack:
  added: []
  patterns: [typer-callback-invoke-without-command, rich-panel-expand-true, typer-testing-cli-runner]
key_files:
  created:
    - src/devmon/render/shop.py
    - src/devmon/commands/shop.py
    - src/devmon/commands/items.py
  modified:
    - src/devmon/main.py
    - tests/test_economy.py
decisions:
  - "render/shop.py is pure — no engine/persistence imports; only models/ and render/themes"
  - "shop command wired into main.py before Task 1 tests could pass — deviation from task ordering"
  - "CliRunner(mix_stderr=False) not supported by this Click version — dropped that kwarg (Rule 1 bug fix)"
  - "T-08-06 mitigated: item_id validated via load_all_items() + sold_in_shop check before purchase"
  - "T-08-08 mitigated: qty >= 1 validated before any purchase deduction"
metrics:
  duration_minutes: 22
  completed_date: "2026-04-06"
  tasks_completed: 2
  files_created: 3
  files_modified: 2
---

# Phase 8 Plan 03: Shop Command, Items Command, and Render Module Summary

`devmon shop` and `devmon items` CLI commands built with full Rich render functions, interactive and quick-buy purchase modes, XP booster activation, and all 5 xfail stubs replaced with passing tests.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Shop render module and shop command | 7bac6f6 | `render/shop.py`, `commands/shop.py`, `tests/test_economy.py` |
| 2 | Items command and main.py wiring | 0c9a01b | `commands/items.py`, `main.py`, `tests/test_economy.py` |

## What Was Built

### render/shop.py (pure render module)

| Function | Output | Notes |
|----------|--------|-------|
| `render_shop_header(bits, theme)` | Panel | Bits balance, expand=True, theme border |
| `render_shop_category(name, items, player_bits, theme)` | Panel | Affordability graying (D-21), earn-only items |
| `render_purchase_confirmation(item_name, qty, cost, balance)` | Panel | Green border, expand=False |
| `render_items_inventory(inventory, items_catalog, booster_remaining, theme)` | Panel | Grouped by category, XP booster active indicator |
| `render_battle_items_menu(usable_items)` | None (prints inline) | Action-menu style, no panel |
| `render_capture_submenu(capsules_owned)` | None (prints inline) | Empty state message if no capsules |

### commands/shop.py

- Interactive mode: numbered catalog loop, `q` to quit, re-displays after each purchase
- Quick mode: `--buy <item_id> [--qty N]` one-shot purchase
- Insufficient funds: `"Not enough Bits. You need {N}, you have {M}."` in bold red
- Confirmation: `render_purchase_confirmation` panel after successful purchase

### commands/items.py

- Default: renders full inventory via `render_items_inventory`
- `--use xp-booster`: consumes item, activates booster, prints `"XP Booster active! 1.5x XP for 30 minutes."` in bold magenta
- Potions/revives: prints battle-only error directing user to `devmon battle`
- Hyphenated input (`xp-booster`) mapped to underscore ID (`xp_booster`)

### main.py

- Added `from devmon.commands import shop as shop_cmd`
- Added `from devmon.commands import items as items_cmd`
- Added `app.add_typer(shop_cmd.app, name="shop")`
- Added `app.add_typer(items_cmd.app, name="items")`

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Registered shop/items in main.py during Task 1**
- **Found during:** Task 1 verification
- **Issue:** `test_shop_purchase` invokes `devmon_app` which requires `shop` to be registered. Without the registration, tests exit code 2 ("No such command 'shop'").
- **Fix:** Added both imports and `add_typer` registrations to `main.py` during Task 1 rather than waiting for Task 2.
- **Files modified:** `src/devmon/main.py`
- **Commit:** 0c9a01b (included in Task 2 commit)

**2. [Rule 1 - Bug] Removed `mix_stderr=False` from CliRunner**
- **Found during:** Task 1 test run
- **Issue:** `CliRunner.__init__()` in this version of Click/Typer does not accept `mix_stderr` keyword argument — raises `TypeError`.
- **Fix:** Changed `CliRunner(mix_stderr=False)` to `CliRunner()` in all 5 new tests.
- **Files modified:** `tests/test_economy.py`
- **Commit:** 7bac6f6

## Known Stubs

None — all render functions produce real output. Shop and items commands are fully wired and functional.

## Threat Flags

None — no new network endpoints, auth paths, or unexpected trust boundaries. Threat mitigations T-08-06 and T-08-08 implemented as planned.

## Self-Check: PASSED

Files verified:
- `src/devmon/render/shop.py` — FOUND
- `src/devmon/commands/shop.py` — FOUND
- `src/devmon/commands/items.py` — FOUND
- `src/devmon/main.py` — modified, FOUND

Commits verified:
- `7bac6f6` — FOUND (feat: shop render + shop command)
- `0c9a01b` — FOUND (feat: items command + main.py wiring)

Test results: 43 passed, 2 xfailed (intentional — separate plan scope) in test_economy.py
