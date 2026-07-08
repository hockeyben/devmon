# DevMon: Repo Polish, Quest System, Update Hook, Multi-Profile, Anti-Cheat

Date: 2026-07-08
Status: Approved for planning

## Context

DevMon is a mature local CLI/TUI game (Python 3.12, Typer/Rich/Textual, Pydantic
save model, schema_version 12, 1094+ tests). Five previously-separate asks are
bundled here because the user requested a single fan-out pass; each is an
independently shippable subsystem and gets its own implementation plan.

DevMon makes **zero AI API calls** — verified via grep (only network-adjacent
import in the whole `src/` tree is `urllib.parse.urlparse` for `devmon://`
protocol parsing). It reads the user's local Claude Code event log for XP
timing only. This remains true after this work; no new subsystem may call an
LLM API.

## 1. Repo polish & docs

- New root `README.md`: badges (build/tests, Python version, license), feature
  overview, screenshots (reuse the existing `shoot_app.py` + headless-Edge
  screenshot pipeline), full command reference table (all `devmon <cmd>` +
  in-app `/` commands), quickstart (install, `devmon hook install`, `devmon
  play`).
- `CONTRIBUTING.md`: dev setup (`uv sync`), test command, code style pointers
  (matches CLAUDE.md conventions already in the repo).
- `LICENSE`: MIT.
- `docs/STORY.md`: dev-world lore primer (tone reference for quest content).
- GitHub repo created via `gh repo create devmon --public --source=. --push`,
  description + topics set via `gh repo edit`.

## 2. Quest system

**Data model** (`src/devmon/data/quests.json`, loaded by a new
`engine/quest_loader.py` following the existing `recipe_loader.py`/
`npc_loader.py` pattern):

```json
{
  "quest_id": "termina_meadows_01",
  "title": "First Compile",
  "region": "termina_meadows",
  "prerequisites": {"level": 1, "prior_quest": null, "rank": null},
  "objectives": [{"type": "defeat", "count": 3, "target": null}],
  "rewards": {"bits": 50, "xp": 100, "items": [], "creatures": []},
  "next_quests": ["termina_meadows_02"],
  "narrative": {"offer": "...", "complete": "..."}
}
```

Objective types: `defeat` (N encounters won, optionally filtered by
region/rarity), `capture` (N creatures captured), `deliver` (N of item X to an
NPC), `reach_region`, `reach_level`. Branching: `next_quests` may list 2+ ids;
offering logic checks each candidate's `prerequisites` independently — no
forced single path.

**Engine** (`src/devmon/engine/quests.py`): pure functions mirroring
`legendary_quests.py`'s existing shape — `available_quests(state)`,
`accept_quest(state, quest_id)`, `progress_quest(state, event)` (called from
the same event points that already update `legendary_quests` progress —
battle win, capture, region change), `complete_quest(state, quest_id)`
(grants rewards via existing `loot.py` grant helpers, no new economy code).

**Save model**: additive field `quest_log: dict[str, str]` (quest_id →
status: `offered|active|complete`) on `GameState`, migration bumps
`schema_version` to 13 per the existing field-presence migration pattern in
`persistence/save.py`.

**NPCs**: extend `data/npcs.json` entries with an optional `quests: [quest_id,
...]` list; `commands/npc.py` (or wherever NPC interaction lives) offers
those quests alongside existing shop deals.

**UI**: `devmon quests` CLI command (list active/available/complete with
objective progress); new "Quests" section — either its own TabPane or a
sub-view inside Progression — showing the same, with per-quest objective
progress bars matching the existing bar-rendering helpers.

**Main story questline**: one authored quest chain per region
(termina_meadows → compiler_wastes → cloud_reaches → kernel_depths →
voidnet), capstone quest gated on defeating/capturing a mythic. All narrative
text is static authored content in `quests.json` — never generated at
runtime.

**Dungeons**: explicitly deferred. `docs/ROADMAP-DEPTH.md` gets a "Dungeons
(planned)" section: multi-encounter gauntlet + boss fight, dungeon-exclusive
loot table, entry gated by a quest or item. The `objectives` list shape
(ordered, typed steps) is designed so a future `dungeon` objective type or a
dungeon-as-quest-chain can be added without reshaping `quest_log`.

## 3. Update-migration hook

`devmon update` (new command, `commands/update.py`):

1. Check installed version (`importlib.metadata.version("devmon")`) against
   latest available (git tag on the new GitHub remote, fetched via `git ls-remote
   --tags`; falls back to "unknown, skipping check" if remote unreachable —
   never blocks on network).
2. If newer available: back up `save.json` using the existing
   `save.bak1/2/3` rotation (already implemented in `persistence/save.py`),
   `git pull` (or instruct the user if not a git checkout), reinstall the uv
   tool env ONLY if `pyproject.toml`'s dependency block changed (diff
   before/after pull) — reuses the `UV_LINK_MODE=copy uv tool install
   --editable . --reinstall` + retry-on-lock pattern already documented in
   project memory.
3. Run any pending schema migrations (already versioned).
4. Verify: reload the save, confirm it parses and `schema_version` matches
   current — on ANY failure, restore the pre-update backup and report the
   error; never leave the user with a half-migrated or unloadable save.
5. Report a summary (old version → new version, migrations applied).

No silent background auto-update — this is a command the user runs.

## 4. Multi-profile saves

- Directory layout: `<data dir>/profiles/<name>/save.json` (+ its own
  `.bak1/2/3`); `<data dir>/active_profile` is a plain-text pointer file
  (default profile name `default`, auto-created on first run — existing
  single-save users get migrated: existing `save.json` moves to
  `profiles/default/save.json` transparently on next load, no data loss).
- `commands/profile.py`: `devmon profile create <name>`, `list`, `switch
  <name>`, `delete <name>` (delete requires `--confirm` flag, refuses to
  delete the active profile without switching first).
- `persistence/save.py`'s `_save_dir()` becomes profile-aware: resolves
  through `active_profile` unless `DEVMON_PROFILE` env var overrides it
  (keeps tests hermetic via existing `tmp_devmon_home` fixture pattern).
- TUI: profile switcher in the Settings tab — lists profiles, switching
  reloads `self.state` via the app's existing `reload_state()`/`refresh_all()`
  path (no restart needed, matches the existing 10s sync-reload mechanism).

## 5. Anti-cheat (tamper-evident, not tamper-proof)

- A local secret (`<data dir>/.integrity_key`, generated once via
  `secrets.token_hex(32)`, file permissions best-effort restricted) — never
  committed, never transmitted.
- On every `save()`, compute `HMAC-SHA256(key, canonical_json(state))` over
  the save content (excluding the checksum field itself) and store it as
  `state._integrity` (or a sidecar file `save.integrity` — sidecar preferred:
  keeps `GameState`'s schema clean, avoids the checksum needing to exclude
  itself from its own input).
- On `load()`: recompute and compare. Mismatch → do NOT wipe or revert
  anything; set an in-memory `state.integrity_flagged = True` (not persisted
  as a field that itself needs integrity — recomputed fresh each load) shown
  as a visible badge in the TUI status/dashboard and `devmon status` output
  ("⚠ save modified outside DevMon"). The flag clears itself the next time
  the game legitimately writes the save (new correct checksum).
- This blocks the casual case (hand-editing `save.json`, or asking an AI
  assistant to bump `bits` to 999999) from silently passing as legitimate
  progress, without any risk of bricking a save for a determined tamperer who
  edits the sidecar too — that's accepted as out of scope per the "tamper-evident
  not tamper-proof" decision.

## Testing

Every subsystem gets unit tests following existing patterns (pytest,
`tmp_devmon_home`/`tmp_save_dir` fixtures). Quest engine: objective
progress/branching/reward-granting. Profiles: create/switch/delete,
migration of a pre-existing single save into `profiles/default/`. Update
hook: backup-restore-on-failure path (simulate a migration exception).
Integrity: tamper detection round-trip, flag clears on next legitimate save.
Full suite must stay green (baseline 1094+ passed).

## Out of scope (this pass)

- Dungeons (see section 2 — deferred, roadmap entry only).
- Cryptographically tamper-*proof* saves (would require server-side
  validation this is architecturally a local-only game).
- Auto-update without an explicit `devmon update` invocation.
- PyPI publishing for `devmon update`'s version check (uses git tags on the
  new GitHub remote instead).
