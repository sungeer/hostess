import pytest

from src import settings
from src.tools.edit import tool_edit


@pytest.fixture(autouse=True)
def _workspace(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, 'WORKSPACE', tmp_path)


def _write(tmp_path, text, name='a.txt'):
    p = tmp_path / name
    p.write_text(text, encoding='utf-8', newline='')
    return p


def _edit(path, edits):
    return tool_edit.invoke({'path': str(path), 'edits': edits})


def test_single_edit(tmp_path):
    p = _write(tmp_path, 'hello world\n')
    assert '已替换 1 处' in _edit(p, [{'oldText': 'world', 'newText': 'python'}])
    assert p.read_text(encoding='utf-8') == 'hello python\n'


def test_multiple_disjoint_edits_matched_against_original(tmp_path):
    p = _write(tmp_path, 'a\nb\nc\n')
    result = _edit(p, [
        {'oldText': 'a', 'newText': 'A'},
        {'oldText': 'c', 'newText': 'C'},
    ])
    assert '已替换 2 处' in result
    assert p.read_text(encoding='utf-8') == 'A\nb\nC\n'


def test_not_found(tmp_path):
    p = _write(tmp_path, 'hello\n')
    assert '找不到' in _edit(p, [{'oldText': 'nope', 'newText': 'x'}])
    assert p.read_text(encoding='utf-8') == 'hello\n'


def test_duplicate_rejected(tmp_path):
    p = _write(tmp_path, 'x\nx\n')
    assert '必须唯一' in _edit(p, [{'oldText': 'x', 'newText': 'y'}])


def test_overlap_rejected(tmp_path):
    p = _write(tmp_path, 'abcdef\n')
    assert '重叠' in _edit(p, [
        {'oldText': 'abc', 'newText': 'A'},
        {'oldText': 'cde', 'newText': 'B'},
    ])


def test_empty_edits_rejected(tmp_path):
    p = _write(tmp_path, 'hello\n')
    assert 'edits 不能为空' in _edit(p, [])


def test_empty_old_text_rejected(tmp_path):
    p = _write(tmp_path, 'hello\n')
    assert 'oldText 不能为空' in _edit(p, [{'oldText': '', 'newText': 'x'}])


def test_no_change_rejected(tmp_path):
    p = _write(tmp_path, 'hello\n')
    assert '没有变化' in _edit(p, [{'oldText': 'hello', 'newText': 'hello'}])


def test_missing_file(tmp_path):
    assert '不存在' in _edit(tmp_path / 'nope.txt', [{'oldText': 'a', 'newText': 'b'}])


def test_directory_rejected(tmp_path):
    assert '目录' in _edit(tmp_path, [{'oldText': 'a', 'newText': 'b'}])


def test_crlf_preserved(tmp_path):
    p = _write(tmp_path, 'a\r\nb\r\n')
    assert '已替换 1 处' in _edit(p, [{'oldText': 'a\nb', 'newText': 'a\nc'}])
    assert p.read_bytes() == b'a\r\nc\r\n'


def test_lf_file_stays_lf(tmp_path):
    p = _write(tmp_path, 'a\nb\n')
    assert '已替换 1 处' in _edit(p, [{'oldText': 'b', 'newText': 'c'}])
    assert p.read_bytes() == b'a\nc\n'


def test_bom_preserved(tmp_path):
    p = _write(tmp_path, '\ufeffa\n')
    assert '已替换 1 处' in _edit(p, [{'oldText': 'a', 'newText': 'b'}])
    assert p.read_bytes() == '\ufeffb\n'.encode('utf-8')


def test_first_changed_line_reported(tmp_path):
    p = _write(tmp_path, 'a\nb\nc\n')
    assert '第 2 行' in _edit(p, [{'oldText': 'b', 'newText': 'B'}])
