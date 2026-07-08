"""devmon settings — view and change DevMon configuration.

UX (Claude's discretion per D-08): Flag-based.
  devmon settings           -> show current settings (read-only)
  devmon settings --theme X -> set theme to X and save

Valid themes: neon, classic (from render/themes.THEMES.keys())

Rarity-filtered auto-fight/auto-skip (opt-in, see engine/auto_battle.py):
  devmon settings auto-fight                          -> show current state
  devmon settings auto-fight --on/--off                -> toggle
  devmon settings auto-fight --rarities common,rare    -> set rarity list
  devmon settings auto-skip   ... (same shape)
"""
from __future__ import annotations

from typing import Optional

import typer

app = typer.Typer()

VALID_RARITIES = ["common", "uncommon", "rare", "epic", "legendary", "mythic"]


def _parse_rarities(raw: str) -> list[str]:
    """Parse a comma-separated rarity list, validating against the 5 tiers.

    Args:
        raw: Comma-separated tier string, e.g. "common,uncommon".

    Returns:
        List of lowercase, whitespace-trimmed rarity tier strings.

    Raises:
        ValueError: If any token is not a recognized rarity tier. The
            message lists the valid tiers for a helpful CLI error.
    """
    tiers = [t.strip().lower() for t in raw.split(",") if t.strip()]
    invalid = [t for t in tiers if t not in VALID_RARITIES]
    if invalid:
        raise ValueError(
            f"Unknown rarity tier(s): {', '.join(invalid)}. "
            f"Valid tiers: {', '.join(VALID_RARITIES)}"
        )
    return tiers


def _format_toggle(label: str, enabled: bool, rarities: list[str]) -> str:
    """Format a one-line toggle + rarity-list summary for display."""
    state = "on" if enabled else "off"
    tiers = ", ".join(rarities) if rarities else "none"
    return f"{label}: {state} ({tiers})"


@app.callback(invoke_without_command=True)
def settings(
    ctx: typer.Context,
    theme: Optional[str] = typer.Option(
        None,
        "--theme",
        "-t",
        help="Set color theme. Options: neon, classic",
    ),
) -> None:
    """View or change DevMon settings."""
    if ctx.invoked_subcommand is not None:
        return

    from devmon.config.loader import load_config, save_config
    from devmon.render.themes import THEMES

    cfg = load_config()

    if theme is not None:
        valid = list(THEMES.keys())
        if theme not in valid:
            typer.echo(
                f"Unknown theme '{theme}'. Valid themes: {', '.join(valid)}",
                err=True,
            )
            raise typer.Exit(1)
        cfg["ui"]["theme"] = theme
        save_config(cfg)
        typer.echo(f"Theme set to '{theme}'.")
    else:
        # Display current settings (read-only mode)
        typer.echo(f"Theme: {cfg['ui']['theme']}")
        game_cfg = cfg.get("game", {})
        typer.echo(_format_toggle(
            "Auto-fight",
            game_cfg.get("auto_fight_enabled", False),
            game_cfg.get("auto_fight_rarities", []),
        ))
        typer.echo(_format_toggle(
            "Auto-skip",
            game_cfg.get("auto_skip_enabled", False),
            game_cfg.get("auto_skip_rarities", []),
        ))
        auto_discard_state = "on" if game_cfg.get("auto_discard_enabled", False) else "off"
        auto_discard_rarities = ", ".join(game_cfg.get("auto_discard_rarities", []) or []) or "none"
        auto_discard_species = ", ".join(game_cfg.get("auto_discard_species", []) or []) or "none"
        typer.echo(
            f"Auto-discard: {auto_discard_state} "
            f"(rarities: {auto_discard_rarities}; species: {auto_discard_species})"
        )


def _auto_rule_command(
    *,
    enabled_key: str,
    rarities_key: str,
    label: str,
    on: bool,
    off: bool,
    rarities: Optional[str],
) -> None:
    """Shared implementation for `auto-fight` and `auto-skip` subcommands.

    Read-modify-write the user's config.toml (preserving other values via
    load_config()'s deep-merge + save_config()'s full write), following the
    same persistence mechanism the top-level `settings --theme` uses.
    """
    from devmon.config.loader import load_config, save_config

    if on and off:
        typer.echo("Cannot pass both --on and --off.", err=True)
        raise typer.Exit(1)

    cfg = load_config()
    game_cfg = cfg.setdefault("game", {})

    changed = False
    if on:
        game_cfg[enabled_key] = True
        changed = True
    if off:
        game_cfg[enabled_key] = False
        changed = True

    if rarities is not None:
        try:
            game_cfg[rarities_key] = _parse_rarities(rarities)
        except ValueError as e:
            typer.echo(str(e), err=True)
            raise typer.Exit(1)
        changed = True

    if changed:
        save_config(cfg)

    typer.echo(_format_toggle(
        label,
        game_cfg.get(enabled_key, False),
        game_cfg.get(rarities_key, []),
    ))


@app.command("auto-fight")
def auto_fight(
    on: bool = typer.Option(False, "--on", help="Enable auto-fight."),
    off: bool = typer.Option(False, "--off", help="Disable auto-fight."),
    rarities: Optional[str] = typer.Option(
        None,
        "--rarities",
        help="Comma-separated rarity tiers to auto-fight, e.g. common,uncommon.",
    ),
) -> None:
    """View or change rarity-filtered auto-fight settings.

    When a matching rarity spawns and auto-fight is enabled for it, the
    wild encounter is resolved automatically via a headless battle
    simulation (see engine/auto_battle.py). Auto-fight takes precedence
    over auto-skip when a rarity is enabled in both.
    """
    _auto_rule_command(
        enabled_key="auto_fight_enabled",
        rarities_key="auto_fight_rarities",
        label="Auto-fight",
        on=on,
        off=off,
        rarities=rarities,
    )


@app.command("auto-skip")
def auto_skip(
    on: bool = typer.Option(False, "--on", help="Enable auto-skip."),
    off: bool = typer.Option(False, "--off", help="Disable auto-skip."),
    rarities: Optional[str] = typer.Option(
        None,
        "--rarities",
        help="Comma-separated rarity tiers to auto-skip, e.g. common.",
    ),
) -> None:
    """View or change rarity-filtered auto-skip settings.

    When a matching rarity spawns and auto-skip is enabled for it (and
    auto-fight does not also claim it), the wild encounter is cleared
    without engaging it -- no rewards, no battle.
    """
    _auto_rule_command(
        enabled_key="auto_skip_enabled",
        rarities_key="auto_skip_rarities",
        label="Auto-skip",
        on=on,
        off=off,
        rarities=rarities,
    )


def _parse_species(raw: str) -> list[str]:
    """Parse a comma-separated species id list, validating against creature_loader.

    Args:
        raw: Comma-separated species id string, e.g. "bugbyte,ember_fox".

    Returns:
        List of lowercase, whitespace-trimmed species id strings.

    Raises:
        ValueError: If any token is not a known creature template id. The
            message lists a sample of valid ids for a helpful CLI error.
    """
    from devmon.engine.creature_loader import load_all_creatures

    ids = [t.strip().lower() for t in raw.split(",") if t.strip()]
    known = load_all_creatures()
    invalid = [t for t in ids if t not in known]
    if invalid:
        sample = ", ".join(sorted(known.keys())[:10])
        raise ValueError(
            f"Unknown creature id(s): {', '.join(invalid)}. "
            f"Valid ids include: {sample}..."
        )
    return ids


@app.command("auto-discard")
def auto_discard(
    on: bool = typer.Option(False, "--on", help="Enable auto-discard."),
    off: bool = typer.Option(False, "--off", help="Disable auto-discard."),
    rarities: Optional[str] = typer.Option(
        None,
        "--rarities",
        help="Comma-separated rarity tiers to auto-discard duplicates of, e.g. common.",
    ),
    species: Optional[str] = typer.Option(
        None,
        "--species",
        help="Comma-separated creature ids to auto-discard duplicates of, e.g. bugbyte.",
    ),
) -> None:
    """View or change opt-in duplicate-capture auto-discard settings.

    OPT-IN ONLY (hard rule): defaults to fully off with empty rarity/species
    lists. When enabled, a fresh capture of a species you already own
    converts instantly to candy instead of joining your collection IF its
    rarity is in --rarities OR its id is in --species (see
    engine/candy_engine.py's should_auto_discard). Never discards anything
    while disabled, regardless of the stored rarity/species lists.
    """
    from devmon.config.loader import load_config, save_config

    if on and off:
        typer.echo("Cannot pass both --on and --off.", err=True)
        raise typer.Exit(1)

    cfg = load_config()
    game_cfg = cfg.setdefault("game", {})

    changed = False
    if on:
        game_cfg["auto_discard_enabled"] = True
        changed = True
    if off:
        game_cfg["auto_discard_enabled"] = False
        changed = True

    if rarities is not None:
        try:
            game_cfg["auto_discard_rarities"] = _parse_rarities(rarities)
        except ValueError as e:
            typer.echo(str(e), err=True)
            raise typer.Exit(1)
        changed = True

    if species is not None:
        try:
            game_cfg["auto_discard_species"] = _parse_species(species)
        except ValueError as e:
            typer.echo(str(e), err=True)
            raise typer.Exit(1)
        changed = True

    if changed:
        save_config(cfg)

    state_label = "on" if game_cfg.get("auto_discard_enabled", False) else "off"
    rarities_label = ", ".join(game_cfg.get("auto_discard_rarities", []) or []) or "none"
    species_label = ", ".join(game_cfg.get("auto_discard_species", []) or []) or "none"
    typer.echo(
        f"Auto-discard: {state_label} "
        f"(rarities: {rarities_label}; species: {species_label})"
    )
