"""Settings screen -- mirrors commands/settings.py's read-modify-write
config pattern EXACTLY: same config.toml keys (`game.auto_fight_enabled`,
`game.auto_fight_rarities`, `game.auto_skip_enabled`, `game.auto_skip_rarities`,
`game.auto_discard_enabled`, `game.auto_discard_rarities`, `ui.animations`,
`ui.theme`), round-tripped through the same `load_config()`/`save_config()`
pair. `game.auto_discard_species` is left untouched by this screen (no
per-species picker in the UI) -- toggling rarities/enabled here never wipes
an existing species list a user set via the CLI.
"""
from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Checkbox, DataTable, Static

from devmon.config.loader import load_config, save_config

VALID_RARITIES = ["common", "uncommon", "rare", "epic", "legendary", "mythic"]


class SettingsScreen(Vertical):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._loading = False
        self._selected_skin_id = None

    def compose(self) -> ComposeResult:
        yield Static("Auto-Fight", classes="settings-heading")
        yield Checkbox("Enabled", id="auto-fight-toggle")
        with Horizontal(id="auto-fight-rarities"):
            for rarity in VALID_RARITIES:
                yield Checkbox(rarity.title(), id=f"af-{rarity}")

        yield Static("Auto-Skip", classes="settings-heading")
        yield Checkbox("Enabled", id="auto-skip-toggle")
        with Horizontal(id="auto-skip-rarities"):
            for rarity in VALID_RARITIES:
                yield Checkbox(rarity.title(), id=f"as-{rarity}")

        yield Static("Auto-Discard (duplicate captures)", classes="settings-heading")
        yield Checkbox("Enabled", id="auto-discard-toggle")
        with Horizontal(id="auto-discard-rarities"):
            for rarity in VALID_RARITIES:
                yield Checkbox(rarity.title(), id=f"ad-{rarity}")

        yield Static("Display", classes="settings-heading")
        yield Checkbox("Animations", id="animations-toggle")
        with Horizontal(id="theme-buttons"):
            yield Static("Theme:")
            for theme_name in ("neon", "classic", "monochrome", "solarized_abyss", "voidwave", "root_access", "prestige_gold"):
                yield Button(theme_name, id=f"theme-{theme_name}")

        yield Static("Skins", classes="settings-heading")
        table = DataTable(id="skins-table", cursor_type="row")
        table.add_columns("Skin", "Unlocked", "Equipped")
        yield table
        with Horizontal(id="skins-actions"):
            yield Button("Equip Selected", id="equip-skin-btn")

    # ------------------------------------------------------------------

    def refresh_data(self) -> None:
        self._loading = True
        try:
            cfg = self.app.config
            game_cfg = cfg.get("game", {})
            ui_cfg = cfg.get("ui", {})

            self.query_one("#auto-fight-toggle", Checkbox).value = bool(game_cfg.get("auto_fight_enabled", False))
            af_rarities = set(game_cfg.get("auto_fight_rarities", []) or [])
            for rarity in VALID_RARITIES:
                self.query_one(f"#af-{rarity}", Checkbox).value = rarity in af_rarities

            self.query_one("#auto-skip-toggle", Checkbox).value = bool(game_cfg.get("auto_skip_enabled", False))
            as_rarities = set(game_cfg.get("auto_skip_rarities", []) or [])
            for rarity in VALID_RARITIES:
                self.query_one(f"#as-{rarity}", Checkbox).value = rarity in as_rarities

            self.query_one("#auto-discard-toggle", Checkbox).value = bool(game_cfg.get("auto_discard_enabled", False))
            ad_rarities = set(game_cfg.get("auto_discard_rarities", []) or [])
            for rarity in VALID_RARITIES:
                self.query_one(f"#ad-{rarity}", Checkbox).value = rarity in ad_rarities

            self.query_one("#animations-toggle", Checkbox).value = bool(ui_cfg.get("animations", True))

            self._refresh_skins()
        finally:
            self._loading = False

    def _refresh_skins(self) -> None:
        from devmon.engine.skins import is_skin_unlocked, skin_catalog

        state = self.app.state
        table = self.query_one("#skins-table", DataTable)
        table.clear()
        for skin in skin_catalog():
            unlocked = is_skin_unlocked(skin, state)
            equipped = state.skins_equipped == skin.id
            table.add_row(
                skin.name,
                "Yes" if unlocked else "No",
                "Yes" if equipped else "No",
                key=skin.id,
            )

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        if event.row_key is not None:
            self._selected_skin_id = event.row_key.value

    # ------------------------------------------------------------------
    # Config read-modify-write handlers
    # ------------------------------------------------------------------

    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        if self._loading:
            return
        event.stop()
        checkbox_id = event.checkbox.id or ""

        cfg = load_config()
        game_cfg = cfg.setdefault("game", {})
        ui_cfg = cfg.setdefault("ui", {})

        if checkbox_id == "auto-fight-toggle":
            game_cfg["auto_fight_enabled"] = event.value
        elif checkbox_id == "auto-skip-toggle":
            game_cfg["auto_skip_enabled"] = event.value
        elif checkbox_id == "auto-discard-toggle":
            game_cfg["auto_discard_enabled"] = event.value
        elif checkbox_id == "animations-toggle":
            ui_cfg["animations"] = event.value
        elif checkbox_id.startswith("af-"):
            rarity = checkbox_id[len("af-"):]
            self._update_rarity_list(game_cfg, "auto_fight_rarities", rarity, event.value)
        elif checkbox_id.startswith("as-"):
            rarity = checkbox_id[len("as-"):]
            self._update_rarity_list(game_cfg, "auto_skip_rarities", rarity, event.value)
        elif checkbox_id.startswith("ad-"):
            rarity = checkbox_id[len("ad-"):]
            self._update_rarity_list(game_cfg, "auto_discard_rarities", rarity, event.value)
        else:
            return

        save_config(cfg)
        self.app.config = cfg

    @staticmethod
    def _update_rarity_list(game_cfg: dict, key: str, rarity: str, enabled: bool) -> None:
        current = list(game_cfg.get(key, []) or [])
        if enabled and rarity not in current:
            current.append(rarity)
        elif not enabled and rarity in current:
            current.remove(rarity)
        game_cfg[key] = current

    def on_button_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        button_id = event.button.id or ""
        if button_id.startswith("theme-"):
            theme_name = button_id[len("theme-"):]
            cfg = load_config()
            cfg.setdefault("ui", {})["theme"] = theme_name
            save_config(cfg)
            self.app.config = cfg
            self.app.notify(f"Theme set to {theme_name}.")
            self.app.refresh_all()
        elif button_id == "equip-skin-btn":
            self._equip_selected_skin()

    def _equip_selected_skin(self) -> None:
        if self._selected_skin_id is None:
            self.app.notify("Select a skin first.", severity="warning")
            return
        from devmon.engine.skins import equip_skin

        state = self.app.state
        success, message = equip_skin(state, self._selected_skin_id)
        if success:
            self.app.persist()
            self.app.refresh_after_mutation("settings-screen")
            self.app.notify(message)
        else:
            self.app.notify(message, severity="error")
