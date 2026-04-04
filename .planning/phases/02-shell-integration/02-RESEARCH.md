# Phase 2: Shell Integration - Research

**Researched:** 2026-04-03
**Domain:** Shell hook integration (bash/zsh/PowerShell), JSON Lines event logging, XP compounding math, streak mechanics
**Confidence:** HIGH (core shell mechanics), MEDIUM (PowerShell hook design, XP balance numbers)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Event format is JSON Lines — one JSON object per line in the event log file.
- **D-02:** Each event captures: timestamp, exit code, command duration, working directory. NO command text — privacy-conscious design. Command text is never recorded.
- **D-03:** Claude's discretion on write method (pure shell append vs named pipe). Research recommends shell append for zero latency.
- **D-04:** Claude's discretion on git commit and test pass detection without command text.
- **D-05:** Hybrid XP model with three sources: flat XP for event types, time-based XP at 5 XP/minute base with 1.2x per-minute compounding, AI task XP (tokens/duration exponential).
- **D-06:** Exponential level curve — each level requires more XP than the last.
- **D-07:** All XP rates, multipliers, and level thresholds live in config.toml under `game` section.
- **D-08:** Minimum XP threshold to qualify as a "coding day" for streak purposes.
- **D-09:** Grace period is 1 day — miss one day and streak is preserved. Miss two consecutive days and streak breaks.
- **D-10:** Claude's discretion on streak multiplier scaling curve.
- **D-11:** When streak breaks, multiplier resets fully to 1.0x.
- **D-12:** Phase 2 supports: Bash (via bash-preexec shim), Zsh (via native add-zsh-hook), PowerShell (via Set-PSReadLineOption or equivalent).
- **D-13:** Windows support via Git Bash hooks — bash hooks work inside Git Bash on Windows.
- **D-14:** Fish shell deferred — not in MVP scope.

### Claude's Discretion

- Hook write method (D-03): research recommends pure shell append (no Python, no pipes) — zero latency, maximum reliability.
- Git/test detection without command text (D-04): research recommends git native hooks + post-hoc state diffing (see Architecture Patterns).
- Streak multiplier curve shape (D-10): research recommends linear with hard cap (see Architecture Patterns).

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SHELL-01 | `devmon hook install` appends hooks to .bashrc and .zshrc without overwriting existing hooks | Hook installer pattern; idempotency via marker comments |
| SHELL-02 | Shell hooks passively track execution (exit code, duration, cwd) without blocking | Pure-shell JSON-lines append; backgrounded event write |
| SHELL-03 | Hook writes events to lightweight log file — never spawns Python process directly | Pure bash `printf` to file; no Python spawn in hook |
| SHELL-04 | `devmon hook uninstall` cleanly removes all devmon hook lines | Marker-delimited block removal; sed/awk pattern |
| TRACK-01 | Successful commands generate XP based on event type and session context | ProgressionSystem.process_events() on devmon invocation |
| TRACK-02 | Git commits detected generate bonus XP | git post-commit hook writes special event type to log |
| TRACK-03 | Test suite passes detected generate bonus XP | exit code 0 + working dir heuristics; configurable test commands |
| TRACK-04 | Session start/end tracked from hook activity | Gap-based session detection from event log timestamps |
| TRACK-05 | Daily coding streaks tracked with consecutive-day detection | DateOnly comparison on event log; last_active_date in PlayerProfile |
| TRACK-06 | Streaks apply XP multipliers up to configurable cap | ProgressionSystem streak multiplier computation |
| TRACK-07 | Streaks have grace period (streak freeze) | streak_grace_used flag in PlayerProfile; 1-day allowance |
</phase_requirements>

---

## Summary

Phase 2 is the most infrastructure-dense phase in the project. It builds two separate integration surfaces: (1) a shell bridge that writes raw events to disk without ever invoking Python, and (2) a Python-side ProgressionSystem that batch-processes those events when `devmon` is next invoked.

The critical insight from research is that these two systems must be completely decoupled — the shell side is pure POSIX shell script that appends one line to a file; the Python side reads that file on demand. This is the only approach that satisfies the zero-latency constraint (SHELL-02, SHELL-03). Python startup time alone (50–200ms for importing Typer + Rich) would make every terminal command noticeably slow.

Git and test detection without command text requires a creative solution: install a git `post-commit` hook that writes a `git_commit` event directly to the DevMon event log, and detect test runner exit codes via configurable working-directory heuristics. These are the only reliable signals available without reading command text.

**Primary recommendation:** Pure shell `printf` append to a JSON Lines event log file. No pipes, no daemons, no Python in the hook. Process the backlog synchronously on every `devmon` invocation. Install a git global hook template for git commit detection.

---

## Project Constraints (from CLAUDE.md)

- **Tech stack:** Python + Typer + Rich. No deviations.
- **Non-intrusive:** Game must never block or slow normal terminal usage. Shell hook must have zero measurable latency.
- **Persistence:** JSON file for MVP saves — already implemented in Phase 1 (save.py).
- **Terminal only:** All UI rendered in terminal via Rich. No subprocess GUI.
- **Creature identity:** Creatures are game entities — not relevant to this phase directly.
- **GSD workflow enforcement:** All file changes via GSD commands (execute-phase).
- **Architecture boundary:** Domain modules (engine/, models/, persistence/) must never import from commands/ or render/. EventBus singleton injected only at CLI layer.

---

## Standard Stack

### Core (inherited from Phase 1 — no new dependencies needed)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python | 3.12.10 (verified on this machine) | Runtime | Already in use; 3.12 is current production version |
| Typer | 0.24.1 | New `hook` subcommand | Already in pyproject.toml |
| Pydantic v2 | 2.12.x | Extend PlayerProfile + GameState | Already in pyproject.toml |
| platformdirs | 4.9.x | Event log path resolution | Already in defaults.py; _default_event_log() already uses this |

### New Phase 2 Components (pure shell, no pip install)

| Component | Type | Purpose | Notes |
|-----------|------|---------|-------|
| bash-preexec | Shell script (0.6.0) | Provides preexec/precmd for bash | NOT a pip package. Downloaded once and sourced. Already researched in STACK.md. |
| devmon hook snippet | Embedded shell string | Appended to .bashrc/.zshrc by installer | Generated by installer.py from Python template strings |
| git hook template | Shell script | Writes git_commit event to event log | Installed via `git config --global core.hooksPath` |

**No new pip dependencies required for Phase 2.** All work is Python code in new modules using existing dependencies.

### Verified Versions on This Machine

```bash
python --version   # Python 3.12.10
uv --version       # uv 0.11.3
pytest --version   # pytest 8.4.1
```

---

## Architecture Patterns

### Recommended Project Structure (new files only)

```
src/devmon/
├── shell/                         # NEW — shell bridge layer
│   ├── __init__.py
│   ├── installer.py               # hook install/uninstall logic
│   ├── hooks.py                   # hook snippet templates (Python strings)
│   └── event_reader.py            # reads + parses events.log JSON Lines
├── engine/
│   └── progression.py             # NEW — XP, session, streak logic
├── commands/
│   └── hook.py                    # NEW — `devmon hook install/uninstall` Typer command
└── models/
    └── state.py                   # EXTEND — add streak/session fields to PlayerProfile

tests/
├── test_shell_installer.py        # NEW — hook install/uninstall idempotency tests
├── test_event_reader.py           # NEW — JSON Lines parsing, malformed line handling
└── test_progression.py            # NEW — XP, streak, session logic unit tests
```

### Pattern 1: Pure Shell Event Append (SHELL-02, SHELL-03)

**What:** The hook body is a single `printf` call that appends a JSON Lines entry to the event log. No Python. No subprocess. No pipe. The shell writes directly to a file.

**When to use:** Always — this is the only approach that satisfies zero-latency.

**Hook snippet installed into .bashrc/.zshrc:**
```bash
# --- devmon hook begin ---
_devmon_preexec() {
  _DEVMON_CMD_START=$(date +%s%3N)
}
_devmon_precmd() {
  local _exit=$?
  local _now
  _now=$(date +%s%3N)
  local _dur=$(( _now - ${_DEVMON_CMD_START:-$_now} ))
  local _log="${DEVMON_EVENT_LOG:-$HOME/.local/share/devmon/devmon/events.log}"
  printf '{"ts":%s,"exit":%d,"dur":%d,"cwd":"%s","type":"cmd"}\n' \
    "$_now" "$_exit" "$_dur" "$PWD" >> "$_log" 2>/dev/null
  _DEVMON_CMD_START=
}
preexec_functions+=(_devmon_preexec)
precmd_functions+=(_devmon_precmd)
# --- devmon hook end ---
```

**Why:** `printf` to a file is a shell builtin (or near-builtin) operation — microsecond-range latency. Verified pattern used by Atuin and other shell history tools.

**Zsh note:** Identical snippet. In zsh, `preexec_functions` and `precmd_functions` are native arrays — `add-zsh-hook` can also be used (equivalent, either works).

### Pattern 2: Bash-Preexec + Starship Load Order (SHELL-01 critical)

**What:** In bash, `preexec_functions` and `precmd_functions` don't exist natively. bash-preexec provides them. Starship detects bash-preexec at init time.

**The required load order in .bashrc:**
```bash
# 1. Source bash-preexec FIRST
[[ -f ~/.bash-preexec.sh ]] && source ~/.bash-preexec.sh

# 2. DevMon hook block (appended by devmon hook install)
# --- devmon hook begin ---
# ... hook code using preexec_functions += ...
# --- devmon hook end ---

# 3. Starship LAST (detects bash-preexec and wraps its functions into the array)
eval "$(starship init bash)"
```

**Critical finding (HIGH confidence, verified from Starship source):** Starship's bash init script (`starship.bash`) explicitly detects bash-preexec by checking for `bash_preexec_imported`, `__bp_imported`, `preexec_functions`, or `precmd_functions` variables. When detected, Starship registers itself via `preexec_functions` / `precmd_functions` instead of overwriting the DEBUG trap. This means bash-preexec MUST be sourced before Starship for coexistence to work.

**DevMon installer implication:** When `devmon hook install` writes to .bashrc, it must:
1. Check if bash-preexec is already sourced; if not, add the source line first.
2. Append the devmon hook block.
3. Warn (but not fail) if Starship's eval line appears before the devmon block — user must reorder manually.

### Pattern 3: Installer Idempotency via Marker Comments (SHELL-01, SHELL-04)

**What:** The installer wraps its entire hook block in `# --- devmon hook begin ---` / `# --- devmon hook end ---` comments. Install checks for these markers before appending (prevents duplicates). Uninstall removes everything between them.

**Python installer logic:**
```python
HOOK_BEGIN = "# --- devmon hook begin ---"
HOOK_END = "# --- devmon hook end ---"

def is_installed(rc_path: Path) -> bool:
    if not rc_path.exists():
        return False
    return HOOK_BEGIN in rc_path.read_text(encoding="utf-8")

def install_hook(rc_path: Path, hook_snippet: str) -> None:
    if is_installed(rc_path):
        return  # idempotent
    rc_path.parent.mkdir(parents=True, exist_ok=True)
    with rc_path.open("a", encoding="utf-8") as f:
        f.write(f"\n{HOOK_BEGIN}\n{hook_snippet}\n{HOOK_END}\n")

def uninstall_hook(rc_path: Path) -> None:
    if not rc_path.exists():
        return
    text = rc_path.read_text(encoding="utf-8")
    # Remove everything between begin and end markers (inclusive)
    import re
    pattern = rf"\n?{re.escape(HOOK_BEGIN)}.*?{re.escape(HOOK_END)}\n?"
    cleaned = re.sub(pattern, "", text, flags=re.DOTALL)
    rc_path.write_text(cleaned, encoding="utf-8")
```

### Pattern 4: Event Log Processing on Invocation (TRACK-01 through TRACK-07)

**What:** Every `devmon` command invocation triggers event log processing as its first action. The event log is read, parsed, converted to game events, and the log is truncated (consumed). XP/streak/session state is updated and persisted.

**Why not a daemon:** A background daemon adds complexity (PID files, crash recovery, port conflicts, startup ordering). The "process on next devmon invocation" pattern is simpler, more reliable, and sufficient for this use case — the player sees results when they next interact with devmon.

**Processing flow:**
```python
# In commands/hook.py or a shared startup helper
def process_event_log(state: GameState, config: dict, log_path: Path) -> None:
    if not log_path.exists():
        return
    raw_lines = log_path.read_text(encoding="utf-8").splitlines()
    log_path.write_text("")  # truncate — events consumed
    events = []
    for line in raw_lines:
        try:
            events.append(json.loads(line.strip()))
        except json.JSONDecodeError:
            continue  # malformed lines silently skipped
    progression.process_events(state, events, config)
```

**Concurrent write safety:** Multiple shell sessions can append to events.log simultaneously. `printf >> file` is atomic for small writes on Linux/macOS (POSIX O_APPEND guarantee). On Windows/Git Bash, same behavior. Reading the file and truncating it in Python requires care — use read-then-truncate (not read-then-delete) to minimize the window for lost events.

### Pattern 5: Git Commit Detection via git Native Hook (TRACK-02)

**What:** Without command text, we cannot detect `git commit` from the shell preexec hook. The solution is to install a git `post-commit` hook that writes a `git_commit` event directly to the DevMon event log.

**Two approaches for git hook installation:**

**Option A — Global git hook template (recommended):**
```bash
# devmon hook install sets this globally:
git config --global core.hooksPath ~/.devmon-hooks/

# ~/.devmon-hooks/post-commit (written by installer):
#!/bin/sh
_log="${DEVMON_EVENT_LOG:-$HOME/.local/share/devmon/devmon/events.log}"
printf '{"ts":%s,"exit":0,"dur":0,"cwd":"%s","type":"git_commit","branch":"%s"}\n' \
  "$(date +%s%3N)" "$PWD" "$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)" \
  >> "$_log" 2>/dev/null
```

**Option B — Per-repo hook (fallback):**
When `core.hooksPath` is already set by another tool (e.g., husky), devmon cannot override it. In this case, `devmon hook install --repo` writes to `.git/hooks/post-commit` in the current repo only.

**Conflict detection:** The installer should check `git config --global core.hooksPath` before setting it and warn if already set.

### Pattern 6: Test Pass Detection via Exit Code + Heuristics (TRACK-03)

**What:** Without command text, direct test runner detection is impossible from the preexec hook. Best available approach: use a configurable list of working-directory patterns or manually-tagged events.

**Recommended design (Claude's discretion, D-04):**
1. Add a `devmon track test-pass` command that players run manually in their test aliases: `alias pytest="pytest && devmon track test-pass"`. This is explicit, zero-false-positives, and simple.
2. Alternatively: process events where `exit_code == 0` and CWD matches a project root heuristic (contains `pyproject.toml`, `package.json`, etc.) — but this generates false positives.

**Recommendation:** Implement option 1 (explicit `devmon track` subcommand). Document it as the supported pattern. This matches the privacy-first design — no command text, no heuristic guessing.

### Pattern 7: XP Compounding Formula (TRACK-01, TRACK-06)

**What:** The 1.2x-per-minute compounding creates an accelerating reward curve. Here is the concrete math:

**Time-based XP (within a session):**
```
base_rate = 5  # XP per minute (from config)
multiplier_growth = 1.2  # per continuous minute (from config)

# For minute N (0-indexed) of an unbroken session:
xp_for_minute_N = base_rate * (multiplier_growth ** N)

# Total XP for a session of M minutes:
# Sum of geometric series: base_rate * (1.2^M - 1) / (1.2 - 1)
total_session_xp = base_rate * ((1.2 ** M) - 1) / 0.2

# Example values:
# 10 min: 5 * (1.2^10 - 1) / 0.2 = 5 * (6.192 - 1) / 0.2 = 129.8 XP
# 30 min: 5 * (1.2^30 - 1) / 0.2 = 5 * (237.4 - 1) / 0.2 = 5910 XP
# 60 min: 5 * (1.2^60 - 1) / 0.2 ≈ ~2.8M XP  [INFLATION RISK]
```

**CRITICAL: 1.2x per minute compounding inflates exponentially.** A 60-minute session generates ~2.8 million XP at these rates — clearly unbalanced. The PITFALLS.md notes this. **Recommendations:**
- Apply a soft cap: the multiplier maxes out at `max_multiplier` (e.g., 3.0x) after N minutes.
- OR: interpret "1.2x compounding" as `5 * min(3.0, 1.2 ** N)` — same formula with a cap.
- OR: treat the multiplier as additive tier bonuses (minute 1-5: 1.0x, 6-15: 1.5x, 16+: 2.0x).

**Recommended implementation (Claude's discretion):**
```python
def compute_session_xp(duration_seconds: int, config: dict) -> int:
    base = config["game"].get("xp_per_minute", 5)
    growth = config["game"].get("xp_multiplier_growth", 1.2)
    cap = config["game"].get("xp_multiplier_cap", 3.0)
    minutes = duration_seconds / 60.0
    # Capped per-minute rate
    effective_multiplier = min(cap, growth ** int(minutes))
    # Accumulate minute by minute with cap
    total = 0.0
    for m in range(int(minutes)):
        total += base * min(cap, growth ** m)
    return int(total)
```

**Level curve (D-06):**
```python
def xp_for_level(level: int, config: dict) -> int:
    base = config["game"].get("xp_base_level", 100)
    exponent = config["game"].get("xp_level_exponent", 1.5)
    return int(base * (level ** exponent))
    # Level 1: 100 XP, Level 5: 559 XP, Level 10: 3162 XP, Level 20: ~17,889 XP
```

### Pattern 8: Streak Multiplier Curve (TRACK-05, TRACK-06, D-10)

**Research finding:** Linear-with-hard-cap is the industry standard for streak multipliers in productivity apps. Exponential curves create "streak hoarding" behavior where players pause the game for fear of losing a high multiplier.

**Recommended curve (Claude's discretion, D-10):**
```python
def streak_multiplier(streak_days: int, config: dict) -> float:
    per_day = config["game"].get("streak_xp_bonus_per_day", 0.05)  # +5% per day
    cap = config["game"].get("streak_multiplier_cap", 2.0)          # max 2.0x
    return min(cap, 1.0 + (streak_days * per_day))
    # Day 1: 1.05x, Day 7: 1.35x, Day 20: 2.0x (cap), Day 50+: 2.0x
```

**Grace period logic (D-09):**
```python
def update_streak(profile: PlayerProfile, today: date, min_xp: int, session_xp: int) -> None:
    last = profile.last_active_date  # Optional[date]
    if last is None:
        # First ever session
        profile.streak_count = 1
        profile.streak_grace_used = False
    elif today == last:
        pass  # Same day, no change
    elif (today - last).days == 1:
        # Consecutive day
        profile.streak_count += 1
        profile.streak_grace_used = False
    elif (today - last).days == 2 and not profile.streak_grace_used:
        # Missed one day — use grace
        profile.streak_grace_used = True
        profile.streak_count += 1  # streak continues
    else:
        # Missed 2+ days or grace already used — reset
        profile.streak_count = 1
        profile.streak_grace_used = False
    if session_xp >= min_xp:
        profile.last_active_date = today
```

### Pattern 9: PowerShell Hook Mechanism (D-12)

**Research finding (MEDIUM confidence):** PowerShell does not have a native `preexec` equivalent. Feature request [#15271](https://github.com/PowerShell/PowerShell/issues/15271) in the PowerShell project was marked as a duplicate — no native preexec planned.

**Best available mechanism:** Override the `prompt` function in `$PROFILE`. PowerShell calls `prompt` after each command completes (equivalent to `precmd`). Timing the previous command requires storing a start time, but `preexec` (before command runs) is not available.

**PowerShell hook approach:**
```powershell
# Added to $PROFILE by devmon hook install --powershell
$_devmon_cmd_start = $null

function _DevmonPrePrompt {
    $exit = $LASTEXITCODE
    $now = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()
    $dur = if ($_devmon_cmd_start) { $now - $_devmon_cmd_start } else { 0 }
    $log = if ($env:DEVMON_EVENT_LOG) { $env:DEVMON_EVENT_LOG } else { 
        "$env:APPDATA\devmon\devmon\events.log" 
    }
    $cwd = $PWD.Path -replace '\\', '/'
    $entry = "{`"ts`":$now,`"exit`":$exit,`"dur`":$dur,`"cwd`":`"$cwd`",`"type`":`"cmd`"}`n"
    Add-Content -Path $log -Value $entry -NoNewline -ErrorAction SilentlyContinue
    $_devmon_cmd_start = $null
}

# Wrap existing prompt function
$_devmon_original_prompt = (Get-Command prompt -ErrorAction SilentlyContinue)
function prompt {
    _DevmonPrePrompt
    $global:_devmon_cmd_start = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()
    if ($_devmon_original_prompt) { & $_devmon_original_prompt } else { "PS $PWD> " }
}
```

**Limitation:** PowerShell `prompt` hook fires after command completion, not before execution — so duration tracking requires start-time stored in `prompt` (which runs at the end of one command / start of next). This is the same approach used by Starship (`Invoke-Starship-PreCommand`) and Zoxide in PowerShell. Duration will be off-by-one prompt cycle but is acceptable for session-level tracking.

**Windows path for event log:** Uses `$env:APPDATA\devmon\devmon\events.log` — matches platformdirs `user_data_dir("devmon", "devmon")` on Windows.

### Pattern 10: PlayerProfile Extensions Needed

**Existing fields (from state.py — can be reused):** `streak_count`, `total_sessions`, `total_commands`.

**New fields to add to PlayerProfile:**
```python
class PlayerProfile(BaseModel):
    # ... existing fields ...
    # Phase 2 additions:
    last_active_date: Optional[str] = None    # ISO date string "2026-04-03"
    streak_grace_used: bool = False
    current_session_start: Optional[int] = None  # unix ms timestamp
    current_session_xp: int = 0
    xp_multiplier: float = 1.0               # computed from streak, not stored separately
```

**Schema version:** Adding Optional fields with defaults does NOT require a schema version bump — Pydantic v2 handles missing fields via defaults. However, note this in migrations.py as "v1 compatible".

### Anti-Patterns to Avoid

- **Spawning Python from shell hook:** Python startup (importing Typer + Rich) adds 100-500ms per command. Verified from PITFALLS.md and community reports. Never do this.
- **Raw DEBUG trap in bash:** Only one DEBUG trap can exist. Starship uses it. Using `trap ... DEBUG` directly in the hook will conflict. Always use bash-preexec's `preexec_functions` array.
- **Sourcing bash-preexec after Starship:** Starship detects bash-preexec at its own init time. If bash-preexec is sourced after `eval "$(starship init bash)"`, Starship has already fallen back to DEBUG trap mode — both will conflict.
- **FIFO/named pipe for event log:** Named pipes block on write if the reader isn't running. Pure file append is safer and faster for this use case.
- **Overwriting preexec_functions in zsh:** Use `+=` to append, never assign: `preexec_functions+=(_devmon_preexec)`.
- **Processing events in the shell hook:** The hook must only write. All game logic (XP, streak, encounters) runs in Python on the next devmon invocation.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| JSON Lines parsing | Custom line splitter | `json.loads()` per line, skip JSONDecodeError | stdlib handles edge cases; malformed lines are ignorable |
| Atomic file truncation | Custom lock mechanism | Read-then-truncate with Path.write_text("") | O_APPEND writes are atomic; truncate window is tiny; acceptable for MVP |
| bash hook detection | Custom shell type detection | `shellingham` (bundled with Typer) | Typer already bundles shellingham; `shellingham.detect_shell()` works cross-platform |
| RC file path resolution | Hardcoded `~/.bashrc` | `shellingham.detect_shell()` + known RC file map | Different shells, different RC files; shellingham already in dependency tree |
| Date arithmetic for streaks | Manual day counting | `datetime.date` arithmetic `(today - last).days` | stdlib handles DST, leap years, month boundaries |
| git hook installation | Custom git API | `subprocess.run(["git", "config", "--global", ...])` | Standard git config API; no library needed |

**Key insight:** Phase 2 adds zero new Python dependencies. Every problem is solvable with stdlib + existing Typer/platformdirs/Pydantic stack.

---

## Common Pitfalls

### Pitfall 1: bash-preexec + Starship Load Order
**What goes wrong:** Sourcing bash-preexec after `eval "$(starship init bash)"` causes Starship to fall back to DEBUG trap mode. Then bash-preexec also installs a DEBUG trap. They overwrite each other, breaking both Starship and DevMon tracking.
**Why it happens:** Starship detects bash-preexec at init time by checking for `preexec_functions` variable. If not present at that moment, Starship uses DEBUG trap instead.
**How to avoid:** installer must place bash-preexec source line BEFORE the devmon hook block, and document that Starship must be initialized AFTER both. The installer can detect if Starship is already in .bashrc and emit a warning.
**Warning signs:** XP stops generating; user reports hooks stopped working after Starship install.

### Pitfall 2: XP Compounding Inflation at Long Sessions
**What goes wrong:** 1.2x per minute compounding without a cap yields ~2.8M XP in a 60-minute session. Player hits max level in one sitting.
**Why it happens:** Geometric growth with base 1.2 reaches explosive values beyond 30 minutes.
**How to avoid:** Apply `min(cap, 1.2 ** N)` in the formula. Set `xp_multiplier_cap = 3.0` (or similar) in config defaults. This still creates the "accelerating reward" feeling early in a session while preventing inflation.
**Warning signs:** `devmon status` showing level 50+ after one coding session.

### Pitfall 3: event log Growing Unbounded
**What goes wrong:** Shell sessions write hundreds of events per day. Without consuming the log, it grows without bound. By week 2, reading and parsing a 50MB log on each `devmon` invocation adds seconds of startup latency.
**Why it happens:** Log is append-only; no cleanup mechanism.
**How to avoid:** Truncate the log immediately after reading it in `process_event_log()`. Keep a MAX_EVENTS_PER_PROCESS limit (e.g., 10,000 lines) and discard oldest if exceeded.
**Warning signs:** `devmon status` feels slow; events.log is megabytes in size.

### Pitfall 4: Concurrent Shell Sessions Race on Event Log
**What goes wrong:** Two terminal sessions write events simultaneously. Python reads the file and truncates it while the second session is mid-write, losing that session's events.
**Why it happens:** Read-truncate is not atomic.
**How to avoid:** For MVP, this is acceptable — occasional event loss in concurrent sessions is a minor issue (not data corruption). Document it. For robustness, use `os.replace()` to atomically swap: read log, rename to events.log.consumed, write new empty log. Each session's `printf >>` to events.log still works because they open a new append handle.
**Warning signs:** XP occasionally missing after a coding session.

### Pitfall 5: Hook Fires on Every Command Including `ls`, `cd`, `clear`
**What goes wrong:** The ignored_commands list in config is never applied at the shell level (it can't be — no command text). All commands generate events, even no-ops.
**Why it happens:** Privacy design (D-02) means no command text is recorded, so filtering in the hook is impossible.
**How to avoid:** Apply filtering in Python during event processing, not in the shell hook. For commands with sub-1-second duration and exit code 0, apply a minimum duration threshold (e.g., 500ms) before awarding XP. This naturally filters `ls`, `cd`, etc. without needing command text.
**Warning signs:** XP generation from trivially short commands; inflated command counts.

### Pitfall 6: PowerShell Prompt Override Clobbers Starship
**What goes wrong:** DevMon's `function prompt` override replaces the entire PowerShell prompt function, removing Starship's custom prompt.
**Why it happens:** PowerShell's prompt is a single function — last writer wins.
**How to avoid:** Capture the existing `prompt` function before overriding, then call it from within the new prompt function (see Pattern 9 above). Same pattern used by Starship itself (`Invoke-Starship-PreCommand`).
**Warning signs:** User's Starship prompt disappears after `devmon hook install --powershell`.

---

## Code Examples

### JSON Lines Event Format (D-01, D-02)

```json
{"ts":1743724800000,"exit":0,"dur":1234,"cwd":"/home/user/project","type":"cmd"}
{"ts":1743724801500,"exit":1,"dur":500,"cwd":"/home/user/project","type":"cmd"}
{"ts":1743724802000,"exit":0,"dur":0,"cwd":"/home/user/project","type":"git_commit","branch":"main"}
```

Fields:
- `ts`: Unix millisecond timestamp (integer)
- `exit`: Exit code (integer, 0 = success)
- `dur`: Duration in milliseconds (integer)
- `cwd`: Working directory (string)
- `type`: `"cmd"` | `"git_commit"` | `"test_pass"` (string)
- `branch`: (git_commit only) Current branch name

### New GameEvent Dataclasses for engine/events.py

```python
# Source: ARCHITECTURE.md Pattern 1 + Phase 2 design
@dataclass
class CommandTracked(GameEvent):
    timestamp_ms: int
    exit_code: int
    duration_ms: int
    cwd: str
    event_type: str  # "cmd" | "git_commit" | "test_pass"

@dataclass
class XPGained(GameEvent):
    amount: int
    source: str  # "session_time" | "git_commit" | "test_pass" | "flat_event"
    new_total: int

@dataclass
class SessionStarted(GameEvent):
    timestamp_ms: int

@dataclass
class SessionEnded(GameEvent):
    duration_seconds: int
    xp_earned: int

@dataclass
class StreakUpdated(GameEvent):
    streak_days: int
    multiplier: float
    grace_used: bool
```

### shell/event_reader.py Skeleton

```python
# Source: Phase 2 design based on ARCHITECTURE.md data flow
import json
from pathlib import Path

def read_and_consume(log_path: Path) -> list[dict]:
    """Read all events from log_path and truncate it atomically."""
    if not log_path.exists():
        return []
    text = log_path.read_text(encoding="utf-8")
    log_path.write_text("", encoding="utf-8")  # consume
    events = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return events
```

### hook Typer Subcommand Skeleton (commands/hook.py)

```python
# Source: Phase 2 design; follows main.py subcommand pattern
import typer
app = typer.Typer(help="Manage shell hook installation.")

@app.command()
def install(
    shell: str = typer.Option("auto", help="Shell to install for: bash, zsh, powershell, auto"),
    git: bool = typer.Option(True, help="Also install git post-commit hook"),
) -> None:
    """Install DevMon shell hooks into your shell's RC file."""
    ...

@app.command()
def uninstall(
    shell: str = typer.Option("auto", help="Shell to uninstall from: bash, zsh, powershell, auto"),
) -> None:
    """Remove DevMon shell hooks from your shell's RC file."""
    ...
```

Register in main.py:
```python
from devmon.commands import hook as hook_cmd
app.add_typer(hook_cmd.app, name="hook")
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Daemon process for shell tracking | Log-file append + batch process on invocation | ~2020 (Atuin pattern) | Simpler, zero daemon management, no port conflicts |
| DEBUG trap in bash | bash-preexec + preexec_functions array | ~2015 | Composable with Starship/Oh-My-Zsh |
| Named pipe for event IPC | Direct file append with O_APPEND | Always preferred | No blocking, no reader required |
| Fish shell event-based hooks | Same pattern, still current | 2023+ | Fish has native `fish_preexec` — safe and composable |

**Deprecated/outdated:**
- Raw `trap DEBUG` in bash hook scripts: conflicts with Starship, cannot compose. Replaced by bash-preexec.
- Spawning Python from shell preexec: documented as catastrophic for latency. Never correct.

---

## Open Questions

1. **bash-preexec global hook template path conflicts**
   - What we know: Some tools (husky, lefthook) set `git config --global core.hooksPath` to their own directory.
   - What's unclear: How common is this for DevMon's target audience? Is a per-repo fallback sufficient?
   - Recommendation: Detect existing `core.hooksPath`, emit a warning with fallback instructions. Document `devmon hook install --repo` as the escape hatch.

2. **PowerShell `function prompt` composition robustness**
   - What we know: Capturing and re-calling the original `prompt` function works in standard PowerShell. Starship uses `Invoke-Starship-PreCommand` as its hook point.
   - What's unclear: Interaction with Oh-My-Posh, which also overrides `prompt`. Multiple prompt frameworks overriding PowerShell's single prompt function may chain in unexpected ways.
   - Recommendation: Document known-compatible frameworks (Starship, vanilla PowerShell). Flag Oh-My-Posh as untested in Phase 2. Address in a follow-up if user-reported issues arise.

3. **Minimum XP threshold for a "coding day" (D-08)**
   - What we know: Threshold must be configurable (D-07). Too low = streak-gaming; too high = punishes short sessions.
   - What's unclear: What is the right default value? Needs playtesting.
   - Recommendation: Default to 50 XP (`game.streak_min_daily_xp = 50`). At 5 XP/minute base rate, this requires ~10 minutes of coding. Document as tunable.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | All Python code | Yes | 3.12.10 | — |
| uv | Build/test runner | Yes | 0.11.3 | — |
| pytest | Test suite | Yes | 8.4.1 | — |
| git | Git hook installation | Assumed (dev machine) | Not verified in env | Skip git hook, warn user |
| bash | Bash hook testing | Git Bash on Windows | Not directly available in this shell session | Test via Git Bash only |
| zsh | Zsh hook testing | Likely unavailable on Windows | Not verified | Integration tests use mock RC file; manual test on Linux/macOS |
| PowerShell | PowerShell hook testing | Windows — likely available | Not verified in session | Test via PowerShell subprocess or mock |

**Missing dependencies with no fallback:**
- None that block core implementation. All shell hook testing can use mock RC file patterns in pytest.

**Missing dependencies with fallback:**
- zsh (on this Windows machine): installer writes hook text correctly even without zsh installed. The hook snippet is a string template — no shell interpreter needed to write it. Integration test by examining the written text.
- bash (native, not Git Bash): Installer writes correctly. Functional testing of hook execution requires Git Bash.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.4.1 |
| Config file | pyproject.toml `[tool.pytest.ini_options]` |
| Quick run command | `uv run pytest tests/ -q` |
| Full suite command | `uv run pytest tests/ -v --tb=short` |

### Phase Requirements -> Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| SHELL-01 | `hook install` appends marker block to .bashrc without duplicates | unit | `pytest tests/test_shell_installer.py::test_install_is_idempotent -x` | No — Wave 0 |
| SHELL-01 | `hook install` coexists with existing Starship lines | unit | `pytest tests/test_shell_installer.py::test_install_with_starship_present -x` | No — Wave 0 |
| SHELL-02 | Hook snippet body contains no Python process spawn | unit (text check) | `pytest tests/test_shell_installer.py::test_hook_snippet_no_python_spawn -x` | No — Wave 0 |
| SHELL-03 | Hook snippet uses only `printf >>` for event writing | unit (text check) | `pytest tests/test_shell_installer.py::test_hook_snippet_uses_printf -x` | No — Wave 0 |
| SHELL-04 | `hook uninstall` removes marker block cleanly | unit | `pytest tests/test_shell_installer.py::test_uninstall_removes_block -x` | No — Wave 0 |
| TRACK-01 | process_events() awards XP for successful commands | unit | `pytest tests/test_progression.py::test_xp_awarded_for_cmd_event -x` | No — Wave 0 |
| TRACK-02 | process_events() awards bonus XP for git_commit events | unit | `pytest tests/test_progression.py::test_git_commit_bonus_xp -x` | No — Wave 0 |
| TRACK-03 | devmon track test-pass writes test_pass event to log | unit | `pytest tests/test_progression.py::test_test_pass_bonus_xp -x` | No — Wave 0 |
| TRACK-04 | Session detected from event timestamps; start/end recorded | unit | `pytest tests/test_progression.py::test_session_detection -x` | No — Wave 0 |
| TRACK-05 | Consecutive-day streak increments streak_count | unit | `pytest tests/test_progression.py::test_streak_consecutive_days -x` | No — Wave 0 |
| TRACK-06 | Streak multiplier applied to XP; capped at max | unit | `pytest tests/test_progression.py::test_streak_multiplier_capped -x` | No — Wave 0 |
| TRACK-07 | Grace period preserves streak on 1 missed day | unit | `pytest tests/test_progression.py::test_streak_grace_period -x` | No — Wave 0 |
| TRACK-07 | Streak breaks after 2 missed days | unit | `pytest tests/test_progression.py::test_streak_breaks_after_grace -x` | No — Wave 0 |
| (event log) | read_and_consume() handles malformed JSON lines | unit | `pytest tests/test_event_reader.py::test_malformed_lines_skipped -x` | No — Wave 0 |
| (event log) | read_and_consume() truncates log after reading | unit | `pytest tests/test_event_reader.py::test_log_truncated_after_read -x` | No — Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/ -q`
- **Per wave merge:** `uv run pytest tests/ -v --tb=short`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

All test files for this phase are new — none exist yet:

- [ ] `tests/test_shell_installer.py` — covers SHELL-01, SHELL-02, SHELL-03, SHELL-04
- [ ] `tests/test_event_reader.py` — covers event log read/consume/malformed-line handling
- [ ] `tests/test_progression.py` — covers TRACK-01 through TRACK-07
- [ ] `src/devmon/shell/__init__.py` — new package (no test needed)
- [ ] `src/devmon/shell/installer.py` — new module
- [ ] `src/devmon/shell/hooks.py` — new module (hook snippet templates)
- [ ] `src/devmon/shell/event_reader.py` — new module
- [ ] `src/devmon/engine/progression.py` — new module
- [ ] `src/devmon/commands/hook.py` — new module

Existing test infrastructure (`conftest.py` with `tmp_save_dir` fixture, `DEVMON_HOME` override) fully usable for Phase 2 tests.

---

## Sources

### Primary (HIGH confidence)
- [github.com/rcaloras/bash-preexec](https://github.com/rcaloras/bash-preexec) — Load order requirement ("must be last"), version 0.6.0 confirmed
- [github.com/starship/starship — starship.bash source](https://github.com/starship/starship/blob/master/src/init/starship.bash) — Confirms Starship detects bash-preexec at init time; bash-preexec must precede Starship
- [starship.rs/advanced-config/](https://starship.rs/advanced-config/) — DEBUG trap requirement; bash preexec limitation documented
- Phase 1 source code (events.py, state.py, defaults.py, save.py, main.py) — Direct inspection; all patterns verified

### Secondary (MEDIUM confidence)
- [docs.atuin.sh/cli/guide/shell-integration/](https://docs.atuin.sh/cli/guide/shell-integration/) — Confirms add-zsh-hook is the zsh standard; bash-preexec is the bash standard; PowerShell is tier-2 (not natively covered in preexec docs)
- [github.com/PowerShell/PowerShell/issues/15271](https://github.com/PowerShell/PowerShell/issues/15271) — Confirms no native preexec in PowerShell; feature request marked duplicate
- [learn.microsoft.com — Set-PSReadLineOption](https://learn.microsoft.com/en-us/powershell/module/psreadline/set-psreadlineoption) — PSReadLine options; no preexec hook parameter found
- .planning/research/PITFALLS.md — Shell hook pitfalls, XP inflation risks, streak psychology (pre-researched)
- .planning/research/ARCHITECTURE.md — Shell bridge pattern, event flow architecture
- .planning/research/STACK.md — bash-preexec 0.6.0, zsh native hooks documented

### Tertiary (LOW confidence — informational only)
- [gamedeveloper.com — XP thresholds](https://www.gamedeveloper.com/design/quantitative-design---how-to-define-xp-thresholds-) — RPG XP curve design patterns; specific numbers require playtesting to validate

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all dependencies verified in pyproject.toml; no new deps required
- Shell hook mechanism (bash/zsh): HIGH — verified from Starship source + bash-preexec docs
- PowerShell hook mechanism: MEDIUM — `function prompt` pattern confirmed by community sources; not verified against official PowerShell docs for composition guarantees
- XP formula math: HIGH — arithmetic is deterministic; balance values are LOW until playtested
- Streak logic: HIGH — date arithmetic is deterministic; threshold defaults are LOW (best-guess)
- Architecture patterns: HIGH — derived from existing codebase conventions + ARCHITECTURE.md

**Research date:** 2026-04-03
**Valid until:** 2026-07-03 (90 days — stable shell APIs, bash-preexec 0.6.0 is current)
