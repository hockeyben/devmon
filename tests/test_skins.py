"""Phase E: terminal skins tests -- catalog, unlock matrix, equip, and
theme/accent/particle resolution, plus notification queueing.
"""
from __future__ import annotations

import json
import time

from devmon.models.state import GameState


# ---------------------------------------------------------------------------
# Catalog
# ---------------------------------------------------------------------------

class TestSkinCatalog:
    def test_catalog_has_six_skins(self):
        from devmon.engine.skins import skin_catalog

        catalog = skin_catalog()
        assert len(catalog) == 6
        ids = {s.id for s in catalog}
        assert ids == {
            "neon", "monochrome", "solarized_abyss", "voidwave",
            "root_access", "prestige_gold",
        }

    def test_neon_is_always_type(self):
        from devmon.engine.skins import get_skin

        assert get_skin("neon").unlock_type == "always"

    def test_get_skin_unknown_id_raises(self):
        import pytest

        from devmon.engine.skins import get_skin

        with pytest.raises(KeyError):
            get_skin("does_not_exist")


# ---------------------------------------------------------------------------
# Unlock matrix -- one test per skin's unlock condition
# ---------------------------------------------------------------------------

class TestUnlockMatrix:
    def test_neon_always_unlocked(self):
        from devmon.engine.skins import get_skin, is_skin_unlocked

        state = GameState.new_game("Tester")
        assert is_skin_unlocked(get_skin("neon"), state) is True

    def test_monochrome_locked_without_badge_unlocked_with_it(self):
        from devmon.engine.skins import get_skin, is_skin_unlocked

        skin = get_skin("monochrome")
        state = GameState.new_game("Tester")
        assert is_skin_unlocked(skin, state) is False

        state.badges_earned.append("terminal_veteran")
        assert is_skin_unlocked(skin, state) is True

    def test_solarized_abyss_locked_until_kernel_depths_reached(self):
        from devmon.engine.regions import unlock_level
        from devmon.engine.skins import get_skin, is_skin_unlocked

        skin = get_skin("solarized_abyss")
        state = GameState.new_game("Tester")
        state.player.level = 1
        assert is_skin_unlocked(skin, state) is False

        state.player.level = unlock_level("kernel_depths")
        assert is_skin_unlocked(skin, state) is True

    def test_voidwave_locked_until_voidnet_reached(self):
        from devmon.engine.regions import unlock_level
        from devmon.engine.skins import get_skin, is_skin_unlocked

        skin = get_skin("voidwave")
        state = GameState.new_game("Tester")
        state.player.level = 1
        assert is_skin_unlocked(skin, state) is False

        state.player.level = unlock_level("voidnet")
        assert is_skin_unlocked(skin, state) is True

    def test_root_access_locked_until_any_mythic_owned(self):
        from devmon.models.creature import OwnedCreature
        from devmon.engine.skins import get_skin, is_skin_unlocked

        skin = get_skin("root_access")
        state = GameState.new_game("Tester")
        assert is_skin_unlocked(skin, state) is False

        state.creature_collection.append(OwnedCreature(template_id="singulon", level=90))
        assert is_skin_unlocked(skin, state) is True

    def test_prestige_gold_locked_until_first_prestige(self):
        from devmon.engine.skins import get_skin, is_skin_unlocked

        skin = get_skin("prestige_gold")
        state = GameState.new_game("Tester")
        assert is_skin_unlocked(skin, state) is False

        state.player.prestige_count = 1
        assert is_skin_unlocked(skin, state) is True


# ---------------------------------------------------------------------------
# check_skin_unlocks: grants + queues notifications, idempotent
# ---------------------------------------------------------------------------

class TestCheckSkinUnlocks:
    def test_newly_satisfied_skin_is_granted_and_queued(self):
        from devmon.engine.skins import check_skin_unlocks

        state = GameState.new_game("Tester")
        state.player.prestige_count = 1

        check_skin_unlocks(state)

        assert "prestige_gold" in state.skins_owned
        assert len(state.pending_skin_unlocks) == 1
        assert state.pending_skin_unlocks[0].skin_id == "prestige_gold"
        assert state.pending_skin_unlocks[0].skin_name == "Prestige Gold"

    def test_second_call_does_not_re_grant_or_re_queue(self):
        from devmon.engine.skins import check_skin_unlocks

        state = GameState.new_game("Tester")
        state.player.prestige_count = 1
        check_skin_unlocks(state)
        state.pending_skin_unlocks = []  # simulate notification consumed

        check_skin_unlocks(state)

        assert state.skins_owned.count("prestige_gold") == 1
        assert state.pending_skin_unlocks == []

    def test_multiple_conditions_satisfied_at_once_grants_all(self):
        from devmon.models.creature import OwnedCreature
        from devmon.engine.regions import unlock_level
        from devmon.engine.skins import check_skin_unlocks

        state = GameState.new_game("Tester")
        state.player.level = unlock_level("voidnet")
        state.player.prestige_count = 1
        state.badges_earned.append("terminal_veteran")
        state.creature_collection.append(OwnedCreature(template_id="rootd", level=90))

        check_skin_unlocks(state)

        granted = set(state.skins_owned)
        assert {"monochrome", "solarized_abyss", "voidwave", "root_access", "prestige_gold"} <= granted
        queued_ids = {u.skin_id for u in state.pending_skin_unlocks}
        assert queued_ids == {"monochrome", "solarized_abyss", "voidwave", "root_access", "prestige_gold"}

    def test_unlock_hint_names_the_equip_command(self):
        from devmon.engine.skins import unlock_hint

        assert unlock_hint("voidwave") == "devmon skins equip voidwave"


# ---------------------------------------------------------------------------
# Equip
# ---------------------------------------------------------------------------

class TestEquipSkin:
    def test_cannot_equip_a_locked_skin(self):
        from devmon.engine.skins import equip_skin

        state = GameState.new_game("Tester")
        success, message = equip_skin(state, "voidwave")

        assert success is False
        assert "not unlocked" in message.lower()
        assert state.skins_equipped == "neon"

    def test_can_equip_an_owned_skin(self):
        from devmon.engine.skins import check_skin_unlocks, equip_skin

        state = GameState.new_game("Tester")
        state.player.prestige_count = 1
        check_skin_unlocks(state)

        success, message = equip_skin(state, "prestige_gold")

        assert success is True
        assert "Prestige Gold" in message
        assert state.skins_equipped == "prestige_gold"

    def test_equip_unknown_skin_fails(self):
        from devmon.engine.skins import equip_skin

        state = GameState.new_game("Tester")
        success, message = equip_skin(state, "not_a_real_skin")

        assert success is False
        assert "unknown" in message.lower()

    def test_equipped_skin_returns_current_definition(self):
        from devmon.engine.skins import check_skin_unlocks, equip_skin, equipped_skin

        state = GameState.new_game("Tester")
        state.player.prestige_count = 1
        check_skin_unlocks(state)
        equip_skin(state, "prestige_gold")

        assert equipped_skin(state).id == "prestige_gold"

    def test_equipped_skin_falls_back_to_neon_on_corrupt_id(self):
        from devmon.engine.skins import equipped_skin

        state = GameState.new_game("Tester")
        state.skins_equipped = "some_deleted_skin"

        assert equipped_skin(state).id == "neon"


# ---------------------------------------------------------------------------
# Theme / accent / particle resolution
# ---------------------------------------------------------------------------

class TestSkinResolution:
    def test_every_skin_theme_variant_resolves_to_a_full_theme_dict(self):
        from devmon.engine.skins import skin_catalog
        from devmon.render.themes import get_theme

        required_keys = {
            "border", "title", "level", "xp_bar", "xp_complete",
            "stat_key", "stat_value", "levelup_border", "levelup_text",
        }
        for skin in skin_catalog():
            theme = get_theme(skin.theme_variant)
            assert required_keys <= theme.keys(), (
                f"{skin.id}'s theme_variant {skin.theme_variant!r} is missing keys"
            )

    def test_theme_variant_is_not_silently_aliased_to_neon(self):
        """Regression guard: get_theme() falls back to 'neon' for any name
        not in THEME_ALIASES -- every skin's theme_variant must have its own
        alias entry or it would silently render as Neon."""
        from devmon.engine.skins import skin_catalog
        from devmon.render.themes import THEMES

        for skin in skin_catalog():
            if skin.id == "neon":
                continue
            assert THEMES[skin.theme_variant] != THEMES["neon"] or skin.theme_variant == "neon", (
                f"{skin.id}'s theme_variant resolves identically to neon -- check THEME_ALIASES"
            )

    def test_every_skin_statusline_accent_resolves_to_an_ansi_code(self):
        from devmon.commands.statusline import _accent_code
        from devmon.engine.skins import skin_catalog

        for skin in skin_catalog():
            code = _accent_code(skin.statusline_accent)
            assert code.startswith("\033["), f"{skin.id}'s accent did not resolve to an SGR code"

    def test_unknown_accent_name_falls_back_to_bright_yellow(self):
        from devmon.commands.statusline import _BRIGHT_YELLOW, _accent_code

        assert _accent_code("not_a_real_color") == _BRIGHT_YELLOW
        assert _accent_code(None) == _BRIGHT_YELLOW

    def test_neon_has_no_particles_voidwave_does(self):
        from devmon.engine.skins import get_skin

        assert get_skin("neon").particle_style == []
        assert len(get_skin("voidwave").particle_style) > 0

    def test_particle_glyphs_are_width_safe(self):
        from devmon.engine.skins import skin_catalog

        for skin in skin_catalog():
            for glyph in skin.particle_style:
                assert len(glyph) == 1
                assert ord(glyph) < 0x2600


# ---------------------------------------------------------------------------
# Particle sprinkling actually reaches the animation frames
# ---------------------------------------------------------------------------

class _FixedRNG:
    """Deterministic stand-in for the stdlib `random` module -- always
    "hits" the sprinkle chance and always picks the first glyph."""

    def random(self) -> float:
        return 0.0

    def choice(self, seq):
        return list(seq)[0]


class TestParticleSprinkling:
    def test_sprinkle_particles_is_noop_without_glyphs(self):
        from devmon.render.animation import _sprinkle_particles

        rows = [[(" ", None), (" ", None)]]
        result = _sprinkle_particles(rows, None)
        assert result == rows

    def test_sprinkle_particles_replaces_blank_cells_only(self):
        from devmon.render.animation import _sprinkle_particles

        rows = [[(" ", None), ("X", None), (" ", None)]]
        result = _sprinkle_particles(rows, ["~"], density=1.0, rng=_FixedRNG())

        assert result[0][1] == ("X", None)  # opaque cell untouched
        assert result[0][0][0] == "~"
        assert result[0][2][0] == "~"

    def test_entrance_frames_particles_are_a_pure_noop_by_default(self, monkeypatch):
        """Passing particles=None (every pre-Phase-E call site) must produce
        byte-identical frames to the pre-Phase-E behavior."""
        from devmon.render.animation import entrance_frames

        rows = [[(" ", None) for _ in range(4)] for _ in range(4)]
        width = 4

        without = entrance_frames(rows, steps=2, particles=None)
        assert len(without) == 2
        # Final frame is always the untouched full reveal.
        assert without[-1]._rows == rows

    def test_entrance_frames_sprinkle_particles_into_hidden_rows(self, monkeypatch):
        import devmon.render.animation as animation_mod

        monkeypatch.setattr(animation_mod, "_random_module", _FixedRNG())

        rows = [[(" ", None) for _ in range(4)] for _ in range(4)]
        frames = animation_mod.entrance_frames(rows, steps=4, particles=["~"])

        # At least one non-final frame should contain the particle glyph.
        assert any(
            any(cell[0] == "~" for row in f._rows for cell in row)
            for f in frames[:-1]
        )
        # The final (fully revealed) frame stays clean.
        assert not any(cell[0] == "~" for row in frames[-1]._rows for cell in row)

    def test_flash_frames_sprinkle_particles_into_bright_frame_only(self, monkeypatch):
        import devmon.render.animation as animation_mod

        monkeypatch.setattr(animation_mod, "_random_module", _FixedRNG())

        rows = [[(" ", None) for _ in range(4)] for _ in range(4)]
        frames = animation_mod.flash_frames(rows, pulses=1, particles=["*"])

        bright_frame, settle_frame = frames[0], frames[1]
        assert any(cell[0] == "*" for row in bright_frame._rows for cell in row)
        assert not any(cell[0] == "*" for row in settle_frame._rows for cell in row)


# ---------------------------------------------------------------------------
# CLI-level integration: skin unlock notification prints and clears
# ---------------------------------------------------------------------------

class TestSkinUnlockNotificationIntegration:
    def test_unlocking_a_skin_prints_notification_and_clears_pending(self, tmp_save_dir):
        from devmon.main import app
        from devmon.persistence.save import load as load_state, save as save_state
        from typer.testing import CliRunner

        state = GameState.new_game("Tester")
        state.player.prestige_count = 1  # satisfies prestige_gold's unlock
        save_state(state)

        log_path = tmp_save_dir / "events.log"
        event = {
            "ts": int(time.time() * 1000), "exit": 0, "dur": 0,
            "cwd": str(tmp_save_dir), "type": "cmd",
        }
        log_path.write_text(json.dumps(event) + "\n", encoding="utf-8")

        runner = CliRunner()
        result = runner.invoke(app, ["status"])

        assert result.exit_code == 0
        assert "Skin unlocked: Prestige Gold" in result.output
        assert "devmon skins equip prestige_gold" in result.output

        reloaded = load_state()
        assert "prestige_gold" in reloaded.skins_owned
        assert reloaded.pending_skin_unlocks == []


# ---------------------------------------------------------------------------
# battle_accent (dungeon-system plan) -- dungeon theme override during a run
# ---------------------------------------------------------------------------

class TestBattleAccent:
    def test_battle_accent_uses_equipped_skin_outside_dungeon(self, tmp_save_dir):
        from devmon.engine.skins import battle_accent, equipped_skin

        state = GameState.new_game("Ash")
        expected = equipped_skin(state).statusline_accent
        assert battle_accent(state) == expected

    def test_battle_accent_uses_dungeon_theme_when_run_active(self, tmp_save_dir):
        from devmon.engine.dungeons import enter_dungeon
        from devmon.engine.skins import battle_accent

        state = GameState.new_game("Ash")
        state.player.level = 5
        state.quest_log["termina_meadows_01"] = "complete"
        enter_dungeon(state, "termina_meadows_story")
        assert battle_accent(state) == "green"

    def test_battle_accent_reverts_after_dungeon_clears(self, tmp_save_dir):
        from devmon.engine.dungeons import advance_dungeon_room, enter_dungeon
        from devmon.engine.skins import battle_accent, equipped_skin
        from devmon.models.dungeon import DungeonRunState

        state = GameState.new_game("Ash")
        state.player.level = 5
        state.quest_log["termina_meadows_01"] = "complete"
        state.dungeon_run = DungeonRunState(
            dungeon_id="termina_meadows_story", current_room=3, started_at="2026-01-01T00:00:00"
        )
        enter_dungeon(state, "termina_meadows_story")
        advance_dungeon_room(state)  # boss clear -- dungeon_run becomes None
        assert state.dungeon_run is None
        assert battle_accent(state) == equipped_skin(state).statusline_accent
