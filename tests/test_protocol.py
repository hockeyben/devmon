"""Tests for `devmon protocol` (devmon:// URL scheme registration, Windows).

All winreg calls are monkeypatched with a MagicMock -- these tests must
never touch the real Windows registry.
"""
from __future__ import annotations

from unittest.mock import MagicMock

from typer.testing import CliRunner


class TestProtocolInstall:
    def test_install_registers_expected_registry_values(self, monkeypatch):
        from devmon.commands import protocol as protocol_cmd

        fake_winreg = MagicMock()
        fake_winreg.HKEY_CURRENT_USER = "HKCU_SENTINEL"
        fake_winreg.REG_SZ = 1
        fake_key_cm = MagicMock()
        fake_key_cm.__enter__ = MagicMock(return_value="FAKE_KEY_HANDLE")
        fake_key_cm.__exit__ = MagicMock(return_value=False)
        fake_winreg.CreateKey.return_value = fake_key_cm

        monkeypatch.setattr(protocol_cmd, "winreg", fake_winreg)
        # Deterministic launch command regardless of what's actually on this
        # machine's PATH: force the powershell.exe fallback branch.
        monkeypatch.setattr(protocol_cmd.shutil, "which", lambda name: None)

        runner = CliRunner()
        result = runner.invoke(protocol_cmd.app, ["install"])

        assert result.exit_code == 0, result.output
        assert "registered" in result.output.lower()

        created_paths = [c.args[1] for c in fake_winreg.CreateKey.call_args_list]
        assert protocol_cmd._KEY_PATH in created_paths
        assert protocol_cmd._COMMAND_KEY_PATH in created_paths

        default_value_calls = [c for c in fake_winreg.SetValueEx.call_args_list if c.args[1] is None]
        default_values = [c.args[-1] for c in default_value_calls]
        assert "URL:DevMon Protocol" in default_values
        assert any("devmon protocol dispatch" in v for v in default_values)
        assert any("'%1'" in v for v in default_values)
        assert any("-NoExit" in v for v in default_values)
        assert any("powershell" in v.lower() for v in default_values)

        url_protocol_calls = [c for c in fake_winreg.SetValueEx.call_args_list if c.args[1] == "URL Protocol"]
        assert len(url_protocol_calls) == 1
        assert url_protocol_calls[0].args[-1] == ""

    def test_install_prefers_windows_terminal_when_present(self, monkeypatch):
        from devmon.commands import protocol as protocol_cmd

        fake_winreg = MagicMock()
        fake_key_cm = MagicMock()
        fake_key_cm.__enter__ = MagicMock(return_value="FAKE_KEY_HANDLE")
        fake_key_cm.__exit__ = MagicMock(return_value=False)
        fake_winreg.CreateKey.return_value = fake_key_cm
        monkeypatch.setattr(protocol_cmd, "winreg", fake_winreg)

        def _fake_which(name):
            return r"C:\Fake\wt.exe" if "wt" in name else None

        monkeypatch.setattr(protocol_cmd.shutil, "which", _fake_which)

        runner = CliRunner()
        result = runner.invoke(protocol_cmd.app, ["install"])

        assert result.exit_code == 0
        assert "wt.exe" in result.output

    def test_install_non_windows_exits_1_without_touching_registry(self, monkeypatch):
        from devmon.commands import protocol as protocol_cmd

        fake_winreg = MagicMock()
        monkeypatch.setattr(protocol_cmd, "winreg", fake_winreg)
        monkeypatch.setattr(protocol_cmd.sys, "platform", "linux")

        runner = CliRunner()
        result = runner.invoke(protocol_cmd.app, ["install"])

        assert result.exit_code == 1
        assert "windows-only" in result.output.lower()
        fake_winreg.CreateKey.assert_not_called()


class TestProtocolUninstall:
    def test_uninstall_deletes_key_tree(self, monkeypatch):
        from devmon.commands import protocol as protocol_cmd

        fake_winreg = MagicMock()
        fake_winreg.HKEY_CURRENT_USER = "HKCU_SENTINEL"
        fake_winreg.OpenKey.return_value = "FAKE_KEY_HANDLE"
        # No subkeys -- EnumKey immediately signals "no more entries".
        fake_winreg.EnumKey.side_effect = OSError()

        monkeypatch.setattr(protocol_cmd, "winreg", fake_winreg)

        runner = CliRunner()
        result = runner.invoke(protocol_cmd.app, ["uninstall"])

        assert result.exit_code == 0
        assert "unregistered" in result.output.lower()
        fake_winreg.DeleteKey.assert_called_once_with(
            fake_winreg.HKEY_CURRENT_USER, protocol_cmd._KEY_PATH
        )

    def test_uninstall_missing_key_is_idempotent(self, monkeypatch):
        from devmon.commands import protocol as protocol_cmd

        fake_winreg = MagicMock()
        fake_winreg.OpenKey.side_effect = FileNotFoundError()
        monkeypatch.setattr(protocol_cmd, "winreg", fake_winreg)

        runner = CliRunner()
        result = runner.invoke(protocol_cmd.app, ["uninstall"])

        assert result.exit_code == 0
        fake_winreg.DeleteKey.assert_not_called()

    def test_uninstall_non_windows_exits_1(self, monkeypatch):
        from devmon.commands import protocol as protocol_cmd

        monkeypatch.setattr(protocol_cmd.sys, "platform", "linux")

        runner = CliRunner()
        result = runner.invoke(protocol_cmd.app, ["uninstall"])

        assert result.exit_code == 1
        assert "windows-only" in result.output.lower()


class TestProtocolDispatch:
    """`devmon protocol dispatch <url>` is what the registered `%1`
    placeholder actually invokes -- it parses the clicked devmon:// URL and
    spawns the matching subcommand as a real subprocess. All tests here
    monkeypatch subprocess.run; none may require `devmon app` to actually
    exist (a parallel agent is adding it)."""

    def test_battle_url_invokes_battle_subcommand(self, monkeypatch):
        from devmon.commands import protocol as protocol_cmd

        calls = []

        class _FakeResult:
            returncode = 0

        def _fake_run(argv, **kwargs):
            calls.append(argv)
            return _FakeResult()

        monkeypatch.setattr(protocol_cmd.subprocess, "run", _fake_run)

        runner = CliRunner()
        result = runner.invoke(protocol_cmd.app, ["dispatch", "devmon://battle"])

        assert result.exit_code == 0
        assert len(calls) == 1
        assert "battle" in calls[0]

    def test_app_url_invokes_app_subcommand(self, monkeypatch):
        from devmon.commands import protocol as protocol_cmd

        calls = []

        class _FakeResult:
            returncode = 0

        def _fake_run(argv, **kwargs):
            calls.append(argv)
            return _FakeResult()

        monkeypatch.setattr(protocol_cmd.subprocess, "run", _fake_run)

        runner = CliRunner()
        result = runner.invoke(protocol_cmd.app, ["dispatch", "devmon://app"])

        assert result.exit_code == 0
        assert len(calls) == 1
        assert "app" in calls[0]

    def test_battle_url_with_trailing_slash_still_resolves_to_battle(self, monkeypatch):
        from devmon.commands import protocol as protocol_cmd

        calls = []

        class _FakeResult:
            returncode = 0

        def _fake_run(argv, **kwargs):
            calls.append(argv)
            return _FakeResult()

        monkeypatch.setattr(protocol_cmd.subprocess, "run", _fake_run)

        runner = CliRunner()
        result = runner.invoke(protocol_cmd.app, ["dispatch", "devmon://battle/"])

        assert result.exit_code == 0
        assert len(calls) == 1
        assert "battle" in calls[0]

    def test_unknown_url_exits_nonzero_without_spawning(self, monkeypatch):
        from devmon.commands import protocol as protocol_cmd

        calls = []
        monkeypatch.setattr(
            protocol_cmd.subprocess, "run", lambda argv, **kwargs: calls.append(argv)
        )

        runner = CliRunner()
        result = runner.invoke(protocol_cmd.app, ["dispatch", "devmon://bogus"])

        assert result.exit_code != 0
        assert calls == []
        assert "unrecognized" in result.output.lower() or "usage" in result.output.lower()

    def test_non_devmon_scheme_exits_nonzero_without_spawning(self, monkeypatch):
        from devmon.commands import protocol as protocol_cmd

        calls = []
        monkeypatch.setattr(
            protocol_cmd.subprocess, "run", lambda argv, **kwargs: calls.append(argv)
        )

        runner = CliRunner()
        result = runner.invoke(protocol_cmd.app, ["dispatch", "not-a-url-at-all"])

        assert result.exit_code != 0
        assert calls == []

    def test_dispatch_exit_code_mirrors_subprocess_returncode(self, monkeypatch):
        from devmon.commands import protocol as protocol_cmd

        class _FakeResult:
            returncode = 7

        monkeypatch.setattr(
            protocol_cmd.subprocess, "run", lambda argv, **kwargs: _FakeResult()
        )

        runner = CliRunner()
        result = runner.invoke(protocol_cmd.app, ["dispatch", "devmon://battle"])

        assert result.exit_code == 7


class TestProtocolStatus:
    def test_status_reports_registered_command(self, monkeypatch):
        from devmon.commands import protocol as protocol_cmd

        fake_winreg = MagicMock()
        fake_key_cm = MagicMock()
        fake_key_cm.__enter__ = MagicMock(return_value="HANDLE")
        fake_key_cm.__exit__ = MagicMock(return_value=False)
        fake_winreg.OpenKey.return_value = fake_key_cm
        fake_winreg.QueryValueEx.return_value = (
            'powershell -NoLogo -NoExit -Command "devmon battle"', 1,
        )
        monkeypatch.setattr(protocol_cmd, "winreg", fake_winreg)

        runner = CliRunner()
        result = runner.invoke(protocol_cmd.app, ["status"])

        assert result.exit_code == 0
        assert "registered" in result.output.lower()
        assert "devmon battle" in result.output

    def test_status_reports_not_registered(self, monkeypatch):
        from devmon.commands import protocol as protocol_cmd

        fake_winreg = MagicMock()
        fake_winreg.OpenKey.side_effect = FileNotFoundError()
        monkeypatch.setattr(protocol_cmd, "winreg", fake_winreg)

        runner = CliRunner()
        result = runner.invoke(protocol_cmd.app, ["status"])

        assert result.exit_code == 0
        assert "not registered" in result.output.lower()

    def test_status_non_windows_reports_without_erroring(self, monkeypatch):
        from devmon.commands import protocol as protocol_cmd

        monkeypatch.setattr(protocol_cmd.sys, "platform", "linux")

        runner = CliRunner()
        result = runner.invoke(protocol_cmd.app, ["status"])

        assert result.exit_code == 0
        assert "windows-only" in result.output.lower()
