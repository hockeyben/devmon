# Pitfalls Research

**Domain:** Gamified CLI terminal RPG with shell hook integration (Python)
**Researched:** 2026-04-03
**Confidence:** MEDIUM — most findings verified across multiple sources; game-balance specifics are LOW (domain inference)

---

## Critical Pitfalls

### Pitfall 1: Shell Hook Conflicts with Existing Tools

**What goes wrong:**
DevMon installs a `preexec`/`postexec` hook into `.bashrc`/`.zshrc`. If the user already has Starship, Oh-My-Zsh, bash-preexec, or any prompt framework, the DEBUG trap in bash gets clobbered — silently. The hook stops firing, tracking breaks, XP stops generating, and the user has no idea why.

**Why it happens:**
Bash only supports a single DEBUG trap. Whoever sources last wins. Zsh has native `preexec`/`precmd` array hooks that compose safely, but bash requires the `bash-preexec` shim (rcaloras/bash-preexec), which also conflicts with Starship's own bash hook if load order is wrong. Fish uses `fish_preexec` / `fish_postexec` events, which are separate and safe but have their own edge cases (e.g., not firing on empty commands).

**How to avoid:**
- For bash: depend on `bash-preexec` (rcaloras) and document that it must be sourced *before* Starship. Do not install a raw DEBUG trap.
- For zsh: append to `preexec_functions` array, never overwrite the whole hook.
- For fish: use `function fish_preexec --on-event fish_preexec` — this composes correctly.
- Emit a startup diagnostic (`devmon doctor`) that checks hook health and detects conflicts.
- Keep the hook function ultra-minimal: timestamp + queue an async write. Never block.

**Warning signs:**
- XP does not generate during active shell sessions
- `devmon doctor` reports hook as unregistered
- User reports "it stopped working after I installed Starship/Oh-My-Zsh"

**Phase to address:** Shell integration phase (earliest foundation phase). Must be solved before any tracking features are built on top of it.

---

### Pitfall 2: Shell Hook Latency Killing Developer Productivity

**What goes wrong:**
Every command the user types fires the preexec hook. If the hook calls Python (spawning a new process), adds even 100-300ms of latency, and runs for every `ls` and `cd`, developers notice immediately. Measured: direnv (a shell hook tool) adds ~5ms on an M3 Max — acceptable. Python process spawn overhead alone is 50-200ms — unacceptable.

**Why it happens:**
Python's startup overhead is non-trivial. A naive implementation calls `devmon track-command "$cmd"` from the shell hook, spawning a full Python interpreter + importing Typer + importing Rich for every single terminal command. Rich alone accounts for ~85% of Typer's import time. This adds 200-800ms of command lag on every keystroke.

**How to avoid:**
- The shell hook must NEVER spawn a full Python process synchronously.
- Write to a lightweight local socket, a FIFO pipe, or append a line to a log file — all of which complete in microseconds.
- Run a background daemon (`devmon daemon`) that reads the pipe and processes events asynchronously.
- Alternatively: write raw timestamp+command to `~/.devmon/events.log` in the hook itself (pure bash, zero Python), and let the next explicit `devmon` invocation process the backlog.
- Lazy-import Rich and Typer submodules — only import what the current command needs.

**Warning signs:**
- Shell prompt feels sluggish
- `time ls` shows unexpected extra time
- Users remove the hook and disable DevMon

**Phase to address:** Shell integration phase. Establish the async write pattern before implementing any game logic that depends on tracking.

---

### Pitfall 3: Save File Corruption on Interrupted Write

**What goes wrong:**
The game writes JSON save state. The user closes the terminal, kills the process, or loses power mid-write. The JSON file ends up truncated or partially written. On next launch, `json.loads()` throws, the save is unreadable, and the user loses all progress. This is a game-ending defect for engagement.

**Why it happens:**
`open(path, 'w')` truncates the file immediately, then writes. Any interruption between truncate and flush produces a corrupt file. Developers test happy paths — they never test Ctrl+C during a save.

**How to avoid:**
- Always use atomic saves: write to `save.json.tmp`, then `os.replace('save.json.tmp', 'save.json')`. `os.replace` is atomic on POSIX and atomic-enough on Windows (Win32 MoveFileEx).
- Keep a rolling backup: `save.json` (current) + `save.json.bak` (previous successful save). On corrupt load, fall back to `.bak` and notify user.
- Embed a `schema_version` field at the top level of the JSON from day one.
- On load: catch `json.JSONDecodeError` gracefully — never crash, always offer recovery.
- Validate required top-level keys after load before trusting the data.

**Warning signs:**
- Any code path that does `open(save_path, 'w')` without a `.tmp` + rename dance
- Missing `try/except json.JSONDecodeError` on the load path
- No `schema_version` field in the save schema

**Phase to address:** Core persistence phase (before any game state is built). The atomic save pattern must be the only save pattern in the codebase.

---

### Pitfall 4: Schema Migration Neglected Until v2 Breaking Changes

**What goes wrong:**
MVP ships with a JSON save schema. v2 adds evolutions, new creature fields, regions, and streaks. Existing saves break on upgrade. Users with invested save files see an error or data loss. They quit.

**Why it happens:**
"We'll deal with migrations later" — but migrations are 10x harder when the schema has already diverged across two versions in production. No version field means there's no way to know what format an old save is in.

**How to avoid:**
- Add `"schema_version": 1` to every save file from the very first commit.
- Build a migration runner in Phase 1 even if it only has one no-op migration: `migrate_v1_to_v1`.
- Each schema change increments the version and adds a migration function. The loader auto-runs all needed migrations in sequence.
- Never remove fields — deprecate them as `null` first, remove in a later version.
- Test migrations with a corpus of old save files stored in `tests/fixtures/saves/`.

**Warning signs:**
- No `schema_version` in save file
- Schema changes made without a corresponding migration function
- No tests that load old save fixtures

**Phase to address:** Core persistence phase (MVP). Migration infrastructure must exist before the schema is used by any game feature.

---

### Pitfall 5: Rich Re-Rendering Everything Every Frame

**What goes wrong:**
Battle screens, HP bars, and encounter notifications use Rich `Live` or rapid `console.print()` calls. On slower terminals (SSH sessions, Windows Terminal, tmux), excessive ANSI escape sequence output causes visible flickering, tearing, or extreme slowness. Tmux is a particularly common environment for developers — it breaks Rich layout rendering in known ways.

**Why it happens:**
Rich's `Live` context manager is designed for this, but developers bypass it and call `console.print()` in a loop, causing full-terminal redraws. ASCII art with many lines multiplies the problem. Color support detection also fails in tmux (TERM env var is wrong), causing Rich to emit 256-color codes that tmux misinterprets.

**How to avoid:**
- Use `Rich.Live` with a `refresh_per_second` cap (8-12 fps is fine for a turn-based game, not 60).
- Respect `NO_COLOR` and `FORCE_COLOR` environment variables — Rich does this automatically, but check TERM detection in CI/tmux.
- Cap battle screen height to a fixed number of lines rather than dynamic resizing.
- Test rendering in: plain terminal, tmux, SSH session, Windows Terminal, VS Code integrated terminal.
- Provide a `--no-color` / `--plain` flag for degraded environments.

**Warning signs:**
- Flickering on fast `console.print()` calls
- Visual corruption inside tmux
- `rich.console.Console` instantiated multiple times instead of a shared singleton

**Phase to address:** Terminal UI phase. Establish a single shared `Console` instance and render strategy before building battle screens.

---

### Pitfall 6: Encounter Notifications Breaking Flow (Intrusion vs. Notification)

**What goes wrong:**
A wild creature appears mid-command. DevMon prints a banner to stdout. It interrupts a `git log`, a running `make build`, or a compiler's output, injecting game text into terminal output that isn't a TTY. The user sees garbled output in logs, piped commands, or CI. Worse, they find it annoying and uninstall.

**Why it happens:**
Detecting "is the terminal currently in use by another process" is non-trivial. Printing to stdout/stderr from a background notification mechanism corrupts any command that's still writing output. Developers also underestimate how often their terminal is non-interactive.

**How to avoid:**
- Never write encounter notifications to stdout/stderr from the hook or daemon.
- Use a postexec hook (fires after the command returns, before the next prompt) — this is the only safe window.
- Write to stderr with a distinctive prefix (or use the terminal's bell + a minimal one-liner that clears itself), and only when stdin is a TTY: `if sys.stdin.isatty()`.
- Make notification verbosity configurable: `devmon config set notifications quiet/normal/verbose`.
- The queued model (notify at next prompt, battle when ready) is correct — enforce it strictly. Never pop an encounter mid-command.

**Warning signs:**
- Notification logic firing in `preexec` instead of `postexec`
- `console.print()` without a `isatty()` guard
- Encounter trigger logic outside the safe postexec window

**Phase to address:** Shell integration + encounter system phases. The "safe notification window" rule must be documented and enforced before encounter triggers are wired up.

---

### Pitfall 7: Game Balance — XP Inflation and Encounter Rate Miscalibration

**What goes wrong:**
XP is earned for every terminal command. Developers run thousands of commands per day. Without a carefully designed rate limiter and encounter throttle, the player hits max level in the first session, encounters spam every 10 commands regardless of session depth, and the game loop collapses. Alternatively: XP is too stingy, encounters feel pointless, and players disengage because nothing meaningful happens.

**Why it happens:**
Balancing a productivity-tied XP system is qualitatively different from a normal RPG. The "player input rate" (commands/hour) is 10-100x higher than clicking in a game. Copy-paste from Pokémon-style encounter rates does not work — those assume deliberate exploration steps, not hundreds of automated test suite commands.

**How to avoid:**
- Design XP as *session-aware*, not *command-count-aware*. Meaningful events (commits, test runs, first command of session) give disproportionately more XP than raw command count.
- Cap XP per time window (e.g., max 500 XP/hour from commands alone, uncapped from quality events).
- Encounter rate should be based on *meaningful engagement time* (minutes in active session) not raw command count.
- Set encounter probability per "tick" (e.g., every ~5 minutes of active session), not per command.
- Rarity table: Common 60%, Uncommon 25%, Rare 12%, Epic 2.5%, Legendary 0.5% — test these numbers in playtesting before shipping.
- Capture rates: base rate should feel fair (not frustrating). 70-85% for weakened Commons, 10-30% for weakened Rares. Rounding errors in probability math cause reported odds to differ from actual odds — use integer math (multiply by 1000, compare to random integer).

**Warning signs:**
- XP events fired on every command with no rate limiting
- Encounter probability checked on every preexec (before rate gate)
- Max level achievable in one coding session

**Phase to address:** Game loop / balance phase. Define rate limiters before wiring XP to shell events. Treat balance as a first-class design artifact, not a post-MVP tuneup.

---

### Pitfall 8: Event Bus Becoming a God Object

**What goes wrong:**
The event-driven architecture starts clean: `CommandTracked`, `XPEarned`, `EncounterTriggered`. Within three phases, every system emits and listens to every other system's events. The event bus becomes a global mutable object that any module imports directly. Debugging a battle result requires tracing 12 event hops. New contributors can't understand the flow.

**Why it happens:**
Event-driven architecture is excellent for decoupling but creates invisible coupling via event strings. Teams add more event types for convenience without defining clear ownership. "Just emit an event" becomes the answer to every integration problem.

**How to avoid:**
- Define event ownership: each module owns exactly the events it emits. No module emits another module's events.
- Use typed event dataclasses, not raw dicts or string payloads. `@dataclass class XPEarned: amount: int source: str`
- Keep the event bus a thin dispatcher — no state, no business logic.
- Document the full event flow in a single file (`docs/event-flows.md`) before implementing. Update it when flows change.
- For MVP, prefer direct function calls between systems where the dependency is intentional. Reserve events for genuinely decoupled async flows.
- Strict rule: events flow in one direction through layers. Game state does not emit to the shell layer.

**Warning signs:**
- Any module that both emits and handles events from 3+ other modules
- Event handler functions longer than 30 lines
- `event_bus` imported in more than 5 modules

**Phase to address:** Architecture phase (earliest). Establish event ownership rules and typed event schemas before implementing any system that emits events.

---

### Pitfall 9: Streak Mechanics Triggering Shame and Abandonment

**What goes wrong:**
The streak system (coding streaks with reward multipliers) punishes users who miss a day. When the streak breaks, the psychological impact is disproportionate to the actual loss — users feel shame, and "all-or-nothing" thinking causes complete abandonment. The exact problem that breaks Duolingo-style apps.

**Why it happens:**
Streak mechanics are compelling acquisition tools but notoriously bad retention mechanics at month 2+. The overjustification effect means users who code for intrinsic enjoyment start feeling they're coding *for the streak*, not for the work — and when the streak breaks, both motivations collapse.

**How to avoid:**
- Frame streaks as bonuses, not baselines: "you earned a 3x multiplier this week" not "you lost your 47-day streak."
- Never display a "lost streak" message. Display "new streak started: day 1."
- Add streak protection items (consumables that preserve a streak through one missed day) — gives agency.
- Consider "grace periods" (streak counted if you code any 5 of 7 days) rather than strict daily chains.
- Make streak loss feel like a soft reset, not a punishment. Keep all progress (levels, creatures, items) — only the multiplier resets.

**Warning signs:**
- Prominent "streak broken" messaging in the UI
- Streak displayed as the primary metric on the home screen
- No grace period or streak-protection mechanic

**Phase to address:** Quest/achievement/progression phase. Design the streak reward model before implementing it — it's a retention risk, not a retention feature, if implemented naively.

---

### Pitfall 10: ASCII Creature Art Breaking on Non-UTF8 / Narrow Terminals

**What goes wrong:**
Creature ASCII art looks fine in the developer's iTerm2 at 220 columns. On a 80-column SSH session, lines wrap and the creature looks like random characters. On Windows with cp1252 encoding, Unicode box-drawing characters and special symbols throw `UnicodeEncodeError`. In VS Code's integrated terminal, certain ANSI codes render as literal escape sequences.

**Why it happens:**
ASCII art files are authored once at a fixed width and never tested at different terminal widths. Python's `print()` doesn't know terminal width. Rich respects terminal width, but only if the art is passed through Rich's layout system — raw strings bypass it.

**How to avoid:**
- Author all creature art at maximum 60 columns width (works in 80-column terminals with border padding).
- Use `rich.console.Console().width` to detect terminal width and conditionally abbreviate or hide art on narrow terminals.
- Store art as plain ASCII (7-bit) for the fallback tier; Unicode box art as the premium tier. Detect encoding capability at startup.
- Wrap all art output through Rich `Text` objects rather than raw print — this gets encoding handling for free.
- Test art rendering in: 80-col terminal, 40-col terminal, Windows Terminal (UTF-8 mode), VS Code.

**Warning signs:**
- Art strings wider than 60 characters
- Art rendered with `print()` instead of `console.print()`
- No terminal-width check before displaying art

**Phase to address:** Terminal UI / creature display phase. Establish the art rendering pipeline and width constraints before authoring the creature roster.

---

## Technical Debt Patterns

Shortcuts that seem reasonable but create long-term problems.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Hardcode XP values in game logic | Fast to implement | Rebalancing requires code changes; untestable without running the game | Never — use a data file or config |
| Single `save.json` with no version | Simple schema | Breaking changes require manual migration or data loss | Never — add `schema_version: 1` from day one |
| Spawn Python process from shell hook | Easiest tracking implementation | 200-800ms latency on every terminal command | Never — use async pipe/log approach |
| Multiple `Console()` instances | Convenient per-module | Inconsistent color state, duplicate output on some terminals | Never — inject a shared Console singleton |
| Raw dict events on the bus | Fast to add new events | No type checking, silent schema drift, impossible to refactor safely | Never for cross-module events — use typed dataclasses |
| `json.dump()` directly to save path | One-liner | Corrupt file on interrupt | Never — always write to `.tmp` then rename |
| Encounter rate per raw command count | Simple counter | XP inflation, max level in one session | Never for final design — acceptable as dev scaffold only |
| Hardcoded creature stats in class definitions | Quick first pass | Impossible to tune without code changes, no data-driven iteration | MVP scaffold only — move to data files before beta |

---

## Integration Gotchas

Common mistakes when connecting to the shell environment.

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| bash preexec | Installing raw DEBUG trap that conflicts with Starship | Use `bash-preexec` shim; document load order requirement |
| zsh preexec | Overwriting `preexec` function entirely | Append to `preexec_functions` array |
| fish preexec | Assuming it fires on empty commands | Guard hook body: it does not fire for empty input |
| All shells | Spawning Python process in the hook | Write to a FIFO/log from pure shell; process async |
| stdout notification | Printing to stdout from the hook | Write only in postexec window; guard with `isatty()` |
| Piped commands | Encounter notification printing into pipe output | Detect non-TTY and suppress all output |
| tmux | TERM variable set to `screen-256color`, breaking Rich color detection | Detect tmux via `$TMUX` env var and adjust Rich Console init |
| Windows | cp1252 encoding breaking Unicode art characters | Detect encoding at startup; provide ASCII-only fallback art |

---

## Performance Traps

Patterns that work fine during development but degrade user experience.

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Synchronous Python in shell hook | Shell prompt delayed 200-800ms on every command | Async write to log file or FIFO; never spawn Python in hook | Immediately — noticeable from first session |
| Eager Rich + Typer import | CLI commands take 1-2s to respond | Lazy-import Rich inside command functions; use `typer-slim` where Rich not needed | Every `devmon` invocation |
| Rapid `console.print()` in battle loop | Flickering, tearing on slow terminals | Use `Rich.Live` with capped refresh rate | SSH sessions, Windows Terminal, tmux |
| Reading entire save file on every command | Slow startup on large saves | Load lazily; cache in-memory during session | ~10KB+ save files (easily reached by week 2 of play) |
| Global mutable game state dict | Race conditions if any async patterns introduced | Use typed dataclass state objects; never mutate dict directly | When background daemon is added |
| Encounter rate checked per command | Encounter spam with power users running 500+ commands/day | Rate-gate encounters to session-time ticks, not command counts | Power developers immediately |

---

## UX Pitfalls

Common experience mistakes specific to gamified developer tools.

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Streak-loss shaming | "All-or-nothing" psychology causes abandonment | Frame as "bonus earned" not "streak lost"; soft reset messaging |
| Encounter banner during running process | Garbled terminal output; loss of trust | Only notify in postexec window; never mid-command |
| "You must battle to continue" | Blocks real work — destroys the core value prop | Queued model: notify, battle when ready, never gate workflow |
| Over-reward inflation (fast max level) | Game feels trivial; loop collapses in week one | Session-aware XP caps; meaningful events worth more than command spam |
| Under-reward stinginess (rare encounters) | Nothing ever happens; feels broken | Tune encounter rate to fire at least once per typical coding session |
| Complex install (manual shell config edit) | Adoption friction; users give up before first encounter | `devmon install` command that appends hooks automatically with clear messaging |
| Capture odds feel "rigged" | Player frustration and loss of trust | Show exact probability before capture attempt; use integer math to avoid rounding drift |
| Achievement spam (badge for everything) | Notification fatigue; achievements lose meaning | Gate achievements behind meaningful milestones; max 1-2 achievement pops per session |

---

## "Looks Done But Isn't" Checklist

Things that appear complete in happy-path testing but break in real use.

- [ ] **Shell hook installation:** Works on zsh — verify bash (bash-preexec load order), fish (event not dict), and shells with existing Starship/Oh-My-Zsh installed.
- [ ] **Save system:** JSON writes correctly in tests — verify atomic write, corrupt-file recovery, schema_version field present, backup rotation.
- [ ] **Encounter notification:** Shows in developer's terminal — verify suppressed in: non-TTY, piped output, `git log --oneline | head -5`, SSH without TTY allocation.
- [ ] **Battle screen:** Looks correct in iTerm2 — verify in tmux (80 cols), Windows Terminal, VS Code integrated terminal, narrow terminal (40 cols).
- [ ] **XP generation:** XP accrues correctly — verify rate limiting prevents max-level-in-one-session; verify `devmon` commands themselves do not generate XP (no infinite loop).
- [ ] **Schema migration:** Save loads correctly in v1 — verify migration runner exists and is tested with a v1 fixture before shipping any v2 schema change.
- [ ] **Capture probability:** Displayed odds match actual roll — verify integer math implementation, verify rounding does not produce identical results for large catch-rate ranges.
- [ ] **Startup latency:** `devmon battle` feels fast — verify import time with `python -X importtime`; Rich import alone must not block on every invocation.

---

## Recovery Strategies

When pitfalls occur despite prevention, how to recover.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Shell hook conflict destroys tracking | LOW | `devmon doctor` detects it; re-source in correct order; no data loss |
| Hook latency causing shell slowness | MEDIUM | Remove synchronous spawn; refactor to log-file write; users notice immediately if not fixed fast |
| Save file corruption | LOW (with backup) / HIGH (without) | Fall back to `.bak`; if no backup, start fresh with preserved level/XP (never silently lose everything) |
| Schema migration missing for a version | HIGH | Write retroactive migration reading all possible old fields; test against user-reported save files; ship hotfix |
| XP inflation (max level week 1) | MEDIUM | Deploy rebalance; existing players keep creatures but XP curve resets going forward; communicate transparently |
| Event bus spaghetti | HIGH | Extract explicit call graph for one system at a time; no shortcut — full refactor |
| Capture probability rounding bug | LOW | Fix integer math; ship patch; trust not permanently damaged if caught early |
| Streak shame causing abandonment | MEDIUM | Redesign streak UI to "bonus framing"; A/B test if possible; existing broken streaks auto-reset |

---

## Pitfall-to-Phase Mapping

How roadmap phases should address these pitfalls.

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Shell hook conflicts | Foundation / Shell Integration | `devmon doctor` passes on bash+Starship, zsh+Oh-My-Zsh, fish; manual test matrix |
| Hook latency | Foundation / Shell Integration | `time ls` shows <10ms overhead after hook install |
| Save corruption | Core Persistence | Unit test: kill process mid-write, verify recovery from backup |
| Schema migration neglect | Core Persistence | CI test loading `tests/fixtures/saves/v1.json` through migration runner |
| Rich re-render flickering | Terminal UI | Screenshot test in tmux at 80 cols; visual regression baseline |
| Intrusive notifications | Shell Integration + Encounter System | Test: pipe output of `ls` through devmon hook; verify no game text in pipe output |
| XP inflation / balance | Game Loop / Balance | Simulate 8-hour coding session (500 commands, 10 commits) — verify max level not reachable |
| Event bus god object | Architecture | PR review gate: no module imports `event_bus` AND dispatches to 3+ foreign systems |
| Streak shame | Quest / Progression | UX review: streak break flow shows "day 1" framing, never loss messaging |
| ASCII art breaking | Creature Display | Test matrix: 80-col terminal, 40-col terminal, Windows cp1252 encoding |

---

## Sources

- [rcaloras/bash-preexec — DEBUG trap conflicts with Starship](https://github.com/rcaloras/bash-preexec)
- [Starship advanced config — bash hook ordering](https://starship.rs/advanced-config/)
- [Shopify/hookbook — composable bash DEBUG hooks](https://github.com/Shopify/hookbook)
- [fish-shell preexec issues — empty command edge case](https://github.com/fish-shell/fish-shell/issues/8020)
- [Typer startup performance discussion — Rich import overhead](https://github.com/fastapi/typer/discussions/744)
- [Common pitfalls of JSON in Python](https://dineshkumarkb.medium.com/common-pitfalls-of-json-in-python-8b874bb4977d)
- [Save Game Best Practices — atomic writes, versioning](https://developers.meta.com/horizon/documentation/unity/ps-save-game-best-practices/)
- [Rich Textualize — tmux rendering issue](https://github.com/Textualize/rich/issues/3840)
- [Common Mistakes in Event-Driven Architecture](https://moldstud.com/articles/p-common-mistakes-in-event-driven-architecture-how-to-avoid-pitfalls-and-optimize-performance)
- [How I Failed in Event-Driven Architecture](https://medium.com/@shiiyan/how-i-failed-in-event-driven-architecture-86eb493082fa)
- [Gamification UX pitfalls — overjustification, hedonic adaptation](https://www.himumsaiddad.com/insights/gamification-trends-2024)
- [Streak psychology and abandonment — gamified productivity apps](https://www.thebrink.me/gamified-life-dark-psychology-app-addiction/)
- [RPG XP curve design — exponential coefficient mistakes](https://www.gamedeveloper.com/design/quantitative-design---how-to-define-xp-thresholds-)
- [Pokémon capture mechanics — rounding errors in probability math](https://www.dragonflycave.com/mechanics/gen-iii-iv-capturing/)
- [Zsh performance optimization — command lag measurement](https://www.dribin.org/dave/blog/archives/2024/01/01/zsh-performance/)

---
*Pitfalls research for: DevMon CLI — gamified terminal creature-collection RPG*
*Researched: 2026-04-03*
