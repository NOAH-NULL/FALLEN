import pytest
from unittest.mock import AsyncMock

from bot.commands.rules import Rules, _guard_rules_command


def test_all_rules_subcommands_are_registered():
    registered = {command.name for command in Rules.rules.commands}
    assert registered == {
        "setup",
        "add",
        "edit",
        "remove",
        "button",
        "publish",
        "edit-panel",
        "image",
        "image-url",
        "remove-image",
        "status",
    }


@pytest.mark.asyncio
async def test_rules_command_guard_reports_uncaught_failure():
    interaction = object()

    class FakeRules:
        def __init__(self):
            self._report_error = AsyncMock()
            self.bot = type(
                "FakeBot",
                (),
                {"log": type("FakeLog", (), {"error": lambda *args, **kwargs: None})()},
            )()

    async def failing_callback(self, received_interaction):
        assert received_interaction is interaction
        raise RuntimeError("database unavailable")

    guarded = _guard_rules_command(failing_callback)
    instance = FakeRules()

    result = await guarded(instance, interaction)

    assert result is None
    instance._report_error.assert_awaited_once()
    assert isinstance(instance._report_error.await_args.args[1], RuntimeError)
