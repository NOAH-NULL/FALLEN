"""Import smoke tests for every extension registered by the bot."""

from importlib import import_module

import pytest

from bot.core.bot import EXTENSIONS


@pytest.mark.parametrize("extension", EXTENSIONS)
def test_registered_extension_imports(extension):
    module = import_module(extension)
    assert callable(getattr(module, "setup", None)), (
        f"{extension} must expose an async setup(bot) entry point"
    )
