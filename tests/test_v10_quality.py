import ast
from pathlib import Path


def _command_names(path: Path, decorator_owner: str):
    tree = ast.parse(path.read_text())
    names = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr != 'command' or not isinstance(node.func.value, ast.Name) or node.func.value.id != decorator_owner:
            continue
        for kw in node.keywords:
            if kw.arg == 'name' and isinstance(kw.value, ast.Constant):
                names.add(kw.value.value)
    return names


def test_top_level_slash_commands_have_prefix_counterparts():
    root = Path('bot/commands')
    slash = set()
    prefix = set()
    prefix_groups = set()
    for path in root.glob('*.py'):
        slash |= _command_names(path, 'app_commands')
        prefix |= _command_names(path, 'commands')
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == 'group':
                if isinstance(node.func.value, ast.Name) and node.func.value.id == 'commands':
                    for kw in node.keywords:
                        if kw.arg == 'name' and isinstance(kw.value, ast.Constant): prefix_groups.add(kw.value.value)
    missing = sorted(slash - prefix - prefix_groups)
    assert not missing, f'No prefix implementation for: {missing}'


def test_reaction_surface_is_cached_and_fast():
    src = Path('bot/services/reactions.py').read_text()
    assert '_cache' in src
    assert 'asyncio.Lock' in src
    assert 'ClientTimeout(total=3.0)' in src
    assert 'if cached' in src


def test_action_surface_contains_fast_social_commands():
    src = Path('bot/commands/fun.py').read_text()
    for name in ('hug', 'highfive', 'pat', 'poke', 'bonk', 'wave', 'dance', 'smile', 'cry', 'shrug', 'sleep', 'boop', 'tickle', 'punch'):
        assert f"name='{name}'" in src


def test_release_excludes_runtime_artifacts():
    ignore = Path('.gitignore').read_text() + Path('.dockerignore').read_text()
    assert '__pycache__/' in ignore
    assert '*.pyc' in ignore
    assert '.pytest_cache/' in ignore
