# Repo Polish, Quest System, Update Hook, Multi-Profile, Anti-Cheat Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. **This plan is executed via the Workflow tool with git-worktree isolation per task** (five subsystems touch overlapping files — see Global Constraints) rather than in the main working tree directly.

**Goal:** Ship five independently shippable DevMon subsystems: a polished public GitHub presence, a full quest/story system, a safe `devmon update` migration hook, multi-profile saves, and tamper-evident save integrity — per `docs/superpowers/specs/2026-07-08-repo-polish-quests-profiles-design.md`.

**Architecture:** Each task is a self-contained subsystem with its own files, tests, and commit(s). Tasks 2-5 all touch `persistence/save.py` and/or `models/state.py` — they run in isolated git worktrees in parallel, then are merged sequentially (Task 3 → 4 → 5 → 6 order below) with the full suite re-run after each merge to catch cross-task interaction. Task 1 (repo polish) is fully independent (docs/README only) and can merge anytime.

**Tech Stack:** Python 3.12, Typer, Rich, Textual, Pydantic v2, pytest, uv, `gh` CLI, git worktrees.

## Global Constraints

- Full test suite must stay green after every merge: `uv run python -m pytest -q` (baseline: 1094 passed).
- All new Pydantic model fields are additive with defaults — never break loading a pre-existing save.json.
- `schema_version` bumps to 13 for the quest_log field (Task 3); no other task needs a schema bump (profile-dir move and integrity sidecar are file-layout changes, not model-shape changes).
- No AI/LLM API calls anywhere in new code — DevMon runs with zero AI credits. Verify with `grep -riE "anthropic|openai|api_key" src/devmon/<new files>` before considering a task done.
- Follow existing patterns: data-driven JSON + `*_loader.py` (see `npc_loader.py`, `recipe_loader.py`); Typer sub-app per command group (see `commands/indicator.py`); `tmp_devmon_home`/`tmp_save_dir` pytest fixtures for hermetic save-dir tests (see `tests/conftest.py`).
- Commit messages end with `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`.

---

### Task 1: Repo polish — README, CONTRIBUTING, LICENSE, GitHub repo

**Files:**
- Create: `README.md` (repo root, replaces nothing — none exists yet)
- Create: `CONTRIBUTING.md`
- Create: `LICENSE` (MIT)
- Create: `docs/STORY.md`
- No test file — this task is documentation + `gh` CLI calls, verified by manual review, not pytest.

**Interfaces:** None consumed. Produces: public GitHub repo URL (report it back).

- [ ] **Step 1: Inventory commands for the reference table**

Run: `uv run devmon --help` and `uv run devmon <each-subcommand> --help` for every top-level command registered in `src/devmon/main.py` (grep `app.add_typer` and `@app.command` there for the full list). Capture the flag/purpose of each into a table: Command | Purpose | Example.

- [ ] **Step 2: Capture screenshots**

Reuse `C:\Users\flopp\AppData\Local\Temp\claude\...\scratchpad\shoot_app.py` pattern (pilot `run_test(size=(140,38))`, `save_screenshot` per tab, headless Edge SVG→PNG). Save 3-4 PNGs to `docs/screenshots/` (dashboard, collection, economy, quests once Task 3 lands — for this task, dashboard/collection/economy/world are enough; quests screenshot can be a follow-up, don't block on it).

- [ ] **Step 3: Write README.md**

Sections: title + one-line pitch, badges (tests via a simple "tests: passing" static badge is fine — no CI configured yet, don't claim a CI badge that lies), Features (bullet list: statusline XP tracking, auto-battle, 78 creatures across 5 regions, crafting/marketplace/NPCs, full-screen TUI, quest system if Task 3 has landed by the time this is written — otherwise omit and add in a follow-up commit), Screenshots (embed the PNGs from Step 2), Quickstart (`uv tool install --editable .`, `devmon hook install`, `devmon play`), Command Reference (table from Step 1), License link.

- [ ] **Step 4: Write CONTRIBUTING.md**

Dev setup (`uv sync`), running tests (`uv run python -m pytest -q`), code style pointers pulled from this repo's `CLAUDE.md` Conventions section (comments-only-when-non-obvious, no premature abstraction, atomic commits).

- [ ] **Step 5: Add LICENSE (MIT)**

Standard MIT license text, copyright line `Copyright (c) 2026 HockeyBen MacDonald`.

- [ ] **Step 6: Write docs/STORY.md**

Dev-world lore primer: 1 paragraph per region (termina_meadows, compiler_wastes, cloud_reaches, kernel_depths, voidnet) tying tone to `data/regions.json`'s level bands, written for a reader who hasn't played yet (this doc is also the tone reference Task 3's quest-writer agent should read before authoring quest narrative text).

- [ ] **Step 7: Commit docs**

```bash
git add README.md CONTRIBUTING.md LICENSE docs/STORY.md docs/screenshots/
git commit -m "docs: add README, CONTRIBUTING, LICENSE, and dev-world lore primer

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

- [ ] **Step 8: Create and push the GitHub repo**

```bash
gh repo create devmon --public --source=. --description "Gamified terminal creature-collection RPG powered by real coding activity" --push
gh repo edit --add-topic python --add-topic cli --add-topic textual --add-topic game --add-topic terminal
```

Report the resulting repo URL back to the user.

---

### Task 2: Quest data model + engine

**Files:**
- Create: `src/devmon/data/quests.json`
- Create: `src/devmon/engine/quest_loader.py`
- Create: `src/devmon/engine/quests.py`
- Modify: `src/devmon/models/state.py` (add `quest_log` field)
- Modify: `src/devmon/persistence/save.py` (schema_version 12→13 migration)
- Modify: `src/devmon/data/npcs.json` (add optional `quests` list to entries)
- Test: `tests/test_quests.py`
- Test: `tests/test_quest_loader.py`

**Interfaces:**
- Consumes: `GameState` (from `devmon.models.state`), existing `loot.py` grant helpers (grep `loot.py` for the exact grant-function name/signature before use — likely `grant_rewards(state, rewards) -> None` or similar; use whatever the existing signature is, don't invent a new one), existing battle/capture/region-change event hooks (grep `legendary_quests.py`'s `progress_legendary_quest` call sites in `commands/battle.py`/`commands/travel.py`/`commands/collection.py` to find the exact points to mirror).
- Produces: `available_quests(state: GameState) -> list[Quest]`, `accept_quest(state: GameState, quest_id: str) -> None`, `progress_quest(state: GameState, event: QuestEvent) -> list[str]` (returns ids of quests that became complete as a result), `complete_quest(state: GameState, quest_id: str) -> None`, `Quest` and `QuestEvent` Pydantic models (or dataclasses — match whatever `legendary_quests.py` uses for its own quest model).

- [ ] **Step 1: Read the reference implementation completely**

Read `src/devmon/engine/legendary_quests.py` end to end, and `src/devmon/engine/npc_loader.py` end to end, before writing anything — this task's shape must mirror both exactly (data-driven JSON load pattern from npc_loader, progress-tracking pattern from legendary_quests). Note the exact function names, the exact `GameState` field types for anything quest-adjacent (e.g. does `legendary_quests` track progress as a dict on `state`? What's that field called?).

- [ ] **Step 2: Write quests.json with the main story questline**

One quest per region plus a capstone, per the spec's example shape:

```json
[
  {
    "quest_id": "termina_meadows_01",
    "title": "First Compile",
    "region": "termina_meadows",
    "prerequisites": {"level": 1, "prior_quest": null, "rank": null},
    "objectives": [{"type": "defeat", "count": 3, "target": null}],
    "rewards": {"bits": 50, "xp": 100, "items": [], "creatures": []},
    "next_quests": ["termina_meadows_02"],
    "narrative": {
      "offer": "The compiler hums, waiting for its first real test. Prove your build works -- defeat three wild DevMon.",
      "complete": "First compile clean. Termina Meadows opens fully to you now."
    }
  }
]
```

Write 5 main-line quests (one per region) plus one capstone quest gated on `rank` or a mythic capture (check `mythic.py` for how mythic ownership is queried, use that same check as the capstone's prerequisite type — add a `"mythic_owned": true` prerequisite key if none exists yet, document it in this same file's schema comment). Author narrative text using the tone from `docs/STORY.md` (Task 1) if it exists yet at write time — if Task 1 hasn't merged yet, use the existing region descriptions in `data/regions.json` as the tone source instead, don't block on Task 1.

- [ ] **Step 3: Write the failing test for quest_loader**

```python
def test_load_all_quests_returns_dict_keyed_by_id():
    from devmon.engine.quest_loader import load_all_quests
    quests = load_all_quests()
    assert "termina_meadows_01" in quests
    assert quests["termina_meadows_01"].title == "First Compile"
```

- [ ] **Step 4: Run test to verify it fails**

Run: `uv run python -m pytest tests/test_quest_loader.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'devmon.engine.quest_loader'`

- [ ] **Step 5: Implement quest_loader.py**

Mirror `npc_loader.py`'s exact caching/parsing pattern (module-level cache dict, `importlib.resources` or the same file-path resolution `npc_loader.py` uses for `data/npcs.json` — copy that resolution logic exactly, don't invent a new one). Define a `Quest` model (Pydantic) matching the JSON shape from Step 2.

- [ ] **Step 6: Run test to verify it passes**

Run: `uv run python -m pytest tests/test_quest_loader.py -v`
Expected: PASS

- [ ] **Step 7: Add quest_log field to GameState**

In `src/devmon/models/state.py`, add:
```python
quest_log: dict[str, str] = Field(default_factory=dict)
"""quest_id -> status ('offered' | 'active' | 'complete')."""
```
Place it near the existing `party`/`creature_collection` fields for locality.

- [ ] **Step 8: Write the failing migration test**

```python
def test_load_migrates_pre_quest_save_with_empty_quest_log(tmp_save_dir):
    # write a save.json dict with schema_version=12 and no quest_log key
    ...
    state = load()
    assert state.quest_log == {}
    assert state.schema_version == 13
```
(Match this repo's existing migration test style — read `tests/test_persistence.py`'s existing schema-version migration tests first and copy their exact save-dict-construction helper rather than writing a new one.)

- [ ] **Step 9: Run test to verify it fails, then implement the migration**

In `persistence/save.py`, follow the exact field-presence migration pattern already used for prior schema bumps (grep `schema_version` in that file to find the pattern) — bump to 13, default `quest_log` to `{}` if absent.

- [ ] **Step 10: Run migration test to verify it passes**

Run: `uv run python -m pytest tests/test_persistence.py -k quest -v`
Expected: PASS

- [ ] **Step 11: Write failing tests for the quest engine**

```python
def test_available_quests_respects_level_prerequisite():
    state = make_state(level=1)
    quests = available_quests(state)
    assert any(q.quest_id == "termina_meadows_01" for q in quests)

def test_accept_quest_sets_status_active():
    state = make_state(level=1)
    accept_quest(state, "termina_meadows_01")
    assert state.quest_log["termina_meadows_01"] == "active"

def test_progress_quest_completes_on_objective_met():
    state = make_state(level=1)
    accept_quest(state, "termina_meadows_01")
    for _ in range(3):
        completed = progress_quest(state, QuestEvent(type="defeat", region="termina_meadows"))
    assert "termina_meadows_01" in completed
    assert state.quest_log["termina_meadows_01"] == "complete"

def test_complete_quest_grants_rewards():
    state = make_state(level=1, bits=0)
    accept_quest(state, "termina_meadows_01")
    complete_quest(state, "termina_meadows_01")
    assert state.player.currency == 50  # matches quests.json reward
```
(Use whatever `make_state` helper `tests/test_quests.py`'s neighbors use — check `tests/test_legendary_quests.py` if it exists for the exact fixture helper name/import.)

- [ ] **Step 12: Run tests to verify they fail**

Run: `uv run python -m pytest tests/test_quests.py -v`
Expected: FAIL (`quests.py` doesn't exist yet)

- [ ] **Step 13: Implement engine/quests.py**

Implement `available_quests`, `accept_quest`, `progress_quest`, `complete_quest`, `QuestEvent` per the Interfaces section above. `complete_quest` calls the exact reward-grant helper found in Step 1's read of `loot.py`.

- [ ] **Step 14: Run tests to verify they pass**

Run: `uv run python -m pytest tests/test_quests.py tests/test_quest_loader.py -v`
Expected: all PASS

- [ ] **Step 15: Wire progress_quest into existing event points**

In `commands/battle.py` (or wherever `legendary_quests`' own progress call lives — mirror the exact call site found in Step 1), add a `progress_quest(state, QuestEvent(...))` call alongside the existing legendary-quest progress call. Same for capture (`commands/collection.py` or wherever captures are recorded) and region-change (`commands/travel.py`). Add one integration test per hook point confirming a real battle win advances a `defeat`-type quest objective.

- [ ] **Step 16: Add quests field to NPC data + npc_loader quest offers**

In `data/npcs.json`, add `"quests": ["quest_id", ...]` (optional key, empty/absent for NPCs with none) to at least one NPC entry (e.g. Skye in cloud_reaches, tied to `cloud_reaches`-region quests once written). Extend whatever module handles NPC interaction (grep for where `npcs.json`'s existing `deals`/shop data is consumed) to also surface `available_quests(state)` filtered to that NPC's `quests` list.

- [ ] **Step 17: Add `devmon quests` CLI command**

Create/extend a Typer command (follow `commands/npcs.py` or `commands/perks.py`'s exact CLI-table-rendering style for consistency) listing active/available/complete quests with objective progress. Test via `CliRunner` matching this repo's existing CLI test style (`tests/test_perks.py` as the closest analog).

- [ ] **Step 18: Add ROADMAP-DEPTH.md dungeons entry**

Append to `docs/ROADMAP-DEPTH.md`: a "Dungeons (planned)" section per the spec's Section 2 dungeons paragraph — multi-encounter gauntlet, boss creature, dungeon-exclusive loot, entry gated by quest/item, noting the `objectives` list shape already supports future extension.

- [ ] **Step 19: Full task gate + commit**

```bash
uv run python -m pytest -q
git add src/devmon/data/quests.json src/devmon/data/npcs.json src/devmon/engine/quest_loader.py src/devmon/engine/quests.py src/devmon/models/state.py src/devmon/persistence/save.py src/devmon/commands/ docs/ROADMAP-DEPTH.md tests/test_quests.py tests/test_quest_loader.py
git commit -m "feat(quests): data-driven quest engine, main storyline, NPC quest offers, devmon quests CLI

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 3: Quests Textual UI panel

**Files:**
- Modify: `src/devmon/app/screens/progression.py` (or create `src/devmon/app/screens/quests.py` if progression.py is already large — check its current line count first; if over ~250 lines, split into its own TabPane instead of cramming in)
- Modify: `src/devmon/app/tui.py` (register new tab if a separate screen was created)
- Test: `tests/app/test_app.py` (extend)

**Interfaces:**
- Consumes: `devmon.engine.quests.available_quests`, `state.quest_log`, `devmon.engine.quest_loader.load_all_quests` (all from Task 2 — this task cannot start until Task 2's engine functions exist; sequence after Task 2 merges).
- Produces: nothing consumed by later tasks.

- [ ] **Step 1: Check progression.py's current size**

Run: `wc -l src/devmon/app/screens/progression.py` (or PowerShell equivalent `(Get-Content ... | Measure-Object -Line).Lines`). If > 250 lines, create a new `quests.py` screen + new TabPane in `tui.py` (mirror exactly how `WorldScreen`/`EconomyScreen` are registered). If under 250, add a "Quests" sub-section within the existing Progression screen's `.panel` layout.

- [ ] **Step 2: Write failing pilot test**

```python
async def test_quests_panel_lists_available_and_active(tmp_save_dir):
    # seed a save where termina_meadows_01 is available (level 1, no quest_log entry)
    ...
    app = DevMonApp()
    async with app.run_test(size=(140, 38)) as pilot:
        await pilot.pause()
        # navigate to quests tab/section
        ...
        table_text = app.query_one("#quests-table")... # match this repo's DataTable query idiom from collection.py
        assert "First Compile" in str(table_text.render())  # or however collection.py's existing tests assert table contents -- copy that exact idiom
```
Read `tests/app/test_app.py`'s existing collection-tab test first and copy its exact assertion idiom rather than inventing a new one.

- [ ] **Step 3: Run test to verify it fails**

Run: `uv run python -m pytest tests/app/test_app.py -k quest -v`
Expected: FAIL (no quests panel yet)

- [ ] **Step 4: Implement the panel**

Bordered `.panel` DataTable (Title | Region | Status | Progress), populated in `refresh_data()` from `available_quests(self.app.state)` + `self.app.state.quest_log`, following the exact `.panel`/`refresh_data()` contract already used by every other screen (see `tui.py`'s `refresh_all`/`refresh_after_mutation` docstrings for the contract every screen must follow).

- [ ] **Step 5: Run test to verify it passes**

Run: `uv run python -m pytest tests/app/test_app.py -k quest -v`
Expected: PASS

- [ ] **Step 6: Full task gate + commit**

```bash
uv run python -m pytest -q
git add src/devmon/app/ tests/app/test_app.py
git commit -m "feat(app): Quests panel in the Textual UI

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 4: Update-migration hook (`devmon update`)

**Files:**
- Create: `src/devmon/commands/update.py`
- Modify: `src/devmon/main.py` (register the new Typer sub-app)
- Test: `tests/test_update.py`

**Interfaces:**
- Consumes: `devmon.persistence.save.load`/`save` (existing), the existing `save.bak1/2/3` backup rotation (read `persistence/save.py`'s save() function to find its exact name — likely `_rotate_backups()` or inline in `save()`; reuse it, don't reimplement backup rotation).
- Produces: nothing consumed by later tasks.

- [ ] **Step 1: Read persistence/save.py's backup rotation completely**

Find the exact function/inline logic that produces `save.bak1/2/3` and note its exact call signature so Step 5 below calls the real thing.

- [ ] **Step 2: Write failing test for version check**

```python
def test_update_reports_up_to_date_when_no_newer_tag(monkeypatch, tmp_devmon_home):
    import devmon.commands.update as update_mod
    monkeypatch.setattr(update_mod, "_installed_version", lambda: "0.1.0")
    monkeypatch.setattr(update_mod, "_latest_remote_tag", lambda: "0.1.0")
    result = CliRunner().invoke(main_app, ["update"])
    assert result.exit_code == 0
    assert "up to date" in result.output.lower()
```

- [ ] **Step 3: Run test to verify it fails**

Run: `uv run python -m pytest tests/test_update.py -v`
Expected: FAIL (`devmon.commands.update` doesn't exist)

- [ ] **Step 4: Implement version-check skeleton**

`_installed_version() -> str` via `importlib.metadata.version("devmon")`. `_latest_remote_tag() -> str | None` via `subprocess.run(["git", "ls-remote", "--tags", "origin"], capture_output=True, timeout=5)`, parsing the highest semver tag; returns `None` (never raises) on any failure (no remote, network down, git not a repo) — the command then reports "couldn't check for updates" and exits 0, never blocking the user.

- [ ] **Step 5: Run test to verify it passes; write failing test for the migration-failure-restores-backup path**

```python
def test_update_restores_backup_on_migration_failure(monkeypatch, tmp_devmon_home):
    # seed a valid save.json
    ...
    monkeypatch.setattr(update_mod, "_installed_version", lambda: "0.1.0")
    monkeypatch.setattr(update_mod, "_latest_remote_tag", lambda: "0.2.0")
    monkeypatch.setattr(update_mod, "_git_pull", lambda: None)
    monkeypatch.setattr(update_mod, "_maybe_reinstall_tool_env", lambda: None)
    monkeypatch.setattr(update_mod, "_run_post_pull_migration_check", lambda: (_ for _ in ()).throw(RuntimeError("bad migration")))
    result = CliRunner().invoke(main_app, ["update"])
    assert result.exit_code != 0
    assert "restored" in result.output.lower()
    # assert save.json content is byte-identical to the pre-update backup
```

- [ ] **Step 6: Run test to verify it fails, then implement the full update flow**

`update_command()`: compare versions → if current, report and exit 0 → else back up save (reuse Step 1's helper) → `_git_pull()` (`subprocess.run(["git", "pull"], cwd=<repo root>)`; if not a git checkout, report "not a git checkout, please update manually" and exit 1 before touching anything) → `_maybe_reinstall_tool_env()` (diff `pyproject.toml`'s dependency block before/after pull via `git diff`, run `UV_LINK_MODE=copy uv tool install --editable . --reinstall` with the retry-on-lock loop documented in project memory `project_devmon_tool_env_reinstall.md` only if the diff shows a change) → `_run_post_pull_migration_check()` (calls `persistence.save.load()`, confirms it doesn't raise and `schema_version` matches the current code's expected version) → on any exception from pull/reinstall/migration-check, restore the backup file over `save.json` and report failure with exit code 1 → on success, report old→new version.

- [ ] **Step 7: Run all update tests to verify pass**

Run: `uv run python -m pytest tests/test_update.py -v`
Expected: all PASS

- [ ] **Step 8: Register in main.py**

Mirror exactly how `indicator_cmd`/`play_app` are registered in `main.py` (`app.add_typer(update_cmd.app, name="update")` — check whether `update` should be a bare command or sub-app; a single command with no subcommands should use `@app.command()` directly in `main.py` or a single-callback Typer app like `commands/app.py`'s `play_app` — match that pattern, not the multi-subcommand `indicator` pattern).

- [ ] **Step 9: Full task gate + commit**

```bash
uv run python -m pytest -q
git add src/devmon/commands/update.py src/devmon/main.py tests/test_update.py
git commit -m "feat(update): devmon update command — safe git-pull + migration + backup-restore-on-failure

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 5: Multi-profile saves

**Files:**
- Modify: `src/devmon/persistence/save.py` (`_save_dir()` becomes profile-aware)
- Create: `src/devmon/commands/profile.py`
- Modify: `src/devmon/main.py` (register `profile` sub-app)
- Modify: `src/devmon/app/screens/settings.py` (profile switcher)
- Test: `tests/test_profile.py`
- Test: `tests/app/test_app.py` (extend, profile switcher)

**Interfaces:**
- Consumes: `persistence.save._save_dir()` (existing — this task changes its internals, must keep its return type `Path` and all existing callers working unchanged).
- Produces: `profile_dir(name: str) -> Path`, `active_profile() -> str`, `set_active_profile(name: str) -> None`, `list_profiles() -> list[str]`, `create_profile(name: str) -> None`, `delete_profile(name: str) -> None` (all in `persistence/save.py` or a new `persistence/profiles.py` if `save.py` is already large — check line count first, same rule as Task 3).

- [ ] **Step 1: Check save.py's current size and read _save_dir() completely**

Run: `wc -l src/devmon/persistence/save.py`. Read `_save_dir()`'s exact current implementation (platformdirs + `DEVMON_HOME` override) — the profile-aware version must preserve the `DEVMON_HOME` override behavior exactly (existing tests depend on it for hermetic test isolation).

- [ ] **Step 2: Write failing test for profile-aware save dir with migration**

```python
def test_existing_single_save_migrates_to_default_profile_on_first_load(tmp_devmon_home):
    # tmp_devmon_home fixture already writes save.json directly under the data dir (old layout)
    from devmon.persistence.save import load, _save_dir
    state = load()
    assert state is not None
    assert (tmp_devmon_home / "profiles" / "default" / "save.json").exists()

def test_create_list_switch_profiles(tmp_devmon_home):
    from devmon.persistence.save import create_profile, list_profiles, set_active_profile, active_profile
    create_profile("alt")
    assert "alt" in list_profiles()
    assert "default" in list_profiles()
    set_active_profile("alt")
    assert active_profile() == "alt"
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `uv run python -m pytest tests/test_profile.py -v`
Expected: FAIL

- [ ] **Step 4: Implement profile-aware _save_dir + migration + CRUD functions**

`active_profile()`: reads `<data dir>/active_profile` text file, defaults to and creates it with `"default"` if absent. `profile_dir(name)`: `<data dir>/profiles/<name>/`. `_save_dir()`: returns `profile_dir(active_profile())`, but FIRST (once, idempotently) checks whether `<data dir>/save.json` exists at the OLD top-level location and `<data dir>/profiles/default/save.json` does NOT — if so, move it (and its `.bak1/2/3` siblings) into `profiles/default/` before returning. `DEVMON_PROFILE` env var overrides `active_profile()`'s file read (mirrors how `DEVMON_HOME` already overrides the base dir — check existing env-var-override pattern in `pid.py`/`save.py` and copy it exactly). `create_profile`/`delete_profile`/`list_profiles`/`set_active_profile` as plain filesystem operations; `delete_profile` refuses (raises `ValueError`) if `name == active_profile()`.

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run python -m pytest tests/test_profile.py -v`
Expected: PASS

- [ ] **Step 6: Run the FULL existing persistence test suite to confirm no regression**

Run: `uv run python -m pytest tests/test_persistence.py -v`
Expected: all PASS unchanged (the migration must be fully transparent to every existing save/load test using `tmp_devmon_home`)

- [ ] **Step 7: Add devmon profile CLI command**

`commands/profile.py`: `create <name>`, `list`, `switch <name>`, `delete <name> --confirm`. Mirror `commands/indicator.py`'s Typer sub-app-with-subcommands structure exactly (closest analog: multiple named subcommands under one group).

```python
@app.command()
def switch(name: str) -> None:
    """Switch the active profile."""
    from devmon.persistence.save import list_profiles, set_active_profile
    if name not in list_profiles():
        typer.echo(f"No such profile: {name}")
        raise typer.Exit(1)
    set_active_profile(name)
    typer.echo(f"Switched to profile '{name}'")
```
(Write all four subcommands with this level of completeness — no placeholders.)

- [ ] **Step 8: Write CliRunner tests for the profile command**

Follow `tests/test_indicator.py`'s CliRunner test style exactly. Test create/list/switch/delete, and delete-without-confirm-flag-refuses, delete-active-profile-refuses.

- [ ] **Step 9: Register in main.py**

`app.add_typer(profile_cmd.app, name="profile")` next to the existing `indicator_cmd` registration.

- [ ] **Step 10: Add profile switcher to Settings TUI screen**

In `app/screens/settings.py`, add a `.panel` section listing `list_profiles()` with a button/select to switch — on switch, call `set_active_profile(name)` then `self.app.reload_state()` + `self.app.refresh_all()` (the exact two-call sequence `tui.py`'s `_on_sync_tick` already uses — copy it, this is the established "state changed outside normal handlers" convergence pattern).

- [ ] **Step 11: Write failing pilot test for the TUI switcher, implement, verify pass**

```python
async def test_settings_profile_switch_reloads_state(tmp_devmon_home):
    from devmon.persistence.save import create_profile
    create_profile("alt")
    app = DevMonApp()
    async with app.run_test(size=(140, 38)) as pilot:
        await pilot.pause()
        # navigate to settings tab, trigger switch to "alt"
        ...
        await pilot.pause()
        from devmon.persistence.save import active_profile
        assert active_profile() == "alt"
```

- [ ] **Step 12: Full task gate + commit**

```bash
uv run python -m pytest -q
git add src/devmon/persistence/save.py src/devmon/commands/profile.py src/devmon/main.py src/devmon/app/screens/settings.py tests/test_profile.py tests/app/test_app.py
git commit -m "feat(profiles): multi-profile saves with in-app switching, transparent single-save migration

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 6: Tamper-evident save integrity

**Files:**
- Create: `src/devmon/persistence/integrity.py`
- Modify: `src/devmon/persistence/save.py` (call integrity compute-on-save, verify-on-load)
- Modify: `src/devmon/commands/status.py` (or wherever `devmon status` renders — show the flagged badge)
- Modify: `src/devmon/app/tui.py` or a screen (show the flagged badge in the TUI)
- Test: `tests/test_integrity.py`

**Interfaces:**
- Consumes: `GameState` (Pydantic `.model_dump_json()` or equivalent canonical serialization — check what `save()` already uses to serialize and reuse that exact method so the checksum is computed over the same bytes that get written).
- Produces: `compute_checksum(state: GameState, key: bytes) -> str`, `verify_checksum(state: GameState, key: bytes, stored: str) -> bool`, `get_or_create_integrity_key() -> bytes`, sets an in-memory (non-persisted-as-a-model-field) `state.integrity_flagged: bool` attribute after `load()`.

- [ ] **Step 1: Write failing test for key generation**

```python
def test_get_or_create_integrity_key_persists_across_calls(tmp_devmon_home):
    from devmon.persistence.integrity import get_or_create_integrity_key
    k1 = get_or_create_integrity_key()
    k2 = get_or_create_integrity_key()
    assert k1 == k2
    assert len(k1) == 32
```

- [ ] **Step 2: Run test to verify it fails, then implement key generation**

`get_or_create_integrity_key()`: reads `<data dir>/.integrity_key` (hex-decoded), generates via `secrets.token_bytes(32)` and writes hex-encoded if absent. Best-effort restrict file perms on POSIX (`os.chmod(path, 0o600)`); no-op on Windows (NTFS ACLs are out of scope per spec's "best-effort").

- [ ] **Step 3: Run test to verify it passes**

Run: `uv run python -m pytest tests/test_integrity.py -k key -v`
Expected: PASS

- [ ] **Step 4: Write failing tests for checksum compute/verify**

```python
def test_verify_checksum_true_for_unmodified_state(tmp_devmon_home):
    from devmon.persistence.integrity import compute_checksum, verify_checksum, get_or_create_integrity_key
    state = make_state()
    key = get_or_create_integrity_key()
    checksum = compute_checksum(state, key)
    assert verify_checksum(state, key, checksum) is True

def test_verify_checksum_false_after_hand_edit(tmp_devmon_home):
    state = make_state()
    key = get_or_create_integrity_key()
    checksum = compute_checksum(state, key)
    state.player.currency = 999999  # simulated hand-edit
    assert verify_checksum(state, key, checksum) is False
```

- [ ] **Step 5: Run tests to verify they fail, then implement compute_checksum/verify_checksum**

`compute_checksum`: `hmac.new(key, state.model_dump_json(exclude={"integrity_flagged"} if that ever becomes a real field, else no exclude needed since it's not a model field, sort_keys equivalent — Pydantic v2 doesn't guarantee key order by default, so use `json.dumps(state.model_dump(mode="json"), sort_keys=True).encode()` as the canonical form instead of raw `model_dump_json()`).digest(), hashlib.sha256).hexdigest()`. `verify_checksum`: `hmac.compare_digest(compute_checksum(state, key), stored)`.

- [ ] **Step 6: Run tests to verify they pass**

Run: `uv run python -m pytest tests/test_integrity.py -k checksum -v`
Expected: PASS

- [ ] **Step 7: Write failing integration test for save/load round-trip**

```python
def test_load_flags_state_when_sidecar_mismatches(tmp_devmon_home):
    from devmon.persistence.save import save, load
    state = make_state()
    save(state)
    # hand-corrupt save.json's currency field without updating the sidecar
    ...
    loaded = load()
    assert loaded.integrity_flagged is True

def test_load_does_not_flag_legitimately_saved_state(tmp_devmon_home):
    from devmon.persistence.save import save, load
    state = make_state()
    save(state)
    loaded = load()
    assert loaded.integrity_flagged is False

def test_flag_clears_after_next_legitimate_save(tmp_devmon_home):
    from devmon.persistence.save import save, load
    state = make_state()
    save(state)
    # hand-corrupt
    ...
    loaded = load()
    assert loaded.integrity_flagged is True
    save(loaded)
    reloaded = load()
    assert reloaded.integrity_flagged is False
```

- [ ] **Step 8: Run tests to verify they fail, then wire into save()/load()**

In `persistence/save.py`'s `save()`: after writing `save.json`, compute checksum via Task 6's `compute_checksum` and write it to a sidecar file `save.integrity` (same directory, alongside `save.bak1/2/3`). In `load()`: after successfully parsing `save.json` into a `GameState`, read `save.integrity` (if absent — e.g. a pre-integrity-feature save — treat as unflagged, do NOT flag saves that predate this feature), recompute and compare; set `state.integrity_flagged = (comparison failed)` as a plain instance attribute (NOT a Pydantic field — set it after construction, e.g. `object.__setattr__` if the model is frozen, or a plain attribute assignment if not; check whether `GameState` has `model_config = ConfigDict(frozen=...)` first and handle accordingly).

- [ ] **Step 9: Run all integrity tests to verify pass**

Run: `uv run python -m pytest tests/test_integrity.py -v`
Expected: all PASS

- [ ] **Step 10: Show the flagged badge in devmon status**

In whatever module renders `devmon status`'s output (grep for the Rich rendering of player level/rank there), add: if `getattr(state, "integrity_flagged", False)`, print a line `"⚠ save modified outside DevMon"` (using this repo's existing width-safe glyph rule from `commands/statusline.py`'s docstring — `⚠` is U+26A0, ABOVE the width-safe threshold that file established; use `(!)` instead, matching `_encounter_row`'s existing ASCII-safe convention). Add a CliRunner test asserting the line appears when flagged, absent when not.

- [ ] **Step 11: Show the flagged badge in the TUI dashboard**

In `app/screens/dashboard.py`'s Trainer panel (the same panel showing Rank/Streak/Region/Currency/Skin), add a conditional line when `self.app.state.integrity_flagged` is true. Add a pilot test.

- [ ] **Step 12: Full task gate + commit**

```bash
uv run python -m pytest -q
git add src/devmon/persistence/integrity.py src/devmon/persistence/save.py src/devmon/commands/status.py src/devmon/app/screens/dashboard.py tests/test_integrity.py
git commit -m "feat(integrity): tamper-evident save checksums with a visible flag on mismatch

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

## Merge & Final Gate

After all six tasks are implemented (each in its own worktree/branch):

1. Merge Task 1 (repo polish) first — fully independent, lowest risk.
2. Merge Task 2 (quest engine) — establishes `quest_log` field and schema 13.
3. Merge Task 3 (quests UI) — depends on Task 2's engine functions; resolve any merge conflict in `tui.py`'s tab registration by keeping both new tabs.
4. Merge Task 5 (profiles) — touches `persistence/save.py`'s `_save_dir()`; resolve conflicts with Task 2's schema-migration edits to the same file by keeping both (migration logic and profile-dir logic are independent changes to different functions in the same file).
5. Merge Task 6 (integrity) — also touches `persistence/save.py`'s `save()`/`load()`; resolve by ensuring the integrity compute/verify calls wrap around (not replace) the profile-aware path and the schema migration.
6. Merge Task 4 (update hook) — fully independent of the others, any order.
7. After every merge: `uv run python -m pytest -q` — must stay green before merging the next task. If a merge breaks tests, fix forward in a small commit before proceeding, don't merge the next task on top of a red suite.
8. Final report to the user: full pass count, GitHub repo URL, list of new CLI commands (`devmon quests`, `devmon update`, `devmon profile ...`).
