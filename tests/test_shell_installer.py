"""Tests for shell hook installer (SHELL-01, SHELL-02, SHELL-03, SHELL-04)."""
import pytest


def test_install_appends_hook_block(tmp_rc_file):
    """SHELL-01: install_hook() appends hook block to rc file."""
    from devmon.shell.installer import install_hook, HOOK_BEGIN, HOOK_END
    install_hook(tmp_rc_file, shell="bash")
    content = tmp_rc_file.read_text(encoding="utf-8")
    assert HOOK_BEGIN in content
    assert HOOK_END in content


def test_install_is_idempotent(tmp_rc_file):
    """SHELL-01: Calling install_hook twice does not duplicate the block."""
    from devmon.shell.installer import install_hook, HOOK_BEGIN
    install_hook(tmp_rc_file, shell="bash")
    install_hook(tmp_rc_file, shell="bash")
    content = tmp_rc_file.read_text(encoding="utf-8")
    assert content.count(HOOK_BEGIN) == 1


def test_uninstall_removes_hook_block(tmp_rc_file):
    """SHELL-04: uninstall_hook() removes marker block completely."""
    from devmon.shell.installer import install_hook, uninstall_hook, HOOK_BEGIN
    install_hook(tmp_rc_file, shell="bash")
    uninstall_hook(tmp_rc_file)
    content = tmp_rc_file.read_text(encoding="utf-8")
    assert HOOK_BEGIN not in content


def test_uninstall_preserves_other_content(tmp_rc_file):
    """SHELL-04: Uninstall does not remove non-devmon lines."""
    from devmon.shell.installer import install_hook, uninstall_hook
    tmp_rc_file.write_text('export PATH="$PATH:/usr/local/bin"\n', encoding="utf-8")
    install_hook(tmp_rc_file, shell="bash")
    uninstall_hook(tmp_rc_file)
    content = tmp_rc_file.read_text(encoding="utf-8")
    assert 'export PATH' in content


def test_hook_snippet_contains_no_python_spawn(tmp_rc_file):
    """SHELL-03: The hook snippet written to rc file must not contain 'python' or 'devmon'
    as a command invocation (no Python spawn — only printf to file)."""
    from devmon.shell.installer import install_hook
    install_hook(tmp_rc_file, shell="bash")
    content = tmp_rc_file.read_text(encoding="utf-8")
    # The hook must use printf, not spawn python
    assert "printf" in content
    # Must not call python or devmon as a subprocess command in the hook
    # (devmon may appear in path strings like devmon/devmon/events.log — that is fine)
    import re
    # Check for command invocations: python/devmon at start of line or after $()
    assert not re.search(r'(?:^|\$\()\s*python\b', content, re.MULTILINE)
    assert not re.search(r'(?:^|\$\()\s*devmon\b', content, re.MULTILINE)


def test_event_log_var_in_hook_snippet(tmp_rc_file):
    """SHELL-02: Hook snippet uses DEVMON_EVENT_LOG env var for log path."""
    from devmon.shell.installer import install_hook
    install_hook(tmp_rc_file, shell="bash")
    content = tmp_rc_file.read_text(encoding="utf-8")
    assert "DEVMON_EVENT_LOG" in content


def test_is_installed_returns_false_for_empty_file(tmp_rc_file):
    """SHELL-01: is_installed() returns False when hook block is absent."""
    from devmon.shell.installer import is_installed
    assert is_installed(tmp_rc_file) is False


def test_is_installed_returns_true_after_install(tmp_rc_file):
    """SHELL-01: is_installed() returns True after install_hook() runs."""
    from devmon.shell.installer import install_hook, is_installed
    install_hook(tmp_rc_file, shell="bash")
    assert is_installed(tmp_rc_file) is True
