import pytest

from src import settings
from src.core.errors import ToolAbort
from src.tools.read import tool_read


@pytest.fixture(autouse=True)
def _workspace(tmp_path, monkeypatch):
    # 工具只允许操作 WORKSPACE 内的路径，测试把工作目录指到 tmp_path
    monkeypatch.setattr(settings, 'WORKSPACE', tmp_path)


def _write(tmp_path, lines):
    p = tmp_path / 'sample.txt'
    p.write_text('\n'.join(lines), encoding='utf-8')
    return p


def test_offset_beyond_end(tmp_path):
    p = _write(tmp_path, ['a', 'b', 'c'])
    result = tool_read.invoke({'file_path': str(p), 'offset': 5})
    assert 'offset' in result
    assert '超出' in result
    assert '共 3 行' in result


def test_offset_at_last_line_is_ok(tmp_path):
    p = _write(tmp_path, ['a', 'b', 'c'])
    result = tool_read.invoke({'file_path': str(p), 'offset': 3})
    assert result.rstrip().endswith('c')
    assert '错误' not in result


def test_line_too_long_raises(tmp_path):
    p = _write(tmp_path, ['ok', 'x' * 2001, 'ok'])
    with pytest.raises(ToolAbort):
        tool_read.invoke({'file_path': str(p)})


def test_line_at_threshold_is_ok(tmp_path):
    p = _write(tmp_path, ['x' * 2000])
    result = tool_read.invoke({'file_path': str(p)})
    assert 'x' * 2000 in result


def test_negative_limit(tmp_path):
    p = _write(tmp_path, ['a', 'b', 'c'])
    result = tool_read.invoke({'file_path': str(p), 'limit': -1})
    assert 'limit' in result
    assert '错误' in result
