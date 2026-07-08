"""Shell hook snippet templates for bash, zsh, and PowerShell.

These are raw strings appended to shell rc files by the installer.
CRITICAL (SHELL-03): No Python process spawned in any hook — only
shell builtins (printf/Add-Content) write to the event log file.

D-01: Events are JSON Lines format.
D-02: Events capture ts, exit, dur, cwd, type — NO command text (privacy).
D-03: Pure shell append (printf >> file) for zero latency.
"""

# Bash and Zsh share the same hook snippet.
# In bash, preexec_functions/precmd_functions are provided by bash-preexec.
# In zsh, they are native.
# The installer adds a bash-preexec source line before this block for bash.
BASH_ZSH_HOOK_SNIPPET = """\
_devmon_preexec() {
  _DEVMON_CMD_START=$(date +%s%3N)
  # AI detection (D-04): check if command starts with known AI CLI names
  local _cmd="${1%% *}"
  case "$_cmd" in
    claude|aider|cursor|copilot)
      local _log="${DEVMON_EVENT_LOG:-$HOME/.local/share/devmon/devmon/events.log}"
      printf '{"ts":%s,"exit":0,"dur":0,"cwd":"%s","type":"ai_start"}\\n' \
        "$(date +%s%3N)" "$PWD" >> "$_log" 2>/dev/null
      ;;
  esac
  # SC6: Signal daemon that readline/command is active — do not write to terminal
  touch "${DEVMON_HOME:-$HOME/.local/share/devmon/devmon}/typing.flag" 2>/dev/null
}
_devmon_precmd() {
  local _exit=$?
  # SC6: Signal daemon that prompt is drawing — safe to write to terminal
  rm -f "${DEVMON_HOME:-$HOME/.local/share/devmon/devmon}/typing.flag" 2>/dev/null
  # Touch show signal so daemon renders for a few seconds then auto-hides
  touch "${DEVMON_HOME:-$HOME/.local/share/devmon/devmon}/indicator.show" 2>/dev/null
  local _now
  _now=$(date +%s%3N)
  local _dur=$(( _now - ${_DEVMON_CMD_START:-$_now} ))
  local _log="${DEVMON_EVENT_LOG:-$HOME/.local/share/devmon/devmon/events.log}"
  printf '{"ts":%s,"exit":%d,"dur":%d,"cwd":"%s","type":"cmd"}\\n' \\
    "$_now" "$_exit" "$_dur" "$PWD" >> "$_log" 2>/dev/null
  # Indicator daemon auto-start (Phase 11, D-02)
  local _pid_file="${DEVMON_HOME:-$HOME/.local/share/devmon/devmon}/indicator.pid"
  if [[ ! -f "$_pid_file" ]] || ! kill -0 "$(cat "$_pid_file" 2>/dev/null)" 2>/dev/null; then
    devmon indicator start >/dev/null 2>&1 &
    disown
  fi
  _DEVMON_CMD_START=
}
preexec_functions+=(_devmon_preexec)
precmd_functions+=(_devmon_precmd)\
"""

# bash-preexec source line — added before hook block for bash (Pattern 2)
BASH_PREEXEC_SOURCE = '[[ -f ~/.bash-preexec.sh ]] && source ~/.bash-preexec.sh'

# PowerShell hook (D-12, D-13, Pattern 9)
# Appended to $PROFILE by installer --powershell
POWERSHELL_HOOK_SNIPPET = """\
$script:_devmon_cmd_start = $null
$script:_devmon_in_hook = $false
function _DevmonPrePrompt {
    # Reentrancy guard: cmdlets invoked below must never re-trigger the hook
    if ($script:_devmon_in_hook) { return }
    $script:_devmon_in_hook = $true
    try {
        $exit = $LASTEXITCODE
        $now = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()
        $dur = if ($script:_devmon_cmd_start) { $now - $script:_devmon_cmd_start } else { 0 }
        $script:_devmon_cmd_start = $now
        # LOCALAPPDATA matches platformdirs.user_data_dir("devmon", "devmon"),
        # where devmon's startup backlog processor reads events from.
        $log = if ($env:DEVMON_EVENT_LOG) { $env:DEVMON_EVENT_LOG } else {
            Join-Path $env:LOCALAPPDATA 'devmon\\devmon\\events.log'
        }
        $logDir = Split-Path -Parent $log
        if (-not (Test-Path $logDir)) {
            New-Item -ItemType Directory -Path $logDir -Force -ErrorAction SilentlyContinue | Out-Null
        }
        $cwd = $PWD.Path -replace '\\\\', '/'
        $entry = "{`"ts`":$now,`"exit`":$exit,`"dur`":$dur,`"cwd`":`"$cwd`",`"type`":`"cmd`"}`n"
        try { Add-Content -Path $log -Value $entry -NoNewline -ErrorAction SilentlyContinue } catch {}
        # AI detection (D-04)
        $lastCmd = (Get-History -Count 1).CommandLine -split ' ' | Select-Object -First 1
        if ($lastCmd -in @('claude','aider','cursor','copilot')) {
            $aiEntry = "{`"ts`":$now,`"exit`":0,`"dur`":0,`"cwd`":`"$cwd`",`"type`":`"ai_start`"}`n"
            try { Add-Content -Path $log -Value $aiEntry -NoNewline -ErrorAction SilentlyContinue } catch {}
        }
        # Touch show signal so daemon renders briefly then auto-hides
        $runtimeDir = if ($env:DEVMON_HOME) { $env:DEVMON_HOME } else { Join-Path $env:TEMP 'devmon\\devmon' }
        $showFile = Join-Path $runtimeDir 'indicator.show'
        try { New-Item -ItemType Directory -Path $runtimeDir -Force -ErrorAction SilentlyContinue | Out-Null; [System.IO.File]::WriteAllText($showFile, '') } catch {}
        # Indicator daemon auto-start (Phase 11)
        $pidFile = Join-Path $runtimeDir 'indicator.pid'
        $daemonAlive = $false
        if (Test-Path $pidFile) {
            $pidVal = Get-Content $pidFile -ErrorAction SilentlyContinue
            if ($pidVal) { try { Get-Process -Id $pidVal -ErrorAction Stop | Out-Null; $daemonAlive = $true } catch {} }
        }
        if (-not $daemonAlive) {
            try { Start-Process -FilePath 'devmon' -ArgumentList 'indicator','start' -WindowStyle Hidden -ErrorAction SilentlyContinue } catch {}
        }
    } finally {
        $script:_devmon_in_hook = $false
    }
}
# Wrap the prompt function (canonical PowerShell pre-prompt hook). The previous
# PostCommandLookupAction approach used a wrong signature (it passes 2 args,
# not 4) so it silently never fired — and would have run on every command
# lookup inside every pipeline if it had.
if (-not $script:_devmon_orig_prompt) { $script:_devmon_orig_prompt = $function:prompt }
function prompt {
    _DevmonPrePrompt
    & $script:_devmon_orig_prompt
}\
"""
