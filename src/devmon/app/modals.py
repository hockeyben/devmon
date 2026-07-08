"""Modal screens for the DevMon Textual app.

`DoubleConfirmModal` enforces the hard project rule that releasing a
creature or prestiging must never happen from a single confirmation --
the user must press "Confirm" twice, each press showing a distinct prompt,
before `dismiss(True)` is ever called. A single press, or Cancel at any
point, dismisses with False/None and mutates nothing.
"""
from __future__ import annotations

from typing import Optional

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Static


class DoubleConfirmModal(ModalScreen[bool]):
    """Two-step Yes/Yes-again confirmation dialog. Cancel-safe at every step."""

    DEFAULT_CSS = """
    DoubleConfirmModal {
        align: center middle;
    }
    DoubleConfirmModal > Vertical {
        width: 64;
        height: auto;
        border: thick $error 80%;
        background: $surface;
        padding: 1 2;
    }
    DoubleConfirmModal .confirm-title {
        text-style: bold;
        margin-bottom: 1;
    }
    DoubleConfirmModal .confirm-body {
        margin-bottom: 1;
    }
    DoubleConfirmModal .confirm-buttons {
        align: center middle;
        height: auto;
    }
    """

    def __init__(self, title: str, first_prompt: str, second_prompt: str) -> None:
        super().__init__()
        self._title = title
        self._first_prompt = first_prompt
        self._second_prompt = second_prompt
        self._step = 0

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static(self._title, classes="confirm-title")
            yield Static(self._first_prompt, classes="confirm-body", id="confirm-body")
            with Horizontal(classes="confirm-buttons"):
                yield Button("Confirm", id="confirm", variant="error")
                yield Button("Cancel", id="cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        if event.button.id == "cancel":
            self.dismiss(False)
            return
        if event.button.id == "confirm":
            if self._step == 0:
                self._step = 1
                self.query_one("#confirm-body", Static).update(self._second_prompt)
                self.query_one("#confirm", Button).label = "Confirm Again"
                return
            self.dismiss(True)


class AmountModal(ModalScreen[Optional[int]]):
    """Prompt for a positive integer amount (e.g. how much candy to feed)."""

    DEFAULT_CSS = """
    AmountModal {
        align: center middle;
    }
    AmountModal > Vertical {
        width: 50;
        height: auto;
        border: thick $primary 80%;
        background: $surface;
        padding: 1 2;
    }
    AmountModal .amount-buttons {
        align: center middle;
        height: auto;
        margin-top: 1;
    }
    """

    def __init__(self, title: str, max_amount: int) -> None:
        super().__init__()
        self._title = title
        self._max_amount = max(1, max_amount)

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static(self._title)
            yield Input(
                placeholder=f"1-{self._max_amount}",
                value="1",
                id="amount-input",
            )
            with Horizontal(classes="amount-buttons"):
                yield Button("Feed", id="ok", variant="success")
                yield Button("Cancel", id="cancel")

    def _resolve(self) -> None:
        raw = self.query_one("#amount-input", Input).value.strip()
        try:
            amount = int(raw)
        except ValueError:
            self.dismiss(None)
            return
        if amount < 1 or amount > self._max_amount:
            self.dismiss(None)
            return
        self.dismiss(amount)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        if event.button.id == "cancel":
            self.dismiss(None)
            return
        if event.button.id == "ok":
            self._resolve()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        event.stop()
        self._resolve()


class ConfirmModal(ModalScreen[bool]):
    """Single Yes/No confirmation (for non-destructive actions like travel --
    the hard double-confirm rule only applies to release and prestige)."""

    DEFAULT_CSS = """
    ConfirmModal {
        align: center middle;
    }
    ConfirmModal > Vertical {
        width: 60;
        height: auto;
        border: thick $primary 80%;
        background: $surface;
        padding: 1 2;
    }
    ConfirmModal .confirm-buttons {
        align: center middle;
        height: auto;
        margin-top: 1;
    }
    """

    def __init__(self, title: str, body: str) -> None:
        super().__init__()
        self._title = title
        self._body = body

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static(self._title, classes="confirm-title")
            yield Static(self._body)
            with Horizontal(classes="confirm-buttons"):
                yield Button("Confirm", id="confirm", variant="primary")
                yield Button("Cancel", id="cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        self.dismiss(event.button.id == "confirm")


class MessageModal(ModalScreen[None]):
    """Simple dismissible info/result popup (craft result, purchase result, etc.)."""

    DEFAULT_CSS = """
    MessageModal {
        align: center middle;
    }
    MessageModal > Vertical {
        width: 64;
        height: auto;
        border: thick $primary 80%;
        background: $surface;
        padding: 1 2;
    }
    """

    def __init__(self, title: str, body: str) -> None:
        super().__init__()
        self._title = title
        self._body = body

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static(self._title, classes="confirm-title")
            yield Static(self._body)
            yield Button("OK", id="ok", variant="primary")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        self.dismiss(None)
