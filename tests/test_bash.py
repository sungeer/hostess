import pytest

from src import settings
from src.tools.bash import tool_bash


@pytest.fixture(autouse=True)
def _workspace(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, 'WORKSPACE', tmp_path)


def test_echo_and_exit_code():
    result = tool_bash.invoke({'command': 'echo hi'})
    assert 'hi' in result
    assert '退出码 0' in result


def test_cwd_is_workspace(tmp_path):
    (tmp_path / 'a.txt').write_text('x', encoding='utf-8')
    assert 'a.txt' in tool_bash.invoke({'command': 'ls'})


def test_nonzero_exit_code():
    assert '退出码 3' in tool_bash.invoke({'command': 'exit 3'})


def test_stderr_captured():
    assert 'boom' in tool_bash.invoke({'command': 'echo boom >&2'})


def test_timeout():
    assert '超时' in tool_bash.invoke({'command': 'sleep 5', 'timeout': 1})


def test_output_truncated():
    result = tool_bash.invoke({'command': "printf 'x%.0s' {1..30000}"})
    assert '已截断' in result


def test_missing_bash(monkeypatch):
    monkeypatch.setattr(settings, 'BASH_PATH', '')
    assert '错误' in tool_bash.invoke({'command': 'echo hi'})


def test_invalid_timeout():
    assert '错误' in tool_bash.invoke({'command': 'echo hi', 'timeout': 0})
