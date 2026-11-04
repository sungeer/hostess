from src.tools.read import tool_read


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


def test_negative_limit(tmp_path):
    p = _write(tmp_path, ['a', 'b', 'c'])
    result = tool_read.invoke({'file_path': str(p), 'limit': -1})
    assert 'limit' in result
    assert '错误' in result
