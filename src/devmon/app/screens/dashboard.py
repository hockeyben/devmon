"""Dashboard screen -- player identity, party HP at a glance, wild encounter."""
from __future__ import annotations

from rich import box
from rich.table import Table
from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Static

from devmon.app.util import current_theme, progress_bar


class DashboardScreen(Vertical):
    """Landing screen: identity/progression summary + party + encounter."""

    def compose(self) -> ComposeResult:
        yield Static(id="dash-identity")
        yield Static(id="dash-party")
        with Horizontal(id="dash-encounter"):
            yield Static(id="dash-encounter-art")
            with Vertical(id="dash-encounter-info-box"):
                yield Static("No wild encounter. Keep coding!", id="dash-encounter-info")
                yield Button("Fight!", id="fight-btn", variant="success", disabled=True)

    # ------------------------------------------------------------------

    def refresh_data(self) -> None:
        app = self.app
        state = app.state
        theme = current_theme()

        self.query_one("#dash-identity", Static).update(self._render_identity(state, theme))
        self.query_one("#dash-party", Static).update(self._render_party(state))

        info = self.query_one("#dash-encounter-info", Static)
        fight_btn = self.query_one("#fight-btn", Button)
        art = self.query_one("#dash-encounter-art", Static)

        entry = state.encounter_queue
        if entry is not None:
            name = entry.template_id
            try:
                from devmon.engine.creature_loader import get_creature
                template = get_creature(entry.template_id)
                name = template.name
                from devmon.render.image import render_creature_art
                art.update(render_creature_art(template.id, template.ascii_art, width=24))
            except Exception:
                art.update("")
            info.update(
                f"Wild encounter: [bold]{name}[/bold]  "
                f"Lv.{entry.encounter_level}  ({entry.rarity})"
            )
            fight_btn.disabled = False
        else:
            art.update("")
            info.update("No wild encounter. Keep coding!")
            fight_btn.disabled = True

    def _render_identity(self, state, theme: dict[str, str]) -> Text:
        from devmon.engine.auras import active_aura_names
        from devmon.engine.badges import rank_for_state
        from devmon.engine.progression import xp_within_level
        from devmon.engine.skins import equipped_skin

        cfg = self.app.config
        earned, needed = xp_within_level(state.player, cfg)

        body = Text()
        body.append(f"{state.player.name}", style="bold")
        body.append(f"  Level {state.player.level}\n")
        body.append_text(progress_bar(earned, needed, theme, width=30))
        body.append(f" {earned}/{needed} XP\n")

        try:
            rank = rank_for_state(state)
        except Exception:
            rank = "Intern"
        stars = "*" * state.player.prestige_count
        body.append(f"Rank: {rank}{(' ' + stars) if stars else ''}\n", style=theme["stat_key"])
        body.append(f"Streak: {state.player.streak_count} day(s)\n", style=theme["stat_key"])
        body.append(f"Region: {state.current_region}\n", style=theme["stat_key"])
        body.append(f"Currency: {state.player.currency} bits\n", style=theme["stat_key"])

        try:
            skin = equipped_skin(state)
            body.append(f"Skin: {skin.name}\n", style=theme["stat_key"])
        except Exception:
            pass

        try:
            auras = active_aura_names(state)
        except Exception:
            auras = []
        if auras:
            body.append("Auras: " + " ".join(f"+{a}" for a in auras) + "\n", style="green")

        return body

    def _render_party(self, state) -> Table:
        from devmon.app.util import display_name, owned_by_id
        from devmon.engine.creature_loader import get_creature
        from devmon.engine.natures import effective_max_hp

        table = Table(box=box.SIMPLE_HEAD, title="Party", expand=False)
        table.add_column("Slot")
        table.add_column("Name")
        table.add_column("HP")
        table.add_column("Status")

        by_id = owned_by_id(state)
        if not state.party:
            table.add_row("-", "[dim](empty)[/dim]", "-", "-")
            return table

        for i, tid in enumerate(state.party, start=1):
            owned = by_id.get(tid)
            if owned is None:
                table.add_row(str(i), "[dim](empty)[/dim]", "-", "-")
                continue
            try:
                template = get_creature(tid)
            except Exception:
                table.add_row(str(i), tid, "-", "-")
                continue
            max_hp = effective_max_hp(template, owned.level, owned.ivs.get("hp", 0), owned.nature)
            current_hp = owned.current_hp if owned.current_hp is not None else max_hp
            status = "FAINTED" if owned.is_fainted else "OK"
            table.add_row(
                str(i),
                display_name(owned, template),
                f"{current_hp}/{max_hp}",
                status,
            )
        return table

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "fight-btn":
            event.stop()
            self.app.action_fight()
