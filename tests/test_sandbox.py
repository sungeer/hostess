import pytest

from src import settings
from src.tools.glob import tool_glob


@pytest.fixture(autouse=True)
def _workspace(tmp_path, monkeypatch):
    ws = tmp_path / 'ws'
    ws.mkdir()
    monkeypatch.setattr(settings, 'WORKSPACE', ws)
    return ws


def test_resolve_inside_ok(_workspace):
    assert settings.resolve_path('a.txt') == (_workspace / 'a.txt').resolve()
    assert settings.resolve_path('.') == _workspace


@pytest.mark.parametrize('p', ['../outside.txt', 'C:/Windows/win.ini', '/etc/passwd'])
def test_resolve_outside_rejected(_workspace, p):
    with pytest.raises(ValueError):
        settings.resolve_path(p)


def test_glob_rejects_absolute_pattern(_workspace):
    assert '错误' in tool_glob.invoke({'pattern': 'C:/Windows/*.ini'})


def test_glob_rejects_parent_pattern(_workspace):
    assert '错误' in tool_glob.invoke({'pattern': '../*'})
