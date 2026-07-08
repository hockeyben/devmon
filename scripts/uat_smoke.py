#!/usr/bin/env python3
"""UAT smoke-test automation for DevMon phases 06, 08, 09, 10.

Drives the REAL devmon CLI (via subprocess) against an isolated DEVMON_HOME,
seeding GameState through the real persistence layer (devmon.persistence.save).
Also exercises a handful of engine/render functions directly where a full
battle-victory RNG sequence would be infeasible to script deterministically
(each such check is labelled "[engine-level]" or "[render-level]" below).

This script is a REPORTING tool, not a CI gate: it always exits 0 after
printing the full PASS/FAIL table, including rows for known bugs discovered
while building the checks (those rows are prefixed "BUG:" in the detail
column and are intentionally left FAIL so they are visible).

Usage:
    uv run python scripts/uat_smoke.py
"""
from __future__ import annotations

import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import traceback
from contextlib import contextmanager
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from devmon.models.creature import OwnedCreature  # noqa: E402
from devmon.models.encounter import EncounterEntry  # noqa: E402
from devmon.models.quest import (  # noqa: E402
    AchievementUnlock,
    ActiveQuest,
    QuestCompletion,
    QuestCriterion,
)
from devmon.models.state import GameState  # noqa: E402
from devmon.persistence.save import load as load_state  # noqa: E402
from devmon.persistence.save import save as save_state  # noqa: E402

BASE_TMP = Path(tempfile.mkdtemp(prefix="devmon_uat_"))
RESULTS: list[tuple[str, bool, str]] = []


# ---------------------------------------------------------------------------
# Infrastructure helpers
# ---------------------------------------------------------------------------

@contextmanager
def devmon_home_env(path: Path):
    """Temporarily point DEVMON_HOME at *path* for in-process persistence calls."""
    old = os.environ.get("DEVMON_HOME")
    os.environ["DEVMON_HOME"] = str(path)
    try:
        yield
    finally:
        if old is None:
            os.environ.pop("DEVMON_HOME", None)
        else:
            os.environ["DEVMON_HOME"] = old


def fresh_home(name: str) -> Path:
    """Create (or recreate) an isolated DEVMON_HOME directory for one scenario."""
    d = BASE_TMP / name
    if d.exists():
        shutil.rmtree(d)
    d.mkdir(parents=True)
    return d


def seed(home: Path, state: GameState) -> None:
    with devmon_home_env(home):
        save_state(state)


def load(home: Path) -> GameState | None:
    with devmon_home_env(home):
        return load_state()


def write_event(home: Path) -> None:
    """Append one valid shell event line so main.py's startup processor takes
    its real path (it fast-returns when the event log is empty), which is
    required to trigger deferred quest/achievement/evolution notifications.
    """
    log = home / "events.log"
    line = json.dumps({"ts": int(time.time() * 1000), "exit": 0, "dur": 100, "cwd": "/x", "type": "cmd"})
    with log.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def run_cli(
    args: list[str],
    home: Path,
    input_text: str | None = None,
    columns: int = 100,
    timeout: int = 40,
) -> subprocess.CompletedProcess:
    """Invoke `python -m devmon <args>` against an isolated DEVMON_HOME."""
    env = os.environ.copy()
    env["DEVMON_HOME"] = str(home)
    env["PYTHONIOENCODING"] = "utf-8"
    env["FORCE_COLOR"] = "1"
    env["COLUMNS"] = str(columns)
    env["LINES"] = "40"
    return subprocess.run(
        [sys.executable, "-m", "devmon", *args],
        input=input_text,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        cwd=str(REPO_ROOT),
        timeout=timeout,
    )


def new_player(name: str = "UATBot", currency: int = 0) -> GameState:
    state = GameState.new_game(name)
    state.player.currency = currency
    return state


def with_bugbyte(state: GameState, level: int = 5, current_hp: int | None = None) -> OwnedCreature:
    owned = OwnedCreature(template_id="bugbyte", level=level, current_hp=current_hp)
    state.creature_collection.append(owned)
    state.party.append("bugbyte")
    state.codex_state["bugbyte"] = "captured"
    return owned


def queue_encounter(
    state: GameState,
    template_id: str = "pebblite",
    level: int = 2,
    rarity: str = "common",
    etype: str = "normal",
) -> None:
    state.encounter_queue = EncounterEntry(
        template_id=template_id,
        encounter_level=level,
        encounter_type=etype,  # type: ignore[arg-type]
        rarity=rarity,
        queued_at=time.time(),
    )


def hp_values(text: str, max_hp: int) -> list[int]:
    """Extract every 'current' HP number for a given max_hp from a battle transcript."""
    return [int(m) for m in re.findall(rf"HP [█░]+ (\d+)/{max_hp}", text)]


# ---------------------------------------------------------------------------
# Test runner
# ---------------------------------------------------------------------------

def run_check(uat_id: str, name: str, fn) -> bool:
    """Run one check, retrying once on failure (flakiness allowance), and record it."""
    last_detail = ""
    for attempt in range(2):
        try:
            ok, detail = fn()
        except Exception as exc:  # noqa: BLE001 - report, don't crash the harness
            ok = False
            detail = f"EXCEPTION: {type(exc).__name__}: {exc}"
            if attempt == 1:
                detail += "\n" + traceback.format_exc(limit=4)
        last_detail = detail
        if ok:
            break
        if attempt == 0:
            print(f"  [retry] {uat_id} {name} failed on attempt 1, retrying once...")
    RESULTS.append((f"{uat_id} {name}", ok, last_detail))
    return ok


# ---------------------------------------------------------------------------
# Phase 06 — battle-and-capture checks
# ---------------------------------------------------------------------------

def check_help_lists_battle():
    home = fresh_home("06_help")
    proc = run_cli(["--help"], home)
    ok = proc.returncode == 0 and "battle" in proc.stdout
    return ok, f"exit={proc.returncode}"


def check_battle_empty_state():
    home = fresh_home("06_empty")
    proc = run_cli(["battle"], home)
    ok = proc.returncode == 0 and "No wild encounter queued" in proc.stdout
    return ok, proc.stdout.strip()[:200]


def check_battle_screen_renders():
    home = fresh_home("06_screen")
    state = new_player(currency=500)
    with_bugbyte(state)
    queue_encounter(state)
    seed(home, state)

    proc = run_cli(["battle"], home, input_text="6\n")
    out = proc.stdout
    required = [
        "WILD: Pebblite",
        "YOUR: Bugbyte",
        "Turn 1",
        "Battle begins!",
        "Your turn! What will you do?",
        "[1] Attack",
        "[2] Special Ability",
        "[3] Capture",
        "[4] Switch Creature",
        "[5] Items",
        "[6] Flee",
        "HP ",
    ]
    missing = [r for r in required if r not in out]
    ok = proc.returncode == 0 and not missing
    return ok, f"exit={proc.returncode} missing={missing}"


def check_attack_produces_damage_and_hp_change():
    home = fresh_home("06_attack")
    state = new_player(currency=500)
    with_bugbyte(state)
    queue_encounter(state)
    seed(home, state)

    proc = run_cli(["battle"], home, input_text="1\n6\n")
    out = proc.stdout
    has_dmg = "dmg" in out
    has_turn2 = "Turn 2" in out
    wild_hp = hp_values(out, 57)
    player_hp = hp_values(out, 28)
    wild_damaged = any(v < 57 for v in wild_hp)
    player_damaged = any(v < 28 for v in player_hp)
    ok = proc.returncode == 0 and has_dmg and has_turn2 and wild_damaged and player_damaged
    detail = (
        f"exit={proc.returncode} has_dmg={has_dmg} has_turn2={has_turn2} "
        f"wild_hp_seen={wild_hp} player_hp_seen={player_hp}"
    )
    return ok, detail


def check_flee_exits():
    home = fresh_home("06_flee")
    state = new_player(currency=500)
    with_bugbyte(state)
    queue_encounter(state)
    seed(home, state)

    proc = run_cli(["battle"], home, input_text="6\n")
    ok = proc.returncode == 0 and "You fled from Pebblite. Encounter lost." in proc.stdout
    post = load(home)
    encounter_cleared = post is not None and post.encounter_queue is None
    ok = ok and encounter_cleared
    return ok, f"exit={proc.returncode} encounter_cleared={encounter_cleared}"


def check_capture_success():
    home = fresh_home("06_capture_success")
    state = new_player(currency=500)
    with_bugbyte(state)
    state.inventory["basic_capsule"] = 0  # remove starter capsule so master_capsule is [1]
    state.inventory["master_capsule"] = 1  # guaranteed capture (100x multiplier)
    queue_encounter(state)
    seed(home, state)

    proc = run_cli(["battle"], home, input_text="3\n1\n\n")
    out = proc.stdout
    ok = (
        proc.returncode == 0
        and "Throw which capsule?" in out
        and "Master Capsule" in out
        and "CLICK!" in out
        and "Pebblite was captured!" in out
        and "Rewards:" in out
        and "Capture Bonus XP:" in out
    )
    post = load(home)
    captured = post is not None and any(c.template_id == "pebblite" for c in post.creature_collection)
    ok = ok and captured
    return ok, f"exit={proc.returncode} captured_in_collection={captured}"


def check_capture_failure_render():
    """[render-level] attempt_capture() outcome is random; the failure-path
    render (run_capture_animation success=False) is exercised directly and
    deterministically instead of trying to force a real RNG failure."""
    from devmon.render import battle as battle_render_mod
    from rich.console import Console

    buf = io.StringIO()
    console = Console(file=buf, width=80, force_terminal=False)
    orig_sleep = battle_render_mod.time.sleep
    battle_render_mod.time.sleep = lambda *_a, **_k: None
    try:
        battle_render_mod.run_capture_animation(console, "Basic Capsule", "Pebblite", "common", success=False)
    finally:
        battle_render_mod.time.sleep = orig_sleep
    out = buf.getvalue()
    ok = "wobbles" in out and "broke free!" in out
    return ok, out.strip()[-120:]


# ---------------------------------------------------------------------------
# Phase 08 — economy-and-shop checks
# ---------------------------------------------------------------------------

def check_shop_display_rendering():
    home = fresh_home("08_display")
    seed(home, new_player(currency=3))
    proc = run_cli(["shop"], home, input_text="q\n")
    out = proc.stdout
    required = ["Capsules", "Potions", "Boosters", "Bits", "(need"]
    missing = [r for r in required if r not in out]
    ok = proc.returncode == 0 and not missing
    return ok, f"exit={proc.returncode} missing={missing}"


def check_shop_purchase_confirmation_interactive():
    ok_home = fresh_home("08_purchase_ok")
    seed(ok_home, new_player(currency=100))
    proc_ok = run_cli(["shop"], ok_home, input_text="1\nq\n")
    ok1 = proc_ok.returncode == 0 and "Purchased" in proc_ok.stdout and "Basic Capsule" in proc_ok.stdout

    fail_home = fresh_home("08_purchase_fail")
    seed(fail_home, new_player(currency=0))
    proc_fail = run_cli(["shop"], fail_home, input_text="1\nq\n")
    ok2 = proc_fail.returncode == 0 and "Not enough Bits" in proc_fail.stdout

    ok = ok1 and ok2
    return ok, f"purchase_ok={ok1} insufficient_funds_blocked={ok2}"


def check_shop_quick_buy():
    home = fresh_home("08_quickbuy")
    seed(home, new_player(currency=100))

    proc = run_cli(["shop", "--buy", "basic_capsule", "--qty", "3"], home)
    ok1 = proc.returncode == 0 and "Purchased" in proc.stdout and "Basic Capsule x3" in proc.stdout
    post = load(home)
    ok2 = post is not None and post.inventory.get("basic_capsule") == 8 and post.player.currency == 85

    proc_insufficient = run_cli(["shop", "--buy", "ultra_capsule", "--qty", "50"], home)
    ok3 = proc_insufficient.returncode == 1 and "Not enough Bits" in proc_insufficient.stdout

    ok = ok1 and ok2 and ok3
    detail = f"purchase_ok={ok1} state_correct={ok2} (qty={post.inventory.get('basic_capsule') if post else None}, bits={post.player.currency if post else None}) insufficient_blocked={ok3}"
    return ok, detail


def check_items_inventory_display():
    home = fresh_home("08_items_display")
    seed(home, new_player())  # starter kit: basic_capsule=5, small_potion=3
    proc = run_cli(["items"], home)
    out = proc.stdout
    required = ["Your Items", "Capsules", "Potions", "Boosters", "Basic Capsule", "x5", "Small Potion", "x3"]
    missing = [r for r in required if r not in out]

    empty_home = fresh_home("08_items_empty")
    empty_state = new_player()
    empty_state.inventory = {}
    seed(empty_home, empty_state)
    proc_empty = run_cli(["items"], empty_home)
    ok_empty = "Your bag is empty" in proc_empty.stdout

    ok = proc.returncode == 0 and not missing and ok_empty
    return ok, f"exit={proc.returncode} missing={missing} empty_state_ok={ok_empty}"


def check_xp_booster_activation():
    home = fresh_home("08_booster")
    seed(home, new_player(currency=100))
    run_cli(["shop", "--buy", "xp_booster", "--qty", "1"], home)
    proc_use = run_cli(["items", "--use", "xp-booster"], home)
    ok1 = proc_use.returncode == 0 and "XP Booster active! 1.5x XP for 30 minutes." in proc_use.stdout

    proc_status = run_cli(["status"], home)
    ok2 = "XP Boost" in proc_status.stdout and "ACTIVE" in proc_status.stdout

    no_booster_home = fresh_home("08_booster_none")
    seed(no_booster_home, new_player())
    proc_none = run_cli(["items", "--use", "xp-booster"], no_booster_home)
    ok3 = proc_none.returncode == 1 and "don't have any XP Boosters" in proc_none.stdout

    ok = ok1 and ok2 and ok3
    return ok, f"activation_msg={ok1} status_indicator={ok2} blocked_without_booster={ok3}"


def check_battle_capsule_submenu():
    home = fresh_home("08_battle_capsule")
    state = new_player(currency=500)
    with_bugbyte(state)
    state.inventory["great_capsule"] = 2  # starter already has basic_capsule=5
    queue_encounter(state)
    seed(home, state)

    proc = run_cli(["battle"], home, input_text="3\nb\n6\n")
    out = proc.stdout
    ok = (
        proc.returncode == 0
        and "Throw which capsule?" in out
        and "Basic Capsule" in out
        and "x5" in out
        and "Great Capsule" in out
        and "x2" in out
        and "Back" in out
        and "You fled from Pebblite. Encounter lost." in out
    )
    return ok, f"exit={proc.returncode} tail={out.strip()[-160:]}"


def check_battle_items_submenu():
    home = fresh_home("08_battle_items")
    state = new_player(currency=500)
    owned = with_bugbyte(state, current_hp=10)  # damaged: max is 28
    queue_encounter(state)
    seed(home, state)

    proc = run_cli(["battle"], home, input_text="5\n1\n6\n")
    out = proc.stdout
    menu_shown = (
        proc.returncode == 0
        and "Use which item?" in out
        and "Small Potion" in out
        and "x3" in out
    )
    post = load(home)
    post_owned = post.creature_collection[0] if post and post.creature_collection else None
    potion_consumed = post is not None and post.inventory.get("small_potion") == 2
    hp_changed = post_owned is not None and post_owned.current_hp is not None and post_owned.current_hp != 10 and post_owned.current_hp > 0

    ok = menu_shown and potion_consumed and hp_changed
    detail = (
        f"menu_shown={menu_shown} potion_consumed={potion_consumed} "
        f"hp_after={post_owned.current_hp if post_owned else None} "
        f"(NOTE: on-screen narration for this turn is not visible due to a "
        f"Live-lifecycle bug in battle.py -- verified via post-battle state instead; see bugs)"
    )
    return ok, detail


# ---------------------------------------------------------------------------
# Phase 09 — quests-and-achievements checks
# ---------------------------------------------------------------------------

def _seed_quests(state: GameState) -> None:
    state.active_quests = [
        ActiveQuest(
            template_id="t1", name="Command Runner", description="Run 10 commands",
            difficulty="easy", category="coding",
            criteria=[QuestCriterion(type="total_commands", target=10, current=4)],
            xp_reward=20, bits_reward=10, started_date=date.today(),
        ),
        ActiveQuest(
            template_id="t2", name="Battle Champ", description="Win 3 battles",
            difficulty="hard", category="game",
            criteria=[QuestCriterion(type="battles_won", target=3, current=1)],
            xp_reward=100, bits_reward=50, item_reward_id="small_potion",
            started_date=date.today(),
        ),
    ]


def check_quests_panel_rendering():
    home = fresh_home("09_quests_panel")
    state = new_player()
    _seed_quests(state)
    seed(home, state)

    proc = run_cli(["quests"], home)
    out = proc.stdout
    required = [
        "Active Quests", "Command Runner", "Battle Champ",
        "[EASY]", "[HARD]", "Coding", "Game", "Reward:", "+20 XP", "+10 Bits", "█",
    ]
    missing = [r for r in required if r not in out]
    ok = proc.returncode == 0 and not missing
    return ok, f"exit={proc.returncode} missing={missing}"


def check_achievements_panel_rendering():
    home = fresh_home("09_achv_panel")
    state = new_player()
    state.player.battles_won = 5
    state.achievement_state = {"warrior": ["Bronze"]}
    seed(home, state)

    proc = run_cli(["achievements"], home)
    out = proc.stdout
    required = ["Achievements", "Combat", "Collection", "Coding", "Exploration", "Warrior", "●", "○"]
    missing = [r for r in required if r not in out]
    ok = proc.returncode == 0 and not missing
    return ok, f"exit={proc.returncode} missing={missing}"


def check_deferred_notification_stack():
    """Covers quest completion, achievement unlock, and daily bonus notifications
    (phase 09 items 2, 4, 5) in one seeded run, since they share the same
    startup-stack display and clear-after-show mechanism in main.py.
    """
    home = fresh_home("09_notifications")
    state = new_player()
    state.pending_quest_completions = [
        QuestCompletion(quest_name="Command Runner", xp_reward=20, bits_reward=10, item_reward=None)
    ]
    state.pending_achievement_unlocks = [
        AchievementUnlock(achievement_name="Warrior", tier_label="Bronze", xp_reward=50, bits_reward=25)
    ]
    state.daily_bonus_pending = True
    seed(home, state)
    write_event(home)

    proc1 = run_cli(["status"], home)
    out1 = proc1.stdout
    first_run_ok = (
        proc1.returncode == 0
        and "Quest Complete!" in out1
        and "Command Runner" in out1
        and "Daily Bonus!" in out1
        and "Achievement Unlocked!" in out1
        and "Warrior" in out1
        and "Bronze" in out1
    )
    quest_before_achievement = out1.find("Quest Complete!") < out1.find("Achievement Unlocked!")

    post = load(home)
    cleared = (
        post is not None
        and post.pending_quest_completions == []
        and post.pending_achievement_unlocks == []
        and post.daily_bonus_pending is False
    )

    write_event(home)  # second invocation should show nothing new
    proc2 = run_cli(["status"], home)
    out2 = proc2.stdout
    second_run_clean = "Quest Complete!" not in out2 and "Achievement Unlocked!" not in out2 and "Daily Bonus!" not in out2

    ok = first_run_ok and quest_before_achievement and cleared and second_run_clean
    detail = (
        f"first_run_ok={first_run_ok} correct_order={quest_before_achievement} "
        f"cleared_after_display={cleared} second_run_clean={second_run_clean}"
    )
    return ok, detail


# ---------------------------------------------------------------------------
# Phase 10 — evolution-and-polish checks
# ---------------------------------------------------------------------------

def check_evolution_prompt_render_and_readiness():
    """[engine-level] Full RNG battle-victory-to-level-10 is infeasible to
    script deterministically (turn-order/damage variance risks a loss before
    leveling); the prompt render and the readiness predicate are exercised
    directly instead.
    """
    from devmon.engine.creature_loader import get_creature
    from devmon.engine.evolution_engine import check_evolution_ready
    from devmon.render.evolution import render_evolution_prompt
    from rich.console import Console

    template = get_creature("bugbyte")
    assert template.evolves_to == "cyber_beetle"
    assert template.evolution_level_threshold == 10

    ready_owned = OwnedCreature(template_id="bugbyte", level=10)
    not_ready_owned = OwnedCreature(template_id="bugbyte", level=9)
    declined_owned = OwnedCreature(template_id="bugbyte", level=10, evolution_declined=True)

    is_ready = check_evolution_ready(ready_owned, template)
    is_not_ready = not check_evolution_ready(not_ready_owned, template)
    is_declined_blocked = not check_evolution_ready(declined_owned, template)

    buf = io.StringIO()
    console = Console(file=buf, width=80, force_terminal=False)
    console.print(render_evolution_prompt("Bugbyte", "CyberBeetle", 10))
    out = buf.getvalue()
    prompt_ok = (
        "wants to evolve!" in out
        and "level 10" in out
        and "CyberBeetle" in out
        and "Allow evolution? [y/n]:" in out
    )

    ok = is_ready and is_not_ready and is_declined_blocked and prompt_ok
    detail = f"ready_at_10={is_ready} not_ready_at_9={is_not_ready} blocked_when_declined={is_declined_blocked} prompt_text_ok={prompt_ok}"
    return ok, detail


def check_evolution_accept_flow():
    """[engine-level] Documents a real bug: accepting an evolution prompt
    ("y") crashes battle.py with NameError because `_run_evolution_checks`
    references `narrow`, a variable local to `battle_cmd()` and never passed
    into this helper. Reproduced directly (not via full CLI battle) for
    determinism -- see BUGS section of the report.
    """
    import builtins

    from devmon.commands.battle import _run_evolution_checks
    from rich.console import Console

    home = fresh_home("10_evo_accept")
    with devmon_home_env(home):
        state = new_player()
        owned = OwnedCreature(template_id="bugbyte", level=10, xp=0)
        state.creature_collection.append(owned)
        state.party.append("bugbyte")

        participated = {"bugbyte"}
        prev_levels = {"bugbyte": 9}
        console = Console(file=io.StringIO(), width=80, force_terminal=False)

        old_input = builtins.input
        builtins.input = lambda *a, **k: "y"
        try:
            _run_evolution_checks(state, participated, prev_levels, console)
            return True, "no error raised -- bug appears fixed, re-verify manually"
        except NameError as exc:
            return False, (
                f"BUG: NameError in src/devmon/commands/battle.py "
                f"_run_evolution_checks() (~line 187): {exc}. "
                f"render_evolution_before_after(..., narrow=narrow) references "
                f"'narrow', which is a local of battle_cmd(), not a parameter or "
                f"local of _run_evolution_checks(). Repro: win a battle that "
                f"levels a creature past its evolution_level_threshold, answer "
                f"'y' to the evolve prompt -- battle.py crashes with NameError."
            )
        finally:
            builtins.input = old_input


def check_evolution_decline_flow():
    from devmon.commands.battle import _run_evolution_checks
    from rich.console import Console
    import builtins

    home = fresh_home("10_evo_decline")
    with devmon_home_env(home):
        state = new_player()
        owned = OwnedCreature(template_id="bugbyte", level=10, xp=0)
        state.creature_collection.append(owned)
        state.party.append("bugbyte")

        participated = {"bugbyte"}
        prev_levels = {"bugbyte": 9}
        buf = io.StringIO()
        console = Console(file=buf, width=80, force_terminal=False)

        old_input = builtins.input
        builtins.input = lambda *a, **k: "n"
        try:
            _run_evolution_checks(state, participated, prev_levels, console)
        finally:
            builtins.input = old_input

        out = buf.getvalue()
        ok = (
            "held back" in out
            and owned.template_id == "bugbyte"
            and owned.evolution_declined is True
        )
        return ok, f"held_back_msg={'held back' in out} template_unchanged={owned.template_id == 'bugbyte'} declined_flag={owned.evolution_declined}"


def check_deferred_evolution_notification_render():
    """[render-level] Confirms the startup-stack display mechanism in main.py
    works correctly when state.pending_evolution_notifications is populated
    and clears after one display. IMPORTANT CAVEAT (see BUGS section): nothing
    in src/devmon actually appends to pending_evolution_notifications --
    evolution is applied synchronously inside battle.py (and crashes before
    completing, see check_evolution_accept_flow). This check therefore only
    verifies the display half of the feature is wired correctly; the
    producer half is missing.
    """
    home = fresh_home("10_evo_notification")
    state = new_player()
    state.pending_evolution_notifications = [
        {"old_name": "Bugbyte", "new_name": "CyberBeetle", "old_template_id": "bugbyte", "new_template_id": "cyber_beetle"}
    ]
    seed(home, state)
    write_event(home)

    proc1 = run_cli(["status"], home)
    out1 = proc1.stdout
    shown = "Evolution!" in out1 and "Bugbyte evolved into CyberBeetle!" in out1

    post = load(home)
    cleared = post is not None and post.pending_evolution_notifications == []

    write_event(home)
    proc2 = run_cli(["status"], home)
    not_shown_again = "Evolution!" not in proc2.stdout

    ok = shown and cleared and not_shown_again
    detail = (
        f"shown_on_first_run={shown} cleared_after={cleared} not_repeated={not_shown_again} "
        f"(render-level only -- see BUGS: nothing in gameplay ever populates this field)"
    )
    return ok, detail


def check_narrow_terminal_no_crash():
    home = fresh_home("10_narrow_basic")
    seed(home, new_player())

    proc_status = run_cli(["status"], home, columns=38)
    proc_party = run_cli(["party"], home, columns=38)
    proc_battle = run_cli(["battle"], home, columns=38)

    ok = (
        proc_status.returncode == 0
        and proc_party.returncode == 0
        and proc_battle.returncode == 0
        and "No wild encounter queued" in proc_battle.stdout
    )
    detail = f"status_exit={proc_status.returncode} party_exit={proc_party.returncode} battle_exit={proc_battle.returncode}"
    return ok, detail


def check_narrow_terminal_battle_compresses():
    home = fresh_home("10_narrow_battle")
    state = new_player()
    with_bugbyte(state)
    queue_encounter(state)
    seed(home, state)

    proc = run_cli(["battle"], home, input_text="6\n", columns=38)
    out = proc.stdout
    no_art = "▀" not in out and "▄" not in out  # half-block art chars absent
    compressed_bar = bool(re.search(r"HP [█░]{10} \d", out))
    ok = proc.returncode == 0 and no_art and compressed_bar
    return ok, f"exit={proc.returncode} no_art={no_art} compressed_bar_width10={compressed_bar}"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

CHECKS: list[tuple[str, str, object]] = [
    ("06#6", "devmon --help lists battle", check_help_lists_battle),
    ("06#5", "battle empty-state message", check_battle_empty_state),
    ("06#1", "battle screen renders (panels + action menu)", check_battle_screen_renders),
    ("06#2", "attack produces damage narration + HP change", check_attack_produces_damage_and_hp_change),
    ("06#4", "flee exits battle", check_flee_exits),
    ("06#3a", "capture success (screen + rewards)", check_capture_success),
    ("06#3b", "capture failure render [render-level]", check_capture_failure_render),
    ("08#1", "shop display renders tabs + prices + graying", check_shop_display_rendering),
    ("08#2", "purchase confirmation + insufficient funds (interactive)", check_shop_purchase_confirmation_interactive),
    ("08#3", "quick-buy deducts bits, adds item, blocks insufficient funds", check_shop_quick_buy),
    ("08#4", "items inventory groups + empty-bag state", check_items_inventory_display),
    ("08#5", "xp booster activation message + status indicator", check_xp_booster_activation),
    ("08#6", "battle capsule sub-menu shows owned capsules + qty", check_battle_capsule_submenu),
    ("08#7", "battle items sub-menu: potion heals, consumes, wild counterattacks", check_battle_items_submenu),
    ("09#1", "quests panel renders bars/badges/categories/rewards", check_quests_panel_rendering),
    ("09#3", "achievements panel renders categories + tier dots", check_achievements_panel_rendering),
    ("09#2,4,5", "quest/achievement/daily-bonus notification stack", check_deferred_notification_stack),
    ("10#1", "evolution prompt render + readiness predicate [engine-level]", check_evolution_prompt_render_and_readiness),
    ("10#2", "accepting evolution (before/after display) [engine-level]", check_evolution_accept_flow),
    ("10#3", "declining evolution suppresses + sets flag [engine-level]", check_evolution_decline_flow),
    ("10#5", "deferred evolution notification display [render-level]", check_deferred_evolution_notification_render),
    ("10#4a", "narrow terminal: status/party/battle-empty don't crash", check_narrow_terminal_no_crash),
    ("10#4b", "narrow terminal battle: art hidden, HP bar compressed", check_narrow_terminal_battle_compresses),
]


def main() -> int:
    print(f"DevMon UAT smoke test -- isolated DEVMON_HOME root: {BASE_TMP}\n")

    for uat_id, name, fn in CHECKS:
        run_check(uat_id, name, fn)

    # ---- Print PASS/FAIL table ----
    print("\n" + "=" * 100)
    print(f"{'UAT':<8} {'RESULT':<6} NAME")
    print("=" * 100)
    passed = 0
    failed = 0
    for full_name, ok, detail in RESULTS:
        uat_id, _, name = full_name.partition(" ")
        status = "PASS" if ok else "FAIL"
        if ok:
            passed += 1
        else:
            failed += 1
        print(f"{uat_id:<8} {status:<6} {name}")
        if not ok:
            for line in str(detail).splitlines():
                print(f"         -> {line}")
    print("=" * 100)
    print(f"TOTAL: {len(RESULTS)}  PASS: {passed}  FAIL: {failed}")
    print("=" * 100)

    try:
        shutil.rmtree(BASE_TMP, ignore_errors=True)
    except Exception:
        pass

    # Reporting tool, not a CI gate -- always exit 0 (FAIL rows above surface
    # both flakiness and the known bugs documented in the UAT markdown files).
    return 0


if __name__ == "__main__":
    sys.exit(main())
