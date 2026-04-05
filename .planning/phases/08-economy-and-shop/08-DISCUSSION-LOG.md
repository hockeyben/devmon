# Phase 8: Economy and Shop - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-05
**Phase:** 08-economy-and-shop
**Areas discussed:** Shop presentation, Item catalog & balance, Currency earning & display, Inventory management, Item data storage, Capsule selection in battle, Starter items, Insufficient funds UX

---

## Shop Presentation

### Shop Layout

| Option | Description | Selected |
|--------|-------------|----------|
| Category tabs | Grouped sections: Capsules, Potions, Boosters. Browse one category at a time. | ✓ |
| Single list | All items in one Rich table with category column. | |
| Grid cards | Rich panels in a grid, each showing item name, price, effect. | |

**User's choice:** Category tabs

### Purchase UX

| Option | Description | Selected |
|--------|-------------|----------|
| Interactive menu | Multi-step guided flow with Rich prompts. | |
| Command flags | One-shot CLI style with --buy flag. | |
| Both modes | Interactive by default, --buy flag for quick purchase. | ✓ |

**User's choice:** Both modes

### Balance Display

| Option | Description | Selected |
|--------|-------------|----------|
| Header balance | Currency shown at top of shop, always visible. | ✓ |
| Inline only | Currency shown next to each item contextually. | |
| You decide | Claude picks. | |

**User's choice:** Header balance

### Item Descriptions

| Option | Description | Selected |
|--------|-------------|----------|
| Short effect only | Just mechanical description. | ✓ |
| Effect + flavor | Mechanical effect plus fun lore line. | |
| You decide | Claude picks. | |

**User's choice:** Short effect only

### Purchase Confirmation

| Option | Description | Selected |
|--------|-------------|----------|
| Inline confirmation | Simple text message below shop table. | |
| Rich panel flash | Styled Rich panel with green success styling. | ✓ |
| You decide | Claude picks. | |

**User's choice:** Rich panel flash

### Daily Deals

| Option | Description | Selected |
|--------|-------------|----------|
| No deals | Static catalog, same items and prices always. | ✓ |
| Simple discounts | Random item gets 20% off each day. | |

**User's choice:** No deals

---

## Item Catalog & Balance

### Healing Potions

| Option | Description | Selected |
|--------|-------------|----------|
| Two tiers | Small (30% HP), Full (100% HP). | |
| Three tiers | Small (30%), Medium (60%), Full (100%). | |
| You decide | Claude picks based on capsule tier pattern. | ✓ |

**User's choice:** You decide (Claude's discretion)

### XP Boosters

| Option | Description | Selected |
|--------|-------------|----------|
| Next-battle boost | 1.5x creature XP for one fight. | |
| Timed boost | 30 minutes real time, 1.5x all XP. | ✓ |
| Next N commands | Boosts XP for next 50 shell commands. | |

**User's choice:** Timed boost (30 min real time)

### Revive Items

| Option | Description | Selected |
|--------|-------------|----------|
| Single revive | One type, restores fainted creature to 50% HP. | ✓ |
| Two tiers | Basic (25% HP) and Full (100% HP). | |
| You decide | Claude picks. | |

**User's choice:** Single revive

### Pricing Philosophy

| Option | Description | Selected |
|--------|-------------|----------|
| Affordable early | Basic items cost ~1-2 battles. Rare items are the sink. | ✓ |
| Scarce economy | Even basics require 3-5 battles. Currency feels precious. | |
| You decide | Claude balances against existing formulas. | |

**User's choice:** Affordable early

---

## Currency Earning & Display

### Currency Name

| Option | Description | Selected |
|--------|-------------|----------|
| Bits | Developer-themed, as in binary bits. | ✓ |
| Credits | Generic sci-fi/game currency. | |
| Gold | Classic RPG currency. | |

**User's choice:** Bits

### Reward Display

| Option | Description | Selected |
|--------|-------------|----------|
| Reward summary panel | Rich panel after victory with XP + Bits. | ✓ |
| Inline narration | Rewards in battle text flow. | |
| You decide | Claude picks. | |

**User's choice:** Reward summary panel

### Status Integration

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, in profile panel | Add Bits to existing status display. | ✓ |
| Separate wallet command | Dedicated devmon wallet command. | |
| Both | Status panel + shop header. | |

**User's choice:** Yes, in profile panel

---

## Inventory Management

### Items View

| Option | Description | Selected |
|--------|-------------|----------|
| Category table | Rich table grouped by category, mirrors shop. | ✓ |
| Flat list | Single list sorted by type. | |
| You decide | Claude picks to match shop. | |

**User's choice:** Category table

### Battle Item Usage

| Option | Description | Selected |
|--------|-------------|----------|
| Items action menu | Sub-menu of usable items in battle. Uses a turn. | ✓ |
| Pre-battle only | Use items before battle, only capsules during. | |
| You decide | Claude designs integration. | |

**User's choice:** Items action menu

### Stack Limits

| Option | Description | Selected |
|--------|-------------|----------|
| No limits | Unlimited stacking. | ✓ |
| Per-item cap of 99 | Classic RPG cap. | |
| Low caps (10-20) | Forces strategic purchasing. | |

**User's choice:** No limits

### XP Booster Activation

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, from items command | devmon items use xp-booster activates timer. | ✓ |
| Battle menu only | Only usable during battle. | |
| You decide | Claude picks. | |

**User's choice:** Yes, from items command

---

## Item Data Storage

| Option | Description | Selected |
|--------|-------------|----------|
| JSON data files | Items in src/devmon/data/items/, loaded like creatures. | ✓ |
| Python constants | Dict/enum in Python source. | |
| Single JSON file | All items in one items.json. | |

**User's choice:** JSON data files

---

## Capsule Selection in Battle

| Option | Description | Selected |
|--------|-------------|----------|
| Sub-menu | Capture opens sub-menu of owned capsules with quantities. | ✓ |
| Best available auto | Auto-selects best capsule owned. | |
| Items menu route | Remove Capture action, route through Items menu. | |

**User's choice:** Sub-menu

---

## Starter Items

| Option | Description | Selected |
|--------|-------------|----------|
| Small starter kit | 5 Basic Capsules + 3 Small Potions. | ✓ |
| No free items | Must earn and buy everything. | |
| You decide | Claude picks. | |

**User's choice:** Small starter kit

---

## Insufficient Funds UX

| Option | Description | Selected |
|--------|-------------|----------|
| Friendly denial | Encouraging message with needed amount. | |
| Grayed items | Unaffordable items visually grayed out. | ✓ |
| Both | Gray out + friendly message on attempt. | |

**User's choice:** Grayed items

---

## Claude's Discretion

- Potion tier count and exact HP restoration percentages
- Exact pricing for all items
- XP booster timer persistence mechanism
- Item sub-menu rendering style in battle
- Schema version bump strategy
- Starter kit grant timing (new game vs first shop visit)

## Deferred Ideas

- Daily deals / rotating stock
- Item flavor text / lore
- Selling items back to shop
- Item drops from wild encounters
