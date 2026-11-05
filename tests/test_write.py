import pytest

from src import settings
from src.tools.write import tool_write


@pytest.fixture(autouse=True)
def _workspace(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, 'WORKSPACE', tmp_path)


def test_new_file(tmp_path):
    result = tool_write.invoke({'file_path': 'a.txt', 'content': 'hi'})
    assert '已写入' in result
    assert (tmp_path / 'a.txt').read_text(encoding='utf-8') == 'hi'


def test_parent_dir_created(tmp_path):
    tool_write.invoke({'file_path': 'sub/dir/a.txt', 'content': 'hi'})
    assert (tmp_path / 'sub' / 'dir' / 'a.txt').read_text(encoding='utf-8') == 'hi'


def test_existing_file_rejected(tmp_path):
    p = tmp_path / 'a.txt'
    p.write_text('old', encoding='utf-8')
    result = tool_write.invoke({'file_path': 'a.txt', 'content': 'new'})
    assert '禁止覆盖' in result
    assert p.read_text(encoding='utf-8') == 'old'


def test_existing_directory_rejected(tmp_path):
    (tmp_path / 'd').mkdir()
    assert '禁止覆盖' in tool_write.invoke({'file_path': 'd', 'content': 'x'})


def test_outside_workspace_rejected(tmp_path):
    with pytest.raises(ValueError):
        tool_write.invoke({'file_path': '../outside.txt', 'content': 'x'})
