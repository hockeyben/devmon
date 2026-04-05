# Phase 8: Economy and Shop - Research

**Researched:** 2026-04-05
**Domain:** In-game economy, item catalog, shop CLI, inventory system, battle item integration
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Shop Presentation**
- D-01: Category tabs layout — grouped sections (Capsules, Potions, Boosters). Player browses one category at a time.
- D-02: Both interactive and CLI purchase modes. `devmon shop` opens interactive menu by default; `--buy` flag enables one-shot quick purchase for power users.
- D-03: Player's Bits balance shown prominently in shop header, updates after each purchase.
- D-04: Items show short mechanical effect descriptions only — no flavor text or lore.
- D-05: Purchase confirmation via styled Rich panel (green success styling) showing item purchased, quantity, and updated balance.
- D-06: Static catalog — no daily deals or rotating stock. Same items, same prices.

**Item Catalog & Balance**
- D-07: Capture capsule tiers carry forward from Phase 6 D-13: Basic (1x, cheap), Great (1.5x), Ultra (2x), Master (100%, not sold in shop — earned through gameplay only).
- D-08: XP boosters are timed: activates for 30 minutes of real time, 1.5x XP on all activities. Requires timer tracking in game state.
- D-09: Single revive item type: restores fainted creature to 50% HP.
- D-10: Affordable early pricing — basic items cost ~1-2 battles worth of currency. Rare items (Ultra Capsule, Full Potion) are the real currency sink.

**Currency Earning & Display**
- D-11: Currency is called "Bits" (developer-themed, as in binary bits).
- D-12: Battle rewards shown in a Rich summary panel after victory — XP earned + Bits earned in one clean display.
- D-13: Bits balance visible in `devmon status` profile panel alongside level, XP, and streak.

**Inventory Management**
- D-14: `devmon items` displays inventory as a Rich table grouped by category (Capsules, Potions, Boosters) — mirrors shop layout.
- D-15: Items usable in battle via the Items action menu — selecting Items opens a sub-menu of usable items (potions, revives, capsules). Uses a turn.
- D-16: No stack limits — unlimited item stacking.
- D-17: XP boosters usable from `devmon items use xp-booster` outside battle, as well as from the battle Items menu.

**Capsule Selection in Battle**
- D-18: Capture action opens a sub-menu showing owned capsule types with quantities (e.g., "Basic Capsule x5"). Player picks which tier to throw.

**Item Data Storage**
- D-19: Items defined in JSON data files under `src/devmon/data/items/`, loaded like creature data. User-tweakable, consistent with existing creature data pattern.

**Starter Items**
- D-20: New players receive a small starter kit: 5 Basic Capsules + 3 Small Potions. Enough to try systems without shopping first.

**Insufficient Funds**
- D-21: Unaffordable items grayed out in shop listing. Short error message if player attempts purchase anyway.

### Claude's Discretion
- Potion tier count and exact HP restoration percentages
- Exact pricing for all items (balanced against existing battle/capture reward formulas)
- XP booster timer persistence mechanism in game state
- Item sub-menu rendering in battle (Rich prompt style)
- Schema version bump strategy for inventory fields in GameState
- Whether starter kit is granted on first `devmon shop` visit or on new game creation

### Deferred Ideas (OUT OF SCOPE)
- Daily deals / rotating stock — could be a future polish feature
- Item flavor text / lore descriptions — could add personality later
- Selling items back to shop — not in scope for v1
- Item drops from wild encounters (random loot) — could be Phase 9 or later
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| ECON-01 | Player earns currency from winning battles and completing quests | `compute_battle_rewards()` already returns `currency`; wired into `battle.py` — just needs the shop to spend it on |
| ECON-02 | Player can buy capture items, healing items, and buffs from a shop via `devmon shop` | New `commands/shop.py` + `render/shop.py` following existing command/render split pattern |
| ECON-03 | Items include: basic/enhanced/ultra capsules, healing potions, revive items, XP boosters | `ItemCatalog` model loaded from JSON at `data/items/`; `CAPTURE_ITEM_MULTIPLIERS` already in `battle_engine.py` |
| ECON-04 | Item inventory viewable via `devmon items` | New `commands/items.py` + `render/shop.py::render_items_inventory()` |
| CLI-05 | `devmon shop` — browse and buy items | New Typer subapp registered in `main.py` |
| CLI-06 | `devmon items` — view inventory | New Typer subapp registered in `main.py` |
</phase_requirements>

---

## Summary

Phase 8 builds the economy layer on top of a battle system that already computes and awards currency (`PlayerProfile.currency` exists, `compute_battle_rewards()` already returns `currency` dict). The core work is: (1) storing item inventory in `GameState`, (2) loading item definitions from JSON data files, (3) building `devmon shop` and `devmon items` commands, (4) wiring items into the battle loop (capsule sub-menu for capture, item sub-menu for potions/revives), and (5) applying the XP booster multiplier to `progression.py`.

The codebase already has every architectural pattern this phase needs: the creature_loader JSON pattern for item definitions, the Pydantic v2 `model_validate()` approach for data integrity, schema migrations via `_migrate_N_to_N1()` in `migrations.py`, and Rich Panel/Text rendering patterns established across `render/battle.py` and `commands/status.py`. No new dependencies are required.

The highest-complexity sub-problems are: (a) the XP booster timer — it must check real-time elapsed minutes across sessions using a `float` Unix timestamp stored in `GameState`; (b) the capsule sub-menu in the battle loop — it must exit `Rich Live` before the interactive sub-prompt (same pattern already used for the switch sub-menu); and (c) the starter kit grant timing (new game vs. first shop visit).

**Primary recommendation:** Follow the creature_loader pattern for items, add a single `inventory: dict[str, int]` field to `GameState`, bump schema to version 8, and build shop/items as thin CLI commands that delegate to pure domain engine and render functions.

---

## Standard Stack

### Core (no new installs needed)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python | >=3.10 | Runtime | Already in use [VERIFIED: pyproject.toml] |
| Pydantic v2 | 2.12.5 | Item model validation, JSON round-trip | Already in use; `model_validate()` for item JSON loading [VERIFIED: existing codebase] |
| Rich | 14.3.3 | All terminal rendering for shop/items UI | Already in use; Panel, Text, Table, box.ROUNDED established patterns [VERIFIED: existing codebase] |
| Typer | 0.24.1 | `devmon shop` and `devmon items` CLI commands | Already in use; `app.callback(invoke_without_command=True)` pattern [VERIFIED: existing codebase] |

**No new packages required.** [VERIFIED: codebase audit — all needed capabilities present]

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `importlib.resources` | stdlib | Load bundled item JSON from package | Same as creature_loader.py pattern [VERIFIED: creature_loader.py] |
| `time.time()` | stdlib | XP booster expiry timestamp (Unix float) | Store activation time + 1800 seconds; compare at XP award time [VERIFIED: stdlib] |

---

## Architecture Patterns

### Recommended Project Structure — New Files

```
src/devmon/
├── data/items/              # NEW — item JSON catalog (D-19)
│   ├── __init__.py
│   ├── basic_capsule.json
│   ├── great_capsule.json
│   ├── ultra_capsule.json
│   ├── small_potion.json
│   ├── full_potion.json
│   ├── revive.json
│   └── xp_booster.json
├── models/
│   └── item.py              # NEW — ItemDefinition Pydantic model
├── engine/
│   └── item_engine.py       # NEW — pure item logic (use_item, apply_booster, etc.)
│   └── item_loader.py       # NEW — JSON loading pattern (mirrors creature_loader.py)
├── commands/
│   ├── shop.py              # NEW — devmon shop command
│   └── items.py             # NEW — devmon items command
└── render/
    └── shop.py              # NEW — render_shop_header, render_shop_category, etc.
```

**Modified files:**
- `src/devmon/models/state.py` — add `inventory: dict[str, int]` and `xp_booster_active_until: float` fields
- `src/devmon/persistence/migrations.py` — add `_migrate_7_to_8()`; bump `CURRENT_VERSION = 8`
- `src/devmon/engine/progression.py` — apply booster multiplier in `compute_event_xp()` or `process_events()`
- `src/devmon/commands/battle.py` — enable [5] Items sub-menu; upgrade [3] Capture to capsule sub-menu
- `src/devmon/render/battle.py` — update `render_action_menu()` to remove `(coming soon)`; update victory/capture screens to say "Bits" (capital B)
- `src/devmon/commands/status.py` — update currency display from `G` to `Bits`; add XP booster active row
- `src/devmon/main.py` — register `shop_cmd.app` and `items_cmd.app`

### Pattern 1: Item Definition (ItemDefinition Pydantic Model)

**What:** Static data container loaded from JSON, validated at load time. Pure data — no logic methods.
**When to use:** All item catalog entries.

```python
# src/devmon/models/item.py
# Source: mirrors devmon.models.creature.CreatureTemplate pattern [VERIFIED: creature.py]
from __future__ import annotations
from typing import Literal, Optional
from pydantic import BaseModel, Field

ItemCategory = Literal["capsule", "potion", "booster"]

class ItemDefinition(BaseModel):
    """Static item catalog entry — loaded from data/items/*.json.

    Pure data container. No imports from commands/, render/, or engine/.
    """
    id: str              # snake_case, matches filename stem: "basic_capsule"
    name: str            # Display name: "Basic Capsule"
    category: ItemCategory
    price: int = Field(ge=0)          # 0 = not sold in shop (Master Capsule)
    sold_in_shop: bool = True
    effect_description: str           # Short mechanical description (D-04)
    # Capsule-specific
    capture_multiplier: float = 1.0
    # Potion-specific
    hp_restore_percent: float = 0.0   # 0.25 = 25% HP restore
    restores_fainted: bool = False    # True for Revive
    # Booster-specific
    xp_multiplier: float = 1.0
    duration_minutes: int = 0         # 30 for XP booster
```

### Pattern 2: Item Loader (mirrors creature_loader.py)

**What:** Load all item JSON files from package data, validate with Pydantic, return dict by id.
**When to use:** Called from commands/shop.py and commands/items.py at command time (never at import time).

```python
# src/devmon/engine/item_loader.py
# Source: mirrors creature_loader.py pattern exactly [VERIFIED: creature_loader.py]
from importlib.resources import files
from devmon.models.item import ItemDefinition

def load_all_items() -> dict[str, ItemDefinition]:
    """Load and validate all item definitions from bundled data/items/*.json."""
    registry: dict[str, ItemDefinition] = {}
    pkg = files("devmon.data.items")
    for entry in pkg.iterdir():
        if entry.is_file() and entry.name.endswith(".json"):
            data = json.loads(entry.read_text(encoding="utf-8"))
            item = ItemDefinition.model_validate(data)
            registry[item.id] = item
    return registry
```

### Pattern 3: GameState Inventory Field

**What:** Simple `dict[str, int]` mapping item_id to quantity. No custom model needed — dict is JSON-serializable by Pydantic v2 natively.
**When to use:** All inventory operations — check, add, subtract.

```python
# src/devmon/models/state.py additions [VERIFIED: state.py current structure]
# Add to GameState:
inventory: dict[str, int] = Field(default_factory=dict)
"""Item inventory: {item_id: quantity}. Absence means 0 owned. No stack limit (D-16)."""

xp_booster_active_until: float = 0.0
"""Unix timestamp when active XP booster expires. 0.0 = no active booster. (D-08)"""
```

Migration:
```python
# src/devmon/persistence/migrations.py
# Source: established migration pattern [VERIFIED: migrations.py]
CURRENT_VERSION = 8  # bump from 7

def _migrate_7_to_8(data: dict) -> dict:
    """Version 7 -> 8: Phase 8 adds inventory and XP booster timer to GameState."""
    data.setdefault("inventory", {})
    data.setdefault("xp_booster_active_until", 0.0)
    data["schema_version"] = 8
    return data
```

### Pattern 4: XP Booster Timer Logic

**What:** Store activation expiry as Unix float (`time.time() + 1800`). At XP award time, compare `time.time()` against stored value.
**When to use:** In `progression.py:process_events()` and anywhere XP is awarded (battle rewards, capture rewards).

```python
# src/devmon/engine/item_engine.py (pure domain logic)
import time

def is_booster_active(state) -> bool:
    """Return True if XP booster is currently active."""
    return time.time() < state.xp_booster_active_until

def activate_booster(state, duration_minutes: int = 30) -> None:
    """Activate XP booster. Extends existing duration if already active."""
    remaining = max(0.0, state.xp_booster_active_until - time.time())
    state.xp_booster_active_until = time.time() + remaining + (duration_minutes * 60)

def booster_remaining_minutes(state) -> int:
    """Return integer minutes remaining on active booster (0 if inactive)."""
    remaining = state.xp_booster_active_until - time.time()
    return max(0, int(remaining / 60))
```

Integration in `progression.py`:
```python
# In process_events(), after computing final_xp:
from devmon.engine.item_engine import is_booster_active
if is_booster_active(state):
    final_xp = int(final_xp * 1.5)  # D-08: 1.5x XP multiplier
```

Integration in `battle.py` (battle/capture rewards):
```python
# After computing rewards in battle loop victory branch:
from devmon.engine.item_engine import is_booster_active
if is_booster_active(state):
    rewards["player_xp"] = int(rewards["player_xp"] * 1.5)
```

### Pattern 5: Shop Command Structure

**What:** Typer command with `invoke_without_command=True` callback for interactive mode, plus `--buy` option for one-shot purchase (D-02).
**When to use:** `commands/shop.py`.

```python
# src/devmon/commands/shop.py
# Source: mirrors battle.py/status.py Typer structure [VERIFIED: existing commands]
import typer
app = typer.Typer()

@app.callback(invoke_without_command=True)
def shop_cmd(
    buy: str = typer.Option(None, "--buy", help="Item ID to purchase"),
    qty: int = typer.Option(1, "--qty", help="Quantity to purchase"),
) -> None:
    """Browse and buy items from the shop."""
    if buy:
        _quick_purchase(buy, qty)
    else:
        _interactive_shop()
```

### Pattern 6: Starter Kit Grant

**Claude's discretion per CONTEXT.md.** Recommendation: grant on `new_game()` creation in `GameState.new_game()`, not on first shop visit. Reason: simpler, avoids need to track "has visited shop" flag, ensures items are always available from first battle. The `new_game()` method is the established place for initial state setup.

```python
# src/devmon/models/state.py — update new_game()
@classmethod
def new_game(cls, player_name: str) -> "GameState":
    state = cls(player=PlayerProfile(name=player_name))
    # D-20: starter kit for new players
    state.inventory["basic_capsule"] = 5
    state.inventory["small_potion"] = 3
    return state
```

### Pattern 7: Battle Items Sub-Menu (Live Context Exit)

**What:** Exit `Rich Live` before the items/capture sub-menu prompt — same pattern used for switch sub-menu in Phase 6.
**When to use:** Choice "5" (Items) and choice "3" (Capture) in battle loop.

```python
# Source: established Phase 6 pattern in commands/battle.py [VERIFIED: battle.py lines 631-644]
# Choice [5] Items:
elif choice == "5":
    live.stop()
    # render items sub-menu inline
    # get player input
    # apply item effect
    # Re-open Live for continued battle
    with Live(auto_refresh=False, console=console) as live:
        continue
```

The capture sub-menu replaces the current hardcoded `item_multiplier=1.0` call — it collects capsule choice first, then calls `compute_capture_chance()` with the selected multiplier.

### Pattern 8: Item Use in Battle (Potions/Revives)

**What:** Pure domain function in `item_engine.py` that takes `OwnedCreature`, `CreatureTemplate`, and `ItemDefinition`, applies the effect, and returns a result string. No I/O.
**When to use:** Called from `commands/battle.py` items sub-menu handler.

```python
# src/devmon/engine/item_engine.py
def use_potion_on_creature(
    owned: "OwnedCreature",
    template: "CreatureTemplate",
    item: ItemDefinition,
    max_hp: int,
) -> str:
    """Apply potion effect. Returns narration string. Raises ValueError if invalid."""
    if item.restores_fainted:
        if not owned.is_fainted:
            raise ValueError("Revive can only be used on a fainted creature.")
        owned.is_fainted = False
        owned.current_hp = max(1, int(max_hp * 0.5))
        return f"{template.name} is back in the fight!"  # D per UI-SPEC copywriting
    else:
        if owned.is_fainted:
            raise ValueError("Cannot heal a fainted creature.")
        heal = max(1, int(max_hp * item.hp_restore_percent))
        if owned.current_hp is None:
            owned.current_hp = max_hp
        owned.current_hp = min(max_hp, owned.current_hp + heal)
        return f"{item.name} used on {template.name}."
```

### Anti-Patterns to Avoid

- **Embedding item quantities in ItemDefinition:** ItemDefinition is a static catalog entry (like CreatureTemplate). Inventory state lives in `GameState.inventory`. Never mix catalog and runtime state.
- **Calling `load_all_items()` at module import time:** Same pitfall as creature_loader — call at use time, not import time.
- **Importing engine modules from models:** `item_engine.py` must only import from `models/`. The six-layer architecture rule applies: engine/ imports models/ only, commands/ imports engine/ and render/, render/ imports models/ only.
- **Storing booster expiry as datetime object in GameState:** Pydantic serializes `float` to JSON natively; `datetime` requires a custom serializer. Use `float` (Unix timestamp) for `xp_booster_active_until`.
- **Hardcoding item prices or catalog in Python:** D-19 mandates JSON data files. Prices must be in JSON for user-tweakability.
- **Showing capture percentage to player:** Project memory note enforces this. `run_capture_animation()` and any new capture sub-menu must NEVER display the capture probability.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| JSON loading with override support | Custom glob + file merge logic | Mirror `creature_loader.py` exactly | Pattern already battle-tested, includes DEVMON_HOME override support |
| Item model validation | Manual dict key checks | `ItemDefinition.model_validate()` | Type errors surface at startup, not mid-battle; Pydantic v2 covers edge cases |
| Timer for XP booster | Custom timer class | `time.time()` float stored in GameState | Zero dependencies, JSON-serializable, already used in encounter_engine.py |
| Rich Table for inventory | Custom text formatting | `Rich.Table` with `rich.table.Table` | Handles terminal width, alignment, borders automatically |
| Schema migration | Modify all existing saves on disk | `_migrate_7_to_8()` with `setdefault()` | Established safe migration pattern — do not skip |

**Key insight:** Every structural problem in Phase 8 has a solved pattern already in the codebase. The work is replication and integration, not invention.

---

## Item Catalog — Recommended Pricing and Effects

Per Claude's discretion (CONTEXT.md). Battle at level 1 wild creature awards ~13 Bits (`compute_battle_rewards(1, "normal")` = `int((10 + 1*3) * 1.0)` = 13). Level 5 normal = 25 Bits.

| Item ID | Name | Category | Price | Effect | Sold |
|---------|------|----------|-------|--------|------|
| `basic_capsule` | Basic Capsule | capsule | 5 | 1.0x capture | yes |
| `great_capsule` | Great Capsule | capsule | 12 | 1.5x capture | yes |
| `ultra_capsule` | Ultra Capsule | capsule | 30 | 2.0x capture | yes |
| `master_capsule` | Master Capsule | capsule | 0 | 100x capture | no (earn only) |
| `small_potion` | Small Potion | potion | 8 | +25% HP restore | yes |
| `full_potion` | Full Potion | potion | 20 | +100% HP restore | yes |
| `revive` | Revive | potion | 15 | Restore fainted to 50% HP | yes |
| `xp_booster` | XP Booster | booster | 25 | 1.5x XP, 30 min | yes |

**Rationale:** Basic Capsule (5 Bits) costs less than one level-1 battle (13 Bits). Ultra Capsule (30 Bits) and Full Potion (20 Bits) require 2-4 battles — meaningful sinks without grinding. Consistent with D-10. [ASSUMED — pricing not validated against live player data, but computed from verified `compute_battle_rewards()` formula]

---

## Common Pitfalls

### Pitfall 1: Rich Live Context Active During Sub-Menu Input
**What goes wrong:** `input()` call while `Rich Live` is active causes terminal corruption or input swallowing.
**Why it happens:** `Rich Live` owns stdout during its context; `input()` goes to stdin but display refresh interferes.
**How to avoid:** Call `live.stop()` before any `input()` inside the battle loop. Reopen with `with Live(...) as live: continue` afterward. [VERIFIED: Phase 6 pattern in battle.py — switch sub-menu uses exact same pattern at lines 631-644, 701-702]
**Warning signs:** Terminal freezes after item use; output appears on wrong line.

### Pitfall 2: `new_game()` Starter Kit Inventory Not Migrated
**What goes wrong:** Existing players (schema < 8) who upgrade do NOT get starter kit because `new_game()` is only called for fresh installs.
**Why it happens:** `_migrate_7_to_8()` adds `inventory: {}` — existing players get empty inventory.
**How to avoid:** The migration intentionally leaves inventory empty for existing players. Starter kit (D-20) is only for NEW players via `new_game()`. Do not add starter kit in migration — that would give existing players free items on every upgrade. Document this clearly in migration comment.
**Warning signs:** None — this is expected behavior.

### Pitfall 3: Import Cycle via item_engine → battle_engine
**What goes wrong:** `item_engine.py` importing from `battle_engine.py` creates a cycle if `battle_engine.py` ever needs to import back.
**Why it happens:** Both are in `engine/`; shared capture multiplier data is tempting to centralize.
**How to avoid:** Keep `CAPTURE_ITEM_MULTIPLIERS` in `battle_engine.py` where it already lives. `item_engine.py` references `ItemDefinition.capture_multiplier` directly — it does NOT import from `battle_engine.py`. `commands/battle.py` wires them together at the CLI layer.
**Warning signs:** `ImportError: cannot import name` at startup.

### Pitfall 4: XP Booster Double-Application
**What goes wrong:** XP booster multiplier applied in both `process_events()` (shell activity XP) and in battle reward code, but battle rewards use `compute_battle_rewards()` which doesn't know about the booster.
**Why it happens:** XP award happens in two separate code paths; easy to miss one.
**How to avoid:** Apply booster check in `process_events()` for shell-event XP AND in battle victory/capture branches in `commands/battle.py`. Both paths check `is_booster_active(state)` independently. The booster should apply everywhere XP is awarded. [ASSUMED — no existing booster logic to verify against; this is greenfield]
**Warning signs:** Booster activates but XP gain looks the same in battle.

### Pitfall 5: `inventory.get(item_id, 0) -= 1` Key Error
**What goes wrong:** Decrementing inventory for an item with qty=0 or absent from dict.
**Why it happens:** `dict[str, int].get()` returns a value but `dict[key] -= 1` requires the key to exist.
**How to avoid:** Always check `state.inventory.get(item_id, 0) >= qty_needed` before deducting. Use a helper:
```python
def consume_item(inventory: dict[str, int], item_id: str, qty: int = 1) -> bool:
    current = inventory.get(item_id, 0)
    if current < qty:
        return False
    inventory[item_id] = current - qty
    return True
```
**Warning signs:** `KeyError` during item use, or negative item counts in save file.

### Pitfall 6: `__init__.py` Missing from `data/items/`
**What goes wrong:** `importlib.resources.files("devmon.data.items")` fails with `ModuleNotFoundError` or returns empty.
**Why it happens:** Python package resources require `__init__.py` and `pyproject.toml` inclusion.
**How to avoid:** Add `src/devmon/data/items/__init__.py` (empty file). Verify `pyproject.toml` includes `"devmon.data.items"` in package data if not using wildcard. Check `devmon.data.creatures` for the existing pattern. [VERIFIED: creature_loader.py uses same approach — requires __init__.py to be present]
**Warning signs:** `ModuleNotFoundError: No module named 'devmon.data.items'` when loading items.

### Pitfall 7: Schema CURRENT_VERSION Mismatch
**What goes wrong:** Test suite fails with `AssertionError: schema_version mismatch` — a project-enforced invariant.
**Why it happens:** `CURRENT_VERSION` in `migrations.py` must always equal `GameState.schema_version` default. If one is updated without the other, the test that enforces this (T-01-xx) fails.
**How to avoid:** When adding `_migrate_7_to_8()`, update BOTH `CURRENT_VERSION = 8` in `migrations.py` AND `schema_version: int = Field(default=8, ...)` in `state.py`. Never update one without the other. [VERIFIED: STATE.md decision log — "CURRENT_VERSION in migrations.py must always equal GameState.schema_version default — enforced by test suite"]
**Warning signs:** `FAILED tests/test_persistence.py::test_schema_version_matches_current`.

---

## Code Examples

### Loading Items (from official creature_loader pattern)
```python
# Source: mirrors creature_loader.py exactly [VERIFIED: creature_loader.py]
# src/devmon/engine/item_loader.py
import json
import os
import pathlib
from importlib.resources import files
from devmon.models.item import ItemDefinition

def load_all_items() -> dict[str, ItemDefinition]:
    registry: dict[str, ItemDefinition] = {}
    errors: list[str] = []

    bundled: dict[str, str] = {}
    pkg = files("devmon.data.items")
    for entry in pkg.iterdir():
        if entry.is_file() and entry.name.endswith(".json"):
            bundled[entry.name] = entry.read_text(encoding="utf-8")

    devmon_home = os.environ.get("DEVMON_HOME")
    if devmon_home:
        override_dir = pathlib.Path(devmon_home) / "items"
        if override_dir.exists():
            for json_file in override_dir.glob("*.json"):
                bundled[json_file.name] = json_file.read_text(encoding="utf-8")

    for filename, text in bundled.items():
        try:
            data = json.loads(text)
            item = ItemDefinition.model_validate(data)
            registry[item.id] = item
        except Exception as e:
            errors.append(f"{filename}: {e}")

    if errors:
        raise ValueError("Item data validation failed:\n" + "\n".join(errors))
    return registry
```

### Shop Render (from UI-SPEC Surface 1)
```python
# Source: UI-SPEC.md Surface 1, 2 [VERIFIED: 08-UI-SPEC.md]
# src/devmon/render/shop.py
from rich import box
from rich.panel import Panel
from rich.text import Text

def render_shop_header(bits: int, theme: dict) -> Panel:
    body = Text()
    body.append("Bits: ", style=theme["stat_key"])
    body.append(str(bits), style="bold white")
    return Panel(body, title="[bold]Shop[/bold]", border_style=theme["border"], expand=True)

def render_purchase_confirmation(item_name: str, qty: int, cost: int, balance: int) -> Panel:
    body = Text()
    body.append(f"{item_name} x{qty}\n", style="white")
    body.append("Cost: ", style="dim white")
    body.append(f"-{cost} Bits\n", style="red")
    body.append("Balance: ", style="dim white")
    body.append(f"{balance} Bits", style="bold white")
    return Panel(
        body,
        title="[bold green]Purchased[/bold green]",
        border_style="green",
        box=box.ROUNDED,
        expand=False,
    )
```

### Inventory Field JSON (sample item file)
```json
{
  "id": "basic_capsule",
  "name": "Basic Capsule",
  "category": "capsule",
  "price": 5,
  "sold_in_shop": true,
  "effect_description": "1.0x capture multiplier",
  "capture_multiplier": 1.0,
  "hp_restore_percent": 0.0,
  "restores_fainted": false,
  "xp_multiplier": 1.0,
  "duration_minutes": 0
}
```

### Battle Capture Sub-Menu Pattern
```python
# Source: adapted from switch creature pattern [VERIFIED: battle.py lines 631-644]
# In choice == "3" branch:
elif choice == "3":
    live.stop()
    # Show capsule sub-menu
    capsule_ids = ["basic_capsule", "great_capsule", "ultra_capsule", "master_capsule"]
    owned_capsules = [
        (cid, state.inventory.get(cid, 0))
        for cid in capsule_ids
        if state.inventory.get(cid, 0) > 0
    ]
    if not owned_capsules:
        console.print("  You have no capsules. Buy some at the shop.", style="dim white")
        with Live(auto_refresh=False, console=console) as live:
            continue

    console.print("  Throw which capsule?\n")
    for i, (cid, qty) in enumerate(owned_capsules, 1):
        item = items[cid]
        console.print(f"  [{i}] {item.name}    x{qty}")
    console.print("  [b] Back\n")

    capsule_choice = input("  Choose: ").strip()
    if capsule_choice == "b":
        with Live(auto_refresh=False, console=console) as live:
            continue
    # ... resolve multiplier and proceed to existing capture logic
```

---

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|------------------|--------|
| `{currency} G` in status panel | `{currency} Bits` (D-11) | Text change only in `commands/status.py` |
| Hardcoded `item_multiplier=1.0` in capture | Sub-menu-selected capsule from inventory | Enables CAPT-04 to actually function with item tiers |
| `"Items (coming soon)"` in action menu | Active Items sub-menu | Enables BATL-02 Items action |

**Deprecated/outdated:**
- `"basic"`, `"great"`, `"ultra"` string keys in `CAPTURE_ITEM_MULTIPLIERS` — these internal keys are fine, but the user-facing capsule IDs in inventory are `"basic_capsule"`, `"great_capsule"`, `"ultra_capsule"`. The battle command must translate inventory ID to engine multiplier key at use time.

---

## Integration Points Summary

| File | Change Type | Scope |
|------|-------------|-------|
| `models/state.py` | Field additions | `inventory: dict[str, int]`, `xp_booster_active_until: float` |
| `models/state.py` | `new_game()` update | Starter kit initialization (D-20) |
| `persistence/migrations.py` | New migration | `_migrate_7_to_8()`, `CURRENT_VERSION = 8` |
| `engine/progression.py` | XP booster hook | Check `is_booster_active()` in `process_events()` |
| `commands/battle.py` | Choice [3] upgrade | Capsule sub-menu replaces hardcoded basic multiplier |
| `commands/battle.py` | Choice [5] activate | Items sub-menu (potions, revives) |
| `render/battle.py` | Minor text updates | `render_action_menu()` — remove `(coming soon)` from Items; victory/capture screens — capitalize "Bits" |
| `commands/status.py` | Label update | `{currency} G` → `{currency} Bits`; add XP booster active row |
| `main.py` | Command registration | `add_typer(shop_cmd.app, name="shop")`, `add_typer(items_cmd.app, name="items")` |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Recommended pricing (5/12/30 Bits for capsule tiers; 8/20/15 Bits for potions; 25 Bits for booster) | Item Catalog | Prices could feel too cheap or too expensive — adjust via JSON without code changes |
| A2 | Starter kit granted in `new_game()` rather than first shop visit | Architecture Patterns Pattern 6 | If granted on first shop visit: need a `has_visited_shop` flag in GameState — extra field, more migration; recommend new_game() for simplicity |
| A3 | XP booster applies to shell-event XP (in `process_events()`) AND battle/capture rewards independently | Common Pitfalls Pitfall 4 | If booster should NOT apply to battle XP: remove from battle branch; design intent is "all activities" per D-08 |
| A4 | `data/items/__init__.py` follows same importlib.resources pattern as `data/creatures/` | Architecture Patterns | If Python packaging is configured differently: would need to verify `pyproject.toml` package data includes items |

**No [ASSUMED] claims are blocking.** All are documented here; planner can lock them or flag for confirm.

---

## Open Questions

1. **Starter kit timing (Claude's discretion)**
   - What we know: D-20 says new players receive starter kit. CONTEXT.md leaves timing to Claude's discretion.
   - What's unclear: `new_game()` vs. first shop visit.
   - Recommendation: `new_game()` — simpler, no extra state flag needed.

2. **Potion tier count (Claude's discretion)**
   - What we know: D-09 specifies one revive type. ECON-03 mentions "healing potions" (plural tier implied).
   - What's unclear: Two tiers (small + full) vs. three.
   - Recommendation: Two tiers (Small Potion 25% HP at 8 Bits, Full Potion 100% HP at 20 Bits) — keeps catalog focused. UI-SPEC confirms this choice.

3. **XP booster timer behavior — extension vs. stack**
   - What we know: D-08 says "activates for 30 minutes of real time."
   - What's unclear: Using a second booster while one is active — reset timer or add 30 min?
   - Recommendation: Extend (add 30 min to remaining time) — player-friendly, simple to implement.

---

## Environment Availability

Step 2.6: SKIPPED (no external dependencies — all changes are code and JSON data files within the existing Python project).

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest >= 8.0 |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` section |
| Quick run command | `uv run pytest tests/test_economy.py -x` |
| Full suite command | `uv run pytest tests/ -x` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ECON-01 | Battle win awards Bits that persist in save | unit | `pytest tests/test_economy.py::test_battle_awards_bits -x` | ❌ Wave 0 |
| ECON-01 | Currency persists across save/load cycle | unit | `pytest tests/test_economy.py::test_bits_persist_save_load -x` | ❌ Wave 0 |
| ECON-02 | `devmon shop` renders and handles purchase | unit | `pytest tests/test_economy.py::test_shop_purchase -x` | ❌ Wave 0 |
| ECON-02 | Insufficient funds shows error, no deduction | unit | `pytest tests/test_economy.py::test_shop_insufficient_funds -x` | ❌ Wave 0 |
| ECON-03 | All item types load from JSON without errors | unit | `pytest tests/test_economy.py::test_item_loader -x` | ❌ Wave 0 |
| ECON-03 | Enhanced/ultra capsule produces higher capture chance | unit | `pytest tests/test_economy.py::test_capsule_multiplier_effectiveness -x` | ❌ Wave 0 |
| ECON-03 | Revive restores fainted creature to 50% HP | unit | `pytest tests/test_economy.py::test_revive_restores_fainted -x` | ❌ Wave 0 |
| ECON-04 | `devmon items` renders inventory | unit | `pytest tests/test_economy.py::test_items_command -x` | ❌ Wave 0 |
| CLI-05 | `devmon shop --buy basic_capsule` quick purchase | unit | `pytest tests/test_economy.py::test_shop_quick_buy -x` | ❌ Wave 0 |
| CLI-06 | `devmon items` exits 0 | unit | `pytest tests/test_economy.py::test_items_exits_ok -x` | ❌ Wave 0 |
| (schema) | schema_version == 8, migration 7→8 works | unit | `pytest tests/test_persistence.py -x` | ✅ (extend existing) |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_economy.py -x`
- **Per wave merge:** `uv run pytest tests/ -x`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_economy.py` — new file covering all ECON-* and CLI-05/06 requirements
- [ ] `src/devmon/data/items/__init__.py` — package marker for importlib.resources
- [ ] `src/devmon/data/items/*.json` — 8 item definition files

---

## Security Domain

> This phase adds no authentication, session management, external network calls, or user-supplied data beyond existing save file. No new ASVS categories apply beyond those already addressed in the project.

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V5 Input Validation | yes | Pydantic `ItemDefinition.model_validate()` at load time; `int()` conversion on shop choice input |
| V2 Authentication | no | No auth added |
| V3 Session Management | no | No session changes |
| V4 Access Control | no | No permissions model |
| V6 Cryptography | no | No crypto changes |

**Threat pattern:** Malformed item JSON in DEVMON_HOME override could crash startup. Mitigation: item_loader collects all errors and raises a single `ValueError` listing all failures — same defensive pattern as creature_loader.

---

## Sources

### Primary (HIGH confidence)
- `src/devmon/engine/creature_loader.py` — item_loader.py pattern to replicate exactly
- `src/devmon/persistence/migrations.py` — migration pattern, CURRENT_VERSION enforcement rule
- `src/devmon/models/state.py` — GameState field additions; `new_game()` for starter kit
- `src/devmon/engine/battle_engine.py` — `CAPTURE_ITEM_MULTIPLIERS`, `compute_battle_rewards()`, `compute_capture_chance()` signatures
- `src/devmon/commands/battle.py` — Live context exit pattern for sub-menus (lines 631-644)
- `src/devmon/render/battle.py` — `render_action_menu()` update target; render patterns
- `.planning/phases/08-economy-and-shop/08-UI-SPEC.md` — complete Surface inventory, copywriting contract, item catalog with prices

### Secondary (MEDIUM confidence)
- `.planning/phases/08-economy-and-shop/08-CONTEXT.md` — all locked decisions D-01 through D-21
- `src/devmon/commands/status.py` — `render_status()` integration point for Bits label and XP booster row
- `src/devmon/engine/progression.py` — `process_events()` XP booster hook location

### Tertiary (LOW confidence)
- A1-A4 in Assumptions Log — pricing and timing recommendations based on reading game design intent from context, not validated with live player data

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all dependencies already in the project; no new packages
- Architecture: HIGH — every pattern has a direct verified precedent in the codebase
- Pitfalls: HIGH — most pitfalls are concrete, discovered from reading existing code (Live context, schema version invariant, import cycle risk)
- Item catalog/pricing: MEDIUM — pricing computed from verified battle reward formula but not playtested

**Research date:** 2026-04-05
**Valid until:** 2026-05-05 (stable stack, no fast-moving dependencies)
